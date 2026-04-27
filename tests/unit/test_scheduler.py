import pytest
from datetime import datetime
from luminamind.scheduler.cron_parser import CronExpression, parse_cron


def test_parse_cron():
    """Test parse: '*/5 * * * *' produces CronExpression with correct fields."""
    expr = parse_cron("*/5 * * * *")
    assert expr.minute == "*/5"
    assert expr.hour == "*"
    assert expr.day_of_month == "*"
    assert expr.month == "*"
    assert expr.day_of_week == "*"


def test_validate_valid():
    """Test validate: valid cron expression returns True."""
    expr = parse_cron("*/5 * * * *")
    assert expr.validate() is True


def test_validate_invalid():
    """Test validate: invalid cron expression returns False."""
    expr = CronExpression(minute="60", hour="*", day_of_month="*", month="*", day_of_week="*")
    assert expr.validate() is False


def test_validate_invalid_hour():
    """Test validate: invalid hour field returns False."""
    expr = CronExpression(minute="*", hour="25", day_of_month="*", month="*", day_of_week="*")
    assert expr.validate() is False


def test_validate_invalid_month():
    """Test validate: invalid month field returns False."""
    expr = CronExpression(minute="*", hour="*", day_of_month="*", month="13", day_of_week="*")
    assert expr.validate() is False


def test_next_fire_time_hourly():
    """Test next_fire_time: given a time, returns next datetime matching expression."""
    expr = parse_cron("0 * * * *")  # Every hour at minute 0
    current = datetime(2026, 4, 27, 10, 30)
    next_time = expr.next_fire_time(current)
    assert next_time.hour == 11
    assert next_time.minute == 0


def test_next_fire_time_daily():
    """Test next_fire_time: 9 AM daily."""
    expr = parse_cron("0 9 * * *")  # 9 AM daily
    current = datetime(2026, 4, 27, 10, 30)
    next_time = expr.next_fire_time(current)
    assert next_time.day == 28
    assert next_time.hour == 9
    assert next_time.minute == 0


def test_next_fire_time_invalid():
    """Test next_fire_time raises ValueError for invalid expression."""
    expr = CronExpression(minute="60", hour="*", day_of_month="*", month="*", day_of_week="*")
    with pytest.raises(ValueError):
        expr.next_fire_time(datetime.utcnow())


def test_parse_cron_invalid_format():
    """Test parse_cron raises ValueError for wrong number of fields."""
    with pytest.raises(ValueError):
        parse_cron("*/5 * * *")  # Only 4 fields


def test_parse_cron_invalid_minute_value():
    """Test parse_cron handles invalid minute values."""
    expr = parse_cron("60 * * * *")
    assert expr.validate() is False


# Scheduler tests
def test_scheduler_schedule():
    """Test schedule: task registered, next_run calculated."""
    from luminamind.queue import MemoryBackend, TaskQueue
    from luminamind.scheduler import Scheduler, ScheduledTask

    backend = MemoryBackend()
    tq = TaskQueue(backend)
    sched = Scheduler(tq)

    task = ScheduledTask(name="test", task_type="test", payload={"data": "test"})
    task_id = sched.schedule(task)

    assert task_id in sched._tasks
    assert sched._tasks[task_id].next_run is not None


def test_scheduler_unschedule():
    """Test unschedule: task removed from scheduler."""
    from luminamind.queue import MemoryBackend, TaskQueue
    from luminamind.scheduler import Scheduler, ScheduledTask

    backend = MemoryBackend()
    tq = TaskQueue(backend)
    sched = Scheduler(tq)

    task = ScheduledTask(name="test", task_type="test", payload={"data": "test"})
    task_id = sched.schedule(task)

    assert sched.unschedule(task_id) is True
    assert task_id not in sched._tasks


def test_scheduler_pause_resume():
    """Test pause/resume: task stops/starts firing."""
    from luminamind.queue import MemoryBackend, TaskQueue
    from luminamind.scheduler import Scheduler, ScheduledTask

    backend = MemoryBackend()
    tq = TaskQueue(backend)
    sched = Scheduler(tq)

    task = ScheduledTask(name="test", task_type="test", payload={"data": "test"})
    task.next_run = datetime.utcnow()
    task_id = sched.schedule(task)

    assert sched.pause(task_id) is True
    assert sched._tasks[task_id].enabled is False

    assert sched.resume(task_id) is True
    assert sched._tasks[task_id].enabled is True


def test_scheduler_tick():
    """Test tick: returns list of due tasks, advances next_run."""
    from luminamind.queue import MemoryBackend, TaskQueue
    from luminamind.scheduler import Scheduler, ScheduledTask

    backend = MemoryBackend()
    tq = TaskQueue(backend)
    sched = Scheduler(tq)

    # Schedule a task for immediate execution
    task = ScheduledTask(name="immediate", task_type="test", payload={})
    task.next_run = datetime.utcnow()
    sched.schedule(task)

    due = sched.tick()
    assert len(due) == 1
    assert due[0].name == "immediate"


def test_scheduler_tick_with_cron():
    """Test tick with cron expression advances next_run."""
    from luminamind.queue import MemoryBackend, TaskQueue
    from luminamind.scheduler import Scheduler, ScheduledTask

    backend = MemoryBackend()
    tq = TaskQueue(backend)
    sched = Scheduler(tq)

    # Schedule a cron task for immediate execution
    cron_expr = parse_cron("0 * * * *")  # Every hour
    task = ScheduledTask(
        name="hourly",
        task_type="test",
        payload={},
        cron=cron_expr
    )
    # Set next_run to now so task is due immediately
    task.next_run = datetime.utcnow()
    original_next_run = task.next_run
    task_id = sched.schedule(task)

    # Tick should enqueue and advance next_run
    due = sched.tick()
    assert len(due) == 1
    assert sched._tasks[task_id].next_run > original_next_run


def test_scheduler_get_next_runs():
    """Test get_next_runs returns sorted upcoming fire times."""
    from luminamind.queue import MemoryBackend, TaskQueue
    from luminamind.scheduler import Scheduler, ScheduledTask

    backend = MemoryBackend()
    tq = TaskQueue(backend)
    sched = Scheduler(tq)

    task1 = ScheduledTask(name="task1", task_type="test", payload={})
    task1.next_run = datetime(2026, 4, 27, 12, 0)
    sched.schedule(task1)

    task2 = ScheduledTask(name="task2", task_type="test", payload={})
    task2.next_run = datetime(2026, 4, 27, 9, 0)
    sched.schedule(task2)

    runs = sched.get_next_runs(10)
    assert len(runs) == 2
    assert runs[0] < runs[1]  # Sorted ascending
