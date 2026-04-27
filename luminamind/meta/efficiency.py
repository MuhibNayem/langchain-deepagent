from dataclasses import dataclass
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from luminamind.streaming.reasoning_trace import ReasoningTrace


@dataclass
class TokenEfficiency:
    """Token usage efficiency metrics."""
    tokens_used: int
    theoretical_minimum: int
    efficiency_ratio: float  # theoretical / used
    wasted_tokens: int
    waste_categories: dict[str, int]  # category -> wasted tokens


class RedundancyDetector:
    """Detects redundant actions and patterns."""
    
    def __init__(self):
        self._patterns: dict[tuple, int] = {}  # pattern -> count
    
    def detect(self, trace: 'ReasoningTrace') -> List[str]:
        """Detect redundant actions in trace."""
        from luminamind.streaming.reasoning_trace import ReasoningStepType
        
        redundancies = []
        
        # Detect repeated patterns
        tool_sequence = self._get_tool_sequence(trace)
        for i in range(len(tool_sequence) - 1):
            pattern = tuple(tool_sequence[i:i+2])
            if pattern in self._patterns:
                redundancies.append(f"Repeated pattern: {pattern[0]} → {pattern[1]}")
            self._patterns[pattern] = self._patterns.get(pattern, 0) + 1
        
        # Detect retry patterns
        retries = self._detect_retries(trace)
        redundancies.extend(retries)
        
        return redundancies
    
    def _get_tool_sequence(self, trace: 'ReasoningTrace') -> list[str]:
        """Extract tool call sequence from trace."""
        from luminamind.streaming.reasoning_trace import ReasoningStepType
        return [
            s.content for s in trace.steps 
            if s.step_type == ReasoningStepType.ACT
        ]
    
    def _detect_retries(self, trace: 'ReasoningTrace') -> list[str]:
        """Detect tool call retries."""
        from luminamind.streaming.reasoning_trace import ReasoningStepType
        
        retries = []
        tool_attempts = {}
        
        for step in trace.steps:
            if step.step_type == ReasoningStepType.ACT:
                tool = step.content
                if tool in tool_attempts:
                    retries.append(f"Retry detected: {tool} called {tool_attempts[tool] + 1} times")
                tool_attempts[tool] = tool_attempts.get(tool, 0) + 1
        
        return retries
