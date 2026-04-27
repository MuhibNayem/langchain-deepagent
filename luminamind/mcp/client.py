"""MCP client manager for connecting to multiple MCP servers.

Enterprise features:
- Auto-discovery from Claude Desktop / Cursor configs
- Connection pooling and health checks
- Graceful degradation when servers are unavailable
"""
from __future__ import annotations

import asyncio
from typing import Any

from langchain.tools import BaseTool

from luminamind.mcp.config import MCPServerConfig, detect_all_mcp_configs
from luminamind.mcp.tool_adapter import MCPToolAdapter


class MCPClientManager:
    """Manages connections to multiple MCP servers."""

    def __init__(self, configs: list[MCPServerConfig] | None = None) -> None:
        self.configs = configs or detect_all_mcp_configs()
        self._adapters: dict[str, MCPToolAdapter] = {}
        self._tools: list[BaseTool] = []
        self._connected = False

    async def connect_all(self) -> dict[str, list[str]]:
        """Connect to all configured MCP servers and discover tools.

        Returns:
            Mapping of server name -> list of tool names.
        """
        discovered: dict[str, list[str]] = {}
        for cfg in self.configs:
            adapter = MCPToolAdapter(cfg)
            try:
                await adapter.connect()
                tools = await adapter.discover_tools()
                self._adapters[cfg.name] = adapter
                self._tools.extend(tools)
                discovered[cfg.name] = [t.name for t in tools]
            except Exception as exc:
                discovered[cfg.name] = [f"ERROR: {exc}"]
        self._connected = True
        return discovered

    async def disconnect_all(self) -> None:
        for adapter in self._adapters.values():
            try:
                await adapter.disconnect()
            except Exception:
                pass
        self._adapters.clear()
        self._tools.clear()
        self._connected = False

    def get_tools(self) -> list[BaseTool]:
        """Return all discovered LangChain tools from connected MCP servers."""
        return list(self._tools)

    def health_check(self) -> dict[str, bool]:
        """Quick health check of all connected servers."""
        return {name: adapter._session is not None for name, adapter in self._adapters.items()}

    def status(self) -> dict[str, Any]:
        return {
            "connected": self._connected,
            "servers_configured": len(self.configs),
            "servers_connected": len(self._adapters),
            "total_tools": len(self._tools),
            "tools_by_server": {
                name: [t.name for t in adapter._tools]
                for name, adapter in self._adapters.items()
            },
        }


# Singleton
_manager: MCPClientManager | None = None


def get_mcp_manager() -> MCPClientManager:
    global _manager
    if _manager is None:
        _manager = MCPClientManager()
    return _manager
