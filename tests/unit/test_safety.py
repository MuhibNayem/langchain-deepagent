"""Unit tests for the safety tool."""

import pytest
from unittest.mock import patch, Mock
from pathlib import Path
import os
from luminamind.py_tools.safety import ensure_path_allowed, is_auto_generated_path, get_allowed_root

class TestSafety:
    """Test cases for the safety tool."""

    @patch('luminamind.py_tools.safety._DEFAULT_ROOT', Path("/app"))
    def test_ensure_path_allowed_success(self):
        """Test allowed path."""
        path = "/app/test.txt"
        result = ensure_path_allowed(path)
        assert result == Path(path)

    @patch('luminamind.py_tools.safety._DEFAULT_ROOT', Path("/app"))
    def test_ensure_path_allowed_failure(self):
        """Test disallowed path."""
        path = "/root/test.txt"
        with pytest.raises(ValueError) as exc:
            ensure_path_allowed(path)
        assert "Path not allowed" in str(exc.value)

    @patch('luminamind.py_tools.safety._DEFAULT_ROOT', Path("/app"))
    def test_is_auto_generated_path_true(self):
        """Test auto-generated path detection."""
        assert is_auto_generated_path("/app/node_modules/pkg") is True
        assert is_auto_generated_path("/app/.git/config") is True
        assert is_auto_generated_path("/app/test.log") is True

    @patch('luminamind.py_tools.safety._DEFAULT_ROOT', Path("/app"))
    def test_is_auto_generated_path_false(self):
        """Test non-auto-generated path detection."""
        assert is_auto_generated_path("/app/src/main.py") is False

    def test_get_allowed_root(self):
        """Test get_allowed_root returns a Path."""
        root = get_allowed_root()
        assert isinstance(root, Path)
