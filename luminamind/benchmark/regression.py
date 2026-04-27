"""Regression detection for benchmark results.

This module provides the RegressionDetector class that compares
current benchmark scores against baseline to identify regressions.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from luminamind.benchmark.scoring import AggregateScores


@dataclass
class RegressionEntry:
    """A single regression or improvement entry.

    Attributes:
        category: The category that regressed
        baseline: Baseline score
        current: Current score
        delta: Change in score (negative = regression)
        severity: Severity level (CRITICAL, HIGH, MEDIUM, LOW)
    """

    category: str
    baseline: float
    current: float
    delta: float
    severity: str


@dataclass
class RegressionReport:
    """Report identifying score regressions.

    Attributes:
        has_regression: Whether any regression was detected
        regressions: List of regression entries
        improvements: List of improvement entries
        summary: Human-readable summary
        timestamp: When the report was generated
    """

    has_regression: bool
    regressions: list[RegressionEntry] = field(default_factory=list)
    improvements: list[RegressionEntry] = field(default_factory=list)
    summary: str = ""
    timestamp: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "has_regression": self.has_regression,
            "regressions": [
                {
                    "category": r.category,
                    "baseline": r.baseline,
                    "current": r.current,
                    "delta": r.delta,
                    "severity": r.severity,
                }
                for r in self.regressions
            ],
            "improvements": [
                {
                    "category": r.category,
                    "baseline": r.baseline,
                    "current": r.current,
                    "delta": r.delta,
                }
                for r in self.improvements
            ],
            "summary": self.summary,
            "timestamp": self.timestamp,
        }


@dataclass
class TrendPoint:
    """A single point in a trend line.

    Attributes:
        timestamp: When the measurement was taken
        score: The measured score
        label: Optional label for the point
    """

    timestamp: str
    score: float
    label: str = ""


@dataclass
class TrendLine:
    """Trend line over multiple benchmark runs.

    Attributes:
        category: The category this trend is for
        points: List of trend points
        direction: Trend direction ("improving", "declining", "stable")
        slope: Calculated slope of the trend
    """

    category: str
    points: list[TrendPoint] = field(default_factory=list)
    direction: str = "stable"
    slope: float = 0.0


class RegressionDetector:
    """Detector for benchmark score regressions.

    Compares current scores against baseline and identifies
    statistically significant drops with severity ratings.

    Severity thresholds:
    - CRITICAL: > 20% drop
    - HIGH: > 10% drop
    - MEDIUM: > 5% drop
    - LOW: any drop
    """

    SEVERITY_THRESHOLDS = {
        "CRITICAL": 0.20,  # 20% drop
        "HIGH": 0.10,      # 10% drop
        "MEDIUM": 0.05,    # 5% drop
        "LOW": 0.0,        # any drop
    }

    def __init__(self, baseline_path: Path | str | None = None):
        """Initialize the regression detector.

        Args:
            baseline_path: Path to baseline JSON file. If None, uses default.
        """
        if baseline_path is None:
            # Default to ~/.luminamind/benchmark_baseline.json
            home = Path.home()
            default_dir = home / ".luminamind"
            default_dir.mkdir(exist_ok=True)
            baseline_path = default_dir / "benchmark_baseline.json"

        self.baseline_path = Path(baseline_path)
        self._baseline: AggregateScores | None = None
        self._load_baseline()

    def _load_baseline(self) -> None:
        """Load baseline scores from file."""
        if self.baseline_path.exists():
            try:
                with open(self.baseline_path) as f:
                    data = json.load(f)
                self._baseline = self._parse_baseline(data)
            except (json.JSONDecodeError, KeyError):
                self._baseline = None

    def _parse_baseline(self, data: dict[str, Any]) -> AggregateScores:
        """Parse baseline data into AggregateScores.

        Args:
            data: Dictionary from JSON

        Returns:
            AggregateScores instance
        """
        from luminamind.benchmark.scoring import CategoryScore

        category_scores = []
        for cs_data in data.get("category_scores", []):
            category_scores.append(CategoryScore(
                category=cs_data.get("category", ""),
                average_score=cs_data.get("average_score", 0.0),
                pass_rate=cs_data.get("pass_rate", 0.0),
                count=cs_data.get("count", 0),
            ))

        return AggregateScores(
            overall_average=data.get("overall_average", 0.0),
            category_scores=category_scores,
            difficulty_scores=data.get("difficulty_scores", {}),
            percentile_25=data.get("percentiles", {}).get("p25", 0.0),
            percentile_50=data.get("percentiles", {}).get("p50", 0.0),
            percentile_75=data.get("percentiles", {}).get("p75", 0.0),
            total_tests=data.get("total_tests", 0),
            total_passed=data.get("total_passed", 0),
        )

    def check_regression(self, current: AggregateScores) -> RegressionReport:
        """Check for regressions against baseline.

        Args:
            current: Current benchmark scores

        Returns:
            RegressionReport identifying any regressions
        """
        from datetime import datetime

        regressions: list[RegressionEntry] = []
        improvements: list[RegressionEntry] = []

        if self._baseline is None:
            # No baseline to compare against
            return RegressionReport(
                has_regression=False,
                summary="No baseline available for comparison",
                timestamp=datetime.utcnow().isoformat(),
            )

        # Check overall regression
        overall_delta = current.overall_average - self._baseline.overall_average
        overall_pct = overall_delta / self._baseline.overall_average if self._baseline.overall_average > 0 else 0

        if overall_pct < -self.SEVERITY_THRESHOLDS["LOW"]:
            regressions.append(RegressionEntry(
                category="OVERALL",
                baseline=self._baseline.overall_average,
                current=current.overall_average,
                delta=overall_delta,
                severity=self._get_severity(overall_pct),
            ))
        elif overall_pct > self.SEVERITY_THRESHOLDS["LOW"]:
            improvements.append(RegressionEntry(
                category="OVERALL",
                baseline=self._baseline.overall_average,
                current=current.overall_average,
                delta=overall_delta,
                severity="IMPROVEMENT",
            ))

        # Check per-category regressions
        baseline_cat_map = {cs.category: cs for cs in self._baseline.category_scores}
        current_cat_map = {cs.category: cs for cs in current.category_scores}

        all_categories = set(baseline_cat_map.keys()) | set(current_cat_map.keys())

        for cat in all_categories:
            baseline_cs = baseline_cat_map.get(cat)
            current_cs = current_cat_map.get(cat)

            if baseline_cs is None or current_cs is None:
                continue

            delta = current_cs.average_score - baseline_cs.average_score
            pct = delta / baseline_cs.average_score if baseline_cs.average_score > 0 else 0

            if pct < -self.SEVERITY_THRESHOLDS["LOW"]:
                regressions.append(RegressionEntry(
                    category=cat,
                    baseline=baseline_cs.average_score,
                    current=current_cs.average_score,
                    delta=delta,
                    severity=self._get_severity(pct),
                ))
            elif pct > self.SEVERITY_THRESHOLDS["LOW"]:
                improvements.append(RegressionEntry(
                    category=cat,
                    baseline=baseline_cs.average_score,
                    current=current_cs.average_score,
                    delta=delta,
                    severity="IMPROVEMENT",
                ))

        # Generate summary
        summary_parts = []
        if regressions:
            critical = [r for r in regressions if r.severity == "CRITICAL"]
            high = [r for r in regressions if r.severity == "HIGH"]
            medium = [r for r in regressions if r.severity == "MEDIUM"]
            low = [r for r in regressions if r.severity == "LOW"]

            if critical:
                summary_parts.append(f"{len(critical)} CRITICAL regression(s)")
            if high:
                summary_parts.append(f"{len(high)} HIGH regression(s)")
            if medium:
                summary_parts.append(f"{len(medium)} MEDIUM regression(s)")
            if low:
                summary_parts.append(f"{len(low)} LOW regression(s)")

        if improvements:
            summary_parts.append(f"{len(improvements)} improvement(s)")

        summary = " | ".join(summary_parts) if summary_parts else "No significant changes"

        return RegressionReport(
            has_regression=len(regressions) > 0,
            regressions=regressions,
            improvements=improvements,
            summary=summary,
            timestamp=datetime.utcnow().isoformat(),
        )

    def _get_severity(self, pct_change: float) -> str:
        """Determine severity based on percentage change.

        Args:
            pct_change: Percentage change (negative = regression)

        Returns:
            Severity string
        """
        abs_pct = abs(pct_change)
        if abs_pct > self.SEVERITY_THRESHOLDS["CRITICAL"]:
            return "CRITICAL"
        elif abs_pct > self.SEVERITY_THRESHOLDS["HIGH"]:
            return "HIGH"
        elif abs_pct > self.SEVERITY_THRESHOLDS["MEDIUM"]:
            return "MEDIUM"
        else:
            return "LOW"

    def update_baseline(self, current: AggregateScores) -> None:
        """Save current scores as the new baseline.

        Args:
            current: Current scores to save as baseline
        """
        data = current.to_dict()
        with open(self.baseline_path, "w") as f:
            json.dump(data, f, indent=2)
        self._baseline = current

    def get_trend(self, historical: list[AggregateScores]) -> list[TrendLine]:
        """Calculate trend over multiple benchmark runs.

        Args:
            historical: List of AggregateScores in chronological order

        Returns:
            List of TrendLine, one per category
        """
        if len(historical) < 2:
            return []

        # Build trends per category
        category_map: dict[str, list[tuple[str, float]]] = {}

        for i, scores in enumerate(historical):
            ts = f"run_{i + 1}"
            for cs in scores.category_scores:
                if cs.category not in category_map:
                    category_map[cs.category] = []
                category_map[cs.category].append((ts, cs.average_score))

        trend_lines: list[TrendLine] = []

        for cat, points_data in category_map.items():
            if len(points_data) < 2:
                continue

            points = [TrendPoint(timestamp=ts, score=score) for ts, score in points_data]

            # Calculate simple slope
            n = len(points)
            if n >= 2:
                x_vals = list(range(n))
                y_vals = [p.score for p in points]
                x_mean = sum(x_vals) / n
                y_mean = sum(y_vals) / n
                numerator = sum((x_vals[i] - x_mean) * (y_vals[i] - y_mean) for i in range(n))
                denominator = sum((x_vals[i] - x_mean) ** 2 for i in range(n))
                slope = numerator / denominator if denominator != 0 else 0
            else:
                slope = 0

            # Determine direction
            if slope > 0.01:
                direction = "improving"
            elif slope < -0.01:
                direction = "declining"
            else:
                direction = "stable"

            trend_lines.append(TrendLine(
                category=cat,
                points=points,
                direction=direction,
                slope=slope,
            ))

        return trend_lines