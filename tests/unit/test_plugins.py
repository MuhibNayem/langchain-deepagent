"""Tests for plugin system."""
import pytest
from pathlib import Path
from datetime import datetime
from luminamind.plugins.plugin import (
    Plugin,
    PluginManifest,
    PluginType,
    PluginDependency,
    PluginPermissions,
    PluginRegistry,
    PluginStore,
)
from luminamind.plugins.lifecycle import (
    PluginLifecycle,
    DefaultPluginLifecycle,
)
from luminamind.plugins.evaluator_iface import EvaluatorPluginInterface
from luminamind.plugins.tool_iface import ToolPluginInterface


class TestPluginManifest:
    """Tests for PluginManifest."""

    def test_plugin_type_enum(self):
        """Test PluginType enum values."""
        assert PluginType.EVALUATOR.value == "evaluator"
        assert PluginType.TOOL.value == "tool"
        assert PluginType.PROMPT.value == "prompt"
        assert PluginType.NOTIFICATION.value == "notification"

    def test_plugin_dependency_creation(self):
        """Test PluginDependency creation."""
        dep = PluginDependency(name="requests", version="2.0.0", optional=False)
        assert dep.name == "requests"
        assert dep.version == "2.0.0"
        assert dep.optional is False

    def test_plugin_permissions_defaults(self):
        """Test PluginPermissions default values."""
        perms = PluginPermissions()
        assert perms.network is False
        assert perms.filesystem_read == []
        assert perms.filesystem_write == []
        assert perms.environment == []


class TestPluginRegistry:
    """Tests for PluginRegistry."""

    def test_registry_empty_init(self):
        """Test empty registry initialization."""
        registry = PluginRegistry()
        assert registry.list_all() == []

    def test_register_plugin(self):
        """Test plugin registration."""
        registry = PluginRegistry()
        manifest = PluginManifest(
            name="test-plugin",
            version="1.0.0",
            description="A test plugin",
            author="Test Author",
            plugin_type=PluginType.TOOL,
            entry_point="main.py",
        )
        plugin = Plugin(
            manifest=manifest,
            root_path=Path("/tmp/test-plugin"),
            installed_at=datetime.utcnow(),
        )
        registry.register(plugin)
        assert registry.get("test-plugin") == plugin
        assert len(registry.list_all()) == 1

    def test_unregister_plugin(self):
        """Test plugin unregistration."""
        registry = PluginRegistry()
        manifest = PluginManifest(
            name="test-plugin",
            version="1.0.0",
            description="A test plugin",
            author="Test Author",
            plugin_type=PluginType.TOOL,
            entry_point="main.py",
        )
        plugin = Plugin(
            manifest=manifest,
            root_path=Path("/tmp/test-plugin"),
            installed_at=datetime.utcnow(),
        )
        registry.register(plugin)
        registry.unregister("test-plugin")
        assert registry.get("test-plugin") is None

    def test_list_by_type(self):
        """Test listing plugins by type."""
        registry = PluginRegistry()
        manifest1 = PluginManifest(
            name="eval-plugin",
            version="1.0.0",
            description="An evaluator plugin",
            author="Test",
            plugin_type=PluginType.EVALUATOR,
            entry_point="main.py",
        )
        manifest2 = PluginManifest(
            name="tool-plugin",
            version="1.0.0",
            description="A tool plugin",
            author="Test",
            plugin_type=PluginType.TOOL,
            entry_point="main.py",
        )
        registry.register(Plugin(manifest1, Path("/tmp/eval"), datetime.utcnow()))
        registry.register(Plugin(manifest2, Path("/tmp/tool"), datetime.utcnow()))

        eval_plugins = registry.list_by_type(PluginType.EVALUATOR)
        assert len(eval_plugins) == 1
        assert eval_plugins[0].manifest.name == "eval-plugin"


class TestDefaultPluginLifecycle:
    """Tests for DefaultPluginLifecycle."""

    def test_on_enable(self):
        """Test enabling a plugin."""
        lifecycle = DefaultPluginLifecycle()
        manifest = PluginManifest(
            name="test-plugin",
            version="1.0.0",
            description="Test",
            author="Test",
            plugin_type=PluginType.TOOL,
            entry_point="main.py",
        )
        plugin = Plugin(manifest, Path("/tmp"), datetime.utcnow(), enabled=False)
        lifecycle.on_enable(plugin)
        assert plugin.enabled is True

    def test_on_disable(self):
        """Test disabling a plugin."""
        lifecycle = DefaultPluginLifecycle()
        manifest = PluginManifest(
            name="test-plugin",
            version="1.0.0",
            description="Test",
            author="Test",
            plugin_type=PluginType.TOOL,
            entry_point="main.py",
        )
        plugin = Plugin(manifest, Path("/tmp"), datetime.utcnow(), enabled=True)
        lifecycle.on_disable(plugin)
        assert plugin.enabled is False


class TestEvaluatorPluginInterface:
    """Tests for EvaluatorPluginInterface."""

    def test_interface_is_abc(self):
        """Test that EvaluatorPluginInterface is abstract."""
        # Cannot instantiate directly - must be subclassed
        assert EvaluatorPluginInterface.__abstractmethods__ == {
            "name", "description", "get_criteria", "evaluate"
        }


class TestToolPluginInterface:
    """Tests for ToolPluginInterface."""

    def test_interface_is_abc(self):
        """Test that ToolPluginInterface is abstract."""
        # Cannot instantiate directly - must be subclassed
        assert ToolPluginInterface.__abstractmethods__ == {
            "name", "description", "input_schema", "execute"
        }