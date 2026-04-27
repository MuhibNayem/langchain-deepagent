from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from enum import Enum
import json


class Provider(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    GROQ = "groq"
    MINIMAX = "minimax"
    ZHIPU = "zhipu"
    MOONSHOT = "moonshot"
    OTHER = "other"


@dataclass
class ModelInfo:
    """Information about a model."""
    provider: Provider
    name: str  # e.g., "gpt-4o", "claude-3-opus"
    display_name: str
    input_price: float  # per 1M tokens
    output_price: float  # per 1M tokens
    context_window: int  # max tokens
    capabilities: list[str] = field(default_factory=list)  # "reasoning", "coding", "vision"
    quality_score: float = 0.5  # 0.0 - 1.0 relative quality
    latency_profile: str = "medium"  # "low", "medium", "high"
    is_free: bool = False


@dataclass
class ProviderConfig:
    """Configuration for a model provider."""
    provider: Provider
    base_url: str
    api_key_env: str  # Environment variable name for API key
    models: list[ModelInfo] = field(default_factory=list)
    enabled: bool = True


class ModelCostRegistry:
    """Registry of models with cost and capability information."""
    
    DEFAULT_MODELS = [
        # OpenAI
        ModelInfo(provider=Provider.OPENAI, name="gpt-4o", display_name="GPT-4o",
                 input_price=5.0, output_price=15.0, context_window=128000,
                 capabilities=["reasoning", "coding", "vision"], quality_score=0.9,
                 latency_profile="medium"),
        ModelInfo(provider=Provider.OPENAI, name="gpt-4o-mini", display_name="GPT-4o Mini",
                 input_price=0.15, output_price=0.60, context_window=128000,
                 capabilities=["reasoning", "coding"], quality_score=0.8,
                 latency_profile="low"),
        # Anthropic
        ModelInfo(provider=Provider.ANTHROPIC, name="claude-3-5-sonnet", 
                 display_name="Claude 3.5 Sonnet",
                 input_price=3.0, output_price=15.0, context_window=200000,
                 capabilities=["reasoning", "coding", "vision"], quality_score=0.92,
                 latency_profile="medium"),
        ModelInfo(provider=Provider.ANTHROPIC, name="claude-3-haiku", 
                 display_name="Claude 3 Haiku",
                 input_price=0.25, output_price=1.25, context_window=200000,
                 capabilities=["reasoning", "coding"], quality_score=0.75,
                 latency_profile="low"),
        # Free models
        ModelInfo(provider=Provider.ZHIPU, name="glm-4.7-flash", 
                 display_name="GLM-4.7-Flash (FREE)",
                 input_price=0.0, output_price=0.0, context_window=131072,
                 capabilities=["reasoning", "coding"], quality_score=0.7,
                 latency_profile="medium", is_free=True),
        # MiniMax
        ModelInfo(provider=Provider.MINIMAX, name="minimax/m2.7", 
                 display_name="MiniMax M2.7",
                 input_price=0.5, output_price=1.0, context_window=128000,
                 capabilities=["reasoning", "coding"], quality_score=0.82,
                 latency_profile="low"),
        # Moonshot
        ModelInfo(provider=Provider.MOONSHOT, name="moonshot/kimi-k2.6", 
                 display_name="Moonshot Kimi K2.6",
                 input_price=0.5, output_price=1.0, context_window=256000,
                 capabilities=["reasoning", "coding"], quality_score=0.85,
                 latency_profile="medium"),
    ]
    
    def __init__(self):
        self._providers: dict[Provider, ProviderConfig] = {}
        self._models: dict[str, ModelInfo] = {}  # key: "provider/model"
        
        # Register default models
        for model in self.DEFAULT_MODELS:
            self.register_model(model)
    
    def register_model(self, model: ModelInfo) -> None:
        """Register a model."""
        key = f"{model.provider.value}/{model.name}"
        self._models[key] = model
    
    def register_provider(self, config: ProviderConfig) -> None:
        """Register a provider configuration."""
        self._providers[config.provider] = config
        for model in config.models:
            self.register_model(model)
    
    def get_model(self, provider: Provider, name: str) -> ModelInfo | None:
        """Get model by provider and name."""
        key = f"{provider.value}/{name}"
        return self._models.get(key)
    
    def get_by_name(self, full_name: str) -> ModelInfo | None:
        """Get model by full name (provider/model)."""
        return self._models.get(full_name)
    
    def list_models(self, provider: Provider = None,
                   min_quality: float = None,
                   free_only: bool = False) -> list[ModelInfo]:
        """List models with optional filters."""
        models = list(self._models.values())
        
        if provider:
            models = [m for m in models if m.provider == provider]
        if min_quality:
            models = [m for m in models if m.quality_score >= min_quality]
        if free_only:
            models = [m for m in models if m.is_free]
        
        return sorted(models, key=lambda m: m.input_price)
    
    def estimate_cost(self, model: ModelInfo, input_tokens: int, 
                     output_tokens: int) -> float:
        """Estimate cost for a model with given token usage."""
        input_cost = (input_tokens / 1_000_000) * model.input_price
        output_cost = (output_tokens / 1_000_000) * model.output_price
        return input_cost + output_cost
    
    def get_cheapest(self, min_quality: float = 0.5) -> ModelInfo | None:
        """Get cheapest model meeting minimum quality threshold."""
        candidates = self.list_models(min_quality=min_quality)
        return candidates[0] if candidates else None
