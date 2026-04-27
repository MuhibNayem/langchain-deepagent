"""Per-model token pricing database for cost tracking.

Prices in USD per 1M tokens (input / output).
Updated 2026-04-27. Supports OpenAI, Anthropic, Google, GLM/Z.AI, Kimi, MiniMax, Ollama (free).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ModelPricing:
    """Pricing for a specific model variant."""

    model_id: str
    input_per_1m: float
    output_per_1m: float
    provider: str
    currency: str = "USD"

    def calculate(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate total cost in USD."""
        input_cost = (input_tokens / 1_000_000) * self.input_per_1m
        output_cost = (output_tokens / 1_000_000) * self.output_per_1m
        return round(input_cost + output_cost, 6)


# Enterprise pricing database (2026-04-27)
_PRICING_DB: dict[str, ModelPricing] = {
    # OpenAI
    "gpt-4.5": ModelPricing("gpt-4.5", 75.00, 150.00, "openai"),
    "gpt-4.5-preview": ModelPricing("gpt-4.5-preview", 75.00, 150.00, "openai"),
    "gpt-4o": ModelPricing("gpt-4o", 2.50, 10.00, "openai"),
    "gpt-4o-mini": ModelPricing("gpt-4o-mini", 0.15, 0.60, "openai"),
    "o3-mini": ModelPricing("o3-mini", 1.10, 4.40, "openai"),
    "o1": ModelPricing("o1", 15.00, 60.00, "openai"),
    "o1-mini": ModelPricing("o1-mini", 1.10, 4.40, "openai"),
    "text-embedding-3-small": ModelPricing("text-embedding-3-small", 0.02, 0.00, "openai"),
    "text-embedding-3-large": ModelPricing("text-embedding-3-large", 0.13, 0.00, "openai"),
    # Anthropic
    "claude-opus-4": ModelPricing("claude-opus-4", 15.00, 75.00, "anthropic"),
    "claude-sonnet-4": ModelPricing("claude-sonnet-4", 3.00, 15.00, "anthropic"),
    "claude-haiku-4": ModelPricing("claude-haiku-4", 0.25, 1.25, "anthropic"),
    "claude-3-7-sonnet-latest": ModelPricing("claude-3-7-sonnet-latest", 3.00, 15.00, "anthropic"),
    # Google
    "gemini-2.5-pro": ModelPricing("gemini-2.5-pro", 1.25, 10.00, "google"),
    "gemini-2.5-flash": ModelPricing("gemini-2.5-flash", 0.15, 0.60, "google"),
    # Z.AI / GLM
    "glm-4.7-flash": ModelPricing("glm-4.7-flash", 0.06, 0.40, "z.ai"),
    "glm-4.7": ModelPricing("glm-4.7", 0.60, 2.20, "z.ai"),
    "glm-4.5-flash": ModelPricing("glm-4.5-flash", 0.50, 2.00, "z.ai"),
    "glm-4.5": ModelPricing("glm-4.5", 2.00, 8.00, "z.ai"),
    "glm-4": ModelPricing("glm-4", 1.00, 4.00, "z.ai"),
    "glm-5": ModelPricing("glm-5", 0.72, 2.30, "z.ai"),
    # Kimi / Moonshot
    "kimi-k2.6": ModelPricing("kimi-k2.6", 0.60, 3.00, "kimi"),
    "kimi-k2.5": ModelPricing("kimi-k2.5", 0.60, 3.00, "kimi"),
    "kimi-k2-0905-preview": ModelPricing("kimi-k2-0905-preview", 0.60, 3.00, "kimi"),
    "kimi-k2-turbo-preview": ModelPricing("kimi-k2-turbo-preview", 0.30, 1.50, "kimi"),
    "kimi-k2-thinking": ModelPricing("kimi-k2-thinking", 0.60, 3.00, "kimi"),
    "moonshot-v1-8k": ModelPricing("moonshot-v1-8k", 0.10, 0.50, "kimi"),
    "moonshot-v1-32k": ModelPricing("moonshot-v1-32k", 0.20, 1.00, "kimi"),
    "moonshot-v1-128k": ModelPricing("moonshot-v1-128k", 0.30, 1.50, "kimi"),
    # MiniMax
    "minimax-m2.7": ModelPricing("minimax-m2.7", 0.80, 2.40, "minimax"),
    "minimax-m2.7-highspeed": ModelPricing("minimax-m2.7-highspeed", 1.20, 3.60, "minimax"),
    "minimax-m2.5": ModelPricing("minimax-m2.5", 0.60, 1.80, "minimax"),
    "minimax-m2.5-highspeed": ModelPricing("minimax-m2.5-highspeed", 0.90, 2.70, "minimax"),
    "minimax-m2.1": ModelPricing("minimax-m2.1", 0.40, 1.20, "minimax"),
    "minimax-m2.1-highspeed": ModelPricing("minimax-m2.1-highspeed", 0.60, 1.80, "minimax"),
    "minimax-m2": ModelPricing("minimax-m2", 0.30, 0.90, "minimax"),
    # Local / Free
    "llama3": ModelPricing("llama3", 0.0, 0.0, "ollama"),
    "llama3.1": ModelPricing("llama3.1", 0.0, 0.0, "ollama"),
    "llama3.2": ModelPricing("llama3.2", 0.0, 0.0, "ollama"),
    "llama3.3": ModelPricing("llama3.3", 0.0, 0.0, "ollama"),
    "mistral": ModelPricing("mistral", 0.0, 0.0, "ollama"),
    "qwen2.5": ModelPricing("qwen2.5", 0.0, 0.0, "ollama"),
    "deepseek-r1": ModelPricing("deepseek-r1", 0.0, 0.0, "ollama"),
    "deepseek-v3": ModelPricing("deepseek-v3", 0.0, 0.0, "ollama"),
}


def get_pricing(model_id: str) -> ModelPricing | None:
    """Get pricing for a model. Falls back to heuristic match."""
    if model_id in _PRICING_DB:
        return _PRICING_DB[model_id]
    # Heuristic: prefix match and normalized match
    normalized = model_id.lower().replace(" ", "-").replace("_", "-")
    for key in sorted(_PRICING_DB.keys(), key=len, reverse=True):
        if model_id.startswith(key) or key in model_id or key in normalized:
            return _PRICING_DB[key]
    # Default to cheap glm-4.7-flash equivalent if unknown
    return ModelPricing(model_id, 0.15, 0.60, "unknown")


def list_priced_models() -> list[ModelPricing]:
    return list(_PRICING_DB.values())
