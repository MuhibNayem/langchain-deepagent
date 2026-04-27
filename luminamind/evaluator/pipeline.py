"""RefinementPipeline for multi-round generator-evaluator refinement per GE-03.

Orchestrates the generator-evaluator loop:
1. Generator produces initial artifact
2. Evaluator critiques artifact
3. Generator refines based on feedback
4. Repeat until convergence or max iterations
5. Quality gate enforces minimum threshold

This pipeline combines IterationController for loop control and FeedbackBridge
for generator-evaluator communication.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from luminamind.evaluator.iteration import IterationController, IterationStats
from luminamind.evaluator.feedback_bridge import FeedbackBridge
from luminamind.evaluator.agent import EvaluatorAgent, GradingResult
from luminamind.observability.harness_metrics import HarnessMetrics
from luminamind.observability.decision_logger import (
    DecisionLogger,
    DecisionPoint,
    TraceEntry,
)


@dataclass
class RefinementResult:
    """Result from multi-round refinement.

    Attributes:
        final_artifact: The final artifact after refinement
        final_result: Final grading result from evaluator
        iteration_stats: Statistics from the iteration run
        session_id: Unique session identifier
        converged: Whether the pipeline converged
        reason: Reason for termination
        feedback_for_generator: Actionable feedback when quality gate fails
    """

    final_artifact: Any
    final_result: GradingResult
    iteration_stats: IterationStats
    session_id: str
    converged: bool
    reason: str
    feedback_for_generator: dict | None = None


@dataclass
class RoundResult:
    """Result from a single round of refinement.

    Attributes:
        round_number: Current round number (1-indexed)
        artifact: Artifact after this round
        grading_result: Grading result from evaluator
        should_continue: Whether to continue refinement
        trend: Score trend direction ("improving", "declining", "stable")
    """

    round_number: int
    artifact: Any
    grading_result: GradingResult
    should_continue: bool
    trend: str = "stable"


# Module-level decision logger instance
_decision_logger = DecisionLogger()


class RefinementPipeline:
    """Multi-round refinement pipeline per GE-03.

    Orchestrates the generator-evaluator loop with quality gate enforcement:
    - Uses IterationController for loop control and convergence detection
    - Uses FeedbackBridge for generator-evaluator communication
    - Enforces configurable quality gate threshold
    - Supports early termination on quality threshold or convergence
    - Logs decisions and trace entries for debugging replay

    Args:
        generator: The generator agent (main agent) that produces artifacts
        evaluator: EvaluatorAgent instance for grading artifacts
        controller: IterationController instance (created if None)
        bridge: FeedbackBridge instance (created if None)
        quality_gate: Minimum score threshold (0-100) to pass quality gate
    """

    def __init__(
        self,
        generator: Any,  # The generator agent (main agent)
        evaluator: EvaluatorAgent,
        controller: IterationController | None = None,
        bridge: FeedbackBridge | None = None,
        quality_gate: float = 80.0,  # Minimum score to pass
    ):
        self.generator = generator
        self.evaluator = evaluator
        self.controller = controller or IterationController(
            evaluator, max_iterations=5, quality_gate=quality_gate
        )
        self.bridge = bridge or FeedbackBridge()
        self.quality_gate = quality_gate
        self._metrics = HarnessMetrics()

    def refine(
        self,
        initial_artifact: Any,
        task_description: str,
        artifact_type: str = "code",
    ) -> RefinementResult:
        """Run multi-round refinement.

        Args:
            initial_artifact: Starting point from generator
            task_description: What the artifact should do
            artifact_type: Type for evaluator context

        Returns:
            RefinementResult with final artifact, grading, and stats
        """
        session_id = str(uuid.uuid4())
        current_artifact = initial_artifact

        # Run iteration loop via controller
        result, stats = self.controller.run(current_artifact)

        # Log trace entry with decisions at iteration boundaries
        self._log_iteration_trace(session_id, current_artifact, result, stats)

        # Quality gate enforcement
        if result.score < self.quality_gate:
            # Generate actionable feedback for generator
            actionable_feedback = self._generate_feedback(result)

            return RefinementResult(
                final_artifact=current_artifact,
                final_result=result,
                iteration_stats=stats,
                session_id=session_id,
                converged=False,
                reason="quality_gate_failed",
                feedback_for_generator=actionable_feedback,
            )

        return RefinementResult(
            final_artifact=current_artifact,
            final_result=result,
            iteration_stats=stats,
            session_id=session_id,
            converged=stats.converged,
            reason=stats.reason,
        )

    def run_round(
        self,
        artifact: Any,
        round_number: int,
        session_id: str,
        artifact_type: str = "code",
    ) -> RoundResult:
        """Run a single round of evaluation and get result.

        Args:
            artifact: The artifact to evaluate
            round_number: Current round number (1-indexed)
            session_id: Unique session identifier
            artifact_type: Type of artifact for context

        Returns:
            RoundResult with evaluation and continuation decision
        """
        # Use bridge to send for evaluation
        grading_result = self.bridge.send_for_evaluation(
            artifact=artifact,
            evaluator=self.evaluator,
            session_id=session_id,
            iteration=round_number,
            artifact_type=artifact_type,
        )

        # Determine if should continue
        should_continue = self.should_terminate(grading_result) is False

        # Get score trend from controller
        # Build temporary stats for trend calculation
        temp_stats = IterationStats(iteration=round_number, score_history=[grading_result.score])
        trend = self.controller.get_score_trend(temp_stats)

        return RoundResult(
            round_number=round_number,
            artifact=artifact,
            grading_result=grading_result,
            should_continue=should_continue,
            trend=trend,
        )

    def evaluate_output(self, artifact: Any, context: dict | None = None) -> GradingResult:
        """Evaluate an artifact and return grading result.

        Args:
            artifact: The artifact to evaluate
            context: Optional context for evaluation

        Returns:
            GradingResult from evaluator
        """
        return self.evaluator.evaluate(artifact, context)

    def should_terminate(self, grading_result: GradingResult) -> bool:
        """Determine if pipeline should terminate based on grading result.

        Args:
            grading_result: Current grading result

        Returns:
            True if should terminate, False if should continue
        """
        # Quality gate check
        if grading_result.score >= self.quality_gate:
            return True

        # Check if score is too low to recover
        if grading_result.score < 20:
            return True

        return False

    def should_continue_refinement(self, stats: IterationStats) -> bool:
        """Check if refinement should continue based on stats.

        Args:
            stats: Current iteration statistics

        Returns:
            True if should continue, False otherwise
        """
        return self.controller.should_refine(stats)

    def get_score_trend(self, stats: IterationStats) -> str:
        """Get the trend direction of scores.

        Args:
            stats: Current iteration statistics

        Returns:
            "improving", "declining", or "stable"
        """
        return self.controller.get_score_trend(stats)

    def aggregate_scores(self, score_history: list[float]) -> dict:
        """Aggregate score history for analysis.

        Args:
            score_history: List of scores from iterations

        Returns:
            dict with aggregated metrics (avg, min, max, trend)
        """
        if not score_history:
            return {"avg": 0.0, "min": 0.0, "max": 0.0, "trend": "stable"}

        return {
            "avg": sum(score_history) / len(score_history),
            "min": min(score_history),
            "max": max(score_history),
            "trend": self.controller.get_score_trend(
                IterationStats(iteration=len(score_history), score_history=score_history)
            ),
        }

    def _generate_feedback(self, result: GradingResult) -> dict:
        """Generate structured feedback for generator.

        Returns:
            dict with specific issues and recommended fixes
        """
        return {
            "score": result.score,
            "threshold": self.quality_gate,
            "gap": self.quality_gate - result.score,
            "critical_issues": [
                issue for issue in result.issues if self._is_critical(issue)
            ],
            "recommended_fixes": [self._get_fix_suggestion(issue) for issue in result.issues],
            "iteration_guidance": self._get_iteration_guidance(result),
        }

    def _is_critical(self, issue: str) -> bool:
        """Determine if issue is critical severity."""
        critical_keywords = ["security", "crash", "data loss", "injection"]
        return any(kw in issue.lower() for kw in critical_keywords)

    def _get_fix_suggestion(self, issue: str) -> str:
        """Get specific fix suggestion for issue."""
        # Map issues to specific fixes
        return f"Fix required: {issue}"

    def _get_iteration_guidance(self, result: GradingResult) -> str:
        """Get guidance for next iteration."""
        return f"Focus on: {', '.join(result.issues[:3])}"

    def _log_iteration_trace(
        self,
        session_id: str,
        artifact: Any,
        result: GradingResult,
        stats: IterationStats,
    ) -> None:
        """Log a trace entry for the iteration.

        Creates a TraceEntry with decisions from quality gate and convergence.
        """
        decisions: list[DecisionPoint] = []

        # Quality gate decision
        quality_decision = DecisionPoint(
            decision_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            phase="iteration",
            decision_type="quality_gate",
            context={
                "scores": result.score,
                "threshold": self.quality_gate,
            },
            choice="pass" if result.score >= self.quality_gate else "fail",
            alternatives=["fail"] if result.score >= self.quality_gate else ["pass"],
            rationale=f"score {result.score} {'above' if result.score >= self.quality_gate else 'below'} threshold {self.quality_gate}",
            outcome="converged" if result.score >= self.quality_gate else "needs_refinement",
        )
        decisions.append(quality_decision)

        # Convergence decision
        convergence_decision = DecisionPoint(
            decision_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            phase="iteration",
            decision_type="convergence",
            context={
                "iteration_count": stats.iteration,
                "stability": self._compute_stability(stats),
            },
            choice="converged" if stats.converged else "continue",
            alternatives=["continue"] if stats.converged else ["converged"],
            rationale=f"iteration {stats.iteration}: {'converged' if stats.converged else 'not converged'}",
            outcome=stats.reason,
        )
        decisions.append(convergence_decision)

        # Create trace entry
        entry = TraceEntry(
            entry_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            step_number=stats.iteration,
            component="refinement_pipeline",
            action=f"iteration_{stats.iteration}_complete",
            inputs={"task_description": getattr(artifact, "__name__", str(artifact))},
            outputs={
                "score": result.score,
                "issues": result.issues,
            },
            decisions=decisions,
            metadata={
                "session_id": session_id,
                "reason": stats.reason,
            },
        )

        _decision_logger.log_trace_entry(entry, session_id)

    def _compute_stability(self, stats: IterationStats) -> str:
        """Compute stability description for convergence tracking."""
        if len(stats.score_history) < 2:
            return "insufficient_data"

        recent_scores = stats.score_history[-3:] if len(stats.score_history) >= 3 else stats.score_history
        if len(recent_scores) < 2:
            return "insufficient_data"

        score_diff = max(recent_scores) - min(recent_scores)
        if score_diff <= 0.05:
            return "stable"
        elif score_diff <= 0.15:
            return "moderately_changing"
        else:
            return "volatile"
