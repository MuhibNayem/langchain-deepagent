"""Legacy edit_file tool compatibility wrapper."""
from __future__ import annotations

from pathlib import Path

from langchain.tools import tool

from luminamind.py_tools.safety import ensure_path_allowed


def _resolve_path(file_path: str) -> Path:
    """Resolve and validate a target path."""
    return ensure_path_allowed(file_path)


@tool("edit_file")
def edit_file(file_path: str, text: str) -> dict:
    """Write text to a file, creating parent directories when needed."""
    try:
        path = _resolve_path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return {
            "error": False,
            "path": str(path),
            "bytes_written": len(text.encode("utf-8")),
        }
    except Exception as exc:
        return {"error": True, "message": str(exc)}

__all__ = ["edit_file", "_resolve_path", "ensure_path_allowed"]
