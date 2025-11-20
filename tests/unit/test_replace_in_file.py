"""Unit tests for the replace_in_file tool."""

import pytest
from unittest.mock import patch, Mock
from pathlib import Path
from luminamind.py_tools.replace_in_file import replace_in_file, _parse_flags
import re

class TestReplaceInFile:
    """Test cases for the replace_in_file tool."""

    def test_parse_flags(self):
        """Test regex flag parsing."""
        assert _parse_flags("i") == re.IGNORECASE
        assert _parse_flags("m") == re.MULTILINE
        assert _parse_flags("s") == re.DOTALL
        assert _parse_flags("im") == re.IGNORECASE | re.MULTILINE
        assert _parse_flags(None) == 0

    @patch('luminamind.py_tools.replace_in_file.ensure_path_allowed')
    @patch('pathlib.Path.read_text')
    @patch('pathlib.Path.write_text')
    def test_replace_simple_success(self, mock_write, mock_read, mock_ensure):
        """Test simple string replacement."""
        mock_ensure.return_value = Path("test.txt")
        mock_read.return_value = "Hello World"
        
        result = replace_in_file.invoke({"path": "test.txt", "find": "World", "replace": "Universe"})
        
        assert result["error"] is False
        assert result["changes"] == 1
        mock_write.assert_called_with("Hello Universe", encoding="utf8")

    @patch('luminamind.py_tools.replace_in_file.ensure_path_allowed')
    @patch('pathlib.Path.read_text')
    def test_replace_no_matches(self, mock_read, mock_ensure):
        """Test replacement with no matches."""
        mock_ensure.return_value = Path("test.txt")
        mock_read.return_value = "Hello World"
        
        result = replace_in_file.invoke({"path": "test.txt", "find": "Foo", "replace": "Bar"})
        
        assert result["error"] is False
        assert result["changes"] == 0
        assert "No matches replaced" in result["message"]

    @patch('luminamind.py_tools.replace_in_file.ensure_path_allowed')
    @patch('pathlib.Path.read_text')
    @patch('pathlib.Path.write_text')
    def test_replace_regex_success(self, mock_write, mock_read, mock_ensure):
        """Test regex replacement."""
        mock_ensure.return_value = Path("test.txt")
        mock_read.return_value = "Hello World"
        
        result = replace_in_file.invoke({"path": "test.txt", "find": "W[a-z]+", "replace": "Universe", "use_regex": True})
        
        assert result["error"] is False
        assert result["changes"] == 1
        mock_write.assert_called_with("Hello Universe", encoding="utf8")

    @patch('luminamind.py_tools.replace_in_file.ensure_path_allowed')
    @patch('pathlib.Path.read_text')
    def test_replace_invalid_regex(self, mock_read, mock_ensure):
        """Test replacement with invalid regex."""
        mock_ensure.return_value = Path("test.txt")
        mock_read.return_value = "Hello World"
        
        result = replace_in_file.invoke({"path": "test.txt", "find": "[", "replace": "Universe", "use_regex": True})
        
        assert result["error"] is True
        assert "Invalid regex" in result["message"]

    @patch('luminamind.py_tools.replace_in_file.ensure_path_allowed')
    @patch('pathlib.Path.read_text')
    def test_replace_read_error(self, mock_read, mock_ensure):
        """Test file read error."""
        mock_ensure.return_value = Path("test.txt")
        mock_read.side_effect = OSError("Read error")
        
        result = replace_in_file.invoke({"path": "test.txt", "find": "Foo", "replace": "Bar"})
        
        assert result["error"] is True
        assert "Read error" in result["message"]
