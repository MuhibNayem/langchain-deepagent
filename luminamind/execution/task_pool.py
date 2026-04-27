from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable
import concurrent.futures
import threading

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class Task:
    """A unit of work for parallel execution."""
    task_id: str
    name: str
    func: Callable[..., Any]  # The function to execute
    args: tuple = field(default_factory=())
    kwargs: dict[str, Any] = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)  # task_ids this depends on
    priority: int = 0  # Higher = earlier execution
    timeout: int | None = None  # Seconds, None = no timeout
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

@dataclass
class TaskResult:
    """Result of a task execution."""
    task_id: str
    success: bool
    result: Any = None
    error: str | None = None
    execution_time: float = 0.0

class TaskPool:
    """Pool for parallel task execution."""

    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self._tasks: dict[str, Task] = {}
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        self._futures: dict[str, concurrent.futures.Future] = {}
        self._lock = threading.Lock()

    def submit(self, task: Task) -> str:
        """Submit a task for execution.

        Returns task_id.
        """
        with self._lock:
            self._tasks[task.task_id] = task

        # Submit to executor
        future = self._executor.submit(self._execute_task, task)
        self._futures[task.task_id] = future

        return task.task_id

    def _execute_task(self, task: Task) -> TaskResult:
        """Execute a single task."""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()

        try:
            if task.timeout:
                import signal
                # Set timeout alarm
                signal.alarm(int(task.timeout))

            result = task.func(*task.args, **task.kwargs)

            if task.timeout:
                signal.alarm(0)  # Cancel alarm

            task.status = TaskStatus.COMPLETED
            task.result = result
            task.completed_at = datetime.now()

            return TaskResult(
                task_id=task.task_id,
                success=True,
                result=result,
                execution_time=(datetime.now() - task.started_at).total_seconds()
            )
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.now()

            return TaskResult(
                task_id=task.task_id,
                success=False,
                error=str(e),
                execution_time=(datetime.now() - task.started_at).total_seconds()
            )

    def get_result(self, task_id: str, timeout: float | None = None) -> TaskResult | None:
        """Get result of a task, optionally waiting for completion."""
        future = self._futures.get(task_id)
        if not future:
            return None

        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            return None

    def wait_all(self, timeout: float | None = None) -> list[TaskResult]:
        """Wait for all submitted tasks to complete."""
        results = []
        for task_id, future in self._futures.items():
            try:
                results.append(future.result(timeout=timeout))
            except concurrent.futures.TimeoutError:
                results.append(TaskResult(
                    task_id=task_id,
                    success=False,
                    error="Timeout waiting for result"
                ))
        return results

    def execute_with_dependencies(self, tasks: list[Task]) -> list[TaskResult]:
        """Execute tasks respecting dependencies.

        Uses DependencyGraph to determine execution order and parallelization.
        """
        from luminamind.execution.dependency_graph import DependencyGraph

        graph = DependencyGraph()
        for task in tasks:
            graph.add_node(task.task_id, task.dependencies)

        validation = graph.validate()
        if validation:
            raise ValueError(f"Invalid task dependencies: {validation}")

        batches = graph.get_execution_order()
        all_results = []

        for batch in batches:
            # Submit all tasks in this batch
            for task_id in batch:
                task = next(t for t in tasks if t.task_id == task_id)
                self.submit(task)

            # Wait for batch to complete
            batch_results = self.wait_all()
            all_results.extend(batch_results)

        return all_results

    def shutdown(self, wait: bool = True):
        """Shutdown the task pool."""
        self._executor.shutdown(wait=wait)