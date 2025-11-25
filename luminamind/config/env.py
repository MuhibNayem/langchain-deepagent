import typer
from pathlib import Path
from dotenv import load_dotenv


def get_global_config_path() -> Path:
    """Get the path to the global configuration file."""
    app_dir = Path(typer.get_app_dir("luminamind"))
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir / ".env"


def load_project_env() -> None:
    """
    Load environment variables.
    
    Priority (highest to lowest):
    1. System environment variables (already set)
    2. Global configuration (~/.config/luminamind/.env)
    3. Project .env file
    
    load_dotenv does not override existing variables by default, so we load in order of priority.
    """
    # 1. Load global config
    global_env = get_global_config_path()
    if global_env.exists():
        load_dotenv(dotenv_path=global_env)

    # 2. Load project config
    project_env = Path.cwd() / ".env"
    if project_env.exists():
        load_dotenv(dotenv_path=project_env)
    else:
        # Fallback to searching up the tree if no local .env
        load_dotenv()


def configure_global_env(force: bool = False) -> None:
    """
    Interactively configure global environment variables.
    
    Args:
        force: If True, prompt even if the file exists.
    """
    import questionary
    from rich.console import Console
    from rich.panel import Panel
    
    console = Console()
    config_path = get_global_config_path()
    
    if config_path.exists() and not force:
        return

    console.print(Panel(f"Global configuration file: [bold]{config_path}[/bold]", title="Configuration", border_style="cyan"))
    
    # Load existing
    current_vars = {}
    if config_path.exists():
        with open(config_path) as f:
            for line in f:
                if "=" in line:
                    k, v = line.strip().split("=", 1)
                    current_vars[k] = v
    
    if current_vars:
        console.print("\n[bold]Current Global Variables:[/bold]")
        for k, v in current_vars.items():
            masked = v[:4] + "*" * (len(v) - 4) if len(v) > 8 else "*" * len(v)
            console.print(f"  {k} = {masked}")
    
    if config_path.exists():
        if not questionary.confirm("Do you want to add/update environment variables?").ask():
            return

    new_vars = current_vars.copy()
    
    # Define configuration variables with defaults and properties
    config_definitions = [
        {"key": "OLLAMA_BASE_URL", "default": "http://localhost:11434", "secret": False},
        {"key": "OLLAMA_MODEL", "default": "qwen3:latest", "secret": False},
        {"key": "OLLAMA_API_KEY", "default": "", "secret": True},
        {"key": "GLM_API_KEY", "default": "", "secret": True},
        {"key": "GOOGLE_API_KEY", "default": "", "secret": True},
        {"key": "SERPER_API_KEY", "default": "", "secret": True},
        {"key": "GOOGLE_CSE_ID", "default": "", "secret": False},
        {"key": "WEATHER_API_KEY", "default": "", "secret": True},
        {"key": "DEBUG_WEB_SEARCH", "default": "0", "secret": False},
        {"key": "AGENT_VERBOSE", "default": "1", "secret": False},
        {"key": "TOOL_DEBUG", "default": "0", "secret": False},
        {"key": "DISABLE_CUSTOM_CHECKPOINTER", "default": "0", "secret": False},
    ]
    
    for item in config_definitions:
        key = item["key"]
        default_val = item["default"]
        is_secret = item["secret"]
        
        # Skip if already set and we are not forcing a full re-entry, 
        # BUT the user might want to edit existing values.
        # The prompt logic below allows editing.
        
        current_val = new_vars.get(key, default_val)
        
        if is_secret:
            # For secrets, we don't show the current value in the prompt text to avoid exposure,
            # but we can indicate if it's set.
            prompt_msg = f"Enter value for {key}"
            if current_val and current_val != default_val:
                prompt_msg += " (leave empty to keep current)"
            
            val = questionary.password(f"{prompt_msg}:").ask()
            
            if val:
                new_vars[key] = val
            elif not current_val:
                # If no current value and user entered nothing, use default if exists
                if default_val:
                    new_vars[key] = default_val
        else:
            val = questionary.text(f"Enter value for {key}:", default=current_val).ask()
            if val is not None: # text returns empty string if enter is pressed with no input but default is used?
                # questionary.text with default returns the default if user just presses enter.
                new_vars[key] = val

    # Allow adding custom variables
    if questionary.confirm("Do you want to add any other custom environment variables?").ask():
        while True:
            key = questionary.text("Enter variable name (e.g. CUSTOM_KEY) [Leave empty to finish]:").ask()
            if not key:
                break
            
            key = key.upper().strip()
            val = questionary.text(f"Enter value for {key}:").ask()
            
            if val:
                new_vars[key] = val
                console.print(f"[green]Set {key}[/green]")
    
    # Save
    with open(config_path, "w") as f:
        for k, v in new_vars.items():
            f.write(f"{k}={v}\n")
            
    console.print(f"\n[green]Configuration saved to {config_path}[/green]")
    # Reload environment to apply changes immediately
    load_dotenv(dotenv_path=config_path, override=True)


def ensure_global_env() -> None:
    """Ensure global configuration exists, prompting if missing."""
    config_path = get_global_config_path()
    if not config_path.exists():
        configure_global_env(force=True)
