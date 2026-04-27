"""Multi-provider configuration manager.

Manages parallel provider configs in the global .env file:
- All providers can be configured simultaneously
- One provider is marked as "active" via LUMINAMIND_ACTIVE_PROVIDER
- Users can add, list, switch, and remove providers at any time
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from luminamind.config.env import get_global_config_path


# Schema: provider_id → {name, env_prefixes, default_model, api_base}
PROVIDER_SCHEMA: dict[str, dict[str, Any]] = {
    "z.ai": {
        "display_name": "Z.AI (GLM)",
        "api_key_env": "GLM_API_KEY",
        "api_base_env": "GLM_API_BASE",
        "model_env": "GLM_MODEL",
        "default_base": "https://api.z.ai/api/paas/v4/",
        "default_model": "glm-4.7-flash",
    },
    "kimi": {
        "display_name": "Kimi (Moonshot)",
        "api_key_env": "KIMI_API_KEY",
        "api_base_env": "KIMI_API_BASE",
        "model_env": "KIMI_MODEL",
        "default_base": "https://api.moonshot.ai/v1",
        "default_model": "kimi-k2.6",
    },
    "minimax": {
        "display_name": "MiniMax",
        "api_key_env": "MINIMAX_API_KEY",
        "api_base_env": "MINIMAX_API_BASE",
        "model_env": "MINIMAX_MODEL",
        "default_base": "https://api.minimax.chat/v1",
        "default_model": "MiniMax-M2.7",
    },
    "openai": {
        "display_name": "OpenAI",
        "api_key_env": "OPENAI_API_KEY",
        "api_base_env": "OPENAI_API_BASE",
        "model_env": "OPENAI_MODEL",
        "default_base": "https://api.openai.com/v1",
        "default_model": "gpt-4o",
    },
    "ollama": {
        "display_name": "Ollama (Local)",
        "api_key_env": "OLLAMA_API_KEY",
        "api_base_env": "OLLAMA_BASE_URL",
        "model_env": "OLLAMA_MODEL",
        "default_base": "http://localhost:11434",
        "default_model": "qwen3:latest",
    },
}

# Legacy/alias names
PROVIDER_ALIASES = {
    "glm": "z.ai",
    "moonshot": "kimi",
    "local": "ollama",
}


def _resolve_provider_id(name: str) -> str:
    """Normalize provider name to canonical ID."""
    name = name.lower().strip()
    return PROVIDER_ALIASES.get(name, name)


def _read_env_file(path: Path) -> dict[str, str]:
    """Read key=value pairs from an .env file."""
    result: dict[str, str] = {}
    if not path.exists():
        return result
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        result[k.strip()] = v.strip()
    return result


def _write_env_file(path: Path, data: dict[str, str]) -> None:
    """Write key=value pairs to an .env file, preserving comments from existing file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    # Collect existing comments to preserve them
    comments: dict[str, list[str]] = {}
    if path.exists():
        current_section = None
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                comments.setdefault(current_section or "__header", []).append(stripped)
            elif "=" in stripped:
                k = stripped.split("=", 1)[0].strip()
                current_section = k
                comments.setdefault(k, []).extend(comments.get("__pending", []))
                comments["__pending"] = []
            else:
                comments.setdefault("__pending", []).append(stripped)

    lines: list[str] = []
    written: set[str] = set()

    # Write header comments
    for c in comments.get("__header", []):
        lines.append(c)

    # Write provider sections with their comments
    for key, value in data.items():
        for c in comments.get(key, []):
            lines.append(c)
        lines.append(f"{key}={value}")
        written.add(key)

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def read_provider_configs() -> dict[str, dict[str, str]]:
    """Read all provider configurations from the global config file.

    Returns:
        Dict mapping provider_id → {api_key, api_base, model, display_name}
    """
    config_path = get_global_config_path()
    env_vars = _read_env_file(config_path)

    providers: dict[str, dict[str, str]] = {}
    for pid, schema in PROVIDER_SCHEMA.items():
        api_key = env_vars.get(schema["api_key_env"], "")
        api_base = env_vars.get(schema["api_base_env"], "")
        model = env_vars.get(schema["model_env"], "")

        # Ollama is special: base_url is enough
        is_configured = bool(api_key) or (pid == "ollama" and bool(api_base))

        if is_configured:
            providers[pid] = {
                "id": pid,
                "display_name": schema["display_name"],
                "api_key": api_key,
                "api_base": api_base or schema["default_base"],
                "model": model or schema["default_model"],
                "api_key_env": schema["api_key_env"],
            }

    return providers


def write_provider_config(
    provider_id: str,
    api_key: str,
    api_base: str | None = None,
    model: str | None = None,
    set_active: bool = True,
) -> None:
    """Write or update a provider's configuration in the global .env file.

    Preserves all other provider configs that already exist.
    """
    provider_id = _resolve_provider_id(provider_id)
    if provider_id not in PROVIDER_SCHEMA:
        raise ValueError(f"Unknown provider: {provider_id}. Known: {list(PROVIDER_SCHEMA.keys())}")

    schema = PROVIDER_SCHEMA[provider_id]
    config_path = get_global_config_path()
    env_vars = _read_env_file(config_path)

    # Update this provider's vars
    env_vars[schema["api_key_env"]] = api_key
    env_vars[schema["api_base_env"]] = api_base or schema["default_base"]
    env_vars[schema["model_env"]] = model or schema["default_model"]

    if set_active:
        env_vars["LUMINAMIND_ACTIVE_PROVIDER"] = provider_id

    # Ensure setup-complete marker
    env_vars["LUMINAMIND_SETUP_COMPLETE"] = "1"

    _write_env_file(config_path, env_vars)

    # Apply to current process
    for k, v in env_vars.items():
        os.environ[k] = v


def set_active_provider(provider_id: str) -> bool:
    """Set the active provider without changing its config.

    Returns:
        True if the provider was found and activated, False otherwise.
    """
    provider_id = _resolve_provider_id(provider_id)
    configs = read_provider_configs()

    if provider_id not in configs:
        return False

    config_path = get_global_config_path()
    env_vars = _read_env_file(config_path)
    env_vars["LUMINAMIND_ACTIVE_PROVIDER"] = provider_id
    _write_env_file(config_path, env_vars)

    os.environ["LUMINAMIND_ACTIVE_PROVIDER"] = provider_id
    return True


def get_active_provider() -> str | None:
    """Get the currently active provider ID."""
    # 1. Check explicit env var
    active = os.environ.get("LUMINAMIND_ACTIVE_PROVIDER")
    if active:
        return _resolve_provider_id(active)

    # 2. Check config file
    config_path = get_global_config_path()
    if config_path.exists():
        env_vars = _read_env_file(config_path)
        active = env_vars.get("LUMINAMIND_ACTIVE_PROVIDER")
        if active:
            return _resolve_provider_id(active)

    # 3. Fallback: find first configured provider
    configs = read_provider_configs()
    if configs:
        return next(iter(configs))

    return None


def remove_provider(provider_id: str) -> bool:
    """Remove a provider's configuration from the global .env file.

    Returns:
        True if provider was found and removed, False otherwise.
    """
    provider_id = _resolve_provider_id(provider_id)
    if provider_id not in PROVIDER_SCHEMA:
        return False

    schema = PROVIDER_SCHEMA[provider_id]
    config_path = get_global_config_path()
    env_vars = _read_env_file(config_path)

    removed = False
    for key in [schema["api_key_env"], schema["api_base_env"], schema["model_env"]]:
        if key in env_vars:
            del env_vars[key]
            removed = True

    if not removed:
        return False

    # If we removed the active provider, clear it
    if env_vars.get("LUMINAMIND_ACTIVE_PROVIDER") == provider_id:
        del env_vars["LUMINAMIND_ACTIVE_PROVIDER"]
        # Pick another active provider if available
        remaining = read_provider_configs()
        if remaining:
            env_vars["LUMINAMIND_ACTIVE_PROVIDER"] = next(iter(remaining))

    _write_env_file(config_path, env_vars)
    return True


def get_provider_env_vars(provider_id: str | None = None) -> dict[str, str]:
    """Get the resolved environment variables for a specific provider.

    Returns:
        Dict with keys: api_key, api_base, model, provider_id
    """
    provider_id = _resolve_provider_id(provider_id or get_active_provider() or "z.ai")
    if provider_id not in PROVIDER_SCHEMA:
        raise ValueError(f"Unknown provider: {provider_id}")

    schema = PROVIDER_SCHEMA[provider_id]
    return {
        "provider_id": provider_id,
        "api_key": os.environ.get(schema["api_key_env"], ""),
        "api_base": os.environ.get(schema["api_base_env"], schema["default_base"]),
        "model": os.environ.get(schema["model_env"], schema["default_model"]),
        "api_key_env": schema["api_key_env"],
        "api_base_env": schema["api_base_env"],
        "model_env": schema["model_env"],
    }
