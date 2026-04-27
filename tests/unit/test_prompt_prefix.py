"""Unit tests for prompt_prefix module."""

import hashlib
from pathlib import Path

import pytest

from luminamind.config.prompt_prefix import PromptPrefixBuilder, WorkspaceSummary


class TestWorkspaceSummary:
    """Test WorkspaceSummary model."""

    def test_workspace_summary_fields(self, tmp_path):
        """Test WorkspaceSummary has all required fields."""
        summary = WorkspaceSummary(
            repo_root=str(tmp_path),
            git_status="?? new_file.py",
            project_structure="├── new_file.py",
            tool_descriptions="shell: Run shell commands",
            mtimes={"new_file.py": 1234567890.0},
        )
        assert summary.repo_root == str(tmp_path)
        assert summary.git_status == "?? new_file.py"
        assert summary.project_structure == "├── new_file.py"
        assert summary.tool_descriptions == "shell: Run shell commands"
        assert summary.mtimes == {"new_file.py": 1234567890.0}

    def test_workspace_summary_serialize(self, tmp_path):
        """Test serialize() returns cacheable dict."""
        summary = WorkspaceSummary(
            repo_root=str(tmp_path),
            git_status="",
            project_structure=".",
            tool_descriptions="",
            mtimes={"pyproject.toml": 1234567890.0},
        )
        data = summary.serialize()
        assert isinstance(data, dict)
        assert data["repo_root"] == str(tmp_path)
        assert "mtimes" in data

    def test_workspace_summary_cache_key(self, tmp_path):
        """Test cache_key() returns deterministic hash."""
        summary = WorkspaceSummary(
            repo_root=str(tmp_path),
            git_status="",
            project_structure=".",
            tool_descriptions="",
            mtimes={},
        )
        key = summary.cache_key()
        # Should be a 16-char hex string (SHA256 truncated)
        assert len(key) == 16
        assert all(c in "0123456789abcdef" for c in key)

        # Same content should produce same key
        summary2 = WorkspaceSummary(
            repo_root=str(tmp_path),
            git_status="",
            project_structure=".",
            tool_descriptions="",
            mtimes={},
        )
        assert summary2.cache_key() == key

    def test_cache_key_changes_on_content_change(self, tmp_path):
        """Test cache_key differs when content differs."""
        summary1 = WorkspaceSummary(
            repo_root=str(tmp_path),
            git_status="",
            project_structure=".",
            tool_descriptions="",
            mtimes={},
        )
        summary2 = WorkspaceSummary(
            repo_root=str(tmp_path),
            git_status="?? new_file",  # different
            project_structure=".",
            tool_descriptions="",
            mtimes={},
        )
        assert summary1.cache_key() != summary2.cache_key()

    def test_is_stale_returns_false_when_fresh(self, tmp_path):
        """Test is_stale() returns False when files unchanged."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        stat = test_file.stat()

        summary = WorkspaceSummary(
            repo_root=str(tmp_path),
            git_status="",
            project_structure=".",
            tool_descriptions="",
            mtimes={"test.txt": {"mtime": stat.st_mtime, "size": stat.st_size}},
        )
        assert summary.is_stale() is False

    def test_is_stale_returns_true_when_file_modified(self, tmp_path):
        """Test is_stale() returns True when file mtime or size changed."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("short")  # 5 bytes
        original_stat = test_file.stat()

        summary = WorkspaceSummary(
            repo_root=str(tmp_path),
            git_status="",
            project_structure=".",
            tool_descriptions="",
            mtimes={"test.txt": {"mtime": original_stat.st_mtime, "size": original_stat.st_size}},
        )

        # Modify file with different size to ensure cache bust
        test_file.write_text("much longer content here")  # 26 bytes
        new_stat = test_file.stat()

        summary_fresh = WorkspaceSummary(
            repo_root=str(tmp_path),
            git_status="",
            project_structure=".",
            tool_descriptions="",
            mtimes={"test.txt": {"mtime": new_stat.st_mtime, "size": new_stat.st_size}},
        )
        assert summary_fresh.is_stale() is False
        # Original summary now stale because size changed
        assert summary.is_stale() is True

    def test_is_stale_returns_true_when_file_missing(self, tmp_path):
        """Test is_stale() returns True when tracked file is missing."""
        summary = WorkspaceSummary(
            repo_root=str(tmp_path),
            git_status="",
            project_structure=".",
            tool_descriptions="",
            mtimes={"nonexistent.txt": {"mtime": 1234567890.0, "size": 0}},
        )
        assert summary.is_stale() is True


class TestPromptPrefixBuilder:
    """Test PromptPrefixBuilder class."""

    def test_prompt_prefix_builder_init(self, tmp_path):
        """Test PromptPrefixBuilder initializes correctly."""
        builder = PromptPrefixBuilder(workspace_path=tmp_path)
        assert builder.workspace == Path(tmp_path)

    def test_get_prefix_returns_string(self, tmp_path):
        """Test get_prefix() returns a string."""
        builder = PromptPrefixBuilder(workspace_path=tmp_path)
        prefix = builder.get_prefix()
        assert isinstance(prefix, str)

    def test_get_prefix_contains_workspace_info(self, tmp_path):
        """Test get_prefix() contains repo root."""
        builder = PromptPrefixBuilder(workspace_path=tmp_path)
        prefix = builder.get_prefix()
        assert str(tmp_path) in prefix

    def test_cache_hit_on_unchanged_workspace(self, tmp_path):
        """Test second call returns cached content."""
        builder = PromptPrefixBuilder(workspace_path=tmp_path)

        prefix1 = builder.get_prefix()
        prefix2 = builder.get_prefix()

        # Content should be identical (cache hit)
        assert prefix1 == prefix2

    def test_force_refresh_bypasses_cache(self, tmp_path):
        """Test force_refresh=True always regenerates."""
        builder = PromptPrefixBuilder(workspace_path=tmp_path)

        prefix1 = builder.get_prefix()
        prefix2 = builder.get_prefix(force_refresh=True)

        # Both should be valid strings
        assert prefix1 and prefix2
        # With no changes, they should be equal
        assert prefix1 == prefix2

    def test_prefix_contains_git_status_section(self, tmp_path):
        """Test prefix contains git status section."""
        builder = PromptPrefixBuilder(workspace_path=tmp_path)
        prefix = builder.get_prefix()
        assert "git" in prefix.lower() or "Git" in prefix

    def test_prefix_contains_project_structure_section(self, tmp_path):
        """Test prefix contains project structure section."""
        builder = PromptPrefixBuilder(workspace_path=tmp_path)
        prefix = builder.get_prefix()
        assert "structure" in prefix.lower() or "tree" in prefix.lower()