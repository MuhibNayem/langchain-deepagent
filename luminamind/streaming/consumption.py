from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class TokenConsumption:
    """Token usage for a task or session."""
    session_id: str
    task_id: str | None
    agent_id: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost: float  # Estimated cost in USD
    timestamp: datetime
    model: str
    provider: str


@dataclass
class TokenBudget:
    """Budget tracking for token usage."""
    max_tokens: int
    warning_threshold: float = 0.8  # Warn at 80%
    current_usage: int = 0

    @property
    def remaining(self) -> int:
        return self.max_tokens - self.current_usage

    @property
    def usage_ratio(self) -> float:
        return self.current_usage / self.max_tokens if self.max_tokens > 0 else 0

    @property
    def is_exceeded(self) -> bool:
        return self.current_usage > self.max_tokens

    @property
    def is_warning(self) -> bool:
        return self.usage_ratio >= self.warning_threshold


class TokenConsumptionTracker:
    """Tracks token consumption per task, session, agent."""

    def __init__(self):
        self._by_session: dict[str, list[TokenConsumption]] = {}
        self._by_task: dict[str, list[TokenConsumption]] = {}
        self._by_agent: dict[str, list[TokenConsumption]] = {}

    def record(self, consumption: TokenConsumption) -> None:
        """Record token usage."""
        # By session
        if consumption.session_id not in self._by_session:
            self._by_session[consumption.session_id] = []
        self._by_session[consumption.session_id].append(consumption)

        # By task
        if consumption.task_id:
            if consumption.task_id not in self._by_task:
                self._by_task[consumption.task_id] = []
            self._by_task[consumption.task_id].append(consumption)

        # By agent
        if consumption.agent_id not in self._by_agent:
            self._by_agent[consumption.agent_id] = []
        self._by_agent[consumption.agent_id].append(consumption)

    def get_session_total(self, session_id: str) -> TokenConsumption:
        """Get total consumption for session."""
        consumptions = self._by_session.get(session_id, [])
        return self._sum_consumptions(consumptions)

    def get_task_total(self, task_id: str) -> TokenConsumption:
        """Get total consumption for task."""
        consumptions = self._by_task.get(task_id, [])
        return self._sum_consumptions(consumptions)

    def get_agent_total(self, agent_id: str) -> TokenConsumption:
        """Get total consumption for agent."""
        consumptions = self._by_agent.get(agent_id, [])
        return self._sum_consumptions(consumptions)

    def _sum_consumptions(self, consumptions: list[TokenConsumption]) -> TokenConsumption:
        """Sum multiple consumptions."""
        if not consumptions:
            return TokenConsumption(
                session_id="", task_id=None, agent_id="",
                input_tokens=0, output_tokens=0, total_tokens=0,
                cost=0, timestamp=datetime.utcnow(), model="", provider=""
            )

        first = consumptions[0]
        return TokenConsumption(
            session_id=first.session_id,
            task_id=first.task_id,
            agent_id=first.agent_id,
            input_tokens=sum(c.input_tokens for c in consumptions),
            output_tokens=sum(c.output_tokens for c in consumptions),
            total_tokens=sum(c.total_tokens for c in consumptions),
            cost=sum(c.cost for c in consumptions),
            timestamp=datetime.utcnow(),
            model=first.model,
            provider=first.provider
        )