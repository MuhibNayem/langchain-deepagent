"""Model Context Protocol (MCP) integration for LuminaMind."""
from luminamind.mcp.client import MCPClientManager, get_mcp_manager
from luminamind.mcp.config import (
    MCPServerConfig,
    detect_all_mcp_configs,
    detect_claude_desktop_config,
    detect_cursor_config,
    load_custom_config,
)
from luminamind.mcp.tool_adapter import MCPToolAdapter

__all__ = [
    "MCPServerConfig",
    "detect_all_mcp_configs",
    "detect_claude_desktop_config",
    "detect_cursor_config",
    "load_custom_config",
    "MCPToolAdapter",
    "MCPClientManager",
    "get_mcp_manager",
]
