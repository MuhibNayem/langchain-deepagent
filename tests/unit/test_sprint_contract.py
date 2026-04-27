"""Tests for SprintContract with negotiation, persistence, and version control."""
import pytest
import tempfile
from pathlib import Path
from luminamind.planner.sprint_contract import SprintContract
from luminamind.planner.negotiation import NegotiationState
from luminamind.planner.spec import SpecDocument


class TestSprintContract:
    """Test SprintContract lifecycle and persistence."""

    def create_sample_contract(self) -> SprintContract:
        """Create a sample contract for testing."""
        return SprintContract(
            id="contract-001",
            spec=SpecDocument(
                id="spec-1",
                title="Login Feature",
                description="Add login functionality",
                feature_request="As a user I want to login with email",
            ),
            parties=["planner", "evaluator"],
            timeline={"start": "2024-01-01", "end": "2024-01-14", "sprint": "2wk"},
            acceptance_criteria=["AC-1"]
        )

    def test_initial_state_is_draft(self):
        """Test contract starts in DRAFT state."""
        contract = self.create_sample_contract()
        assert contract.state == NegotiationState.DRAFT

    def test_negotiation_flow_draft_to_proposed(self):
        """Test: Contract negotiation flow DRAFT → PROPOSED."""
        contract = self.create_sample_contract()
        contract.propose("planner")
        assert contract.state == NegotiationState.PROPOSED

    def test_negotiation_flow_proposed_to_accepted(self):
        """Test: Contract negotiation flow PROPOSED → ACCEPTED."""
        contract = self.create_sample_contract()
        contract.propose("planner")
        contract.accept("evaluator")
        assert contract.state == NegotiationState.ACCEPTED

    def test_negotiation_flow_proposed_to_rejected(self):
        """Test: Contract negotiation flow PROPOSED → REJECTED."""
        contract = self.create_sample_contract()
        contract.propose("planner")
        contract.reject("evaluator", "Too aggressive timeline")
        assert contract.state == NegotiationState.REJECTED

    def test_full_negotiation_flow_signed(self):
        """Test: Contract negotiation flow DRAFT → PROPOSED → ACCEPTED → SIGNED."""
        contract = self.create_sample_contract()
        assert contract.state == NegotiationState.DRAFT

        contract.propose("planner")
        assert contract.state == NegotiationState.PROPOSED

        contract.accept("evaluator")
        assert contract.state == NegotiationState.ACCEPTED

        contract.sign("planner")
        assert contract.state == NegotiationState.SIGNED
        assert contract.signed_at != ""

    def test_counter_proposal_tracking(self):
        """Test: Counter-proposal tracking with proposed changes."""
        contract = self.create_sample_contract()
        contract.propose("planner")
        contract.counter("evaluator", {"timeline": {"end": "2024-01-21"}})
        assert contract.state == NegotiationState.COUNTERED

    def test_version_increment_on_propose(self):
        """Test: Version increments on propose action."""
        contract = self.create_sample_contract()
        initial_version = contract.version
        contract.propose("planner")
        assert contract.version == initial_version + 1

    def test_version_increment_on_accept(self):
        """Test: Version increments on accept action."""
        contract = self.create_sample_contract()
        contract.propose("planner")
        initial_version = contract.version
        contract.accept("evaluator")
        assert contract.version == initial_version + 1

    def test_version_increment_on_counter(self):
        """Test: Version increments on counter action."""
        contract = self.create_sample_contract()
        contract.propose("planner")
        initial_version = contract.version
        contract.counter("evaluator", {"timeline": {"end": "2024-01-21"}})
        assert contract.version == initial_version + 1

    def test_history_records_actions(self):
        """Test: Contract history tracks all negotiation actions."""
        contract = self.create_sample_contract()
        contract.propose("planner")
        contract.accept("evaluator")
        assert len(contract.history) == 2
        assert contract.history[0].action == "propose"
        assert contract.history[1].action == "accept"

    def test_contract_persistence(self, tmp_path):
        """Test: Contract persists to JSON and restores."""
        contract = self.create_sample_contract()
        contract.propose("planner")

        path = tmp_path / "contract.json"
        contract.save(path)

        loaded = SprintContract.load(path)
        assert loaded.state == NegotiationState.PROPOSED
        assert loaded.version == contract.version
        assert loaded.id == contract.id

    def test_contract_persistence_restores_history(self, tmp_path):
        """Test: Contract persistence restores full history."""
        contract = self.create_sample_contract()
        contract.propose("planner")
        contract.accept("evaluator")

        path = tmp_path / "contract.json"
        contract.save(path)

        loaded = SprintContract.load(path)
        assert len(loaded.history) == 2
        assert loaded.history[0].action == "propose"
        assert loaded.history[1].action == "accept"

    def test_contract_to_dict_serialization(self):
        """Test: Contract serializes to dict correctly."""
        contract = self.create_sample_contract()
        contract.propose("planner")

        data = contract.to_dict()
        assert isinstance(data, dict)
        assert data["id"] == "contract-001"
        assert data["state"] == "proposed"
        assert data["version"] == 2  # Initial (1) + propose (1)
        assert len(data["history"]) == 1

    def test_contract_from_dict_deserialization(self, tmp_path):
        """Test: Contract deserializes from dict correctly."""
        contract = self.create_sample_contract()
        contract.propose("planner")
        contract.accept("evaluator")

        path = tmp_path / "contract.json"
        contract.save(path)

        loaded = SprintContract.load(path)
        assert loaded.id == contract.id
        assert loaded.state == NegotiationState.ACCEPTED
        assert loaded.spec.id == "spec-1"

    def test_rejected_contract_cannot_transition(self):
        """Test: Rejected contract is terminal."""
        contract = self.create_sample_contract()
        contract.propose("planner")
        contract.reject("evaluator", "Unacceptable terms")
        assert contract.state == NegotiationState.REJECTED
        # Cannot sign from rejected
        from luminamind.planner.negotiation import InvalidTransitionError
        with pytest.raises(InvalidTransitionError):
            contract.sign("planner")

    def test_signed_contract_cannot_transition(self):
        """Test: Signed contract is terminal."""
        contract = self.create_sample_contract()
        contract.propose("planner")
        contract.accept("evaluator")
        contract.sign("planner")
        assert contract.state == NegotiationState.SIGNED
        # Cannot propose again
        from luminamind.planner.negotiation import InvalidTransitionError
        with pytest.raises(InvalidTransitionError):
            contract.propose("planner")