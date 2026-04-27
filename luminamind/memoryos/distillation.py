from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class DistilledKnowledge:
    """Distilled knowledge from task execution."""
    pattern_id: str
    pattern_type: str  # "success", "failure", "optimization"
    description: str
    code_snippet: str | None = None
    trigger_conditions: list[str] = None
    confidence: float = 0.5
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.trigger_conditions is None:
            self.trigger_conditions = []


class KnowledgeDistiller:
    """Distills knowledge from task executions into reusable patterns."""
    
    def __init__(self):
        self._patterns: list[DistilledKnowledge] = []
    
    def distill(self, task_result: Any) -> list[DistilledKnowledge]:
        """Extract distilled knowledge from task result.
        
        Args:
            task_result: Task result containing patterns, decisions, lessons
            
        Returns:
            List of distilled knowledge entries
        """
        patterns = []
        
        # Extract patterns if available
        if hasattr(task_result, 'patterns'):
            for i, pattern in enumerate(task_result.patterns):
                patterns.append(DistilledKnowledge(
                    pattern_id=f"pattern-{id(task_result)}-{i}",
                    pattern_type="success",
                    description=pattern if isinstance(pattern, str) else str(pattern),
                    confidence=0.7
                ))
        
        # Extract decisions if available
        if hasattr(task_result, 'decisions'):
            for decision in task_result.decisions:
                patterns.append(DistilledKnowledge(
                    pattern_id=f"decision-{id(task_result)}-{len(patterns)}",
                    pattern_type="optimization",
                    description=decision if isinstance(decision, str) else str(decision),
                    confidence=0.6
                ))
        
        # Extract lessons if available
        if hasattr(task_result, 'lessons'):
            for lesson in task_result.lessons:
                patterns.append(DistilledKnowledge(
                    pattern_id=f"lesson-{id(task_result)}-{len(patterns)}",
                    pattern_type="optimization",
                    description=lesson if isinstance(lesson, str) else str(lesson),
                    confidence=0.5
                ))
        
        self._patterns.extend(patterns)
        return patterns
    
    def get_relevant_patterns(self, context: dict, min_confidence: float = 0.5) -> list[DistilledKnowledge]:
        """Get patterns relevant to the given context."""
        relevant = []
        for pattern in self._patterns:
            if pattern.confidence >= min_confidence:
                relevant.append(pattern)
        return sorted(relevant, key=lambda p: p.confidence, reverse=True)
