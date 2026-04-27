from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
import uuid
import threading
import time

from .roles import AgentRole, RoleRegistry


@dataclass
class SwarmConfig:
    max_agents: int = 10
    idle_timeout_seconds: int = 300
    consensus_threshold: float = 0.5
    heartbeat_interval_seconds: int = 30
    auto_spawn: bool = True
    shared_knowledge_enabled: bool = True


@dataclass
class AgentInfo:
    agent_id: str
    role: AgentRole
    status: str = "idle"  # idle, working, waiting
    last_heartbeat: datetime = field(default_factory=datetime.utcnow)
    config: dict = field(default_factory=dict)


@dataclass
class SwarmStatus:
    active_agents: int
    idle_agents: int
    total_tasks: int
    pending_tasks: int


@dataclass
class SwarmMessage:
    sender_id: str
    recipient_id: Optional[str] = None  # None = broadcast
    message_type: str = ""
    payload: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


class Swarm:
    def __init__(self, config: SwarmConfig = None, message_bus=None):
        """Initialize Swarm with optional message_bus for inter-agent communication.

        Args:
            config: SwarmConfig instance for swarm behavior settings
            message_bus: Optional AgentMessageBus instance for message dispatch.
                        If None, uses internal queue for standalone operation.
        """
        self.config = config or SwarmConfig()
        self._agents: dict[str, AgentInfo] = {}
        self._roles = RoleRegistry()
        self._lock = threading.Lock()
        self._message_bus = message_bus
        self._message_queue: list[SwarmMessage] = []
        self._total_tasks: int = 0

    def spawn(self, role: AgentRole, config: dict = None) -> str:
        """Spawn a new agent with the given role."""
        with self._lock:
            # Check max agents
            active_count = sum(1 for a in self._agents.values() if a.status != "dead")
            if active_count >= self.config.max_agents:
                raise RuntimeError(f"Max agents reached: {self.config.max_agents}")

            # Check role capacity
            role_spec = self._roles.get(role)
            if role_spec:
                role_count = sum(1 for a in self._agents.values() if a.role == role and a.status != "dead")
                if role_count >= role_spec.max_instances:
                    raise RuntimeError(f"Max {role.value} instances: {role_spec.max_instances}")

            agent_id = str(uuid.uuid4())
            self._agents[agent_id] = AgentInfo(
                agent_id=agent_id,
                role=role,
                status="idle",
                config=config or {},
            )
            self._total_tasks += 1
            return agent_id

    def kill(self, agent_id: str) -> bool:
        """Terminate an agent."""
        with self._lock:
            if agent_id in self._agents:
                self._agents[agent_id].status = "dead"
                return True
            return False

    def _validate_sender(self, sender_id: str) -> bool:
        """Validate sender_id exists in swarm and is not dead. Returns True if valid."""
        agent = self._agents.get(sender_id)
        return agent is not None and agent.status != "dead"

    def broadcast(self, message: SwarmMessage) -> None:
        """Broadcast message to all agents."""
        with self._lock:
            if not self._validate_sender(message.sender_id):
                raise ValueError(f"Invalid sender_id: {message.sender_id}")
            message.recipient_id = None
            if self._message_bus is not None:
                self._message_bus.publish(message)
            else:
                self._message_queue.append(message)

    def send_to(self, agent_id: str, message: SwarmMessage) -> None:
        """Send direct message to specific agent."""
        with self._lock:
            if not self._validate_sender(message.sender_id):
                raise ValueError(f"Invalid sender_id: {message.sender_id}")
            if agent_id not in self._agents or self._agents[agent_id].status == "dead":
                raise ValueError(f"Invalid recipient_id: {agent_id}")
            message.recipient_id = agent_id
            if self._message_bus is not None:
                self._message_bus.publish(message)
            else:
                self._message_queue.append(message)

    def get_status(self) -> SwarmStatus:
        """Get swarm status."""
        with self._lock:
            active = sum(1 for a in self._agents.values() if a.status == "working")
            idle = sum(1 for a in self._agents.values() if a.status == "idle")
            return SwarmStatus(
                active_agents=active,
                idle_agents=idle,
                total_tasks=self._total_tasks,
                pending_tasks=idle,
            )

    def wait_for_completion(self, timeout_seconds: int = 300) -> dict:
        """Wait for all agents to complete current tasks."""
        deadline = datetime.utcnow().timestamp() + timeout_seconds
        while datetime.utcnow().timestamp() < deadline:
            status = self.get_status()
            if status.active_agents == 0:
                return {"status": "complete", "agents": len(self._agents)}
            time.sleep(1)
        return {"status": "timeout", "active": status.active_agents}