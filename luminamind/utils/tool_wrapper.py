from typing import Any, Optional, Type
from langchain_core.tools import BaseTool
from pydantic import BaseModel

from luminamind.config.settings import MAX_TOOL_OUTPUT_TOKENS
from luminamind.utils.content_manager import count_tokens

class SmartTool(BaseTool):
    """
    A wrapper around a BaseTool that truncates its output if it exceeds a token limit.
    """
    original_tool: BaseTool
    name: str
    description: str
    args_schema: Optional[Type[BaseModel]] = None

    def __init__(self, tool: BaseTool, **kwargs):
        super().__init__(
            original_tool=tool,
            name=tool.name,
            description=tool.description,
            args_schema=tool.args_schema,
            **kwargs
        )

    def _run(self, *args, **kwargs) -> Any:
        """Run the tool and truncate output."""
        run_manager = kwargs.pop("run_manager", None)
        if args:
            tool_input = args[0]
        else:
            tool_input = kwargs
            
        result = self.original_tool.run(tool_input, run_manager=run_manager)
        return self._truncate_result(result)

    async def _arun(self, *args, **kwargs) -> Any:
        """Run the tool asynchronously and truncate output."""
        run_manager = kwargs.pop("run_manager", None)
        if args:
            tool_input = args[0]
        else:
            tool_input = kwargs
            
        if hasattr(self.original_tool, "_arun"):
            result = await self.original_tool.arun(tool_input, run_manager=run_manager)
        else:
            result = await self.original_tool.arun(tool_input, run_manager=run_manager)
            
        return self._truncate_result(result)

    def _truncate_result(self, result: Any) -> Any:
        """Truncate the result if it's too long."""
        if not isinstance(result, str):
            return result
            
        tokens = count_tokens(result)
        if tokens > MAX_TOOL_OUTPUT_TOKENS:
            keep_ratio = 0.5 # Keep 50% head, 50% tail roughly? No, usually head is more important?
            # Let's keep 4000 tokens.
            # Actually, let's just keep the head and tail.
            limit = MAX_TOOL_OUTPUT_TOKENS
            head = int(limit * 0.6)
            tail = int(limit * 0.4)
            
            # This is a rough char approximation if we don't want to decode/encode
            # But we have count_tokens.
            # For speed, let's just use char approximation assuming 4 chars/token
            # limit_chars = limit * 4
            # ...
            # Let's use the simple truncation message
            return result[:head*4] + f"\n... [OUTPUT TRUNCATED: {tokens - limit} tokens omitted] ...\n" + result[-tail*4:]
            
        return result

def wrap_tool(tool: BaseTool) -> BaseTool:
    return SmartTool(tool)
