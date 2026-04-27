"""Model preset profiles for LuminaMind."""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import yaml
from pathlib import Path


@dataclass
class PresetProfile:
    """A preset configuration for model selection."""
    name: str
    description: str
    mappings: Dict[str, str]  # role -> "provider/model"
    is_free_optimal: bool = False


class ModelPresets:
    """Manages model preset profiles."""

    BUILT_IN_PRESETS = {
        'free_optimal': PresetProfile(
            name='free_optimal',
            description='Use free models where possible, paid only when needed',
            mappings={
                'planner': 'moonshot/kimi-k2.6',       # Paid - best reasoning
                'executor': 'zhipu/glm-4.7-flash',     # FREE - fast execution
                'evaluator': 'minimax/MiniMax-M2.7',   # Good quality evaluator
                'critic': 'zhipu/glm-4.7-flash',       # FREE - long-context critique
            },
            is_free_optimal=True
        ),
        'balanced': PresetProfile(
            name='balanced',
            description='Balanced mix of quality and cost',
            mappings={
                'planner': 'moonshot/kimi-k2.6',
                'executor': 'zhipu/glm-4.7-flash',
                'evaluator': 'minimax/MiniMax-M2.7',
                'critic': 'zhipu/glm-4.7-flash',
            }
        ),
        'quality': PresetProfile(
            name='quality',
            description='Maximum quality, cost secondary',
            mappings={
                'planner': 'moonshot/kimi-k2.6',
                'executor': 'moonshot/kimi-k2.6',
                'evaluator': 'minimax/MiniMax-M2.7',
                'critic': 'moonshot/kimi-k2.6',
            }
        ),
        'fast': PresetProfile(
            name='fast',
            description='Fast response times, lower cost',
            mappings={
                'planner': 'zhipu/glm-4.7-flash',
                'executor': 'zhipu/glm-4.7-flash',
                'evaluator': 'zhipu/glm-4.7-flash',
                'critic': 'zhipu/glm-4.7-flash',
            }
        ),
    }

    def __init__(self, config_path: Path = Path("~/.luminamind/models.yaml")):
        self.config_path = Path(config_path).expanduser()
        self._presets = dict(self.BUILT_IN_PRESETS)
        self._load_custom()

    def _load_custom(self) -> None:
        """Load custom presets from config."""
        if not self.config_path.exists():
            return

        with open(self.config_path) as f:
            data = yaml.safe_load(f)

        for preset_data in data.get('presets', []):
            preset = PresetProfile(
                name=preset_data['name'],
                description=preset_data.get('description', ''),
                mappings=preset_data['mappings'],
                is_free_optimal=preset_data.get('is_free_optimal', False)
            )
            self._presets[preset.name] = preset

    def get(self, name: str) -> Optional[PresetProfile]:
        """Get preset by name."""
        return self._presets.get(name)

    def list_presets(self) -> List[PresetProfile]:
        """List all available presets."""
        return list(self._presets.values())

    def apply_preset(self, name: str, registry: 'ModelRegistry') -> None:
        """Apply a preset to the model registry."""
        preset = self.get(name)
        if not preset:
            raise ValueError(f"Unknown preset: {name}")

        from luminamind.models.registry import AgentRole, RoleModelMapping

        for role_str, model_key in preset.mappings.items():
            provider, model = model_key.split('/', 1)
            mapping = RoleModelMapping(
                role=AgentRole(role_str),
                provider=provider,
                model=model
            )
            registry.set(AgentRole(role_str), mapping)