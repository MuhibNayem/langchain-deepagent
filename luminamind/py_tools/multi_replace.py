from __future__ import annotations

import re
from pathlib import Path
from typing import Optional, List, Dict

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


@tool("multi_replace_in_file")
def multi_replace_in_file(
    path: str,
    replacements: List[Dict[str, str]],
    use_regex: bool = False,
    flags: Optional[str] = None,
) -> dict:
    """
    Replace multiple patterns in a single file.
    
    Args:
        path: Path to the file.
        replacements: List of dicts, each containing 'find' and 'replace' keys.
        use_regex: If True, treats 'find' strings as regex patterns.
        flags: Regex flags (e.g., 'i' for ignore case).
    """
    resolved = ensure_path_allowed(path)
    try:
        original = Path(resolved).read_text(encoding="utf8")
    except OSError as exc:
        return {"error": True, "message": str(exc)}

    current_content = original
    total_changes = 0
    
    regex_flags = _parse_flags(flags) if use_regex else 0

    for item in replacements:
        find_pattern = item.get("find")
        replace_pattern = item.get("replace")
        
        if not find_pattern:
            continue
            
        if use_regex:
            try:
                pattern = re.compile(find_pattern, regex_flags)
            except re.error as exc:
                return {"error": True, "message": f"Invalid regex '{find_pattern}': {exc}"}
            current_content, count = pattern.subn(replace_pattern, current_content)
            total_changes += count
        else:
            count = current_content.count(find_pattern)
            if count > 0:
                current_content = current_content.replace(find_pattern, replace_pattern)
                total_changes += count

    if current_content == original:
        return {"error": False, "path": str(resolved), "changes": 0, "message": "No matches replaced."}

    try:
        Path(resolved).write_text(current_content, encoding="utf8")
    except OSError as exc:
        return {"error": True, "message": str(exc)}

    return {
        "error": False,
        "path": str(resolved),
        "changes": total_changes,
        "note": "Content updated with multiple replacements.",
    }
