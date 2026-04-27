"""Plugin system for LuminaMind third-party extensibility."""
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional
from enum import Enum
import yaml


class PluginType(Enum):
    """Types of plugins supported by LuminaMind."""
    EVALUATOR = "evaluator"  # Custom evaluator criteria
    TOOL = "tool"            # Custom tool integration
    PROMPT = "prompt"        # Custom prompt template
    NOTIFICATION = "notification"  # Notification channel


@dataclass
class PluginDependency:
    """A dependency required by a plugin."""
    name: str
    version: str  # semver or "any"
    optional: bool = False


@dataclass
class PluginPermissions:
    """Permissions requested by a plugin."""
    network: bool = False
    filesystem_read: list[str] = field(default_factory=list)  # Allowed read paths
    filesystem_write: list[str] = field(default_factory=list)  # Allowed write paths
    environment: list[str] = field(default_factory=list)  # Env vars accessible


@dataclass
class PluginManifest:
    """Plugin manifest (plugin.yaml)."""
    name: str
    version: str
    description: str
    author: str
    plugin_type: PluginType
    entry_point: str  # Python module or script
    dependencies: list[PluginDependency] = field(default_factory=list)
    permissions: PluginPermissions = field(default_factory=PluginPermissions)
    min_luminamind_version: str = "1.0.0"
    homepage: str = ""
    license: str = "MIT"


@dataclass
class Plugin:
    """A loaded/installed plugin."""
    manifest: PluginManifest
    root_path: Path
    installed_at: datetime
    enabled: bool = True
    errors: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    @classmethod
    def from_yaml(cls, yaml_path: Path) -> 'Plugin':
        """Load plugin from plugin.yaml."""
        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        manifest = PluginManifest(
            name=data['name'],
            version=data['version'],
            description=data.get('description', ''),
            author=data.get('author', ''),
            plugin_type=PluginType(data.get('type', 'tool')),
            entry_point=data['entry_point'],
            dependencies=[
                PluginDependency(**d) for d in data.get('dependencies', [])
            ],
            permissions=PluginPermissions(**data.get('permissions', {})),
            min_luminamind_version=data.get('min_luminamind_version', '1.0.0'),
            homepage=data.get('homepage', ''),
            license=data.get('license', 'MIT')
        )

        return cls(
            manifest=manifest,
            root_path=yaml_path.parent,
            installed_at=datetime.utcnow()
        )


class PluginStore:
    """Persistent storage for installed plugins."""

    def __init__(self, base_path: Path = Path("~/.luminamind/plugins")):
        self.base_path = Path(base_path).expanduser()
        self.base_path.mkdir(parents=True, exist_ok=True)
        self._index_file = self.base_path / "plugins.json"

    def save(self, plugin: Plugin) -> None:
        """Save plugin to store."""
        import json
        data = {
            'name': plugin.manifest.name,
            'version': plugin.manifest.version,
            'root_path': str(plugin.root_path),
            'installed_at': plugin.installed_at.isoformat(),
            'enabled': plugin.enabled
        }

        index = self._load_index()
        index[plugin.manifest.name] = data
        self._save_index(index)

    def load(self, name: str) -> Plugin | None:
        """Load plugin from store."""
        index = self._load_index()
        if name not in index:
            return None

        data = index[name]
        yaml_path = Path(data['root_path']) / 'plugin.yaml'

        if not yaml_path.exists():
            return None

        return Plugin.from_yaml(yaml_path)

    def list(self) -> list[str]:
        """List all installed plugin names."""
        return list(self._load_index().keys())

    def _load_index(self) -> dict:
        """Load plugin index."""
        import json
        if not self._index_file.exists():
            return {}
        with open(self._index_file) as f:
            return json.load(f)

    def _save_index(self, index: dict) -> None:
        """Save plugin index."""
        import json
        with open(self._index_file, 'w') as f:
            json.dump(index, f, indent=2)


class PluginRegistry:
    """In-memory registry of loaded plugins."""

    def __init__(self):
        self._plugins: dict[str, Plugin] = {}
        self._by_type: dict[PluginType, list[str]] = {}

    def register(self, plugin: Plugin) -> None:
        """Register a plugin."""
        self._plugins[plugin.manifest.name] = plugin

        ptype = plugin.manifest.plugin_type
        if ptype not in self._by_type:
            self._by_type[ptype] = []
        self._by_type[ptype].append(plugin.manifest.name)

    def unregister(self, name: str) -> None:
        """Unregister a plugin."""
        if name not in self._plugins:
            return

        plugin = self._plugins[name]
        ptype = plugin.manifest.plugin_type
        if ptype in self._by_type:
            self._by_type[ptype].remove(name)

        del self._plugins[name]

    def get(self, name: str) -> Plugin | None:
        """Get plugin by name."""
        return self._plugins.get(name)

    def list_by_type(self, plugin_type: PluginType) -> list[Plugin]:
        """List all plugins of a type."""
        names = self._by_type.get(plugin_type, [])
        return [self._plugins[n] for n in names]

    def list_all(self) -> list[Plugin]:
        """List all plugins."""
        return list(self._plugins.values())