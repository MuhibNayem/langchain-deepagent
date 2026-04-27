"""LLM factory functions for LuminaMind.

Provides LLM initialization with support for multiple providers:
- OpenAI-compatible (GLM, etc.)
- Ollama local models
"""
from __future__ import annotations

import os
from typing import Any

from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI


def get_llm(provider: str | None = None) -> Any:
    """Get LLM instance based on provider configuration.

    Args:
        provider: Force a specific provider ("openai", "ollama"). If None, uses LLM_PROVIDER env var.

    Returns:
        Configured LLM instance
    """
    provider = provider or os.environ.get("LLM_PROVIDER", "openai").lower()

    if provider == "ollama":
        return ChatOllama(
            model=os.environ.get("OLLAMA_MODEL", "qwen3:latest"),
            base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
            temperature=0.7,
            streaming=True,
        )

    api_key = os.environ.get("GLM_API_KEY")
    api_base = os.environ.get("GLM_API_BASE", "https://api.z.ai/api/paas/v4/")

    return ChatOpenAI(
        temperature=0.7,
        model="glm-4.5-flash",
        openai_api_key=api_key,
        openai_api_base=api_base,
        max_retries=30,
        streaming=True,
    )
