import threading
import time
from typing import Optional
from datetime import datetime

from .task_queue import Task, TaskStatus, Priority, QueueBackend, QueueMetrics


class MemoryBackend(QueueBackend):
    """In-memory queue backend for testing or when Redis unavailable."""
    
    def __init__(self):
        self._pending: list[Task] = []
        self._running: dict[str, Task] = {}
        self._dead_letter: list[Task] = []
        self._lock = threading.Lock()
    
    def enqueue(self, task: Task, delay_seconds: int = 0) -> str:
        with self._lock:
            if delay_seconds > 0:
                task.scheduled_at = datetime.utcnow()
            
            task.status = TaskStatus.PENDING
            # Insert in priority order (higher priority first)
            insert_pos = len(self._pending)
            for i, t in enumerate(self._pending):
                if t.priority.value < task.priority.value:
                    insert_pos = i
                    break
            self._pending.insert(insert_pos, task)
            return task.id
    
    def dequeue(self, timeout_seconds: int = 0) -> Optional[Task]:
        deadline = time.time() + timeout_seconds if timeout_seconds > 0 else None
        
        with self._lock:
            while True:
                # Check for due delayed tasks AND get next non-delayed task
                now = datetime.utcnow().timestamp()
                i = 0
                while i < len(self._pending):
                    task = self._pending[i]
                    # Task is due (no delay or delay expired)
                    if not task.scheduled_at or task.scheduled_at.timestamp() <= now:
                        self._pending.pop(i)
                        task.status = TaskStatus.RUNNING
                        task.started_at = datetime.utcnow()
                        self._running[task.id] = task
                        return task
                    i += 1
                
                # No tasks available
                if timeout_seconds == 0:
                    return None
                
                remaining = deadline - time.time()
                if remaining <= 0:
                    return None
                
                # Wait for new tasks (simplified — real impl would use threading.Event)
                time.sleep(min(0.1, remaining))
    
    def ack(self, task_id: str) -> None:
        with self._lock:
            self._running.pop(task_id, None)
    
    def nack(self, task_id: str, error: str) -> None:
        with self._lock:
            task = self._running.pop(task_id, None)
            if not task:
                return
            
            task.attempts += 1
            task.error = error
            
            if task.attempts >= task.max_attempts:
                task.status = TaskStatus.DEAD_LETTER
                # Store by ID for get_status lookup
                self._dead_letter.append(task)
            else:
                task.status = TaskStatus.PENDING
                task.started_at = None
                # Re-queue with exponential backoff
                backoff = 2 ** task.attempts
                task.scheduled_at = datetime.fromtimestamp(time.time() + backoff)
                self._pending.append(task)
    
    def cancel(self, task_id: str) -> bool:
        with self._lock:
            for task in self._pending:
                if task.id == task_id:
                    task.status = TaskStatus.CANCELLED
                    self._pending.remove(task)
                    return True
            if task_id in self._running:
                self._running[task_id].status = TaskStatus.CANCELLED
                del self._running[task_id]
                return True
            return False
    
    def get_status(self, task_id: str) -> TaskStatus:
        with self._lock:
            for task in self._pending:
                if task.id == task_id:
                    return task.status
            if task_id in self._running:
                return self._running[task_id].status
            for task in self._dead_letter:
                if task.id == task_id:
                    return task.status
            return TaskStatus.PENDING
    
    def get_metrics(self) -> QueueMetrics:
        with self._lock:
            return QueueMetrics(
                pending=len(self._pending),
                running=len(self._running),
                completed=0,
                failed=0,
                dead_letter=len(self._dead_letter),
            )