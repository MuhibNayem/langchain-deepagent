"""EvaluatorAgent base class with LangGraph ReAct pattern.

Implements observe → reason → act → reflect loop for artifact evaluation.
Foundation for GAN-inspired dual-agent system where evaluator critiques generator output.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TypedDict

from langgraph.graph import StateGraph, END

from luminamind.deep_agent import get_llm
from luminamind.evaluator.live_verifier import LiveVerifier, VerificationConfig, LiveVerificationReport


@dataclass
class GradingResult:
    """Result of evaluating an artifact.

    Attributes:
        score: Overall score from 0-100
        issues: List of identified issues
        feedback: Actionable feedback for improvement
        iteration: Number of ReAct iterations used
    """

    score: float
    issues: list[str] = field(default_factory=list)
    feedback: str = ""
    iteration: int = 0


class EvaluatorState(TypedDict):
    """State for the EvaluatorAgent ReAct graph.

    Attributes:
        artifact: The artifact being evaluated
        context: Optional context for evaluation
        issues: Accumulated issues found so far
        score: Running score
        iteration: Current iteration count
        reasoning: Current reasoning trace
        done: Whether evaluation is complete
    """

    artifact: str
    context: dict | None
    issues: list[str]
    score: float
    iteration: int
    reasoning: str
    done: bool


class EvaluatorAgent:
    """Base EvaluatorAgent using LangGraph ReAct pattern.

    Implements a ReAct-style reasoning loop:
    1. OBSERVE: Load artifact and criteria
    2. REASON: Analyze artifact for issues
    3. ACT: Either continue reasoning or finalize
    4. REFLECT: Check if more iterations needed

    Args:
        model: LLM to use (uses get_llm() if None)
        grading_criteria: GradingCriteria instance for evaluation
        max_iterations: Maximum ReAct iterations before forcing completion
    """

    def __init__(
        self,
        model: Any | None = None,
        grading_criteria: Any | None = None,
        max_iterations: int = 5,
        live_verifier: LiveVerifier | None = None,
    ):
        self.model = model or get_llm()
        self.grading_criteria = grading_criteria
        self.max_iterations = max_iterations
        self.live_verifier = live_verifier
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Build the ReAct evaluation graph.

        Graph structure:
        evaluate_node → decision_node → [ END | continue to evaluate_node ]

        Returns:
            Compiled StateGraph for the ReAct loop
        """
        graph = StateGraph(EvaluatorState)

        # Add nodes
        graph.add_node("evaluate", self._evaluate_node)
        graph.add_node("decide", self._decision_node)

        # Set entry point
        graph.set_entry_point("evaluate")

        # Conditional edge: continue if not done and iterations remain
        def should_continue(state: EvaluatorState) -> str:
            if state.get("done", False):
                return END
            if state.get("iteration", 0) >= self.max_iterations:
                return END
            return "evaluate"

        graph.add_conditional_edges("decide", should_continue)
        graph.add_edge("evaluate", "decide")

        return graph.compile()

    def _evaluate_node(self, state: EvaluatorState) -> dict:
        """Evaluate node: analyze artifact for issues.

        Args:
            state: Current evaluation state

        Returns:
            Updated state with issues found and reasoning
        """
        artifact = state.get("artifact", "")
        context = state.get("context", {})
        current_issues = state.get("issues", [])
        current_score = state.get("score", 100.0)
        current_reasoning = state.get("reasoning", "")

        iteration = state.get("iteration", 0)
        new_issues = []
        reasoning = ""

        # Use grading criteria if available
        if self.grading_criteria is not None:
            result = self.grading_criteria.evaluate(artifact)
            new_issues = result.get("issues", [])
            current_score = result.get("score", current_score)
            reasoning = f"[Iteration {iteration + 1}] Evaluated using {self.grading_criteria.domain} criteria"
        else:
            # Basic evaluation heuristics
            reasoning = f"[Iteration {iteration + 1}] Performing basic evaluation"

            # Check for common issues
            if len(artifact) < 5:
                new_issues.append("Artifact is too short to evaluate properly")
                current_score -= 20

            if artifact.strip() == "":
                new_issues.append("Artifact is empty")
                current_score = 0

            # Check for placeholder patterns
            placeholder_patterns = ["TODO", "FIXME", "placeholder", "not implemented"]
            for pattern in placeholder_patterns:
                if pattern.lower() in artifact.lower():
                    new_issues.append(f"Contains placeholder: '{pattern}'")
                    current_score -= 10

            # Check for code-like content
            if "def " in artifact or "class " in artifact or "function" in artifact.lower():
                reasoning += "\n- Detected code content, applying code heuristics"
                if ";" in artifact and ":" not in artifact:
                    new_issues.append("Possible missing colons in code")
                    current_score -= 5

        # Bound score
        current_score = max(0.0, min(100.0, current_score))

        # Update reasoning
        if new_issues:
            reasoning += f"\n- Found issues: {', '.join(new_issues)}"
        else:
            reasoning += "\n- No new issues found"

        return {
            "issues": current_issues + new_issues,
            "score": current_score,
            "iteration": iteration + 1,
            "reasoning": current_reasoning + ("\n" if current_reasoning else "") + reasoning,
        }

    def _decision_node(self, state: EvaluatorState) -> dict:
        """Decision node: determine if more reasoning is needed.

        Args:
            state: Current evaluation state

        Returns:
            Updated state with done flag
        """
        issues = state.get("issues", [])
        iteration = state.get("iteration", 0)
        score = state.get("score", 100.0)

        # Decide if evaluation is complete
        done = False

        # If we've done enough iterations
        if iteration >= self.max_iterations:
            done = True

        # If score is very low (< 30) or very high (> 90), we can stop early
        if score < 30 or score > 90:
            done = True

        # If we found critical issues, might need more passes
        critical_threshold = 3
        if len(issues) >= critical_threshold:
            # Continue for more analysis unless at max iterations
            if iteration < self.max_iterations:
                done = False
            else:
                done = True

        return {"done": done}

    def evaluate(self, artifact: Any, context: dict | None = None) -> GradingResult:
        """Evaluate an artifact using the ReAct loop.

        Args:
            artifact: The artifact to evaluate (will be converted to string)
            context: Optional context dictionary with additional information

        Returns:
            GradingResult with score, issues, feedback, and iteration count
        """
        # Convert artifact to string for processing
        artifact_str = str(artifact)

        # Initialize state
        initial_state: EvaluatorState = {
            "artifact": artifact_str,
            "context": context,
            "issues": [],
            "score": 100.0,
            "iteration": 0,
            "reasoning": "",
            "done": False,
        }

        # Run the graph
        final_state = self.graph.invoke(initial_state)

        # Extract results
        issues = final_state.get("issues", [])
        score = final_state.get("score", 0.0)
        iteration = final_state.get("iteration", 0)
        reasoning = final_state.get("reasoning", "")

        # Generate feedback from reasoning and issues
        feedback = self._generate_feedback(issues, reasoning, score)

        return GradingResult(
            score=score,
            issues=issues,
            feedback=feedback,
            iteration=iteration,
        )

    def _generate_feedback(
        self, issues: list[str], reasoning: str, score: float
    ) -> str:
        """Generate actionable feedback from issues and reasoning.

        Args:
            issues: List of identified issues
            reasoning: Reasoning trace from ReAct loop
            score: Final score

        Returns:
            Human-readable feedback string
        """
        if not issues:
            return "No significant issues found. Artifact meets evaluation criteria."

        feedback_lines = []

        # Score summary
        if score >= 80:
            feedback_lines.append("Good overall quality with minor suggestions for improvement.")
        elif score >= 60:
            feedback_lines.append("Acceptable quality but several issues should be addressed.")
        elif score >= 40:
            feedback_lines.append("Quality needs improvement. Critical issues detected.")
        else:
            feedback_lines.append("Significant quality problems require immediate attention.")

        # Issue summary
        feedback_lines.append("")
        feedback_lines.append("Issues identified:")
        for i, issue in enumerate(issues, 1):
            feedback_lines.append(f"  {i}. {issue}")

        return "\n".join(feedback_lines)

    async def verify_live(self, artifact: Any, context: dict | None = None) -> LiveVerificationReport:
        """Run live verification on artifact.

        Args:
            artifact: The artifact to verify (code, UI, API, etc.)
            context: Optional context for verification

        Returns:
            LiveVerificationReport with verification results
        """
        if self.live_verifier is None:
            raise RuntimeError("LiveVerifier not configured")

        return await self.live_verifier.verify()

    def get_live_verifier(self) -> LiveVerifier | None:
        """Get the live verifier instance."""
        return self.live_verifier

    def critique(self, artifact: Any, context: dict | None = None) -> str:
        """Generate a text critique of the artifact.

        Args:
            artifact: The artifact to critique
            context: Optional context

        Returns:
            Text critique string
        """
        result = self.evaluate(artifact, context)
        return result.feedback

    def score(self, artifact: Any, context: dict | None = None) -> float:
        """Score an artifact.

        Args:
            artifact: The artifact to score
            context: Optional context

        Returns:
            Score from 0-100
        """
        result = self.evaluate(artifact, context)
        return result.score
