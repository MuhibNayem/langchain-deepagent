import os
from pathlib import Path
from langchain.tools import tool

@tool
def read_files_in_directory(
    directory_path: str,
    extensions: list[str] | None = None,
    recursive: bool = False,
    max_files: int = 10,
    max_size_per_file: int = 10000
) -> str:
    """
    Reads the content of multiple files in a directory.
    
    Args:
        directory_path: The path to the directory to read.
        extensions: Optional list of file extensions to include (e.g. ['.py', '.md']).
        recursive: Whether to search recursively.
        max_files: Maximum number of files to read (default 10).
        max_size_per_file: Maximum bytes to read per file (default 10000).
        
    Returns:
        A formatted string containing the content of the read files.
    """
    try:
        root_path = Path(directory_path).resolve()
        if not root_path.exists() or not root_path.is_dir():
            return f"Error: Directory '{directory_path}' does not exist or is not a directory."

        files_to_read = []
        
        if recursive:
            iterator = root_path.rglob("*")
        else:
            iterator = root_path.glob("*")

        for path in iterator:
            if path.is_file():
                if extensions:
                    if path.suffix not in extensions:
                        continue
                files_to_read.append(path)
                if len(files_to_read) >= max_files:
                    break
        
        if not files_to_read:
            return f"No matching files found in '{directory_path}'."

        result = []
        for file_path in files_to_read:
            try:
                content = file_path.read_text(encoding='utf-8')
                if len(content) > max_size_per_file:
                    content = content[:max_size_per_file] + "\n...[TRUNCATED]..."
                
                result.append(f"--- FILE: {file_path.name} ---\n{content}\n")
            except Exception as e:
                result.append(f"--- FILE: {file_path.name} ---\nError reading file: {e}\n")

        return "\n".join(result)

    except Exception as e:
        return f"Error processing directory '{directory_path}': {e}"
