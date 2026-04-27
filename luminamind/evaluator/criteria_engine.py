"""CriteriaEngine for domain-specific criteria management per GE-04.

Manages domain-specific criteria sets:
- design: FrontendEvaluator (visual quality)
- code: CodeEvaluator (correctness, maintainability, performance, security)
- craft: Code quality (naming, documentation)
- originality: Innovation assessment

Selects appropriate criteria based on artifact type.
Supports composite evaluation (multiple domains).
"""
from typing import Any

from luminamind.evaluator.criteria import (
    GradingCriteria,
    DesignCriteria,
    CodeCriteria,
    CraftCriteria,
    OriginalityCriteria,
)


class CriteriaNotFoundError(ValueError):
    """Raised when requested domain has no registered criteria."""
    pass


class CriteriaEngine:
    """Grading criteria engine per GE-04.

    Manages domain-specific criteria sets with selection and composite evaluation.
    """

    def __init__(self):
        self._criteria_registry: dict[str, GradingCriteria] = {}
        self._weights: dict[str, float] = {
            "design": 0.30,
            "code": 0.35,
            "craft": 0.15,
            "originality": 0.20,
        }
        self._load_default_criteria()

    def _load_default_criteria(self) -> None:
        """Load default criteria instances."""
        self._criteria_registry = {
            "design": DesignCriteria(),
            "code": CodeCriteria(),
            "craft": CraftCriteria(),
            "originality": OriginalityCriteria(),
        }

    def get_criteria(self, domain: str) -> GradingCriteria | None:
        """Get criteria for a specific domain.

        Args:
            domain: One of design, code, craft, originality

        Returns:
            GradingCriteria instance or None if not found
        """
        return self._criteria_registry.get(domain)

    def get_criteria_for_artifact(
        self,
        artifact_type: str,
        domains: list[str] | None = None,
    ) -> list[GradingCriteria]:
        """Get criteria appropriate for artifact type.

        Args:
            artifact_type: Type hint (code, frontend, spec, etc.)
            domains: Specific domains to use (default: inferred from type)

        Returns:
            List of GradingCriteria to apply
        """
        if domains:
            return [
                self._criteria_registry[d]
                for d in domains
                if d in self._criteria_registry
            ]

        # Infer domains from artifact type
        type_mapping = {
            "frontend": ["design"],
            "code": ["code", "craft"],
            "spec": ["originality"],
            "full": ["design", "code", "craft", "originality"],
        }

        selected_domains = type_mapping.get(artifact_type, ["code"])
        return [self._criteria_registry[d] for d in selected_domains]

    def register_criteria(self, domain: str, criteria: GradingCriteria) -> None:
        """Register custom criteria for a domain.

        Args:
            domain: Domain name
            criteria: GradingCriteria instance
        """
        self._criteria_registry[domain] = criteria

    def set_domain_weight(self, domain: str, weight: float) -> None:
        """Configure weight for a domain in composite scoring.

        Args:
            domain: Domain name
            weight: Weight (0.0 to 1.0)
        """
        self._weights[domain] = weight

    def get_available_domains(self) -> list[str]:
        """List all registered domains."""
        return list(self._criteria_registry.keys())

    def clear_criteria(self) -> None:
        """Clear all registered criteria."""
        self._criteria_registry.clear()

    def evaluate_composite(
        self,
        artifact: Any,
        domains: list[str] | None = None,
    ) -> dict:
        """Evaluate artifact using multiple criteria domains.

        Composite score = sum(domain_score * weight) / sum(weights)
        Default weights: design=0.30, code=0.35, craft=0.15, originality=0.20

        Args:
            artifact: Artifact to evaluate
            domains: Domains to evaluate (default: all registered)

        Returns:
            dict with per-domain results and composite score
        """
        if domains is None:
            domains = list(self._criteria_registry.keys())

        results = {}
        total_weighted_score = 0.0
        total_weight = 0.0

        for domain in domains:
            criteria = self._criteria_registry.get(domain)
            if criteria:
                domain_result = criteria.evaluate(artifact)
                results[domain] = domain_result
                weight = self._weights.get(domain, 0.25)
                total_weighted_score += domain_result.get("score", 0) * weight
                total_weight += weight

        # Normalize composite score by total weight
        if total_weight > 0:
            results["composite_score"] = total_weighted_score / total_weight
        else:
            results["composite_score"] = 0.0

        return results