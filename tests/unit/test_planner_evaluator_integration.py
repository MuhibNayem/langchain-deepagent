"""Tests for PlannerEvaluatorIntegration review loop (PLAN-03).

Tests the planner-evaluator iteration loop behavior.
"""
import pytest
from unittest.mock import MagicMock, patch
from luminamind.planner.planner_evaluator_integration import (
    PlannerEvaluatorIntegration,
    SpecGradingCriteria,
    SpecReviewResult
)
from luminamind.planner.spec import SpecDocument, UserStory, AcceptanceCriterion
from luminamind.planner.agent import SpecResult


def create_complete_spec() -> SpecDocument:
    """Create a spec that should score >= 80."""
    return SpecDocument(
        id="spec-complete",
        title="Login Feature",
        description="Add user login functionality",
        feature_request="Add login for user",
        user_stories=[
            UserStory(
                id="US-1",
                description="As a user I want to login so that I can access my account",
                criteria=[
                    AcceptanceCriterion(
                        id="AC-1",
                        description="Login with valid credentials succeeds",
                        verify_method="pytest tests/test_login.py::test_login_success"
                    )
                ]
            )
        ]
    )


def create_mock_planner_agent(spec: SpecDocument):
    """Create a mock planner agent that returns the given spec."""
    mock_planner = MagicMock()
    mock_planner.generate_spec.return_value = SpecResult(
        spec=spec,
        generation_time_seconds=0.1,
        suggestions=[]
    )
    return mock_planner


def create_mock_evaluator_agent(score: float, issues: list[str] = None):
    """Create a mock evaluator agent that returns the given score and issues."""
    from luminamind.evaluator.agent import GradingResult
    mock_evaluator = MagicMock()
    mock_evaluator.evaluate.return_value = GradingResult(
        score=score,
        issues=issues or [],
        feedback=f"Score: {score}",
        iteration=1
    )
    return mock_evaluator


class TestPlannerEvaluatorIntegration:
    """Test PlannerEvaluatorIntegration review loop behavior."""

    def test_review_spec_converges_when_score_meets_threshold(self):
        """Test: review_spec returns when spec score >= threshold."""
        spec = create_complete_spec()
        mock_planner = create_mock_planner_agent(spec)
        mock_evaluator = create_mock_evaluator_agent(score=85.0, issues=[])

        integration = PlannerEvaluatorIntegration(
            planner_agent=mock_planner,
            evaluator_agent=mock_evaluator,
            score_threshold=80.0,
            max_iterations=3
        )

        result = integration.review_spec(spec, "Add login")

        assert isinstance(result, SpecReviewResult)
        assert result.final_score >= 80.0
        assert result.iterations == 1  # Converged on first iteration
        assert len(result.final_issues) == 0

    def test_review_spec_enforces_max_iterations(self):
        """Test: review_spec enforces max iterations when score < threshold."""
        spec = create_complete_spec()
        # Low-scoring spec that will never meet threshold
        low_spec = SpecDocument(
            id="low-spec",
            title="",
            description="",
            feature_request="x",
            user_stories=[]
        )
        mock_planner = create_mock_planner_agent(low_spec)
        mock_evaluator = create_mock_evaluator_agent(score=50.0, issues=["Missing title", "Missing desc"])

        integration = PlannerEvaluatorIntegration(
            planner_agent=mock_planner,
            evaluator_agent=mock_evaluator,
            score_threshold=80.0,
            max_iterations=2
        )

        result = integration.review_spec(spec, "Add login")

        assert isinstance(result, SpecReviewResult)
        assert result.iterations <= 2  # Max iterations enforced
        assert result.final_score == 50.0

    def test_review_spec_returns_specreviewresult(self):
        """Test: review_spec returns SpecReviewResult with metadata."""
        spec = create_complete_spec()
        mock_planner = create_mock_planner_agent(spec)
        mock_evaluator = create_mock_evaluator_agent(score=90.0, issues=[])

        integration = PlannerEvaluatorIntegration(
            planner_agent=mock_planner,
            evaluator_agent=mock_evaluator
        )

        result = integration.review_spec(spec, "Add login")

        assert isinstance(result, SpecReviewResult)
        assert hasattr(result, 'spec')
        assert hasattr(result, 'final_score')
        assert hasattr(result, 'iterations')
        assert hasattr(result, 'issues_resolved')
        assert hasattr(result, 'final_issues')

    def test_review_spec_incorporates_feedback_in_revision(self):
        """Test: When score < threshold, planner generates revised spec."""
        spec = create_complete_spec()
        low_spec = SpecDocument(
            id="revised",
            title="Revised Login",
            description="Improved",
            feature_request="x",
            user_stories=[]
        )
        mock_planner = create_mock_planner_agent(low_spec)
        mock_evaluator = create_mock_evaluator_agent(score=50.0, issues=["Missing title"])

        integration = PlannerEvaluatorIntegration(
            planner_agent=mock_planner,
            evaluator_agent=mock_evaluator,
            score_threshold=80.0,
            max_iterations=3
        )

        result = integration.review_spec(spec, "Add login")

        # Planner should have been called to generate revision
        assert mock_planner.generate_spec.called
        # Issues should be tracked
        assert len(result.issues_resolved) > 0 or len(result.final_issues) > 0


class TestSpecReviewResult:
    """Test SpecReviewResult dataclass."""

    def test_spec_review_result_has_required_fields(self):
        """Test: SpecReviewResult has all required fields."""
        spec = create_complete_spec()
        result = SpecReviewResult(
            spec=spec,
            final_score=85.0,
            iterations=2,
            issues_resolved=["Issue 1"],
            final_issues=[]
        )

        assert result.spec == spec
        assert result.final_score == 85.0
        assert result.iterations == 2
        assert result.issues_resolved == ["Issue 1"]
        assert result.final_issues == []

    def test_spec_review_result_defaults(self):
        """Test: SpecReviewResult has correct defaults."""
        spec = create_complete_spec()
        result = SpecReviewResult(
            spec=spec,
            final_score=80.0,
            iterations=1
        )

        assert result.issues_resolved == []
        assert result.final_issues == []


class TestPlannerEvaluatorIntegrationConfig:
    """Test PlannerEvaluatorIntegration configuration."""

    def test_custom_score_threshold(self):
        """Test: Custom score threshold is respected."""
        spec = create_complete_spec()
        mock_planner = create_mock_planner_agent(spec)
        mock_evaluator = create_mock_evaluator_agent(score=75.0, issues=[])

        integration = PlannerEvaluatorIntegration(
            planner_agent=mock_planner,
            evaluator_agent=mock_evaluator,
            score_threshold=70.0  # Lower threshold
        )

        result = integration.review_spec(spec, "Add login")
        assert result.final_score >= 70.0

    def test_custom_max_iterations(self):
        """Test: Custom max_iterations is respected."""
        spec = create_complete_spec()
        mock_planner = create_mock_planner_agent(spec)
        mock_evaluator = create_mock_evaluator_agent(score=50.0, issues=["Issue"])

        integration = PlannerEvaluatorIntegration(
            planner_agent=mock_planner,
            evaluator_agent=mock_evaluator,
            max_iterations=5
        )

        result = integration.review_spec(spec, "Add login")
        assert result.iterations <= 5
