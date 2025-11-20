"""Unit tests for the tool registry."""

from luminamind.py_tools.registry import PY_TOOL_REGISTRY

def test_registry_contains_expected_tools():
    """Test that the registry contains all expected tools."""
    expected_tools = [
        "os_info",
        "edit_file",
        "shell",
        "replace_in_file",
        "get_weather",
        "web_crawl",
        "web_search",
    ]
    
    for tool_name in expected_tools:
        assert tool_name in PY_TOOL_REGISTRY
        assert PY_TOOL_REGISTRY[tool_name].name == tool_name

def test_registry_tools_are_callable():
    """Test that registered tools are valid BaseTool instances."""
    for tool in PY_TOOL_REGISTRY.values():
        assert hasattr(tool, "invoke")
        assert hasattr(tool, "name")
        assert hasattr(tool, "description")
