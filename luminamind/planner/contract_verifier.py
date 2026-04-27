"""Contract verification framework for criterion-by-criterion checking.

Per PLAN-04: Contract verification with criterion-by-criterion checking.
Per PLAN-05: Contract verification runs as part of sprint lifecycle.
"""
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from luminamind.planner.sprint_contract import SprintContract


@dataclass
class CriterionResult:
    """Result of verifying a single acceptance criterion.

    Attributes:
        criterion_id: Unique identifier for this criterion
        description: Human-readable description
        passed: Whether the criterion was satisfied
        evidence: List of evidence strings (output, exit codes, etc.)
        error_message: Error message if verification failed
        remediation: Suggested fix if verification failed
        checked_at: ISO timestamp when verification ran
    """
    criterion_id: str
    description: str
    passed: bool
    evidence: list[str] = field(default_factory=list)
    error_message: str = ""
    remediation: str = ""
    checked_at: str = ""

    def __post_init__(self):
        if not self.checked_at:
            self.checked_at = datetime.now(timezone.utc).isoformat()


@dataclass
class VerificationReport:
    """Report from verifying all acceptance criteria in a contract.

    Attributes:
        contract_id: ID of the contract being verified
        spec_id: ID of the spec containing the criteria
        timestamp: ISO timestamp of verification
        overall_passed: True if all criteria passed
        results: List of per-criterion results
        summary: Dict with total/passed/failed/pass_rate
    """
    contract_id: str
    spec_id: str
    timestamp: str = ""
    overall_passed: bool = False
    results: list[CriterionResult] = field(default_factory=list)
    summary: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        self._update_summary()

    def _update_summary(self):
        """Update summary statistics."""
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed
        self.summary = {
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": (passed / total * 100) if total > 0 else 0
        }
        # overall_passed is True only if there are results and all passed
        self.overall_passed = total > 0 and failed == 0

    def add_result(self, result: CriterionResult) -> None:
        """Add a criterion result and update summary."""
        self.results.append(result)
        self._update_summary()


class ContractVerifier:
    """Verifies acceptance criteria by executing verify_method commands.

    Per PLAN-04: Criterion-by-criterion checking with pass/fail determination.
    """

    def __init__(self, working_dir: Optional[Path] = None):
        """Initialize verifier.

        Args:
            working_dir: Working directory for command execution (default: cwd)
        """
        self.working_dir = working_dir or Path.cwd()

    def verify_contract(self, contract: SprintContract) -> VerificationReport:
        """Verify all acceptance criteria in contract.

        Args:
            contract: SprintContract to verify

        Returns:
            VerificationReport with per-criterion results
        """
        report = VerificationReport(
            contract_id=contract.id,
            spec_id=contract.spec.id
        )

        for criterion_id in contract.acceptance_criteria:
            criterion = self._find_criterion(contract.spec, criterion_id)
            if not criterion:
                result = CriterionResult(
                    criterion_id=criterion_id,
                    description=f"Criterion {criterion_id} not found in spec",
                    passed=False,
                    error_message="Criterion not found",
                    remediation="Add acceptance criterion to spec",
                )
            else:
                result = self._verify_criterion(criterion)

            report.add_result(result)

        return report

    def _find_criterion(self, spec, criterion_id: str):
        """Find criterion in spec user stories.

        Args:
            spec: SpecDocument to search
            criterion_id: ID of criterion to find

        Returns:
            AcceptanceCriterion if found, None otherwise
        """
        for story in spec.user_stories:
            for criterion in story.criteria:
                if criterion.id == criterion_id:
                    return criterion
        return None

    def _verify_criterion(self, criterion) -> CriterionResult:
        """Run verification command for a criterion.

        Args:
            criterion: AcceptanceCriterion to verify

        Returns:
            CriterionResult with pass/fail and evidence
        """
        verify_method = criterion.verify_method
        result = CriterionResult(
            criterion_id=criterion.id,
            description=criterion.description,
            passed=False,
        )

        try:
            if verify_method.startswith("pytest"):
                cmd = verify_method.split()
                proc = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    cwd=self.working_dir,
                    timeout=60
                )
                result.evidence.append(f"Exit code: {proc.returncode}")
                if proc.stdout:
                    result.evidence.append(proc.stdout[:500])
                if proc.stderr:
                    result.evidence.append(proc.stderr[:500])
                result.passed = proc.returncode == 0
                if not result.passed:
                    result.error_message = "Test failed"
                    result.remediation = f"Fix test or update verify_method: {verify_method}"

            elif verify_method.startswith("bash") or verify_method.startswith("sh"):
                cmd = verify_method[5:] if verify_method.startswith("bash ") else verify_method[3:]
                proc = subprocess.run(
                    ["bash", "-c", cmd],
                    capture_output=True,
                    text=True,
                    cwd=self.working_dir,
                    timeout=60
                )
                result.passed = proc.returncode == 0
                result.evidence.append(proc.stdout[:500])

            else:
                result.error_message = f"Unknown verify_method type: {verify_method}"
                result.remediation = "Use pytest or bash prefix for verification command"

        except subprocess.TimeoutExpired:
            result.passed = False
            result.error_message = "Verification timed out after 60s"
            result.remediation = "Optimize test or increase timeout"

        except Exception as e:
            result.passed = False
            result.error_message = str(e)
            result.remediation = "Check verify_method command is valid"

        return result