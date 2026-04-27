from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from collections import defaultdict, deque

@dataclass
class DependencyGraph:
    """Graph for managing task dependencies and ordering."""

    def __init__(self):
        self._nodes: dict[str, set[str]] = defaultdict(set)  # task_id -> set of dependencies
        self._reverse: dict[str, set[str]] = defaultdict(set)  # task_id -> set of dependents

    def add_node(self, task_id: str, dependencies: list[str] | None = None):
        """Add a task node to the graph.

        Args:
            task_id: Unique identifier for the task
            dependencies: List of task_ids this depends on
        """
        if dependencies is None:
            dependencies = []

        self._nodes[task_id] = set(dependencies)
        for dep in dependencies:
            self._reverse[dep].add(task_id)

    def get_execution_order(self) -> list[list[str]]:
        """Get tasks in execution order (parallelizable tasks grouped together).

        Returns list of batches, where each batch can execute in parallel
        but batches must execute in sequence.
        """
        in_degree: dict[str, int] = {}
        for node in self._nodes:
            in_degree[node] = len(self._nodes[node])

        batches: list[list[str]] = []
        remaining = set(self._nodes.keys())

        while remaining:
            # Find all nodes with no remaining dependencies
            batch = []
            for node in remaining:
                deps = self._nodes[node]
                if all(d not in remaining for d in deps):
                    batch.append(node)

            if not batch:
                # Cycle detected
                raise ValueError(f"Cycle detected in dependency graph among: {remaining}")

            batches.append(batch)
            remaining -= set(batch)

        return batches

    def get_dependencies(self, task_id: str) -> set[str]:
        """Get direct dependencies of a task."""
        return self._nodes.get(task_id, set())

    def get_dependents(self, task_id: str) -> set[str]:
        """Get direct dependents of a task."""
        return self._reverse.get(task_id, set())

    def validate(self) -> list[str]:
        """Validate the graph.

        Returns list of error messages (empty if valid).
        """
        errors = []

        # Check for cycles
        try:
            self.get_execution_order()
        except ValueError as e:
            errors.append(str(e))

        # Check for missing dependencies
        for node, deps in self._nodes.items():
            for dep in deps:
                if dep not in self._nodes:
                    errors.append(f"Task {node} depends on missing task {dep}")

        return errors