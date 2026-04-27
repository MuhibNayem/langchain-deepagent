"""Negotiation protocol state machine for contract negotiation.

Per PLAN-03: Negotiation protocol enables signed agreements.
"""
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime


class NegotiationState(Enum):
    """States for contract negotiation lifecycle."""
    DRAFT = "draft"
    PROPOSED = "proposed"
    COUNTERED = "countered"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    SIGNED = "signed"


class InvalidTransitionError(Exception):
    """Raised when state transition is not allowed."""
    pass


@dataclass
class NegotiationAction:
    """An action taken during contract negotiation.

    Attributes:
        action: The type of action (propose, counter, accept, reject, sign)
        actor: Who performed the action (planner, evaluator, human)
        timestamp: ISO timestamp of when action occurred
        comments: Optional comments about the action
        proposed_changes: Dict of proposed changes (for counter actions)
    """
    action: str
    actor: str
    timestamp: str
    comments: str = ""
    proposed_changes: dict = field(default_factory=dict)


class NegotiationProtocol:
    """State machine for contract negotiation.

    Enforces valid state transitions and records negotiation history.
    """

    TRANSITIONS = {
        NegotiationState.DRAFT: [NegotiationState.PROPOSED],
        NegotiationState.PROPOSED: [NegotiationState.COUNTERED, NegotiationState.ACCEPTED, NegotiationState.REJECTED],
        NegotiationState.COUNTERED: [NegotiationState.PROPOSED, NegotiationState.ACCEPTED, NegotiationState.REJECTED],
        NegotiationState.ACCEPTED: [NegotiationState.SIGNED],
        NegotiationState.REJECTED: [],  # Terminal state
        NegotiationState.SIGNED: [],  # Terminal state
    }

    def next_state(self, current: NegotiationState, action: str) -> NegotiationState:
        """Get next state based on current state and action.

        Args:
            current: Current negotiation state
            action: Action to perform (propose, counter, accept, reject, sign)

        Returns:
            Next negotiation state

        Raises:
            InvalidTransitionError: If action is not valid from current state
        """
        valid_next_states = self.TRANSITIONS.get(current, [])

        action_to_state = {
            "propose": NegotiationState.PROPOSED,
            "counter": NegotiationState.COUNTERED,
            "accept": NegotiationState.ACCEPTED,
            "reject": NegotiationState.REJECTED,
            "sign": NegotiationState.SIGNED,
        }

        if action not in action_to_state:
            raise InvalidTransitionError(f"Unknown action: {action}")

        next_state = action_to_state[action]

        if next_state not in valid_next_states:
            raise InvalidTransitionError(
                f"Cannot {action} from {current.value}. Valid: {[s.value for s in valid_next_states]}"
            )

        return next_state

    def record_action(self, current: NegotiationState, action: NegotiationAction) -> NegotiationState:
        """Record action and return new state.

        Args:
            current: Current negotiation state
            action: NegotiationAction to record

        Returns:
            New negotiation state after applying action
        """
        new_state = self.next_state(current, action.action)
        return new_state