"""Plugin lifecycle management for LuminaMind."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Optional
import importlib
import sys

if TYPE_CHECKING:
    from luminamind.plugins.plugin import Plugin


class PluginLifecycle(ABC):
    """Abstract base for plugin lifecycle management."""

    @abstractmethod
    def on_load(self, plugin: 'Plugin') -> bool:
        """Called when plugin is loaded. Return True to accept, False to reject."""
        pass

    @abstractmethod
    def on_enable(self, plugin: 'Plugin') -> None:
        """Called when plugin is enabled."""
        pass

    @abstractmethod
    def on_disable(self, plugin: 'Plugin') -> None:
        """Called when plugin is disabled."""
        pass

    @abstractmethod
    def on_uninstall(self, plugin: 'Plugin') -> None:
        """Called before plugin is uninstalled."""
        pass


class DefaultPluginLifecycle(PluginLifecycle):
    """Default lifecycle that just validates."""

    def on_load(self, plugin: 'Plugin') -> bool:
        """Validate plugin can be loaded."""
        from luminamind import __version__
        if plugin.manifest.min_luminamind_version > __version__:
            plugin.errors.append(f"Requires LuminaMind {plugin.manifest.min_luminamind_version}, have {__version__}")
            return False
        return True

    def on_enable(self, plugin: 'Plugin') -> None:
        """Enable plugin."""
        plugin.enabled = True

    def on_disable(self, plugin: 'Plugin') -> None:
        """Disable plugin."""
        plugin.enabled = False

    def on_uninstall(self, plugin: 'Plugin') -> None:
        """Cleanup before uninstall."""
        pass