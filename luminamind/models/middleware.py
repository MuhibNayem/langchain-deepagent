"""Model middleware for per-role model routing."""
from typing import TYPE_CHECKING, Optional, Tuple, Dict, Any

if TYPE_CHECKING:
    from luminamind.models.registry import AgentRole, ModelRegistry, RoleModelMapping
    from luminamind.orbit.selector import DynamicModelSelector


class RoleModelMiddleware:
    """Middleware that routes each role to its assigned model."""

    def __init__(self, registry: 'ModelRegistry', orbit_selector: 'DynamicModelSelector'):
        self.registry = registry
        self.orbit_selector = orbit_selector
        self._client = None  # LLM client instance

    def get_client_for_role(self, role: 'AgentRole') -> 'LLMClient':
        """Get configured LLM client for a role."""
        mapping = self.registry.get(role)
        if not mapping or not mapping.enabled:
            mapping = self.registry.get_default_for_role(role)

        return self._create_client(
            provider=mapping.provider,
            model=mapping.model,
            temperature=mapping.temperature,
            max_tokens=mapping.max_tokens
        )

    def _create_client(self, provider: str, model: str,
                      temperature: float, max_tokens: int) -> 'LLMClient':
        """Create LLM client for provider."""
        # Placeholder: This would integrate with the actual LLM client
        # e.g., from luminamind.llm import create_client
        pass

    def route(self, role: 'AgentRole', prompt: str, **kwargs) -> str:
        """Route a prompt to the appropriate model for role."""
        client = self.get_client_for_role(role)
        return client.complete(prompt, **kwargs)


class ModelRouter:
    """Routes requests to appropriate models based on role and task."""

    def __init__(self, registry: 'ModelRegistry', selector: 'DynamicModelSelector'):
        self.registry = registry
        self.selector = selector

    def route(self, role: 'AgentRole', task_description: str,
             **kwargs) -> Tuple[str, Dict[str, Any]]:
        """Route task to appropriate model.

        Returns:
            (model_key, kwargs_with_model)
        """
        mapping = self.registry.get(role)
        if not mapping:
            return "openai/gpt-4o-mini", kwargs

        # Check if we should use dynamic selection
        criteria = kwargs.pop('selection_criteria', None)
        if criteria:
            model, reasoning = self.selector.select(task_description, criteria)
            return f"{model.provider}/{model.name}", kwargs

        return f"{mapping.provider}/{mapping.model}", kwargs