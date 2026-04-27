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
    max_tokens: int = 4000
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
                max_tokens=mapping.get('max_tokens', 4000),
                enabled=mapping.get('enabled', True)
            )

    def _create_default(self) -> None:
        """Create default configuration."""
        defaults = {
            AgentRole.PLANNER: RoleModelMapping(AgentRole.PLANNER, "openai", "gpt-4o", 0.7, 4000),
            AgentRole.EXECUTOR: RoleModelMapping(AgentRole.EXECUTOR, "anthropic", "claude-3-haiku", 0.5, 2000),
            AgentRole.EVALUATOR: RoleModelMapping(AgentRole.EVALUATOR, "openai", "gpt-4o-mini", 0.3, 1000),
            AgentRole.CRITIC: RoleModelMapping(AgentRole.CRITIC, "anthropic", "claude-3-haiku", 0.3, 500),
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
        """Get mapping for role, falling back to executor defaults."""
        mapping = self.get(role)
        if mapping and mapping.enabled:
            return mapping
        return RoleModelMapping(
            role=role,
            provider="openai",
            model="gpt-4o-mini",
            temperature=0.5,
            max_tokens=2000,
            enabled=True
        )