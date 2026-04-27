"""Tests for PlannerAgent spec generation components."""
import pytest
from luminamind.planner.spec import SpecDocument, UserStory, AcceptanceCriterion


class TestSpecDocument:
    """Test SpecDocument dataclass structure and serialization."""

    def test_acceptance_criterion_structure(self):
        """Test AcceptanceCriterion has required fields."""
        ac = AcceptanceCriterion(
            id="AC-1",
            description="Login with valid credentials succeeds",
            verify_method="pytest tests/test_login.py"
        )
        assert ac.id == "AC-1"
        assert ac.description == "Login with valid credentials succeeds"
        assert ac.verify_method == "pytest tests/test_login.py"
        assert ac.priority == "must"  # default value

    def test_user_story_structure(self):
        """Test UserStory has id, description, criteria list."""
        ac = AcceptanceCriterion(
            id="AC-1",
            description="Login succeeds",
            verify_method="pytest tests/test_login.py"
        )
        us = UserStory(
            id="US-1",
            description="As a user I want to login with email",
            criteria=[ac]
        )
        assert us.id == "US-1"
        assert us.description == "As a user I want to login with email"
        assert len(us.criteria) == 1
        assert us.priority == "must"  # default value

    def test_spec_document_structure(self):
        """Test SpecDocument has title, description, user_stories list, acceptance_criteria list."""
        ac = AcceptanceCriterion(
            id="AC-1",
            description="Login succeeds",
            verify_method="pytest tests/test_login.py"
        )
        us = UserStory(
            id="US-1",
            description="As a user I want to login",
            criteria=[ac]
        )
        spec = SpecDocument(
            id="spec-1",
            title="User Login",
            description="Add login functionality",
            feature_request="As a user I want to login",
            user_stories=[us]
        )
        assert spec.title == "User Login"
        assert spec.description == "Add login functionality"
        assert len(spec.user_stories) == 1
        assert spec.created_at == ""  # default empty until generated

    def test_spec_document_serialization(self):
        """Test SpecDocument serializes to/from dict for persistence."""
        spec = SpecDocument(
            id="spec-1",
            title="Test Spec",
            description="Test description",
            feature_request="Test feature request",
            user_stories=[],
            technical_notes="Some technical notes",
            estimated_complexity="medium"
        )
        data = spec.to_dict()
        assert isinstance(data, dict)
        assert data["id"] == "spec-1"
        assert data["title"] == "Test Spec"

        # Test deserialization
        restored = SpecDocument.from_dict(data)
        assert restored.id == spec.id
        assert restored.title == spec.title
        assert restored.description == spec.description

    def test_spec_document_from_dict_with_user_stories(self):
        """Test SpecDocument.from_dict restores user stories and criteria."""
        data = {
            "id": "spec-2",
            "title": "Feature X",
            "description": "Description of feature X",
            "feature_request": "User wants feature X",
            "user_stories": [
                {
                    "id": "US-1",
                    "description": "As a user I want feature X",
                    "criteria": [
                        {
                            "id": "AC-1",
                            "description": "Feature X works",
                            "verify_method": "pytest tests/"
                        }
                    ],
                    "priority": "should"
                }
            ],
            "technical_notes": "Technical notes here",
            "estimated_complexity": "high",
            "created_at": "2026-04-27T10:00:00Z"
        }
        spec = SpecDocument.from_dict(data)
        assert spec.id == "spec-2"
        assert len(spec.user_stories) == 1
        assert spec.user_stories[0].id == "US-1"
        assert len(spec.user_stories[0].criteria) == 1
        assert spec.user_stories[0].criteria[0].id == "AC-1"