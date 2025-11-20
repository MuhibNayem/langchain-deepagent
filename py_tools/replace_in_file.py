from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from langchain.tools import tool

from .safety import ensure_path_allowed


def _parse_flags(flag_str: Optional[str]) -> int:
    mapping = {
        "i": re.IGNORECASE,
        "m": re.MULTILINE,
        "s": re.DOTALL,
    }
    value = 0
    if not flag_str:
        return value
    for char in flag_str.lower():
        value |= mapping.get(char, 0)
    return value


@tool("replace_in_file")
def replace_in_file(
    path: str,
    find: str,
    replace: str,
    use_regex: bool = False,
    flags: Optional[str] = None,
) -> dict:
    """Replace occurrences in a file (supports regex)."""
    resolved = ensure_path_allowed(path)
    try:
        original = Path(resolved).read_text(encoding="utf8")
    except OSError as exc:
        return {"error": True, "message": str(exc)}

    if use_regex:
        try:
            pattern = re.compile(find, _parse_flags(flags))
        except re.error as exc:
            return {"error": True, "message": f"Invalid regex: {exc}"}
        updated, count = pattern.subn(replace, original)
    else:
        count = original.count(find)
        updated = original.replace(find, replace)

    if updated == original:
        return {"error": False, "path": str(resolved), "changes": 0, "message": "No matches replaced."}

    try:
        Path(resolved).write_text(updated, encoding="utf8")
    except OSError as exc:
        return {"error": True, "message": str(exc)}

    return {
        "error": False,
        "path": str(resolved),
        "changes": count if count >= 0 else -1,
        "note": "Content replaced.",
    }


__all__ = ["replace_in_file"]
