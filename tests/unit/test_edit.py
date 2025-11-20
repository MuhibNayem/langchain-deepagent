"""Unit tests for the edit tool."""

import pytest
from unittest.mock import patch, Mock
from pathlib import Path
from luminamind.py_tools.edit import edit_file, _resolve_path

class TestEditFile:
    """Test cases for the edit_file tool."""

    @patch('luminamind.py_tools.edit._resolve_path')
    def test_edit_file_success(self, mock_resolve):
        """Test successful file edit."""
        mock_path = Mock()
        mock_resolve.return_value = mock_path
        
        result = edit_file.invoke({"file_path": "test.txt", "text": "Hello World"})
        
        mock_path.parent.mkdir.assert_called_with(parents=True, exist_ok=True)
        mock_path.write_text.assert_called_with("Hello World", encoding="utf-8")
        
        assert result["error"] is False
        assert "bytes_written" in result

    @patch('luminamind.py_tools.edit.ensure_path_allowed')
    @patch('os.getcwd')
    def test_resolve_path_absolute(self, mock_getcwd, mock_ensure):
        """Test path resolution for absolute paths."""
        mock_getcwd.return_value = "/app"
        mock_ensure.return_value = Path("/app/test.txt")
        
        # If we pass an absolute path that is inside cwd
        path = _resolve_path("/app/test.txt")
        
        # It should be passed to ensure_path_allowed
        mock_ensure.assert_called()
        assert path == Path("/app/test.txt")

    @patch('luminamind.py_tools.edit.ensure_path_allowed')
    def test_resolve_path_relative(self, mock_ensure):
        """Test path resolution for relative paths."""
        mock_ensure.return_value = Path("test.txt")
        
        path = _resolve_path("test.txt")
        
        mock_ensure.assert_called()
