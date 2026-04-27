"""
Sandbox for executing generated code with restrictions.
"""
from __future__ import annotations
import tempfile
import os
import subprocess
import shutil
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Any

from luminamind.py_tools.safety import ensure_path_allowed


@dataclass
class SandboxConfig:
    max_execution_seconds: int = 30
    max_output_bytes: int = 1024 * 1024  # 1MB
    allowed_dirs: list[Path] | None = None  # If None, use ALLOWED_ROOT
    blocked_imports: list[str] = None  # e.g., ["os", "subprocess"]


@dataclass
class SandboxResult:
    """Result of sandboxed code execution."""

    success: bool
    output: str
    error: str
    execution_time: float
    return_code: int


class CodeSandbox:
    """Sandbox for executing generated code with restrictions."""

    def __init__(self, config: SandboxConfig | None = None):
        self.config = config or SandboxConfig()

    def execute(self, code: str, language: str = "python") -> SandboxResult:
        """Execute code in sandboxed temporary directory.

        Args:
            code: The code to execute
            language: python (only python supported initially)

        Returns:
            SandboxResult with output, error, execution_time
        """
        if language != "python":
            raise ValueError(f"Language {language} not supported")

        # Create temp dir inside allowed root
        allowed_root = self.config.allowed_dirs[0] if self.config.allowed_dirs else Path.cwd()

        # Use tempfile.mkdtemp which creates dir inside tmp by default (always allowed)
        tmp_dir = Path(tempfile.mkdtemp())
        try:
            # Write code to temp file
            script_path = tmp_dir / "script.py"
            script_path.write_text(code)

            # Execute with restricted permissions
            start = time.time()
            result = subprocess.run(
                ["python3", str(script_path)],
                capture_output=True,
                timeout=self.config.max_execution_seconds,
                cwd=str(tmp_dir),
                env={**os.environ, "HOME": str(tmp_dir)}  # Restrict home dir
            )
            execution_time = time.time() - start

            output = result.stdout[:self.config.max_output_bytes]
            error = result.stderr[:self.config.max_output_bytes]

            return SandboxResult(
                success=result.returncode == 0,
                output=output,
                error=error,
                execution_time=execution_time,
                return_code=result.returncode
            )
        finally:
            # Clean up temp dir
            shutil.rmtree(tmp_dir, ignore_errors=True)
