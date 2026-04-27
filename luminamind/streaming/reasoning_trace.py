from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from enum import Enum


class ReasoningStepType(Enum):
    THINK = "think"      # Internal reasoning
    ACT = "act"          # Action taken
    OBSERVE = "observe"  # Observation/result
    DECIDE = "decide"    # Decision point


@dataclass
class ThinkActObserve:
    """A single think→act→observe reasoning step."""
    step_id: str
    step_type: ReasoningStepType
    content: str
    timestamp: datetime
    duration_ms: float | None = None
    parent_step_id: str | None = None  # For nested reasoning
    children: list[str] = field(default_factory=list)  # Child step IDs
    metadata: dict = field(default_factory=dict)


@dataclass
class ReasoningTrace:
    """Complete reasoning trace for an agent task."""
    trace_id: str
    agent_id: str
    session_id: str
    task_id: str
    started_at: datetime
    completed_at: datetime | None = None
    steps: list[ThinkActObserve] = field(default_factory=list)
    total_think_time_ms: float = 0
    total_act_time_ms: float = 0
    total_observe_time_ms: float = 0
    depth: int = 0  # Max nesting depth

    def add_step(self, step: ThinkActObserve) -> None:
        """Add a step to the trace."""
        self.steps.append(step)
        if step.parent_step_id:
            parent = self.get_step(step.parent_step_id)
            if parent:
                parent.children.append(step.step_id)

        # Update depth
        if step.parent_step_id is None:
            step_depth = 0
        else:
            parent = self.get_step(step.parent_step_id)
            step_depth = self._get_step_depth(parent) + 1 if parent else 0
        self.depth = max(self.depth, step_depth)

        # Update timing totals
        if step.duration_ms is not None:
            if step.step_type == ReasoningStepType.THINK:
                self.total_think_time_ms += step.duration_ms
            elif step.step_type == ReasoningStepType.ACT:
                self.total_act_time_ms += step.duration_ms
            elif step.step_type == ReasoningStepType.OBSERVE:
                self.total_observe_time_ms += step.duration_ms

    def _get_step_depth(self, step: ThinkActObserve) -> int:
        """Get depth of a step."""
        depth = 0
        current = step
        while current and current.parent_step_id:
            depth += 1
            current = self.get_step(current.parent_step_id)
        return depth

    def get_step(self, step_id: str) -> ThinkActObserve | None:
        """Get step by ID."""
        for step in self.steps:
            if step.step_id == step_id:
                return step
        return None

    def get_path(self) -> list[ThinkActObserve]:
        """Get the primary reasoning path (first child of each level)."""
        path = []
        if not self.steps:
            return path

        current = self.steps[0]
        while current:
            path.append(current)
            children = [self.get_step(cid) for cid in current.children]
            current = children[0] if children else None

        return path

    def to_visualization(self) -> dict:
        """Convert to visualization-friendly format."""
        return {
            'trace_id': self.trace_id,
            'agent_id': self.agent_id,
            'session_id': self.session_id,
            'task_id': self.task_id,
            'started_at': self.started_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'steps': [
                {
                    'id': s.step_id,
                    'type': s.step_type.value,
                    'content': s.content,
                    'timestamp': s.timestamp.isoformat(),
                    'duration_ms': s.duration_ms,
                    'parent': s.parent_step_id,
                    'children': s.children,
                    'metadata': s.metadata
                }
                for s in self.steps
            ],
            'stats': {
                'total_think_time_ms': self.total_think_time_ms,
                'total_act_time_ms': self.total_act_time_ms,
                'total_observe_time_ms': self.total_observe_time_ms,
                'depth': self.depth
            }
        }


class ReasoningTraceCollector:
    """Collects reasoning trace from agent execution."""

    def __init__(self, event_stream=None):
        self.event_stream = event_stream
        self._active_traces: dict[str, ReasoningTrace] = {}

    async def start_trace(self, trace_id: str, agent_id: str,
                         session_id: str, task_id: str) -> ReasoningTrace:
        """Start a new reasoning trace."""
        trace = ReasoningTrace(
            trace_id=trace_id,
            agent_id=agent_id,
            session_id=session_id,
            task_id=task_id,
            started_at=datetime.utcnow()
        )
        self._active_traces[trace_id] = trace
        return trace

    async def add_think(self, trace_id: str, content: str,
                       parent_step_id: str | None = None) -> ThinkActObserve:
        """Add a think step."""
        trace = self._active_traces.get(trace_id)
        if not trace:
            raise ValueError(f"No active trace with ID: {trace_id}")

        step = ThinkActObserve(
            step_id=f"{trace_id}-think-{len(trace.steps)}",
            step_type=ReasoningStepType.THINK,
            content=content,
            timestamp=datetime.utcnow(),
            parent_step_id=parent_step_id
        )
        trace.add_step(step)
        return step

    async def add_act(self, trace_id: str, content: str,
                     parent_step_id: str | None = None) -> ThinkActObserve:
        """Add an act step."""
        trace = self._active_traces.get(trace_id)
        if not trace:
            raise ValueError(f"No active trace with ID: {trace_id}")

        step = ThinkActObserve(
            step_id=f"{trace_id}-act-{len(trace.steps)}",
            step_type=ReasoningStepType.ACT,
            content=content,
            timestamp=datetime.utcnow(),
            parent_step_id=parent_step_id
        )
        trace.add_step(step)
        return step

    async def add_observe(self, trace_id: str, content: str,
                         parent_step_id: str | None = None) -> ThinkActObserve:
        """Add an observe step."""
        trace = self._active_traces.get(trace_id)
        if not trace:
            raise ValueError(f"No active trace with ID: {trace_id}")

        step = ThinkActObserve(
            step_id=f"{trace_id}-observe-{len(trace.steps)}",
            step_type=ReasoningStepType.OBSERVE,
            content=content,
            timestamp=datetime.utcnow(),
            parent_step_id=parent_step_id
        )
        trace.add_step(step)
        return step

    async def end_trace(self, trace_id: str) -> ReasoningTrace:
        """End and return the trace."""
        trace = self._active_traces.pop(trace_id)
        trace.completed_at = datetime.utcnow()
        return trace