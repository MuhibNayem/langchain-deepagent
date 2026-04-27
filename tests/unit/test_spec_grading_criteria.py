"""Tests for SpecGradingCriteria quality evaluation (PLAN-03).

RED phase: Tests define expected behavior for spec quality evaluation.
"""
import pytest
from luminamind.planner.planner_evaluator_integration import SpecGradingCriteria
from luminamind.planner.spec import SpecDocument, UserStory, AcceptanceCriterion


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
                    ),
                    AcceptanceCriterion(
                        id="AC-2",
                        description="Login with invalid credentials shows error",
                        verify_method="pytest tests/test_login.py::test_login_failure"
                    )
                ]
            ),
            UserStory(
                id="US-2",
                description="As a user I want to logout so that I can secure my account",
                criteria=[
                    AcceptanceCriterion(
                        id="AC-3",
                        description="Logout terminates session",
                        verify_method="pytest tests/test_login.py::test_logout"
                    )
                ]
            )
        ]
    )


def create_incomplete_spec() -> SpecDocument:
    """Create a spec that should score < 80 due to missing elements."""
    return SpecDocument(
        id="spec-incomplete",
        title="",  # Missing title
        description="",  # Missing description
        feature_request="Add login",
        user_stories=[]  # No user stories
    )


def create_partial_spec() -> SpecDocument:
    """Create a spec with some but not all required elements."""
    return SpecDocument(
        id="spec-partial",
        title="Login",  # Has title
        description="Login feature",  # Has description
        feature_request="Add login",
        user_stories=[
            UserStory(
                id="US-1",
                description="User wants login",  # Missing "As a" format
                criteria=[
                    AcceptanceCriterion(
                        id="AC-1",
                        description="Login works",  # Missing verify_method
                        verify_method=""
                    )
                ]
            )
        ]
    )


class TestSpecGradingCriteria:
    """Test SpecGradingCriteria evaluation behavior."""

    def test_complete_spec_scores_high(self):
        """Test: Complete spec with title, description, user stories scores >= 80."""
        criteria = SpecGradingCriteria()
        spec = create_complete_spec()
        result = criteria.evaluate(spec)

        assert result["score"] >= 80, f"Expected score >= 80, got {result['score']}"
        assert len(result["issues"]) == 0, f"Expected no issues, got {result['issues']}"

    def test_incomplete_spec_scores_low(self):
        """Test: Spec missing title, description, user stories scores < 80."""
        criteria = SpecGradingCriteria()
        spec = create_incomplete_spec()
        result = criteria.evaluate(spec)

        assert result["score"] < 80, f"Expected score < 80, got {result['score']}"
        assert len(result["issues"]) > 0, "Expected issues for incomplete spec"

    def test_missing_title_reduces_score(self):
        """Test: Spec without title gets score penalty."""
        criteria = SpecGradingCriteria()
        spec = create_incomplete_spec()
        spec.title = ""  # Ensure it's empty
        result = criteria.evaluate(spec)

        assert any("title" in issue.lower() for issue in result["issues"]), \
            "Expected issue about missing title"

    def test_missing_description_reduces_score(self):
        """Test: Spec without description gets score penalty."""
        criteria = SpecGradingCriteria()
        spec = create_incomplete_spec()
        spec.description = ""  # Ensure it's empty
        result = criteria.evaluate(spec)

        assert any("description" in issue.lower() for issue in result["issues"]), \
            "Expected issue about missing description"

    def test_missing_user_stories_reduces_score(self):
        """Test: Spec without user stories gets score penalty."""
        criteria = SpecGradingCriteria()
        spec = create_incomplete_spec()
        spec.user_stories = []  # Ensure no user stories
        result = criteria.evaluate(spec)

        assert any("user stories" in issue.lower() for issue in result["issues"]), \
            f"Expected issue about missing user stories, got {result['issues']}"

    def test_user_story_without_as_a_format(self):
        """Test: User story not starting with 'As a' gets penalty."""
        criteria = SpecGradingCriteria()
        spec = create_partial_spec()
        result = criteria.evaluate(spec)

        assert any("as-a" in issue.lower() for issue in result["issues"]), \
            f"Expected issue about As-a format, got {result['issues']}"

    def test_acceptance_criterion_without_verify_method(self):
        """Test: Criterion without verify_method gets penalty."""
        criteria = SpecGradingCriteria()
        spec = create_partial_spec()
        result = criteria.evaluate(spec)

        assert any("verify_method" in issue.lower() for issue in result["issues"]), \
            "Expected issue about missing verify_method"

    def test_returns_strengths_for_good_spec(self):
        """Test: Complete spec returns positive strengths."""
        criteria = SpecGradingCriteria()
        spec = create_complete_spec()
        result = criteria.evaluate(spec)

        assert len(result["strengths"]) > 0, "Expected strengths for complete spec"
        assert any("title" in s.lower() for s in result["strengths"]), \
            "Expected strength about having title"

    def test_returns_recommendations_for_improvable_spec(self):
        """Test: Partial spec returns recommendations."""
        criteria = SpecGradingCriteria()
        spec = create_partial_spec()
        result = criteria.evaluate(spec)

        assert len(result["recommendations"]) > 0, \
            "Expected recommendations for partial spec"

    def test_score_bounded_between_0_and_100(self):
        """Test: Score is always bounded between 0 and 100."""
        criteria = SpecGradingCriteria()

        # Test with empty spec
        empty_spec = SpecDocument(id="empty", title="", description="", feature_request="")
        result = criteria.evaluate(empty_spec)
        assert 0 <= result["score"] <= 100, "Score should be bounded 0-100"

        # Test with complete spec
        complete_spec = create_complete_spec()
        result = criteria.evaluate(complete_spec)
        assert 0 <= result["score"] <= 100, "Score should be bounded 0-100"
