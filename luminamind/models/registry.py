"""Per-role model registry for LuminaMind."""
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from enum import Enum
import yaml


class AgentRole(Enum):
    """Agent roles that can have different model configurations."""
    PLANNER = "planner"
    EXECUTOR = "executor"
    EVALUATOR = "evaluator"
    CRITIC = "critic"
    ORCHESTRATOR = "orchestrator"


@dataclass
class RoleModelMapping:
    """Maps an agent role to a specific model."""
    role: AgentRole
    provider: str  # e.g., "openai", "anthropic"
    model: str     # e.g., "gpt-4o", "claude-3-5-sonnet"
    temperature: float = 0.7
    max_tokens: int | None = None
    enabled: bool = True


@dataclass
class ProviderConfig:
    """Configuration for an LLM provider."""
    name: str
    api_key_env: str  # Environment variable containing API key
    base_url: Optional[str] = None
    default_model: Optional[str] = None
    enabled: bool = True


class ModelRegistry:
    """Registry for per-role model configuration."""

    def __init__(self, config_path: Path = Path("~/.luminamind/models.yaml")):
        self.config_path = Path(config_path).expanduser()
        self._mappings: dict[AgentRole, RoleModelMapping] = {}
        self._load()

    def _load(self) -> None:
        """Load from YAML config."""
        if not self.config_path.exists():
            self._create_default()
            return

        with open(self.config_path) as f:
            data = yaml.safe_load(f)

        for role_str, mapping in data.get('role_mappings', {}).items():
            role = AgentRole(role_str)
            self._mappings[role] = RoleModelMapping(
                role=role,
                provider=mapping['provider'],
                model=mapping['model'],
                temperature=mapping.get('temperature', 0.7),
                max_tokens=mapping.get('max_tokens'),
                enabled=mapping.get('enabled', True)
            )

        # Migration: if orchestrator is missing, this is an old config — regenerate
        if AgentRole.ORCHESTRATOR not in self._mappings:
            self._create_default()

    def _create_default(self) -> None:
        """Create default configuration.

        Defaults tuned for cost-effectiveness with the user's provider portfolio:
        - Planner: kimi-k2.6 (strong reasoning, unlimited tokens)
        - Executor: glm-4.7-flash (free tier, fast, unlimited tokens)
        - Evaluator: MiniMax-M2.7 (good quality, unlimited tokens)
        - Critic: glm-4.7-flash (free tier, 15k token budget for long critiques)
        """
        defaults = {
            AgentRole.PLANNER: RoleModelMapping(AgentRole.PLANNER, "moonshot", "kimi-k2.6", 0.7, None),
            AgentRole.EXECUTOR: RoleModelMapping(AgentRole.EXECUTOR, "zhipu", "glm-4.7-flash", 0.5, None),
            AgentRole.EVALUATOR: RoleModelMapping(AgentRole.EVALUATOR, "minimax", "MiniMax-M2.7", 0.3, None),
            AgentRole.CRITIC: RoleModelMapping(AgentRole.CRITIC, "zhipu", "glm-4.7-flash", 0.3, 15000),
            AgentRole.ORCHESTRATOR: RoleModelMapping(AgentRole.ORCHESTRATOR, "zhipu", "glm-4.7-flash", 0.7, None),
        }

        for role, mapping in defaults.items():
            self._mappings[role] = mapping

        self._save()

    def _save(self) -> None:
        """Save to YAML config."""
        data = {
            'role_mappings': {
                role.value: {
                    'provider': m.provider,
                    'model': m.model,
                    'temperature': m.temperature,
                    'max_tokens': m.max_tokens,
                    'enabled': m.enabled
                }
                for role, m in self._mappings.items()
            }
        }

        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False)

    def get(self, role: AgentRole) -> RoleModelMapping | None:
        """Get model mapping for role."""
        return self._mappings.get(role)

    def set(self, role: AgentRole, mapping: RoleModelMapping) -> None:
        """Set model mapping for role."""
        self._mappings[role] = mapping
        self._save()

    def list_all(self) -> List[RoleModelMapping]:
        """List all role mappings."""
        return list(self._mappings.values())

    def get_default_for_role(self, role: AgentRole) -> RoleModelMapping:
        """Get mapping for role, falling back to sensible defaults."""
        mapping = self.get(role)
        if mapping and mapping.enabled:
            return mapping
        # Fallback defaults mirror the primary defaults
        fallbacks = {
            AgentRole.PLANNER: ("moonshot", "kimi-k2.6", 0.7, None),
            AgentRole.EXECUTOR: ("zhipu", "glm-4.7-flash", 0.5, None),
            AgentRole.EVALUATOR: ("minimax", "MiniMax-M2.7", 0.3, None),
            AgentRole.CRITIC: ("zhipu", "glm-4.7-flash", 0.3, 15000),
            AgentRole.ORCHESTRATOR: ("zhipu", "glm-4.7-flash", 0.7, None),
        }
        provider, model, temp, max_tok = fallbacks.get(role, ("zhipu", "glm-4.7-flash", 0.5, None))
        return RoleModelMapping(
            role=role,
            provider=provider,
            model=model,
            temperature=temp,
            max_tokens=max_tok,
            enabled=True,
        )