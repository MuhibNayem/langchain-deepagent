"""Agent configuration per role for LuminaMind."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict
import yaml


@dataclass
class AgentConfig:
    """Configuration for an agent role."""
    role: str  # "planner", "executor", etc.
    system_prompt: str = ""
    criteria: List[str] = field(default_factory=list)
    tool_access: List[str] = field(default_factory=list)
    llm_params: Dict = field(default_factory=dict)
    limits: Dict = field(default_factory=dict)


class AgentConfigManager:
    """Manages agent configurations per role."""

    def __init__(self, base_path: Path = Path("~/.luminamind/config")):
        self.base_path = Path(base_path).expanduser()
        self.base_path.mkdir(parents=True, exist_ok=True)
        self._configs: Dict[str, AgentConfig] = {}
        self._load_all()

    def _load_all(self) -> None:
        """Load all agent configs from YAML."""
        config_file = self.base_path / "agent_config.yaml"
        if config_file.exists():
            with open(config_file) as f:
                data = yaml.safe_load(f)
            for role, cfg in data.get('agents', {}).items():
                self._configs[role] = AgentConfig(
                    role=role,
                    system_prompt=cfg.get('system_prompt', ''),
                    criteria=cfg.get('criteria', []),
                    tool_access=cfg.get('tool_access', []),
                    llm_params=cfg.get('llm_params', {}),
                    limits=cfg.get('limits', {}),
                )

    def _save_all(self) -> None:
        """Save all agent configs to YAML."""
        data = {
            'agents': {
                role: {
                    'system_prompt': cfg.system_prompt,
                    'criteria': cfg.criteria,
                    'tool_access': cfg.tool_access,
                    'llm_params': cfg.llm_params,
                    'limits': cfg.limits,
                }
                for role, cfg in self._configs.items()
            }
        }
        self.base_path.mkdir(parents=True, exist_ok=True)
        config_file = self.base_path / "agent_config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(data, f, default_flow_style=False)

    def get(self, role: str) -> AgentConfig:
        """Get config for role, creating default if needed."""
        if role not in self._configs:
            self._configs[role] = AgentConfig(role=role)
        return self._configs[role]

    def set_prompt(self, role: str, prompt: str) -> None:
        """Set system prompt for role."""
        config = self.get(role)
        config.system_prompt = prompt
        self._save_all()

    def set_criteria(self, role: str, criteria: List[str]) -> None:
        """Set evaluation criteria for role."""
        config = self.get(role)
        config.criteria = criteria
        self._save_all()

    def set_tool_access(self, role: str, tools: List[str]) -> None:
        """Set tool access for role."""
        config = self.get(role)
        config.tool_access = tools
        self._save_all()

    def set_llm_params(self, role: str, params: Dict) -> None:
        """Set LLM parameters for role."""
        config = self.get(role)
        config.llm_params = params
        self._save_all()

    def validate(self, config: AgentConfig) -> List[str]:
        """Validate agent config. Returns list of errors."""
        errors = []

        if not config.role:
            errors.append("Role is required")

        if config.llm_params:
            if 'temperature' in config.llm_params:
                t = config.llm_params['temperature']
                if not (0 <= t <= 2):
                    errors.append("Temperature must be 0-2")

        return errors