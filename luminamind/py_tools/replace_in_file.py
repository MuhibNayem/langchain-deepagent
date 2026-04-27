"""Legacy replace_in_file compatibility wrapper."""
from __future__ import annotations

import re

from langchain.tools import tool

from luminamind.py_tools.multi_replace import _parse_flags
from luminamind.py_tools.safety import ensure_path_allowed


@tool("replace_in_file")
def replace_in_file(
    path: str,
    find: str,
    replace: str,
    use_regex: bool = False,
    flags: str | None = None,
) -> dict:
    """Replace text in a file using the legacy single-replacement schema."""
    try:
        target = ensure_path_allowed(path)
        content = target.read_text(encoding="utf8")
        if use_regex:
            try:
                new_content, changes = re.subn(find, replace, content, flags=_parse_flags(flags))
            except re.error as exc:
                return {"error": True, "message": f"Invalid regex: {exc}"}
        else:
            changes = content.count(find)
            new_content = content.replace(find, replace)

        if changes:
            target.write_text(new_content, encoding="utf8")
            message = f"Replaced {changes} occurrence(s)"
        else:
            message = "No matches replaced"
        return {"error": False, "path": str(target), "changes": changes, "message": message}
    except Exception as exc:
        return {"error": True, "message": str(exc)}

__all__ = ["replace_in_file", "_parse_flags", "ensure_path_allowed"]
