"""Unit tests for the shell tool."""

import pytest
from unittest.mock import patch, Mock
import subprocess
from luminamind.py_tools.shell import shell

class TestShell:
    """Test cases for the shell tool."""

    @patch('luminamind.py_tools.shell.subprocess.run')
    def test_shell_success(self, mock_run):
        """Test successful shell command execution."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="Command output",
            stderr=""
        )
        
        result = shell.invoke({"command": "echo 'hello world'"})
        
        assert result["error"] is False
        assert result["stdout"] == "Command output"
        assert result["stderr"] == ""
        assert "cwd" in result

    @patch('luminamind.py_tools.shell.subprocess.run')
    def test_shell_error_code(self, mock_run):
        """Test shell command with non-zero exit code."""
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="Command failed"
        )
        
        result = shell.invoke({"command": "exit 1"})
        
        assert result["error"] is True
        assert result["code"] == 1
        assert result["stderr"] == "Command failed"

    @patch('luminamind.py_tools.shell.subprocess.run')
    def test_shell_timeout(self, mock_run):
        """Test shell command timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="sleep 10", timeout=1)
        
        result = shell.invoke({"command": "sleep 10", "timeout_ms": 1000})
        
        assert result["error"] is True
        assert "Command timed out" in result["message"]

    @patch('luminamind.py_tools.shell.subprocess.run')
    @patch('luminamind.py_tools.shell.ensure_path_allowed')
    def test_shell_with_cwd(self, mock_ensure, mock_run):
        """Test shell command with custom working directory."""
        mock_ensure.return_value = "/tmp"
        mock_run.return_value = Mock(
            returncode=0,
            stdout="",
            stderr=""
        )
        
        result = shell.invoke({"command": "pwd", "cwd": "/tmp"})
        
        assert result["error"] is False
        assert result["cwd"] == "/tmp"

    @patch('luminamind.py_tools.shell.subprocess.run')
    def test_shell_subprocess_error(self, mock_run):
        """Test shell command with subprocess error."""
        mock_run.side_effect = subprocess.SubprocessError("Subprocess error")
        
        result = shell.invoke({"command": "invalid_command"})
        
        assert result["error"] is True
        assert "Subprocess error" in result["message"]

    @patch('luminamind.py_tools.shell.ensure_path_allowed')
    def test_shell_path_not_allowed(self, mock_ensure):
        """Test shell command with disallowed path."""
        mock_ensure.side_effect = ValueError("Path not allowed")
        
        result = shell.invoke({"command": "echo 'test'", "cwd": "/root"})
        
        assert result["error"] is True
        assert "Path not allowed" in result["message"]
        assert "allowed_root" in result
