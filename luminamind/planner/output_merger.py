"""OutputMerger for merging subagent outputs with conflict resolution.

Per MULTI-02: OutputMerger merges subagent outputs with conflict resolution.
"""
from dataclasses import dataclass, field
from typing import Any

from luminamind.planner.agent_message_bus import AgentMessage


@dataclass
class MergeConflict:
    """Represents a conflict between subagent outputs for a field.

    Attributes:
        field_path: Field identifier (e.g., "spec.title")
        conflicting_values: List of different values from subagents
        resolution: How the conflict was resolved
        auto_resolved: Whether resolution was automatic or requires human input
    """
    field_path: str
    conflicting_values: list[Any]
    resolution: str = ""
    auto_resolved: bool = False


@dataclass
class MergeResult:
    """Result of merging multiple subagent outputs.

    Attributes:
        unified_output: Merged output dict
        conflicts: List of MergeConflict objects
        partial: True if some fields couldn't be auto-merged
    """
    unified_output: dict
    conflicts: list[MergeConflict] = field(default_factory=list)
    partial: bool = False

    @property
    def has_conflicts(self) -> bool:
        """Returns True if there are any unresolved conflicts."""
        return len(self.conflicts) > 0


class OutputMerger:
    """Merges outputs from multiple subagents with conflict resolution.

    Per MULTI-02: OutputMerger detects conflicts and auto-resolves when possible.

    Conflict strategies:
    - priority_wins: Use value from most recently updated field (default)
    - first_wins: Use value from first subagent
    - longest: Use longest value (for strings/lists)
    """

    def __init__(self, conflict_strategy: str = "priority_wins"):
        """Initialize OutputMerger.

        Args:
            conflict_strategy: Strategy for resolving conflicts
                (priority_wins, first_wins, longest)
        """
        self.conflict_strategy = conflict_strategy

    def merge(self, subagent_results: list[dict]) -> MergeResult:
        """Merge outputs from multiple subagents.

        Args:
            subagent_results: List of output dicts from subagents

        Returns:
            MergeResult with unified output and any conflicts
        """
        if not subagent_results:
            return MergeResult(unified_output={})

        if len(subagent_results) == 1:
            return MergeResult(unified_output=subagent_results[0])

        conflicts = []
        unified = {}

        # Collect all keys from all results
        all_keys = set()
        for result in subagent_results:
            all_keys.update(result.keys())

        for key in all_keys:
            values = [r.get(key) for r in subagent_results if key in r]
            # Filter out None values
            values = [v for v in values if v is not None]

            if len(values) == 1:
                # Single value - no conflict
                unified[key] = values[0]
            else:
                # Multiple values - check for conflict
                if self._is_conflicting(values):
                    conflict = MergeConflict(
                        field_path=key,
                        conflicting_values=values,
                        auto_resolved=False
                    )
                    conflicts.append(conflict)
                    # Auto-resolve based on strategy
                    resolved = self._auto_resolve(key, values)
                    unified[key] = resolved
                    conflict.resolution = f"Auto-resolved via {self.conflict_strategy}"
                    conflict.auto_resolved = True
                else:
                    # Same value or all equal - use first
                    unified[key] = values[0]

        return MergeResult(
            unified_output=unified,
            conflicts=conflicts,
            partial=any(not c.auto_resolved for c in conflicts)
        )

    def _is_conflicting(self, values: list[Any]) -> bool:
        """Check if values are truly conflicting (not just different representations).

        Args:
            values: List of values to check

        Returns:
            True if values are in conflict and require resolution
        """
        if len(set(type(v).__name__ for v in values)) > 1:
            return True  # Different types
        if all(v == values[0] for v in values):
            return False  # All same
        # Check if values are containers with same content
        if isinstance(values[0], (list, dict, set)):
            return False  # Mergeable
        return True  # Scalar conflicting values

    def _auto_resolve(self, key: str, values: list[Any]) -> Any:
        """Auto-resolve conflict based on configured strategy.

        Args:
            key: Field key being resolved
            values: Conflicting values

        Returns:
            Resolved value
        """
        if self.conflict_strategy == "priority_wins":
            # Use value from most recently updated field
            return values[-1]
        elif self.conflict_strategy == "first_wins":
            return values[0]
        elif self.conflict_strategy == "longest":
            if all(isinstance(v, (str, list)) for v in values):
                return max(values, key=len)
        return values[-1]
