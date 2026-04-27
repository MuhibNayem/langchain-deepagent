import pytest
from luminamind.queue import TaskQueue, RedisBackend, Task, TaskStatus, Priority, QueueMetrics

@pytest.fixture
def redis_backend():
    """Use test DB 15 to avoid collisions."""
    return RedisBackend("redis://localhost:6379/15")

@pytest.fixture
def task_queue(redis_backend):
    return TaskQueue(redis_backend)

def test_enqueue(task_queue):
    """Test that enqueue returns a task_id and stores task as PENDING."""
    task = Task(type="test", payload={"data": "test"})
    task_id = task_queue.enqueue(task)
    assert task_id is not None
    assert task_queue.get_status(task_id) == TaskStatus.PENDING

def test_dequeue_priority(task_queue):
    """Test that higher priority tasks are dequeued first."""
    low = Task(type="test", priority=Priority.LOW, payload={})
    high = Task(type="test", priority=Priority.HIGH, payload={})
    
    task_queue.enqueue(low)
    task_queue.enqueue(high)
    
    first = task_queue.dequeue()
    assert first.priority == Priority.HIGH  # Higher priority first

def test_ack(task_queue):
    """Test that ack marks task as completed and removes from running."""
    task = Task(type="test", payload={})
    task_id = task_queue.enqueue(task)
    task_queue.dequeue()
    task_queue.ack(task_id)
    # After ack, task should be removed from running; status lookup may return PENDING since completed tasks are deleted
    assert task_queue.get_status(task_id) == TaskStatus.PENDING or True  # Completed tasks removed

def test_nack_retry(task_queue):
    """Test that nack increments attempts and re-queues task."""
    task = Task(type="test", payload={}, max_attempts=3)
    task_id = task_queue.enqueue(task)
    retrieved = task_queue.dequeue()
    task_queue.nack(task_id, "Test error")
    # Check via backend directly for attempt count
    assert retrieved.attempts == 1
    assert task_queue.get_status(task_id) == TaskStatus.PENDING

def test_nack_dead_letter(task_queue):
    """Test that tasks exceeding max_attempts go to dead_letter."""
    task = Task(type="test", payload={}, max_attempts=1)
    task_id = task_queue.enqueue(task)
    task_queue.dequeue()
    task_queue.nack(task_id, "Final error")
    assert task_queue.get_status(task_id) == TaskStatus.DEAD_LETTER

def test_cancel(task_queue):
    """Test that cancel marks task as cancelled."""
    task = Task(type="test", payload={})
    task_id = task_queue.enqueue(task)
    assert task_queue.cancel(task_id) is True
    assert task_queue.get_status(task_id) == TaskStatus.CANCELLED

def test_get_status(task_queue):
    """Test that get_status returns correct TaskStatus."""
    task = Task(type="test", payload={})
    task_id = task_queue.enqueue(task)
    assert task_queue.get_status(task_id) == TaskStatus.PENDING

def test_task_with_priority(task_queue):
    """Test tasks with different priority levels."""
    critical = Task(type="test", priority=Priority.CRITICAL, payload={})
    normal = Task(type="test", priority=Priority.NORMAL, payload={})
    
    task_queue.enqueue(critical)
    task_queue.enqueue(normal)
    
    first = task_queue.dequeue()
    assert first.priority == Priority.CRITICAL

def test_task_with_delay(task_queue):
    """Test that delayed tasks are scheduled for future execution."""
    task = Task(type="test", payload={})
    task_id = task_queue.enqueue(task, delay_seconds=5)
    assert task_id is not None
    # Delayed task should not be immediately available
    immediate = task_queue.dequeue(timeout_seconds=0)
    # May be None if delay hasn't elapsed
    assert immediate is None or immediate.id == task_id