from __future__ import annotations

import os
import shlex
import subprocess
import tempfile
from pathlib import Path
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


def _allowed_commands() -> set[str]:
    configured = os.environ.get("LUMINAMIND_ALLOWED_SHELL_COMMANDS")
    if not configured:
        return set(ALLOWED_COMMANDS)
    commands = {item.strip().lower() for item in configured.split(",") if item.strip()}
    return commands or set(ALLOWED_COMMANDS)


def _redirect_path(target: str) -> Path:
    """Validate a redirection target without using a shell."""
    resolved = Path(target).expanduser().resolve()
    allowed_root = get_allowed_root()
    temp_root = Path(tempfile.gettempdir()).resolve()
    try:
        resolved.relative_to(allowed_root)
        return resolved
    except ValueError:
        pass
    try:
        resolved.relative_to(temp_root)
        return resolved
    except ValueError as exc:
        raise ValueError(
            f"Redirect path not allowed: {resolved}. Allowed roots: {allowed_root}, {temp_root}"
        ) from exc


def _split_redirection(cmd_list: list[str]) -> tuple[list[str], Path | None, bool]:
    """Split a simple stdout redirection from argv.

    Supports `>` and `>>` without enabling shell interpretation.
    """
    redirect_positions = [idx for idx, token in enumerate(cmd_list) if token in {">", ">>"}]
    if not redirect_positions:
        return cmd_list, None, False
    if len(redirect_positions) > 1:
        raise ValueError("Only one stdout redirection is supported")
    idx = redirect_positions[0]
    if idx == 0 or idx != len(cmd_list) - 2:
        raise ValueError("Redirection must be the final operator followed by a path")
    return cmd_list[:idx], _redirect_path(cmd_list[idx + 1]), cmd_list[idx] == ">>"


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

    try:
        cmd_list, redirect_to, append_redirect = _split_redirection(cmd_list)
    except ValueError as exc:
        return {"error": True, "message": str(exc)}

    # Case-insensitive command check
    cmd_lower = cmd_list[0].lower()
    allowed_commands = _allowed_commands()
    if cmd_lower not in allowed_commands and not any(
        allowed in cmd_lower for allowed in allowed_commands
    ):
        return {
            "error": True,
            "message": f"Command '{cmd_list[0]}' not allowed",
            "allowed_commands": sorted(allowed_commands),
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

    result = {
        "error": False,
        "cwd": str(safe_cwd),
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }
    if redirect_to is not None:
        redirect_to.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if append_redirect else "w"
        with redirect_to.open(mode, encoding="utf8") as handle:
            handle.write(completed.stdout)
        result["redirected_to"] = str(redirect_to)
    return result


__all__ = ["shell"]
