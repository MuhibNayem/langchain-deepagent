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


class TestConflictResolution:
    """Test conflict resolution strategies."""

    def test_concurrent_messages_timestamp_ordering(self):
        """Concurrent messages from same sender resolved by timestamp ordering."""
        from luminamind.planner.agent_message_bus import resolve_conflict, ConflictResolution

        # Create messages with different timestamps
        msg1 = AgentMessage(
            id="1",
            sender="agent1",
            recipient=None,
            content={"data": "first"}
        )
        msg2 = AgentMessage(
            id="2",
            sender="agent1",
            recipient=None,
            content={"data": "second"}
        )

        messages = [msg1, msg2]
        resolved = resolve_conflict(messages, ConflictResolution.LATEST_WINS)
        assert resolved.content["data"] == "second"

    def test_high_priority_delivered_before_normal_low(self):
        """HIGH priority messages should win in priority_wins strategy."""
        from luminamind.planner.agent_message_bus import resolve_conflict, ConflictResolution

        msg_low = AgentMessage(
            id="1",
            sender="a",
            recipient=None,
            content={"data": "low"},
            priority=MessagePriority.LOW
        )
        msg_high = AgentMessage(
            id="2",
            sender="b",
            recipient=None,
            content={"data": "high"},
            priority=MessagePriority.HIGH
        )
        msg_normal = AgentMessage(
            id="3",
            sender="c",
            recipient=None,
            content={"data": "normal"},
            priority=MessagePriority.NORMAL
        )

        resolved = resolve_conflict([msg_low, msg_normal, msg_high], ConflictResolution.HIGHEST_PRIORITY_WINS)
        assert resolved.priority == MessagePriority.HIGH

    def test_reply_routing(self):
        """Reply routing via in_reply_to correctly associates messages."""
        # Create a reply message with in_reply_to set
        original = AgentMessage(
            id="orig-1",
            sender="agent1",
            recipient="agent2",
            content={"text": "Hello"}
        )
        reply = AgentMessage(
            id="reply-1",
            sender="agent2",
            recipient="agent1",
            content={"text": "Hi there!"},
            in_reply_to="orig-1"
        )

        # Verify the reply is correctly associated
        assert reply.in_reply_to == "orig-1"
        assert original.id == reply.in_reply_to

        # Verify messages can be correlated via conversation_id if needed
        msg_with_conversation = AgentMessage(
            id="1",
            sender="a",
            recipient=None,
            content={},
            conversation_id="conv-1"
        )
        assert msg_with_conversation.conversation_id == "conv-1"


class TestOutputMerger:
    """Test OutputMerger for subagent result merging."""

    def test_merge_produces_unified_output(self):
        """OutputMerger.merge(subagent_results) produces unified output."""
        from luminamind.planner.output_merger import OutputMerger

        merger = OutputMerger()
        results = [
            {"title": "Spec", "description": "Test spec", "status": "draft"},
            {"title": "Spec", "description": "Test spec", "status": "draft"},
        ]
        result = merger.merge(results)
        assert result.unified_output["title"] == "Spec"
        assert result.unified_output["description"] == "Test spec"

    def test_merge_detects_conflict(self):
        """MergeConflict detected when subagents produce conflicting outputs."""
        from luminamind.planner.output_merger import OutputMerger

        merger = OutputMerger()
        results = [
            {"title": "First Title"},
            {"title": "Second Title"},
        ]
        result = merger.merge(results)
        assert result.has_conflicts
        assert len(result.conflicts) > 0

    def test_merge_conflict_includes_resolution_options(self):
        """MergeConflict includes resolution options."""
        from luminamind.planner.output_merger import OutputMerger

        merger = OutputMerger()
        # Use data with a clear conflict on one field only
        results = [
            {"title": "Title A", "description": "Same"},  # title conflicts
            {"title": "Title B", "description": "Same"},
        ]
        result = merger.merge(results)

        assert result.has_conflicts
        conflict = result.conflicts[0]
        assert conflict.field_path == "title"
        assert len(conflict.conflicting_values) == 2
        assert conflict.resolution != ""
        assert conflict.auto_resolved is True

    def test_merge_result_has_unified_output_and_conflicts(self):
        """MergeResult has unified output and any unresolved conflicts."""
        from luminamind.planner.output_merger import OutputMerger, MergeResult

        merger = OutputMerger()
        results = [
            {"field1": "value1"},
            {"field2": "value2"},
        ]
        result = merger.merge(results)

        assert isinstance(result, MergeResult)
        assert "field1" in result.unified_output
        assert "field2" in result.unified_output
        # Non-conflicting fields should not create conflicts
        assert not result.has_conflicts

    def test_merge_with_empty_results(self):
        """Merge handles empty results list."""
        from luminamind.planner.output_merger import OutputMerger

        merger = OutputMerger()
        result = merger.merge([])
        assert result.unified_output == {}
        assert not result.has_conflicts

    def test_merge_single_result(self):
        """Merge with single result returns that result."""
        from luminamind.planner.output_merger import OutputMerger

        merger = OutputMerger()
        result = merger.merge([{"title": "Single"}])
        assert result.unified_output["title"] == "Single"
        assert not result.has_conflicts

