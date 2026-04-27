import asyncio
import uuid
from datetime import datetime
from typing import Optional

try:
    import docker
    from docker.models.containers import Container
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False

from luminamind.sandbox.sandbox import (
    Sandbox, SandboxConfig, SandboxResult, SandboxStatus, SandboxBackend
)
from luminamind.sandbox.limits import ResourceLimits, ContainerResources

class DockerBackend(Sandbox):
    """Docker-based sandbox implementation."""
    
    def __init__(self, config: SandboxConfig):
        super().__init__(config)
        if not DOCKER_AVAILABLE:
            raise ImportError("docker-py not installed: pip install docker")
        self._client = docker.from_env()
        self._container: Optional[Container] = None
        self._sandbox_id: str = str(uuid.uuid4())[:8]
        self._started_at: Optional[datetime] = None
    
    async def start(self) -> str:
        """Start a new container from the configured image."""
        host_config = self._create_host_config()
        
        self._container = self._client.containers.run(
            image=self.config.image,
            command=self.config.command,
            detach=True,
            hostname=f"sandbox-{self._sandbox_id}",
            user=self.config.user,
            working_dir=self.config.working_dir,
            environment=self.config.env_vars,
            host_config=host_config
        )
        
        self._started_at = datetime.utcnow()
        return self._sandbox_id
    
    def _create_host_config(self):
        """Create Docker host config with resource limits."""
        return self._client.api.create_host_config(
            # Resource limits
            cpu_period=100000,
            cpu_quota=int(100000 * self.config.resources.cpu_count),
            mem_limit=self.config.resources.memory_limit,
            pids_limit=self.config.resources.pids_limit,
            # Storage
            volumes={
                '/tmp': {'bind': '/tmp', 'mode': 'rw'} if not self.config.limits.readonly_filesystem else None
            },
            # Network - disabled by default for isolation
            network_mode='none' if not self.config.resources.network else 'bridge',
            # Security
            read_only=self.config.limits.readonly_filesystem,
            cap_drop=['ALL'],
            security_opt=['no-new-privileges'],
        )
    
    async def execute(self, code: str, language: str = "python") -> SandboxResult:
        """Execute code in Docker container."""
        if not self._container:
            raise RuntimeError("Sandbox not started")
        
        start_time = datetime.utcnow()
        
        # Write code to temp file and execute
        filename = self._get_filename(language)
        await self.write_file(f"/workspace/{filename}", code)
        
        cmd = self._get_run_command(language, filename)
        
        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                self._run_command(cmd),
                timeout=self.config.limits.time_limit_seconds
            )
            
            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return SandboxResult(
                status=SandboxStatus.COMPLETED,
                stdout=result['stdout'],
                stderr=result['stderr'],
                exit_code=result['exit_code'],
                duration_ms=duration_ms,
                output_size=len(result['stdout']) + len(result['stderr'])
            )
        except asyncio.TimeoutError:
            await self._container.stop()
            return SandboxResult(
                status=SandboxStatus.TIMEOUT,
                stdout="",
                stderr=f"Execution timed out after {self.config.limits.time_limit_seconds}s",
                exit_code=-1,
                duration_ms=self.config.limits.time_limit_seconds * 1000,
                output_size=0,
                error="timeout"
            )
    
    async def _run_command(self, cmd: list[str]) -> dict:
        """Run command in container and return result."""
        exec_result = await asyncio.to_thread(
            self._container.exec_run,
            cmd,
            demux=True
        )
        
        stdout, stderr = exec_result.output
        return {
            'stdout': stdout.decode() if stdout else '',
            'stderr': stderr.decode() if stderr else '',
            'exit_code': exec_result.exit_code
        }
    
    def _get_filename(self, language: str) -> str:
        """Get filename for language."""
        return {
            'python': 'run.py',
            'node': 'run.js',
            'javascript': 'run.js',
            'java': 'Main.java',
            'go': 'run.go',
            'bash': 'run.sh'
        }.get(language, 'run.txt')
    
    def _get_run_command(self, language: str, filename: str) -> list[str]:
        """Get command to run file."""
        return {
            'python': ['python', f'/workspace/{filename}'],
            'node': ['node', f'/workspace/{filename}'],
            'javascript': ['node', f'/workspace/{filename}'],
            'java': ['javac', f'/workspace/{filename}'],
            'go': ['go', 'run', f'/workspace/{filename}'],
            'bash': ['bash', f'/workspace/{filename}']
        }.get(language, ['cat', f'/workspace/{filename}'])
    
    async def stop(self) -> None:
        """Stop and remove container."""
        if self._container:
            try:
                await asyncio.to_thread(self._container.stop)
                await asyncio.to_thread(self._container.remove)
            except Exception:
                pass
            self._container = None
    
    async def get_status(self) -> SandboxStatus:
        """Get container status."""
        if not self._container:
            return SandboxStatus.PENDING
        
        container = await asyncio.to_thread(
            self._client.containers.get, self._container.id
        )
        
        state = container.status
        if state == 'running':
            return SandboxStatus.RUNNING
        elif state == 'exited':
            return SandboxStatus.COMPLETED
        return SandboxStatus.PENDING
    
    async def write_file(self, path: str, content: str) -> None:
        """Write file to container."""
        if not self._container:
            raise RuntimeError("Sandbox not started")
        
        import base64
        content_b64 = base64.b64encode(content.encode()).decode()
        
        await asyncio.to_thread(
            self._container.exec_run,
            ['sh', '-c', f'echo {content_b64} | base64 -d > {path}']
        )
    
    async def read_file(self, path: str) -> str:
        """Read file from container."""
        if not self._container:
            raise RuntimeError("Sandbox not started")
        
        result = await asyncio.to_thread(
            self._container.exec_run,
            ['cat', path]
        )
        return result.output.decode()
