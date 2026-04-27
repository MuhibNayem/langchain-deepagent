"""SpecDocument dataclass for structured specification output.

Per PLAN-01: Spec in <5 min that evaluator approves.
Per PLAN-02: Structured output with feature decomposition into user stories.
"""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class AcceptanceCriterion:
    """An acceptance criterion for a user story.

    Attributes:
        id: Unique identifier (e.g., "AC-1")
        description: Human-readable description of the criterion
        verify_method: How to verify this criterion (e.g., "pytest tests/test_login.py")
        priority: must, should, or could (default: "must")
    """

    id: str
    description: str
    verify_method: str
    priority: str = "must"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "description": self.description,
            "verify_method": self.verify_method,
            "priority": self.priority,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AcceptanceCriterion":
        return cls(
            id=data["id"],
            description=data["description"],
            verify_method=data["verify_method"],
            priority=data.get("priority", "must"),
        )


@dataclass
class UserStory:
    """A user story decomposed from a feature request.

    Attributes:
        id: Unique identifier (e.g., "US-1")
        description: "As a [role] I want [feature] so that [benefit]"
        criteria: List of AcceptanceCriterion instances
        priority: must, should, or could (default: "must")
    """

    id: str
    description: str
    criteria: list[AcceptanceCriterion] = field(default_factory=list)
    priority: str = "must"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "description": self.description,
            "criteria": [c.to_dict() for c in self.criteria],
            "priority": self.priority,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "UserStory":
        return cls(
            id=data["id"],
            description=data["description"],
            criteria=[
                AcceptanceCriterion.from_dict(c) for c in data.get("criteria", [])
            ],
            priority=data.get("priority", "must"),
        )


@dataclass
class SpecDocument:
    """A structured specification document for a feature request.

    Attributes:
        id: Unique identifier for this spec
        title: Short descriptive title
        description: Detailed description of the feature
        feature_request: Original request from user/AI
        user_stories: Decomposed user stories
        technical_notes: Optional technical implementation notes
        estimated_complexity: low, medium, or high
        created_at: ISO timestamp of creation
    """

    id: str
    title: str
    description: str
    feature_request: str
    user_stories: list[UserStory] = field(default_factory=list)
    technical_notes: str = ""
    estimated_complexity: str = ""
    created_at: str = ""

    def to_dict(self) -> dict:
        """Serialize to dictionary for persistence."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "feature_request": self.feature_request,
            "user_stories": [us.to_dict() for us in self.user_stories],
            "technical_notes": self.technical_notes,
            "estimated_complexity": self.estimated_complexity,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SpecDocument":
        """Deserialize from dictionary."""
        return cls(
            id=data["id"],
            title=data["title"],
            description=data["description"],
            feature_request=data["feature_request"],
            user_stories=[UserStory.from_dict(us) for us in data.get("user_stories", [])],
            technical_notes=data.get("technical_notes", ""),
            estimated_complexity=data.get("estimated_complexity", ""),
            created_at=data.get("created_at", ""),
        )