"""Tests for session resumption (save/load/resume/list/cleanup)."""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path

import pytest


class TestSessionIndex:
    """Tests for session index with metadata tracking."""

    @pytest.fixture(autouse=True)
    def setup_temp_dir(self, tmp_path: Path) -> None:
        """Create a temporary session directory for each test."""
        self.session_dir = tmp_path / "sessions"
        self.session_dir.mkdir(parents=True, exist_ok=True)
        os.environ["CHECKPOINT_DIR"] = str(tmp_path)

    def teardown_method(self) -> None:
        """Clean up env vars."""
        if "CHECKPOINT_DIR" in os.environ:
            del os.environ["CHECKPOINT_DIR"]

    def test_index_file_created(self) -> None:
        """Test: Session index file created at sessions/index.json after save."""
        from luminamind.config.session_store import FileBackedSessionStore

        store = FileBackedSessionStore(os.environ["CHECKPOINT_DIR"])
        store.get_session("test-thread-001")
        store.save("test-thread-001")

        index_path = self.session_dir / "index.json"
        assert index_path.exists(), "Index file should be created after save"

    def test_index_stores_thread_metadata(self) -> None:
        """Test: Index stores thread_id, created_at, last_accessed, summary, message_count."""
        from luminamind.config.session_store import FileBackedSessionStore

        store = FileBackedSessionStore(os.environ["CHECKPOINT_DIR"])
        thread_id = "test-thread-002"

        # Create session with messages
        session = store.get_session(thread_id)
        session.append_message({"role": "user", "content": "Hello"})
        session.append_message({"role": "assistant", "content": "Hi there"})

        # Update working memory with task
        session.update_working_memory({"current_task": "Test task"})

        # Save session to index
        store.save(thread_id)

        # Read index directly
        index_path = self.session_dir / "index.json"
        with open(index_path) as f:
            index = json.load(f)

        assert thread_id in index["sessions"]
        entry = index["sessions"][thread_id]
        assert entry["thread_id"] == thread_id
        assert "created_at" in entry
        assert "last_accessed" in entry
        assert entry["summary"] == "Test task"
        assert entry["message_count"] == 2

    def test_index_atomic_write(self) -> None:
        """Test: Index writes are atomic (temp file + rename)."""
        from luminamind.config.session_store import FileBackedSessionStore

        store = FileBackedSessionStore(os.environ["CHECKPOINT_DIR"])
        thread_id = "test-thread-atomic"

        store.get_session(thread_id)
        store.save(thread_id)

        index_path = self.session_dir / "index.json"
        assert index_path.exists()

        # Verify it's valid JSON (not half-written)
        with open(index_path) as f:
            data = json.load(f)
            assert "sessions" in data


class TestSaveLoadResume:
    """Tests for save/load/resume functions."""

    @pytest.fixture(autouse=True)
    def setup_temp_dir(self, tmp_path: Path) -> None:
        """Create a temporary session directory for each test."""
        self.session_dir = tmp_path / "sessions"
        self.session_dir.mkdir(parents=True, exist_ok=True)
        os.environ["CHECKPOINT_DIR"] = str(tmp_path)

    def teardown_method(self) -> None:
        """Clean up env vars."""
        if "CHECKPOINT_DIR" in os.environ:
            del os.environ["CHECKPOINT_DIR"]

    def test_save_load_cycle(self) -> None:
        """Test: save() and load() preserve FullTranscript and WorkingMemory."""
        from luminamind.config.session_store import FileBackedSessionStore

        store = FileBackedSessionStore(os.environ["CHECKPOINT_DIR"])
        thread_id = "test-save-load"

        # Create session with data
        session = store.get_session(thread_id)
        session.append_message({"role": "user", "content": "First message"})
        session.append_message({"role": "assistant", "content": "Second message"})
        session.update_working_memory({
            "current_task": "Testing save/load",
            "important_files": ["test.py"],
            "recent_notes": ["Note 1"],
        })

        # Save session
        store.save(thread_id)

        # Create new store instance (simulating restart)
        store2 = FileBackedSessionStore(os.environ["CHECKPOINT_DIR"])

        # Load session
        result = store2.load(thread_id)
        assert result is True

        # Verify session restored
        session2 = store2.get_session(thread_id)
        assert session2.transcript.get_message_count() == 2
        assert session2.working_memory.current_task == "Testing save/load"
        assert "test.py" in session2.working_memory.important_files

    def test_resume_returns_ready_session(self) -> None:
        """Test: resume() returns session ready for use with full state."""
        from luminamind.config.session_store import FileBackedSessionStore

        store = FileBackedSessionStore(os.environ["CHECKPOINT_DIR"])
        thread_id = "test-resume"

        # Create and save session
        session = store.get_session(thread_id)
        session.append_message({"role": "user", "content": "Hello"})
        session.update_working_memory({"current_task": "Resume test"})
        store.save(thread_id)

        # Resume session
        resumed = store.resume(thread_id)
        assert resumed is not None
        assert resumed.transcript.get_message_count() == 1
        assert resumed.working_memory.current_task == "Resume test"

    def test_resume_nonexistent_creates_new(self) -> None:
        """Test: resume() returns new session if thread_id not found."""
        from luminamind.config.session_store import FileBackedSessionStore

        store = FileBackedSessionStore(os.environ["CHECKPOINT_DIR"])

        # Resume non-existent session
        resumed = store.resume("nonexistent-thread")
        assert resumed is not None
        assert resumed.thread_id == "nonexistent-thread"

    def test_load_returns_false_for_missing(self) -> None:
        """Test: load() returns False for nonexistent thread_id."""
        from luminamind.config.session_store import FileBackedSessionStore

        store = FileBackedSessionStore(os.environ["CHECKPOINT_DIR"])

        result = store.load("missing-thread")
        assert result is False


class TestListAndCleanup:
    """Tests for session listing and cleanup."""

    @pytest.fixture(autouse=True)
    def setup_temp_dir(self, tmp_path: Path) -> None:
        """Create a temporary session directory for each test."""
        self.session_dir = tmp_path / "sessions"
        self.session_dir.mkdir(parents=True, exist_ok=True)
        os.environ["CHECKPOINT_DIR"] = str(tmp_path)

    def teardown_method(self) -> None:
        """Clean up env vars."""
        if "CHECKPOINT_DIR" in os.environ:
            del os.environ["CHECKPOINT_DIR"]

    def test_list_returns_all_sessions(self) -> None:
        """Test: list() returns all sessions with metadata."""
        from luminamind.config.session_store import FileBackedSessionStore

        store = FileBackedSessionStore(os.environ["CHECKPOINT_DIR"])

        # Create multiple sessions
        for i in range(3):
            session = store.get_session(f"thread-{i}")
            session.append_message({"role": "user", "content": f"Message {i}"})
            session.update_working_memory({"current_task": f"Task {i}"})
            store.save(f"thread-{i}")

        # List sessions
        sessions = store.list()
        assert len(sessions) == 3

    def test_list_sorted_by_last_accessed(self) -> None:
        """Test: list() returns sessions sorted by last_accessed descending."""
        from luminamind.config.session_store import FileBackedSessionStore

        store = FileBackedSessionStore(os.environ["CHECKPOINT_DIR"])

        # Create sessions
        session1 = store.get_session("thread-old")
        session1.append_message({"role": "user", "content": "Old"})
        store.save("thread-old")

        # Slight delay to ensure different timestamps
        time.sleep(0.01)

        session2 = store.get_session("thread-new")
        session2.append_message({"role": "user", "content": "New"})
        store.save("thread-new")

        # List sessions
        sessions = store.list()
        assert sessions[0]["thread_id"] == "thread-new"
        assert sessions[1]["thread_id"] == "thread-old"

    def test_cleanup_removes_old_sessions(self) -> None:
        """Test: cleanup() removes sessions older than max_age_days."""
        from luminamind.config.session_store import FileBackedSessionStore

        store = FileBackedSessionStore(os.environ["CHECKPOINT_DIR"])

        # Create session
        session = store.get_session("thread-to-cleanup")
        session.append_message({"role": "user", "content": "Old session"})
        store.save("thread-to-cleanup")

        # Manually modify index to make it appear old
        index_path = self.session_dir / "index.json"
        with open(index_path) as f:
            index = json.load(f)

        old_time = (datetime.utcnow() - timedelta(days=31)).isoformat()
        index["sessions"]["thread-to-cleanup"]["last_accessed"] = old_time

        with open(index_path, "w") as f:
            json.dump(index, f)

        # Run cleanup
        removed = store.cleanup(max_age_days=30)
        assert "thread-to-cleanup" in removed

        # Verify session file deleted
        jsonl_file = self.session_dir / "thread-to-cleanup.jsonl"
        assert not jsonl_file.exists()

        # Verify index updated
        with open(index_path) as f:
            index = json.load(f)
            assert "thread-to-cleanup" not in index["sessions"]

    def test_get_session_info(self) -> None:
        """Test: get_session_info() returns metadata for single session."""
        from luminamind.config.session_store import FileBackedSessionStore

        store = FileBackedSessionStore(os.environ["CHECKPOINT_DIR"])

        # Create session
        session = store.get_session("thread-info")
        session.append_message({"role": "user", "content": "Hello"})
        session.update_working_memory({"current_task": "Info test"})
        store.save("thread-info")

        # Get info
        info = store.get_session_info("thread-info")
        assert info is not None
        assert info["thread_id"] == "thread-info"
        assert info["summary"] == "Info test"
        assert info["message_count"] == 1

    def test_get_session_info_returns_none_for_missing(self) -> None:
        """Test: get_session_info() returns None for nonexistent thread."""
        from luminamind.config.session_store import FileBackedSessionStore

        store = FileBackedSessionStore(os.environ["CHECKPOINT_DIR"])

        info = store.get_session_info("missing-thread")
        assert info is None


class TestIntegration:
    """Integration tests for session resumption."""

    @pytest.fixture(autouse=True)
    def setup_temp_dir(self, tmp_path: Path) -> None:
        """Create a temporary session directory for each test."""
        self.session_dir = tmp_path / "sessions"
        self.session_dir.mkdir(parents=True, exist_ok=True)
        os.environ["CHECKPOINT_DIR"] = str(tmp_path)

    def teardown_method(self) -> None:
        """Clean up env vars."""
        if "CHECKPOINT_DIR" in os.environ:
            del os.environ["CHECKPOINT_DIR"]

    def test_full_resume_workflow(self) -> None:
        """Integration: Create session, save, restart, resume."""
        from luminamind.config.session_store import FileBackedSessionStore

        # First instance - create and save
        store1 = FileBackedSessionStore(os.environ["CHECKPOINT_DIR"])
        thread_id = "workflow-thread"

        session = store1.get_session(thread_id)
        session.append_message({"role": "user", "content": "Start conversation"})
        session.append_message({"role": "assistant", "content": "How can I help?"})
        session.update_working_memory({
            "current_task": "Testing workflow",
            "important_files": ["src/main.py"],
            "pending_actions": ["Review output"],
        })
        store1.save(thread_id)

        # Simulate restart - create new instance
        store2 = FileBackedSessionStore(os.environ["CHECKPOINT_DIR"])

        # Resume
        resumed = store2.resume(thread_id)
        assert resumed is not None

        # Verify all state restored
        assert resumed.transcript.get_message_count() == 2
        assert resumed.working_memory.current_task == "Testing workflow"
        assert "src/main.py" in resumed.working_memory.important_files
        assert "Review output" in resumed.working_memory.pending_actions

        # Continue conversation
        resumed.append_message({"role": "user", "content": "Continue"})
        store2.save(thread_id)

        # Verify count increased
        assert resumed.transcript.get_message_count() == 3