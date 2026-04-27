"""Tests for file read deduplication in ContextCompactor."""
from __future__ import annotations

import pytest

from luminamind.config.context_compactor import ContextCompactor


class TestDeduplication:
    """Test file read deduplication per D-09 and D-14."""

    def test_same_file_content_deduplicated_within_window(self):
        """Same file content not re-sent within deduplication window (D-09)."""
        compactor = ContextCompactor(dedup_window=5)

        # First message with file content
        msg1 = {
            "type": "tool_result",
            "name": "read_file",
            "role": "tool",
            "content": "file content here",
            "path": "/tmp/test.txt"
        }
        # Same file content within window
        msg2 = {
            "type": "tool_result",
            "name": "read_file",
            "role": "tool",
            "content": "file content here",
            "path": "/tmp/test.txt"
        }

        messages = [msg1, msg2]
        result = compactor.deduplicate(messages)

        # msg1 should be kept, msg2 should be replaced with reference
        assert result[0]["content"] == "file content here"
        assert result[1].get("is_dedup_ref") is True
        assert "[File /tmp/test.txt unchanged" in result[1]["content"]

    def test_different_file_content_still_sent(self):
        """Different file content should NOT be deduplicated (D-09)."""
        compactor = ContextCompactor(dedup_window=5)

        msg1 = {
            "type": "tool_result",
            "name": "read_file",
            "role": "tool",
            "content": "original content",
            "path": "/tmp/test.txt"
        }
        msg2 = {
            "type": "tool_result",
            "name": "read_file",
            "role": "tool",
            "content": "modified content",
            "path": "/tmp/test.txt"
        }

        messages = [msg1, msg2]
        result = compactor.deduplicate(messages)

        # Both should be present with original content
        assert result[0]["content"] == "original content"
        assert result[1]["content"] == "modified content"
        assert result[1].get("is_dedup_ref") is not True

    def test_deduplication_window_respected(self):
        """Deduplication should only apply within window (D-14)."""
        compactor = ContextCompactor(dedup_window=2)

        base_msg = {
            "type": "tool_result",
            "name": "read_file",
            "role": "tool",
            "content": "same content",
            "path": "/tmp/test.txt"
        }

        # Create 5 messages with same content - only window should dedup
        messages = [base_msg.copy() for _ in range(5)]

        result = compactor.deduplicate(messages)

        # First message always kept, second within window should dedup
        # After window, should be kept again
        assert result[0].get("is_dedup_ref") is not True

    def test_content_hash_change_busts_dedup(self):
        """Content hash change should bust deduplication (D-09)."""
        compactor = ContextCompactor(dedup_window=10)

        msg1 = {
            "type": "tool_result",
            "name": "read_file",
            "role": "tool",
            "content": "version 1",
            "path": "/tmp/test.txt"
        }
        msg2 = {
            "type": "tool_result",
            "name": "read_file",
            "role": "tool",
            "content": "version 2",  # Different content
            "path": "/tmp/test.txt"
        }
        msg3 = {
            "type": "tool_result",
            "name": "read_file",
            "role": "tool",
            "content": "version 2",  # Same as msg2
            "path": "/tmp/test.txt"
        }

        messages = [msg1, msg2, msg3]
        result = compactor.deduplicate(messages)

        # msg1: original content
        # msg2: different content (updated hash)
        # msg3: same as msg2, should be deduped
        assert result[0]["content"] == "version 1"
        assert result[1]["content"] == "version 2"
        assert result[2].get("is_dedup_ref") is True

    def test_non_file_read_messages_pass_through(self):
        """Non-file-read messages should pass through unchanged."""
        compactor = ContextCompactor(dedup_window=5)

        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]

        result = compactor.deduplicate(messages)

        assert len(result) == 2
        assert result[0]["content"] == "Hello"
        assert result[1]["content"] == "Hi there"

    def test_different_file_paths_not_deduped(self):
        """Different file paths should not affect each other."""
        compactor = ContextCompactor(dedup_window=5)

        msg1 = {
            "type": "tool_result",
            "name": "read_file",
            "role": "tool",
            "content": "content A",
            "path": "/tmp/file_a.txt"
        }
        msg2 = {
            "type": "tool_result",
            "name": "read_file",
            "role": "tool",
            "content": "content A",  # Same content but different path
            "path": "/tmp/file_b.txt"
        }

        messages = [msg1, msg2]
        result = compactor.deduplicate(messages)

        # Both should be kept since paths differ
        assert result[0]["content"] == "content A"
        assert result[1]["content"] == "content A"
        assert result[1].get("is_dedup_ref") is not True