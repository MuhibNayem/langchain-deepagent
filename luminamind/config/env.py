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
