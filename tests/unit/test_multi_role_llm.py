"""Tests for multi-role LLM assignment system."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


class TestGetLLMForRole:
    """Test suite for role-based LLM routing."""

    def test_registry_provider_name_mapping(self):
        """Registry names like 'moonshot' and 'zhipu' map to canonical IDs."""
        from luminamind.llm import REGISTRY_PROVIDER_MAP

        assert REGISTRY_PROVIDER_MAP["moonshot"] == "kimi"
        assert REGISTRY_PROVIDER_MAP["zhipu"] == "z.ai"
        assert REGISTRY_PROVIDER_MAP["glm"] == "z.ai"
        assert REGISTRY_PROVIDER_MAP["kimi"] == "kimi"
        assert REGISTRY_PROVIDER_MAP["minimax"] == "minimax"
        assert REGISTRY_PROVIDER_MAP["openai"] == "openai"
        assert REGISTRY_PROVIDER_MAP["ollama"] == "ollama"
        assert REGISTRY_PROVIDER_MAP["anthropic"] == "openai"  # fallback

    def test_runtime_override_env_var(self):
        """LUMINAMIND_ROLE_MODEL_* env vars override registry."""
        from luminamind.llm import get_llm_for_role

        os.environ["LUMINAMIND_ROLE_MODEL_PLANNER"] = "override-model-x"
        try:
            llm = get_llm_for_role("planner")
            assert llm.model_name == "override-model-x"
        finally:
            del os.environ["LUMINAMIND_ROLE_MODEL_PLANNER"]

    def test_unknown_role_fallback(self):
        """Unknown roles fall back to active provider."""
        from luminamind.llm import get_llm_for_role

        llm = get_llm_for_role("nonexistent_role_xyz")
        # Should not crash; returns a ChatOpenAI instance
        assert llm is not None

    def test_get_llm_accepts_temperature_and_max_tokens(self):
        """get_llm() passes through temperature and max_tokens."""
        from luminamind.llm import get_llm

        llm = get_llm(temperature=0.3, max_tokens=512)
        assert llm.temperature == 0.3
        assert llm.max_tokens == 512


class TestModelRegistryIntegration:
    """Integration tests with real ModelRegistry."""

    @pytest.fixture
    def temp_registry(self):
        """Create a temporary ModelRegistry in a temp directory."""
        from luminamind.models.registry import ModelRegistry, AgentRole, RoleModelMapping

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "models.yaml"
            registry = ModelRegistry(config_path=path)
            yield registry

    def test_set_and_get_role_mapping(self, temp_registry):
        """Set a role mapping and retrieve it."""
        from luminamind.models.registry import AgentRole, RoleModelMapping

        mapping = RoleModelMapping(
            AgentRole.PLANNER, "moonshot", "kimi-k2.6", temperature=0.5, max_tokens=8000
        )
        temp_registry.set(AgentRole.PLANNER, mapping)

        retrieved = temp_registry.get(AgentRole.PLANNER)
        assert retrieved.provider == "moonshot"
        assert retrieved.model == "kimi-k2.6"
        assert retrieved.temperature == 0.5
        assert retrieved.max_tokens == 8000

    def test_preset_application(self, temp_registry):
        """Apply a preset and verify roles are updated."""
        from luminamind.models.presets import ModelPresets
        from luminamind.models.registry import AgentRole

        presets = ModelPresets()
        presets.apply_preset("fast", temp_registry)

        planner = temp_registry.get(AgentRole.PLANNER)
        assert planner.provider == "zhipu"
        assert planner.model == "glm-4.7-flash"

        executor = temp_registry.get(AgentRole.EXECUTOR)
        assert executor.provider == "zhipu"
        assert executor.model == "glm-4.7-flash"

    def test_default_for_unmapped_role(self, temp_registry):
        """Unmapped roles get sensible defaults."""
        from luminamind.models.registry import AgentRole

        default = temp_registry.get_default_for_role(AgentRole.ORCHESTRATOR)
        assert default.enabled is True
        assert default.model is not None
