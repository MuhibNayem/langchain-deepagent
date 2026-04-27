"""Tests for EvaluatorAgent with ReAct pattern."""
from __future__ import annotations

import pytest


class TestEvaluatorAgent:
    """Tests for EvaluatorAgent ReAct loop and scoring."""

    def test_evaluator_agent_react_loop(self):
        """Test: EvaluatorAgent accepts artifact and grading criteria, runs ReAct loop."""
        from luminamind.evaluator.agent import EvaluatorAgent, GradingResult

        agent = EvaluatorAgent(max_iterations=3)
        artifact = "def foo(): return 42"
        result = agent.evaluate(artifact)

        assert isinstance(result, GradingResult)
        assert 0 <= result.score <= 100
        assert result.iteration >= 0

    def test_grading_result_structure(self):
        """Test: GradingResult has score, issues, feedback, iteration."""
        from luminamind.evaluator.agent import GradingResult

        result = GradingResult(
            score=85.0, issues=["unused_var"], feedback="Good", iteration=1
        )
        assert result.score == 85.0
        assert result.issues == ["unused_var"]
        assert result.feedback == "Good"
        assert result.iteration == 1

    def test_evaluate_returns_grading_result(self):
        """Test: evaluate() returns GradingResult with expected fields."""
        from luminamind.evaluator.agent import EvaluatorAgent, GradingResult

        agent = EvaluatorAgent(max_iterations=3)
        artifact = "x = 1 + 2"
        result = agent.evaluate(artifact)

        assert isinstance(result, GradingResult)
        assert hasattr(result, "score")
        assert hasattr(result, "issues")
        assert hasattr(result, "feedback")
        assert hasattr(result, "iteration")


class TestGradingCriteria:
    """Tests for GradingCriteria framework."""

    def test_code_criteria_evaluate(self):
        """Test: CodeCriteria.evaluate() returns structured dict."""
        from luminamind.evaluator.criteria import CodeCriteria

        criteria = CodeCriteria()
        result = criteria.evaluate("def add(a, b): return a + b")
        assert "score" in result
        assert "issues" in result
        assert "strengths" in result
        assert "recommendations" in result

    def test_design_criteria_domain(self):
        """Test: DesignCriteria has correct domain."""
        from luminamind.evaluator.criteria import DesignCriteria

        criteria = DesignCriteria()
        assert criteria.domain == "design"

    def test_craft_criteria_domain(self):
        """Test: CraftCriteria has correct domain."""
        from luminamind.evaluator.criteria import CraftCriteria

        criteria = CraftCriteria()
        assert criteria.domain == "craft"

    def test_originality_criteria_domain(self):
        """Test: OriginalityCriteria has correct domain."""
        from luminamind.evaluator.criteria import OriginalityCriteria

        criteria = OriginalityCriteria()
        assert criteria.domain == "originality"

    def test_code_criteria_issues_found(self):
        """Test: CodeCriteria finds issues in bad code."""
        from luminamind.evaluator.criteria import CodeCriteria

        criteria = CodeCriteria()
        result = criteria.evaluate("def f(x):x=1;return x")
        assert "issues" in result
        assert isinstance(result["issues"], list)
