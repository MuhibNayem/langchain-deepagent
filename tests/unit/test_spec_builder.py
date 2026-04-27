"""Tests for SpecBuilder - structured spec generation with feature decomposition.

Per PLAN-02: Structured output with feature decomposition.
"""
import pytest
from unittest.mock import MagicMock, Mock
from luminamind.planner.spec_builder import SpecBuilder
from luminamind.planner.spec import UserStory, AcceptanceCriterion


class TestSpecBuilderDecomposition:
    """Test SpecBuilder.decompose functionality."""

    def test_decompose_returns_list_of_user_stories(self, mock_llm):
        """SpecBuilder.decompose returns list of UserStory."""
        builder = SpecBuilder(llm=mock_llm)
        # Mock the LLM to return structured JSON
        mock_response = MagicMock()
        mock_response.content = '''[
            {"id": "US-1", "description": "As a user I want to login so that I can access my account", "criteria": [
                {"id": "AC-1", "description": "Login succeeds with valid credentials", "verify_method": "pytest tests/test_login.py::test_login_success"}
            ]}
        ]'''
        mock_llm.invoke.return_value = mock_response

        stories = builder.decompose("User login feature")
        assert isinstance(stories, list)
        assert len(stories) >= 1
        assert all(isinstance(s, UserStory) for s in stories)

    def test_user_stories_follow_as_a_format(self, mock_llm):
        """Each UserStory description follows 'As a [role] I want [feature] so that [benefit]' format."""
        builder = SpecBuilder(llm=mock_llm)
        mock_response = MagicMock()
        mock_response.content = '''[
            {"id": "US-1", "description": "As a user I want to login so that I can access my account", "criteria": [
                {"id": "AC-1", "description": "Login succeeds", "verify_method": "pytest tests/test_login.py"}
            ]},
            {"id": "US-2", "description": "As an admin I want to manage users so that I can maintain system security", "criteria": [
                {"id": "AC-1", "description": "Admin can view user list", "verify_method": "pytest tests/test_admin.py"}
            ]}
        ]'''
        mock_llm.invoke.return_value = mock_response

        stories = builder.decompose("User and admin management")
        assert all(s.description.startswith("As a") for s in stories)
        # Verify format has all three parts
        for story in stories:
            desc = story.description
            assert "I want" in desc
            assert "so that" in desc

    def test_each_user_story_has_acceptance_criteria(self, mock_llm):
        """Each UserStory has at least one AcceptanceCriterion."""
        builder = SpecBuilder(llm=mock_llm)
        mock_response = MagicMock()
        mock_response.content = '''[
            {"id": "US-1", "description": "As a user I want to login", "criteria": [
                {"id": "AC-1", "description": "Login succeeds with valid credentials", "verify_method": "pytest tests/test_login.py"}
            ]}
        ]'''
        mock_llm.invoke.return_value = mock_response

        stories = builder.decompose("Login feature")
        for story in stories:
            assert len(story.criteria) >= 1
            assert all(isinstance(c, AcceptanceCriterion) for c in story.criteria)

    def test_decomposition_is_deterministic(self, mock_llm):
        """Same input produces same output (rule-based fallback)."""
        builder = SpecBuilder(llm=None)  # Force rule-based
        stories1 = builder.decompose("User login feature")
        stories2 = builder.decompose("User login feature")
        assert len(stories1) == len(stories2)
        # Rule-based should produce identical output
        for s1, s2 in zip(stories1, stories2):
            assert s1.id == s2.id
            assert s1.description == s2.description


class TestAcceptanceCriteria:
    """Test acceptance criteria generation with verify_method."""

    def test_acceptance_criterion_has_non_empty_verify_method(self, mock_llm):
        """AcceptanceCriterion has non-empty verify_method."""
        builder = SpecBuilder(llm=mock_llm)
        mock_response = MagicMock()
        mock_response.content = '''[
            {"id": "AC-1", "description": "Login succeeds", "verify_method": "pytest tests/test_login.py::test_login_success", "priority": "must"}
        ]'''
        mock_llm.invoke.return_value = mock_response

        story = UserStory(id="US-1", description="As a user I want to login", criteria=[])
        criteria = builder.generate_criteria(story)

        assert len(criteria) >= 1
        for c in criteria:
            assert hasattr(c, 'verify_method')
            assert c.verify_method
            assert len(c.verify_method.strip()) > 0

    def test_verify_method_points_to_test_or_command(self, mock_llm):
        """verify_method points to test file or contains command."""
        builder = SpecBuilder(llm=mock_llm)
        mock_response = MagicMock()
        mock_response.content = '''[
            {"id": "AC-1", "description": "Login succeeds", "verify_method": "pytest tests/test_login.py", "priority": "must"},
            {"id": "AC-2", "description": "UI renders correctly", "verify_method": "playwright test spec.spec.ts", "priority": "should"}
        ]'''
        mock_llm.invoke.return_value = mock_response

        story = UserStory(id="US-1", description="As a user I want to login", criteria=[])
        criteria = builder.generate_criteria(story)

        for c in criteria:
            # verify_method should reference test file or command
            vm = c.verify_method.lower()
            assert any(keyword in vm for keyword in ['pytest', 'playwright', 'test', 'spec', 'command']), \
                f"verify_method '{c.verify_method}' doesn't look like a test command"

    def test_priority_field_set_correctly(self, mock_llm):
        """Priority field set correctly (must/should/could)."""
        builder = SpecBuilder(llm=mock_llm)
        mock_response = MagicMock()
        mock_response.content = '''[
            {"id": "AC-1", "description": "Critical functionality", "verify_method": "pytest test.py", "priority": "must"},
            {"id": "AC-2", "description": "Nice to have", "verify_method": "pytest test.py", "priority": "could"}
        ]'''
        mock_llm.invoke.return_value = mock_response

        story = UserStory(id="US-1", description="Test story", criteria=[])
        criteria = builder.generate_criteria(story)

        valid_priorities = ['must', 'should', 'could']
        for c in criteria:
            assert c.priority in valid_priorities


class TestRuleBasedFallback:
    """Test rule-based fallback when LLM unavailable."""

    def test_rule_based_produces_valid_output(self):
        """Rule-based fallback produces valid output when LLM unavailable."""
        builder = SpecBuilder(llm=None)
        stories = builder.decompose("Add login for user")

        assert len(stories) >= 1
        assert all(isinstance(s, UserStory) for s in stories)

    def test_rule_based_follows_as_a_format(self):
        """Rule-based output follows As-a format."""
        builder = SpecBuilder(llm=None)
        stories = builder.decompose("User authentication feature")

        for story in stories:
            assert story.description.startswith("As a")
            assert "I want" in story.description
            assert "so that" in story.description

    def test_rule_based_has_criteria(self):
        """Rule-based output includes acceptance criteria."""
        builder = SpecBuilder(llm=None)
        stories = builder.decompose("Add user login feature")

        for story in stories:
            assert len(story.criteria) >= 1


class TestBuildSpec:
    """Test complete SpecDocument building."""

    def test_build_spec_returns_spec_document(self):
        """build_spec returns SpecDocument with correct structure."""
        builder = SpecBuilder(llm=None)
        spec = builder.build_spec("Add user login", "Login Feature")

        assert spec.title == "Login Feature"
        assert len(spec.user_stories) >= 1
        assert hasattr(spec, 'created_at')
        assert spec.created_at  # Non-empty timestamp

    def test_build_spec_includes_all_user_stories(self):
        """build_spec includes all decomposed user stories."""
        builder = SpecBuilder(llm=None)
        spec = builder.build_spec("User management system", "User Management")

        assert len(spec.user_stories) >= 1
        for story in spec.user_stories:
            assert isinstance(story, UserStory)
            assert story.id.startswith("US-")


@pytest.fixture
def mock_llm():
    """Mock LLM for testing."""
    return MagicMock()


class TestSpecBuilderIntegration:
    """Integration tests for SpecBuilder with real components."""

    def test_full_decomposition_pipeline(self):
        """Test full pipeline from feature request to spec."""
        builder = SpecBuilder(llm=None)
        spec = builder.build_spec("User authentication and profile management", "Auth System")

        # Verify spec structure
        assert spec.id.startswith("spec-")
        assert spec.title == "Auth System"
        assert len(spec.user_stories) >= 1

        # Verify each story
        for story in spec.user_stories:
            assert story.id.startswith("US-")
            assert story.description.startswith("As a")
            assert len(story.criteria) >= 1
            for criterion in story.criteria:
                assert criterion.id.startswith("AC-")
                assert criterion.verify_method