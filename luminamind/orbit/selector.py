from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING
from enum import Enum

if TYPE_CHECKING:
    from luminamind.orbit.cost_registry import ModelCostRegistry, ModelInfo


class TaskComplexity(Enum):
    SIMPLE = "simple"      # Quick tasks, simple operations
    MEDIUM = "medium"     # Standard tasks
    COMPLEX = "complex"    # Complex reasoning, multi-step


@dataclass
class SelectionCriteria:
    """Criteria for model selection."""
    min_quality: float = 0.5
    max_cost: float | None = None  # Max cost per task
    preferred_latency: str = "medium"  # low, medium, high
    required_capabilities: list[str] = field(default_factory=list)
    free_preferred: bool = False


class DynamicModelSelector:
    """Dynamically selects the best model for a task based on cost-quality tradeoff."""
    
    def __init__(self, registry: 'ModelCostRegistry'):
        self.registry = registry
    
    def classify_task(self, task_description: str, 
                     history: list = None) -> TaskComplexity:
        """Classify task complexity based on description and history.
        
        Heuristics:
        - "debug", "fix", "error" → complex
        - "write", "create", "generate" → medium
        - "list", "show", "get" → simple
        """
        task_lower = task_description.lower()
        
        complex_keywords = ["debug", "architect", "design", "analyze", "review", 
                          "optimize", "refactor", "security"]
        simple_keywords = ["list", "show", "get", "find", "search", "check"]
        
        if any(kw in task_lower for kw in complex_keywords):
            return TaskComplexity.COMPLEX
        if any(kw in task_lower for kw in simple_keywords):
            return TaskComplexity.SIMPLE
        return TaskComplexity.MEDIUM
    
    def select(self, task_description: str, criteria: SelectionCriteria,
              estimated_input_tokens: int = 1000,
              estimated_output_tokens: int = 500) -> tuple:
        """Select the best model for the task.
        
        Returns:
            (selected_model, reasoning)
        """
        from luminamind.orbit.cost_registry import ModelInfo
        
        complexity = self.classify_task(task_description)
        
        # Determine minimum quality threshold based on complexity
        min_quality = {
            TaskComplexity.SIMPLE: 0.5,
            TaskComplexity.MEDIUM: 0.7,
            TaskComplexity.COMPLEX: 0.85
        }[complexity]
        
        # Override if criteria specifies higher
        min_quality = max(min_quality, criteria.min_quality)
        
        # Get candidate models
        candidates = self.registry.list_models(min_quality=min_quality)
        
        if not candidates:
            return self.registry.get_by_name("openai/gpt-4o-mini"), "Fallback: no candidates meet criteria"
        
        # Filter by cost if specified
        if criteria.max_cost:
            candidates = [
                m for m in candidates
                if self.registry.estimate_cost(m, estimated_input_tokens, estimated_output_tokens) 
                <= criteria.max_cost
            ]
        
        if not candidates:
            return candidates[0], f"Warning: cost limit exceeded, using cheapest available"
        
        # Prefer free if available and criteria says so
        if criteria.free_preferred:
            free_candidates = [m for m in candidates if m.is_free]
            if free_candidates and free_candidates[0].quality_score >= min_quality:
                return free_candidates[0], f"Selected free model: {free_candidates[0].display_name}"
        
        # Select by quality-adjusted cost (cheapest for given quality)
        best = min(candidates, key=lambda m: m.input_price)
        
        reasoning = f"{complexity.value} task → min_quality={min_quality} → selected {best.display_name}"
        return best, reasoning
    
    def should_switch_model(self, current_model: 'ModelInfo', 
                          actual_complexity: TaskComplexity) -> tuple[bool, str]:
        """Determine if mid-task model switch is needed.
        
        Called when initial complexity estimate was wrong.
        """
        if actual_complexity == TaskComplexity.SIMPLE and \
           current_model.quality_score >= 0.85:
            return True, "Task simpler than expected, could use cheaper model"
        
        if actual_complexity == TaskComplexity.COMPLEX and \
           current_model.quality_score < 0.85:
            return True, "Task more complex than expected, should upgrade model"
        
        return False, ""
