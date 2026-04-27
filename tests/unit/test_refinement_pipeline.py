"""Unit tests for RefinementPipeline per GE-03.

Tests cover:
- Pipeline execution
- Quality gate pass/fail
- Iteration stats recording
- Round-trip management
- Score aggregation
"""
import pytest
from unittest.mock import Mock, MagicMock
from luminamind.evaluator.pipeline import RefinementPipeline, RefinementResult, RoundResult
from luminamind.evaluator.agent import GradingResult
from luminamind.evaluator.iteration import IterationStats


class TestRefinementPipeline:
    """Test suite for RefinementPipeline."""

    def test_pipeline_execution(self):
        """Test pipeline accepts generator and evaluator and returns RefinementResult."""
        mock_generator = Mock()
        mock_evaluator = Mock()
        mock_evaluator.evaluate.return_value = GradingResult(
            score=85.0, issues=["style"], feedback="Good", iteration=1
        )

        mock_controller = Mock()
        mock_controller.run.return_value = (
            GradingResult(score=85.0, issues=[], feedback="", iteration=1),
            IterationStats(iteration=1, score_history=[85.0], converged=True, reason="quality_threshold"),
        )

        pipeline = RefinementPipeline(
            generator=mock_generator,
            evaluator=mock_evaluator,
            controller=mock_controller,
            quality_gate=80.0,
        )

        result = pipeline.refine("initial code", "Add feature")

        assert isinstance(result, RefinementResult)
        assert result.final_result.score == 85.0
        assert result.converged is True
        assert result.reason == "quality_threshold"

    def test_quality_gate_passes(self):
        """Test quality gate passes when score meets or exceeds threshold."""
        mock_generator = Mock()
        mock_evaluator = Mock()
        mock_controller = Mock()
        mock_controller.run.return_value = (
            GradingResult(score=90.0, issues=[], feedback="Great!", iteration=1),
            IterationStats(iteration=1, score_history=[90.0], converged=True, reason="quality_threshold"),
        )

        pipeline = RefinementPipeline(
            generator=mock_generator,
            evaluator=mock_evaluator,
            controller=mock_controller,
            quality_gate=80.0,
        )

        result = pipeline.refine("quality code", "Add feature")

        assert result.converged is True
        assert result.reason == "quality_threshold"
        assert result.feedback_for_generator is None

    def test_quality_gate_fails(self):
        """Test quality gate fails with feedback when score below threshold."""
        mock_generator = Mock()
        mock_evaluator = Mock()
        mock_controller = Mock()
        mock_controller.run.return_value = (
            GradingResult(score=50.0, issues=["security"], feedback="", iteration=1),
            IterationStats(iteration=1, score_history=[50.0], converged=False, reason="max_iterations"),
        )

        pipeline = RefinementPipeline(
            generator=mock_generator,
            evaluator=mock_evaluator,
            controller=mock_controller,
            quality_gate=80.0,
        )

        result = pipeline.refine("insecure code", "Add feature")

        assert result.converged is False
        assert result.reason == "quality_gate_failed"
        assert result.feedback_for_generator is not None
        assert "gap" in result.feedback_for_generator
        assert result.feedback_for_generator["gap"] == 30.0

    def test_iteration_stats_recorded(self):
        """Test pipeline records iteration stats correctly."""
        mock_generator = Mock()
        mock_evaluator = Mock()
        mock_controller = Mock()
        mock_controller.run.return_value = (
            GradingResult(score=90.0, issues=[], feedback="", iteration=2),
            IterationStats(iteration=2, score_history=[70.0, 90.0], converged=True, reason="quality_threshold"),
        )

        pipeline = RefinementPipeline(
            generator=mock_generator,
            evaluator=mock_evaluator,
            controller=mock_controller,
            quality_gate=80.0,
        )

        result = pipeline.refine("code", "Add feature")

        assert result.iteration_stats.iteration == 2
        assert result.iteration_stats.score_history == [70.0, 90.0]
        assert result.iteration_stats.converged is True

    def test_run_round(self):
        """Test run_round returns RoundResult with correct data."""
        mock_generator = Mock()
        mock_evaluator = Mock()
        mock_bridge = Mock()
        mock_bridge.send_for_evaluation.return_value = GradingResult(
            score=75.0, issues=["style"], feedback="Good", iteration=1
        )

        pipeline = RefinementPipeline(
            generator=mock_generator,
            evaluator=mock_evaluator,
            bridge=mock_bridge,
            quality_gate=80.0,
        )

        result = pipeline.run_round("artifact", 1, "session-123")

        assert isinstance(result, RoundResult)
        assert result.round_number == 1
        assert result.grading_result.score == 75.0
        mock_bridge.send_for_evaluation.assert_called_once()

    def test_evaluate_output(self):
        """Test evaluate_output returns GradingResult."""
        mock_generator = Mock()
        mock_evaluator = Mock()
        mock_evaluator.evaluate.return_value = GradingResult(
            score=85.0, issues=[], feedback="Good", iteration=1
        )

        pipeline = RefinementPipeline(
            generator=mock_generator,
            evaluator=mock_evaluator,
            quality_gate=80.0,
        )

        result = pipeline.evaluate_output("test artifact")

        assert isinstance(result, GradingResult)
        assert result.score == 85.0
        mock_evaluator.evaluate.assert_called_once_with("test artifact", None)

    def test_should_terminate(self):
        """Test should_terminate correctly evaluates grading result."""
        mock_generator = Mock()
        mock_evaluator = Mock()

        pipeline = RefinementPipeline(
            generator=mock_generator,
            evaluator=mock_evaluator,
            quality_gate=80.0,
        )

        # Should terminate when score meets quality gate
        result1 = GradingResult(score=85.0, issues=[], feedback="", iteration=1)
        assert pipeline.should_terminate(result1) is True

        # Should not terminate when score below quality gate but recoverable
        result2 = GradingResult(score=50.0, issues=["style"], feedback="", iteration=1)
        assert pipeline.should_terminate(result2) is False

        # Should terminate when score too low to recover
        result3 = GradingResult(score=15.0, issues=["critical"], feedback="", iteration=1)
        assert pipeline.should_terminate(result3) is True

    def test_should_continue_refinement(self):
        """Test should_continue_refinement delegates to controller."""
        mock_generator = Mock()
        mock_evaluator = Mock()
        mock_controller = Mock()
        mock_controller.should_refine.return_value = True

        pipeline = RefinementPipeline(
            generator=mock_generator,
            evaluator=mock_evaluator,
            controller=mock_controller,
            quality_gate=80.0,
        )

        stats = IterationStats(iteration=2, score_history=[70.0, 80.0])
        result = pipeline.should_continue_refinement(stats)

        assert result is True
        mock_controller.should_refine.assert_called_once_with(stats)

    def test_aggregate_scores(self):
        """Test aggregate_scores computes correct metrics."""
        mock_generator = Mock()
        mock_evaluator = Mock()

        pipeline = RefinementPipeline(
            generator=mock_generator,
            evaluator=mock_evaluator,
            quality_gate=80.0,
        )

        result = pipeline.aggregate_scores([70.0, 75.0, 80.0, 85.0])

        assert result["avg"] == 77.5
        assert result["min"] == 70.0
        assert result["max"] == 85.0
        assert result["trend"] == "improving"

    def test_aggregate_scores_empty(self):
        """Test aggregate_scores handles empty history."""
        mock_generator = Mock()
        mock_evaluator = Mock()

        pipeline = RefinementPipeline(
            generator=mock_generator,
            evaluator=mock_evaluator,
            quality_gate=80.0,
        )

        result = pipeline.aggregate_scores([])

        assert result["avg"] == 0.0
        assert result["min"] == 0.0
        assert result["max"] == 0.0
        assert result["trend"] == "stable"

    def test_feedback_generation_critical_issues(self):
        """Test feedback generation identifies critical issues."""
        mock_generator = Mock()
        mock_evaluator = Mock()
        mock_controller = Mock()
        mock_controller.run.return_value = (
            GradingResult(
                score=40.0,
                issues=["SQL injection vulnerability", "style issue"],
                feedback="",
                iteration=1,
            ),
            IterationStats(iteration=1, score_history=[40.0], converged=False, reason="max_iterations"),
        )

        pipeline = RefinementPipeline(
            generator=mock_generator,
            evaluator=mock_evaluator,
            controller=mock_controller,
            quality_gate=80.0,
        )

        result = pipeline.refine("vulnerable code", "Add feature")

        assert result.feedback_for_generator is not None
        assert "SQL injection vulnerability" in result.feedback_for_generator["critical_issues"]
        assert len(result.feedback_for_generator["recommended_fixes"]) == 2

    def test_session_id_unique(self):
        """Test that each refine call gets a unique session ID."""
        mock_generator = Mock()
        mock_evaluator = Mock()
        mock_controller = Mock()
        mock_controller.run.return_value = (
            GradingResult(score=90.0, issues=[], feedback="", iteration=1),
            IterationStats(iteration=1, score_history=[90.0], converged=True, reason="quality_threshold"),
        )

        pipeline = RefinementPipeline(
            generator=mock_generator,
            evaluator=mock_evaluator,
            controller=mock_controller,
            quality_gate=80.0,
        )

        result1 = pipeline.refine("code1", "task1")
        result2 = pipeline.refine("code2", "task2")

        assert result1.session_id != result2.session_id

    def test_convergence_and_quality_gate_together(self):
        """Test that when score meets quality gate, convergence is used."""
        mock_generator = Mock()
        mock_evaluator = Mock()
        mock_controller = Mock()
        mock_controller.run.return_value = (
            GradingResult(score=85.0, issues=[], feedback="", iteration=3),
            IterationStats(
                iteration=3,
                score_history=[60.0, 70.0, 85.0],
                converged=True,
                reason="quality_threshold",
            ),
        )

        pipeline = RefinementPipeline(
            generator=mock_generator,
            evaluator=mock_evaluator,
            controller=mock_controller,
            quality_gate=80.0,
        )

        result = pipeline.refine("code", "Add feature")

        # Score meets quality gate, so converged
        assert result.converged is True
        assert result.reason == "quality_threshold"
        assert result.iteration_stats.score_history == [60.0, 70.0, 85.0]
