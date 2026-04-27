import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class NotificationChannel(Enum):
    EMAIL = "email"
    SLACK = "slack"
    PAGERDUTY = "pagerduty"
    WEBHOOK = "webhook"

@dataclass
class AlertRule:
    name: str
    condition: str  # Simple expression: "queue_depth > 100"
    severity: AlertSeverity
    channels: list[NotificationChannel] = field(default_factory=list)
    enabled: bool = True

class Alert:
    def __init__(self, rule: AlertRule, triggered_at: datetime = None):
        self.rule = rule
        self.triggered_at = triggered_at or datetime.utcnow()
        self.acknowledged: bool = False

class AlertEngine:
    """Evaluates alert rules against current metrics."""

    def __init__(self):
        self._rules: list[AlertRule] = []
        self._active_alerts: list[Alert] = []

    def add_rule(self, rule: AlertRule):
        self._rules.append(rule)

    def remove_rule(self, name: str):
        self._rules = [r for r in self._rules if r.name != name]

    def evaluate(self, task_queue_metrics: Any = None, swarm_status: Any = None):
        """Check all rules against current state."""
        self._active_alerts = []

        for rule in self._rules:
            if not rule.enabled:
                continue

            if self._evaluate_condition(rule.condition, task_queue_metrics, swarm_status):
                self._active_alerts.append(Alert(rule))

        return self._active_alerts

    # Field alias mapping (condition name -> actual metrics field)
    _FIELD_ALIASES = {
        "queued": "pending",  # queued is the dashboard name, pending is the QueueMetrics name
        "queue_depth": "pending",
    }

    def _evaluate_condition(self, condition: str, tq_metrics, swarm_status) -> bool:
        """Simple condition evaluator. Supports: queue_depth > N, active_agents == N, etc."""
        # Parse simple conditions
        match = re.match(r'(\w+)\s*([><=!]+)\s*(\d+)', condition.strip())
        if not match:
            return False

        field_name, op, value = match.groups()
        value = int(value)

        # Resolve field aliases
        field_name = self._FIELD_ALIASES.get(field_name, field_name)

        # Get field value from metrics
        if tq_metrics and hasattr(tq_metrics, field_name):
            actual = getattr(tq_metrics, field_name)
        elif swarm_status and hasattr(swarm_status, field_name):
            actual = getattr(swarm_status, field_name)
        else:
            return False

        # Evaluate
        if op == '>':
            return actual > value
        elif op == '>=':
            return actual >= value
        elif op == '<':
            return actual < value
        elif op == '<=':
            return actual <= value
        elif op == '==':
            return actual == value
        elif op == '!=':
            return actual != value

        return False

    def get_active_alerts(self) -> list[dict]:
        return [
            {
                "name": a.rule.name,
                "severity": a.rule.severity.value,
                "triggered_at": a.triggered_at.isoformat(),
                "acknowledged": a.acknowledged,
            }
            for a in self._active_alerts
        ]

    def acknowledge(self, alert_name: str):
        for alert in self._active_alerts:
            if alert.rule.name == alert_name:
                alert.acknowledged = True