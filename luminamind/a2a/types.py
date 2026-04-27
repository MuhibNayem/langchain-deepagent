"""Core A2A (Agent-to-Agent) protocol types.

Implements Google A2A protocol v0.2 concepts:
- AgentCard: capability advertisement
- Task: unit of work
- Message: communication payload
- Part: content fragment (text, file, data)
- Artifact: task output
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TaskState(str, Enum):
    SUBMITTED = "submitted"
    WORKING = "working"
    INPUT_REQUIRED = "input-required"
    COMPLETED = "completed"
    CANCELED = "canceled"
    FAILED = "failed"


@dataclass
class AgentSkill:
    """A skill exposed by an agent."""

    id: str
    name: str
    description: str
    tags: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "tags": self.tags,
            "examples": self.examples,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentSkill":
        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            tags=data.get("tags", []),
            examples=data.get("examples", []),
        )


@dataclass
class AgentCard:
    """Capability advertisement for an A2A agent."""

    name: str
    description: str
    url: str
    version: str = "0.1.0"
    capabilities: dict[str, bool] = field(default_factory=dict)
    skills: list[AgentSkill] = field(default_factory=list)
    default_input_modes: list[str] = field(default_factory=lambda: ["text"])
    default_output_modes: list[str] = field(default_factory=lambda: ["text"])
    provider: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "url": self.url,
            "version": self.version,
            "capabilities": self.capabilities,
            "skills": [s.to_dict() for s in self.skills],
            "defaultInputModes": self.default_input_modes,
            "defaultOutputModes": self.default_output_modes,
            "provider": self.provider,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentCard":
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            url=data["url"],
            version=data.get("version", "0.1.0"),
            capabilities=data.get("capabilities", {}),
            skills=[AgentSkill.from_dict(s) for s in data.get("skills", [])],
            default_input_modes=data.get("defaultInputModes", ["text"]),
            default_output_modes=data.get("defaultOutputModes", ["text"]),
            provider=data.get("provider", {}),
        )


@dataclass
class TextPart:
    type: str = "text"
    text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, "text": self.text}


@dataclass
class FilePart:
    type: str = "file"
    name: str = ""
    mime_type: str = ""
    bytes: str | None = None  # base64
    uri: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"type": self.type, "name": self.name, "mimeType": self.mime_type}
        if self.bytes:
            d["bytes"] = self.bytes
        if self.uri:
            d["uri"] = self.uri
        return d


@dataclass
class DataPart:
    type: str = "data"
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, "data": self.data}


Part = TextPart | FilePart | DataPart


def part_to_dict(part: Part) -> dict[str, Any]:
    return part.to_dict()


def part_from_dict(data: dict[str, Any]) -> Part:
    t = data.get("type", "text")
    if t == "text":
        return TextPart(text=data.get("text", ""))
    elif t == "file":
        return FilePart(
            name=data.get("name", ""),
            mime_type=data.get("mimeType", ""),
            bytes=data.get("bytes"),
            uri=data.get("uri"),
        )
    else:
        return DataPart(data=data.get("data", {}))


@dataclass
class Message:
    """A2A message with role and parts."""

    role: str  # user | agent
    parts: list[Part] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "parts": [part_to_dict(p) for p in self.parts],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Message":
        return cls(
            role=data["role"],
            parts=[part_from_dict(p) for p in data.get("parts", [])],
            metadata=data.get("metadata", {}),
        )


@dataclass
class Artifact:
    """Output artifact from a task."""

    name: str
    parts: list[Part] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    index: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "parts": [part_to_dict(p) for p in self.parts],
            "metadata": self.metadata,
            "index": self.index,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Artifact":
        return cls(
            name=data["name"],
            parts=[part_from_dict(p) for p in data.get("parts", [])],
            metadata=data.get("metadata", {}),
            index=data.get("index", 0),
        )


@dataclass
class Task:
    """A2A task unit."""

    id: str
    state: TaskState
    messages: list[Message] = field(default_factory=list)
    artifacts: list[Artifact] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "state": self.state.value,
            "messages": [m.to_dict() for m in self.messages],
            "artifacts": [a.to_dict() for a in self.artifacts],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Task":
        return cls(
            id=data["id"],
            state=TaskState(data.get("state", "submitted")),
            messages=[Message.from_dict(m) for m in data.get("messages", [])],
            artifacts=[Artifact.from_dict(a) for a in data.get("artifacts", [])],
            metadata=data.get("metadata", {}),
        )
