from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Any
import re


@dataclass
class EscalationRule:
    """A rule determining when an operation requires approval."""
    name: str
    description: str
    condition: Callable[[dict[str, Any]], bool]  # Returns True if escalation needed
    priority: int = 0  # Higher = more urgent
    enabled: bool = True


class ApprovalPolicies:
    """Registry of escalation rules for approval workflow."""

    def __init__(self):
        self._rules: list[EscalationRule] = []
        self._setup_default_rules()

    def _setup_default_rules(self):
        """Set up default escalation rules."""
        # High-value operations
        self.add_rule(EscalationRule(
            name="file_delete",
            description="File deletion operations",
            condition=lambda ctx: ctx.get("operation_type") == "file_delete",
            priority=10,
        ))

        self.add_rule(EscalationRule(
            name="code_execution",
            description="Code execution in sandbox",
            condition=lambda ctx: ctx.get("operation_type") == "code_execution",
            priority=5,
        ))

        self.add_rule(EscalationRule(
            name="api_call_external",
            description="External API calls",
            condition=lambda ctx: ctx.get("operation_type") == "api_call" and ctx.get("external", False),
            priority=7,
        ))

        # Low evaluator score — escalate for human review
        self.add_rule(EscalationRule(
            name="low_quality_score",
            description="Low evaluator score — needs human review",
            condition=lambda ctx: (
                ctx.get("evaluator_score", 1.0) < 0.5 and
                ctx.get("iteration_count", 0) >= 3
            ),
            priority=8,
        ))

        # Pattern-based rules
        self.add_rule(EscalationRule(
            name="sensitive_file_modification",
            description="Modifications to sensitive files",
            condition=lambda ctx: bool(re.search(
                r"(password|secret|key|credential|\.env|config\.yaml)",
                ctx.get("file_path", "")
            )),
            priority=9,
        ))

    def add_rule(self, rule: EscalationRule):
        """Register a new escalation rule."""
        self._rules.append(rule)
        self._rules.sort(key=lambda r: r.priority, reverse=True)

    def should_escalate(self, context: dict[str, Any]) -> list[EscalationRule]:
        """Check which rules match the given context.

        Returns list of matching escalation rules, sorted by priority.
        """
        matching = []
        for rule in self._rules:
            if rule.enabled:
                try:
                    if rule.condition(context):
                        matching.append(rule)
                except Exception:
                    pass  # Skip rules that error
        return matching

    def get_escalation_priority(self, context: dict[str, Any]) -> int:
        """Get highest priority escalation for given context."""
        matching = self.should_escalate(context)
        return matching[0].priority if matching else 0
