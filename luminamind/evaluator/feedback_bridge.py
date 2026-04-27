"""FeedbackBridge for file-based generator-evaluator communication per GE-03.

This module implements a file-based communication bridge between the generator
and evaluator agents in the GAN-inspired dual-agent system.

Communication pattern:
- Bridge writes artifact to input file
- Bridge waits for evaluator to write result to output file
- Bridge reads result and returns to generator
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from luminamind.evaluator.agent import GradingResult


@dataclass
class FeedbackMessage:
    """Message format for generator-evaluator communication.

    Attributes:
        session_id: Unique session identifier
        iteration: Current iteration number
        artifact_type: Type of artifact ("code", "frontend", "spec")
        artifact_content: The actual artifact content
        metadata: Additional metadata including timestamp
    """

    session_id: str
    iteration: int
    artifact_type: str  # "code", "frontend", "spec"
    artifact_content: str
    metadata: dict


@dataclass
class FeedbackResult:
    """Result format from evaluator back to generator.

    Attributes:
        session_id: Unique session identifier
        iteration: Current iteration number
        grading_result: The actual grading result from evaluator
        evaluation_context: Optional context from evaluation
    """

    session_id: str
    iteration: int
    grading_result: GradingResult
    evaluation_context: dict | None


class FeedbackBridge:
    """File-based generator-evaluator communication per GE-03.

    Uses shared filesystem for communication between generator and evaluator:
    - Bridge writes artifact to input file
    - Bridge waits for evaluator to write result to output file
    - Bridge reads result and returns to generator

    Args:
        bridge_dir: Directory for bridge files (defaults to /tmp/luminamind/bridge)
        poll_interval: Time between polling checks in seconds
        timeout: Maximum time to wait for result in seconds
    """

    def __init__(
        self,
        bridge_dir: Path | None = None,
        poll_interval: float = 0.5,
        timeout: float = 60.0,
    ):
        self.bridge_dir = bridge_dir or Path("/tmp/luminamind/bridge")
        self.poll_interval = poll_interval
        self.timeout = timeout
        self.bridge_dir.mkdir(parents=True, exist_ok=True)

    def send_for_evaluation(
        self,
        artifact: Any,
        evaluator: Any,
        session_id: str,
        iteration: int,
        artifact_type: str = "code",
    ) -> GradingResult:
        """Send artifact for evaluation and wait for result.

        Args:
            artifact: The artifact to evaluate
            evaluator: EvaluatorAgent instance
            session_id: Unique session identifier
            iteration: Current iteration number
            artifact_type: Type of artifact for context

        Returns:
            GradingResult from evaluator
        """
        # Write input file
        input_file = self.bridge_dir / f"{session_id}_{iteration}_input.json"
        message = FeedbackMessage(
            session_id=session_id,
            iteration=iteration,
            artifact_type=artifact_type,
            artifact_content=str(artifact),
            metadata={"timestamp": time.time()},
        )

        with open(input_file, "w") as f:
            json.dump(asdict(message), f)

        # Send to evaluator and get result
        result = evaluator.evaluate(artifact)

        # Write output file
        output_file = self.bridge_dir / f"{session_id}_{iteration}_output.json"
        feedback_result = FeedbackResult(
            session_id=session_id,
            iteration=iteration,
            grading_result=result,
            evaluation_context=None,
        )

        with open(output_file, "w") as f:
            json.dump(asdict(feedback_result), f)

        return result

    def poll_for_result(self, output_file: Path, timeout: float | None = None) -> GradingResult:
        """Poll for evaluation result.

        Args:
            output_file: Path to output file to poll
            timeout: Max time to wait (uses default if None)

        Returns:
            GradingResult when output file is ready

        Raises:
            TimeoutError: If timeout exceeded
        """
        timeout = timeout or self.timeout
        start_time = time.time()

        while time.time() - start_time < timeout:
            if output_file.exists():
                with open(output_file, "r") as f:
                    data = json.load(f)
                    grading = data.get("grading_result", data)
                    result = GradingResult(
                        score=grading.get("score", 0.0),
                        issues=grading.get("issues", []),
                        feedback=grading.get("feedback", ""),
                        iteration=grading.get("iteration", 0),
                    )
                    return result
            time.sleep(self.poll_interval)

        raise TimeoutError(f"Evaluation timed out after {timeout}s")

    def send_for_evaluation_async(
        self,
        artifact: Any,
        session_id: str,
        iteration: int,
        artifact_type: str = "code",
    ) -> tuple[Path, Any]:
        """Non-blocking send for evaluation.

        Args:
            artifact: The artifact to evaluate
            session_id: Unique session identifier
            iteration: Current iteration number
            artifact_type: Type of artifact for context

        Returns:
            tuple of (output_file_path, future-like object)
        """
        # Write input file for async processing
        input_file = self.bridge_dir / f"{session_id}_{iteration}_input.json"
        message = FeedbackMessage(
            session_id=session_id,
            iteration=iteration,
            artifact_type=artifact_type,
            artifact_content=str(artifact),
            metadata={"timestamp": time.time(), "async": True},
        )

        with open(input_file, "w") as f:
            json.dump(asdict(message), f)

        output_file = self.bridge_dir / f"{session_id}_{iteration}_output.json"

        # Return a simple future-like wrapper
        class AsyncResult:
            """Simple future-like wrapper for async results."""

            def __init__(self, output_path: Path, bridge: FeedbackBridge, timeout: float | None):
                self.output_path = output_path
                self.bridge = bridge
                self.timeout = timeout
                self._result = None

            def result(self) -> GradingResult:
                """Block and return the result."""
                return self.bridge.poll_for_result(self.output_path, self.timeout)

        return output_file, AsyncResult(output_file, self, self.timeout)
