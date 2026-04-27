"""Prompt prefix builder with workspace summary caching.

Per D-05: PromptPrefixBuilder generates workspace summary (repo root, git status, project structure).
Per D-06: Cache invalidation on mtime changes (file modifications bust the cache).
Per D-07: Stable content cached; dynamic content (tool results, user input) excluded.
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from luminamind.py_tools.registry import PY_TOOL_REGISTRY


class WorkspaceSummary(BaseModel):
    """Workspace summary capturing stable content for caching.

    Fields:
        repo_root: Absolute path to repository root
        git_status: Output of 'git status --short'
        project_structure: Tree view of project structure
        tool_descriptions: Formatted tool descriptions from PY_TOOL_REGISTRY
        mtimes: Dict mapping file paths to modification times and sizes for cache invalidation.
        Value can be a float (mtime only, for backwards compatibility) or a dict
        with 'mtime' and 'size' keys for full tracking.
    """

    repo_root: str
    git_status: str
    project_structure: str
    tool_descriptions: str
    mtimes: dict[str, float | dict[str, float]]

    def cache_key(self) -> str:
        """Hash of stable content for cache invalidation.

        Returns a deterministic 16-character hex string based on stable content.
        Dynamic content (mtimes) is excluded from cache key computation.
        """
        content = f"{self.repo_root}|{self.git_status}|{self.project_structure}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def is_stale(self) -> bool:
        """Check if any cached file has been modified.

        Returns True if any tracked file's current mtime OR size differs from stored values,
        or if the file no longer exists.
        """
        repo_root_path = Path(self.repo_root)
        for path_str, stored_meta in self.mtimes.items():
            file_path = Path(path_str)
            # Resolve relative paths against repo_root
            if not file_path.is_absolute():
                file_path = repo_root_path / file_path
            if not file_path.exists():
                return True
            current_stat = file_path.stat()
            current_mtime = current_stat.st_mtime
            current_size = current_stat.st_size
            # Handle both old format (float mtime) and new format (dict with mtime and size)
            if isinstance(stored_meta, dict):
                stored_mtime = stored_meta.get("mtime", 0)
                stored_size = stored_meta.get("size", 0)
            else:
                stored_mtime = stored_meta
                stored_size = 0
            if abs(current_mtime - stored_mtime) > 0.5 or current_size != stored_size:
                return True
        return False

    def serialize(self) -> dict[str, Any]:
        """Return cacheable dict representation."""
        return self.model_dump()


class PromptPrefixBuilder:
    """Builds prompt prefix with cached workspace summary.

    Caches stable workspace content (repo root, git status, project structure, tool descriptions).
    Dynamic content (tool results, user input) is never cached.

    Usage:
        builder = PromptPrefixBuilder(workspace_path="/path/to/repo")
        prefix = builder.get_prefix()  # Returns cached prefix if valid
        prefix = builder.get_prefix(force_refresh=True)  # Force regeneration
    """

    def __init__(self, workspace_path: str | Path) -> None:
        """Initialize builder with workspace path.

        Args:
            workspace_path: Path to the workspace/repo root
        """
        self.workspace = Path(workspace_path).resolve()
        self._cache: dict[str, tuple[str, WorkspaceSummary]] = {}

    def get_prefix(self, force_refresh: bool = False) -> str:
        """Return cached prompt prefix or regenerate if stale.

        Args:
            force_refresh: If True, bypass cache and regenerate

        Returns:
            The prompt prefix string containing workspace summary
        """
        cache_key = self._compute_cache_key()
        if not force_refresh and cache_key in self._cache:
            cached_content, summary = self._cache[cache_key]
            if not summary.is_stale():
                return cached_content

        # Regenerate
        summary = self._generate_summary()
        content = self._build_prefix(summary)
        self._cache[cache_key] = (content, summary)
        return content

    def _compute_cache_key(self) -> str:
        """Compute cache key based on workspace file mtimes."""
        mtimes = self._collect_mtimes()
        # Include mtimes in cache key so any change triggers regeneration
        content = "|".join(f"{k}:{v}" for k, v in sorted(mtimes.items()))
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _generate_summary(self) -> WorkspaceSummary:
        """Generate workspace summary content."""
        repo_root = self._get_repo_root()
        git_status = self._get_git_status()
        project_structure = self._get_project_structure()
        tool_descriptions = self._get_tool_descriptions()
        mtimes = self._collect_mtimes()

        return WorkspaceSummary(
            repo_root=repo_root,
            git_status=git_status,
            project_structure=project_structure,
            tool_descriptions=tool_descriptions,
            mtimes=mtimes,
        )

    def _get_repo_root(self) -> str:
        """Return absolute path to repo root.

        Returns workspace path if .git not found, otherwise finds git root.
        """
        git_dir = self.workspace / ".git"
        if git_dir.exists():
            try:
                result = subprocess.run(
                    ["git", "rev-parse", "--show-toplevel"],
                    cwd=self.workspace,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    return result.stdout.strip()
            except (subprocess.TimeoutExpired, OSError):
                pass
        return str(self.workspace)

    def _get_git_status(self) -> str:
        """Run 'git status --short' if git repo, else empty string.

        Per T-01-05: 5 second timeout on git commands.
        """
        git_dir = self.workspace / ".git"
        if not git_dir.exists():
            return ""

        try:
            result = subprocess.run(
                ["git", "status", "--short"],
                cwd=self.workspace,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (subprocess.TimeoutExpired, OSError):
            pass
        return ""

    def _get_project_structure(self) -> str:
        """Return tree view of project structure.

        Uses 'tree -L 3' or lists files if tree unavailable.
        """
        try:
            result = subprocess.run(
                ["tree", "-L", "3", "-a", "--noreport"],
                cwd=self.workspace,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass

        # Fallback: list files manually
        lines = ["Project Structure:"]
        for item in sorted(self.workspace.iterdir()):
            if item.name.startswith("."):
                continue
            prefix = "├── " if item != sorted(self.workspace.iterdir())[-1] else "└── "
            lines.append(f"{prefix}{item.name}/")
        return "\n".join(lines)

    def _get_tool_descriptions(self) -> str:
        """Format tool descriptions from PY_TOOL_REGISTRY."""
        if not PY_TOOL_REGISTRY:
            return "No tools available."

        lines = ["Available Tools:"]
        for name, tool in sorted(PY_TOOL_REGISTRY.items()):
            desc = getattr(tool, "description", "No description")
            lines.append(f"- {name}: {desc}")
        return "\n".join(lines)

    def _collect_mtimes(self) -> dict[str, dict[str, float]]:
        """Collect mtimes of files that influence cache validity.

        Collects mtimes and sizes of:
        - .git/index (git status changes)
        - All .py files at repo root
        - pyproject.toml
        - luminamind/ directory tree
        """
        mtimes: dict[str, dict[str, float]] = {}

        # Git index
        git_index = self.workspace / ".git" / "index"
        if git_index.exists():
            stat = git_index.stat()
            mtimes[str(git_index)] = {"mtime": stat.st_mtime, "size": stat.st_size}

        # pyproject.toml at root
        pyproject = self.workspace / "pyproject.toml"
        if pyproject.exists():
            stat = pyproject.stat()
            mtimes[str(pyproject)] = {"mtime": stat.st_mtime, "size": stat.st_size}

        # Python files at root level
        for pattern in ["*.py"]:
            for f in self.workspace.glob(pattern):
                if f.name.startswith("."):
                    continue
                stat = f.stat()
                mtimes[str(f)] = {"mtime": stat.st_mtime, "size": stat.st_size}

        # luminamind directory tree
        luminamind_dir = self.workspace / "luminamind"
        if luminamind_dir.exists():
            for f in luminamind_dir.rglob("*.py"):
                stat = f.stat()
                mtimes[str(f)] = {"mtime": stat.st_mtime, "size": stat.st_size}

        return mtimes

    def _build_prefix(self, summary: WorkspaceSummary) -> str:
        """Build the prompt prefix string from workspace summary."""
        parts = [
            "# Workspace Summary",
            f"## Repository Root: {summary.repo_root}",
            "",
            "## Git Status",
            summary.git_status or "(not a git repository)",
            "",
            "## Project Structure",
            summary.project_structure,
            "",
            "## Available Tools",
            summary.tool_descriptions,
        ]
        return "\n".join(parts)


__all__ = ["PromptPrefixBuilder", "WorkspaceSummary"]