import os
from pathlib import Path
from langchain.tools import tool

@tool
def read_file_segment(
    file_path: str,
    start_line: int = 1,
    end_line: int | None = None
) -> str:
    """
    Read a specific segment of a file by line numbers (1-indexed).
    
    Args:
        file_path: The absolute path to the file.
        start_line: The line number to start reading from (inclusive, 1-indexed). Defaults to 1.
        end_line: The line number to stop reading at (inclusive, 1-indexed). If None, reads to the end.
        
    Returns:
        The content of the file segment, or an error message.
    """
    try:
        path = Path(file_path).resolve()
        if not path.exists():
            return f"Error: File '{file_path}' does not exist."
        if not path.is_file():
            return f"Error: '{file_path}' is not a file."
            
        try:
            with open(path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except UnicodeDecodeError:
            return f"Error: File '{file_path}' is not a valid text file (encoding error)."
            
        total_lines = len(lines)
        
        # Validate line numbers
        if start_line < 1:
            start_line = 1
        
        if end_line is None or end_line > total_lines:
            end_line = total_lines
            
        if start_line > total_lines:
            return f"Error: Start line {start_line} exceeds total lines in file ({total_lines})."
            
        if start_line > end_line:
            return f"Error: Start line {start_line} is greater than end line {end_line}."
            
        # Extract segment (convert 1-indexed to 0-indexed)
        segment_lines = lines[start_line-1 : end_line]
        content = "".join(segment_lines)
        
        return (
            f"--- FILE: {path.name} ({start_line}-{end_line}/{total_lines}) ---\n"
            f"{content}"
        )

    except Exception as e:
        return f"Error reading file segment: {e}"
