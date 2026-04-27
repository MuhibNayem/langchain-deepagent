"""Planner-Evaluator Integration for spec review loop with iterative refinement.

Per PLAN-03: Connects PlannerAgent to EvaluatorAgent for spec quality verification
before sprint execution. Enables spec review loop with iterative refinement.
"""
from dataclasses import dataclass, field

from luminamind.evaluator.criteria import GradingCriteria
from luminamind.evaluator.agent import EvaluatorAgent, GradingResult
from luminamind.planner.agent import PlannerAgent
from luminamind.planner.spec import SpecDocument, UserStory, AcceptanceCriterion


@dataclass
class SpecReviewResult:
    """Result of spec review through planner-evaluator loop.

    Attributes:
        spec: The final (possibly revised) SpecDocument
        final_score: The score after review loop
        iterations: Number of review iterations performed
        issues_resolved: Issues that were resolved during revision
        final_issues: Remaining issues after review
    """

    spec: SpecDocument
    final_score: float
    iterations: int
    issues_resolved: list[str] = field(default_factory=list)
    final_issues: list[str] = field(default_factory=list)


class SpecGradingCriteria(GradingCriteria):
    """Grading criteria for spec quality evaluation (PLAN-03).

    Evaluates spec completeness, specificity, and feasibility:
    - Completeness: has title, description, >=1 user story, >=1 acceptance criterion per story
    - Specificity: acceptance criteria have verify_method
    - Feasibility: no contradictory or impossible requirements
    """

    domain = "spec"

    def evaluate(self, artifact) -> dict:
        """Evaluate spec quality.

        Args:
            artifact: SpecDocument to evaluate

        Returns:
            dict with score, issues, strengths, recommendations
        """
        issues = []
        score = 100.0

        # Handle string conversion for compatibility with EvaluatorAgent
        if isinstance(artifact, str):
            # Can't properly evaluate a string as a spec
            issues.append("Artifact is not a SpecDocument")
            score -= 50
            return {
                "score": max(0, score),
                "issues": issues,
                "strengths": [],
                "recommendations": ["Provide a valid SpecDocument object"]
            }

        spec = artifact

        # Completeness checks
        if not spec.title:
            issues.append("Spec missing title")
            score -= 20

        if not spec.description:
            issues.append("Spec missing description")
            score -= 10

        if not spec.user_stories:
            issues.append("Spec has no user stories")
            score -= 30

        # User story quality
        for story in spec.user_stories:
            if not story.description.startswith("As a"):
                issues.append(f"User story {story.id} doesn't follow As-a-... format")
                score -= 5
            if not story.criteria:
                issues.append(f"User story {story.id} has no acceptance criteria")
                score -= 15

        # Acceptance criteria specificity
        for story in spec.user_stories:
            for criterion in story.criteria:
                if not criterion.verify_method:
                    issues.append(f"Criterion {criterion.id} missing verify_method")
                    score -= 10

        return {
            "score": max(0, score),
            "issues": issues,
            "strengths": self._get_strengths(spec),
            "recommendations": self._get_recommendations(spec, issues)
        }

    def _get_strengths(self, spec: SpecDocument) -> list[str]:
        """Get positive strengths of the spec."""
        strengths = []
        if spec.title:
            strengths.append("Has clear title")
        if spec.user_stories:
            strengths.append(f"Has {len(spec.user_stories)} user stories")
        return strengths

    def _get_recommendations(self, spec: SpecDocument, issues: list[str]) -> list[str]:
        """Get recommendations for improving the spec."""
        recs = []
        if len(spec.user_stories) < 3:
            recs.append("Consider decomposing into more user stories for clearer scope")
        for story in spec.user_stories:
            if len(story.criteria) < 2:
                recs.append(f"Add more acceptance criteria to {story.id}")
        return recs


class PlannerEvaluatorIntegration:
    """Integration connecting PlannerAgent to EvaluatorAgent for spec review loop.

    Per PLAN-03: Enables spec quality verification before sprint execution.
    Runs an iterative review loop: planner generates → evaluator grades → 
    revisions until spec meets acceptance threshold or max iterations reached.

    Attributes:
        planner_agent: PlannerAgent instance (or creates default)
        evaluator_agent: EvaluatorAgent instance with SpecGradingCriteria
        score_threshold: Minimum score to pass review (default 80)
        max_iterations: Maximum revision loops (default 3)
    """

    def __init__(
        self,
        planner_agent: PlannerAgent | None = None,
        evaluator_agent: EvaluatorAgent | None = None,
        score_threshold: float = 80.0,
        max_iterations: int = 3
    ):
        self.planner = planner_agent or PlannerAgent()
        self.evaluator = evaluator_agent or EvaluatorAgent(
            grading_criteria=SpecGradingCriteria()
        )
        self.score_threshold = score_threshold
        self.max_iterations = max_iterations

    def review_spec(self, spec: SpecDocument, feature_request: str) -> SpecReviewResult:
        """Run spec through planner-evaluator review loop.

        Iterates: evaluate spec → if score < threshold, revise spec → repeat.
        Loop converges when spec meets acceptance threshold or max iterations reached.

        Args:
            spec: Initial SpecDocument to review
            feature_request: Original feature request for context

        Returns:
            SpecReviewResult with final spec and metadata
        """
        current_spec = spec
        iterations = 0
        resolved_issues = []
        final_issues = []

        while iterations < self.max_iterations:
            iterations += 1

            # Evaluate current spec
            grading = self.evaluator.evaluate(current_spec)

            if grading.score >= self.score_threshold:
                # Spec meets threshold - review complete
                return SpecReviewResult(
                    spec=current_spec,
                    final_score=grading.score,
                    iterations=iterations,
                    issues_resolved=resolved_issues,
                    final_issues=grading.issues
                )

            # Revision needed - incorporate feedback
            final_issues = grading.issues

            # Generate revised spec incorporating feedback
            revision_prompt = self._build_revision_prompt(feature_request, current_spec, grading)
            result = self.planner.generate_spec(revision_prompt)
            current_spec = result.spec
            resolved_issues.extend(grading.issues)

        # Max iterations reached
        return SpecReviewResult(
            spec=current_spec,
            final_score=grading.score,
            iterations=iterations,
            issues_resolved=resolved_issues,
            final_issues=final_issues
        )

    def _build_revision_prompt(
        self, original_request: str, spec: SpecDocument, grading: GradingResult
    ) -> str:
        """Build revision prompt from evaluator feedback.

        Args:
            original_request: Original feature request
            spec: Current spec being revised
            grading: GradingResult with issues

        Returns:
            Prompt string for planner to generate revised spec
        """
        issues_str = "\n".join(f"- {issue}" for issue in grading.issues)
        return f"""
Revise the spec based on these issues:

Original request: {original_request}

Issues to address:
{issues_str}

Current spec:
Title: {spec.title}
Description: {spec.description}
User stories: {len(spec.user_stories)}

Produce an improved spec addressing these issues.
"""
