"""Unit tests for the os_info tool."""

import pytest
from unittest.mock import patch, Mock
import sys
import os
from luminamind.py_tools.os_info import os_info, _total_memory_bytes, _uptime_seconds

class TestOsInfo:
    """Test cases for the os_info tool."""

    @patch('platform.system')
    @patch('platform.release')
    @patch('platform.machine')
    @patch('os.cpu_count')
    @patch('luminamind.py_tools.os_info._total_memory_bytes')
    @patch('luminamind.py_tools.os_info._uptime_seconds')
    def test_os_info_success(self, mock_uptime, mock_memory, mock_cpu, mock_machine, mock_release, mock_system):
        """Test successful retrieval of OS info."""
        mock_system.return_value = "TestOS"
        mock_release.return_value = "1.0.0"
        mock_machine.return_value = "x86_64"
        mock_cpu.return_value = 4
        mock_memory.return_value = 16000000000
        mock_uptime.return_value = 3600

        result = os_info.invoke({})

        assert result["error"] is False
        assert result["platform"] == "TestOS"
        assert result["release"] == "1.0.0"
        assert result["arch"] == "x86_64"
        assert result["cpus"] == 4
        assert result["memory"] == 16000000000
        assert result["uptime_seconds"] == 3600

    def test_total_memory_bytes_linux(self):
        """Test memory retrieval on Linux (mocked)."""
        with patch('os.sysconf') as mock_sysconf:
            mock_sysconf.side_effect = lambda x: 4096 if x == "SC_PAGE_SIZE" else 1000
            memory = _total_memory_bytes()
            assert memory == 4096000

    def test_total_memory_bytes_error(self):
        """Test memory retrieval error handling."""
        with patch('os.sysconf', side_effect=ValueError):
            # Also mock sys.platform to ensure we don't hit windows logic if running on windows
            with patch('sys.platform', 'linux'): 
                memory = _total_memory_bytes()
                assert memory is None

    @patch('sys.platform', 'darwin')
    @patch('subprocess.check_output')
    @patch('time.time')
    def test_uptime_seconds_darwin(self, mock_time, mock_check_output):
        """Test uptime retrieval on macOS."""
        mock_time.return_value = 10000
        mock_check_output.return_value = "kern.boottime: { sec = 9000, usec = 0 } Thu Jan 1 00:00:00 1970"
        
        # We need to mock os.name to 'posix' for the function to enter the first block
        with patch('os.name', 'posix'):
            uptime = _uptime_seconds()
            assert uptime == 1000

    @patch('os.name', 'posix')
    def test_uptime_seconds_linux(self):
        """Test uptime retrieval on Linux."""
        from unittest.mock import mock_open
        m = mock_open(read_data="1234.56 7890.12")
        with patch('builtins.open', m):
            uptime = _uptime_seconds()
            assert uptime == 1234

    def test_uptime_seconds_error(self):
        """Test uptime retrieval error handling."""
        with patch('os.name', 'unknown'):
             uptime = _uptime_seconds()
             assert uptime is None
