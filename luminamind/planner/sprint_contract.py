"""SprintContract framework with negotiation, persistence, and version control.

Per PLAN-03: Contract negotiation produces signed agreements.
Per PLAN-04: Contract verification with criterion-by-criterion checking.
"""
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from luminamind.planner.spec import SpecDocument
from luminamind.planner.negotiation import NegotiationState, NegotiationAction, NegotiationProtocol, InvalidTransitionError


@dataclass
class SprintContract:
    """A sprint contract binding planner and evaluator in a negotiated agreement.

    Attributes:
        id: Unique identifier for this contract
        spec: The SpecDocument this contract governs
        parties: List of party identifiers (e.g., ["planner", "evaluator"])
        timeline: Sprint timeline dict with start, end, sprint keys
        acceptance_criteria: List of criterion IDs from the spec
        state: Current negotiation state
        version: Version number (increments on each modification)
        history: List of all negotiation actions
        created_at: ISO timestamp of creation
        updated_at: ISO timestamp of last modification
        signed_at: ISO timestamp when contract was signed (empty if not signed)
    """

    id: str
    spec: SpecDocument
    parties: List[str]
    timeline: dict
    acceptance_criteria: List[str]
    state: NegotiationState = NegotiationState.DRAFT
    version: int = 1
    history: List[NegotiationAction] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    signed_at: str = ""

    def __post_init__(self):
        """Initialize timestamps if not provided."""
        if not self.created_at:
            self.created_at = datetime.utcnow().isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at

    def propose(self, actor: str, comments: str = "") -> None:
        """Propose the contract for negotiation.

        Args:
            actor: Who is proposing (planner, evaluator, human)
            comments: Optional comments about the proposal
        """
        self._transition("propose", actor, comments)

    def counter(self, actor: str, proposed_changes: dict, comments: str = "") -> None:
        """Counter-propose with changes to the contract.

        Args:
            actor: Who is making the counter-proposal
            proposed_changes: Dict of proposed changes (e.g., {"timeline": {...}})
            comments: Optional comments about the counter-proposal
        """
        action = NegotiationAction(
            action="counter",
            actor=actor,
            timestamp=datetime.utcnow().isoformat(),
            comments=comments,
            proposed_changes=proposed_changes
        )
        self._record_action(action)

    def accept(self, actor: str, comments: str = "") -> None:
        """Accept the contract proposal.

        Args:
            actor: Who is accepting
            comments: Optional comments about the acceptance
        """
        self._transition("accept", actor, comments)

    def reject(self, actor: str, reason: str) -> None:
        """Reject the contract proposal.

        Args:
            actor: Who is rejecting
            reason: Reason for rejection
        """
        self._transition("reject", actor, reason)

    def sign(self, actor: str) -> None:
        """Sign the contract (both parties must sign).

        Args:
            actor: Who is signing
        """
        self._transition("sign", actor, "")
        if self.state == NegotiationState.SIGNED:
            self.signed_at = datetime.utcnow().isoformat()

    def _transition(self, action: str, actor: str, comments: str) -> None:
        """Internal method to perform a state transition.

        Args:
            action: The action to perform
            actor: Who is performing the action
            comments: Optional comments
        """
        protocol = NegotiationProtocol()
        action_obj = NegotiationAction(
            action=action,
            actor=actor,
            timestamp=datetime.utcnow().isoformat(),
            comments=comments
        )
        self.state = protocol.record_action(self.state, action_obj)
        self.history.append(action_obj)
        self.updated_at = datetime.utcnow().isoformat()
        self.version += 1

    def _record_action(self, action: NegotiationAction) -> None:
        """Internal method to record an action with proposed_changes.

        Args:
            action: The NegotiationAction to record
        """
        protocol = NegotiationProtocol()
        self.state = protocol.record_action(self.state, action)
        self.history.append(action)
        self.updated_at = datetime.utcnow().isoformat()
        self.version += 1

    def to_dict(self) -> dict:
        """Serialize to dict for JSON persistence.

        Returns:
            Dictionary representation of the contract
        """
        return {
            "id": self.id,
            "spec": self.spec.to_dict(),
            "parties": self.parties,
            "timeline": self.timeline,
            "acceptance_criteria": self.acceptance_criteria,
            "state": self.state.value,
            "version": self.version,
            "history": [
                {
                    "action": h.action,
                    "actor": h.actor,
                    "timestamp": h.timestamp,
                    "comments": h.comments,
                    "proposed_changes": h.proposed_changes
                }
                for h in self.history
            ],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "signed_at": self.signed_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SprintContract":
        """Deserialize from dict.

        Args:
            data: Dictionary representation of the contract

        Returns:
            SprintContract instance
        """
        spec = SpecDocument.from_dict(data["spec"])
        contract = cls(
            id=data["id"],
            spec=spec,
            parties=data["parties"],
            timeline=data["timeline"],
            acceptance_criteria=data["acceptance_criteria"],
            state=NegotiationState[data["state"].upper()],
            version=data["version"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            signed_at=data.get("signed_at", ""),
        )
        # Replay history to restore state
        for h in data.get("history", []):
            action = NegotiationAction(
                action=h["action"],
                actor=h["actor"],
                timestamp=h["timestamp"],
                comments=h.get("comments", ""),
                proposed_changes=h.get("proposed_changes", {})
            )
            contract.history.append(action)
        return contract

    def save(self, path: Path) -> None:
        """Save contract to JSON file.

        Args:
            path: Path to save the contract JSON file
        """
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: Path) -> "SprintContract":
        """Load contract from JSON file.

        Args:
            path: Path to load the contract JSON file from

        Returns:
            SprintContract instance
        """
        with open(path) as f:
            data = json.load(f)
        return cls.from_dict(data)