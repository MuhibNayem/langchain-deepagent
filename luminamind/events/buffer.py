from collections import deque
from datetime import datetime
from typing import List
import threading

from luminamind.events.schema import AgentEvent


class EventBuffer:
    """Thread-safe event buffer with replay capability.

    Uses event_id-based lookup instead of positional indices to avoid
    corruption when deque rotates (items shift but event_ids stay constant).
    """

    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self._buffer: deque[AgentEvent] = deque(maxlen=max_size)
        self._by_id: dict[str, AgentEvent] = {}  # event_id -> event (authoritative)
        self._lock = threading.Lock()
        self._session_index: dict[str, list[str]] = {}  # session_id -> [event_ids]
        self._task_index: dict[str, list[str]] = {}  # task_id -> [event_ids]

    def append(self, event: AgentEvent) -> None:
        """Add event to buffer."""
        with self._lock:
            evicted = self._buffer[0] if len(self._buffer) == self.max_size else None
            self._buffer.append(event)
            if evicted is not None and evicted.event_id != event.event_id:
                self._remove_indexes(evicted)
            self._by_id[event.event_id] = event
            if event.session_id:
                if event.session_id not in self._session_index:
                    self._session_index[event.session_id] = []
                self._session_index[event.session_id].append(event.event_id)
            if event.task_id:
                if event.task_id not in self._task_index:
                    self._task_index[event.task_id] = []
                self._task_index[event.task_id].append(event.event_id)

    def _remove_indexes(self, event: AgentEvent) -> None:
        """Remove an event from lookup indexes after eviction."""
        self._by_id.pop(event.event_id, None)
        if event.session_id and event.session_id in self._session_index:
            self._session_index[event.session_id] = [
                eid for eid in self._session_index[event.session_id] if eid != event.event_id
            ]
            if not self._session_index[event.session_id]:
                del self._session_index[event.session_id]
        if event.task_id and event.task_id in self._task_index:
            self._task_index[event.task_id] = [
                eid for eid in self._task_index[event.task_id] if eid != event.event_id
            ]
            if not self._task_index[event.task_id]:
                del self._task_index[event.task_id]

    def get(self, event_id: str) -> AgentEvent | None:
        """Get event by ID."""
        with self._lock:
            return self._by_id.get(event_id)

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
                if eid in self._by_id:
                    result.append(self._by_id[eid])
            return result

    def get_session_events(self, session_id: str, limit: int | None = None) -> list[AgentEvent]:
        """Get all events for a session."""
        with self._lock:
            if session_id not in self._session_index:
                return []
            event_ids = self._session_index[session_id]
            result = [self._by_id[eid] for eid in event_ids if eid in self._by_id]
            if limit:
                return result[-limit:]
            return result

    def get_task_events(self, task_id: str) -> list[AgentEvent]:
        """Get all events for a task."""
        with self._lock:
            if task_id not in self._task_index:
                return []
            event_ids = self._task_index[task_id]
            return [self._by_id[eid] for eid in event_ids if eid in self._by_id]

    def clear_oldest(self, count: int) -> list[AgentEvent]:
        """Remove and return oldest events."""
        with self._lock:
            result = []
            for _ in range(min(count, len(self._buffer))):
                event = self._buffer.popleft()
                result.append(event)
                self._remove_indexes(event)
            return result

    def size(self) -> int:
        """Current buffer size."""
        with self._lock:
            return len(self._buffer)
