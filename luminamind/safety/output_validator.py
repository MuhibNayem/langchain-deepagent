"""
Validator for checking execution results before returning to agent.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import re


@dataclass
class ValidationResult:
    """Result of output validation."""

    valid: bool
    issues: list[str]  # Empty if valid


class OutputValidator:
    """Validates execution outputs before returning to agent."""

    def __init__(
        self,
        max_output_lines: int = 10000,
        max_line_length: int = 10000,
        blocked_patterns: list[str] | None = None,
    ):
        self.max_output_lines = max_output_lines
        self.max_line_length = max_line_length
        self.blocked_patterns = blocked_patterns or [
            r"import\s+os\b",
            r"import\s+subprocess\b",
            r"import\s+sys\b",
            r"__import__\(",
            r"eval\s*\(",
            r"exec\s*\(",
            r"open\s*\(",
        ]

    def validate(self, output: str, context: dict[str, Any] | None = None) -> ValidationResult:
        """Validate output against safety rules.

        Args:
            output: The execution output to validate
            context: Optional context (code, language, etc.) for deeper validation
        """
        issues = []

        # Line count check
        lines = output.split("\n")
        if len(lines) > self.max_output_lines:
            issues.append(f"Output too long: {len(lines)} lines (max {self.max_output_lines})")

        # Line length check
        for i, line in enumerate(lines[:100]):  # Check first 100 lines only for perf
            if len(line) > self.max_line_length:
                issues.append(f"Line {i+1} too long: {len(line)} chars (max {self.max_line_length})")
                break

        # Pattern check for dangerous content
        for pattern in self.blocked_patterns:
            if re.search(pattern, output, re.IGNORECASE):
                issues.append(f"Output contains blocked pattern: {pattern}")

        return ValidationResult(valid=len(issues) == 0, issues=issues)

    def validate_json(self, output: str) -> ValidationResult:
        """Validate that output is valid JSON."""
        import json
        issues = []
        try:
            json.loads(output)
        except json.JSONDecodeError as e:
            issues.append(f"Invalid JSON: {e}")
        return ValidationResult(valid=len(issues) == 0, issues=issues)
