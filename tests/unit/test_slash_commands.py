"""Tests for in-chat slash commands (/model, /provider, /role-model, /preset)."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest


class TestProviderSlashCommand:
    """Test /provider switching logic."""

    def test_set_active_provider(self):
        """Switching active provider updates env and config file."""
        from luminamind.config.providers import (
            write_provider_config,
            set_active_provider,
            get_active_provider,
            read_provider_configs,
        )

        with tempfile.TemporaryDirectory() as td:
            import luminamind.config.env as env
            import luminamind.config.providers as prov

            orig_get_path = env.get_global_config_path
            test_path = Path(td) / ".env"
            env.get_global_config_path = lambda: test_path
            prov.get_global_config_path = lambda: test_path

            try:
                # Configure two providers
                write_provider_config("z.ai", api_key="glm-key", model="glm-4.7-flash")
                write_provider_config("kimi", api_key="kimi-key", model="kimi-k2.6")

                # Active should be kimi (last added)
                assert get_active_provider() == "kimi"

                # Switch to z.ai
                assert set_active_provider("z.ai") is True
                assert get_active_provider() == "z.ai"

                # Switch back to kimi
                assert set_active_provider("kimi") is True
                assert get_active_provider() == "kimi"

                # Unknown provider should fail
                assert set_active_provider("nonexistent") is False
            finally:
                env.get_global_config_path = orig_get_path
                prov.get_global_config_path = orig_get_path


class TestRoleModelSlashCommand:
    """Test /role-model parsing and application."""

    @pytest.fixture
    def temp_registry(self):
        """Temp ModelRegistry in an isolated directory."""
        from luminamind.models.registry import ModelRegistry

        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "models.yaml"
            yield ModelRegistry(config_path=path)

    def test_role_model_set_and_read(self, temp_registry):
        """Set a role's model and read it back."""
        from luminamind.models.registry import AgentRole, RoleModelMapping

        temp_registry.set(
            AgentRole.PLANNER,
            RoleModelMapping(AgentRole.PLANNER, "moonshot", "kimi-k2.6", temperature=0.5, max_tokens=8000),
        )
        m = temp_registry.get(AgentRole.PLANNER)
        assert m.model == "kimi-k2.6"
        assert m.temperature == 0.5
        assert m.max_tokens == 8000

    def test_preset_applied_then_read_by_role(self, temp_registry):
        """Apply a preset and verify role models."""
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


class TestModelSlashCommand:
    """Test /model runtime override logic."""

    def test_apply_runtime_overrides_sets_env(self):
        """_apply_runtime_overrides populates env vars."""
        from luminamind.main import _apply_runtime_overrides

        # Clean env
        for key in ["LLM_PROVIDER", "LUMINAMIND_ACTIVE_PROVIDER", "LUMINAMIND_MODEL"]:
            os.environ.pop(key, None)

        _apply_runtime_overrides(provider="kimi", model="kimi-k2.6")
        assert os.environ["LLM_PROVIDER"] == "kimi"
        assert os.environ["LUMINAMIND_ACTIVE_PROVIDER"] == "kimi"
        assert os.environ["LUMINAMIND_MODEL"] == "kimi-k2.6"

    def test_apply_runtime_overrides_with_role_models(self):
        """_apply_runtime_overrides handles --role-model pairs."""
        from luminamind.main import _apply_runtime_overrides

        os.environ.pop("LUMINAMIND_ROLE_MODEL_PLANNER", None)
        os.environ.pop("LUMINAMIND_ROLE_MODEL_EXECUTOR", None)

        _apply_runtime_overrides(
            provider="z.ai",
            model="glm-4.7-flash",
            role_models=["planner=kimi-k2.6", "executor=MiniMax-M2.7"],
        )

        assert os.environ["LUMINAMIND_ROLE_MODEL_PLANNER"] == "kimi-k2.6"
        assert os.environ["LUMINAMIND_ROLE_MODEL_EXECUTOR"] == "MiniMax-M2.7"
        assert os.environ["LUMINAMIND_ACTIVE_PROVIDER"] == "z.ai"

        del os.environ["LUMINAMIND_ROLE_MODEL_PLANNER"]
        del os.environ["LUMINAMIND_ROLE_MODEL_EXECUTOR"]

    def test_get_llm_for_role_reads_runtime_override(self):
        """Runtime env override is picked up by get_llm_for_role."""
        from luminamind.llm import get_llm_for_role

        os.environ["LUMINAMIND_ROLE_MODEL_PLANNER"] = "special-model"
        try:
            llm = get_llm_for_role("planner")
            assert llm.model_name == "special-model"
        finally:
            del os.environ["LUMINAMIND_ROLE_MODEL_PLANNER"]
