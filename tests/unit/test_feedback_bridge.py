"""Unit tests for FeedbackBridge - file-based generator-evaluator communication.

Tests cover:
- File write/read format
- Async polling
- Timeout handling
- Session isolation
"""
import pytest
import time
import tempfile
from pathlib import Path
from unittest.mock import Mock
from luminamind.evaluator.feedback_bridge import FeedbackBridge, FeedbackMessage
from luminamind.evaluator.agent import GradingResult


class TestFeedbackBridge:
    """Test FeedbackBridge file-based communication."""

    def test_file_write_read(self, tmp_path):
        """Test: Bridge writes artifact to input file and reads result from output file."""
        bridge = FeedbackBridge(bridge_dir=tmp_path)
        mock_evaluator = Mock()
        mock_evaluator.evaluate.return_value = GradingResult(
            score=85.0, issues=["style"], feedback="Good", iteration=1
        )

        result = bridge.send_for_evaluation(
            artifact="code content",
            evaluator=mock_evaluator,
            session_id="test-session",
            iteration=1,
        )

        # Verify result
        assert result.score == 85.0
        assert result.issues == ["style"]

        # Verify input file was created
        input_file = tmp_path / "test-session_1_input.json"
        assert input_file.exists(), "Input file should be created"

        # Verify output file was created
        output_file = tmp_path / "test-session_1_output.json"
        assert output_file.exists(), "Output file should be created"

    def test_async_polling(self, tmp_path):
        """Test: send_for_evaluation_async returns immediately with Future."""
        bridge = FeedbackBridge(bridge_dir=tmp_path, poll_interval=0.1)
        output_file = tmp_path / "test_1_output.json"

        # Create output file with valid content before polling
        output_file.write_text(
            '{"grading_result": {"score": 80.0, "issues": [], "feedback": "", "iteration": 1}}'
        )

        result = bridge.poll_for_result(output_file, timeout=2.0)
        assert result.score == 80.0

    def test_poll_timeout(self, tmp_path):
        """Test: Timeout triggers if evaluation takes too long."""
        bridge = FeedbackBridge(bridge_dir=tmp_path, poll_interval=0.1, timeout=0.5)
        output_file = tmp_path / "nonexistent_1_output.json"

        with pytest.raises(TimeoutError):
            bridge.poll_for_result(output_file, timeout=0.5)

    def test_session_isolation(self, tmp_path):
        """Test: Session isolation per session_id."""
        bridge = FeedbackBridge(bridge_dir=tmp_path)
        assert bridge.bridge_dir == tmp_path

        # Different sessions should use different files
        session1_file = tmp_path / "session1_1_input.json"
        session2_file = tmp_path / "session2_1_input.json"

        # Write to session1
        session1_file.write_text('{"test": "data1"}')
        assert session1_file.exists()
        assert not session2_file.exists()

    def test_feedback_message_format(self, tmp_path):
        """Test: FeedbackMessage has correct structure."""
        msg = FeedbackMessage(
            session_id="test-session",
            iteration=1,
            artifact_type="code",
            artifact_content="def hello(): pass",
            metadata={"timestamp": time.time()},
        )

        assert msg.session_id == "test-session"
        assert msg.iteration == 1
        assert msg.artifact_type == "code"
        assert msg.artifact_content == "def hello(): pass"
        assert "timestamp" in msg.metadata

    def test_unique_session_files_per_iteration(self, tmp_path):
        """Test: Bridge creates unique session files per iteration."""
        bridge = FeedbackBridge(bridge_dir=tmp_path)
        mock_evaluator = Mock()
        mock_evaluator.evaluate.return_value = GradingResult(
            score=90.0, issues=[], feedback="", iteration=1
        )

        # Send for evaluation with iteration 1
        bridge.send_for_evaluation(
            artifact="code v1",
            evaluator=mock_evaluator,
            session_id="test",
            iteration=1,
        )

        # Send for evaluation with iteration 2
        mock_evaluator.evaluate.return_value = GradingResult(
            score=95.0, issues=[], feedback="", iteration=2
        )
        bridge.send_for_evaluation(
            artifact="code v2",
            evaluator=mock_evaluator,
            session_id="test",
            iteration=2,
        )

        # Both input files should exist
        assert (tmp_path / "test_1_input.json").exists()
        assert (tmp_path / "test_2_input.json").exists()

        # Output files should also exist
        assert (tmp_path / "test_1_output.json").exists()
        assert (tmp_path / "test_2_output.json").exists()

    def test_evaluation_result_parsing(self, tmp_path):
        """Test: Bridge correctly parses GradingResult from output file."""
        bridge = FeedbackBridge(bridge_dir=tmp_path, poll_interval=0.01)

        # Create a properly formatted output file
        output_file = tmp_path / "parse_test_1_output.json"
        output_file.write_text(
            """{
                "session_id": "parse-test",
                "iteration": 1,
                "grading_result": {
                    "score": 75.5,
                    "issues": ["issue1", "issue2"],
                    "feedback": "Needs work",
                    "iteration": 2
                },
                "evaluation_context": null
            }"""
        )

        result = bridge.poll_for_result(output_file, timeout=1.0)
        assert result.score == 75.5
        assert result.issues == ["issue1", "issue2"]
        assert result.feedback == "Needs work"
        assert result.iteration == 2
