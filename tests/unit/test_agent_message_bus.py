"""Tests for AgentMessageBus - RED phase (failing tests first)."""
import pytest
from luminamind.planner.agent_message_bus import (
    AgentMessageBus,
    AgentMessage,
    MessagePriority,
)


class TestAgentMessage:
    """Test AgentMessage dataclass."""

    def test_agent_message_has_required_fields(self):
        """AgentMessage has sender, recipient, content, priority, timestamp."""
        msg = AgentMessage(
            id="test-1",
            sender="agent1",
            recipient="agent2",
            content={"data": "test"},
        )
        assert msg.sender == "agent1"
        assert msg.recipient == "agent2"
        assert msg.content == {"data": "test"}
        assert msg.priority == MessagePriority.NORMAL
        assert msg.timestamp is not None

    def test_message_priority_enum(self):
        """MessagePriority enum has HIGH, NORMAL, LOW."""
        assert MessagePriority.HIGH.value == 1
        assert MessagePriority.NORMAL.value == 2
        assert MessagePriority.LOW.value == 3

    def test_message_priority_ordering(self):
        """Messages can be queued and dequeued by priority."""
        msg_low = AgentMessage(id="1", sender="a", recipient=None, content={}, priority=MessagePriority.LOW)
        msg_high = AgentMessage(id="2", sender="b", recipient=None, content={}, priority=MessagePriority.HIGH)
        msg_normal = AgentMessage(id="3", sender="c", recipient=None, content={}, priority=MessagePriority.NORMAL)

        # HIGH should come first (lowest value)
        assert msg_high.priority.value < msg_normal.priority.value
        assert msg_normal.priority.value < msg_low.priority.value

    def test_broadcast_recipient_none(self):
        """Recipient=None means broadcast to all."""
        msg = AgentMessage(id="1", sender="a", recipient=None, content={})
        assert msg.recipient is None


class TestAgentMessageBus:
    """Test AgentMessageBus."""

    def test_publish_subscribe(self):
        """Test publish and subscribe flow."""
        bus = AgentMessageBus()
        received = []

        def callback(msg):
            received.append(msg)

        bus.subscribe("agent1", callback=callback)
        bus.broadcast("system", {"type": "event", "data": "test"})

        # Deliver to agent1
        msg = bus.deliver_next("agent1", timeout=0.1)
        assert msg is not None
        assert msg.content["data"] == "test"

    def test_priority_ordering_in_queue(self):
        """HIGH priority messages delivered before NORMAL/LOW."""
        bus = AgentMessageBus()
        bus.subscribe("test", callback=lambda m: None)

        bus.publish(AgentMessage(id="1", sender="a", recipient=None, content={}, priority=MessagePriority.LOW))
        bus.publish(AgentMessage(id="2", sender="b", recipient=None, content={}, priority=MessagePriority.HIGH))
        bus.publish(AgentMessage(id="3", sender="c", recipient=None, content={}, priority=MessagePriority.NORMAL))

        # HIGH should come first
        first = bus.deliver_next("test", timeout=0.1)
        assert first.priority == MessagePriority.HIGH

    def test_deliver_next_returns_none_for_no_subscription(self):
        """Messages stay in queue if no subscription exists."""
        bus = AgentMessageBus()
        bus.publish(AgentMessage(id="1", sender="a", recipient=None, content={}))

        # No subscription - should return None and re-queue
        result = bus.deliver_next("unsubscribed_agent", timeout=0.1)
        assert result is None

    def test_filter_based_subscription(self):
        """Filter-based subscription prevents unwanted message delivery."""
        bus = AgentMessageBus()
        received = []

        # Only accept HIGH priority messages
        def filter_fn(msg):
            return msg.priority == MessagePriority.HIGH

        def callback(msg):
            received.append(msg)

        bus.subscribe("agent1", filter_fn=filter_fn, callback=callback)
        bus.publish(AgentMessage(id="1", sender="a", recipient=None, content={}, priority=MessagePriority.LOW))
        bus.publish(AgentMessage(id="2", sender="b", recipient=None, content={}, priority=MessagePriority.HIGH))

        # Should only receive HIGH priority
        msg = bus.deliver_next("agent1", timeout=0.1)
        assert msg is not None
        assert msg.priority == MessagePriority.HIGH
        assert len(received) == 1
