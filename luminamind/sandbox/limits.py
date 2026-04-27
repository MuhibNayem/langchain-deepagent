from dataclasses import dataclass
from typing import Optional

@dataclass
class ContainerResources:
    """Container resource specifications."""
    cpu_count: float = 1.0  # Number of CPUs
    memory_limit: str = "512m"  # Memory limit (e.g., "512m", "2g")
    disk_limit: str = "1g"  # Disk limit
    pids_limit: int = 100  # Max processes
    network: bool = False  # Network enabled (default: isolated)

@dataclass
class ResourceLimits:
    """Runtime resource limits for sandbox execution."""
    time_limit_seconds: int = 300  # Max execution time
    max_output_size: int = 1024 * 1024  # 1MB max output
    max_file_size: str = "10m"  # Max file creation
    allow_downloads: bool = False
    allow_uploads: bool = True
    readonly_filesystem: bool = True
    temp_dir_size: str = "100m"  # /tmp size

class TimeoutError(Exception):
    """Execution timed out."""
    pass

class ResourceExceededError(Exception):
    """Resource limit exceeded."""
    pass

class SandboxSecurityError(Exception):
    """Security policy violation."""
    pass
