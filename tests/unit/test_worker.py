import pytest
import threading
import time

from luminamind.worker import Worker, WorkerConfig, WorkerStatus, WorkerRegistry, WorkerInfo, LifecycleManager, GracefulShutdown
from luminamind.queue import MemoryBackend, TaskQueue, Task, Priority


def get_task_queue():
    """Create a TaskQueue with MemoryBackend for testing."""
    return TaskQueue(MemoryBackend())


def test_worker_config_defaults():
    """Test WorkerConfig has sensible defaults."""
    config = WorkerConfig()
    assert config.worker_id == ""
    assert config.queue_name == "default"
    assert config.heartbeat_interval_seconds == 30
    assert config.max_concurrent_tasks == 1
    assert config.graceful_shutdown_timeout_seconds == 60


def test_worker_status_enum():
    """Test WorkerStatus enum values."""
    assert WorkerStatus.STARTING.value == "starting"
    assert WorkerStatus.IDLE.value == "idle"
    assert WorkerStatus.WORKING.value == "working"
    assert WorkerStatus.DRAINING.value == "draining"
    assert WorkerStatus.STOPPED.value == "stopped"


def test_worker_lifecycle():
    """Test Worker starts and stops correctly."""
    config = WorkerConfig(worker_id="test-worker")
    task_queue = get_task_queue()
    worker = Worker(config, task_queue)

    assert worker.status == WorkerStatus.STARTING

    worker.start()
    time.sleep(0.1)
    assert worker.status == WorkerStatus.IDLE
    assert worker._thread is not None
    assert worker._thread.is_alive()

    worker.stop()
    assert worker.status == WorkerStatus.STOPPED


def test_worker_start_idempotent():
    """Test that starting an already running worker is safe."""
    config = WorkerConfig(worker_id="test-worker")
    task_queue = get_task_queue()
    worker = Worker(config, task_queue)

    worker.start()
    first_thread = worker._thread
    worker.start()  # Should be no-op
    assert worker._thread is first_thread

    worker.stop()


def test_worker_graceful_shutdown():
    """Test that graceful shutdown waits for in-flight tasks."""
    config = WorkerConfig(worker_id="test-worker", graceful_shutdown_timeout_seconds=2)
    task_queue = get_task_queue()
    worker = Worker(config, task_queue)

    # Override _process_task to simulate work
    processed = []

    def fake_process(task):
        processed.append(task.id)
        time.sleep(0.2)

    worker._process_task = fake_process
    worker.start()

    # Enqueue a task
    task = Task(type="test", payload={})
    task_queue.enqueue(task)

    # Give task time to be dequeued
    time.sleep(0.3)
    assert len(processed) == 1

    # Stop with graceful=True (default)
    worker.stop(graceful=True)
    assert worker.status == WorkerStatus.STOPPED


def test_worker_task_processing():
    """Test that worker dequeues and acknowledges tasks."""
    config = WorkerConfig(worker_id="test-worker")
    task_queue = get_task_queue()
    worker = Worker(config, task_queue)

    processed = []

    def fake_process(task):
        processed.append(task.id)

    worker._process_task = fake_process
    worker.start()

    # Enqueue tasks
    task1 = Task(type="test", payload={})
    task2 = Task(type="test", payload={})
    task_queue.enqueue(task1)
    task_queue.enqueue(task2)

    # Wait for processing
    time.sleep(0.5)
    assert len(processed) >= 1

    worker.stop()


def test_worker_registry():
    """Test WorkerRegistry tracks workers."""
    registry = WorkerRegistry(ttl_seconds=90)

    config1 = WorkerConfig(worker_id="worker1")
    config2 = WorkerConfig(worker_id="worker2")
    task_queue = get_task_queue()

    worker1 = Worker(config1, task_queue, registry)
    worker2 = Worker(config2, task_queue, registry)

    worker1.start()
    worker2.start()
    time.sleep(0.1)

    assert "worker1" in registry.list_idle_workers()
    assert "worker2" in registry.list_idle_workers()

    worker1.stop()
    time.sleep(0.1)
    assert "worker1" not in registry.list_idle_workers()
    assert "worker2" in registry.list_idle_workers()

    worker2.stop()


def test_worker_registry_stale_detection():
    """Test that stale workers are cleaned up."""
    registry = WorkerRegistry(ttl_seconds=1)

    config = WorkerConfig(worker_id="stale-worker")
    task_queue = get_task_queue()
    worker = Worker(config, task_queue, registry)

    worker.start()
    time.sleep(0.1)
    assert "stale-worker" in registry.list_idle_workers()

    worker.stop()
    # Wait for TTL to expire
    time.sleep(1.2)

    # Stale worker should be cleaned up
    idle_workers = registry.list_idle_workers()
    assert "stale-worker" not in idle_workers


def test_worker_registry_get_worker():
    """Test get_worker returns worker info."""
    registry = WorkerRegistry()

    config = WorkerConfig(worker_id="get-worker")
    task_queue = get_task_queue()
    worker = Worker(config, task_queue, registry)

    worker.start()
    time.sleep(0.1)

    info = registry.get_worker("get-worker")
    assert info is not None
    assert info.worker_id == "get-worker"
    assert info.status == WorkerStatus.IDLE

    worker.stop()


def test_worker_registry_unregister():
    """Test unregister removes worker from registry."""
    registry = WorkerRegistry()

    config = WorkerConfig(worker_id="unreg-worker")
    task_queue = get_task_queue()
    worker = Worker(config, task_queue, registry)

    worker.start()
    time.sleep(0.1)
    assert "unreg-worker" in registry.list_idle_workers()

    worker.stop()
    assert "unreg-worker" not in registry.list_idle_workers()


def test_lifecycle_manager():
    """Test LifecycleManager event handlers."""
    manager = LifecycleManager()

    events = []

    def handler(**kwargs):
        events.append(kwargs.get("name", "unknown"))

    manager.register_handler("on_start", handler)
    manager.register_handler("on_stop", handler)

    manager.emit("on_start", name="on_start")
    manager.emit("on_stop", name="on_stop")

    assert "on_start" in events
    assert "on_stop" in events


def test_graceful_shutdown():
    """Test GracefulShutdown tracks state."""
    shutdown = GracefulShutdown()

    shutdown.start(timeout_seconds=10)
    assert shutdown.initiated_at is not None
    assert shutdown.deadline is not None
    assert not shutdown.is_expired()


def test_worker_with_max_concurrent():
    """Test worker respects max_concurrent_tasks limit."""
    config = WorkerConfig(worker_id="concurrent-worker", max_concurrent_tasks=1)
    task_queue = get_task_queue()
    registry = WorkerRegistry()

    worker = Worker(config, task_queue, registry)
    worker.start()

    # Enqueue multiple tasks - worker should process one at a time
    for i in range(3):
        task_queue.enqueue(Task(type="test", payload={"index": i}))

    # Give time for tasks to be dequeued
    time.sleep(0.5)

    # Acknowledge the tasks to complete them
    # Worker should re-nack tasks when at capacity
    worker.stop()


def test_worker_info_dataclass():
    """Test WorkerInfo holds correct data."""
    info = WorkerInfo(
        worker_id="info-worker",
        status=WorkerStatus.IDLE,
        last_heartbeat=time.time(),
        current_task=None
    )
    assert info.worker_id == "info-worker"
    assert info.status == WorkerStatus.IDLE
    assert info.current_task is None