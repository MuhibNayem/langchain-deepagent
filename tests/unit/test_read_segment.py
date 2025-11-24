import pytest
import os
from luminamind.py_tools.read_segment import read_file_segment

@pytest.fixture
def temp_file(tmp_path):
    file_path = tmp_path / "test_segment.txt"
    content = "\n".join([f"Line {i}" for i in range(1, 21)]) # 20 lines
    file_path.write_text(content, encoding="utf-8")
    return str(file_path)

def test_read_segment_valid(temp_file):
    # Read lines 5 to 10
    result = read_file_segment.invoke({"file_path": temp_file, "start_line": 5, "end_line": 10})
    assert "Line 5" in result
    assert "Line 10" in result
    assert "Line 4" not in result
    assert "Line 11" not in result
    assert "(5-10/20)" in result

def test_read_segment_start_only(temp_file):
    # Read from line 15 to end
    result = read_file_segment.invoke({"file_path": temp_file, "start_line": 15})
    assert "Line 15" in result
    assert "Line 20" in result
    assert "Line 14" not in result

def test_read_segment_out_of_bounds(temp_file):
    # Start > End
    result = read_file_segment.invoke({"file_path": temp_file, "start_line": 10, "end_line": 5})
    assert "Error" in result
    
    # Start > Total
    result = read_file_segment.invoke({"file_path": temp_file, "start_line": 25})
    assert "Error" in result

def test_read_segment_file_not_found():
    result = read_file_segment.invoke({"file_path": "/non/existent/file.txt"})
    assert "Error" in result
