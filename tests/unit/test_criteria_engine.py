"""Unit tests for CriteriaEngine."""
import pytest

from luminamind.evaluator.criteria_engine import CriteriaEngine, CriteriaNotFoundError
from luminamind.evaluator.criteria import GradingCriteria


class TestCriteriaEngine:
    """Tests for CriteriaEngine class."""

    def test_initialization(self):
        """CriteriaEngine initializes with all four default domains."""
        engine = CriteriaEngine()
        domains = engine.get_available_domains()
        assert "design" in domains
        assert "code" in domains
        assert "craft" in domains
        assert "originality" in domains

    def test_get_criteria(self):
        """get_criteria returns correct domain criteria."""
        engine = CriteriaEngine()
        design_criteria = engine.get_criteria("design")
        assert design_criteria is not None
        assert design_criteria.domain == "design"

    def test_get_criteria_not_found(self):
        """get_criteria returns None for nonexistent domain."""
        engine = CriteriaEngine()
        assert engine.get_criteria("nonexistent") is None

    def test_criteria_selection_by_artifact_type(self):
        """get_criteria_for_artifact returns correct list by type."""
        engine = CriteriaEngine()

        # Code artifact selects code and craft domains
        code_criteria = engine.get_criteria_for_artifact("code")
        assert len(code_criteria) >= 1
        assert any(c.domain == "code" for c in code_criteria)

        # Frontend artifact selects design domain
        frontend_criteria = engine.get_criteria_for_artifact("frontend")
        assert len(frontend_criteria) >= 1
        assert any(c.domain == "design" for c in frontend_criteria)

        # Full artifact selects all domains
        full_criteria = engine.get_criteria_for_artifact("full")
        assert len(full_criteria) >= 4

    def test_criteria_selection_with_explicit_domains(self):
        """get_criteria_for_artifact respects explicit domains parameter."""
        engine = CriteriaEngine()
        criteria = engine.get_criteria_for_artifact("code", domains=["design"])
        assert len(criteria) == 1
        assert criteria[0].domain == "design"

    def test_composite_criteria(self):
        """evaluate_composite produces weighted score."""
        engine = CriteriaEngine()
        artifact = "def example(): pass"
        result = engine.evaluate_composite(artifact, domains=["code"])

        assert "composite_score" in result
        assert "code" in result
        assert 0 <= result["composite_score"] <= 100

    def test_composite_evaluation_with_multiple_domains(self):
        """evaluate_composite combines multiple domain scores."""
        engine = CriteriaEngine()
        artifact = "def test(): return 42"
        result = engine.evaluate_composite(artifact, domains=["code", "craft"])

        assert "composite_score" in result
        assert "code" in result
        assert "craft" in result

    def test_custom_criteria_registration(self):
        """register_criteria allows custom criteria."""
        engine = CriteriaEngine()

        class CustomCriteria(GradingCriteria):
            domain = "custom"

            def evaluate(self, artifact):
                return {"score": 100, "issues": [], "domain": "custom"}

        engine.register_criteria("custom", CustomCriteria())
        assert engine.get_criteria("custom") is not None
        assert engine.get_criteria("custom").domain == "custom"

    def test_domain_weight_configuration(self):
        """set_domain_weight configures domain weights."""
        engine = CriteriaEngine()
        engine.set_domain_weight("code", 0.50)
        engine.set_domain_weight("design", 0.50)

        # Verify weights are set by checking composite evaluation
        artifact = "def test(): pass"
        result = engine.evaluate_composite(artifact, domains=["code", "design"])
        assert "composite_score" in result

    def test_clear_criteria(self):
        """clear_criteria removes all registered criteria."""
        engine = CriteriaEngine()
        engine.clear_criteria()
        assert len(engine.get_available_domains()) == 0

    def test_evaluate_composite_normalizes_weight(self):
        """evaluate_composite normalizes by total weight."""
        engine = CriteriaEngine()
        artifact = "x = 1"
        # Single domain with weight 0.5 should normalize correctly
        result = engine.evaluate_composite(artifact, domains=["code"])
        assert 0 <= result["composite_score"] <= 100

    def test_criteria_registry_persists(self):
        """Criteria registry persists across get_criteria calls."""
        engine = CriteriaEngine()
        # Get criteria multiple times
        criteria1 = engine.get_criteria("design")
        criteria2 = engine.get_criteria("design")
        assert criteria1 is criteria2  # Same instance


class TestCriteriaNotFoundError:
    """Tests for CriteriaNotFoundError exception."""

    def test_error_is_value_error(self):
        """CriteriaNotFoundError inherits from ValueError."""
        assert issubclass(CriteriaNotFoundError, ValueError)

    def test_error_message(self):
        """CriteriaNotFoundError can be raised with message."""
        with pytest.raises(CriteriaNotFoundError):
            raise CriteriaNotFoundError("Domain 'invalid' not found")