from __future__ import annotations

import os
from pathlib import Path
from typing import List

_DEFAULT_ROOT = Path(os.environ.get("ALLOWED_ROOT", os.getcwd())).expanduser().resolve()

_AUTO_GENERATED_SEGMENTS = {
    "node_modules",
    ".git",
    "dist",
    "build",
    "coverage",
    ".turbo",
    ".next",
    ".cache",
    ".vercel",
    ".parcel-cache",
    ".vscode-test",
    "tmp",
    "logs",
}

_AUTO_GENERATED_GLOBS = [
    "**/node_modules/**",
    "**/.git/**",
    "**/dist/**",
    "**/build/**",
    "**/coverage/**",
    "**/.turbo/**",
    "**/.next/**",
    "**/.cache/**",
    "**/.vercel/**",
    "**/.parcel-cache/**",
    "**/.vscode-test/**",
    "**/tmp/**",
    "**/logs/**",
    "**/*.log",
]


def get_allowed_root() -> Path:
    """Return the root directory all file operations must stay inside."""
    return _DEFAULT_ROOT


def ensure_path_allowed(target_path: os.PathLike[str] | str) -> Path:
    """Ensure the provided path is within the allowed root."""
    resolved = Path(target_path).expanduser().resolve()
    try:
        resolved.relative_to(_DEFAULT_ROOT)
    except ValueError as exc:  # pragma: no cover - defensive
        raise ValueError(
            f"Path not allowed: {resolved}. Allowed root: {_DEFAULT_ROOT}. "
            "Set ALLOWED_ROOT to widen."
        ) from exc
    return resolved


def is_auto_generated_path(target_path: os.PathLike[str] | str) -> bool:
    """Return True when the path points to an auto-generated file/directory."""
    resolved = Path(target_path).expanduser().resolve()
    try:
        rel_parts = resolved.relative_to(_DEFAULT_ROOT).parts
    except ValueError:
        return True
    return any(seg in _AUTO_GENERATED_SEGMENTS for seg in rel_parts) or resolved.name.endswith(".log")


def get_auto_generated_globs() -> List[str]:
    """Return the default glob patterns for auto-generated files."""
    return list(_AUTO_GENERATED_GLOBS)


def get_auto_generated_segments() -> List[str]:
    """Return the path segments that mark auto-generated directories."""
    return sorted(_AUTO_GENERATED_SEGMENTS)


__all__ = [
    "get_allowed_root",
    "ensure_path_allowed",
    "is_auto_generated_path",
    "get_auto_generated_globs",
    "get_auto_generated_segments",
]
