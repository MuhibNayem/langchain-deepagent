from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class TaskMetrics:
    queued: int
    running: int
    completed: int
    failed: int
    dead_letter: int
    rate_per_minute: float = 0.0
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

@dataclass
class SwarmMetrics:
    active_agents: int
    idle_agents: int
    total_agents: int
    tasks_completed: int
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()