"""Two-layer session memory architecture.

FullTranscript: JSONL file persistence + in-memory index for O(1) message lookup.
WorkingMemory: Structured state with current_task, important_files, recent_notes, pending_actions.
SessionStore: Factory with Redis → File → in-memory fallback (mirrors create_checkpointer).
"""
from __future__ import annotations

import json
import os
import pickle
from pathlib import Path
from typing import Any

try:
    from redis import Redis
    from redis.exceptions import RedisError
except ImportError:  # pragma: no cover
    Redis = None  # type: ignore[assignment]
    RedisError = Exception  # type: ignore[misc,assignment]

from pydantic import BaseModel


# Default session directory
DEFAULT_SESSION_DIR = Path.home() / ".luminamind" / "sessions"

# Redis key for session state
REDIS_SESSION_KEY = os.environ.get("CHECKPOINT_REDIS_KEY", "langgraph:sessions")


class FullTranscript:
    """Full conversation transcript with JSONL persistence and in-memory index.

    JSONL file per session, one JSON object per line.
    In-memory index maps message index → byte offset for O(1) lookup.
    """

    def __init__(self, session_dir: Path | str, thread_id: str) -> None:
        """Initialize FullTranscript for a session.

        Args:
            session_dir: Directory for session JSONL files
            thread_id: Unique session identifier (used as filename)
        """
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.thread_id = thread_id
        self.session_file = self.session_dir / f"{thread_id}.jsonl"

        # In-memory index: message_index -> byte_offset
        self._index: list[int] = []

        # Rebuild index from existing file on init
        self._rebuild_index()

    def append(self, message: dict) -> int:
        """Write message to JSONL file, return byte offset.

        Args:
            message: Message dict to serialize as JSON

        Returns:
            Byte offset where message was written
        """
        # Get current file size (end of file = our offset)
        offset = self.session_file.stat().st_size if self.session_file.exists() else 0

        # Write JSON line + newline
        with open(self.session_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(message, ensure_ascii=False) + "\n")

        # Record in index
        self._index.append(offset)

        return offset

    def get_message_at(self, index: int) -> dict | None:
        """Get message at given index by seeking to byte offset.

        Args:
            index: Message index (0-based)

        Returns:
            Message dict or None if index out of range
        """
        if index < 0 or index >= len(self._index):
            return None

        offset = self._index[index]

        # Read from offset to end of relevant section
        with open(self.session_file, "r", encoding="utf-8") as f:
            f.seek(offset)
            line = f.readline()
            if line:
                return json.loads(line.strip())
            return None

    def get_messages_from(self, start_index: int) -> list[dict]:
        """Batch read messages from start_index to end.

        Args:
            start_index: Starting message index (0-based)

        Returns:
            List of message dicts from start to end
        """
        messages = []
        for i in range(start_index, len(self._index)):
            msg = self.get_message_at(i)
            if msg is not None:
                messages.append(msg)
        return messages

    def get_message_count(self) -> int:
        """Get total message count.

        Returns:
            Number of messages in transcript
        """
        return len(self._index)

    def _rebuild_index(self) -> None:
        """Rebuild in-memory index by scanning JSONL file.

        On initialization, scans the file to build offset map.
        Also called after potential external modifications.
        """
        self._index = []

        if not self.session_file.exists():
            return

        with open(self.session_file, "r", encoding="utf-8") as f:
            offset = 0
            while True:
                line = f.readline()
                if not line:
                    break
                self._index.append(offset)
                offset = f.tell()


class WorkingMemory(BaseModel):
    """Structured working state for agent context.

    Fields:
        current_task: Current task description (str | None)
        important_files: List of important file paths
        recent_notes: List of recent notes (max 50, FIFO)
        pending_actions: List of pending action descriptions
    """

    current_task: str | None = None
    important_files: list[str] = []
    recent_notes: list[str] = []
    pending_actions: list[str] = []

    # Max notes to keep (FIFO)
    MAX_RECENT_NOTES: int = 50

    def update_task(self, task: str) -> None:
        """Set current_task.

        Args:
            task: Task description
        """
        self.current_task = task

    def add_important_file(self, path: str) -> None:
        """Add file path to important_files (dedup).

        Args:
            path: File path to add
        """
        if path not in self.important_files:
            self.important_files.append(path)

    def add_note(self, note: str) -> None:
        """Add note to recent_notes (max 50, FIFO).

        Args:
            note: Note content to add
        """
        self.recent_notes.append(note)
        # Enforce max size - FIFO eviction
        if len(self.recent_notes) > self.MAX_RECENT_NOTES:
            self.recent_notes.pop(0)

    def add_pending_action(self, action: str) -> None:
        """Add action to pending_actions.

        Args:
            action: Action description
        """
        self.pending_actions.append(action)

    def serialize(self) -> dict:
        """Serialize to dict for checkpointer integration.

        Returns:
            Dict representation
        """
        return self.model_dump()

    @classmethod
    def deserialize(cls, data: dict) -> "WorkingMemory":
        """Restore from checkpointer state.

        Args:
            data: Dict from serialize()

        Returns:
            WorkingMemory instance
        """
        return cls(**data)


class Session:
    """A session combining FullTranscript + WorkingMemory."""

    def __init__(
        self,
        thread_id: str,
        transcript: FullTranscript,
        working_memory: WorkingMemory,
    ) -> None:
        self.thread_id = thread_id
        self.transcript = transcript
        self.working_memory = working_memory

    def append_message(self, message: dict) -> None:
        """Append message to transcript.

        Args:
            message: Message dict to append
        """
        self.transcript.append(message)

    def get_working_memory(self) -> WorkingMemory:
        """Get working memory."""
        return self.working_memory

    def update_working_memory(self, updates: dict) -> None:
        """Merge updates into working memory.

        Args:
            updates: Dict with fields to update
        """
        if "current_task" in updates:
            self.working_memory.update_task(updates["current_task"])
        if "important_files" in updates:
            for f in updates["important_files"]:
                self.working_memory.add_important_file(f)
        if "recent_notes" in updates:
            for note in updates["recent_notes"]:
                self.working_memory.add_note(note)
        if "pending_actions" in updates:
            for action in updates["pending_actions"]:
                self.working_memory.add_pending_action(action)

    def compact(self) -> None:
        """Compact working memory (placeholder for D-04)."""
        # D-04: Compaction runs on each agent turn - implemented in later phase
        pass


class InMemorySessionStore:
    """In-memory session store (fallback when no Redis or File configured)."""

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def get_session(self, thread_id: str) -> Session:
        """Get or create session for thread_id.

        Args:
            thread_id: Session identifier

        Returns:
            Session instance
        """
        if thread_id not in self._sessions:
            # Use default in-memory paths (no persistence)
            transcript = FullTranscript(DEFAULT_SESSION_DIR, thread_id)
            working_memory = WorkingMemory()
            self._sessions[thread_id] = Session(
                thread_id, transcript, working_memory
            )
        return self._sessions[thread_id]

    def append_message(self, thread_id: str, message: dict) -> None:
        """Append message to session transcript.

        Args:
            thread_id: Session identifier
            message: Message dict
        """
        session = self.get_session(thread_id)
        session.append_message(message)

    def get_working_memory(self, thread_id: str) -> WorkingMemory:
        """Get working memory for session.

        Args:
            thread_id: Session identifier

        Returns:
            WorkingMemory instance
        """
        session = self.get_session(thread_id)
        return session.get_working_memory()

    def update_working_memory(self, thread_id: str, updates: dict) -> None:
        """Merge updates into session working memory.

        Args:
            thread_id: Session identifier
            updates: Dict with fields to update
        """
        session = self.get_session(thread_id)
        session.update_working_memory(updates)


class FileBackedSessionStore:
    """File-backed session store using CHECKPOINT_DIR."""

    def __init__(self, directory: str | Path) -> None:
        self.dir = Path(directory)
        self.session_dir = self.dir / "sessions"
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.state_file = self.dir / "session_state.pkl"
        self._sessions: dict[str, Session] = {}
        self._load()

    def _load(self) -> None:
        """Load session state from pickle file."""
        if not self.state_file.exists():
            return
        try:
            data = self.state_file.read_bytes()
            if data:
                self._sessions = pickle.loads(data)
        except Exception:
            pass

    def _persist(self) -> None:
        """Persist session state to pickle file."""
        try:
            self.state_file.write_bytes(pickle.dumps(self._sessions))
        except Exception:
            pass

    def get_session(self, thread_id: str) -> Session:
        """Get or create session for thread_id.

        Args:
            thread_id: Session identifier

        Returns:
            Session instance
        """
        if thread_id not in self._sessions:
            transcript = FullTranscript(self.session_dir, thread_id)
            working_memory = WorkingMemory()
            self._sessions[thread_id] = Session(
                thread_id, transcript, working_memory
            )
        return self._sessions[thread_id]

    def append_message(self, thread_id: str, message: dict) -> None:
        """Append message to session transcript.

        Args:
            thread_id: Session identifier
            message: Message dict
        """
        session = self.get_session(thread_id)
        session.append_message(message)
        self._persist()

    def get_working_memory(self, thread_id: str) -> WorkingMemory:
        """Get working memory for session.

        Args:
            thread_id: Session identifier

        Returns:
            WorkingMemory instance
        """
        session = self.get_session(thread_id)
        return session.get_working_memory()

    def update_working_memory(self, thread_id: str, updates: dict) -> None:
        """Merge updates into session working memory.

        Args:
            thread_id: Session identifier
            updates: Dict with fields to update
        """
        session = self.get_session(thread_id)
        session.update_working_memory(updates)
        self._persist()


class RedisBackedSessionStore:
    """Redis-backed session store for distributed sessions."""

    def __init__(self, client: Redis, key: str = REDIS_SESSION_KEY) -> None:
        self.redis = client
        self.key = key
        self._sessions: dict[str, Session] = {}
        self._loaded = False

    def _ensure_loaded(self) -> None:
        """Load state from Redis if not yet loaded."""
        if self._loaded:
            return
        self._loaded = True
        try:
            payload = self.redis.get(self.key)
            if payload:
                self._sessions = pickle.loads(payload)
        except RedisError:
            pass

    def _persist(self) -> None:
        """Persist state to Redis."""
        try:
            self.redis.set(self.key, pickle.dumps(self._sessions))
        except RedisError:
            pass

    def get_session(self, thread_id: str) -> Session:
        """Get or create session for thread_id.

        Args:
            thread_id: Session identifier

        Returns:
            Session instance
        """
        self._ensure_loaded()
        if thread_id not in self._sessions:
            # Redis store doesn't persist JSONL - just working memory in Redis
            working_memory = WorkingMemory()
            # For FullTranscript in Redis mode, we could use Redis JSON
            # but for now, use in-memory with Redis state persistence
            transcript = FullTranscript(DEFAULT_SESSION_DIR, thread_id)
            self._sessions[thread_id] = Session(
                thread_id, transcript, working_memory
            )
        return self._sessions[thread_id]

    def append_message(self, thread_id: str, message: dict) -> None:
        """Append message to session transcript.

        Args:
            thread_id: Session identifier
            message: Message dict
        """
        session = self.get_session(thread_id)
        session.append_message(message)
        self._persist()

    def get_working_memory(self, thread_id: str) -> WorkingMemory:
        """Get working memory for session.

        Args:
            thread_id: Session identifier

        Returns:
            WorkingMemory instance
        """
        self._ensure_loaded()
        session = self.get_session(thread_id)
        return session.get_working_memory()

    def update_working_memory(self, thread_id: str, updates: dict) -> None:
        """Merge updates into session working memory.

        Args:
            thread_id: Session identifier
            updates: Dict with fields to update
        """
        session = self.get_session(thread_id)
        session.update_working_memory(updates)
        self._persist()


def create_session_store() -> InMemorySessionStore | FileBackedSessionStore | RedisBackedSessionStore:
    """Factory mirroring create_checkpointer pattern.

    Priority: Redis (if CHECKPOINT_REDIS_URL) → File (if CHECKPOINT_DIR) → In-memory

    Returns:
        SessionStore instance (Redis, File, or InMemory)
    """
    redis_url = os.environ.get("CHECKPOINT_REDIS_URL")
    if redis_url:
        if Redis is None:
            raise ImportError("redis package required for RedisBackedSessionStore")
        client = Redis.from_url(redis_url, decode_responses=False)
        return RedisBackedSessionStore(client, REDIS_SESSION_KEY)

    directory = os.environ.get("CHECKPOINT_DIR")
    if directory:
        return FileBackedSessionStore(directory)

    return InMemorySessionStore()


# Alias for backwards compatibility with plan exports
SessionMemory = Session

__all__ = [
    "FullTranscript",
    "WorkingMemory",
    "Session",
    "SessionMemory",
    "InMemorySessionStore",
    "FileBackedSessionStore",
    "RedisBackedSessionStore",
    "create_session_store",
]
