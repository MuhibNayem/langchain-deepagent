"""BoundedSubagent with context inheritance boundaries and recursion depth limiting.

Per MULTI-01: Ensures subagents respect context limits with configurable depth
and inheritance boundaries.
"""
from dataclasses import dataclass, field
from enum import Enum


class CutoffStrategy(Enum):
    """Strategy for handling context when limits are exceeded."""
    TRUNCATE = "truncate"  # Truncate oldest messages
    SUMMARIZE = "summarize"  # Summarize old messages
    REJECT = "reject"  # Reject subagent creation


class RecursionLimitExceeded(Exception):
    """Raised when subagent recursion depth exceeds limit."""
    pass


class ContextBoundaryViolation(Exception):
    """Raised when subagent attempts to exceed context boundaries."""
    pass


@dataclass
class ContextBoundary:
    """Defines context inheritance boundaries for subagents."""
    max_tokens: int = 100000
    max_depth: int = 3  # Max subagent nesting depth
    inherit_depth: int = 2  # How many levels of parent context to inherit
    cutoff_strategy: CutoffStrategy = CutoffStrategy.TRUNCATE
    inherited_context_keys: list[str] = field(default_factory=list)  # Specific keys to inherit

    def check_depth(self, current_depth: int) -> None:
        """Check if current depth is within limits.

        Args:
            current_depth: The current recursion depth

        Raises:
            RecursionLimitExceeded: If current_depth >= max_depth
        """
        if current_depth >= self.max_depth:
            raise RecursionLimitExceeded(
                f"Depth {current_depth} exceeds max_depth {self.max_depth}"
            )

    def get_inherited_context(self, parent_context: dict, current_depth: int) -> dict:
        """Extract context to inherit based on boundary rules.

        Args:
            parent_context: The parent agent's context
            current_depth: Current recursion depth

        Returns:
            Filtered context dict with only allowed keys up to inherit_depth
        """
        if current_depth >= self.inherit_depth:
            # Too deep - no more context inheritance
            return {}

        inherited = {}
        for key in self.inherited_context_keys:
            if key in parent_context:
                inherited[key] = parent_context[key]

        return inherited


class BoundedSubagent:
    """Subagent with context inheritance and depth limit enforcement.

    Per MULTI-01: BoundedSubagent enforces context inheritance with boundaries,
    configurable recursion depth limits, respects parent context cutoff, and
    provides clean termination on boundary violation.
    """

    def __init__(
        self,
        name: str,
        system_prompt: str,
        tools: list = None,
        boundary: ContextBoundary | None = None,
        parent_context: dict | None = None,
        current_depth: int = 0,
        subagents: list = None,
        interrupt_on: list = None,
    ):
        """Initialize bounded subagent.

        Args:
            name: Subagent name
            system_prompt: System prompt for the agent
            tools: List of tools available to the agent
            boundary: Context boundary settings
            parent_context: Parent agent's context for inheritance
            current_depth: Current recursion depth
            subagents: List of child subagent configs
            interrupt_on: List of interrupt triggers
        """
        self.name = name
        self.system_prompt = system_prompt
        self.tools = tools or []
        self.boundary = boundary or ContextBoundary()
        self.parent_context = parent_context or {}
        self.current_depth = current_depth
        self.subagents = subagents or []
        self.interrupt_on = interrupt_on or []

        # Check depth before creation
        self.boundary.check_depth(self.current_depth)

        # Build inherited context
        self.context = self.boundary.get_inherited_context(
            self.parent_context, self.current_depth
        )

        # Import here to avoid circular dependency
        from luminamind.llm import get_llm

        # Create agent
        self.model = get_llm()

        # Build agent kwargs - only include interrupt_on if non-empty
        agent_kwargs = {
            "model": self.model,
            "tools": self.tools,
            "system_prompt": self.system_prompt,
            "subagents": self._create_bounded_subagents(),
        }
        if self.interrupt_on:
            agent_kwargs["interrupt_on"] = self.interrupt_on

        self.agent = create_deep_agent(**agent_kwargs)

    def _create_bounded_subagents(self) -> list:
        """Create bounded child subagents for this subagent."""
        bounded = []
        for subagent in self.subagents:
            bounded.append(BoundedSubagent(
                name=subagent["name"],
                system_prompt=subagent["system_prompt"],
                tools=subagent.get("tools", []),
                boundary=self.boundary,
                parent_context=self.context,
                current_depth=self.current_depth + 1,
                subagents=subagent.get("subagents", []),
                interrupt_on=subagent.get("interrupt_on", []),
            ))
        return bounded

    def invoke(self, input_text: str) -> dict:
        """Invoke agent with context enforcement.

        Args:
            input_text: Input text for the agent

        Returns:
            Agent response dict

        Raises:
            ContextBoundaryViolation: If REJECT strategy and input exceeds limit
        """
        # Check context size before invocation
        context_tokens = self._estimate_tokens(str(self.context) + input_text)
        if context_tokens > self.boundary.max_tokens:
            if self.boundary.cutoff_strategy == CutoffStrategy.REJECT:
                raise ContextBoundaryViolation(
                    f"Input exceeds max_tokens {self.boundary.max_tokens}"
                )
            elif self.boundary.cutoff_strategy == CutoffStrategy.TRUNCATE:
                input_text = self._truncate_input(input_text)
            elif self.boundary.cutoff_strategy == CutoffStrategy.SUMMARIZE:
                input_text = self._summarize_input(input_text)

        return self.agent.invoke(input_text)

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimate (4 chars per token)."""
        return len(text) // 4

    def _truncate_input(self, input_text: str) -> str:
        """Truncate input to fit within max_tokens."""
        max_chars = self.boundary.max_tokens * 4
        if len(input_text) > max_chars:
            return input_text[:max_chars] + "\n[TRUNCATED]"
        return input_text

    def _summarize_input(self, input_text: str) -> str:
        """Summarize input using LLM when available."""
        # For now, truncate - full summarization would use LLM
        return self._truncate_input(input_text)