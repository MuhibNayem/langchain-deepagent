"""Production-grade task worker with Celery-like semantics.

Provides:
- Task execution loop with retry, idempotency, timeout
- Worker lifecycle management
- Result backends (memory/Redis)
- Task acknowledgment and rejection
- Delayed/scheduled task support
- Dead letter queue for failed tasks
"""
from __future__ import annotations

import logging
import threading
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable
import concurrent.futures

from luminamind.queue.memory_backend import MemoryBackend
from luminamind.queue.task_queue import Priority, Task, TaskStatus

logger = logging.getLogger(__name__)


class WorkerMode(Enum):
    """Worker execution modes."""
    SPRING = "spring"  # Spawn agent per task
    STREAM = "stream"  # Long-running agent with task stream


@dataclass
class WorkerConfig:
    """Configuration for the task worker."""
    max_workers: int = 4
    max_retries: int = 3
    retry_delay: float = 5.0
    retry_multiplier: float = 2.0
    max_retry_delay: float = 300.0
    task_timeout: int | None = 600
    idle_timeout: int = 300
    poll_interval: float = 1.0
    mode: WorkerMode = WorkerMode.SPRING
    backend_url: str | None = None  # None = in-memory


@dataclass
class WorkerResult:
    """Result from a worker task execution."""
    task_id: str
    success: bool
    result: Any = None
    error: str | None = None
    execution_time: float = 0.0
    retry_count: int = 0
    worker_id: str | None = None


class ResultBackend(ABC):
    """Abstract result backend."""

    @abstractmethod
    def store_result(self, task_id: str, result: WorkerResult) -> None:
        pass

    @abstractmethod
    def get_result(self, task_id: str) -> WorkerResult | None:
        pass

    @abstractmethod
    def mark_done(self, task_id: str) -> None:
        pass

    @abstractmethod
    def is_done(self, task_id: str) -> bool:
        pass


class MemoryResultBackend:
    """In-memory result backend for single-worker setups."""

    def __init__(self):
        self._results: dict[str, WorkerResult] = {}
        self._done: set[str] = set()
        self._lock = threading.Lock()

    def store_result(self, task_id: str, result: WorkerResult) -> None:
        with self._lock:
            self._results[task_id] = result

    def get_result(self, task_id: str) -> WorkerResult | None:
        with self._lock:
            return self._results.get(task_id)

    def mark_done(self, task_id: str) -> None:
        with self._lock:
            self._done.add(task_id)

    def is_done(self, task_id: str) -> bool:
        with self._lock:
            return task_id in self._done


class TaskExecutor:
    """Executor that wraps agent functions for task worker.

    This is the core bridge between the queue system and actual agent execution.
    """

    def __init__(self, mode: WorkerMode = WorkerMode.SPRING):
        self.mode = mode
        self._active_agents: dict[str, Any] = {}
        self._lock = threading.Lock()

    def execute(self, task: Task, worker_id: str) -> WorkerResult:
        """Execute a task and return the result.

        Args:
            task: The task to execute
            worker_id: ID of this worker

        Returns:
            WorkerResult with success/error info
        """
        start = time.time()
        task_id = task.task_id

        try:
            logger.info(f"[{worker_id}] Executing task {task_id}: {task.name}")

            if self.mode == WorkerMode.SPRING:
                result = self._execute_spring(task)
            else:
                result = self._execute_stream(task)

            elapsed = time.time() - start
            return WorkerResult(
                task_id=task_id,
                success=True,
                result=result,
                execution_time=elapsed,
                retry_count=task.attempts - 1,
                worker_id=worker_id,
            )

        except Exception as e:
            elapsed = time.time() - start
            logger.error(f"[{worker_id}] Task {task_id} failed: {e}")
            return WorkerResult(
                task_id=task_id,
                success=False,
                error=str(e),
                execution_time=elapsed,
                retry_count=task.attempts - 1,
                worker_id=worker_id,
            )

    def _execute_spring(self, task: Task) -> Any:
        """Spawn a new agent for each task (Celery-like)."""
        from luminamind.deep_agent import create_deep_agent

        agent = create_deep_agent()
        if hasattr(agent, "run"):
            if hasattr(agent, "run_async"):
                import asyncio
                return asyncio.run(agent.run_async(task.payload.get("task", task.name)))
            return agent.run(task.payload.get("task", task.name))
        raise RuntimeError("DeepAgent missing run() method")

    def _execute_stream(self, task: Task) -> Any:
        """Reuse a long-running agent for multiple tasks."""
        agent_id = task.payload.get("agent_id")
        with self._lock:
            if agent_id not in self._active_agents:
                from luminamind.deep_agent import create_deep_agent
                self._active_agents[agent_id] = create_deep_agent()
            agent = self._active_agents[agent_id]

        if hasattr(agent, "run"):
            return agent.run(task.payload.get("task", task.name))
        raise RuntimeError("DeepAgent missing run() method")


class TaskWorker:
    """Production-grade task worker with retry, timeout, and lifecycle management.

    This is the core execution engine that:
    1. Polls the queue for ready tasks
    2. Executes them with configurable retry semantics
    3. Reports results back
    4. Handles dead letter queue for poison tasks

    Usage:
        worker = TaskWorker(config=WorkerConfig(max_workers=4))
        worker.start()  # Starts processing in background threads
        worker.stop()   # Graceful shutdown
    """

    def __init__(self, config: WorkerConfig | None = None, queue_backend=None, result_backend=None):
        self.config = config or WorkerConfig()
        self._worker_id = str(uuid.uuid4())[:8]
        self._running = False
        self._executor_thread: threading.Thread | None = None
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.config.max_workers)

        # Queue backend (default to in-memory)
        if queue_backend is None:
            self._queue = MemoryBackend()
        else:
            self._queue = queue_backend

        # Result backend
        self._result_backend = result_backend or MemoryResultBackend()

        # Task executor
        self._task_executor = TaskExecutor(mode=self.config.mode)

        # Shutdown event
        self._shutdown = threading.Event()
        self._lock = threading.Lock()

        # Metrics
        self._metrics = {
            "processed": 0,
            "succeeded": 0,
            "failed": 0,
            "retried": 0,
        }

    def start(self) -> None:
        """Start the worker in background threads."""
        if self._running:
            logger.warning(f"Worker {self._worker_id} already running")
            return

        self._running = True
        self._shutdown.clear()

        # Start polling thread
        self._executor_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._executor_thread.start()

        logger.info(f"Worker {self._worker_id} started with {self.config.max_workers} threads")

    def stop(self, wait: bool = True) -> None:
        """Stop the worker gracefully."""
        if not self._running:
            return

        logger.info(f"Stopping worker {self._worker_id}...")
        self._running = False
        self._shutdown.set()

        if wait and self._executor_thread:
            self._executor_thread.join(timeout=30)

        self._executor.shutdown(wait=wait)
        logger.info(f"Worker {self._worker_id} stopped")

    def _poll_loop(self) -> None:
        """Main polling loop - continuously dequeue and execute tasks."""
        while self._running and not self._shutdown.is_set():
            try:
                task = self._queue.dequeue(timeout_seconds=self.config.poll_interval)
                if task is None:
                    continue

                # Submit to executor pool
                self._executor.submit(self._execute_with_retry, task)

            except Exception as e:
                logger.error(f"Worker {self._worker_id} poll error: {e}")
                time.sleep(1)

    def _execute_with_retry(self, task: Task) -> None:
        """Execute a task with retry logic."""
        max_retries = self.config.max_retries
        attempt = task.attempts

        # Check if task was already completed
        if self._result_backend.is_done(task.task_id):
            logger.debug(f"Task {task.task_id} already completed, skipping")
            return

        result = self._task_executor.execute(task, self._worker_id)

        if result.success:
            self._result_backend.store_result(task.task_id, result)
            self._result_backend.mark_done(task.task_id)
            self._queue.ack(task.task_id)
            self._metrics["succeeded"] += 1
            self._metrics["processed"] += 1
            logger.info(f"Task {task.task_id} completed successfully")
            return

        # Failure - check if we should retry
        if attempt < max_retries:
            # Calculate delay with exponential backoff
            delay = min(
                self.config.retry_delay * (self.config.retry_multiplier ** attempt),
                self.config.max_retry_delay,
            )

            logger.info(f"Task {task.task_id} failed (attempt {attempt + 1}/{max_retries}), "
                        f"retrying in {delay:.1f}s: {result.error}")

            # Re-enqueue with delay
            task.attempts += 1
            self._queue.enqueue(task, delay_seconds=delay)
            self._metrics["retried"] += 1
        else:
            # Max retries exceeded - move to dead letter
            logger.error(f"Task {task.task_id} failed permanently after {max_retries} attempts: {result.error}")
            self._result_backend.store_result(task.task_id, result)
            self._result_backend.mark_done(task.task_id)
            self._queue.nack(task.task_id, result.error or "Max retries exceeded")
            self._metrics["failed"] += 1
            self._metrics["processed"] += 1

    def get_metrics(self) -> dict:
        """Get worker metrics."""
        return dict(self._metrics)

    @property
    def worker_id(self) -> str:
        """Get this worker's ID."""
        return self._worker_id

    @property
    def is_running(self) -> bool:
        """Check if worker is running."""
        return self._running


class SwarmWorker:
    """Worker that integrates with Swarm for multi-agent task execution.

    This extends TaskWorker to:
    1. Use Swarm.spawn() to create agents
    2. Route tasks through swarm message queue
    3. Track agent lifecycle and health
    4. Coordinate multi-agent work via swarm consensus
    """

    def __init__(self, swarm, config: WorkerConfig | None = None):
        self.swarm = swarm
        self.config = config or WorkerConfig()
        self._worker_id = str(uuid.uuid4())[:8]
        self._running = False
        self._threads: list[threading.Thread] = []
        self._shutdown = threading.Event()
        self._task_executor = TaskExecutor(mode=self.config.mode)

    def start(self) -> None:
        """Start the swarm worker."""
        if self._running:
            return

        self._running = True

        roles = ["planner", "generator", "reviewer"]
        with self.swarm._lock:
            active_count = sum(1 for agent in self.swarm._agents.values() if agent.status != "dead")
            available_slots = max(self.swarm.config.max_agents - active_count, 0)

        # Start only consumers that can actually spawn an agent.
        for role_name in roles[:available_slots]:
            t = threading.Thread(target=self._consume_messages, args=(role_name,), daemon=True)
            t.start()
            self._threads.append(t)

        logger.info(f"SwarmWorker {self._worker_id} started")

    def stop(self) -> None:
        """Stop the swarm worker."""
        self._running = False
        self._shutdown.set()
        for t in self._threads:
            t.join(timeout=10)
        logger.info(f"SwarmWorker {self._worker_id} stopped")

    def _consume_messages(self, role_name: str) -> None:
        """Consume messages from swarm queue for this role."""
        from luminamind.swarm.roles import AgentRole

        role = AgentRole(role_name)
        try:
            agent_id = self.swarm.spawn(role=role)
        except RuntimeError as exc:
            logger.warning(f"SwarmWorker could not spawn {role_name} consumer: {exc}")
            return

        while self._running and not self._shutdown.is_set():
            # Get messages for this agent from swarm
            messages = self._get_messages_for_agent(agent_id)
            for msg in messages:
                self._execute_message(msg, agent_id)
            time.sleep(1)

    def _get_messages_for_agent(self, agent_id: str) -> list:
        """Get pending messages for this agent from swarm queue."""
        # This polls the internal queue - in production, use message_bus
        messages = []
        with self.swarm._lock:
            for msg in self.swarm._message_queue:
                if msg.recipient_id == agent_id or msg.recipient_id is None:
                    messages.append(msg)
        return messages

    def _execute_message(self, message, agent_id: str) -> None:
        """Execute a message and report outcome back to swarm."""
        task = Task(
            id=message.payload.get("task_id", str(uuid.uuid4())),
            type=message.payload.get("task_name", "swarm_task"),
            payload=message.payload,
        )
        result = self._task_executor.execute(task, self._worker_id)

        # Report result back to swarm
        from luminamind.swarm.swarm import SwarmMessage
        response = SwarmMessage(
            sender_id=agent_id,
            recipient_id=message.sender_id,
            message_type="task_result",
            payload={
                "task_id": task.task_id,
                "success": result.success,
                "result": result.result,
                "error": result.error,
            },
        )
        self.swarm.send_to(message.sender_id, response)
