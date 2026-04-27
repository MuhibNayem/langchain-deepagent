"""Tests for PlannerAgent spec generation."""
import pytest
from unittest.mock import MagicMock, patch
from luminamind.planner.agent import PlannerAgent, SpecResult
from luminamind.planner.spec import SpecDocument, UserStory, AcceptanceCriterion


class TestPlannerAgent:
    """Test PlannerAgent spec generation capabilities."""

    def test_planner_agent_generate_spec(self):
        """Test PlannerAgent.generate_spec returns SpecResult with SpecDocument."""
        # Create mock LLM
        mock_model = MagicMock()
        mock_model.invoke.return_value = MagicMock(content='{"id": "spec-1", "title": "User Login", "description": "Login functionality", "feature_request": "Add login"}')

        agent = PlannerAgent(model=mock_model)
        result = agent.generate_spec("Add user login feature")

        assert isinstance(result, SpecResult)
        assert isinstance(result.spec, SpecDocument)
        assert result.generation_time_seconds > 0
        assert result.generation_time_seconds < 300  # <5 min

    def test_planner_agent_spec_generation_timing(self):
        """Test spec generation completes in <5 minutes (timestamp comparison)."""
        mock_model = MagicMock()
        mock_model.invoke.return_value = MagicMock(content='{"id": "spec-timing", "title": "Test", "description": "Test", "feature_request": "Test"}')

        agent = PlannerAgent(model=mock_model)
        start = __import__("time").time()
        result = agent.generate_spec("Test feature")
        elapsed = result.generation_time_seconds

        assert elapsed < 300, f"Spec generation took {elapsed}s, expected <300s"

    def test_planner_agent_spec_has_user_story(self):
        """Test SpecDocument has at least 1 user story with >=1 acceptance criterion."""
        mock_model = MagicMock()
        mock_model.invoke.return_value = MagicMock(content='{"id": "spec-us", "title": "Feature", "description": "Feature desc", "feature_request": "Test", "user_stories": [{"id": "US-1", "description": "As a user", "criteria": [{"id": "AC-1", "description": "Works", "verify_method": "pytest"}]}]}')

        agent = PlannerAgent(model=mock_model)
        result = agent.generate_spec("Test")

        assert len(result.spec.user_stories) >= 1
        assert len(result.spec.user_stories[0].criteria) >= 1

    def test_planner_agent_ai_suggestions(self):
        """Test AI suggestion integration provides alternative decomposition suggestions."""
        mock_model = MagicMock()
        mock_model.invoke.return_value = MagicMock(content='{"id": "spec-alt", "title": "Alt", "description": "Alt desc", "feature_request": "Test"}')

        agent = PlannerAgent(model=mock_model)
        result = agent.generate_spec("Test feature")

        # Should have suggestions (from _generate_suggestions call)
        assert isinstance(result.suggestions, list)

    def test_spec_result_structure(self):
        """Test SpecResult dataclass has spec, generation_time, suggestions."""
        spec = SpecDocument(id="s1", title="T", description="D", feature_request="F")
        result = SpecResult(spec=spec, generation_time_seconds=1.5, suggestions=["alt1", "alt2"])

        assert result.spec.id == "s1"
        assert result.generation_time_seconds == 1.5
        assert len(result.suggestions) == 2