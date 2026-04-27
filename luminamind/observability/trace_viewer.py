"""TraceViewer for step-by-step harness execution replay.

View, replay, and compare execution traces stored by DecisionLogger.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

try:
    from redis import Redis
except ImportError:  # pragma: no cover
    Redis = None  # type: ignore[assignment]

from luminamind.config.checkpointer import create_checkpointer
from luminamind.observability.decision_logger import (
    DecisionLogger,
    DecisionPoint,
    TraceEntry,
    TRACE_KEY_PREFIX,
)


@dataclass
class ReplayResult:
    """Result from replaying a trace.

    Attributes:
        task_id: The task that was replayed
        decisions_reconstructed: List of decisions in execution order
        execution_path: Step-by-step description of what happened
        partial: Whether the replay was partial (missing entries)
    """

    task_id: str
    decisions_reconstructed: list[DecisionPoint]
    execution_path: list[str]
    partial: bool = False


class TraceViewer:
    """View and replay harness execution traces.

    Retrieves traces from Redis (via DecisionLogger) and provides
    replay, export, and comparison functionality.
    """

    def __init__(self, redis_client: Redis | None = None) -> None:
        """Initialize TraceViewer.

        Args:
            redis_client: Optional Redis client. If None, uses checkpointer's
                         Redis connection.
        """
        self._redis = redis_client
        self._decision_logger: DecisionLogger | None = None

    @property
    def redis(self) -> Redis | None:
        """Get Redis client, lazily initialized."""
        if self._redis is None:
            try:
                checkpointer = create_checkpointer()
                if hasattr(checkpointer, "redis"):
                    self._redis = checkpointer.redis
            except Exception:
                pass
        return self._redis

    @property
    def decision_logger(self) -> DecisionLogger:
        """Get DecisionLogger instance."""
        if self._decision_logger is None:
            self._decision_logger = DecisionLogger(redis_client=self._redis)
        return self._decision_logger

    def get_trace(self, task_id: str) -> list[TraceEntry]:
        """Retrieve full trace for a task.

        Args:
            task_id: The task to get trace for

        Returns:
            List of TraceEntry objects ordered by step_number
        """
        return self.decision_logger.get_trace_for_task(task_id)

    def replay_trace(self, task_id: str) -> ReplayResult:
        """Reconstruct execution path from checkpoints.

        Args:
            task_id: The task to replay

        Returns:
            ReplayResult with decisions_reconstructed and execution_path
        """
        entries = self.get_trace(task_id)

        if not entries:
            return ReplayResult(
                task_id=task_id,
                decisions_reconstructed=[],
                execution_path=[],
                partial=True,
            )

        decisions: list[DecisionPoint] = []
        path: list[str] = []

        for entry in entries:
            path.append(f"[Step {entry.step_number}] {entry.component}: {entry.action}")

            # Collect decisions from this entry
            for decision in entry.decisions:
                decisions.append(decision)
                path.append(
                    f"  Decision {decision.decision_type}: {decision.choice} "
                    f"(reason: {decision.rationale})"
                )

            # Add input/output summary
            if entry.inputs:
                path.append(f"  Inputs: {self._summarize_dict(entry.inputs)}")
            if entry.outputs:
                path.append(f"  Outputs: {self._summarize_dict(entry.outputs)}")

        return ReplayResult(
            task_id=task_id,
            decisions_reconstructed=decisions,
            execution_path=path,
            partial=False,
        )

    def export_trace(self, task_id: str, format: str = "json") -> str:
        """Export trace as JSON or human-readable text.

        Args:
            task_id: The task to export
            format: "json" for JSON, "text" for human-readable

        Returns:
            Exported trace as string
        """
        entries = self.get_trace(task_id)

        if format == "json":
            data = [entry.to_dict() for entry in entries]
            return json.dumps(data, indent=2)

        # Human-readable text format
        lines: list[str] = [f"Trace for task: {task_id}", "=" * 50]

        for entry in entries:
            lines.append(f"\n[Step {entry.step_number}] {entry.component}: {entry.action}")
            lines.append(f"  Timestamp: {entry.timestamp.isoformat()}")

            if entry.inputs:
                lines.append(f"  Inputs: {self._summarize_dict(entry.inputs)}")
            if entry.outputs:
                lines.append(f"  Outputs: {self._summarize_dict(entry.outputs)}")

            if entry.decisions:
                lines.append("  Decisions:")
                for decision in entry.decisions:
                    lines.append(
                        f"    - {decision.decision_type}: {decision.choice}"
                    )
                    lines.append(f"      Rationale: {decision.rationale}")
                    if decision.outcome:
                        lines.append(f"      Outcome: {decision.outcome}")

            if entry.metadata:
                lines.append(f"  Metadata: {self._summarize_dict(entry.metadata)}")

        return "\n".join(lines)

    def compare_traces(self, task_id_a: str, task_id_b: str) -> list[str]:
        """Compare two traces, highlighting differences in decisions.

        Args:
            task_id_a: First task to compare
            task_id_b: Second task to compare

        Returns:
            List of difference descriptions
        """
        entries_a = self.get_trace(task_id_a)
        entries_b = self.get_trace(task_id_b)

        differences: list[str] = []

        # Compare step counts
        if len(entries_a) != len(entries_b):
            differences.append(
                f"Step count differs: {len(entries_a)} vs {len(entries_b)}"
            )

        # Build decision maps
        decisions_a = {
            f"{dp.phase}:{dp.decision_type}:{dp.choice}"
            for entry in entries_a
            for dp in entry.decisions
        }
        decisions_b = {
            f"{dp.phase}:{dp.decision_type}:{dp.choice}"
            for entry in entries_b
            for dp in entry.decisions
        }

        # Find decisions only in A
        only_a = decisions_a - decisions_b
        if only_a:
            differences.append(
                f"Decisions only in {task_id_a}: {', '.join(sorted(only_a))}"
            )

        # Find decisions only in B
        only_b = decisions_b - decisions_a
        if only_b:
            differences.append(
                f"Decisions only in {task_id_b}: {', '.join(sorted(only_b))}"
            )

        # Compare component sequences
        components_a = [e.component for e in entries_a]
        components_b = [e.component for e in entries_b]
        if components_a != components_b:
            differences.append(
                f"Component sequence differs:\n"
                f"  {task_id_a}: {' -> '.join(components_a)}\n"
                f"  {task_id_b}: {' -> '.join(components_b)}"
            )

        if not differences:
            differences.append("Traces are identical")

        return differences

    def _summarize_dict(self, d: dict[str, Any], max_len: int = 100) -> str:
        """Summarize a dict for display, truncating if needed."""
        s = json.dumps(d)
        if len(s) > max_len:
            return s[:max_len] + "..."
        return s


__all__ = ["TraceViewer", "ReplayResult"]
