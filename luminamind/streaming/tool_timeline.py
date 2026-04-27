from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from enum import Enum


class ToolStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class ToolCallNode:
    """A tool call in the execution timeline."""
    node_id: str
    tool_name: str
    tool_input: dict  # Sanitized input (no secrets)
    tool_output: str | None  # Truncated output
    status: ToolStatus
    started_at: datetime
    completed_at: datetime | None = None
    duration_ms: float | None = None
    parent_node_id: str | None = None  # For nested calls
    children: list[str] = field(default_factory=list)
    error: str | None = None
    retry_count: int = 0


@dataclass
class ToolTimeline:
    """Timeline of all tool calls during execution."""
    timeline_id: str
    agent_id: str
    session_id: str
    task_id: str
    started_at: datetime
    nodes: list[ToolCallNode] = field(default_factory=list)
    total_duration_ms: float = 0

    def add_node(self, node: ToolCallNode) -> None:
        """Add a tool call node."""
        self.nodes.append(node)
        if node.parent_node_id:
            parent = self.get_node(node.parent_node_id)
            if parent:
                parent.children.append(node.node_id)

    def get_node(self, node_id: str) -> ToolCallNode | None:
        """Get node by ID."""
        for node in self.nodes:
            if node.node_id == node_id:
                return node
        return None

    def get_execution_order(self) -> list[ToolCallNode]:
        """Get nodes in execution order (topological)."""
        # Build adjacency list
        children_map: dict[str, list[str]] = {}
        in_degree: dict[str, int] = {}

        for node in self.nodes:
            in_degree[node.node_id] = 0
            children_map[node.node_id] = node.children

        for node in self.nodes:
            for child_id in node.children:
                in_degree[child_id] = in_degree.get(child_id, 0) + 1

        # Kahn's algorithm
        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        result = []

        while queue:
            node_id = queue.pop(0)
            result.append(self.get_node(node_id))
            for child_id in children_map.get(node_id, []):
                in_degree[child_id] -= 1
                if in_degree[child_id] == 0:
                    queue.append(child_id)

        return result

    def to_timeline_format(self) -> dict:
        """Convert to Gantt-chart friendly format."""
        return {
            'timeline_id': self.timeline_id,
            'agent_id': self.agent_id,
            'session_id': self.session_id,
            'task_id': self.task_id,
            'started_at': self.started_at.isoformat(),
            'nodes': [
                {
                    'id': n.node_id,
                    'name': n.tool_name,
                    'start': n.started_at.isoformat(),
                    'end': n.completed_at.isoformat() if n.completed_at else None,
                    'duration_ms': n.duration_ms,
                    'status': n.status.value,
                    'parent': n.parent_node_id,
                    'children': n.children,
                    'error': n.error,
                    'retry_count': n.retry_count
                }
                for n in self.nodes
            ],
            'stats': {
                'total_duration_ms': self.total_duration_ms,
                'tool_count': len(self.nodes),
                'failed_count': len([n for n in self.nodes if n.status == ToolStatus.FAILED])
            }
        }


class ToolTimelineCollector:
    """Collects tool timeline from agent execution."""

    def __init__(self, event_stream=None):
        self.event_stream = event_stream

    async def start_timeline(self, timeline_id: str, agent_id: str,
                           session_id: str, task_id: str) -> ToolTimeline:
        """Start a new timeline."""
        timeline = ToolTimeline(
            timeline_id=timeline_id,
            agent_id=agent_id,
            session_id=session_id,
            task_id=task_id,
            started_at=datetime.utcnow()
        )
        return timeline

    async def record_tool_start(self, timeline: ToolTimeline, tool_name: str,
                               tool_input: dict, parent_node_id: str | None = None) -> ToolCallNode:
        """Record tool start."""
        node = ToolCallNode(
            node_id=f"{timeline.timeline_id}-{tool_name}-{len(timeline.nodes)}",
            tool_name=tool_name,
            tool_input=self._sanitize_input(tool_input),
            tool_output=None,
            status=ToolStatus.RUNNING,
            started_at=datetime.utcnow(),
            parent_node_id=parent_node_id
        )
        timeline.add_node(node)
        return node

    async def record_tool_end(self, timeline: ToolTimeline, node_id: str,
                             tool_output: str, error: str | None = None) -> None:
        """Record tool completion."""
        node = timeline.get_node(node_id)
        if node:
            node.completed_at = datetime.utcnow()
            node.duration_ms = (node.completed_at - node.started_at).total_seconds() * 1000
            node.tool_output = self._truncate_output(tool_output)
            node.status = ToolStatus.FAILED if error else ToolStatus.COMPLETED
            node.error = error

    def _sanitize_input(self, tool_input: dict) -> dict:
        """Remove sensitive data from tool input."""
        sensitive_keys = {'password', 'secret', 'api_key', 'token', 'credential', 'auth'}
        return {
            k: '***REDACTED***' if any(s in k.lower() for s in sensitive_keys) else v
            for k, v in tool_input.items()
        }

    def _truncate_output(self, output: str, max_len: int = 10000) -> str:
        """Truncate output to max length."""
        if len(output) <= max_len:
            return output
        return output[:max_len] + f"\n... (truncated, {len(output) - max_len} bytes omitted)"