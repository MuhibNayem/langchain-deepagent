from __future__ import annotations

import os
import subprocess
from typing import Optional

from langchain.tools import tool

from .safety import ensure_path_allowed, get_allowed_root

DEFAULT_TIMEOUT_MS = 20_000


@tool("shell")
def shell(command: str, cwd: Optional[str] = None, timeout_ms: Optional[int] = None) -> dict:
    """Execute a shell command with optional cwd + timeout."""
    try:
        safe_cwd = ensure_path_allowed(cwd or os.getcwd())
    except ValueError as exc:
        return {"error": True, "message": str(exc), "allowed_root": str(get_allowed_root())}

    timeout = (timeout_ms or DEFAULT_TIMEOUT_MS) / 1000
    try:
        completed = subprocess.run(
            command,
            shell=True,
            cwd=str(safe_cwd),
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "error": True,
            "message": "Command timed out",
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
        }
    except subprocess.SubprocessError as exc:
        return {"error": True, "message": str(exc)}

    if completed.returncode != 0:
        return {
            "error": True,
            "code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }

    return {
        "error": False,
        "cwd": str(safe_cwd),
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


__all__ = ["shell"]
