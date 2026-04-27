"""Tests for MCP configuration detection."""
import json
from pathlib import Path

from luminamind.mcp.config import (
    MCPServerConfig,
    detect_all_mcp_configs,
    load_custom_config,
)


def test_mcpserverconfig_from_dict():
    data = {
        "transport": "stdio",
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
        "env": {"FOO": "bar"},
    }
    cfg = MCPServerConfig.from_dict("filesystem", data)
    assert cfg.name == "filesystem"
    assert cfg.transport == "stdio"
    assert cfg.command == "npx"
    assert cfg.args == ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]


def test_load_custom_config(tmp_path):
    config_file = tmp_path / "mcp.json"
    config_file.write_text(
        json.dumps(
            {
                "servers": {
                    "test-server": {
                        "transport": "stdio",
                        "command": "python",
                        "args": ["server.py"],
                    }
                }
            }
        )
    )
    configs = load_custom_config(path=config_file)
    assert len(configs) == 1
    assert configs[0].name == "test-server"
