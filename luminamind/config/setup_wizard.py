"""First-launch setup wizard for LuminaMind.

Automatically prompts the user to configure provider, model, and API key
if no global configuration exists — just like Claude Code, Cursor, or
other modern harnesses.
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

import httpx
import questionary
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

from luminamind.config.env import get_global_config_path, load_project_env
from luminamind.config.providers import (
    PROVIDER_SCHEMA,
    read_provider_configs,
    write_provider_config,
    set_active_provider,
    get_active_provider,
)

console = Console()

# Provider definitions
PROVIDERS = {
    "z.ai": {
        "name": "Z.AI (GLM)",
        "description": "Zhipu AI / Z.AI — GLM models. Free tier available.",
        "api_base": "https://api.z.ai/api/paas/v4/",
        "api_key_env": "GLM_API_KEY",
        "api_base_env": "GLM_API_BASE",
        "models": ["glm-4.7-flash"],
        "dynamic_models": False,
    },
    "kimi": {
        "name": "Kimi (Moonshot)",
        "description": "Moonshot AI — Kimi K2.6, K2.5 series. OpenAI-compatible API.",
        "api_base": "https://api.moonshot.ai/v1",
        "api_key_env": "KIMI_API_KEY",
        "api_base_env": "KIMI_API_BASE",
        "models": [],
        "dynamic_models": True,
    },
    "minimax": {
        "name": "MiniMax",
        "description": "MiniMax — M2.7, M2.5, M2.1 series. Agentic coding models.",
        "api_base": "https://api.minimax.chat/v1",
        "api_key_env": "MINIMAX_API_KEY",
        "api_base_env": "MINIMAX_API_BASE",
        "models": [],
        "dynamic_models": True,
    },
}


def _is_configured() -> bool:
    """Check if the user has already completed first-launch setup.

    The wizard writes LUMINAMIND_SETUP_COMPLETE=1 to the global config
    when finished. This is the authoritative marker.
    """
    # Check global config file (~/.config/luminamind/.env)
    config_path = get_global_config_path()
    if config_path.exists():
        content = config_path.read_text(encoding="utf-8")
        vars_found = {}
        for line in content.splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                vars_found[k.strip()] = v.strip()
        # Authoritative marker: wizard sets this when complete
        if vars_found.get("LUMINAMIND_SETUP_COMPLETE") == "1":
            return True

    # Fallback: check env directly for the marker
    if os.environ.get("LUMINAMIND_SETUP_COMPLETE") == "1":
        return True

    return False


async def _fetch_kimi_models(api_key: str, base_url: str = "https://api.moonshot.ai/v1") -> list[str]:
    """Fetch available models from Kimi API."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{base_url.rstrip('/')}/models",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            response.raise_for_status()
            data = response.json()
            models = [m["id"] for m in data.get("data", [])]
            # Prioritize recent models
            priority = ["kimi-k2.6", "kimi-k2.5", "kimi-k2.5-preview"]
            models.sort(key=lambda m: (next((i for i, p in enumerate(priority) if p in m), 999), m))
            return models
    except Exception as exc:
        console.print(f"[yellow]Could not fetch Kimi models: {exc}[/yellow]")
        # Fallback static list
        return [
            "kimi-k2.6",
            "kimi-k2.5",
            "kimi-k2-0905-preview",
            "kimi-k2-turbo-preview",
            "kimi-k2-thinking",
            "moonshot-v1-128k",
        ]


async def _fetch_minimax_models(api_key: str, base_url: str = "https://api.minimax.chat/v1") -> list[str]:
    """Fetch available models from MiniMax API."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{base_url.rstrip('/')}/models",
                headers={"Authorization": f"Bearer {api_key}"},
            )
            if response.status_code == 200:
                data = response.json()
                models = [m["id"] for m in data.get("data", [])]
                if models:
                    return models
    except Exception as exc:
        console.print(f"[yellow]Could not fetch MiniMax models: {exc}[/yellow]")

    # Fallback static list from official docs
    return [
        "MiniMax-M2.7",
        "MiniMax-M2.7-highspeed",
        "MiniMax-M2.5",
        "MiniMax-M2.5-highspeed",
        "MiniMax-M2.1",
        "MiniMax-M2.1-highspeed",
        "MiniMax-M2",
    ]


async def _prompt_api_key(provider_key: str) -> str:
    """Prompt user for API key with helpful context."""
    info = PROVIDERS[provider_key]
    console.print(
        Panel.fit(
            f"[bold cyan]{info['name']}[/bold cyan]\n"
            f"[dim]{info['description']}[/dim]\n\n"
            f"Get your API key from:\n"
            f"  • z.ai → https://www.z.ai/ (sign up → API Keys)\n"
            f"  • Kimi → https://platform.kimi.ai/ (sign up → API Keys)\n"
            f"  • MiniMax → https://platform.minimax.io/ (sign up → API Keys)",
            title="API Key Required",
            border_style="cyan",
        )
    )
    api_key = await questionary.text(
        f"Enter your {info['name']} API key:",
        validate=lambda text: len(text.strip()) > 10 or "API key looks too short",
    ).unsafe_ask_async()
    return api_key.strip()


async def _prompt_model(provider_key: str, api_key: str, api_base: str) -> str:
    """Prompt user to select a model."""
    info = PROVIDERS[provider_key]

    if not info["dynamic_models"]:
        models = info["models"]
    else:
        with console.status("[bold magenta]Fetching available models..."):
            if provider_key == "kimi":
                models = await _fetch_kimi_models(api_key, api_base)
            elif provider_key == "minimax":
                models = await _fetch_minimax_models(api_key, api_base)
            else:
                models = info["models"]

    if len(models) == 1:
        console.print(f"[green]Auto-selected model: {models[0]}[/green]")
        return models[0]

    choice = await questionary.select(
        "Select a model:",
        choices=[
            questionary.Choice(title=f"{m} {'(recommended)' if i == 0 else ''}", value=m)
            for i, m in enumerate(models[:15])
        ],
    ).unsafe_ask_async()
    return choice


async def run_setup_wizard(force: bool = False) -> dict[str, Any]:
    """Run the first-launch setup wizard.

    Returns:
        Dict of configured environment variables.
    """
    if not force and _is_configured():
        return {}

    console.print(
        Panel.fit(
            "[bold cyan]Welcome to LuminaMind![/bold cyan]\n"
            "Let's get you set up in 30 seconds.",
            title="First Launch Setup",
            border_style="cyan",
        )
    )

    # Offer skip if existing config is detected
    config_path = get_global_config_path()
    if config_path.exists() and not force:
        existing = config_path.read_text(encoding="utf-8")
        has_any_key = any(k in existing for k in ["GLM_API_KEY", "KIMI_API_KEY", "MINIMAX_API_KEY", "OPENAI_API_KEY", "OLLAMA_BASE_URL"])
        if has_any_key:
            skip = await questionary.confirm(
                "Existing configuration detected. Skip wizard and use current settings?",
                default=False,
            ).unsafe_ask_async()
            if skip:
                # Mark as complete so we don't ask again
                lines = existing.splitlines()
                if not any(line.startswith("LUMINAMIND_SETUP_COMPLETE=") for line in lines):
                    lines.append("LUMINAMIND_SETUP_COMPLETE=1")
                    config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
                load_dotenv(dotenv_path=config_path, override=True)
                console.print("[dim]Skipped setup. Run `luminamind config` to reconfigure anytime.[/dim]")
                return {}

    # Step 1: Select provider
    provider_choice = await questionary.select(
        "Choose your LLM provider:",
        choices=[
            questionary.Choice(
                title=f"{p['name']} — {p['description']}",
                value=key,
            )
            for key, p in PROVIDERS.items()
        ],
    ).unsafe_ask_async()

    info = PROVIDERS[provider_choice]

    # Step 2: API Key
    api_key = await _prompt_api_key(provider_choice)

    # Step 3: Select model (with dynamic fetching)
    model = await _prompt_model(provider_choice, api_key, info["api_base"])

    # Step 4: Optional advanced settings
    customize = await questionary.confirm(
        "Customize API base URL? (usually not needed)", default=False
    ).unsafe_ask_async()

    api_base = info["api_base"]
    if customize:
        custom_base = await questionary.text(
            "API Base URL:", default=api_base
        ).unsafe_ask_async()
        if custom_base.strip():
            api_base = custom_base.strip()

    # Step 5: Save to global config — preserves other provider configs
    write_provider_config(
        provider_id=provider_choice,
        api_key=api_key,
        api_base=api_base,
        model=model,
        set_active=True,
    )

    # Apply model to legacy env var for immediate use
    os.environ["LUMINAMIND_MODEL"] = model

    console.print(
        Panel.fit(
            f"[bold green]Setup complete![/bold green]\n"
            f"Provider: {info['name']} [dim](now active)[/dim]\n"
            f"Model: [cyan]{model}[/cyan]\n"
            f"Config saved to: [dim]{config_path}[/dim]\n\n"
            f"You can re-run setup anytime with: [bold]luminamind config[/bold]",
            border_style="green",
        )
    )

    return config_vars


def run_setup_wizard_sync(force: bool = False) -> dict[str, Any]:
    """Synchronous wrapper for the setup wizard."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return asyncio.ensure_future(run_setup_wizard(force))
        return loop.run_until_complete(run_setup_wizard(force))
    except RuntimeError:
        return asyncio.run(run_setup_wizard(force))
