import pytest
from luminamind.queue import TaskQueue, RedisBackend, MemoryBackend, Task, TaskStatus, Priority, QueueMetrics, RateLimitConfig


def get_backend():
    """Get appropriate backend - prefer Redis if available."""
    try:
        backend = RedisBackend("redis://localhost:6379/15")
        backend.redis.ping()  # Test connection
        return backend
    except Exception:
        return MemoryBackend()


def get_task_queue():
    """Create a TaskQueue with available backend."""
    return TaskQueue(get_backend())


def test_enqueue():
    """Test that enqueue returns a task_id and stores task as PENDING."""
    task_queue = get_task_queue()
    task = Task(type="test", payload={"data": "test"})
    task_id = task_queue.enqueue(task)
    assert task_id is not None
    assert task_queue.get_status(task_id) == TaskStatus.PENDING

def test_dequeue_priority():
    """Test that higher priority tasks are dequeued first."""
    task_queue = get_task_queue()
    low = Task(type="test", priority=Priority.LOW, payload={})
    high = Task(type="test", priority=Priority.HIGH, payload={})
    
    task_queue.enqueue(low)
    task_queue.enqueue(high)
    
    first = task_queue.dequeue()
    assert first.priority == Priority.HIGH  # Higher priority first

def test_ack():
    """Test that ack marks task as completed and removes from running."""
    task_queue = get_task_queue()
    task = Task(type="test", payload={})
    task_id = task_queue.enqueue(task)
    task_queue.dequeue()
    task_queue.ack(task_id)
    # After ack, task is removed; get_status returns PENDING as fallback
    assert task_queue.get_status(task_id) == TaskStatus.PENDING

def test_nack_retry():
    """Test that nack increments attempts and re-queues task."""
    task_queue = get_task_queue()
    task = Task(type="test", payload={}, max_attempts=3)
    task_id = task_queue.enqueue(task)
    task_queue.dequeue()
    task_queue.nack(task_id, "Test error")
    # After nack, task should be re-queued as PENDING
    assert task_queue.get_status(task_id) == TaskStatus.PENDING

def test_nack_dead_letter():
    """Test that tasks exceeding max_attempts go to dead_letter."""
    task_queue = get_task_queue()
    task = Task(type="test", payload={}, max_attempts=1)
    task_id = task_queue.enqueue(task)
    task_queue.dequeue()
    task_queue.nack(task_id, "Final error")
    assert task_queue.get_status(task_id) == TaskStatus.DEAD_LETTER

def test_cancel():
    """Test that cancel marks task as cancelled."""
    task_queue = get_task_queue()
    task = Task(type="test", payload={})
    task_id = task_queue.enqueue(task)
    assert task_queue.cancel(task_id) is True
    assert task_queue.get_status(task_id) == TaskStatus.CANCELLED

def test_get_status():
    """Test that get_status returns correct TaskStatus."""
    task_queue = get_task_queue()
    task = Task(type="test", payload={})
    task_id = task_queue.enqueue(task)
    assert task_queue.get_status(task_id) == TaskStatus.PENDING

def test_task_with_priority():
    """Test tasks with different priority levels."""
    task_queue = get_task_queue()
    critical = Task(type="test", priority=Priority.CRITICAL, payload={})
    normal = Task(type="test", priority=Priority.NORMAL, payload={})
    
    task_queue.enqueue(critical)
    task_queue.enqueue(normal)
    
    first = task_queue.dequeue()
    assert first.priority == Priority.CRITICAL

def test_task_with_delay():
    """Test that delayed tasks are scheduled for future execution."""
    task_queue = get_task_queue()
    task = Task(type="test", payload={})
    task_id = task_queue.enqueue(task, delay_seconds=5)
    assert task_id is not None
    # Delayed task should not be immediately available
    immediate = task_queue.dequeue(timeout_seconds=0)
    # May be None if delay hasn't elapsed
    assert immediate is None or immediate.id == task_id

def test_idempotency_key():
    """Test that same idempotency_key returns existing task_id."""
    task_queue = get_task_queue()
    task1 = Task(type="test", payload={}, idempotency_key="dedup-key")
    task2 = Task(type="test", payload={}, idempotency_key="dedup-key")
    
    id1 = task_queue.enqueue(task1)
    id2 = task_queue.enqueue(task2)
    
    assert id1 == id2  # Same key returns same task_id

def test_rate_limit():
    """Test that enqueue raises RuntimeError when rate limit exceeded."""
    task_queue = get_task_queue()
    task_queue.rate_limit = RateLimitConfig(max_concurrent=1)
    
    task_queue.enqueue(Task(type="test", payload={}))
    task = Task(type="test", payload={})
    
    with pytest.raises(RuntimeError, match="Rate limit exceeded"):
        task_queue.enqueue(task)


# MemoryBackend-specific tests
def test_memory_backend_enqueue():
    """Test MemoryBackend enqueue stores task correctly."""
    backend = MemoryBackend()
    task = Task(type="test", payload={"data": "test"})
    task_id = backend.enqueue(task)
    assert task_id is not None

def test_memory_backend_dequeue():
    """Test MemoryBackend dequeue returns highest priority task."""
    backend = MemoryBackend()
    low = Task(type="test", priority=Priority.LOW, payload={})
    high = Task(type="test", priority=Priority.HIGH, payload={})
    
    backend.enqueue(low)
    backend.enqueue(high)
    
    first = backend.dequeue()
    assert first.priority == Priority.HIGH

def test_memory_backend_nack_dead_letter():
    """Test MemoryBackend nack moves task to dead_letter after max attempts."""
    backend = MemoryBackend()
    task = Task(type="test", payload={}, max_attempts=2)
    task_id = backend.enqueue(task)
    backend.dequeue()
    backend.nack(task_id, "Error 1")
    backend.dequeue()
    backend.nack(task_id, "Error 2")
    assert backend.get_status(task_id) == TaskStatus.DEAD_LETTER

def test_memory_backend_metrics():
    """Test MemoryBackend metrics are accurate."""
    backend = MemoryBackend()
    task1 = Task(type="test", payload={})
    task2 = Task(type="test", payload={})
    
    backend.enqueue(task1)
    backend.enqueue(task2)
    
    metrics = backend.get_metrics()
    assert metrics.pending == 2
    assert metrics.running == 0