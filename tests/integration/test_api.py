import pytest
from fastapi.testclient import TestClient
from luminamind.api import create_app


def test_health_endpoint():
    """Test health endpoint returns healthy status."""
    app = create_app()
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert "version" in response.json()


def test_queue_enqueue_without_queue():
    """Test queue enqueue returns 503 when no queue configured."""
    app = create_app()
    client = TestClient(app)
    response = client.post(
        "/api/v1/queue/enqueue?task_type=test",
        json={"data": "test"},
    )
    assert response.status_code == 503


def test_queue_status_without_queue():
    """Test queue status returns 503 when no queue configured."""
    app = create_app()
    client = TestClient(app)
    response = client.get("/api/v1/queue/status/test-id")
    assert response.status_code == 503


def test_scheduler_schedule_without_scheduler():
    """Test scheduler schedule returns 503 when no scheduler configured."""
    app = create_app()
    client = TestClient(app)
    response = client.post(
        "/api/v1/scheduler/schedule?task_type=test",
        json={},
    )
    assert response.status_code == 503


def test_scheduler_list_without_scheduler():
    """Test scheduler list returns 503 when no scheduler configured."""
    app = create_app()
    client = TestClient(app)
    response = client.get("/api/v1/scheduler/list")
    assert response.status_code == 503


def test_swarm_spawn_without_swarm():
    """Test swarm spawn returns 503 when no swarm configured."""
    app = create_app()
    client = TestClient(app)
    response = client.post(
        "/api/v1/swarm/spawn?role=planner",
        json={},
    )
    assert response.status_code == 503


def test_swarm_status_without_swarm():
    """Test swarm status returns 503 when no swarm configured."""
    app = create_app()
    client = TestClient(app)
    response = client.get("/api/v1/swarm/status")
    assert response.status_code == 503


def test_swarm_kill_without_swarm():
    """Test swarm kill returns 503 when no swarm configured."""
    app = create_app()
    client = TestClient(app)
    response = client.delete("/api/v1/swarm/kill/test-agent-id")
    assert response.status_code == 503


def test_swarm_broadcast_without_swarm():
    """Test swarm broadcast returns 503 when no swarm configured."""
    app = create_app()
    client = TestClient(app)
    response = client.post(
        "/api/v1/swarm/broadcast?message_type=test",
        json={},
    )
    assert response.status_code == 503


def test_queue_enqueue_with_task_queue():
    """Test queue enqueue with a configured task queue."""
    from luminamind.queue import TaskQueue, MemoryBackend, Task, Priority

    backend = MemoryBackend()
    task_queue = TaskQueue(backend=backend)
    app = create_app(task_queue=task_queue)
    client = TestClient(app)

    response = client.post(
        "/api/v1/queue/enqueue?task_type=test&priority=NORMAL",
        json={"data": "test"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "task_id" in data
    assert data["status"] == "enqueued"


def test_queue_status_with_task_queue():
    """Test queue status with a configured task queue."""
    from luminamind.queue import TaskQueue, MemoryBackend, Task, Priority

    backend = MemoryBackend()
    task_queue = TaskQueue(backend=backend)

    # Enqueue a task first
    task = Task(type="test", payload={"data": "test"}, priority=Priority.NORMAL)
    task_id = task_queue.enqueue(task)

    app = create_app(task_queue=task_queue)
    client = TestClient(app)

    response = client.get(f"/api/v1/queue/status/{task_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == task_id
    assert data["status"] == "pending"


def test_queue_cancel_with_task_queue():
    """Test queue cancel with a configured task queue."""
    from luminamind.queue import TaskQueue, MemoryBackend, Task, Priority

    backend = MemoryBackend()
    task_queue = TaskQueue(backend=backend)

    # Enqueue a task first
    task = Task(type="test", payload={"data": "test"}, priority=Priority.NORMAL)
    task_id = task_queue.enqueue(task)

    app = create_app(task_queue=task_queue)
    client = TestClient(app)

    response = client.delete(f"/api/v1/queue/cancel/{task_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == task_id
    assert data["status"] == "cancelled"


def test_queue_metrics_with_task_queue():
    """Test queue metrics with a configured task queue."""
    from luminamind.queue import TaskQueue, MemoryBackend, Task, Priority

    backend = MemoryBackend()
    task_queue = TaskQueue(backend=backend)

    # Enqueue a few tasks
    for i in range(3):
        task = Task(type="test", payload={"index": i}, priority=Priority.NORMAL)
        task_queue.enqueue(task)

    app = create_app(task_queue=task_queue)
    client = TestClient(app)

    response = client.get("/api/v1/queue/metrics")
    assert response.status_code == 200
    data = response.json()
    assert data["pending"] == 3
    assert data["running"] == 0
    assert data["completed"] == 0
    assert data["failed"] == 0


def test_swarm_spawn_with_swarm():
    """Test swarm spawn with a configured swarm."""
    from luminamind.swarm import Swarm, AgentRole

    swarm = Swarm()
    app = create_app(swarm=swarm)
    client = TestClient(app)

    response = client.post(
        "/api/v1/swarm/spawn?role=planner",
        json={},
    )
    assert response.status_code == 200
    data = response.json()
    assert "agent_id" in data
    assert data["status"] == "spawned"


def test_swarm_status_with_swarm():
    """Test swarm status with a configured swarm."""
    from luminamind.swarm import Swarm, AgentRole

    swarm = Swarm()
    app = create_app(swarm=swarm)
    client = TestClient(app)

    response = client.get("/api/v1/swarm/status")
    assert response.status_code == 200
    data = response.json()
    assert "active_agents" in data
    assert "idle_agents" in data


def test_swarm_kill_with_swarm():
    """Test swarm kill with a configured swarm."""
    from luminamind.swarm import Swarm, AgentRole

    swarm = Swarm()
    # Spawn an agent first
    agent_id = swarm.spawn(role=AgentRole.PLANNER)

    app = create_app(swarm=swarm)
    client = TestClient(app)

    response = client.delete(f"/api/v1/swarm/kill/{agent_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["agent_id"] == agent_id
    assert data["status"] == "killed"


def test_swarm_broadcast_with_swarm():
    """Test swarm broadcast with a configured swarm."""
    from luminamind.swarm import Swarm, AgentRole

    swarm = Swarm()
    # Spawn an agent first - agent must exist for broadcast to be valid
    agent_id = swarm.spawn(role=AgentRole.PLANNER)

    app = create_app(swarm=swarm)
    client = TestClient(app)

    response = client.post(
        f"/api/v1/swarm/broadcast?message_type=test&sender_id={agent_id}",
        json={"data": "test"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "broadcast"


def test_swarm_invalid_role():
    """Test swarm spawn with invalid role returns 400."""
    from luminamind.swarm import Swarm

    swarm = Swarm()
    app = create_app(swarm=swarm)
    client = TestClient(app)

    response = client.post(
        "/api/v1/swarm/spawn?role=invalid_role",
        json={},
    )
    assert response.status_code == 400
