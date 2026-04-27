"""Evaluator plugin interface for LuminaMind."""
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from luminamind.evaluator.criteria import GradingCriteria
    from luminamind.evaluator.pipeline import EvaluationContext, EvaluationResult


class EvaluatorPluginInterface(ABC):
    """Interface for custom evaluator plugins."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin name."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Plugin description."""
        pass

    @abstractmethod
    def get_criteria(self) -> List['GradingCriteria']:
        """Return list of evaluation criteria this plugin provides."""
        pass

    @abstractmethod
    def evaluate(self, artifact: 'Artifact', context: 'EvaluationContext') -> 'EvaluationResult':
        """Evaluate an artifact using this plugin's criteria."""
        pass