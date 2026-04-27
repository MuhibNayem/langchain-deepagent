from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum

class SandboxBackend(Enum):
    DOCKER = "docker"
    PROCESS = "process"  # Fallback without Docker

class SandboxStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    TIMEOUT = "timeout"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class SandboxConfig:
    """Configuration for sandbox execution."""
    backend: SandboxBackend = SandboxBackend.DOCKER
    image: str = "python:3.12-slim"
    resources: 'ContainerResources' = field(default_factory=lambda: ContainerResources())
    limits: 'ResourceLimits' = field(default_factory=lambda: ResourceLimits())
    working_dir: str = "/workspace"
    env_vars: dict = field(default_factory=dict)
    command: str = "/bin/bash"
    user: str = "nobody"  # Run as non-root user

@dataclass
class SandboxResult:
    """Result from sandbox execution."""
    status: SandboxStatus
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: float
    output_size: int
    error: str | None = None

class Sandbox(ABC):
    """Abstract sandbox for isolated code execution."""
    
    def __init__(self, config: SandboxConfig):
        self.config = config
    
    @abstractmethod
    async def start(self) -> str:
        """Start sandbox. Returns sandbox_id."""
        pass
    
    @abstractmethod
    async def execute(self, code: str, language: str = "python") -> SandboxResult:
        """Execute code in sandbox.
        
        Args:
            code: Code to execute
            language: Programming language (python, node, java, go)
        
        Returns:
            SandboxResult with stdout, stderr, exit_code, duration
        """
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """Stop and cleanup sandbox."""
        pass
    
    @abstractmethod
    async def get_status(self) -> SandboxStatus:
        """Get current sandbox status."""
        pass
    
    @abstractmethod
    async def write_file(self, path: str, content: str) -> None:
        """Write file to sandbox workspace."""
        pass
    
    @abstractmethod
    async def read_file(self, path: str) -> str:
        """Read file from sandbox workspace."""
        pass
    
    async def __aenter__(self) -> 'Sandbox':
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.stop()
