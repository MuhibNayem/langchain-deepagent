"""Tests for A2A protocol types."""
from luminamind.a2a.types import (
    AgentCard,
    AgentSkill,
    Artifact,
    Message,
    Task,
    TaskState,
    TextPart,
    part_from_dict,
    part_to_dict,
)


def test_agent_card_roundtrip():
    card = AgentCard(
        name="TestAgent",
        description="A test agent",
        url="http://localhost:8000/a2a/",
        skills=[AgentSkill(id="skill1", name="Skill One", description="Does one thing")],
    )
    data = card.to_dict()
    restored = AgentCard.from_dict(data)
    assert restored.name == "TestAgent"
    assert len(restored.skills) == 1
    assert restored.skills[0].id == "skill1"


def test_task_roundtrip():
    task = Task(
        id="task-1",
        state=TaskState.WORKING,
        messages=[Message(role="user", parts=[TextPart(text="hello")])],
    )
    data = task.to_dict()
    restored = Task.from_dict(data)
    assert restored.id == "task-1"
    assert restored.state == TaskState.WORKING


def test_part_serialization():
    part = TextPart(text="hello")
    assert part_to_dict(part)["type"] == "text"
    restored = part_from_dict({"type": "text", "text": "hello"})
    assert isinstance(restored, TextPart)
    assert restored.text == "hello"


def test_artifact_roundtrip():
    art = Artifact(name="result", parts=[TextPart(text="done")])
    data = art.to_dict()
    restored = Artifact.from_dict(data)
    assert restored.name == "result"
