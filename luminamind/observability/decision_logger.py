"""DecisionLogger for annotating key decisions during harness execution.

Records DecisionPoints and TraceEntries to Redis for later replay and analysis.
Key format: trace:{task_id}
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Optional

try:
    from redis import Redis
    from redis.exceptions import RedisError
except ImportError:  # pragma: no cover
    Redis = None  # type: ignore[assignment]
    RedisError = Exception  # type: ignore[misc,assignment]

from luminamind.config.checkpointer import create_checkpointer, MemorySaver

TRACE_KEY_PREFIX = "trace"


@dataclass
class DecisionPoint:
    """A key decision made during harness execution.

    Attributes:
        decision_id: Unique identifier for this decision
        timestamp: When the decision was made
        phase: Execution phase (e.g., "iteration", "evaluation", "sprint")
        decision_type: Type of decision (e.g., "quality_gate", "convergence", "tool_selection")
        context: Inputs to the decision
        choice: What was chosen
        alternatives: What else was considered
        rationale: Why this was chosen
        outcome: Result of the decision (filled later)
    """

    decision_id: str
    timestamp: datetime
    phase: str
    decision_type: str
    context: dict[str, Any]
    choice: str
    alternatives: list[str]
    rationale: str
    outcome: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dict for serialization."""
        d = asdict(self)
        d["timestamp"] = self.timestamp.isoformat()
        return d

    @classmethod
    def from_dict(cls, d: dict) -> DecisionPoint:
        """Create from dict."""
        d = d.copy()
        d["timestamp"] = datetime.fromisoformat(d["timestamp"])
        return cls(**d)


@dataclass
class TraceEntry:
    """A single step in the harness execution trace.

    Attributes:
        entry_id: Unique identifier for this entry
        timestamp: When the entry was recorded
        step_number: Sequential step number
        component: Which component (planner, evaluator, executor, etc.)
        action: What action was taken
        inputs: Input data
        outputs: Output data
        decisions: List of DecisionPoints from this step
        metadata: Additional metadata
    """

    entry_id: str
    timestamp: datetime
    step_number: int
    component: str
    action: str
    inputs: dict[str, Any]
    outputs: dict[str, Any]
    decisions: list[DecisionPoint] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dict for serialization."""
        d = asdict(self)
        d["timestamp"] = self.timestamp.isoformat()
        d["decisions"] = [dp.to_dict() for dp in self.decisions]
        return d

    @classmethod
    def from_dict(cls, d: dict) -> TraceEntry:
        """Create from dict."""
        d = d.copy()
        d["timestamp"] = datetime.fromisoformat(d["timestamp"])
        d["decisions"] = [DecisionPoint.from_dict(dp) for dp in d["decisions"]]
        return cls(**d)


class DecisionLogger:
    """Logger for decisions and trace entries.

    Stores traces in Redis using key format: trace:{task_id}
    Falls back to in-memory storage if Redis is unavailable.
    """

    def __init__(self, redis_client: Redis | None = None) -> None:
        """Initialize DecisionLogger.

        Args:
            redis_client: Optional Redis client. If None, uses checkpointer's Redis
                         connection or falls back to in-memory storage.
        """
        self._redis = redis_client
        self._memory: dict[str, list[dict]] = {}

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

    def _get_trace_key(self, task_id: str) -> str:
        """Get Redis key for a task's trace."""
        return f"{TRACE_KEY_PREFIX}:{task_id}"

    def log_decision(self, point: DecisionPoint) -> str:
        """Record a decision point.

        Args:
            point: The DecisionPoint to record

        Returns:
            The decision_id of the recorded decision
        """
        if not point.decision_id:
            point.decision_id = str(uuid.uuid4())

        data = point.to_dict()

        # Store in Redis if available
        if self.redis:
            try:
                key = f"decision:{point.decision_id}"
                self.redis.set(key, json.dumps(data))
            except RedisError:
                pass

        return point.decision_id

    def log_trace_entry(self, entry: TraceEntry, task_id: str) -> str:
        """Record a trace entry for a task.

        Args:
            entry: The TraceEntry to record
            task_id: The task this entry belongs to

        Returns:
            The entry_id of the recorded entry
        """
        if not entry.entry_id:
            entry.entry_id = str(uuid.uuid4())

        data = entry.to_dict()

        if self.redis:
            try:
                key = self._get_trace_key(task_id)
                # Get existing entries
                existing = self.redis.get(key)
                if existing:
                    entries = json.loads(existing)
                else:
                    entries = []
                entries.append(data)
                self.redis.set(key, json.dumps(entries))
            except RedisError:
                # Fall back to memory
                if task_id not in self._memory:
                    self._memory[task_id] = []
                self._memory[task_id].append(data)
        else:
            # Memory fallback
            if task_id not in self._memory:
                self._memory[task_id] = []
            self._memory[task_id].append(data)

        return entry.entry_id

    def get_trace_for_task(self, task_id: str) -> list[TraceEntry]:
        """Retrieve full trace for a task.

        Args:
            task_id: The task to get trace for

        Returns:
            List of TraceEntry objects, ordered by step_number
        """
        entries: list[TraceEntry] = []

        if self.redis:
            try:
                key = self._get_trace_key(task_id)
                data = self.redis.get(key)
                if data:
                    entries = [TraceEntry.from_dict(e) for e in json.loads(data)]
            except RedisError:
                pass

        if not entries and task_id in self._memory:
            entries = [TraceEntry.from_dict(e) for e in self._memory[task_id]]

        return sorted(entries, key=lambda e: e.step_number)

    def annotate_decision_outcome(self, decision_id: str, outcome: str) -> bool:
        """Fill in the outcome for a decision.

        Args:
            decision_id: The decision to update
            outcome: The outcome description

        Returns:
            True if updated successfully, False otherwise
        """
        if self.redis:
            try:
                key = f"decision:{decision_id}"
                data = self.redis.get(key)
                if data:
                    point_dict = json.loads(data)
                    point_dict["outcome"] = outcome
                    self.redis.set(key, json.dumps(point_dict))
                    return True
            except RedisError:
                pass
        return False

    def get_decision(self, decision_id: str) -> DecisionPoint | None:
        """Retrieve a decision by ID.

        Args:
            decision_id: The decision to retrieve

        Returns:
            DecisionPoint if found, None otherwise
        """
        if self.redis:
            try:
                key = f"decision:{decision_id}"
                data = self.redis.get(key)
                if data:
                    return DecisionPoint.from_dict(json.loads(data))
            except RedisError:
                pass
        return None

    def clear_trace(self, task_id: str) -> bool:
        """Clear all trace entries for a task.

        Args:
            task_id: The task whose trace to clear

        Returns:
            True if cleared successfully
        """
        if self.redis:
            try:
                key = self._get_trace_key(task_id)
                self.redis.delete(key)
            except RedisError:
                pass

        if task_id in self._memory:
            del self._memory[task_id]

        return True


__all__ = ["DecisionLogger", "DecisionPoint", "TraceEntry"]
