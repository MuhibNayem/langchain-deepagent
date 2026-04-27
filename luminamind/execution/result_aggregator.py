from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
import hashlib
import json

from luminamind.execution.task_pool import TaskResult


@dataclass
class AggregationConflict:
    """Represents a conflict between parallel results."""
    key: str  # The conflicting key
    values: list[Any]  # The different values
    resolution: Any  # How it was resolved

@dataclass
class AggregatedResult:
    """Result of aggregating multiple task results."""
    merged: dict[str, Any]
    conflicts: list[AggregationConflict]
    source_count: int  # How many results were merged

    def has_conflicts(self) -> bool:
        return len(self.conflicts) > 0

class ResultAggregator:
    """Aggregates results from parallel task execution."""

    def __init__(self, conflict_resolution: str = "last_write_wins"):
        """Initialize aggregator.

        Args:
            conflict_resolution: Strategy for resolving conflicts
                - "last_write_wins": Most recently completed task wins
                - "first_write_wins": First completed task wins
                - "priority": Task with highest priority wins
                - "merge": Attempt to merge dict values (deep merge)
        """
        self.conflict_resolution = conflict_resolution

    def aggregate(self, results: list[TaskResult]) -> AggregatedResult:
        """Aggregate multiple task results.

        Args:
            results: List of TaskResult from parallel execution

        Returns:
            AggregatedResult with merged dict and any conflicts
        """
        merged: dict[str, Any] = {}
        all_keys: set[str] = set()
        conflicts: list[AggregationConflict] = []

        # Collect all keys
        for result in results:
            if result.success and result.result and isinstance(result.result, dict):
                all_keys.update(result.result.keys())

        # For each key, detect conflicts and resolve
        for key in all_keys:
            values = []
            for result in results:
                if result.success and result.result and isinstance(result.result, dict):
                    if key in result.result:
                        values.append(result.result[key])

            if len(values) > 1:
                # Conflict detected
                resolved = self._resolve_conflict(values, results)
                conflicts.append(AggregationConflict(
                    key=key,
                    values=values,
                    resolution=resolved
                ))
                merged[key] = resolved
            elif len(values) == 1:
                merged[key] = values[0]

        return AggregatedResult(
            merged=merged,
            conflicts=conflicts,
            source_count=len(results)
        )

    def _resolve_conflict(self, values: list[Any], results: list[TaskResult]) -> Any:
        """Resolve a conflict between values."""
        if self.conflict_resolution == "last_write_wins":
            return values[-1]
        elif self.conflict_resolution == "first_write_wins":
            return values[0]
        elif self.conflict_resolution == "priority":
            # Find result with highest priority task
            # (This would need access to task priority which we don't have in results)
            return values[-1]
        elif self.conflict_resolution == "merge" and all(isinstance(v, dict) for v in values):
            # Deep merge
            return self._deep_merge(values)
        else:
            return values[-1]

    def _deep_merge(self, dicts: list[dict]) -> dict:
        """Deep merge multiple dicts."""
        result = {}
        for d in dicts:
            for k, v in d.items():
                if k in result and isinstance(result[k], dict) and isinstance(v, dict):
                    result[k] = self._deep_merge([result[k], v])
                else:
                    result[k] = v
        return result