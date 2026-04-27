"""Tool plugin interface for LuminaMind."""
from abc import ABC, abstractmethod
from typing import Dict, Any


class ToolPluginInterface(ABC):
    """Interface for custom tool plugins."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description."""
        pass

    @property
    @abstractmethod
    def input_schema(self) -> Dict[str, Any]:
        """JSON Schema for tool input."""
        pass

    @abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool with given arguments."""
        pass