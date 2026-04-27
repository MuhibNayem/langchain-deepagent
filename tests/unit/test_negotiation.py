"""Tests for negotiation state machine and protocol."""
import pytest
from luminamind.planner.negotiation import (
    NegotiationState,
    NegotiationAction,
    NegotiationProtocol,
    InvalidTransitionError,
)


class TestNegotiationState:
    """Test NegotiationState enum has all required states."""

    def test_has_all_states(self):
        """Test NegotiationState enum has DRAFT, PROPOSED, COUNTERED, ACCEPTED, REJECTED, SIGNED."""
        assert hasattr(NegotiationState, "DRAFT")
        assert hasattr(NegotiationState, "PROPOSED")
        assert hasattr(NegotiationState, "COUNTERED")
        assert hasattr(NegotiationState, "ACCEPTED")
        assert hasattr(NegotiationState, "REJECTED")
        assert hasattr(NegotiationState, "SIGNED")

    def test_state_values(self):
        """Test state string values."""
        assert NegotiationState.DRAFT.value == "draft"
        assert NegotiationState.PROPOSED.value == "proposed"
        assert NegotiationState.COUNTERED.value == "countered"
        assert NegotiationState.ACCEPTED.value == "accepted"
        assert NegotiationState.REJECTED.value == "rejected"
        assert NegotiationState.SIGNED.value == "signed"


class TestNegotiationProtocol:
    """Test NegotiationProtocol state machine."""

    def test_valid_draft_to_proposed(self):
        """Test valid transition: DRAFT → PROPOSED."""
        protocol = NegotiationProtocol()
        next_state = protocol.next_state(NegotiationState.DRAFT, "propose")
        assert next_state == NegotiationState.PROPOSED

    def test_valid_proposed_to_accepted(self):
        """Test valid transition: PROPOSED → ACCEPTED."""
        protocol = NegotiationProtocol()
        next_state = protocol.next_state(NegotiationState.PROPOSED, "accept")
        assert next_state == NegotiationState.ACCEPTED

    def test_valid_proposed_to_rejected(self):
        """Test valid transition: PROPOSED → REJECTED."""
        protocol = NegotiationProtocol()
        next_state = protocol.next_state(NegotiationState.PROPOSED, "reject")
        assert next_state == NegotiationState.REJECTED

    def test_valid_proposed_to_countered(self):
        """Test valid transition: PROPOSED → COUNTERED."""
        protocol = NegotiationProtocol()
        next_state = protocol.next_state(NegotiationState.PROPOSED, "counter")
        assert next_state == NegotiationState.COUNTERED

    def test_valid_countered_to_proposed(self):
        """Test valid transition: COUNTERED → PROPOSED."""
        protocol = NegotiationProtocol()
        next_state = protocol.next_state(NegotiationState.COUNTERED, "propose")
        assert next_state == NegotiationState.PROPOSED

    def test_valid_countered_to_accepted(self):
        """Test valid transition: COUNTERED → ACCEPTED."""
        protocol = NegotiationProtocol()
        next_state = protocol.next_state(NegotiationState.COUNTERED, "accept")
        assert next_state == NegotiationState.ACCEPTED

    def test_valid_countered_to_rejected(self):
        """Test valid transition: COUNTERED → REJECTED."""
        protocol = NegotiationProtocol()
        next_state = protocol.next_state(NegotiationState.COUNTERED, "reject")
        assert next_state == NegotiationState.REJECTED

    def test_valid_accepted_to_signed(self):
        """Test valid transition: ACCEPTED → SIGNED."""
        protocol = NegotiationProtocol()
        next_state = protocol.next_state(NegotiationState.ACCEPTED, "sign")
        assert next_state == NegotiationState.SIGNED

    def test_invalid_draft_to_accepted(self):
        """Test invalid transition: DRAFT → ACCEPTED raises error."""
        protocol = NegotiationProtocol()
        with pytest.raises(InvalidTransitionError):
            protocol.next_state(NegotiationState.DRAFT, "accept")

    def test_invalid_proposed_to_signed(self):
        """Test invalid transition: PROPOSED → SIGNED raises error."""
        protocol = NegotiationProtocol()
        with pytest.raises(InvalidTransitionError):
            protocol.next_state(NegotiationState.PROPOSED, "sign")

    def test_invalid_rejected_to_any(self):
        """Test REJECTED is terminal - cannot transition."""
        protocol = NegotiationProtocol()
        for action in ["propose", "counter", "accept", "reject", "sign"]:
            with pytest.raises(InvalidTransitionError):
                protocol.next_state(NegotiationState.REJECTED, action)

    def test_invalid_signed_to_any(self):
        """Test SIGNED is terminal - cannot transition."""
        protocol = NegotiationProtocol()
        for action in ["propose", "counter", "accept", "reject", "sign"]:
            with pytest.raises(InvalidTransitionError):
                protocol.next_state(NegotiationState.SIGNED, action)

    def test_unknown_action_raises_error(self):
        """Test unknown action raises InvalidTransitionError."""
        protocol = NegotiationProtocol()
        with pytest.raises(InvalidTransitionError):
            protocol.next_state(NegotiationState.DRAFT, "unknown_action")


class TestNegotiationAction:
    """Test NegotiationAction dataclass."""

    def test_action_structure(self):
        """Test NegotiationAction has required fields."""
        action = NegotiationAction(
            action="propose",
            actor="planner",
            timestamp="2026-04-27T10:00:00Z",
            comments="Initial proposal"
        )
        assert action.action == "propose"
        assert action.actor == "planner"
        assert action.timestamp == "2026-04-27T10:00:00Z"
        assert action.comments == "Initial proposal"
        assert action.proposed_changes == {}

    def test_action_with_proposed_changes(self):
        """Test NegotiationAction with proposed_changes."""
        changes = {"timeline": {"end": "2026-05-01"}}
        action = NegotiationAction(
            action="counter",
            actor="evaluator",
            timestamp="2026-04-27T10:00:00Z",
            comments="Suggested timeline change",
            proposed_changes=changes
        )
        assert action.proposed_changes == changes


class TestNegotiationProtocolRecordAction:
    """Test NegotiationProtocol.record_action method."""

    def test_record_action_returns_new_state(self):
        """Test record_action updates state based on action."""
        protocol = NegotiationProtocol()
        action = NegotiationAction(
            action="propose",
            actor="planner",
            timestamp="2026-04-27T10:00:00Z"
        )
        new_state = protocol.record_action(NegotiationState.DRAFT, action)
        assert new_state == NegotiationState.PROPOSED