"""LLM factory functions for LuminaMind.

Provides LLM initialization with support for multiple providers:
- Z.AI (GLM) — OpenAI-compatible
- Kimi (Moonshot) — OpenAI-compatible
- MiniMax — OpenAI-compatible
- OpenAI — native
- Ollama local models

All providers are configured in parallel in the global .env file.
The active provider is selected via LUMINAMIND_ACTIVE_PROVIDER.

Multi-role support:
- Each agent role (planner, executor, evaluator, critic, orchestrator)
  can be assigned a different model via ModelRegistry.
- Registry provider names ("moonshot", "zhipu", "anthropic") are mapped
  to our canonical provider IDs ("kimi", "z.ai", etc.).
"""
from __future__ import annotations

import logging
import os
from typing import Any

from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

from luminamind.config.providers import (
    PROVIDER_SCHEMA,
    get_active_provider,
    _resolve_provider_id,
    get_provider_env_vars,
)

logger = logging.getLogger(__name__)

# Map registry/provider preset names → canonical provider IDs used by our config system
REGISTRY_PROVIDER_MAP = {
    "openai": "openai",
    "anthropic": "openai",  # Anthropic uses OpenAI-compatible base via proxy or fallback
    "zhipu": "z.ai",
    "glm": "z.ai",
    "moonshot": "kimi",
    "kimi": "kimi",
    "minimax": "minimax",
    "ollama": "ollama",
    "local": "ollama",
}


def _get_env(*keys: str) -> str | None:
    """Get first non-empty env var value."""
    for key in keys:
        val = os.environ.get(key)
        if val and val.strip():
            return val.strip()
    return None


def get_llm(
    provider: str | None = None,
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int | None = None,
) -> Any:
    """Get LLM instance based on provider configuration.

    Args:
        provider: Force a specific provider ("z.ai", "kimi", "minimax", "openai", "ollama").
                  If None, uses LUMINAMIND_ACTIVE_PROVIDER env var.
        model: Override the model for this call.
        temperature: Sampling temperature.
        max_tokens: Max output tokens.

    Returns:
        Configured LLM instance
    """
    # Resolve provider
    if provider:
        provider = _resolve_provider_id(provider)
    else:
        provider = get_active_provider() or "z.ai"

    kwargs: dict[str, Any] = {
        "temperature": temperature,
        "streaming": True,
    }
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens

    if provider == "ollama":
        return ChatOllama(
            model=model or _get_env("OLLAMA_MODEL") or "qwen3:latest",
            base_url=_get_env("OLLAMA_BASE_URL") or "http://localhost:11434",
            **kwargs,
        )

    # For OpenAI-compatible providers, look up their env vars
    if provider in PROVIDER_SCHEMA:
        schema = PROVIDER_SCHEMA[provider]
        api_key = _get_env(schema["api_key_env"])
        api_base = _get_env(schema["api_base_env"]) or schema["default_base"]
        resolved_model = model or _get_env(schema["model_env"]) or schema["default_model"]
    else:
        # Fallback to generic OpenAI env vars
        api_key = _get_env("OPENAI_API_KEY")
        api_base = _get_env("OPENAI_API_BASE") or "https://api.openai.com/v1"
        resolved_model = model or _get_env("OPENAI_MODEL") or "gpt-4o"

    return ChatOpenAI(
        model=resolved_model,
        openai_api_key=api_key,
        openai_api_base=api_base,
        max_retries=30,
        **kwargs,
    )


def get_llm_for_role(role: str, fallback_model: str | None = None) -> Any:
    """Get an LLM instance configured for a specific agent role.

    Reads the role's model mapping from ModelRegistry (~/.luminamind/models.yaml)
    and returns the appropriate LLM with provider, model, temperature, and
    max_tokens applied.

    Args:
        role: Agent role — "planner", "executor", "evaluator", "critic",
              "orchestrator", or any custom role.
        fallback_model: Model to use if registry lookup fails.

    Returns:
        Configured LLM instance (ChatOpenAI or ChatOllama)

    Example:
        >>> planner_llm = get_llm_for_role("planner")
        >>> executor_llm = get_llm_for_role("executor")
    """
    # Check runtime env overrides first: LUMINAMIND_ROLE_MODEL_PLANNER=kimi-k2.6
    override = _get_env(f"LUMINAMIND_ROLE_MODEL_{role.upper()}")
    if override:
        logger.debug(f"Role '{role}' using runtime override: {override}")
        return get_llm(model=override)

    try:
        from luminamind.models.registry import ModelRegistry, AgentRole

        registry = ModelRegistry()
        try:
            agent_role = AgentRole(role)
        except ValueError:
            # Unknown role — use active provider as last resort
            logger.debug(f"Unknown role '{role}', using active provider fallback")
            return get_llm(model=fallback_model)

        mapping = registry.get(agent_role)
        if not mapping or not mapping.enabled:
            mapping = registry.get_default_for_role(agent_role)

        # Map registry provider name → canonical provider ID
        canonical = REGISTRY_PROVIDER_MAP.get(mapping.provider.lower(), mapping.provider.lower())

        # If the mapped provider is not in our schema, try generic OpenAI credentials
        if canonical not in PROVIDER_SCHEMA:
            logger.debug(
                f"Provider '{mapping.provider}' not in config schema, "
                f"using generic OpenAI-compatible credentials with model '{mapping.model}'"
            )
            api_key = _get_env("OPENAI_API_KEY", "LLM_API_KEY")
            api_base = _get_env("OPENAI_API_BASE") or "https://api.openai.com/v1"
            kwargs: dict[str, Any] = {
                "temperature": mapping.temperature,
                "streaming": True,
            }
            if mapping.max_tokens is not None:
                kwargs["max_tokens"] = mapping.max_tokens
            return ChatOpenAI(
                model=mapping.model,
                openai_api_key=api_key,
                openai_api_base=api_base,
                max_retries=30,
                **kwargs,
            )

        schema = PROVIDER_SCHEMA[canonical]
        api_key = _get_env(schema["api_key_env"])

        # If no API key for this provider, try generic fallbacks before giving up
        if not api_key and canonical != "ollama":
            api_key = _get_env("OPENAI_API_KEY", "LLM_API_KEY")
            if api_key:
                logger.debug(f"Using generic API key for '{canonical}' (role={role})")

        api_base = _get_env(schema["api_base_env"]) or schema["default_base"]
        resolved_model = mapping.model

        kwargs = {
            "temperature": mapping.temperature,
            "streaming": True,
        }
        if mapping.max_tokens is not None:
            kwargs["max_tokens"] = mapping.max_tokens

        if canonical == "ollama":
            return ChatOllama(
                model=resolved_model,
                base_url=api_base,
                **kwargs,
            )

        return ChatOpenAI(
            model=resolved_model,
            openai_api_key=api_key,
            openai_api_base=api_base,
            max_retries=30,
            **kwargs,
        )

    except Exception as exc:
        logger.warning(f"Role model lookup failed for '{role}': {exc}. Using fallback.")
        return get_llm(model=fallback_model)


def list_available_providers() -> list[dict[str, str]]:
    """List all providers with their configuration status."""
    from luminamind.config.providers import read_provider_configs

    configs = read_provider_configs()
    active = get_active_provider()
    result = []

    for pid, schema in PROVIDER_SCHEMA.items():
        cfg = configs.get(pid, {})
        result.append({
            "id": pid,
            "display_name": schema["display_name"],
            "configured": pid in configs,
            "active": pid == active,
            "model": cfg.get("model", schema["default_model"]),
            "api_base": cfg.get("api_base", schema["default_base"]),
        })

    return result
