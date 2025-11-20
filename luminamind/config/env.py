from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv


def load_project_env() -> None:
    """Load environment variables from the current project's .env file if present."""
    project_env = Path.cwd() / ".env"
    if project_env.exists():
        load_dotenv(dotenv_path=project_env)
    else:
        load_dotenv()
