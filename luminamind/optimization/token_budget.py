"""Token budget allocation based on task complexity.

Per phase 06-05: Token usage optimization with smart context window allocation.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Any
import tiktoken


class TaskComplexity(Enum):
    """Task complexity levels for budget allocation.

    - SIMPLE: Single task, few tools
    - MODERATE: Multi-step, some tools
    - COMPLEX: Complex workflow, many tools
    - CRITICAL: High-stakes, requires careful reasoning
    """
    SIMPLE = 1
    MODERATE = 2
    COMPLEX = 3
    CRITICAL = 4


@dataclass
class BudgetAllocation:
    """Token budget allocation for a task.

    Attributes:
        total_budget: Total context window size
        system_tokens: Tokens allocated for system prompt
        task_tokens: Tokens allocated for task description
        history_tokens: Tokens allocated for conversation history
        available_tokens: What remains for agent response
        compression_ratio: How much to compress if needed (1.0 = no compression)
    """
    total_budget: int
    system_tokens: int
    task_tokens: int
    history_tokens: int
    available_tokens: int
    compression_ratio: float = 1.0


@dataclass
class TokenBudget:
    """Manages token budget allocation based on task complexity.

    Usage:
        tb = TokenBudget()
        alloc = tb.allocate(
            task_description="Write a REST API",
            system_prompt="You are a helpful assistant",
            history_text="Previous conversation...",
            tool_count=5,
            steps=8
        )
        print(f"Available: {alloc.available_tokens} tokens")
    """

    model: str = "gpt-4"
    max_context: int = 128000

    def __post_init__(self):
        try:
            self.encoder = tiktoken.encoding_for_model(self.model)
        except Exception:
            self.encoder = tiktoken.get_encoding("cl100k_base")

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text.

        Args:
            text: Text to estimate tokens for

        Returns:
            Number of tokens
        """
        return len(self.encoder.encode(text))

    def calculate_complexity(
        self,
        task_description: str,
        tool_count: int = 0,
        steps: int = 0
    ) -> TaskComplexity:
        """Determine task complexity based on characteristics.

        Args:
            task_description: Description of the task
            tool_count: Number of tools involved
            steps: Number of steps expected

        Returns:
            TaskComplexity level
        """
        complexity_score = 1

        # Length-based scoring
        if len(task_description) > 500:
            complexity_score += 1
        if len(task_description) > 2000:
            complexity_score += 1

        # Tool usage scoring
        if tool_count > 5:
            complexity_score += 1
        if tool_count > 10:
            complexity_score += 1

        # Step-based scoring
        if steps > 3:
            complexity_score += 1
        if steps > 10:
            complexity_score += 1

        # Map to complexity enum
        if complexity_score <= 2:
            return TaskComplexity.SIMPLE
        elif complexity_score <= 4:
            return TaskComplexity.MODERATE
        elif complexity_score <= 6:
            return TaskComplexity.COMPLEX
        else:
            return TaskComplexity.CRITICAL

    def allocate(
        self,
        task_description: str,
        system_prompt: str,
        history_text: str = "",
        tool_count: int = 0,
        steps: int = 0
    ) -> BudgetAllocation:
        """Allocate tokens based on task complexity.

        Args:
            task_description: Description of the task
            system_prompt: System prompt text
            history_text: Conversation history text
            tool_count: Number of tools involved
            steps: Number of steps expected

        Returns:
            BudgetAllocation with per-component token counts
        """
        complexity = self.calculate_complexity(task_description, tool_count, steps)

        system_tokens = self.estimate_tokens(system_prompt)
        task_tokens = self.estimate_tokens(task_description)
        history_tokens = self.estimate_tokens(history_text)

        # Complexity-based allocation multipliers
        complexity_multipliers = {
            TaskComplexity.SIMPLE: 0.15,    # 15% for history
            TaskComplexity.MODERATE: 0.25,   # 25% for history
            TaskComplexity.COMPLEX: 0.35,    # 35% for history
            TaskComplexity.CRITICAL: 0.40,  # 40% for history
        }

        history_ratio = complexity_multipliers[complexity]

        # Calculate actual allocations
        # Reserve for system + task
        reserved = system_tokens + task_tokens + 1000  # 1000 buffer
        available = self.max_context - reserved

        history_alloc = min(
            int(available * history_ratio),
            history_tokens  # Don't allocate more than we have
        )

        remaining = available - history_alloc

        return BudgetAllocation(
            total_budget=self.max_context,
            system_tokens=system_tokens,
            task_tokens=task_tokens,
            history_tokens=history_alloc,
            available_tokens=remaining,
            compression_ratio=1.0 if remaining > 8000 else 0.7
        )

    def get_compression_needed(
        self,
        allocation: BudgetAllocation,
        current_usage: int
    ) -> float:
        """Calculate compression ratio if over budget.

        Args:
            allocation: Budget allocation to check against
            current_usage: Current token usage

        Returns:
            Compression ratio (1.0 = no compression needed)
        """
        if current_usage <= allocation.available_tokens:
            return 1.0  # No compression needed
        return allocation.available_tokens / max(current_usage, 1)


__all__ = ["TokenBudget", "BudgetAllocation", "TaskComplexity"]