"""Sandboxed execution for plugins using LuminaMind sandbox."""
from typing import Dict, Any, Optional
import asyncio

from luminamind.sandbox.sandbox import SandboxConfig, SandboxBackend, SandboxStatus
from luminamind.sandbox.docker_backend import DockerBackend
from luminamind.sandbox.limits import ResourceLimits, ContainerResources


class PluginSandbox:
    """Isolated execution environment for plugins using Docker sandbox."""

    def __init__(self):
        self._sandbox: Optional[Sandbox] = None

    async def execute(self, plugin_code: str, timeout: int = 30) -> Dict[str, Any]:
        """Execute plugin code in sandbox.

        Args:
            plugin_code: Python code to execute
            timeout: Execution timeout in seconds

        Returns:
            dict with success, stdout, stderr, exit_code
        """
        config = SandboxConfig(
            backend=SandboxBackend.DOCKER,
            image="python:3.12-slim",
            resources=ContainerResources(),
            limits=ResourceLimits(time_limit_seconds=timeout),
        )

        async with DockerBackend(config) as sandbox:
            result = await sandbox.execute(plugin_code, language="python")

            return {
                'success': result.status == SandboxStatus.COMPLETED,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'exit_code': result.exit_code,
                'duration_ms': result.duration_ms,
            }

    async def execute_with_context(
        self,
        plugin_code: str,
        context: Dict[str, Any],
        timeout: int = 30
    ) -> Dict[str, Any]:
        """Execute plugin code with a context dictionary available.

        Args:
            plugin_code: Python code to execute
            context: Variables to make available in execution scope
            timeout: Execution timeout in seconds

        Returns:
            dict with success, stdout, stderr, exit_code
        """
        # Wrap code to inject context
        context_lines = '\n'.join(f"    '{k}': {repr(v)}" for k, v in context.items())
        wrapped_code = f"""
context = {{
{context_lines}
}}
exec('''
{plugin_code}
''')
"""
        return await self.execute(wrapped_code, timeout=timeout)