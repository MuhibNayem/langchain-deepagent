import threading
import signal
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Any


class WorkerStatus(Enum):
    STARTING = "starting"
    IDLE = "idle"
    WORKING = "working"
    DRAINING = "draining"
    STOPPED = "stopped"


@dataclass
class WorkerConfig:
    """Unified worker configuration.

    The legacy Worker uses the queue/heartbeat fields. The production
    TaskWorker uses the pool/retry fields. Keeping one public config preserves
    old imports while allowing the modern worker APIs to share it.
    """
    worker_id: str = ""
    queue_name: str = "default"
    heartbeat_interval_seconds: int = 30
    max_concurrent_tasks: int = 1
    graceful_shutdown_timeout_seconds: int = 60
    max_workers: int = 4
    max_retries: int = 3
    retry_delay: float = 5.0
    retry_multiplier: float = 2.0
    max_retry_delay: float = 300.0
    task_timeout: int | None = 600
    idle_timeout: int = 300
    poll_interval: float = 1.0
    mode: Any = None
    backend_url: str | None = None

    def __post_init__(self) -> None:
        if self.mode is None:
            from luminamind.worker.producer import WorkerMode
            self.mode = WorkerMode.SPRING


class Worker:
    def __init__(self, config: WorkerConfig, task_queue, registry: "WorkerRegistry" = None):
        self.config = config
        self.task_queue = task_queue
        self.registry = registry
        self.status = WorkerStatus.STARTING
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._tasks_in_flight: list[str] = []
        self._lock = threading.Lock()

    def start(self):
        """Start the worker."""
        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()
        self.status = WorkerStatus.IDLE
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

        if self.registry:
            self.registry.register(self)

    def stop(self, graceful: bool = True):
        """Stop the worker."""
        self._stop_event.set()

        if graceful:
            self.status = WorkerStatus.DRAINING
            self._drain_tasks()

        if self._thread:
            self._thread.join(timeout=30)

        if self.registry:
            self.registry.unregister(self.config.worker_id)

        self.status = WorkerStatus.STOPPED

    def _run_loop(self):
        """Main worker loop."""
        while not self._stop_event.is_set():
            try:
                task = self.task_queue.dequeue(timeout_seconds=1)
                if task:
                    with self._lock:
                        if len(self._tasks_in_flight) >= self.config.max_concurrent_tasks:
                            # Re-queue for another worker
                            self.task_queue.nack(task.id, "worker at capacity")
                            continue
                        self._tasks_in_flight.append(task.id)

                    self.status = WorkerStatus.WORKING
                    self._process_task(task)

                    with self._lock:
                        if task.id in self._tasks_in_flight:
                            self._tasks_in_flight.remove(task.id)
                    self.task_queue.ack(task.id)
                    self.status = WorkerStatus.IDLE
            except Exception as e:
                # Log error, continue
                pass

    def _process_task(self, task):
        """Process a single task. Override in subclass."""
        # Default: just acknowledge. Real impl would call agent.
        pass

    def _drain_tasks(self):
        """Wait for in-flight tasks to complete."""
        deadline = datetime.utcnow().timestamp() + self.config.graceful_shutdown_timeout_seconds
        while datetime.utcnow().timestamp() < deadline:
            with self._lock:
                if not self._tasks_in_flight:
                    return
            import time
            time.sleep(0.1)
