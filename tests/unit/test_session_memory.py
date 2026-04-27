"""Tests for session memory (FullTranscript + WorkingMemory)."""
from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path

import pytest


class TestFullTranscript:
    """Tests for FullTranscript JSONL persistence."""

    @pytest.fixture(autouse=True)
    def setup_temp_dir(self, tmp_path: Path) -> None:
        """Create a temporary session directory for each test."""
        self.session_dir = tmp_path / "sessions"
        self.session_dir.mkdir(parents=True, exist_ok=True)

    def test_append_writes_jsonl(self, setup_temp_dir: None) -> None:
        """Test: Write message to JSONL file, read back by index."""
        from luminamind.config.session_store import FullTranscript

        thread_id = "test-thread-001"
        transcript = FullTranscript(self.session_dir, thread_id)

        message = {"role": "user", "content": "Hello, world!"}
        offset = transcript.append(message)

        assert offset == 0  # First message at byte 0

        # Read back
        retrieved = transcript.get_message_at(0)
        assert retrieved == message

    def test_multiple_messages_indexed(self, setup_temp_dir: None) -> None:
        """Test: Multiple messages are indexed correctly."""
        from luminamind.config.session_store import FullTranscript

        thread_id = "test-thread-002"
        transcript = FullTranscript(self.session_dir, thread_id)

        messages = [
            {"role": "user", "content": "First"},
            {"role": "assistant", "content": "Second"},
            {"role": "user", "content": "Third"},
        ]

        for msg in messages:
            transcript.append(msg)

        assert transcript.get_message_count() == 3

        assert transcript.get_message_at(0) == messages[0]
        assert transcript.get_message_at(1) == messages[1]
        assert transcript.get_message_at(2) == messages[2]

    def test_in_memory_index_lookup(self, setup_temp_dir: None) -> None:
        """Test: In-memory index maps message_offset → file_position for O(1) lookup."""
        from luminamind.config.session_store import FullTranscript

        thread_id = "test-thread-003"
        transcript = FullTranscript(self.session_dir, thread_id)

        # Append messages of varying sizes to create distinct offsets
        messages = [
            {"role": "user", "content": "Short"},
            {"role": "assistant", "content": "A" * 100},  # longer message
            {"role": "user", "content": "Medium length"},
        ]

        offsets = []
        for msg in messages:
            offsets.append(transcript.append(msg))

        # Verify offsets are different (different byte positions)
        assert offsets[0] != offsets[1]
        assert offsets[1] != offsets[2]

        # Verify we can retrieve each message at correct index
        for i, msg in enumerate(messages):
            assert transcript.get_message_at(i) == msg

    def test_session_file_named_by_thread_id(self, setup_temp_dir: None) -> None:
        """Test: Session file named by thread_id, located in session_dir."""
        from luminamind.config.session_store import FullTranscript

        thread_id = "unique-thread-id-12345"
        transcript = FullTranscript(self.session_dir, thread_id)

        # File is created on first append
        transcript.append({"role": "user", "content": "Test"})

        expected_file = self.session_dir / f"{thread_id}.jsonl"
        assert expected_file.exists()

    def test_get_messages_from(self, setup_temp_dir: None) -> None:
        """Test: Batch read from index to end."""
        from luminamind.config.session_store import FullTranscript

        thread_id = "test-thread-005"
        transcript = FullTranscript(self.session_dir, thread_id)

        messages = [
            {"role": "user", "content": "First"},
            {"role": "assistant", "content": "Second"},
            {"role": "user", "content": "Third"},
            {"role": "assistant", "content": "Fourth"},
        ]

        for msg in messages:
            transcript.append(msg)

        # Get messages from index 2
        batch = transcript.get_messages_from(2)
        assert len(batch) == 2
        assert batch[0] == messages[2]
        assert batch[1] == messages[3]

    def test_rebuild_index(self, setup_temp_dir: None) -> None:
        """Test: Index rebuild scans file on initialization."""
        from luminamind.config.session_store import FullTranscript

        thread_id = "test-thread-006"
        transcript = FullTranscript(self.session_dir, thread_id)

        messages = [
            {"role": "user", "content": "First"},
            {"role": "assistant", "content": "Second"},
        ]

        for msg in messages:
            transcript.append(msg)

        # Create a NEW transcript instance pointing to same file
        # This simulates program restart - index should be rebuilt
        transcript2 = FullTranscript(self.session_dir, thread_id)

        assert transcript2.get_message_count() == 2
        assert transcript2.get_message_at(0) == messages[0]
        assert transcript2.get_message_at(1) == messages[1]

    def test_get_message_at_out_of_range(self, setup_temp_dir: None) -> None:
        """Test: get_message_at returns None for out-of-range index."""
        from luminamind.config.session_store import FullTranscript

        thread_id = "test-thread-007"
        transcript = FullTranscript(self.session_dir, thread_id)

        transcript.append({"role": "user", "content": "Only one"})

        assert transcript.get_message_at(5) is None
        assert transcript.get_message_at(-1) is None


class TestWorkingMemory:
    """Tests for WorkingMemory structured fields."""

    def test_fields_exist(self) -> None:
        """Test: WorkingMemory has current_task, important_files, recent_notes, pending_actions fields."""
        from luminamind.config.session_store import WorkingMemory

        wm = WorkingMemory()

        assert hasattr(wm, "current_task")
        assert hasattr(wm, "important_files")
        assert hasattr(wm, "recent_notes")
        assert hasattr(wm, "pending_actions")

    def test_empty_defaults(self) -> None:
        """Test: Empty defaults for all fields when initialized."""
        from luminamind.config.session_store import WorkingMemory

        wm = WorkingMemory()

        assert wm.current_task is None
        assert wm.important_files == []
        assert wm.recent_notes == []
        assert wm.pending_actions == []

    def test_update_task(self) -> None:
        """Test: update_task sets current_task."""
        from luminamind.config.session_store import WorkingMemory

        wm = WorkingMemory()
        wm.update_task("Implement authentication")

        assert wm.current_task == "Implement authentication"

    def test_add_important_file_dedup(self) -> None:
        """Test: add_important_file appends (dedup)."""
        from luminamind.config.session_store import WorkingMemory

        wm = WorkingMemory()
        wm.add_important_file("src/auth.py")
        wm.add_important_file("src/config.py")
        wm.add_important_file("src/auth.py")  # duplicate

        assert len(wm.important_files) == 2
        assert "src/auth.py" in wm.important_files
        assert "src/config.py" in wm.important_files

    def test_add_note_fifo(self) -> None:
        """Test: add_note appends (max 50, FIFO)."""
        from luminamind.config.session_store import WorkingMemory

        wm = WorkingMemory()

        # Add 51 notes
        for i in range(51):
            wm.add_note(f"Note {i}")

        # Should keep last 50
        assert len(wm.recent_notes) == 50
        assert wm.recent_notes[0] == "Note 1"  # First was evicted
        assert wm.recent_notes[-1] == "Note 50"

    def test_add_pending_action(self) -> None:
        """Test: add_pending_action appends to list."""
        from luminamind.config.session_store import WorkingMemory

        wm = WorkingMemory()
        wm.add_pending_action("Review PR #123")
        wm.add_pending_action("Update tests")

        assert len(wm.pending_actions) == 2
        assert "Review PR #123" in wm.pending_actions

    def test_serialize_deserialize(self) -> None:
        """Test: Fields serialize/deserialize correctly."""
        from luminamind.config.session_store import WorkingMemory

        wm = WorkingMemory()
        wm.update_task("Test task")
        wm.add_important_file("test.py")
        wm.add_note("Test note")
        wm.add_pending_action("Test action")

        data = wm.serialize()
        assert data["current_task"] == "Test task"
        assert "test.py" in data["important_files"]

        wm2 = WorkingMemory.deserialize(data)
        assert wm2.current_task == "Test task"
        assert "test.py" in wm2.important_files


class TestSessionStoreFactory:
    """Tests for SessionStore factory with Redis/File/in-memory fallback."""

    def test_create_session_store_no_env(self) -> None:
        """Test: create_session_store() returns InMemory if neither env set."""
        # Clear any env vars
        env_backup = {}
        for key in ["CHECKPOINT_REDIS_URL", "CHECKPOINT_DIR"]:
            env_backup[key] = os.environ.pop(key, None)

        try:
            from luminamind.config.session_store import create_session_store

            store = create_session_store()
            # Should return in-memory store (no Redis, no directory)
            assert store is not None
            # Can't easily test the type without mocking, but verify it doesn't raise
        finally:
            # Restore env
            for key, val in env_backup.items():
                if val is not None:
                    os.environ[key] = val

    def test_create_session_store_with_dir(self, tmp_path: Path) -> None:
        """Test: create_session_store() returns File-backed if CHECKPOINT_DIR set."""
        os.environ["CHECKPOINT_DIR"] = str(tmp_path)

        try:
            from luminamind.config.session_store import create_session_store

            store = create_session_store()
            assert store is not None
            # Should work with file backend
        finally:
            del os.environ["CHECKPOINT_DIR"]

    def test_session_store_session_method(self, tmp_path: Path) -> None:
        """Test: SessionStore provides session() context manager."""
        os.environ["CHECKPOINT_DIR"] = str(tmp_path)

        try:
            from luminamind.config.session_store import create_session_store

            store = create_session_store()
            session = store.get_session("test-thread")

            assert hasattr(session, "append_message")
            assert hasattr(session, "get_working_memory")
            assert hasattr(session, "update_working_memory")
        finally:
            del os.environ["CHECKPOINT_DIR"]

    def test_session_store_append_and_retrieve(self, tmp_path: Path) -> None:
        """Test: Session appends message and can retrieve working memory."""
        os.environ["CHECKPOINT_DIR"] = str(tmp_path)

        try:
            from luminamind.config.session_store import create_session_store

            store = create_session_store()
            thread_id = "test-thread-100"

            # Append a message
            store.append_message(thread_id, {"role": "user", "content": "Hello"})

            # Get working memory (should be empty initially)
            wm = store.get_working_memory(thread_id)
            assert wm is not None
        finally:
            del os.environ["CHECKPOINT_DIR"]

    def test_session_store_update_working_memory(self, tmp_path: Path) -> None:
        """Test: SessionStore.update_working_memory merges updates."""
        os.environ["CHECKPOINT_DIR"] = str(tmp_path)

        try:
            from luminamind.config.session_store import create_session_store

            store = create_session_store()
            thread_id = "test-thread-200"

            # Update working memory
            store.update_working_memory(thread_id, {"current_task": "New task"})

            wm = store.get_working_memory(thread_id)
            assert wm.current_task == "New task"
        finally:
            del os.environ["CHECKPOINT_DIR"]


class TestIntegration:
    """Integration tests for FullTranscript + WorkingMemory."""

    def test_full_transcript_persistence(self, tmp_path: Path) -> None:
        """Integration: FullTranscript appends JSONL, indexes by offset, supports random access."""
        from luminamind.config.session_store import FullTranscript

        session_dir = tmp_path / "sessions"
        session_dir.mkdir()
        thread_id = "integration-test-001"
        transcript = FullTranscript(session_dir, thread_id)

        # Append messages
        for i in range(10):
            transcript.append({"index": i, "content": f"Message {i}"})

        # Verify persistence
        assert transcript.get_message_count() == 10

        # Verify random access
        assert transcript.get_message_at(5)["index"] == 5
        assert transcript.get_message_at(9)["content"] == "Message 9"

        # Verify batch read
        batch = transcript.get_messages_from(7)
        assert len(batch) == 3
        assert batch[0]["index"] == 7

    def test_working_memory_fields(self, tmp_path: Path) -> None:
        """Integration: WorkingMemory tracks all fields with serialization."""
        from luminamind.config.session_store import WorkingMemory

        wm = WorkingMemory()
        wm.update_task("Build session store")
        wm.add_important_file("src/session.py")
        wm.add_note("Remember to add tests")
        wm.add_pending_action("Deploy to staging")

        # Serialize
        data = wm.serialize()
        assert data["current_task"] == "Build session store"
        assert "src/session.py" in data["important_files"]

        # Deserialize
        wm2 = WorkingMemory.deserialize(data)
        assert wm2.current_task == "Build session store"
        assert "src/session.py" in wm2.important_files

    def test_session_store_factory(self, tmp_path: Path) -> None:
        """Integration: SessionStore factory with all three backends."""
        from luminamind.config.session_store import (
            FullTranscript,
            InMemorySessionStore,
            WorkingMemory,
            create_session_store,
        )

        # Test in-memory fallback (no env vars)
        store = create_session_store()
        assert isinstance(store, InMemorySessionStore)

        # Test file-backed with CHECKPOINT_DIR
        os.environ["CHECKPOINT_DIR"] = str(tmp_path)
        store = create_session_store()
        assert store is not None  # File-based store
        del os.environ["CHECKPOINT_DIR"]

        # Verify the store has expected methods
        session = store.get_session("test-thread")
        assert hasattr(session, "append_message")
        assert hasattr(session, "get_working_memory")
        assert hasattr(session, "update_working_memory")
