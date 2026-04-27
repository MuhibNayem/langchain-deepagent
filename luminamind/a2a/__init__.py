"""A2A (Agent-to-Agent) protocol support for LuminaMind."""
from luminamind.a2a.client import A2AClient, A2AError
from luminamind.a2a.discovery import AgentDiscovery
from luminamind.a2a.server import A2AServer, create_a2a_server
from luminamind.a2a.types import (
    AgentCard,
    AgentSkill,
    Artifact,
    DataPart,
    FilePart,
    Message,
    Part,
    Task,
    TaskState,
    TextPart,
    part_from_dict,
    part_to_dict,
)

__all__ = [
    "AgentCard",
    "AgentSkill",
    "Artifact",
    "DataPart",
    "FilePart",
    "Message",
    "Part",
    "Task",
    "TaskState",
    "TextPart",
    "part_from_dict",
    "part_to_dict",
    "A2AClient",
    "A2AError",
    "A2AServer",
    "create_a2a_server",
    "AgentDiscovery",
]
