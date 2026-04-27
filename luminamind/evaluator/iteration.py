"""IterationController for controlling the gen-eval loop per GE-02.

Controls the generator-evaluator iteration loop:
- Enforces max-iteration limits
- Detects convergence (score stabilizes)
- Tracks iteration statistics
"""
from dataclasses import dataclass, field
from typing import Any

from luminamind.evaluator.agent import EvaluatorAgent, GradingResult


@dataclass
class IterationStats:
    """Statistics from an iteration run.

    Attributes:
        iteration: Current iteration number
        score_history: List of scores from each evaluation
        issue_count_history: List of issue counts from each evaluation
        converged: Whether the iteration converged
        reason: Reason for termination ("max_iterations" | "converged" | "quality_threshold")
    """

    iteration: int
    score_history: list[float] = field(default_factory=list)
    issue_count_history: list[int] = field(default_factory=list)
    converged: bool = False
    reason: str = ""  # "max_iterations" | "converged" | "quality_threshold"


class IterationController:
    """Iteration controller per GE-02.

    Controls the generator-evaluator iteration loop:
    - Enforces max-iteration limits
    - Detects convergence (score stabilizes)
    - Tracks iteration statistics
    """

    def __init__(
        self,
        evaluator: EvaluatorAgent,
        max_iterations: int = 5,
        convergence_threshold: float = 0.05,  # Score change to consider converged
        convergence_window: int = 2,  # Number of iterations to check for stability
        min_iterations: int = 1,  # Minimum iterations before early termination
        quality_gate: float = 90.0,  # Score threshold to stop early
    ):
        self.evaluator = evaluator
        self.max_iterations = max_iterations
        self.convergence_threshold = convergence_threshold
        self.convergence_window = convergence_window
        self.min_iterations = min_iterations
        self.quality_gate = quality_gate

    def run(self, artifact: Any, context: dict | None = None) -> tuple[GradingResult, IterationStats]:
        """Run iteration loop until convergence or max_iterations.

        Args:
            artifact: The artifact to evaluate
            context: Optional context for evaluation

        Returns:
            tuple of (final GradingResult, IterationStats with history)
        """
        stats = IterationStats(iteration=0)
        current_artifact = artifact

        while stats.iteration < self.max_iterations:
            stats.iteration += 1

            result = self.evaluator.evaluate(current_artifact, context)
            stats.score_history.append(result.score)
            stats.issue_count_history.append(len(result.issues))

            # Check quality gate - if we hit threshold, stop early
            if result.score >= self.quality_gate:
                stats.converged = True
                stats.reason = "quality_threshold"
                return result, stats

            # Check convergence after min_iterations
            if stats.iteration >= self.min_iterations and self._is_converged(stats):
                stats.converged = True
                stats.reason = "converged"
                return result, stats

            # Prepare next iteration artifact if needed
            # (Generator will handle actual refinement)
            current_artifact = self._prepare_next_artifact(result)

        stats.reason = "max_iterations"
        return result, stats

    def _is_converged(self, stats: IterationStats) -> bool:
        """Determine if refinement has converged.

        Convergence = score stabilizes (no significant improvement)
        AND issue count stabilizes (no new issues found)
        """
        if len(stats.score_history) < self.convergence_window + 1:
            return False

        # Check score stability
        recent_scores = stats.score_history[-self.convergence_window:]
        score_diff = max(recent_scores) - min(recent_scores)

        # Check issue count stability
        recent_issues = stats.issue_count_history[-self.convergence_window:]
        issue_diff = max(recent_issues) - min(recent_issues)

        score_stable = score_diff <= self.convergence_threshold
        issues_stable = issue_diff <= 1  # Allow 1 issue variation

        return score_stable and issues_stable

    def _prepare_next_artifact(self, result: GradingResult) -> dict:
        """Prepare feedback for generator.

        Returns structured dict with:
        - current_score: float
        - issues_to_fix: list[str]
        - feedback: str (actionable guidance)
        """
        return {
            "current_score": result.score,
            "issues_to_fix": result.issues,
            "feedback": result.feedback,
            "iteration": result.iteration,
        }

    def should_continue(self, stats: IterationStats) -> bool:
        """Check if iteration should continue.

        Args:
            stats: Current iteration statistics

        Returns:
            True if should continue, False otherwise
        """
        return stats.iteration < self.max_iterations and not stats.converged

    def should_refine(self, stats: IterationStats) -> bool:
        """Check if refinement should continue.

        Args:
            stats: Current iteration statistics

        Returns:
            True if should refine, False if should stop
        """
        if stats.converged:
            return False
        if stats.iteration >= self.max_iterations:
            return False
        return True

    def should_pivot(self, stats: IterationStats) -> bool:
        """Check if should pivot strategy.

        Args:
            stats: Current iteration statistics

        Returns:
            True if should pivot, False otherwise
        """
        # Pivot if we've hit max iterations without meeting quality
        if stats.iteration >= self.max_iterations:
            last_score = stats.score_history[-1] if stats.score_history else 0.0
            if last_score < self.quality_gate:
                return True
        return False

    def get_score_trend(self, stats: IterationStats) -> str:
        """Get the trend direction of scores.

        Args:
            stats: Current iteration statistics

        Returns:
            "improving", "declining", or "stable"
        """
        if len(stats.score_history) < 2:
            return "stable"

        recent = stats.score_history[-3:] if len(stats.score_history) >= 3 else stats.score_history

        if len(recent) < 2:
            return "stable"

        first = recent[0]
        last = recent[-1]

        if last > first + self.convergence_threshold:
            return "improving"
        elif last < first - self.convergence_threshold:
            return "declining"
        else:
            return "stable"
