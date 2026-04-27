from dataclasses import dataclass
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from luminamind.streaming.reasoning_trace import ReasoningTrace


@dataclass
class PathComparison:
    """Compare actual execution path to optimal path."""
    actual_path: list[str]  # Step IDs
    optimal_path: list[str]
    common_steps: list[str]  # Steps in both
    extra_steps: list[str]   # Steps only in actual
    missing_steps: list[str]  # Steps only in optimal
    similarity: float  # Jaccard similarity
    
    @property
    def efficiency(self) -> float:
        """Path efficiency as common / actual."""
        return len(self.common_steps) / max(len(self.actual_path), 1)


class StepAnalyzer:
    """Analyzes execution steps to find optimization opportunities."""
    
    def compare_paths(self, actual: list[str], optimal: list[str]) -> PathComparison:
        """Compare actual vs optimal execution path."""
        actual_set = set(actual)
        optimal_set = set(optimal)
        
        common = list(actual_set & optimal_set)
        extra = list(actual_set - optimal_set)
        missing = list(optimal_set - actual_set)
        
        similarity = len(common) / max(len(actual_set | optimal_set), 1)
        
        return PathComparison(
            actual_path=actual,
            optimal_path=optimal,
            common_steps=common,
            extra_steps=extra,
            missing_steps=missing,
            similarity=similarity
        )
    
    def find_shortcuts(self, trace: 'ReasoningTrace') -> list[list[str]]:
        """Find potential shortcuts through the execution.
        
        Returns paths that skip unnecessary steps.
        """
        # Build adjacency list
        graph = {}
        for step in trace.steps:
            if step.parent_step_id:
                if step.parent_step_id not in graph:
                    graph[step.parent_step_id] = []
                graph[step.parent_step_id].append(step.step_id)
        
        # Find all paths from root to leaves
        def all_paths(start: str, end: str) -> list[list[str]]:
            if start == end:
                return [[start]]
            
            if start not in graph:
                return []
            
            paths = []
            for child in graph.get(start, []):
                for path in all_paths(child, end):
                    paths.append([start] + path)
            return paths
        
        # Get root and leaves
        roots = [s for s in trace.steps if not s.parent_step_id]
        leaves = [s for s in trace.steps if not s.children]
        
        if not roots or not leaves:
            return []
        
        all_possible = all_paths(roots[0].step_id, leaves[0].step_id)
        
        # Return shortest path as optimal
        if all_possible:
            return [min(all_possible, key=len)]
        return []
