import json
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import uuid

from .cron_parser import CronExpression, parse_cron


@dataclass
class ScheduledTask:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    cron: Optional[CronExpression] = None  # None = one-shot
    task_type: str = ""
    payload: dict = field(default_factory=dict)
    timezone: str = "UTC"
    run_missed: bool = False
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    total_runs: int = 0


class Scheduler:
    def __init__(self, task_queue, state_file: Optional[str] = None):
        self.task_queue = task_queue
        self.state_file = state_file
        self._tasks: dict[str, ScheduledTask] = {}
        self._lock = threading.Lock()
        self._tick_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def schedule(self, task: ScheduledTask) -> str:
        """Register a scheduled task."""
        with self._lock:
            if task.cron and task.next_run is None:
                task.next_run = task.cron.next_fire_time(datetime.utcnow())
            elif task.next_run is None:
                task.next_run = datetime.utcnow()  # One-shot: run ASAP

            self._tasks[task.id] = task
            self._persist()
            return task.id

    def unschedule(self, task_id: str) -> bool:
        """Remove a scheduled task."""
        with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
                self._persist()
                return True
            return False

    def pause(self, task_id: str) -> bool:
        """Pause a scheduled task."""
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.enabled = False
                self._persist()
                return True
            return False

    def resume(self, task_id: str) -> bool:
        """Resume a paused task."""
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.enabled = True
                if task.cron and task.next_run is None:
                    task.next_run = task.cron.next_fire_time(datetime.utcnow())
                self._persist()
                return True
            return False

    def get_next_runs(self, count: int = 10) -> list[datetime]:
        """Get next N scheduled fire times."""
        with self._lock:
            tasks = [t for t in self._tasks.values() if t.enabled and t.next_run]
            tasks.sort(key=lambda t: t.next_run)
            return [t.next_run for t in tasks[:count]]

    def tick(self) -> list:
        """Check for due tasks and enqueue them. Returns list of enqueued task payloads."""
        with self._lock:
            now = datetime.utcnow()
            due_tasks = []

            for task in self._tasks.values():
                if not task.enabled:
                    continue
                if task.next_run and task.next_run <= now:
                    # Enqueue the task
                    from luminamind.queue import Task, TaskStatus
                    queue_task = Task(
                        type=task.task_type,
                        payload=task.payload,
                    )
                    self.task_queue.enqueue(queue_task)

                    task.last_run = now
                    task.total_runs += 1

                    if task.cron:
                        task.next_run = task.cron.next_fire_time(now)
                    elif task.run_missed:
                        # One-shot with run_missed: re-run
                        task.next_run = now
                    else:
                        task.next_run = None  # One-shot, done

                    due_tasks.append(task)

            if due_tasks:
                self._persist()

            return due_tasks

    def start(self):
        """Start the scheduler tick loop in background thread."""
        if self._tick_thread and self._tick_thread.is_alive():
            return

        self._stop_event.clear()
        self._tick_thread = threading.Thread(target=self._run_loop, daemon=True)
        self._tick_thread.start()

    def stop(self):
        """Stop the scheduler tick loop."""
        self._stop_event.set()
        if self._tick_thread:
            self._tick_thread.join(timeout=5)

    def _run_loop(self):
        """Background tick loop."""
        while not self._stop_event.is_set():
            self.tick()
            self._stop_event.wait(1)  # Tick every second

    def _persist(self):
        """Save state to disk using atomic write (temp file + rename)."""
        if not self.state_file:
            return

        with self._lock:
            data = {
                task_id: {
                    "id": t.id,
                    "name": t.name,
                    "task_type": t.task_type,
                    "payload": t.payload,
                    "timezone": t.timezone,
                    "run_missed": t.run_missed,
                    "enabled": t.enabled,
                    "last_run": t.last_run.isoformat() if t.last_run else None,
                    "next_run": t.next_run.isoformat() if t.next_run else None,
                    "total_runs": t.total_runs,
                    "cron": f"{t.cron.minute} {t.cron.hour} {t.cron.day_of_month} {t.cron.month} {t.cron.day_of_week}" if t.cron else None,
                }
                for task_id, t in self._tasks.items()
            }

        # Atomic write: write to temp file then rename
        import tempfile
        temp_path = self.state_file + ".tmp"
        with open(temp_path, "w") as f:
            json.dump(data, f, indent=2)
        import os
        os.rename(temp_path, self.state_file)

    def _load(self):
        """Load state from disk."""
        if not self.state_file:
            return

        try:
            with open(self.state_file) as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return

        with self._lock:
            for task_id, task_data in data.items():
                task = ScheduledTask(
                    id=task_data["id"],
                    name=task_data["name"],
                    task_type=task_data["task_type"],
                    payload=task_data["payload"],
                    timezone=task_data.get("timezone", "UTC"),
                    run_missed=task_data.get("run_missed", False),
                    enabled=task_data.get("enabled", True),
                    total_runs=task_data.get("total_runs", 0),
                )
                if task_data.get("last_run"):
                    task.last_run = datetime.fromisoformat(task_data["last_run"])
                if task_data.get("next_run"):
                    task.next_run = datetime.fromisoformat(task_data["next_run"])
                if task_data.get("cron"):
                    task.cron = parse_cron(task_data["cron"])
                self._tasks[task.id] = task


def create_scheduler(task_queue, state_file: str = ".luminamind/scheduler.state") -> Scheduler:
    """Factory function to create and load a scheduler."""
    scheduler = Scheduler(task_queue, state_file)
    scheduler._load()
    return scheduler
