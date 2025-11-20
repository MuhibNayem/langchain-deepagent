from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from langchain.tools import tool

from .safety import ensure_path_allowed


def _resolve_path(file_path: str) -> Path:
    path = Path(file_path)
    if path.is_absolute():
        root = Path(os.getcwd())
        path = root / path.relative_to(path.anchor)
    return ensure_path_allowed(path)


@tool("edit_file")
def edit_file(file_path: str, text: str, encoding: Optional[str] = "utf-8") -> dict:
    """Replace the entire file content with the provided text."""
    resolved = _resolve_path(file_path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(text, encoding=encoding or "utf-8")
    return {"error": False, "path": str(resolved), "bytes_written": len(text.encode(encoding or "utf-8"))}

__all__ = ["edit_file"]
