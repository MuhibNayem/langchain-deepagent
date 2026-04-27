from collections import deque
from datetime import datetime
from typing import List
import threading

from luminamind.events.schema import AgentEvent


class EventBuffer:
    """Thread-safe event buffer with replay capability."""

    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self._buffer: deque[AgentEvent] = deque(maxlen=max_size)
        self._index: dict[str, int] = {}  # event_id -> position
        self._lock = threading.Lock()
        self._session_index: dict[str, list[str]] = {}  # session_id -> [event_ids]
        self._task_index: dict[str, list[str]] = {}  # task_id -> [event_ids]

    def append(self, event: AgentEvent) -> None:
        """Add event to buffer."""
        with self._lock:
            idx = len(self._buffer)
            self._buffer.append(event)
            self._index[event.event_id] = idx
            if event.session_id:
                if event.session_id not in self._session_index:
                    self._session_index[event.session_id] = []
                self._session_index[event.session_id].append(event.event_id)
            if event.task_id:
                if event.task_id not in self._task_index:
                    self._task_index[event.task_id] = []
                self._task_index[event.task_id].append(event.event_id)

    def get(self, event_id: str) -> AgentEvent | None:
        """Get event by ID."""
        with self._lock:
            if event_id not in self._index:
                return None
            idx = self._index[event_id]
            if 0 <= idx < len(self._buffer):
                return self._buffer[idx]
            return None

    def replay(self, session_id: str, from_event_id: str | None = None,
               to_event_id: str | None = None) -> list[AgentEvent]:
        """Replay events for a session, optionally from/to specific events."""
        with self._lock:
            if session_id not in self._session_index:
                return []
            event_ids = self._session_index[session_id]
            result = []
            start_idx = 0
            end_idx = len(event_ids)

            if from_event_id:
                try:
                    start_idx = event_ids.index(from_event_id) + 1
                except ValueError:
                    pass
            if to_event_id:
                try:
                    end_idx = event_ids.index(to_event_id)
                except ValueError:
                    pass

            for eid in event_ids[start_idx:end_idx]:
                if eid in self._index:
                    event = self._buffer[self._index[eid]]
                    result.append(event)
            return result

    def get_session_events(self, session_id: str, limit: int | None = None) -> list[AgentEvent]:
        """Get all events for a session."""
        with self._lock:
            if session_id not in self._session_index:
                return []
            event_ids = self._session_index[session_id]
            result = []
            for eid in event_ids:
                if eid in self._index:
                    result.append(self._buffer[self._index[eid]])
            if limit:
                return result[-limit:]
            return result

    def get_task_events(self, task_id: str) -> list[AgentEvent]:
        """Get all events for a task."""
        with self._lock:
            if task_id not in self._task_index:
                return []
            event_ids = self._task_index[task_id]
            result = []
            for eid in event_ids:
                if eid in self._index:
                    result.append(self._buffer[self._index[eid]])
            return result

    def clear_oldest(self, count: int) -> list[AgentEvent]:
        """Remove and return oldest events."""
        with self._lock:
            result = []
            for _ in range(min(count, len(self._buffer))):
                event = self._buffer.popleft()
                result.append(event)
                if event.event_id in self._index:
                    del self._index[event.event_id]
            return result

    def size(self) -> int:
        """Current buffer size."""
        with self._lock:
            return len(self._buffer)