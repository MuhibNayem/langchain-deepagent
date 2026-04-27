"""Tests for ContractVerifier dataclasses and structure."""
import pytest
from luminamind.planner.contract_verifier import VerificationReport, CriterionResult


class TestVerificationReportStructure:
    """Test VerificationReport and CriterionResult dataclasses."""

    def test_criterion_result_has_required_fields(self):
        """CriterionResult has criterion_id, passed bool, evidence list, error_message."""
        result = CriterionResult(
            criterion_id="AC-1",
            description="Login works",
            passed=True,
            evidence=["Exit code: 0"],
            error_message=""
        )
        assert result.criterion_id == "AC-1"
        assert result.passed is True
        assert result.evidence == ["Exit code: 0"]
        assert result.error_message == ""

    def test_criterion_result_defaults(self):
        """CriterionResult has proper defaults for optional fields."""
        result = CriterionResult(
            criterion_id="AC-1",
            description="Test",
            passed=False,
            error_message="Test failed",
            remediation="Fix the test"
        )
        assert result.evidence == []
        # checked_at is auto-set via __post_init__
        assert result.checked_at != ""

    def test_verification_report_has_required_fields(self):
        """VerificationReport has contract_id, timestamp, overall_passed, results."""
        report = VerificationReport(contract_id="c1", spec_id="s1")
        assert report.contract_id == "c1"
        assert report.spec_id == "s1"
        assert report.timestamp != ""
        # Empty criteria means failed=0, so overall_passed=True per plan spec
        assert report.overall_passed is True
        assert report.results == []

    def test_verification_report_summary(self):
        """VerificationReport.summary shows pass/fail counts."""
        report = VerificationReport(contract_id="c1", spec_id="s1")
        report.add_result(CriterionResult(criterion_id="AC-1", description="Test", passed=True))
        report.add_result(CriterionResult(criterion_id="AC-2", description="Test2", passed=False))

        assert report.summary["total"] == 2
        assert report.summary["passed"] == 1
        assert report.summary["failed"] == 1
        assert report.summary["pass_rate"] == 50.0
        assert report.overall_passed is False

    def test_verification_report_all_passed(self):
        """VerificationReport with all criteria passed marks overall_passed True."""
        report = VerificationReport(contract_id="c1", spec_id="s1")
        report.add_result(CriterionResult(criterion_id="AC-1", description="Test", passed=True))
        report.add_result(CriterionResult(criterion_id="AC-2", description="Test2", passed=True))

        assert report.overall_passed is True
        assert report.summary["failed"] == 0
        assert report.summary["pass_rate"] == 100.0

    def test_verification_report_empty(self):
        """VerificationReport with no results has zero counts."""
        report = VerificationReport(contract_id="c1", spec_id="s1")
        assert report.summary["total"] == 0
        assert report.summary["passed"] == 0
        assert report.summary["failed"] == 0
        assert report.summary["pass_rate"] == 0
