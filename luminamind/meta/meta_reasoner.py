from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from luminamind.learning.skill_library import SkillLibrary
    from luminamind.learning.skill_acquirer import AtomicSkill
    from luminamind.streaming.reasoning_trace import ReasoningTrace


@dataclass
class SelfReview:
    """Post-task self-review result."""
    review_id: str
    task_id: str
    agent_id: str
    timestamp: datetime
    actual_steps: int
    optimal_steps: int
    step_ratio: float  # actual / optimal
    token_efficiency: float  # tokens used vs theoretical minimum
    redundant_actions: list[str]
    suggested_optimizations: list[str]
    confidence: float  # How confident is the review
    approved: bool = False  # Self-approved or needs human review


@dataclass
class OptimizationSuggestion:
    """A suggested optimization."""
    suggestion_id: str
    category: str  # "step_reduction", "token_optimization", "pattern_change"
    description: str
    expected_improvement: str  # e.g., "50% fewer steps"
    effort: str  # "low", "medium", "high"
    risk: str  # "low", "medium", "high"


class MetaReasoner:
    """Recursive meta-reasoning: self-review and optimization suggestions.
    
    Triggered after task completion, asks "how could this be solved with
    50% fewer steps?" and proposes optimizations.
    """
    
    def __init__(self, skill_library: 'SkillLibrary' = None):
        self.skill_library = skill_library
        self._review_history: list[SelfReview] = []
    
    async def review(self, task_id: str, agent_id: str,
                    execution_trace: 'ReasoningTrace',
                    token_usage: int) -> SelfReview:
        """Perform self-review of task execution.
        
        Analyzes:
        1. Actual steps vs. optimal path
        2. Token efficiency
        3. Redundant actions
        4. Pattern improvements
        """
        from luminamind.streaming.reasoning_trace import ReasoningStepType
        
        review = SelfReview(
            review_id=f"review-{task_id}-{len(self._review_history)}",
            task_id=task_id,
            agent_id=agent_id,
            timestamp=datetime.utcnow(),
            actual_steps=len(execution_trace.steps),
            optimal_steps=self._estimate_optimal_steps(execution_trace),
            step_ratio=0,
            token_efficiency=0,
            redundant_actions=[],
            suggested_optimizations=[],
            confidence=0.5
        )
        
        # Calculate step ratio
        review.step_ratio = review.actual_steps / max(review.optimal_steps, 1)
        
        # Calculate token efficiency
        theoretical_min = review.optimal_steps * 50  # ~50 tokens per step minimum
        review.token_efficiency = theoretical_min / max(token_usage, 1)
        
        # Find redundant actions
        review.redundant_actions = self._find_redundant_actions(execution_trace)
        
        # Generate optimizations
        review.suggested_optimizations = self._generate_optimizations(review)
        
        # Calculate confidence
        review.confidence = self._calculate_confidence(review)
        
        self._review_history.append(review)
        return review
    
    def _estimate_optimal_steps(self, trace: 'ReasoningTrace') -> int:
        """Estimate optimal number of steps for this trace."""
        # Simple heuristic: minimum path through the trace
        path = trace.get_path()
        return max(len(path), 1)
    
    def _find_redundant_actions(self, trace: 'ReasoningTrace') -> list[str]:
        """Find redundant or unnecessary actions."""
        from luminamind.streaming.reasoning_trace import ReasoningStepType
        
        redundant = []
        
        # Look for repeated tool calls with same input
        tool_calls = {}
        for step in trace.steps:
            if step.step_type == ReasoningStepType.ACT:
                key = f"{step.content}"
                if key in tool_calls:
                    redundant.append(f"Repeated action: {key[:50]}")
                tool_calls[key] = step.step_id
        
        # Look for excessive observation steps
        observe_count = sum(1 for s in trace.steps if s.step_type == ReasoningStepType.OBSERVE)
        if observe_count > trace.get_path().__len__() * 2:
            redundant.append(f"Excessive observation: {observe_count} observes vs ~{trace.get_path().__len__()} optimal")
        
        return redundant
    
    def _generate_optimizations(self, review: SelfReview) -> list[str]:
        """Generate optimization suggestions."""
        suggestions = []
        
        if review.step_ratio > 1.5:
            suggestions.append(f"Could reduce from {review.actual_steps} to ~{review.optimal_steps} steps ({(1 - 1/review.step_ratio)*100:.0f}% reduction)")
        
        if review.token_efficiency < 0.3:
            suggestions.append("Token efficiency is low - consider more concise prompting")
        
        if review.redundant_actions:
            suggestions.append(f"Found {len(review.redundant_actions)} redundant actions that could be eliminated")
        
        return suggestions
    
    def _calculate_confidence(self, review: SelfReview) -> float:
        """Calculate confidence in the review."""
        confidence = 0.5
        
        # Higher confidence if we have similar past reviews
        similar = sum(1 for r in self._review_history 
                     if r.task_id != review.task_id and 
                     abs(r.optimal_steps - review.optimal_steps) < 3)
        confidence += min(similar * 0.1, 0.3)
        
        # Lower confidence if large discrepancy
        if review.step_ratio > 3:
            confidence -= 0.2
        
        return max(0.1, min(0.95, confidence))
    
    async def apply_optimization(self, review: SelfReview, 
                                skill_library: 'SkillLibrary') -> bool:
        """Apply review suggestions to skill library.
        
        Creates or updates a skill with the optimization.
        """
        if not self.skill_library:
            return False
        
        from luminamind.learning.skill_acquirer import AtomicSkill
        
        for suggestion in review.suggested_optimizations:
            # Create atomic skill from optimization
            skill = AtomicSkill(
                id=f"opt-{review.task_id}-{len(self._review_history)}",
                name=f"Optimization: {suggestion[:30]}",
                description=suggestion,
                trigger_conditions=[f"task_type:{review.task_id}"],
                actions=[],
                success_rate=review.confidence,
                avg_tokens_saved=int((1 - review.token_efficiency) * 1000),
                version=1,
                created_at=datetime.utcnow(),
                last_used=datetime.utcnow()
            )
            
            self.skill_library.register(skill)
        
        return True
