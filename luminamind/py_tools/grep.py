from __future__ import annotations

import os
import re
from pathlib import Path
from typing import List, Optional

from langchain.tools import tool

from .safety import ensure_path_allowed


@tool("grep_search")
def grep_search(
    query: str,
    directory: str = ".",
    extensions: Optional[List[str]] = None,
    case_sensitive: bool = True,
    max_results: int = 50,
) -> str:
    """
    Search for a text pattern in files within a directory.
    
    Args:
        query: The text or regex pattern to search for.
        directory: The directory to search in.
        extensions: Optional list of file extensions to include (e.g. ['.py', '.md']).
        case_sensitive: Whether the search is case sensitive.
        max_results: Maximum number of matches to return.
    """
    try:
        root_path = Path(directory).resolve()
        if not root_path.exists() or not root_path.is_dir():
            return f"Error: Directory '{directory}' does not exist."

        flags = 0 if case_sensitive else re.IGNORECASE
        try:
            pattern = re.compile(query, flags)
        except re.error as exc:
            return f"Error: Invalid regex pattern '{query}': {exc}"

        results = []
        match_count = 0

        for root, _, files in os.walk(root_path):
            for file in files:
                file_path = Path(root) / file
                
                # Filter by extension
                if extensions and file_path.suffix not in extensions:
                    continue
                
                # Skip hidden files/dirs (simple check)
                if any(part.startswith(".") for part in file_path.parts):
                    continue

                try:
                    # Read line by line to avoid loading huge files
                    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                        for line_num, line in enumerate(f, 1):
                            if pattern.search(line):
                                rel_path = file_path.relative_to(root_path)
                                results.append(f"{rel_path}:{line_num}: {line.strip()}")
                                match_count += 1
                                if match_count >= max_results:
                                    results.append("... (max results reached)")
                                    return "\n".join(results)
                except Exception:
                    # Ignore read errors (binary files etc)
                    continue

        if not results:
            return f"No matches found for '{query}' in '{directory}'."

        return "\n".join(results)

    except Exception as e:
        return f"Error executing grep_search: {e}"
