"""Harness-specific metrics for tracking iteration, evaluation, and tool usage.

Implements Prometheus metrics for the LuminaMind harness:
- Iteration count and status tracking
- Evaluator score histograms per domain
- Convergence status gauges
- Tool efficiency histograms
- Agent call counters
- Sprint duration tracking
"""
from __future__ import annotations

import threading
from typing import Optional

from prometheus_client import Counter, Gauge, Histogram

# Iteration metrics
ITERATION_COUNT = Counter(
    "luminamind_iteration_total",
    "Total refinement iterations",
    ["task_id", "status"],  # status: converged|max_iter|failed
)

EVALUATOR_SCORE = Histogram(
    "luminamind_evaluator_score",
    "Evaluator score per iteration",
    ["task_id", "domain"],  # domain: design|code|craft|originality
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
)

CONVERGENCE_STATUS = Gauge(
    "luminamind_convergence_status",
    "Current convergence state",
    ["task_id"],  # 0=iterating, 1=converged, 2=failed
)

# Tool efficiency metrics
TOOL_EFFICIENCY = Histogram(
    "luminamind_tool_efficiency",
    "Tool usage efficiency per task",
    ["task_id", "tool_name"],
    buckets=[1, 5, 10, 20, 50, 100],
)

# Agent-level metrics
AGENT_CALLS = Counter(
    "luminamind_agent_calls_total",
    "Agent invocations by role",
    ["role", "status"],  # role: planner|executor|evaluator, status: success|error
)

SPRINT_DURATION = Histogram(
    "luminamind_sprint_duration_seconds",
    "Sprint contract negotiation duration",
    ["task_id"],
    buckets=[60, 120, 300, 600, 1800, 3600],
)


class HarnessMetrics:
    """Singleton metrics class for harness-level instrumentation.

    Provides thread-safe recording of:
    - Iteration metrics (count, scores, convergence)
    - Tool efficiency tracking
    - Agent call counts
    - Sprint duration

    All metrics share the same prometheus_client registry.
    """

    _instance: Optional["HarnessMetrics"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "HarnessMetrics":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def record_iteration(
        self,
        task_id: str,
        score_breakdown: dict[str, float],
        status: str = "iterating",
    ) -> None:
        """Record iteration metrics.

        Args:
            task_id: Unique task identifier
            score_breakdown: Dict of domain scores (design, code, craft, originality)
            status: Iteration status (converged|max_iter|failed|iterating)
        """
        ITERATION_COUNT.labels(task_id=task_id, status=status).inc()
        for domain, score in score_breakdown.items():
            EVALUATOR_SCORE.labels(task_id=task_id, domain=domain).observe(score)

    def record_tool_usage(
        self,
        task_id: str,
        tool_name: str,
        call_count: int,
        duration: float,
    ) -> None:
        """Record tool usage efficiency.

        Args:
            task_id: Unique task identifier
            tool_name: Name of the tool used
            call_count: Number of calls to the tool
            duration: Total duration in seconds
        """
        for _ in range(min(call_count, 100)):  # Cap at 100 to avoid histogram explosion
            TOOL_EFFICIENCY.labels(task_id=task_id, tool_name=tool_name).observe(duration)

    def record_agent_call(self, role: str, success: bool) -> None:
        """Record agent call invocation.

        Args:
            role: Agent role (planner|executor|evaluator)
            success: Whether the call succeeded
        """
        status = "success" if success else "error"
        AGENT_CALLS.labels(role=role, status=status).inc()

    def record_sprint_duration(self, task_id: str, duration_seconds: float) -> None:
        """Record sprint contract negotiation duration.

        Args:
            task_id: Unique task identifier
            duration_seconds: Duration in seconds
        """
        SPRINT_DURATION.labels(task_id=task_id).observe(duration_seconds)

    def set_convergence(self, task_id: str, status: str) -> None:
        """Set convergence status gauge.

        Args:
            task_id: Unique task identifier
            status: Convergence status (iterating|converged|failed)
        """
        status_map = {"iterating": 0, "converged": 1, "failed": 2}
        value = status_map.get(status, 0)
        CONVERGENCE_STATUS.labels(task_id=task_id).set(value)


__all__ = [
    "HarnessMetrics",
    "ITERATION_COUNT",
    "EVALUATOR_SCORE",
    "CONVERGENCE_STATUS",
    "TOOL_EFFICIENCY",
    "AGENT_CALLS",
    "SPRINT_DURATION",
]