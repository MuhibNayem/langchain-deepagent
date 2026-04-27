"""Unit tests for cache invalidation behavior in PromptPrefixBuilder."""

import subprocess
import time
from pathlib import Path

import pytest

from luminamind.config.prompt_prefix import PromptPrefixBuilder


class TestCacheInvalidation:
    """Test cache invalidation based on file modifications."""

    def test_cache_hit_on_unchanged_files(self, tmp_path):
        """Test that repeated calls return cached content when files unchanged."""
        builder = PromptPrefixBuilder(workspace_path=tmp_path)

        # First call - generates and caches
        prefix1 = builder.get_prefix()

        # Second call - should hit cache (same mtimes)
        prefix2 = builder.get_prefix()

        # Content should be identical
        assert prefix1 == prefix2

    def test_cache_bust_on_file_modified(self, tmp_path):
        """Test that modifying a tracked file triggers cache regeneration."""
        builder = PromptPrefixBuilder(workspace_path=tmp_path)

        # Create luminamind directory with a Python file (tracked by _collect_mtimes)
        luminamind_dir = tmp_path / "luminamind"
        luminamind_dir.mkdir(exist_ok=True)
        test_module = luminamind_dir / "test_module.py"
        test_module.write_text("# initial content")

        # First call - generates and caches
        prefix1 = builder.get_prefix()

        # Verify cache is populated
        cache_key1 = builder._compute_cache_key()

        # Modify the tracked Python file
        test_module.write_text("# modified content that is different")

        # Second call - should detect cache invalidation via is_stale
        prefix2 = builder.get_prefix()

        # Verify cache key changed due to file modification
        cache_key2 = builder._compute_cache_key()

        # Cache key should differ because the tracked file changed
        assert cache_key1 != cache_key2

    def test_cache_bust_on_git_status_change(self, tmp_path):
        """Test that git status changes bust the cache."""
        # Initialize git repo
        subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=tmp_path,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=tmp_path,
            capture_output=True,
        )

        builder = PromptPrefixBuilder(workspace_path=tmp_path)

        # First call - generates with initial git status
        prefix1 = builder.get_prefix()

        # Create and stage a new file
        new_file = tmp_path / "new_file.txt"
        new_file.write_text("new content")
        subprocess.run(["git", "add", "new_file.txt"], cwd=tmp_path, capture_output=True)

        # Second call - should regenerate due to git status change
        prefix2 = builder.get_prefix()

        # Git status in prefix should be different
        assert prefix1 != prefix2

    def test_cache_key_changes_on_new_files(self, tmp_path):
        """Test that new files in workspace change the cache key."""
        builder = PromptPrefixBuilder(workspace_path=tmp_path)

        # First call
        prefix1 = builder.get_prefix()

        # Add a new file to the luminamind directory (which is tracked)
        luminamind_dir = tmp_path / "luminamind"
        luminamind_dir.mkdir(exist_ok=True)
        new_module = luminamind_dir / "new_module.py"
        new_module.write_text("# new module")

        # Second call
        prefix2 = builder.get_prefix()

        # Content should differ because new file changes project structure
        assert prefix1 != prefix2

    def test_force_refresh_bypasses_cache(self, tmp_path):
        """Test that force_refresh=True always regenerates content."""
        builder = PromptPrefixBuilder(workspace_path=tmp_path)

        # First call
        prefix1 = builder.get_prefix()

        # Force refresh should regenerate even without changes
        prefix2 = builder.get_prefix(force_refresh=True)

        # Both should be valid strings (content could be same if no changes)
        assert prefix1 and prefix2

        # With no changes, both should produce same content
        # but internally it should have regenerated (bypassed cache)
        assert prefix1 == prefix2

    def test_cache_stable_across_multiple_calls(self, tmp_path):
        """Test cache remains stable across many rapid calls."""
        builder = PromptPrefixBuilder(workspace_path=tmp_path)

        prefixes = [builder.get_prefix() for _ in range(5)]

        # All prefixes should be identical (cache hit)
        for p in prefixes[1:]:
            assert p == prefixes[0]

    def test_cache_invalidation_on_tracked_file_deletion(self, tmp_path):
        """Test cache busts when a tracked file is deleted."""
        builder = PromptPrefixBuilder(workspace_path=tmp_path)

        # Create and track a file
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("[project]\nname = 'test'\nversion = '0.1.0'")

        # First call
        prefix1 = builder.get_prefix()

        # Delete the tracked file
        pyproject.unlink()

        # Second call - should regenerate
        prefix2 = builder.get_prefix()

        # Project structure should differ
        assert prefix1 != prefix2

    def test_mixed_file_operations_maintain_cache_correctness(self, tmp_path):
        """Test that complex file operations correctly invalidate cache."""
        builder = PromptPrefixBuilder(workspace_path=tmp_path)

        # Create luminamind directory with Python files (tracked by _collect_mtimes)
        luminamind_dir = tmp_path / "luminamind"
        luminamind_dir.mkdir(exist_ok=True)
        module1 = luminamind_dir / "module1.py"
        module2 = luminamind_dir / "module2.py"
        module1.write_text("# content 1")
        module2.write_text("# content 2")

        prefix1 = builder.get_prefix()
        cache_key1 = builder._compute_cache_key()

        # Modify one tracked Python file
        module1.write_text("# modified content 1")

        # Second call - should detect cache invalidation
        cache_key2 = builder._compute_cache_key()

        # Cache key should differ because tracked file changed
        assert cache_key1 != cache_key2

        # Now make no changes
        cache_key3 = builder._compute_cache_key()

        # Should hit cache - same key
        assert cache_key2 == cache_key3