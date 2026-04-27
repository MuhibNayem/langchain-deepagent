import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from .worker import Worker, WorkerStatus


@dataclass
class WorkerInfo:
    worker_id: str
    status: WorkerStatus
    last_heartbeat: datetime
    current_task: Optional[str] = None


class WorkerRegistry:
    """Registry for worker discovery and health monitoring."""

    def __init__(self, ttl_seconds: int = 90):
        self._workers: dict[str, WorkerInfo] = {}
        self._lock = threading.Lock()
        self._ttl = ttl_seconds

    def register(self, worker: Worker):
        with self._lock:
            self._workers[worker.config.worker_id] = WorkerInfo(
                worker_id=worker.config.worker_id,
                status=worker.status,
                last_heartbeat=datetime.utcnow(),
            )

    def unregister(self, worker_id: str):
        with self._lock:
            self._workers.pop(worker_id, None)

    def get_worker(self, worker_id: str) -> Optional[WorkerInfo]:
        with self._lock:
            info = self._workers.get(worker_id)
            if info and self._is_stale(info):
                del self._workers[worker_id]
                return None
            return info

    def list_idle_workers(self) -> list[str]:
        with self._lock:
            self._cleanup_stale()
            return [w.worker_id for w in self._workers.values() if w.status == WorkerStatus.IDLE]

    def update_heartbeat(self, worker_id: str):
        with self._lock:
            if worker_id in self._workers:
                self._workers[worker_id].last_heartbeat = datetime.utcnow()

    def _is_stale(self, info: WorkerInfo) -> bool:
        age = (datetime.utcnow() - info.last_heartbeat).total_seconds()
        return age > self._ttl

    def _cleanup_stale(self):
        stale = [wid for wid, info in self._workers.items() if self._is_stale(info)]
        for wid in stale:
            del self._workers[wid]