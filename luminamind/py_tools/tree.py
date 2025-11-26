from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

from langchain.tools import tool

from .safety import ensure_path_allowed
from ..observability.metrics import monitor_tool


@tool("tree_view")
@monitor_tool
def tree_view(
    path: str = ".",
    max_depth: int = 2,
    exclude: Optional[List[str]] = None,
    show_hidden: bool = False,
) -> str:
    """
    Display the directory structure in a tree-like format.
    
    Args:
        path: The root directory to display.
        max_depth: Maximum depth to traverse.
        exclude: List of names or patterns to exclude (e.g., ["__pycache__", "*.git"]).
        show_hidden: Whether to show hidden files/directories (starting with .).
    """
    try:
        root_path = ensure_path_allowed(Path(path).resolve())
        if not root_path.exists() or not root_path.is_dir():
            return f"Error: Directory '{path}' does not exist."

        exclude_set = set(exclude) if exclude else set()
        
        lines = []
        
        def _should_exclude(name: str) -> bool:
            if not show_hidden and name.startswith("."):
                return True
            if name in exclude_set:
                return True
            # Simple glob-like check for exclusions
            for pattern in exclude_set:
                if "*" in pattern:
                    import fnmatch
                    if fnmatch.fnmatch(name, pattern):
                        return True
            return False

        def _walk(current_path: Path, prefix: str, depth: int):
            if depth > max_depth:
                return
            
            try:
                # Sort for consistent output
                entries = sorted(os.listdir(current_path))
            except OSError:
                return

            entries = [e for e in entries if not _should_exclude(e)]
            count = len(entries)
            
            for index, entry in enumerate(entries):
                is_last = index == count - 1
                connector = "└── " if is_last else "├── "
                
                lines.append(f"{prefix}{connector}{entry}")
                
                full_path = current_path / entry
                if full_path.is_dir():
                    extension = "    " if is_last else "│   "
                    _walk(full_path, prefix + extension, depth + 1)

        lines.append(root_path.name + "/")
        _walk(root_path, "", 1)
        
        return "\n".join(lines)

    except Exception as e:
        return f"Error generating tree view: {e}"
