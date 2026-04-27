"""Automated scoring engine for benchmark results.

This module provides the Scorer class that evaluates agent outputs
and generates score reports with category breakdowns.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from luminamind.benchmark.test_suite import TaskCategory


@dataclass
class Score:
    """Score for a single test case.

    Attributes:
        overall: Overall score (0.0-1.0)
        categories: Breakdown by scoring category
        breakdown: Detailed criterion scores
        passed: Whether the test passed (score >= 0.7)
        details: Additional context about the score
    """

    overall: float
    categories: dict[str, float] = field(default_factory=dict)
    breakdown: list[dict[str, Any]] = field(default_factory=list)
    passed: bool = False
    details: str = ""

    def __post_init__(self) -> None:
        self.passed = self.overall >= 0.7


@dataclass
class CategoryScore:
    """Aggregated score for a category of tests.

    Attributes:
        category: The task category
        average_score: Mean score across tests
        pass_rate: Proportion of tests that passed
        count: Number of tests in category
    """

    category: str
    average_score: float = 0.0
    pass_rate: float = 0.0
    count: int = 0


@dataclass
class AggregateScores:
    """Aggregated scores across all benchmark tests.

    Attributes:
        overall_average: Mean score across all tests
        category_scores: Per-category score breakdowns
        difficulty_scores: Per-difficulty score breakdowns
        percentile_25: 25th percentile score
        percentile_50: 50th percentile score (median)
        percentile_75: 75th percentile score
        total_tests: Total number of tests run
        total_passed: Number of tests that passed
    """

    overall_average: float = 0.0
    category_scores: list[CategoryScore] = field(default_factory=list)
    difficulty_scores: dict[str, float] = field(default_factory=dict)
    percentile_25: float = 0.0
    percentile_50: float = 0.0
    percentile_75: float = 0.0
    total_tests: int = 0
    total_passed: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "overall_average": self.overall_average,
            "category_scores": [
                {
                    "category": cs.category,
                    "average_score": cs.average_score,
                    "pass_rate": cs.pass_rate,
                    "count": cs.count,
                }
                for cs in self.category_scores
            ],
            "difficulty_scores": self.difficulty_scores,
            "percentiles": {
                "p25": self.percentile_25,
                "p50": self.percentile_50,
                "p75": self.percentile_75,
            },
            "total_tests": self.total_tests,
            "total_passed": self.total_passed,
            "pass_rate": self.total_passed / self.total_tests if self.total_tests > 0 else 0.0,
        }


class Scorer:
    """Scorer for evaluating benchmark test outputs.

    Provides scoring for individual test cases and aggregate
    statistics across benchmark runs.
    """

    def __init__(self, pass_threshold: float = 0.7):
        """Initialize the scorer.

        Args:
            pass_threshold: Minimum score to consider a test passed (default 0.7)
        """
        self.pass_threshold = pass_threshold

    def score_test_case(self, case: Any, output: str) -> Score:
        """Score a single test case output.

        Args:
            case: TestCase that was run
            output: The agent's output

        Returns:
            Score with overall and breakdown details
        """
        # Get the base score from the test case
        base_score = case.score(output) if hasattr(case, "score") else 0.5

        # Create category breakdown (simplified scoring)
        categories: dict[str, float] = {}
        breakdown: list[dict[str, Any]] = []

        # Determine categories based on task type
        if hasattr(case, "category"):
            cat = case.category
            if isinstance(cat, TaskCategory):
                categories[cat.value] = base_score

                # Add breakdown entry
                breakdown.append({
                    "criterion": "correctness",
                    "score": base_score,
                    "details": f"Score for {cat.value}",
                })

        # Evaluate output quality
        quality_score = self._evaluate_output_quality(output)
        if quality_score > 0:
            categories["quality"] = quality_score
            breakdown.append({
                "criterion": "quality",
                "score": quality_score,
                "details": "Output quality assessment",
            })

        # Calculate overall as weighted average
        if categories:
            overall = sum(categories.values()) / len(categories)
        else:
            overall = base_score

        details = f"Scored {output[:50]}..." if len(output) > 50 else f"Scored output"

        return Score(
            overall=overall,
            categories=categories,
            breakdown=breakdown,
            passed=overall >= self.pass_threshold,
            details=details,
        )

    def _evaluate_output_quality(self, output: str) -> float:
        """Evaluate the general quality of output.

        Args:
            output: The output to evaluate

        Returns:
            Quality score 0.0-1.0
        """
        if not output:
            return 0.0

        score = 0.5  # Base score

        # Check for empty/near-empty output
        if len(output.strip()) < 10:
            return 0.2

        # Check for placeholder patterns
        placeholders = ["todo", "fixme", "placeholder", "not implemented", "tbd"]
        has_placeholder = any(p in output.lower() for p in placeholders)
        if has_placeholder:
            score -= 0.2

        # Check for reasonable length
        if len(output) > 100:
            score += 0.1

        # Check for code-like content
        code_indicators = ["def ", "class ", "function", "{", "}", "=>", "return"]
        has_code = any(indicator in output for indicator in code_indicators)
        if has_code:
            score += 0.1

        return max(0.0, min(1.0, score))

    def score_results(self, results: Any) -> AggregateScores:
        """Calculate aggregate scores across benchmark results.

        Args:
            results: BenchmarkResults to aggregate

        Returns:
            AggregateScores with statistics
        """
        if not hasattr(results, "scores") or not results.scores:
            return AggregateScores()

        all_scores = [r.score for r in results.scores]
        total_tests = len(all_scores)
        total_passed = sum(1 for s in all_scores if s >= self.pass_threshold)

        # Calculate overall average
        overall_avg = sum(all_scores) / total_tests if total_tests > 0 else 0.0

        # Calculate category scores
        category_map: dict[str, list[float]] = {}
        difficulty_map: dict[str, list[float]] = {}

        for result in results.scores:
            cat = result.category.value if isinstance(result.category, TaskCategory) else str(result.category)
            if cat not in category_map:
                category_map[cat] = []
            category_map[cat].append(result.score)

            # Difficulty tracking
            # We don't have difficulty in results, so skip for now
            # difficulty_map would be populated from test case metadata

        category_scores: list[CategoryScore] = []
        for cat, scores in category_map.items():
            category_scores.append(CategoryScore(
                category=cat,
                average_score=sum(scores) / len(scores) if scores else 0.0,
                pass_rate=sum(1 for s in scores if s >= self.pass_threshold) / len(scores) if scores else 0.0,
                count=len(scores),
            ))

        # Calculate percentiles
        sorted_scores = sorted(all_scores)
        p25_idx = int(total_tests * 0.25)
        p50_idx = int(total_tests * 0.50)
        p75_idx = int(total_tests * 0.75)

        percentile_25 = sorted_scores[p25_idx] if sorted_scores else 0.0
        percentile_50 = sorted_scores[p50_idx] if sorted_scores else 0.0
        percentile_75 = sorted_scores[p75_idx] if sorted_scores else 0.0

        return AggregateScores(
            overall_average=overall_avg,
            category_scores=category_scores,
            difficulty_scores=difficulty_map,
            percentile_25=percentile_25,
            percentile_50=percentile_50,
            percentile_75=percentile_75,
            total_tests=total_tests,
            total_passed=total_passed,
        )

    def generate_report(
        self,
        results: Any,
        scores: AggregateScores | None = None,
        format: str = "markdown",
    ) -> str:
        """Generate a formatted report from benchmark results.

        Args:
            results: BenchmarkResults to report on
            scores: Optional pre-calculated AggregateScores
            format: Report format ("markdown" or "text")

        Returns:
            Formatted report string
        """
        if scores is None:
            scores = self.score_results(results)

        if format == "markdown":
            return self._generate_markdown_report(results, scores)
        else:
            return self._generate_text_report(results, scores)

    def _generate_markdown_report(self, results: Any, scores: AggregateScores) -> str:
        """Generate markdown format report."""
        lines = [
            "# Benchmark Results",
            "",
            f"**Date:** {results.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Total Tests:** {scores.total_tests}",
            f"**Passed:** {scores.total_passed} ({scores.total_passed / scores.total_tests * 100:.1f}%)" if scores.total_tests > 0 else "**Passed:** 0",
            f"**Average Score:** {scores.overall_average:.2%}",
            "",
            "## Category Breakdown",
            "",
            "| Category | Avg Score | Pass Rate | Count |",
            "|----------|-----------|-----------|-------|",
        ]

        for cs in scores.category_scores:
            lines.append(f"| {cs.category} | {cs.average_score:.2%} | {cs.pass_rate:.1%} | {cs.count} |")

        lines.extend([
            "",
            "## Score Distribution",
            "",
            f"- 25th percentile: {scores.percentile_25:.2%}",
            f"- 50th percentile (median): {scores.percentile_50:.2%}",
            f"- 75th percentile: {scores.percentile_75:.2%}",
            "",
        ])

        # Add individual test results
        if results.scores:
            lines.extend([
                "## Individual Test Results",
                "",
                "| Test ID | Name | Score | Status |",
                "|---------|------|-------|--------|",
            ])
            for r in results.scores[:20]:  # Limit to first 20
                status = "✅ PASS" if r.score >= self.pass_threshold else "❌ FAIL"
                name = r.test_name[:40] + "..." if len(r.test_name) > 40 else r.test_name
                lines.append(f"| {r.test_id} | {name} | {r.score:.2%} | {status} |")

            if len(results.scores) > 20:
                lines.append(f"\n*... and {len(results.scores) - 20} more tests*")

        return "\n".join(lines)

    def _generate_text_report(self, results: Any, scores: AggregateScores) -> str:
        """Generate plain text format report."""
        lines = [
            "=" * 60,
            "BENCHMARK RESULTS",
            "=" * 60,
            f"Date: {results.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Total Tests: {scores.total_tests}",
            f"Passed: {scores.total_passed} ({scores.total_passed / scores.total_tests * 100:.1f}%)" if scores.total_tests > 0 else "Passed: 0",
            f"Average Score: {scores.overall_average:.2%}",
            "",
            "CATEGORY BREAKDOWN:",
        ]

        for cs in scores.category_scores:
            lines.append(f"  {cs.category}: {cs.average_score:.2%} (pass rate: {cs.pass_rate:.1%})")

        lines.extend([
            "",
            "SCORE DISTRIBUTION:",
            f"  25th percentile: {scores.percentile_25:.2%}",
            f"  50th percentile: {scores.percentile_50:.2%}",
            f"  75th percentile: {scores.percentile_75:.2%}",
            "=" * 60,
        ])

        return "\n".join(lines)


def calculate_scores(results: Any) -> AggregateScores:
    """Convenience function to calculate scores from results.

    Args:
        results: BenchmarkResults to analyze

    Returns:
        AggregateScores with calculated statistics
    """
    scorer = Scorer()
    return scorer.score_results(results)