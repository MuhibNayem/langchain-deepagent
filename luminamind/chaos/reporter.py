"""Chaos test reporting for result visualization."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from luminamind.chaos.engine import ChaosResult, ChaosSuiteResult
from luminamind.chaos.scenarios import ScenarioType, get_scenario


@dataclass
class ChaosReport:
    """Report of chaos test execution results.

    Attributes:
        timestamp: When the report was generated
        total_scenarios: Total number of scenarios run
        passed: Number of scenarios with graceful degradation
        failed: Number of scenarios with catastrophic failure
        results: List of all scenario results
        summary_by_type: Summary statistics grouped by scenario type
    """
    timestamp: str
    total_scenarios: int = 0
    passed: int = 0
    failed: int = 0
    results: list[ChaosResult] = field(default_factory=list)
    summary_by_type: dict[str, dict[str, Any]] = field(default_factory=dict)

    @classmethod
    def from_suite_result(cls, suite_result: ChaosSuiteResult) -> ChaosReport:
        """Create a ChaosReport from a ChaosSuiteResult.

        Args:
            suite_result: The results from running a chaos suite

        Returns:
            ChaosReport instance
        """
        # Group results by scenario type
        summary_by_type: dict[str, dict[str, Any]] = {}

        for result in suite_result.results:
            scenario = get_scenario(result.scenario_id)
            if scenario:
                type_name = scenario.scenario_type.name
                if type_name not in summary_by_type:
                    summary_by_type[type_name] = {
                        "passed": 0,
                        "failed": 0,
                        "avg_time": 0.0,
                        "total": 0,
                    }

                summary_by_type[type_name]["total"] += 1
                if result.outcome in ("success", "degraded"):
                    summary_by_type[type_name]["passed"] += 1
                else:
                    summary_by_type[type_name]["failed"] += 1

                # Update running average
                current_avg = summary_by_type[type_name]["avg_time"]
                count = summary_by_type[type_name]["total"]
                summary_by_type[type_name]["avg_time"] = (
                    (current_avg * (count - 1) + result.execution_time) / count
                )

        return cls(
            timestamp=suite_result.timestamp or datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            total_scenarios=suite_result.total_scenarios,
            passed=suite_result.passed,
            failed=suite_result.failed,
            results=suite_result.results,
            summary_by_type=summary_by_type,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert report to dictionary for JSON serialization.

        Returns:
            Dictionary representation of the report
        """
        return {
            "timestamp": self.timestamp,
            "total_scenarios": self.total_scenarios,
            "passed": self.passed,
            "failed": self.failed,
            "results": [
                {
                    "scenario_id": r.scenario_id,
                    "task": r.task,
                    "fault_injected": r.fault_injected,
                    "execution_time": r.execution_time,
                    "outcome": r.outcome,
                    "error_message": r.error_message,
                    "graceful_degradation": r.graceful_degradation,
                    "metrics": r.metrics,
                    "timestamp": r.timestamp,
                }
                for r in self.results
            ],
            "summary_by_type": self.summary_by_type,
        }


def generate_chaos_report(suite_result: ChaosSuiteResult) -> str:
    """Generate a formatted markdown chaos test report.

    Args:
        suite_result: The results from running a chaos suite

    Returns:
        Markdown-formatted report string
    """
    report = ChaosReport.from_suite_result(suite_result)

    # Build markdown report
    lines = [
        "# Chaos Test Report",
        "",
        f"**Generated:** {report.timestamp}",
        "",
        "## Summary",
        "",
        f"- **Total Scenarios:** {report.total_scenarios}",
        f"- **Passed (Graceful):** {report.passed}",
        f"- **Failed (Catastrophic):** {report.failed}",
        f"- **Success Rate:** {(report.passed / report.total_scenarios * 100) if report.total_scenarios > 0 else 0:.1f}%",
        "",
        "## Results by Scenario",
        "",
        "| Scenario | Type | Outcome | Execution Time | Graceful? |",
        "|----------|------|---------|----------------|-----------|",
    ]

    for result in report.results:
        scenario = get_scenario(result.scenario_id)
        scenario_name = scenario.name if scenario else result.scenario_id
        scenario_type = scenario.scenario_type.name if scenario else "unknown"

        # Outcome emoji
        if result.outcome == "success":
            outcome_icon = "✓ Success"
        elif result.outcome == "degraded":
            outcome_icon = "⚠ Degraded"
        else:
            outcome_icon = "✗ Failed"

        # Graceful indicator
        graceful = "Yes" if result.graceful_degradation else "No"

        # Execution time
        exec_time = f"{result.execution_time:.2f}s" if result.execution_time > 0 else "-"

        lines.append(
            f"| {scenario_name} | {scenario_type} | {outcome_icon} | {exec_time} | {graceful} |"
        )

    lines.append("")
    lines.append("## Summary by Type")
    lines.append("")

    for type_name, stats in report.summary_by_type.items():
        pass_rate = (stats["passed"] / stats["total"] * 100) if stats["total"] > 0 else 0
        lines.append(f"### {type_name}")
        lines.append("")
        lines.append(f"- Total: {stats['total']}")
        lines.append(f"- Passed: {stats['passed']}")
        lines.append(f"- Failed: {stats['failed']}")
        lines.append(f"- Pass Rate: {pass_rate:.1f}%")
        lines.append(f"- Avg Time: {stats['avg_time']:.2f}s")
        lines.append("")

    # Recommendations
    lines.append("## Recommendations")
    lines.append("")

    # Generate recommendations based on failures
    if report.failed > 0:
        lines.append("1. Review failed scenarios for resilience improvements")
        lines.append("2. Consider adding circuit breakers for critical paths")
        lines.append("3. Implement fallback mechanisms for dependency failures")
    else:
        lines.append("1. All scenarios passed with graceful degradation")
        lines.append("2. System is resilient to injected fault conditions")

    if any(s.get("failed", 0) > 0 for s in report.summary_by_type.values()):
        if "LLM" in report.summary_by_type:
            lines.append("4. Consider implementing LLM response caching")
        if "SYSTEM_REDIS" in str(report.summary_by_type):
            lines.append("5. Implement Redis fallback to in-memory cache")

    lines.append("")
    lines.append(f"*Report generated at {report.timestamp}*")

    return "\n".join(lines)


def save_report(suite_result: ChaosSuiteResult, output_path: Path | str) -> Path:
    """Save a chaos test report to a file.

    Args:
        suite_result: The results from running a chaos suite
        output_path: Path to write the report to

    Returns:
        Path to the saved report file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    report_content = generate_chaos_report(suite_result)
    output_path.write_text(report_content, encoding="utf-8")

    return output_path


def save_json_report(suite_result: ChaosSuiteResult, output_path: Path | str) -> Path:
    """Save a chaos test report as JSON.

    Args:
        suite_result: The results from running a chaos suite
        output_path: Path to write the JSON report to

    Returns:
        Path to the saved report file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    report = ChaosReport.from_suite_result(suite_result)
    import json
    output_path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")

    return output_path