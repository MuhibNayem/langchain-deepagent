"""AgentMessageBus for inter-agent communication with queuing and conflict resolution.

Per MULTI-02: AgentMessageBus handles inter-agent communication with queuing,
priority-based delivery, and conflict resolution.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable, Optional
import uuid

# Use Queue from queue module for priority queue
from queue import PriorityQueue, Empty
import threading


class MessagePriority(Enum):
    """Priority levels for message delivery ordering."""
    HIGH = 1
    NORMAL = 2
    LOW = 3


@dataclass
class AgentMessage:
    """Message sent between agents via the message bus.

    Attributes:
        id: Unique message identifier
        sender: Name of the sending agent ("parent", "system", etc.)
        recipient: Name of receiving agent, or None for broadcast
        content: Message payload dict
        priority: MessagePriority level (default NORMAL)
        timestamp: ISO timestamp (auto-generated)
        in_reply_to: Message ID this is replying to
        conversation_id: Groups related messages
    """
    id: str
    sender: str
    recipient: Optional[str]
    content: dict
    priority: MessagePriority = MessagePriority.NORMAL
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    in_reply_to: Optional[str] = None
    conversation_id: Optional[str] = None

    def __lt__(self, other):
        """PriorityQueue ordering: priority first (lower value = higher priority), then timestamp."""
        if self.priority == other.priority:
            return self.timestamp < other.timestamp
        return self.priority.value < other.priority.value


@dataclass
class Subscription:
    """Subscription to the message bus by an agent.

    Attributes:
        agent_name: Name of subscribing agent
        filter_fn: Returns True if agent wants this message
        callback: Called when message is delivered
    """
    agent_name: str
    filter_fn: Callable[[AgentMessage], bool]
    callback: Callable[[AgentMessage], None]


class AgentMessageBus:
    """Message bus for inter-agent communication.

    Supports:
    - Publish-subscribe pattern
    - Priority-based message delivery (HIGH before NORMAL before LOW)
    - Broadcast (recipient=None) and direct send
    - Filter-based subscription for selective message delivery
    - Thread-safe operations

    Per MULTI-02.
    """

    def __init__(self):
        """Initialize the message bus."""
        self.queue: PriorityQueue[AgentMessage] = PriorityQueue()
        self.subscriptions: list[Subscription] = []
        self.delivered: list[str] = []  # Message IDs delivered
        self.lock = threading.Lock()

    def publish(self, message: AgentMessage) -> None:
        """Publish a message to the bus.

        Args:
            message: AgentMessage to publish
        """
        with self.lock:
            self.queue.put(message)

    def subscribe(
        self,
        agent_name: str,
        filter_fn: Optional[Callable[[AgentMessage], bool]] = None,
        callback: Optional[Callable[[AgentMessage], None]] = None
    ) -> Subscription:
        """Subscribe agent to messages.

        If filter_fn provided, only matching messages trigger callback.

        Args:
            agent_name: Name of agent subscribing
            filter_fn: Optional filter function (default: accept all)
            callback: Optional callback (default: no-op)

        Returns:
            Subscription object
        """
        sub = Subscription(
            agent_name=agent_name,
            filter_fn=filter_fn or (lambda m: True),
            callback=callback or (lambda m: None)
        )
        self.subscriptions.append(sub)
        return sub

    def unsubscribe(self, subscription: Subscription) -> None:
        """Remove subscription from the bus.

        Args:
            subscription: Subscription to remove
        """
        if subscription in self.subscriptions:
            self.subscriptions.remove(subscription)

    def deliver_next(self, agent_name: str, timeout: float = 1.0) -> Optional[AgentMessage]:
        """Get next message for agent, respecting subscriptions.

        Args:
            agent_name: Name of agent to deliver to
            timeout: How long to wait for a message

        Returns:
            AgentMessage if available and accepted by subscription, None otherwise
        """
        try:
            message = self.queue.get(timeout=timeout)
        except Empty:
            return None

        # Find subscription for this agent
        agent_subs = [s for s in self.subscriptions if s.agent_name == agent_name]
        if not agent_subs:
            # No subscription - message stays in queue for next check
            self.queue.put(message)
            return None

        # Check if any subscription's filter accepts this message
        for sub in agent_subs:
            if sub.filter_fn(message):
                sub.callback(message)
                with self.lock:
                    self.delivered.append(message.id)
                return message

        # No subscription accepted - re-queue
        self.queue.put(message)
        return None

    def broadcast(self, sender: str, content: dict, priority: MessagePriority = MessagePriority.NORMAL) -> AgentMessage:
        """Broadcast message to all agents.

        Args:
            sender: Name of sending agent
            content: Message payload
            priority: MessagePriority level

        Returns:
            The created AgentMessage
        """
        message = AgentMessage(
            id=self._generate_id(),
            sender=sender,
            recipient=None,
            content=content,
            priority=priority
        )
        self.publish(message)
        return message

    def send_to(self, sender: str, recipient: str, content: dict, priority: MessagePriority = MessagePriority.NORMAL) -> AgentMessage:
        """Send message to specific agent.

        Args:
            sender: Name of sending agent
            recipient: Name of receiving agent
            content: Message payload
            priority: MessagePriority level

        Returns:
            The created AgentMessage
        """
        message = AgentMessage(
            id=self._generate_id(),
            sender=sender,
            recipient=recipient,
            content=content,
            priority=priority
        )
        self.publish(message)
        return message

    def _generate_id(self) -> str:
        """Generate short unique message ID."""
        return str(uuid.uuid4())[:8]


class ConflictResolution:
    """Strategies for resolving conflicting messages."""
    LATEST_WINS = "latest_wins"
    HIGHEST_PRIORITY_WINS = "priority_wins"
    FIRST_WINS = "first_wins"
    MERGE = "merge"


def resolve_conflict(
    messages: list[AgentMessage],
    strategy: str = ConflictResolution.LATEST_WINS
) -> Optional[AgentMessage]:
    """Resolve multiple messages about same topic into single message.

    Args:
        messages: List of AgentMessages to resolve
        strategy: Resolution strategy (LATEST_WINS, PRIORITY_WINS, FIRST_WINS, MERGE)

    Returns:
        Resolved AgentMessage, or None if messages list is empty
    """
    if len(messages) <= 1:
        return messages[0] if messages else None

    if strategy == ConflictResolution.LATEST_WINS:
        return max(messages, key=lambda m: m.timestamp)

    elif strategy == ConflictResolution.HIGHEST_PRIORITY_WINS:
        return min(messages, key=lambda m: m.priority.value)

    elif strategy == ConflictResolution.FIRST_WINS:
        return min(messages, key=lambda m: m.timestamp)

    elif strategy == ConflictResolution.MERGE:
        # Merge content from all messages
        merged_content = {}
        for msg in messages:
            merged_content.update(msg.content)
        result = messages[0]
        result.content = merged_content
        return result

    return messages[0]
