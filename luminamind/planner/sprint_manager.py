"""SprintManager for sprint lifecycle orchestration.

Per PLAN-05: SprintManager orchestrates planning → execution → verification → handoff.
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable

from luminamind.planner.contract_verifier import ContractVerifier, VerificationReport
from luminamind.planner.negotiation import NegotiationState
from luminamind.planner.sprint_contract import SprintContract


class SprintState(Enum):
    """Sprint lifecycle states."""
    PLANNING = "planning"
    NEGOTIATING = "negotiating"
    READY = "ready"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class SprintContext:
    """Sprint execution context."""
    sprint_id: str
    state: SprintState
    contract: SprintContract | None = None
    verification_report: VerificationReport | None = None
    started_at: str = ""
    completed_at: str = ""
    error: str = ""


@dataclass
class SprintSummary:
    """Sprint execution summary with verification stats."""
    sprint_id: str
    contract_id: str
    duration_seconds: float
    state_at_completion: SprintState
    verification_passed: bool
    verification_report: VerificationReport | None
    total_criteria: int
    passed_criteria: int
    failed_criteria: int


class SprintManager:
    """Manages sprint lifecycle orchestration."""

    def __init__(self):
        self.sprints: dict[str, SprintContext] = {}
        self.event_handlers: dict[str, list[Callable]] = {
            "on_plan": [],
            "on_negotiate": [],
            "on_ready": [],
            "on_execute": [],
            "on_verify": [],
            "on_complete": [],
            "on_fail": [],
        }

    def on(self, event: str, handler: Callable) -> None:
        """Register event handler."""
        if event in self.event_handlers:
            self.event_handlers[event].append(handler)

    def _fire_event(self, event: str, context: SprintContext) -> None:
        """Fire lifecycle event to all handlers."""
        for handler in self.event_handlers.get(event, []):
            try:
                handler(context)
            except Exception as e:
                logging.warning(f"Event handler {event} failed: {e}")

    def create_sprint(self, sprint_id: str) -> SprintContext:
        """Create new sprint in PLANNING state."""
        context = SprintContext(
            sprint_id=sprint_id,
            state=SprintState.PLANNING,
            started_at=datetime.utcnow().isoformat()
        )
        self.sprints[sprint_id] = context
        return context

    def transition_to(self, sprint_id: str, new_state: SprintState) -> None:
        """Transition sprint to new state."""
        context = self.sprints.get(sprint_id)
        if not context:
            raise ValueError(f"Sprint {sprint_id} not found")

        context.state = new_state

        state_to_event = {
            SprintState.NEGOTIATING: "on_negotiate",
            SprintState.READY: "on_ready",
            SprintState.EXECUTING: "on_execute",
            SprintState.VERIFYING: "on_verify",
            SprintState.COMPLETE: "on_complete",
            SprintState.FAILED: "on_fail",
        }

        if new_state in state_to_event:
            self._fire_event(state_to_event[new_state], context)

    def run_sprint(
        self,
        contract: SprintContract,
        execute_callback: Callable | None = None
    ) -> SprintSummary:
        """Run full sprint lifecycle with contract.

        Args:
            contract: SprintContract to execute
            execute_callback: Optional callback to execute during EXECUTING state

        Returns:
            SprintSummary with verification results

        Raises:
            ValueError: If contract is not in SIGNED state
        """
        sprint_id = contract.id
        context = self.create_sprint(sprint_id)
        context.contract = contract

        try:
            # PLANNING → NEGOTIATING
            self.transition_to(sprint_id, SprintState.NEGOTIATING)

            # NEGOTIATING → READY (contract must be signed)
            if contract.state != NegotiationState.SIGNED:
                raise ValueError(f"Contract must be SIGNED, got {contract.state.value}")
            self.transition_to(sprint_id, SprintState.READY)

            # READY → EXECUTING
            self.transition_to(sprint_id, SprintState.EXECUTING)

            # Execute sprint work
            if execute_callback:
                execute_callback(contract)

            # EXECUTING → VERIFYING
            self.transition_to(sprint_id, SprintState.VERIFYING)

            # Verify contract
            verifier = ContractVerifier()
            report = verifier.verify_contract(contract)
            context.verification_report = report

            # VERIFYING → COMPLETE or FAILED
            if report.overall_passed:
                self.transition_to(sprint_id, SprintState.COMPLETE)
                context.completed_at = datetime.utcnow().isoformat()
            else:
                self.transition_to(sprint_id, SprintState.FAILED)
                context.error = f"{report.summary['failed']} criteria failed"

        except Exception as e:
            self.transition_to(sprint_id, SprintState.FAILED)
            context.error = str(e)
            raise

        return self._generate_summary(context)

    def _generate_summary(self, context: SprintContext) -> SprintSummary:
        """Generate sprint summary from context."""
        started = datetime.fromisoformat(context.started_at)
        ended = datetime.fromisoformat(context.completed_at or datetime.utcnow().isoformat())
        duration = (ended - started).total_seconds()

        report = context.verification_report
        verification_passed = report.overall_passed if report else False

        return SprintSummary(
            sprint_id=context.sprint_id,
            contract_id=context.contract.id if context.contract else "",
            duration_seconds=duration,
            state_at_completion=context.state,
            verification_passed=verification_passed,
            verification_report=report,
            total_criteria=report.summary["total"] if report else 0,
            passed_criteria=report.summary["passed"] if report else 0,
            failed_criteria=report.summary["failed"] if report else 0,
        )