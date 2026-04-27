"""Convert MCP server tools into LangChain-compatible tools.

Uses the official `mcp` Python SDK client to connect to servers,
discover tools, and wrap them as LangChain Tool instances.
"""
from __future__ import annotations

from typing import Any, Callable

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, create_model

from luminamind.mcp.config import MCPServerConfig


def _schema_to_pydantic(name: str, schema: dict[str, Any]) -> type[BaseModel]:
    """Convert a JSON schema to a Pydantic model for StructuredTool."""
    properties = schema.get("properties", {})
    required = set(schema.get("required", []))
    fields: dict[str, Any] = {}
    for prop_name, prop_schema in properties.items():
        prop_type = _json_schema_type_to_python(prop_schema)
        if prop_name not in required:
            prop_type = Optional[prop_type]
        default = ... if prop_name in required else None
        fields[prop_name] = (prop_type, default)
    return create_model(name, **fields)


def _json_schema_type_to_python(prop: dict[str, Any]) -> type:
    """Simple JSON schema -> Python type mapping."""
    t = prop.get("type", "string")
    if t == "string":
        return str
    elif t == "integer":
        return int
    elif t == "number":
        return float
    elif t == "boolean":
        return bool
    elif t == "array":
        return list
    elif t == "object":
        return dict
    return str


class MCPToolAdapter:
    """Adapter that connects to an MCP server and exposes its tools."""

    def __init__(self, config: MCPServerConfig) -> None:
        self.config = config
        self._client: Any = None
        self._session: Any = None
        self._tools: list[StructuredTool] = []

    async def connect(self) -> None:
        """Establish connection to the MCP server."""
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
        except ImportError as exc:
            raise ImportError("mcp package required. Install with: pip install mcp") from exc

        if self.config.transport == "stdio":
            params = StdioServerParameters(
                command=self.config.command or "",
                args=self.config.args or [],
                env={**os.environ, **(self.config.env or {})},
            )
            self._client = stdio_client(params)
            read, write = await self._client.__aenter__()
            self._session = ClientSession(read, write)
            await self._session.__aenter__()
            await self._session.initialize()
        else:
            # SSE / HTTP transport
            raise NotImplementedError(f"Transport {self.config.transport} not yet supported")

    async def disconnect(self) -> None:
        if self._session:
            await self._session.__aexit__(None, None, None)
            self._session = None
        if self._client:
            await self._client.__aexit__(None, None, None)
            self._client = None

    async def discover_tools(self) -> list[StructuredTool]:
        """Discover and wrap all tools from the MCP server."""
        if self._session is None:
            raise RuntimeError("Not connected. Call connect() first.")
        response = await self._session.list_tools()
        tools: list[StructuredTool] = []
        for tool_info in response.tools:
            wrapped = self._wrap_tool(tool_info)
            tools.append(wrapped)
        self._tools = tools
        return tools

    def _wrap_tool(self, tool_info: Any) -> StructuredTool:
        name = tool_info.name
        description = tool_info.description or ""
        schema = tool_info.inputSchema
        input_model = _schema_to_pydantic(f"{name}_input", schema)

        async def _invoke(**kwargs: Any) -> str:
            if self._session is None:
                raise RuntimeError("MCP session not connected")
            result = await self._session.call_tool(name, arguments=kwargs)
            # Flatten content to string
            parts = []
            for content in result.content:
                if hasattr(content, "text"):
                    parts.append(content.text)
                else:
                    parts.append(str(content))
            return "\n".join(parts)

        return StructuredTool.from_function(
            func=_invoke,
            name=name,
            description=description,
            args_schema=input_model,
            coroutine=_invoke,
        )


import os
from typing import Optional
