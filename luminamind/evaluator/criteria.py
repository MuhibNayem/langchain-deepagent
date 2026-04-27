"""GradingCriteria framework for domain-specific evaluation."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class GradingCriteria(ABC):
    """Base class for domain-specific grading criteria.

    Each criteria class evaluates artifacts within a specific domain
    (design, code, craft, originality) and returns structured scoring.
    """

    @abstractmethod
    def evaluate(self, artifact: Any) -> dict:
        """Evaluate artifact, return dict with:
        - score: float (0-100)
        - issues: list[str]
        - strengths: list[str]
        - recommendations: list[str]
        """
        pass

    @property
    @abstractmethod
    def domain(self) -> str:
        """Domain name: design, code, craft, originality."""
        pass

    @property
    def weight(self) -> float:
        """Default weight for this criteria domain."""
        return 1.0

    def grade(self, artifact: Any) -> dict:
        """Alias for evaluate() for semantic consistency."""
        return self.evaluate(artifact)

    def get_criteria(self) -> list[str]:
        """Return list of criteria names this domain evaluates."""
        return []


class DesignCriteria(GradingCriteria):
    """Design quality evaluation (visual quality, layout, UX patterns).

    GE-05: visual quality scoring
    """

    domain = "design"

    def evaluate(self, artifact: Any) -> dict:
        """Evaluate design quality."""
        issues = []
        strengths = []
        recommendations = []
        score = 100.0

        artifact_str = str(artifact).lower()

        # Check for basic structure indicators
        if len(str(artifact)) < 10:
            issues.append("Artifact too short to evaluate design quality")
            score -= 30

        # Check for common design pattern keywords
        design_keywords = ["layout", "style", "color", "font", "button", "input", "form"]
        if not any(kw in artifact_str for kw in design_keywords):
            issues.append("No recognizable design patterns detected")
            score -= 20

        # Check for accessibility considerations
        accessibility_keywords = ["alt", "aria", "label", "contrast"]
        if any(kw in artifact_str for kw in accessibility_keywords):
            strengths.append("Contains accessibility considerations")
        else:
            recommendations.append("Consider adding accessibility attributes (alt, aria-label)")

        # Check for visual hierarchy
        if any(kw in artifact_str for kw in ["header", "footer", "nav", "main", "section"]):
            strengths.append("Contains semantic HTML structure")
        else:
            recommendations.append("Consider adding semantic structure (header, main, footer)")

        score = max(0.0, min(100.0, score))
        return {
            "score": score,
            "issues": issues,
            "strengths": strengths,
            "recommendations": recommendations,
            "domain": self.domain,
        }

    def get_criteria(self) -> list[str]:
        """Design evaluation criteria."""
        return ["visual_quality", "layout", "ux_patterns", "accessibility"]


class CodeCriteria(GradingCriteria):
    """Code quality evaluation (correctness, maintainability, performance, security).

    GE-06: correctness, maintainability, performance, security
    """

    domain = "code"

    def evaluate(self, artifact: Any) -> dict:
        """Evaluate code quality."""
        issues = []
        strengths = []
        recommendations = []
        score = 100.0

        artifact_str = str(artifact)

        # Check for basic Python syntax indicators
        if "def " in artifact_str:
            # Function-based code
            if ":" not in artifact_str:
                issues.append("Missing colons in function definitions")
                score -= 15

            # Check for proper indentation indicators (PEP8)
            lines = artifact_str.split("\n")
            if any(line.startswith(" ") or line.startswith("\t") for line in lines if line.strip()):
                strengths.append("Uses indentation for code blocks")

            # Check for docstrings
            if '"""' in artifact_str or "'''" in artifact_str:
                strengths.append("Contains docstrings")
            else:
                recommendations.append("Consider adding docstrings to functions")

        # Check for common code quality issues
        code_smells = [
            ("x=1", "hardcoded value"),
            ("global ", "use of global variable"),
            ("except:", "bare except clause"),
        ]

        for pattern, smell in code_smells:
            if pattern in artifact_str:
                issues.append(f"Code smell: {smell}")
                score -= 10

        # Check for security concerns
        security_issues = [
            ("eval(", "use of eval() is a security risk"),
            ("exec(", "use of exec() is a security risk"),
            ("password", "hardcoded password detected"),
            ("api_key", "hardcoded API key detected"),
        ]

        for pattern, issue in security_issues:
            if pattern in artifact_str:
                issues.append(f"Security: {issue}")
                score -= 20

        # Check for type hints
        if "->" in artifact_str or ":" in artifact_str:
            if "types" in artifact_str or "typing" in artifact_str:
                strengths.append("Uses type hints")

        # Check for comments
        if "#" in artifact_str:
            strengths.append("Contains comments")

        score = max(0.0, min(100.0, score))
        return {
            "score": score,
            "issues": issues,
            "strengths": strengths,
            "recommendations": recommendations,
            "domain": self.domain,
        }

    def get_criteria(self) -> list[str]:
        """Code evaluation criteria."""
        return ["correctness", "maintainability", "performance", "security"]


class CraftCriteria(GradingCriteria):
    """Craft evaluation: naming, documentation, code organization.

    GE-04: craft domain evaluation
    """

    domain = "craft"

    def evaluate(self, artifact: Any) -> dict:
        """Evaluate code craft."""
        issues = []
        strengths = []
        recommendations = []
        score = 100.0

        artifact_str = str(artifact)

        # Check for proper naming conventions
        if "def " in artifact_str:
            import re

            # Extract function names
            func_pattern = r"def\s+([a-zA-Z_][a-zA-Z0-9_]*)\("
            functions = re.findall(func_pattern, artifact_str)

            for func_name in functions:
                if not func_name.islower():
                    issues.append(f"Function '{func_name}' should use snake_case")
                    score -= 5

            if functions:
                strengths.append(f"Found {len(functions)} function definition(s)")

        # Check for consistent indentation
        lines = artifact_str.split("\n")
        indented_lines = [l for l in lines if l.startswith((" ", "\t"))]
        if indented_lines:
            # Check for mixed indentation
            has_spaces = any(l.startswith(" ") for l in indented_lines)
            has_tabs = any(l.startswith("\t") for l in indented_lines)
            if has_spaces and has_tabs:
                issues.append("Mixed spaces and tabs detected")
                score -= 15

        # Check for documentation
        if '"""' in artifact_str or "'''" in artifact_str:
            strengths.append("Contains multi-line docstrings")
        elif "#" in artifact_str:
            recommendations.append("Consider adding docstrings for public APIs")

        # Check for line length (rough estimate)
        long_lines = [l for l in lines if len(l) > 120]
        if long_lines:
            recommendations.append(f"Consider breaking lines over 120 characters ({len(long_lines)} found)")
            score -= 5

        # Check for meaningful code structure
        if "\n\n" in artifact_str:
            strengths.append("Uses blank lines for visual separation")
        elif len(lines) > 10:
            recommendations.append("Consider using blank lines to separate logical sections")

        score = max(0.0, min(100.0, score))
        return {
            "score": score,
            "issues": issues,
            "strengths": strengths,
            "recommendations": recommendations,
            "domain": self.domain,
        }

    def get_criteria(self) -> list[str]:
        """Craft evaluation criteria."""
        return ["naming", "documentation", "code_organization", "readability"]


class OriginalityCriteria(GradingCriteria):
    """Originality evaluation: innovation, uniqueness, problem approach.

    GE-04: originality domain evaluation
    """

    domain = "originality"

    def evaluate(self, artifact: Any) -> dict:
        """Evaluate originality and innovation."""
        issues = []
        strengths = []
        recommendations = []
        score = 70.0  # Default lower - originality is harder to assess

        artifact_str = str(artifact)

        # Check for generic patterns (lower score)
        generic_patterns = [
            "hello world",
            "TODO",
            "FIXME",
            "placeholder",
            "not implemented",
        ]

        for pattern in generic_patterns:
            if pattern.lower() in artifact_str.lower():
                issues.append(f"Contains generic pattern: '{pattern}'")
                score -= 15

        # Check for evidence of thoughtful approach
        thoughtful_indicators = [
            "optimize",
            "efficient",
            "algorithm",
            "strategy",
            "approach",
        ]

        found_thoughtful = [kw for kw in thoughtful_indicators if kw in artifact_str.lower()]
        if found_thoughtful:
            strengths.append(f"Shows evidence of thoughtful approach: {found_thoughtful}")
            score += 10

        # Check for unique problem-solving language
        solution_keywords = [
            "implement",
            "solve",
            "resolve",
            "create",
            "build",
        ]

        found_solution = [kw for kw in solution_keywords if kw in artifact_str.lower()]
        if found_solution:
            strengths.append(f"Demonstrates solution-oriented language: {found_solution}")
            score += 5

        # Length consideration
        if len(artifact_str) > 500:
            strengths.append("Substantial implementation suggests depth")
            score += 10

        score = max(0.0, min(100.0, score))
        return {
            "score": score,
            "issues": issues,
            "strengths": strengths,
            "recommendations": recommendations,
            "domain": self.domain,
        }

    def get_criteria(self) -> list[str]:
        """Originality evaluation criteria."""
        return ["innovation", "uniqueness", "problem_approach"]
