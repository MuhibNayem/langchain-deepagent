from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class GracefulShutdown:
    """Tracks graceful shutdown state and deadlines."""
    initiated_at: Optional[datetime] = None
    deadline: Optional[datetime] = None
    tasks_remaining: int = 0

    def start(self, timeout_seconds: int):
        self.initiated_at = datetime.utcnow()
        self.deadline = datetime.utcnow().timestamp() + timeout_seconds

    def is_expired(self) -> bool:
        if self.deadline is None:
            return False
        return datetime.utcnow().timestamp() > self.deadline


@dataclass
class LifecycleManager:
    """Manages worker lifecycle state transitions."""
    
    def __init__(self):
        self._handlers = {
            "on_start": [],
            "on_stop": [],
            "on_task_start": [],
            "on_task_complete": [],
        }

    def register_handler(self, event: str, handler: callable):
        if event in self._handlers:
            self._handlers[event].append(handler)

    def emit(self, event_name: str, **kwargs):
        for handler in self._handlers.get(event_name, []):
            handler(**kwargs)