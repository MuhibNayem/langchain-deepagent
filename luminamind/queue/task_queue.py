from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import uuid


class Priority(Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DEAD_LETTER = "dead_letter"


@dataclass
class Task:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: str = ""  # "planner", "generator", "evaluator", "sprint"
    payload: dict = field(default_factory=dict)
    priority: Priority = Priority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    attempts: int = 0
    max_attempts: int = 3
    error: Optional[str] = None
    idempotency_key: Optional[str] = None

    @property
    def task_id(self) -> str:
        """Compatibility alias for production worker/result code."""
        return self.id

    @property
    def name(self) -> str:
        """Compatibility alias for task descriptions."""
        return self.type


@dataclass
class QueueMetrics:
    pending: int
    running: int
    completed: int
    failed: int
    dead_letter: int


class RateLimitConfig:
    def __init__(self, max_concurrent: int = 100, namespace: str = "default"):
        self.max_concurrent = max_concurrent
        self.namespace = namespace


class QueueBackend:
    """Interface for queue backends."""
    
    def enqueue(self, task: Task, delay_seconds: int) -> str:
        """Add task to queue. Returns task_id."""
        raise NotImplementedError
    
    def dequeue(self, timeout_seconds: int) -> Optional[Task]:
        """Get next task. Returns None if queue empty."""
        raise NotImplementedError
    
    def ack(self, task_id: str) -> None:
        """Mark task complete."""
        raise NotImplementedError
    
    def nack(self, task_id: str, error: str) -> None:
        """Re-queue failed task with error."""
        raise NotImplementedError
    
    def cancel(self, task_id: str) -> bool:
        """Cancel a task. Returns True if cancelled."""
        raise NotImplementedError
    
    def get_status(self, task_id: str) -> TaskStatus:
        """Get current status of a task."""
        raise NotImplementedError
    
    def get_metrics(self) -> QueueMetrics:
        """Get queue metrics."""
        raise NotImplementedError


class TaskQueue:
    def __init__(self, backend: QueueBackend, rate_limit: RateLimitConfig | None = None):
        self.backend = backend
        self.rate_limit = rate_limit or RateLimitConfig()
        self._idempotency_cache: dict[str, str] = {}  # Only in-memory, not persisted
    
    def enqueue(self, task: Task, delay_seconds: int = 0) -> str:
        # Validate task
        if not isinstance(task.type, str) or not task.type:
            raise ValueError("task.type must be a non-empty string")
        if not isinstance(task.payload, dict):
            raise ValueError("task.payload must be a dict")
        
        # Check idempotency
        if task.idempotency_key:
            if task.idempotency_key in self._idempotency_cache:
                return self._idempotency_cache[task.idempotency_key]
        
        # Check rate limit
        metrics = self.backend.get_metrics()
        if metrics.running >= self.rate_limit.max_concurrent:
            raise RuntimeError(f"Rate limit exceeded: {metrics.running}/{self.rate_limit.max_concurrent} running")
        
        task_id = self.backend.enqueue(task, delay_seconds)
        
        if task.idempotency_key:
            self._idempotency_cache[task.idempotency_key] = task_id
        
        return task_id
    
    def dequeue(self, timeout_seconds: int = 0) -> Optional[Task]:
        """Get next task. Returns None if queue empty."""
        return self.backend.dequeue(timeout_seconds)
    
    def ack(self, task_id: str) -> None:
        """Mark task complete."""
        self.backend.ack(task_id)
    
    def nack(self, task_id: str, error: str) -> None:
        """Re-queue failed task with error."""
        self.backend.nack(task_id, error)
    
    def cancel(self, task_id: str) -> bool:
        """Cancel a task. Returns True if cancelled."""
        return self.backend.cancel(task_id)
    
    def get_status(self, task_id: str) -> TaskStatus:
        """Get current status of a task."""
        return self.backend.get_status(task_id)
    
    def get_metrics(self) -> QueueMetrics:
        """Get queue metrics."""
        return self.backend.get_metrics()
