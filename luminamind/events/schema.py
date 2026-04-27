from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class AgentEventType(Enum):
    AGENT_SPAWN = "agent_spawn"
    AGENT_COMPLETE = "agent_complete"
    AGENT_ERROR = "agent_error"
    TOOL_START = "tool_start"
    TOOL_END = "tool_end"
    TOKEN_STREAM = "token_stream"
    STATE_UPDATE = "state_update"
    INTERRUPT = "interrupt"
    RESUME = "resume"
    METADATA = "metadata"


@dataclass
class AgentEvent:
    """Base event for agent activity."""
    event_id: str
    event_type: AgentEventType
    agent_id: str
    timestamp: datetime
    data: dict  # event-specific payload
    session_id: str
    task_id: str | None = None


@dataclass
class ToolEvent:
    """Tool execution event."""
    event_id: str
    agent_id: str
    timestamp: datetime
    tool_name: str
    tool_input: dict
    tool_output: dict | None
    duration_ms: float
    session_id: str
    task_id: str | None = None
    error: str | None = None


@dataclass
class TokenEvent:
    """Token streaming event."""
    event_id: str
    agent_id: str
    timestamp: datetime
    token: str
    token_type: str  # "text", "thinking", "action", "observation"
    session_id: str
    task_id: str | None = None
    is_final: bool = False


@dataclass
class ErrorEvent:
    """Error event."""
    event_id: str
    agent_id: str
    timestamp: datetime
    error_type: str
    error_message: str
    stack_trace: str | None
    session_id: str
    task_id: str | None = None
    recovered: bool = False


@dataclass
class EventSubscription:
    """Subscription filter for events."""
    session_id: str | None = None
    task_id: str | None = None
    agent_id: str | None = None
    event_types: list[AgentEventType] | None = None
    heartbeat_interval: int = 30  # seconds


class EventSchema:
    """Registry for event schema versioning."""

    SCHEMA_VERSION = "1.0"

    @classmethod
    def validate(cls, event: AgentEvent) -> bool:
        """Validate event against current schema."""
        pass

    @classmethod
    def migrate(cls, event: AgentEvent, from_version: str) -> AgentEvent:
        """Migrate event from older schema version."""
        pass