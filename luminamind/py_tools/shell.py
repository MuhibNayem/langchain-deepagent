from __future__ import annotations

import os
import shlex
import subprocess
from typing import Optional

from langchain.tools import tool
from pydantic import BaseModel, ValidationError, constr, validator

from .safety import ensure_path_allowed, get_allowed_root
from ..observability.metrics import monitor_tool

DEFAULT_TIMEOUT_MS = 20_000
ALLOWED_COMMANDS = {
    "ls",
    "cat",
    "grep",
    "find",
    "git",
    "npm",
    "yarn",
    "python",
    "pytest",
    "echo",
    "pwd",
    "which",
}


class ShellInput(BaseModel):
    command: constr(strip_whitespace=True, min_length=1, max_length=1000)
    cwd: Optional[str]
    timeout_ms: Optional[int]

    @validator("command")
    def validate_command(cls, value: str) -> str:
        dangerous_patterns = [
            "rm -rf /",
            "dd if=",
            ":(){ :|:& };:",
            "chmod 777",
            "> /dev/sd",
        ]
        for pattern in dangerous_patterns:
            if pattern in value:
                raise ValueError(f"Dangerous pattern detected: {pattern}")
        return value

    @validator("timeout_ms")
    def validate_timeout(cls, value: Optional[int]) -> Optional[int]:
        if value is None:
            return value
        if value < 100 or value > 300_000:
            raise ValueError("Timeout must be between 100ms and 300000ms")
        return value


@tool("shell")
@monitor_tool
def shell(
    command: str,
    cwd: Optional[str] = None,
    timeout_ms: Optional[int] = None,
) -> dict:
    """Execute a shell command with optional cwd + timeout."""
    try:
        validated = ShellInput(command=command, cwd=cwd, timeout_ms=timeout_ms)
    except ValidationError as exc:
        return {"error": True, "message": exc.errors()}

    try:
        cmd_list = shlex.split(validated.command)
    except ValueError as exc:
        return {"error": True, "message": f"Invalid command: {exc}"}

    if not cmd_list:
        return {"error": True, "message": "Empty command not allowed"}

    if cmd_list[0] not in ALLOWED_COMMANDS:
        return {
            "error": True,
            "message": f"Command '{cmd_list[0]}' not allowed",
            "allowed_commands": sorted(ALLOWED_COMMANDS),
        }

    try:
        safe_cwd = ensure_path_allowed(validated.cwd or os.getcwd())
    except ValueError as exc:
        return {"error": True, "message": str(exc), "allowed_root": str(get_allowed_root())}

    timeout = (validated.timeout_ms or DEFAULT_TIMEOUT_MS) / 1000
    try:
        completed = subprocess.run(
            cmd_list,
            shell=False,
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
