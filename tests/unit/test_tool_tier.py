"""Unit tests for tool tiering system."""

import pytest
from luminamind.config.tool_tier import (
    ToolTier,
    TierConfig,
    ToolTierEngine,
    create_tiered_registry,
    DEFAULT_TIER_ASSIGNMENTS,
)


# Mock tool functions for testing
def mock_tool(name: str):
    def tool_func():
        return name
    return tool_func


@pytest.fixture
def sample_registry():
    return {
        "tool_a": mock_tool("tool_a"),
        "tool_b": mock_tool("tool_b"),
        "tool_c": mock_tool("tool_c"),
    }


@pytest.fixture
def sample_tiers():
    return {
        "tool_a": TierConfig(tier=ToolTier.CORE, task_types=[], min_score=0.0),
        "tool_b": TierConfig(tier=ToolTier.EXTENDED, task_types=["code-editing"], min_score=0.0),
        "tool_c": TierConfig(tier=ToolTier.SPECIALIST, task_types=["web-research"], min_score=0.3),
    }


def test_tier_config_model():
    """Test TierConfig model with tier, task_types, and min_score fields."""
    config = TierConfig(tier=ToolTier.CORE, task_types=["coding"], min_score=0.5)
    assert config.tier == ToolTier.CORE
    assert config.task_types == ["coding"]
    assert config.min_score == 0.5


def test_tier_config_default_values():
    """Test TierConfig default values."""
    config = TierConfig(tier=ToolTier.EXTENDED)
    assert config.tier == ToolTier.EXTENDED
    assert config.task_types == []
    assert config.min_score == 0.0


def test_tool_tier_enum():
    """Test ToolTier enum values."""
    assert ToolTier.CORE.value == "core"
    assert ToolTier.EXTENDED.value == "extended"
    assert ToolTier.SPECIALIST.value == "specialist"


def test_create_tiered_registry(sample_registry, sample_tiers):
    """Test create_tiered_registry creates registry with tier metadata."""
    tiered = create_tiered_registry(sample_registry, sample_tiers)
    assert len(tiered) == 3
    assert tiered["tool_a"][0] == sample_registry["tool_a"]
    assert tiered["tool_a"][1].tier == ToolTier.CORE
    assert tiered["tool_c"][1].tier == ToolTier.SPECIALIST


def test_create_tiered_registry_with_defaults():
    """Test create_tiered_registry uses default assignments."""
    registry = {"shell": mock_tool("shell")}
    tiered = create_tiered_registry(registry)
    assert "shell" in tiered
    assert tiered["shell"][1].tier == ToolTier.CORE


def test_create_tiered_registry_unknown_tool():
    """Test create_tiered_registry defaults unknown tools to EXTENDED."""
    registry = {"unknown_tool": mock_tool("unknown_tool")}
    tiered = create_tiered_registry(registry)
    assert "unknown_tool" in tiered
    assert tiered["unknown_tool"][1].tier == ToolTier.EXTENDED


def test_tool_tier_engine_core_only(sample_registry, sample_tiers):
    """Test ToolTierEngine.get_core_tools() returns only CORE tier tools."""
    tiered = create_tiered_registry(sample_registry, sample_tiers)
    engine = ToolTierEngine(tiered)
    core = engine.get_core_tools()
    assert len(core) == 1


def test_tool_tier_engine_get_tier_for_tool(sample_registry, sample_tiers):
    """Test ToolTierEngine.get_tier_for_tool() returns correct tier."""
    tiered = create_tiered_registry(sample_registry, sample_tiers)
    engine = ToolTierEngine(tiered)
    assert engine.get_tier_for_tool("tool_a") == ToolTier.CORE
    assert engine.get_tier_for_tool("tool_b") == ToolTier.EXTENDED
    assert engine.get_tier_for_tool("tool_c") == ToolTier.SPECIALIST
    assert engine.get_tier_for_tool("nonexistent") is None


def test_tool_tier_engine_context_filter(sample_registry, sample_tiers):
    """Test ToolTierEngine filters by task type correctly."""
    tiered = create_tiered_registry(sample_registry, sample_tiers)
    engine = ToolTierEngine(tiered)
    tools = engine.get_tools_for_context(task_type="code-editing")
    tool_names = [t() for t in tools]
    assert "tool_a" in tool_names  # CORE (always included)
    assert "tool_b" in tool_names  # EXTENDED + task match


def test_tool_tier_engine_no_task_type(sample_registry, sample_tiers):
    """Test ToolTierEngine includes CORE and EXTENDED when no task_type."""
    tiered = create_tiered_registry(sample_registry, sample_tiers)
    engine = ToolTierEngine(tiered)
    tools = engine.get_tools_for_context()
    tool_names = [t() for t in tools]
    assert "tool_a" in tool_names  # CORE
    assert "tool_b" in tool_names  # EXTENDED (no task_types restriction)
    # tool_c not included (SPECIALIST requires task_type match)


def test_tool_tier_engine_score_threshold(sample_registry, sample_tiers):
    """Test ToolTierEngine filters by minimum score correctly."""
    tiered = create_tiered_registry(sample_registry, sample_tiers)
    engine = ToolTierEngine(tiered)
    # Below threshold
    tools = engine.get_tools_for_context(task_type="web-research", min_score=0.1)
    tool_names = [t() for t in tools]
    assert "tool_c" not in tool_names  # min_score=0.3 > 0.1
    # At threshold
    tools = engine.get_tools_for_context(task_type="web-research", min_score=0.3)
    tool_names = [t() for t in tools]
    assert "tool_c" in tool_names  # min_score=0.3 <= 0.3
    # Above threshold
    tools = engine.get_tools_for_context(task_type="web-research", min_score=0.5)
    tool_names = [t() for t in tools]
    assert "tool_c" in tool_names  # min_score=0.3 <= 0.5


def test_tool_tier_engine_max_tools(sample_registry, sample_tiers):
    """Test ToolTierEngine respects max_tools cap."""
    tiered = create_tiered_registry(sample_registry, sample_tiers)
    engine = ToolTierEngine(tiered)
    tools = engine.get_tools_for_context(max_tools=2)
    assert len(tools) <= 2


def test_default_tier_assignments():
    """Verify default assignments cover all registry tools."""
    from luminamind.py_tools.registry import PY_TOOL_REGISTRY
    tiered = create_tiered_registry(PY_TOOL_REGISTRY, DEFAULT_TIER_ASSIGNMENTS)
    # All tools in registry should be in tiered registry
    for name in PY_TOOL_REGISTRY:
        assert name in tiered, f"Tool {name} not in tiered registry"


def test_default_tier_assignments_values():
    """Verify default tier assignments have correct values."""
    # CORE tools
    assert DEFAULT_TIER_ASSIGNMENTS["read_file"].tier == ToolTier.CORE
    assert DEFAULT_TIER_ASSIGNMENTS["write_file"].tier == ToolTier.CORE
    assert DEFAULT_TIER_ASSIGNMENTS["shell"].tier == ToolTier.CORE
    assert DEFAULT_TIER_ASSIGNMENTS["grep_search"].tier == ToolTier.CORE
    # EXTENDED tools
    assert DEFAULT_TIER_ASSIGNMENTS["list_directory"].tier == ToolTier.EXTENDED
    assert DEFAULT_TIER_ASSIGNMENTS["tree_view"].tier == ToolTier.EXTENDED
    assert DEFAULT_TIER_ASSIGNMENTS["multi_replace_in_file"].tier == ToolTier.EXTENDED
    assert DEFAULT_TIER_ASSIGNMENTS["apply_patch"].tier == ToolTier.EXTENDED
    # SPECIALIST tools
    assert DEFAULT_TIER_ASSIGNMENTS["web_search"].tier == ToolTier.SPECIALIST
    assert DEFAULT_TIER_ASSIGNMENTS["fetch_as_markdown"].tier == ToolTier.SPECIALIST
    assert DEFAULT_TIER_ASSIGNMENTS["get_weather"].tier == ToolTier.SPECIALIST
    assert DEFAULT_TIER_ASSIGNMENTS["read_files_in_directory"].tier == ToolTier.SPECIALIST


def test_specialist_requires_task_match(sample_registry, sample_tiers):
    """Test that specialist tools require task type match."""
    tiered = create_tiered_registry(sample_registry, sample_tiers)
    engine = ToolTierEngine(tiered)
    # task_c is SPECIALIST with task_types=["web-research"]
    # Without matching task_type, specialist tools should not be included
    tools = engine.get_tools_for_context(task_type="general")
    tool_names = [t() for t in tools]
    assert "tool_c" not in tool_names  # specialist requires web-research