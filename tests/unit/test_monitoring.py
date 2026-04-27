import pytest
from luminamind.monitoring import (
    create_app,
    TaskMetrics,
    SwarmMetrics,
    AlertRule,
    AlertEngine,
    AlertSeverity,
    NotificationChannel,
)
from luminamind.queue import QueueMetrics


def test_task_metrics_dataclass():
    """Test TaskMetrics dataclass."""
    metrics = TaskMetrics(
        queued=10,
        running=5,
        completed=100,
        failed=2,
        dead_letter=1,
    )
    assert metrics.queued == 10
    assert metrics.running == 5
    assert metrics.completed == 100
    assert metrics.failed == 2
    assert metrics.dead_letter == 1
    assert metrics.timestamp is not None


def test_swarm_metrics_dataclass():
    """Test SwarmMetrics dataclass."""
    metrics = SwarmMetrics(
        active_agents=3,
        idle_agents=5,
        total_agents=8,
        tasks_completed=50,
    )
    assert metrics.active_agents == 3
    assert metrics.idle_agents == 5
    assert metrics.total_agents == 8
    assert metrics.tasks_completed == 50
    assert metrics.timestamp is not None


def test_dashboard_api_task_metrics():
    """Test dashboard API with task metrics endpoint."""
    from luminamind.monitoring.dashboard import create_app
    from luminamind.queue import TaskQueue, MemoryBackend

    backend = MemoryBackend()
    task_queue = TaskQueue(backend)

    app = create_app(task_queue=task_queue)

    # Get the client
    from fastapi.testclient import TestClient
    client = TestClient(app)

    response = client.get("/api/v1/metrics/tasks")
    assert response.status_code == 200
    data = response.json()
    assert "queued" in data or "error" not in data


def test_dashboard_api_swarm_metrics():
    """Test dashboard API with swarm metrics endpoint."""
    from luminamind.monitoring.dashboard import create_app
    from luminamind.swarm import Swarm, SwarmConfig, AgentRole

    swarm = Swarm(SwarmConfig())
    app = create_app(swarm=swarm)

    from fastapi.testclient import TestClient
    client = TestClient(app)

    response = client.get("/api/v1/metrics/swarm")
    assert response.status_code == 200
    data = response.json()
    assert "active_agents" in data or "error" not in data


def test_dashboard_health_endpoint():
    """Test health endpoint."""
    app = create_app()

    from fastapi.testclient import TestClient
    client = TestClient(app)

    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_dashboard_alerts_endpoint():
    """Test alerts endpoint."""
    app = create_app(alert_engine=AlertEngine())

    from fastapi.testclient import TestClient
    client = TestClient(app)

    response = client.get("/api/v1/alerts")
    assert response.status_code == 200
    assert "alerts" in response.json()


def test_alert_severity_enum():
    """Test AlertSeverity enum values."""
    assert AlertSeverity.INFO.value == "info"
    assert AlertSeverity.WARNING.value == "warning"
    assert AlertSeverity.ERROR.value == "error"
    assert AlertSeverity.CRITICAL.value == "critical"


def test_notification_channel_enum():
    """Test NotificationChannel enum values."""
    assert NotificationChannel.EMAIL.value == "email"
    assert NotificationChannel.SLACK.value == "slack"
    assert NotificationChannel.PAGERDUTY.value == "pagerduty"
    assert NotificationChannel.WEBHOOK.value == "webhook"


def test_alert_rule_dataclass():
    """Test AlertRule creation."""
    rule = AlertRule(
        name="high_queue",
        condition="queued > 100",
        severity=AlertSeverity.WARNING,
        channels=[NotificationChannel.SLACK],
    )
    assert rule.name == "high_queue"
    assert rule.condition == "queued > 100"
    assert rule.severity == AlertSeverity.WARNING
    assert NotificationChannel.SLACK in rule.channels
    assert rule.enabled is True


def test_alert_engine():
    """Test AlertEngine evaluates rules against metrics."""
    engine = AlertEngine()
    engine.add_rule(AlertRule(
        name="high_queue",
        condition="queued > 10",
        severity=AlertSeverity.WARNING,
    ))

    metrics = QueueMetrics(pending=15, running=2, completed=0, failed=0, dead_letter=0)
    alerts = engine.evaluate(task_queue_metrics=metrics)

    assert len(alerts) == 1
    assert alerts[0].rule.name == "high_queue"


def test_alert_engine_no_match():
    """Test AlertEngine does not trigger when condition not met."""
    engine = AlertEngine()
    engine.add_rule(AlertRule(
        name="high_queue",
        condition="queued > 100",
        severity=AlertSeverity.WARNING,
    ))

    metrics = QueueMetrics(pending=10, running=2, completed=0, failed=0, dead_letter=0)
    alerts = engine.evaluate(task_queue_metrics=metrics)

    assert len(alerts) == 0


def test_alert_engine_multiple_rules():
    """Test AlertEngine with multiple rules."""
    engine = AlertEngine()
    engine.add_rule(AlertRule(
        name="high_queue",
        condition="queued > 10",
        severity=AlertSeverity.WARNING,
    ))
    engine.add_rule(AlertRule(
        name="high_failure",
        condition="failed > 5",
        severity=AlertSeverity.ERROR,
    ))

    metrics = QueueMetrics(pending=15, running=2, completed=0, failed=10, dead_letter=0)
    alerts = engine.evaluate(task_queue_metrics=metrics)

    assert len(alerts) == 2
    assert any(a.rule.name == "high_queue" for a in alerts)
    assert any(a.rule.name == "high_failure" for a in alerts)


def test_alert_engine_remove_rule():
    """Test AlertEngine can remove rules."""
    engine = AlertEngine()
    engine.add_rule(AlertRule(
        name="high_queue",
        condition="queued > 10",
        severity=AlertSeverity.WARNING,
    ))
    engine.remove_rule("high_queue")

    metrics = QueueMetrics(pending=15, running=2, completed=0, failed=0, dead_letter=0)
    alerts = engine.evaluate(task_queue_metrics=metrics)

    assert len(alerts) == 0


def test_alert_engine_disabled_rule():
    """Test AlertEngine ignores disabled rules."""
    engine = AlertEngine()
    engine.add_rule(AlertRule(
        name="high_queue",
        condition="queued > 10",
        severity=AlertSeverity.WARNING,
        enabled=False,
    ))

    metrics = QueueMetrics(pending=15, running=2, completed=0, failed=0, dead_letter=0)
    alerts = engine.evaluate(task_queue_metrics=metrics)

    assert len(alerts) == 0


def test_alert_engine_swarm_metrics():
    """Test AlertEngine with swarm metrics."""
    engine = AlertEngine()
    engine.add_rule(AlertRule(
        name="swarm_stalled",
        condition="active_agents > 0",
        severity=AlertSeverity.CRITICAL,
    ))

    # Mock swarm status
    class MockSwarmStatus:
        active_agents = 3
        idle_agents = 5
        total_tasks = 8
        pending_tasks = 5

    alerts = engine.evaluate(swarm_status=MockSwarmStatus())

    assert len(alerts) == 1
    assert alerts[0].rule.name == "swarm_stalled"


def test_get_active_alerts():
    """Test get_active_alerts returns proper format."""
    engine = AlertEngine()
    engine.add_rule(AlertRule(
        name="high_queue",
        condition="queued > 10",
        severity=AlertSeverity.WARNING,
    ))

    metrics = QueueMetrics(pending=15, running=2, completed=0, failed=0, dead_letter=0)
    engine.evaluate(task_queue_metrics=metrics)

    active_alerts = engine.get_active_alerts()
    assert len(active_alerts) == 1
    assert active_alerts[0]["name"] == "high_queue"
    assert active_alerts[0]["severity"] == "warning"
    assert "triggered_at" in active_alerts[0]


def test_alert_acknowledge():
    """Test alert acknowledgment."""
    engine = AlertEngine()
    engine.add_rule(AlertRule(
        name="high_queue",
        condition="queued > 10",
        severity=AlertSeverity.WARNING,
    ))

    metrics = QueueMetrics(pending=15, running=2, completed=0, failed=0, dead_letter=0)
    engine.evaluate(task_queue_metrics=metrics)

    active_alerts = engine.get_active_alerts()
    assert len(active_alerts) == 1
    assert active_alerts[0]["acknowledged"] is False

    engine.acknowledge("high_queue")

    active_alerts = engine.get_active_alerts()
    assert active_alerts[0]["acknowledged"] is True


def test_condition_operators():
    """Test all comparison operators in conditions."""
    engine = AlertEngine()

    # Test greater than
    engine.add_rule(AlertRule(name="gt", condition="queued > 10", severity=AlertSeverity.INFO))
    metrics = QueueMetrics(pending=11, running=0, completed=0, failed=0, dead_letter=0)
    assert len(engine.evaluate(task_queue_metrics=metrics)) == 1
    metrics = QueueMetrics(pending=10, running=0, completed=0, failed=0, dead_letter=0)
    assert len(engine.evaluate(task_queue_metrics=metrics)) == 0

    # Test less than
    engine._rules.clear()
    engine.add_rule(AlertRule(name="lt", condition="queued < 10", severity=AlertSeverity.INFO))
    metrics = QueueMetrics(pending=9, running=0, completed=0, failed=0, dead_letter=0)
    assert len(engine.evaluate(task_queue_metrics=metrics)) == 1
    metrics = QueueMetrics(pending=10, running=0, completed=0, failed=0, dead_letter=0)
    assert len(engine.evaluate(task_queue_metrics=metrics)) == 0

    # Test equality
    engine._rules.clear()
    engine.add_rule(AlertRule(name="eq", condition="queued == 10", severity=AlertSeverity.INFO))
    metrics = QueueMetrics(pending=10, running=0, completed=0, failed=0, dead_letter=0)
    assert len(engine.evaluate(task_queue_metrics=metrics)) == 1
    metrics = QueueMetrics(pending=11, running=0, completed=0, failed=0, dead_letter=0)
    assert len(engine.evaluate(task_queue_metrics=metrics)) == 0

    # Test greater than or equal
    engine._rules.clear()
    engine.add_rule(AlertRule(name="gte", condition="queued >= 10", severity=AlertSeverity.INFO))
    metrics = QueueMetrics(pending=10, running=0, completed=0, failed=0, dead_letter=0)
    assert len(engine.evaluate(task_queue_metrics=metrics)) == 1
    metrics = QueueMetrics(pending=11, running=0, completed=0, failed=0, dead_letter=0)
    assert len(engine.evaluate(task_queue_metrics=metrics)) == 1

    # Test less than or equal
    engine._rules.clear()
    engine.add_rule(AlertRule(name="lte", condition="queued <= 10", severity=AlertSeverity.INFO))
    metrics = QueueMetrics(pending=10, running=0, completed=0, failed=0, dead_letter=0)
    assert len(engine.evaluate(task_queue_metrics=metrics)) == 1
    metrics = QueueMetrics(pending=11, running=0, completed=0, failed=0, dead_letter=0)
    assert len(engine.evaluate(task_queue_metrics=metrics)) == 0

    # Test not equal
    engine._rules.clear()
    engine.add_rule(AlertRule(name="ne", condition="queued != 10", severity=AlertSeverity.INFO))
    metrics = QueueMetrics(pending=11, running=0, completed=0, failed=0, dead_letter=0)
    assert len(engine.evaluate(task_queue_metrics=metrics)) == 1
    metrics = QueueMetrics(pending=10, running=0, completed=0, failed=0, dead_letter=0)
    assert len(engine.evaluate(task_queue_metrics=metrics)) == 0
