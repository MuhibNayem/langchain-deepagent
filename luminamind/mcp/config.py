"""MCP configuration management.

Detects and loads MCP server configs from:
- Environment variable LUMINAMIND_MCP_CONFIG
- Claude Desktop config
- Custom JSON configs
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class MCPServerConfig:
    """Configuration for a single MCP server."""

    name: str
    transport: str  # stdio | sse | http
    command: str | None = None
    args: list[str] | None = None
    url: str | None = None
    env: dict[str, str] | None = None
    headers: dict[str, str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "transport": self.transport,
            "command": self.command,
            "args": self.args,
            "url": self.url,
            "env": self.env,
            "headers": self.headers,
        }

    @classmethod
    def from_dict(cls, name: str, data: dict[str, Any]) -> "MCPServerConfig":
        return cls(
            name=name,
            transport=data.get("transport", "stdio"),
            command=data.get("command"),
            args=data.get("args"),
            url=data.get("url"),
            env=data.get("env"),
            headers=data.get("headers"),
        )


def detect_claude_desktop_config() -> list[MCPServerConfig]:
    """Detect MCP servers from Claude Desktop config."""
    configs: list[MCPServerConfig] = []
    config_paths = [
        Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json",  # macOS
        Path.home() / ".config" / "Claude" / "claude_desktop_config.json",  # Linux
        Path.home() / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json",  # Windows
    ]
    for path in config_paths:
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                mcp_data = data.get("mcpServers", {})
                for name, server in mcp_data.items():
                    cfg = MCPServerConfig.from_dict(name, server)
                    if cfg.transport == "stdio" and cfg.command:
                        cfg.transport = "stdio"
                    elif cfg.url:
                        cfg.transport = "sse"
                    configs.append(cfg)
            except Exception:
                pass
            break
    return configs


def detect_cursor_config() -> list[MCPServerConfig]:
    """Detect MCP servers from Cursor IDE config."""
    configs: list[MCPServerConfig] = []
    path = Path.home() / ".cursor" / "mcp.json"
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            mcp_data = data.get("mcpServers", {})
            for name, server in mcp_data.items():
                configs.append(MCPServerConfig.from_dict(name, server))
        except Exception:
            pass
    return configs


def load_custom_config(path: str | Path | None = None) -> list[MCPServerConfig]:
    """Load custom MCP config from file or env."""
    configs: list[MCPServerConfig] = []
    env_path = os.environ.get("LUMINAMIND_MCP_CONFIG")
    if env_path:
        p = Path(env_path).expanduser()
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                for name, server in data.get("servers", {}).items():
                    configs.append(MCPServerConfig.from_dict(name, server))
            except Exception:
                pass
    if path:
        p = Path(path).expanduser()
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                for name, server in data.get("servers", {}).items():
                    configs.append(MCPServerConfig.from_dict(name, server))
            except Exception:
                pass
    return configs


def detect_all_mcp_configs() -> list[MCPServerConfig]:
    """Detect all MCP server configurations from known sources."""
    configs: list[MCPServerConfig] = []
    seen = set()
    for source in [detect_claude_desktop_config, detect_cursor_config, load_custom_config]:
        for cfg in source():
            if cfg.name not in seen:
                configs.append(cfg)
                seen.add(cfg.name)
    return configs
