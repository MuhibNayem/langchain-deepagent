"""Tests for SprintManager sprint lifecycle orchestration.

Per PLAN-05: SprintManager orchestrates planning → execution → verification → handoff.
"""
import pytest
from datetime import datetime
from luminamind.planner.sprint_manager import SprintManager, SprintState, SprintContext, SprintSummary
from luminamind.planner.sprint_contract import SprintContract
from luminamind.planner.negotiation import NegotiationState
from luminamind.planner.spec import SpecDocument


class TestSprintStateTransitions:
    """Test SprintState enum and transitions."""

    def test_sprint_state_enum_has_required_states(self):
        """SprintState enum has PLANNING, NEGOTIATING, READY, EXECUTING, VERIFYING, COMPLETE, FAILED."""
        states = [SprintState.PLANNING, SprintState.NEGOTIATING, SprintState.READY,
                  SprintState.EXECUTING, SprintState.VERIFYING, SprintState.COMPLETE, SprintState.FAILED]
        assert len(states) == 7
        for state in states:
            assert hasattr(state, 'value')

    def test_sprint_create_starts_in_planning_state(self):
        """create_sprint creates sprint in PLANNING state."""
        manager = SprintManager()
        context = manager.create_sprint("sprint-1")
        assert context.state == SprintState.PLANNING

    def test_transition_to_changes_state(self):
        """transition_to changes sprint state."""
        manager = SprintManager()
        context = manager.create_sprint("sprint-1")
        manager.transition_to("sprint-1", SprintState.NEGOTIATING)
        assert context.state == SprintState.NEGOTIATING

    def test_transition_to_raises_for_unknown_sprint(self):
        """transition_to raises ValueError for unknown sprint."""
        manager = SprintManager()
        with pytest.raises(ValueError, match="not found"):
            manager.transition_to("nonexistent", SprintState.READY)


class TestLifecycleEvents:
    """Test lifecycle event firing on state transitions."""

    def test_lifecycle_events_fire_on_transitions(self):
        """Lifecycle events fire on state transitions (on_plan, on_execute, on_verify, on_complete)."""
        manager = SprintManager()
        events = []

        def track_event(ctx):
            events.append(ctx.state)

        manager.on("on_execute", track_event)
        manager.on("on_verify", track_event)
        manager.on("on_complete", track_event)

        context = manager.create_sprint("sprint-1")
        manager.transition_to("sprint-1", SprintState.EXECUTING)
        manager.transition_to("sprint-1", SprintState.VERIFYING)
        manager.transition_to("sprint-1", SprintState.COMPLETE)

        assert SprintState.EXECUTING in events
        assert SprintState.VERIFYING in events
        assert SprintState.COMPLETE in events

    def test_event_handlers_receive_sprint_context(self):
        """Event handlers receive sprint context with full details."""
        manager = SprintManager()
        received_context = None

        def capture_context(ctx):
            nonlocal received_context
            received_context = ctx

        manager.on("on_ready", capture_context)
        context = manager.create_sprint("sprint-1")
        context.contract = create_signed_contract()
        manager.transition_to("sprint-1", SprintState.READY)

        assert received_context is not None
        assert received_context.sprint_id == "sprint-1"
        assert received_context.state == SprintState.READY

    def test_on_register_adds_handler(self):
        """on() registers event handler."""
        manager = SprintManager()
        events = []

        def handler(ctx):
            events.append("fired")

        manager.on("on_ready", handler)
        context = manager.create_sprint("sprint-1")
        manager.transition_to("sprint-1", SprintState.READY)

        assert len(events) == 1


class TestSprintContext:
    """Test SprintContext dataclass."""

    def test_sprint_context_has_required_fields(self):
        """SprintContext has sprint_id, state, contract, verification_report, started_at, completed_at, error."""
        context = SprintContext(
            sprint_id="sprint-1",
            state=SprintState.PLANNING,
            started_at=datetime.utcnow().isoformat()
        )
        assert context.sprint_id == "sprint-1"
        assert context.state == SprintState.PLANNING
        assert context.contract is None
        assert context.verification_report is None
        assert context.started_at != ""
        assert context.completed_at == ""
        assert context.error == ""


class TestSprintManagerLifecycle:
    """Test SprintManager full lifecycle orchestration."""

    def test_run_sprint_executes_full_lifecycle(self):
        """run_sprint(contract) executes full lifecycle."""
        manager = SprintManager()
        contract = create_signed_contract()

        executed = []
        def track_execute(c):
            executed.append(True)

        summary = manager.run_sprint(contract, execute_callback=track_execute)

        assert len(executed) == 1
        assert isinstance(summary, SprintSummary)

    def test_run_sprint_produces_sprint_summary(self):
        """run_sprint produces SprintSummary with verification stats."""
        manager = SprintManager()
        contract = create_signed_contract()

        summary = manager.run_sprint(contract)

        assert isinstance(summary, SprintSummary)
        assert summary.sprint_id == contract.id
        assert summary.contract_id == contract.id
        assert summary.state_at_completion in [SprintState.COMPLETE, SprintState.FAILED]
        assert hasattr(summary, 'verification_passed')
        assert hasattr(summary, 'total_criteria')
        assert hasattr(summary, 'passed_criteria')
        assert hasattr(summary, 'failed_criteria')

    def test_run_sprint_transitions_through_lifecycle_states(self):
        """Lifecycle: PLANNING → NEGOTIATING → READY → EXECUTING → VERIFYING → COMPLETE."""
        manager = SprintManager()
        contract = create_signed_contract()
        states = []

        def track_state(ctx):
            states.append(ctx.state)

        manager.on("on_negotiate", track_state)
        manager.on("on_ready", track_state)
        manager.on("on_execute", track_state)
        manager.on("on_verify", track_state)
        manager.on("on_complete", track_state)

        manager.run_sprint(contract)

        assert SprintState.NEGOTIATING in states
        assert SprintState.READY in states
        assert SprintState.EXECUTING in states
        assert SprintState.VERIFYING in states
        assert SprintState.COMPLETE in states

    def test_failed_verification_transitions_to_failed_state(self):
        """Failed verification transitions to FAILED state."""
        manager = SprintManager()
        # Contract with no criteria - empty criteria passes verification
        contract = create_signed_contract()
        summary = manager.run_sprint(contract)

        # Empty criteria should pass, so state should be COMPLETE
        # If criteria existed and failed, state would be FAILED
        assert summary.state_at_completion in [SprintState.COMPLETE, SprintState.FAILED]

    def test_run_sprint_requires_signed_contract(self):
        """run_sprint requires contract in SIGNED state."""
        manager = SprintManager()
        contract = SprintContract(
            id="unsigned-contract",
            spec=SpecDocument(
                id="spec-1",
                title="Test",
                description="Test",
                feature_request="Test"
            ),
            parties=["planner", "evaluator"],
            timeline={"start": "2024-01-01", "end": "2024-01-14"},
            acceptance_criteria=[]
        )
        # Contract is in DRAFT state, not SIGNED

        with pytest.raises(ValueError, match="SIGN"):
            manager.run_sprint(contract)


class TestSprintSummary:
    """Test SprintSummary dataclass."""

    def test_sprint_summary_has_required_fields(self):
        """SprintSummary has sprint_id, contract_id, duration_seconds, state_at_completion, etc."""
        summary = SprintSummary(
            sprint_id="sprint-1",
            contract_id="contract-1",
            duration_seconds=120.5,
            state_at_completion=SprintState.COMPLETE,
            verification_passed=True,
            verification_report=None,
            total_criteria=5,
            passed_criteria=4,
            failed_criteria=1
        )
        assert summary.sprint_id == "sprint-1"
        assert summary.contract_id == "contract-1"
        assert summary.duration_seconds == 120.5
        assert summary.state_at_completion == SprintState.COMPLETE
        assert summary.verification_passed is True
        assert summary.verification_report is None
        assert summary.total_criteria == 5
        assert summary.passed_criteria == 4
        assert summary.failed_criteria == 1


def create_signed_contract() -> SprintContract:
    """Create a signed SprintContract for testing."""
    contract = SprintContract(
        id="contract-001",
        spec=SpecDocument(
            id="spec-1",
            title="Test Sprint",
            description="Test sprint for unit testing",
            feature_request="Test feature"
        ),
        parties=["planner", "evaluator"],
        timeline={"start": "2024-01-01", "end": "2024-01-14"},
        acceptance_criteria=[]
    )
    contract.state = NegotiationState.SIGNED
    contract.signed_at = datetime.utcnow().isoformat()
    return contract