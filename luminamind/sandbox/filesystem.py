from dataclasses import dataclass
from pathlib import Path
from typing import Optional

@dataclass
class FilesystemSandbox:
    """Filesystem sandboxing with overlayfs."""
    base_dir: Path
    upper_dir: Path
    work_dir: Path
    readonly_paths: list[str]  # Paths that cannot be modified
    allowed_paths: list[str]  # Only these paths can be accessed
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    
    def __post_init__(self):
        self.base_dir = Path(self.base_dir)
        self.upper_dir = Path(self.upper_dir)
        self.work_dir = Path(self.work_dir)
    
    def setup(self) -> None:
        """Setup overlayfs mount structure."""
        pass
    
    def teardown(self) -> None:
        """Cleanup overlayfs."""
        pass
    
    def is_within_allowed(self, path: str) -> bool:
        """Check if path is within allowed paths."""
        pass
    
    def check_file_size(self, path: str, size: int) -> bool:
        """Check if file size is within limit."""
        pass
    
    def to_overlayfs_args(self) -> dict:
        """Get mount arguments for overlayfs."""
        return {
            'upperdir': str(self.upper_dir),
            'workdir': str(self.work_dir),
            'lowerdir': str(self.base_dir)
        }
