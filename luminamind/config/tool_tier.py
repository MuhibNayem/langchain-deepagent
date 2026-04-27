"""Tool tiering system for context-dependent tool selection."""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Callable, Literal
from pydantic import BaseModel


class ToolTier(str, Enum):
    """Tool tier classification."""
    CORE = "core"       # Always available
    EXTENDED = "extended"  # Task-dependent
    SPECIALIST = "specialist"  # Role-specific


class TierConfig(BaseModel):
    """Configuration for a tool's tier assignment."""
    tier: ToolTier
    task_types: list[str] = []  # e.g., ["code-editing", "web-research"]
    min_score: float = 0.0  # Minimum evaluator score to unlock


# Initial tier assignments (per D-01)
DEFAULT_TIER_ASSIGNMENTS: dict[str, TierConfig] = {
    # CORE - always available
    "read_file": TierConfig(tier=ToolTier.CORE, task_types=[], min_score=0.0),
    "write_file": TierConfig(tier=ToolTier.CORE, task_types=[], min_score=0.0),
    "shell": TierConfig(tier=ToolTier.CORE, task_types=[], min_score=0.0),
    "grep_search": TierConfig(tier=ToolTier.CORE, task_types=[], min_score=0.0),
    # EXTENDED - task-dependent
    "list_directory": TierConfig(tier=ToolTier.EXTENDED, task_types=["code-editing", "exploration"], min_score=0.0),
    "tree_view": TierConfig(tier=ToolTier.EXTENDED, task_types=["exploration"], min_score=0.0),
    "multi_replace_in_file": TierConfig(tier=ToolTier.EXTENDED, task_types=["code-editing"], min_score=0.0),
    "apply_patch": TierConfig(tier=ToolTier.EXTENDED, task_types=["code-editing"], min_score=0.0),
    # SPECIALIST - role-specific
    "web_search": TierConfig(tier=ToolTier.SPECIALIST, task_types=["web-research"], min_score=0.3),
    "fetch_as_markdown": TierConfig(tier=ToolTier.SPECIALIST, task_types=["web-research"], min_score=0.3),
    "get_weather": TierConfig(tier=ToolTier.SPECIALIST, task_types=["general"], min_score=0.0),
    "read_files_in_directory": TierConfig(tier=ToolTier.SPECIALIST, task_types=["exploration"], min_score=0.2),
}


def create_tiered_registry(
    base_registry: dict[str, Callable],
    tier_assignments: dict[str, TierConfig] | None = None,
) -> dict[str, tuple[Callable, TierConfig]]:
    """Create tiered registry with tool + tier metadata."""
    assignments = tier_assignments or DEFAULT_TIER_ASSIGNMENTS
    return {
        name: (tool, assignments.get(name, TierConfig(tier=ToolTier.EXTENDED, task_types=[])))
        for name, tool in base_registry.items()
    }


class ToolTierEngine:
    """Engine for context-dependent tool selection based on tier."""

    def __init__(
        self,
        tiered_registry: dict[str, tuple[Callable, TierConfig]],
    ):
        self._registry = tiered_registry
        self._tool_to_tier: dict[Callable, ToolTier] = {}
        for name, (tool, config) in tiered_registry.items():
            self._tool_to_tier[tool] = config.tier

    def get_tools_for_context(
        self,
        task_type: str | None = None,
        min_score: float = 0.0,
        max_tools: int | None = None,
    ) -> list[Callable]:
        """Get tools matching context criteria.
        
        Args:
            task_type: Filter by task type (e.g., "code-editing", "web-research")
            min_score: Minimum evaluator score to unlock specialist tools
            max_tools: Cap total tools to reduce exposure (per TOOL-01: 50% reduction)
        """
        eligible = []
        for name, (tool, config) in self._registry.items():
            # Check tier
            if config.tier == ToolTier.CORE:
                eligible.append(tool)
            elif config.tier == ToolTier.EXTENDED:
                if task_type is None or task_type in config.task_types or not config.task_types:
                    eligible.append(tool)
            elif config.tier == ToolTier.SPECIALIST:
                if task_type in config.task_types and config.min_score <= min_score:
                    eligible.append(tool)
        
        # Apply max_tools cap (50% reduction target)
        if max_tools is not None and len(eligible) > max_tools:
            eligible = self._prioritize_tools(eligible, max_tools)
        
        return eligible

    def get_core_tools(self) -> list[Callable]:
        """Get only core tier tools (always available)."""
        return [tool for name, (tool, config) in self._registry.items() if config.tier == ToolTier.CORE]

    def _prioritize_tools(self, tools: list[Callable], max_count: int) -> list[Callable]:
        """Select tools prioritizing core > extended > specialist."""
        by_tier = {ToolTier.CORE: [], ToolTier.EXTENDED: [], ToolTier.SPECIALIST: []}
        for tool in tools:
            tier = self._tool_to_tier.get(tool)
            if tier is not None:
                by_tier[tier].append(tool)
        
        result = []
        for tier in [ToolTier.CORE, ToolTier.EXTENDED, ToolTier.SPECIALIST]:
            for tool in by_tier[tier]:
                if len(result) < max_count:
                    result.append(tool)
        return result

    def get_tier_for_tool(self, tool_name: str) -> ToolTier | None:
        """Get the tier of a specific tool."""
        if tool_name in self._registry:
            return self._registry[tool_name][1].tier
        return None


__all__ = [
    "ToolTier",
    "TierConfig",
    "ToolTierEngine",
    "create_tiered_registry",
    "DEFAULT_TIER_ASSIGNMENTS",
]