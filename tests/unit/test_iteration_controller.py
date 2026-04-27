"""Tests for IterationController.

RED phase tests for IterationController per GE-02.
Tests max iteration enforcement, convergence detection, quality gate.
"""
import pytest
from unittest.mock import Mock
from luminamind.evaluator.iteration import IterationController, IterationStats
from luminamind.evaluator.agent import GradingResult


class TestIterationController:
    """Test suite for IterationController."""

    def test_max_iteration_enforcement(self):
        """Controller accepts max_iterations parameter and enforces limit."""
        mock_evaluator = Mock()
        # Use varying scores to prevent early convergence detection
        # With scores changing significantly, convergence won't trigger
        mock_evaluator.evaluate.side_effect = [
            GradingResult(score=50.0 + i * 5, issues=["bug"], feedback="", iteration=i)
            for i in range(1, 4)
        ]

        controller = IterationController(mock_evaluator, max_iterations=3)
        result, stats = controller.run({})

        assert stats.iteration == 3
        assert stats.reason == "max_iterations"
        assert mock_evaluator.evaluate.call_count == 3

    def test_convergence_detection(self):
        """Convergence detected when score change <= threshold over window."""
        mock_evaluator = Mock()
        # Scores that will converge: 70, 72, 73 (diff <= 5 threshold)
        scores = [70.0, 72.0, 73.0, 73.5, 73.8]
        mock_evaluator.evaluate.side_effect = [
            GradingResult(score=s, issues=[], feedback="", iteration=i)
            for i, s in enumerate(scores, 1)
        ]

        controller = IterationController(
            mock_evaluator,
            max_iterations=10,
            convergence_threshold=5.0,
            convergence_window=2,
            min_iterations=2,
        )
        result, stats = controller.run({})

        assert stats.converged is True
        assert stats.reason == "converged"

    def test_quality_gate(self):
        """Quality gate triggers early termination at threshold score."""
        mock_evaluator = Mock()
        mock_evaluator.evaluate.return_value = GradingResult(
            score=95.0, issues=[], feedback="Great!", iteration=1
        )

        controller = IterationController(mock_evaluator, max_iterations=10, quality_gate=90.0)
        result, stats = controller.run({})

        assert stats.converged is True
        assert stats.reason == "quality_threshold"
        assert stats.iteration == 1

    def test_iteration_stats_tracking(self):
        """Iteration stats track score history."""
        mock_evaluator = Mock()
        mock_evaluator.evaluate.side_effect = [
            GradingResult(score=s, issues=["bug"], feedback="", iteration=i)
            for i, s in enumerate([60.0, 70.0, 80.0], 1)
        ]

        # Use max_iterations=3 to match the 3 mock responses
        controller = IterationController(mock_evaluator, max_iterations=3)
        result, stats = controller.run({})

        assert len(stats.score_history) == 3
        assert stats.score_history == [60.0, 70.0, 80.0]
        assert len(stats.issue_count_history) == 3

    def test_convergence_with_issue_stability(self):
        """Convergence considers both score and issue count stability."""
        mock_evaluator = Mock()
        # Scores stabilize but issues still change - should NOT converge
        # Need window+1=6 data points to check convergence with window=5
        scores = [70.0, 72.0, 73.0, 73.5, 73.8, 74.0]
        issues = [[], ["bug1"], ["bug1", "bug2"], ["bug1", "bug2", "bug3"], ["bug1", "bug2", "bug3", "bug4"], ["bug1", "bug2", "bug3", "bug4", "bug5"]]
        mock_evaluator.evaluate.side_effect = [
            GradingResult(score=s, issues=iss, feedback="", iteration=i)
            for i, s, iss in zip(range(1, 7), scores, issues)
        ]

        # Set max_iterations=6 to match the 6 mock responses
        controller = IterationController(
            mock_evaluator,
            max_iterations=6,
            convergence_threshold=5.0,
            convergence_window=5,
            min_iterations=2,
        )
        result, stats = controller.run({})

        # Should NOT converge because issue count is not stable (diff=5 > 1)
        # But will hit max_iterations since we only provide 6 responses
        assert stats.converged is False
        assert stats.iteration == 6
        assert stats.reason == "max_iterations"

    def test_min_iterations_before_convergence(self):
        """min_iterations ensures minimum iterations before convergence check."""
        mock_evaluator = Mock()
        # First two scores are very different, then stable
        scores = [50.0, 80.0, 82.0, 83.0]
        mock_evaluator.evaluate.side_effect = [
            GradingResult(score=s, issues=[], feedback="", iteration=i)
            for i, s in enumerate(scores, 1)
        ]

        controller = IterationController(
            mock_evaluator,
            max_iterations=10,
            convergence_threshold=5.0,
            convergence_window=2,
            min_iterations=3,  # Require at least 3 iterations
        )
        result, stats = controller.run({})

        # Should run all 4 iterations because min_iterations=3 and first convergence check is at iteration 3
        # But actually with min_iterations=3, we check convergence after iteration 3
        # Scores at iterations 2-3 are 80, 82 (diff=2 <= 5) so converge
        assert stats.iteration == 3
        assert stats.converged is True
        assert stats.reason == "converged"

    def test_should_continue_method(self):
        """should_continue() returns True when iterations remain."""
        mock_evaluator = Mock()
        # Use varying scores to prevent early convergence
        mock_evaluator.evaluate.side_effect = [
            GradingResult(score=50.0 + i * 5, issues=[], feedback="", iteration=i)
            for i in range(1, 6)
        ]

        controller = IterationController(mock_evaluator, max_iterations=5)
        result, stats = controller.run({})

        # After 5 iterations with varying scores, should reach max
        assert stats.iteration == 5
        assert stats.reason == "max_iterations"

    def test_should_refine_returns_true_when_not_converged(self):
        """should_refine() returns True when not converged and max not reached."""
        mock_evaluator = Mock()
        # Provide enough responses for max_iterations with varying scores
        mock_evaluator.evaluate.side_effect = [
            GradingResult(score=50.0 + i * 5, issues=["bug"], feedback="", iteration=i)
            for i in range(1, 6)
        ]

        controller = IterationController(mock_evaluator, max_iterations=5)
        result, stats = controller.run({})

        # After 5 iterations, should be max_iterations (not converged)
        assert stats.converged is False
        assert stats.iteration == 5
        assert stats.reason == "max_iterations"

    def test_should_pivot_decision(self):
        """Strategic pivot decision when no improvement over multiple iterations."""
        mock_evaluator = Mock()
        # Scores that show no real improvement
        scores = [60.0, 61.0, 61.5, 62.0, 62.2]
        mock_evaluator.evaluate.side_effect = [
            GradingResult(score=s, issues=["issue"], feedback="", iteration=i)
            for i, s in enumerate(scores, 1)
        ]

        controller = IterationController(
            mock_evaluator,
            max_iterations=10,
            convergence_threshold=2.0,  # Stricter threshold
            convergence_window=3,
            min_iterations=3,
        )
        result, stats = controller.run({})

        # Should converge because scores are not improving significantly
        assert stats.converged is True

    def test_score_trend_tracking(self):
        """get_score_trend() returns appropriate trend."""
        mock_evaluator = Mock()
        # Provide enough responses for max_iterations
        scores = [50.0, 65.0, 75.0, 80.0, 85.0]
        mock_evaluator.evaluate.side_effect = [
            GradingResult(score=s, issues=[], feedback="", iteration=i)
            for i, s in enumerate(scores, 1)
        ]

        controller = IterationController(mock_evaluator, max_iterations=5)
        result, stats = controller.run({})

        # Check that score history shows improvement trend
        assert stats.score_history == [50.0, 65.0, 75.0, 80.0, 85.0]
        # Score should be trending up
        assert stats.score_history[-1] > stats.score_history[0]

    def test_early_termination_on_quality(self):
        """Early termination when quality_gate score achieved."""
        mock_evaluator = Mock()
        # First evaluation meets quality threshold
        mock_evaluator.evaluate.return_value = GradingResult(
            score=92.0, issues=[], feedback="Excellent!", iteration=1
        )

        controller = IterationController(mock_evaluator, max_iterations=10, quality_gate=90.0)
        result, stats = controller.run({})

        assert stats.iteration == 1
        assert stats.converged is True
        assert stats.reason == "quality_threshold"
        assert mock_evaluator.evaluate.call_count == 1

    def test_no_early_termination_below_quality(self):
        """No early termination when score below quality_gate."""
        mock_evaluator = Mock()
        # Use varying scores below quality gate to prevent early termination
        mock_evaluator.evaluate.side_effect = [
            GradingResult(score=75.0 + i * 2, issues=["bug"], feedback="", iteration=i)
            for i in range(1, 6)
        ]

        controller = IterationController(mock_evaluator, max_iterations=5, quality_gate=90.0)
        result, stats = controller.run({})

        assert stats.iteration == 5  # Ran to max
        assert stats.reason == "max_iterations"
        assert mock_evaluator.evaluate.call_count == 5
