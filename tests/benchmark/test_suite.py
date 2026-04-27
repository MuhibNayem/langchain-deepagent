"""Tests for benchmark module.

Tests cover:
- TestSuite: add_case, get_by_category, get_by_difficulty, sample
- Scorer: score calculation, report generation
- RegressionDetector: regression detection, baseline management
- Integration: run 5 cases, verify results format
"""
import json
import tempfile
from pathlib import Path

import pytest

from luminamind.benchmark import TestSuite, BenchmarkRunner, Scorer, RegressionDetector
from luminamind.benchmark.test_suite import TaskCategory, TestCase
from luminamind.benchmark.runner import BenchmarkResult, BenchmarkResults
from luminamind.benchmark.scoring import Score, AggregateScores
from luminamind.benchmark.regression import RegressionReport, RegressionEntry


class TestSuiteModule:
    """Test cases for TestSuite class from test_suite module."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.suite = TestSuite()

    def test_has_100_plus_cases(self) -> None:
        """Test that default suite has 100+ test cases."""
        assert len(self.suite.cases) >= 100, f"Expected 100+ cases, got {len(self.suite.cases)}"

    def test_categories_covered(self) -> None:
        """Test that all 8 categories are present."""
        categories = set(c.category for c in self.suite.cases)
        expected = {
            TaskCategory.CODE_GEN,
            TaskCategory.DEBUGGING,
            TaskCategory.REFACTORING,
            TaskCategory.DOCUMENTATION,
            TaskCategory.UI_DESIGN,
            TaskCategory.API_DESIGN,
            TaskCategory.REVIEW,
            TaskCategory.OPTIMIZATION,
        }
        assert categories == expected, f"Missing categories: {expected - categories}"

    def test_add_case(self) -> None:
        """Test adding a new test case."""
        initial_count = len(self.suite.cases)
        new_case = TestCase(
            id="test_001",
            name="Test Case",
            category=TaskCategory.CODE_GEN,
            task="Write a test",
            difficulty="easy",
        )
        self.suite.add_case(new_case)
        assert len(self.suite.cases) == initial_count + 1

    def test_get_by_category(self) -> None:
        """Test filtering by category."""
        code_gen_cases = self.suite.get_by_category(TaskCategory.CODE_GEN)
        assert len(code_gen_cases) > 0
        assert all(c.category == TaskCategory.CODE_GEN for c in code_gen_cases)

    def test_get_by_difficulty(self) -> None:
        """Test filtering by difficulty."""
        easy_cases = self.suite.get_by_difficulty("easy")
        assert len(easy_cases) > 0
        assert all(c.difficulty == "easy" for c in easy_cases)

    def test_sample(self) -> None:
        """Test random sampling."""
        sample = self.suite.sample(10)
        assert len(sample) == 10
        assert all(isinstance(c, TestCase) for c in sample)

        # Sample should be subset of cases
        sample_ids = {c.id for c in sample}
        case_ids = {c.id for c in self.suite.cases}
        assert sample_ids.issubset(case_ids)

    def test_sample_with_category_filter(self) -> None:
        """Test sampling with category filter."""
        sample = self.suite.sample(5, category=TaskCategory.DEBUGGING)
        assert len(sample) <= 5
        assert all(c.category == TaskCategory.DEBUGGING for c in sample)

    def test_sample_larger_than_suite(self) -> None:
        """Test sampling more cases than available."""
        sample = self.suite.sample(len(self.suite.cases) + 10)
        assert len(sample) == len(self.suite.cases)

    def test_test_case_score(self) -> None:
        """Test TestCase scoring."""
        case = TestCase(
            id="score_test",
            name="Score Test",
            category=TaskCategory.CODE_GEN,
            task="Write a function",
            scoring_criteria=lambda o: 1.0 if "function" in o else 0.0,
            difficulty="easy",
        )

        assert case.score("function test()") == 1.0
        assert case.score("no match") == 0.0


class TestScorer:
    """Test cases for Scorer class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.scorer = Scorer()

    def test_score_test_case(self) -> None:
        """Test scoring a single test case."""
        case = TestCase(
            id="scorer_test",
            name="Scorer Test",
            category=TaskCategory.CODE_GEN,
            task="Write a function",
            scoring_criteria=lambda o: 0.5 if "test" in o else 0.0,
            difficulty="easy",
        )

        score = self.scorer.score_test_case(case, "test function")
        assert isinstance(score, Score)
        assert 0.0 <= score.overall <= 1.0
        assert score.passed == (score.overall >= 0.7)

    def test_score_results_empty(self) -> None:
        """Test scoring empty results."""
        results = BenchmarkResults(
            timestamp=None,
            total_cases=0,
            passed=0,
            failed=0,
            scores=[],
        )
        # BenchmarkResults.timestamp might be None, handle this
        from datetime import datetime
        results.timestamp = datetime.utcnow()

        scores = self.scorer.score_results(results)
        assert isinstance(scores, AggregateScores)
        assert scores.total_tests == 0

    def test_score_results_with_data(self) -> None:
        """Test scoring results with actual data."""
        from datetime import datetime

        results = BenchmarkResults(
            timestamp=datetime.utcnow(),
            total_cases=3,
            passed=2,
            failed=1,
            scores=[
                BenchmarkResult(
                    test_id="test1",
                    test_name="Test 1",
                    category=TaskCategory.CODE_GEN,
                    output="function test() {}",
                    score=0.8,
                    execution_time=1.0,
                ),
                BenchmarkResult(
                    test_id="test2",
                    test_name="Test 2",
                    category=TaskCategory.DEBUGGING,
                    output="use let instead of var",
                    score=0.9,
                    execution_time=2.0,
                ),
                BenchmarkResult(
                    test_id="test3",
                    test_name="Test 3",
                    category=TaskCategory.UI_DESIGN,
                    output="form validation",
                    score=0.5,
                    execution_time=3.0,
                ),
            ],
        )

        scores = self.scorer.score_results(results)
        assert isinstance(scores, AggregateScores)
        assert scores.total_tests == 3
        assert scores.total_passed == 2
        assert scores.overall_average > 0

    def test_generate_report_markdown(self) -> None:
        """Test markdown report generation."""
        from datetime import datetime

        results = BenchmarkResults(
            timestamp=datetime.utcnow(),
            total_cases=2,
            passed=1,
            failed=1,
            scores=[
                BenchmarkResult(
                    test_id="test1",
                    test_name="Test One",
                    category=TaskCategory.CODE_GEN,
                    output="code",
                    score=0.8,
                    execution_time=1.0,
                ),
                BenchmarkResult(
                    test_id="test2",
                    test_name="Test Two",
                    category=TaskCategory.DEBUGGING,
                    output="fix",
                    score=0.5,
                    execution_time=2.0,
                ),
            ],
        )

        scores = self.scorer.score_results(results)
        report = self.scorer.generate_report(results, scores, format="markdown")

        assert "# Benchmark Results" in report
        assert "Test One" in report or "test1" in report

    def test_generate_report_text(self) -> None:
        """Test text report generation."""
        from datetime import datetime

        results = BenchmarkResults(
            timestamp=datetime.utcnow(),
            total_cases=1,
            passed=0,
            failed=1,
            scores=[
                BenchmarkResult(
                    test_id="test1",
                    test_name="Test One",
                    category=TaskCategory.CODE_GEN,
                    output="code",
                    score=0.5,
                    execution_time=1.0,
                ),
            ],
        )

        scores = self.scorer.score_results(results)
        report = self.scorer.generate_report(results, scores, format="text")

        assert "BENCHMARK RESULTS" in report
        assert "Total Tests: 1" in report
        assert "Average Score:" in report


class TestRegressionDetector:
    """Test cases for RegressionDetector class."""

    def setup_method(self) -> None:
        """Set up test fixtures with temporary baseline."""
        self.temp_dir = tempfile.mkdtemp()
        self.baseline_path = Path(self.temp_dir) / "test_baseline.json"

    def teardown_method(self) -> None:
        """Clean up temp files."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_no_baseline(self) -> None:
        """Test regression detection with no baseline."""
        detector = RegressionDetector(baseline_path=None)  # Will use default

        # May or may not have baseline depending on previous runs
        # Just verify it doesn't crash
        assert detector is not None

    def test_check_regression_no_baseline(self) -> None:
        """Test regression check when no baseline exists."""
        # Use a path that doesn't exist
        detector = RegressionDetector(baseline_path="/tmp/nonexistent_baseline.json")

        from luminamind.benchmark.scoring import AggregateScores

        current = AggregateScores(
            overall_average=0.75,
            total_tests=20,
            total_passed=15,
        )

        report = detector.check_regression(current)
        assert isinstance(report, RegressionReport)
        # With no baseline, should report no regression
        assert report.has_regression is False

    def test_update_baseline(self) -> None:
        """Test updating baseline."""
        detector = RegressionDetector(baseline_path=self.baseline_path)

        from luminamind.benchmark.scoring import AggregateScores

        baseline = AggregateScores(
            overall_average=0.80,
            total_tests=20,
            total_passed=16,
        )

        detector.update_baseline(baseline)
        assert self.baseline_path.exists()

        # Verify content
        with open(self.baseline_path) as f:
            data = json.load(f)
        assert data["overall_average"] == 0.80

    def test_check_regression_with_baseline(self) -> None:
        """Test regression detection with existing baseline."""
        # Create a baseline first
        baseline_data = {
            "overall_average": 0.80,
            "total_tests": 20,
            "total_passed": 16,
            "category_scores": [
                {"category": "code_generation", "average_score": 0.80, "pass_rate": 0.8, "count": 10},
                {"category": "debugging", "average_score": 0.80, "pass_rate": 0.8, "count": 10},
            ],
            "difficulty_scores": {},
            "percentiles": {"p25": 0.70, "p50": 0.80, "p75": 0.90},
        }

        with open(self.baseline_path, "w") as f:
            json.dump(baseline_data, f)

        detector = RegressionDetector(baseline_path=self.baseline_path)

        from luminamind.benchmark.scoring import AggregateScores

        # Current scores with a 10% drop (HIGH regression)
        current = AggregateScores(
            overall_average=0.72,  # 10% drop from 0.80
            total_tests=20,
            total_passed=14,
            category_scores=[
                AggregateScores.__dataclass_fields__.keys(),  # This won't work, need proper structure
            ],
        )

        # Simpler test: just check detection works
        from luminamind.benchmark.scoring import CategoryScore
        current = AggregateScores(
            overall_average=0.72,
            total_tests=20,
            total_passed=14,
            category_scores=[
                CategoryScore(category="code_generation", average_score=0.72, pass_rate=0.7, count=10),
                CategoryScore(category="debugging", average_score=0.72, pass_rate=0.7, count=10),
            ],
        )

        report = detector.check_regression(current)
        assert isinstance(report, RegressionReport)
        # 10% drop should be HIGH severity
        assert report.has_regression is True
        assert len(report.regressions) > 0

    def test_severity_thresholds(self) -> None:
        """Test severity threshold classification."""
        detector = RegressionDetector()

        # These are internal but we can verify through behavior
        assert detector.SEVERITY_THRESHOLDS["CRITICAL"] == 0.20
        assert detector.SEVERITY_THRESHOLDS["HIGH"] == 0.10
        assert detector.SEVERITY_THRESHOLDS["MEDIUM"] == 0.05
        assert detector.SEVERITY_THRESHOLDS["LOW"] == 0.0

    def test_get_trend_empty(self) -> None:
        """Test trend calculation with empty history."""
        detector = RegressionDetector()

        trends = detector.get_trend([])
        assert trends == []

    def test_get_trend_single_point(self) -> None:
        """Test trend with single data point."""
        from luminamind.benchmark.scoring import AggregateScores, CategoryScore

        detector = RegressionDetector()

        scores = AggregateScores(
            overall_average=0.80,
            total_tests=10,
            total_passed=8,
            category_scores=[
                CategoryScore(category="code_generation", average_score=0.80, pass_rate=0.8, count=10),
            ],
        )

        trends = detector.get_trend([scores])
        assert trends == []  # Need at least 2 points


class TestBenchmarkRunner:
    """Test cases for BenchmarkRunner class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.runner = BenchmarkRunner(max_parallel=1)  # Use 1 to avoid parallel issues in tests

    def test_runner_initialization(self) -> None:
        """Test runner can be initialized."""
        assert self.runner is not None
        assert self.runner.max_parallel == 1

    def test_runner_with_deep_agent_none(self) -> None:
        """Test runner handles None deep_agent gracefully."""
        runner = BenchmarkRunner(deep_agent=None)
        # DeepAgent import may fail, verify no crash
        assert runner is not None


class TestIntegration:
    """Integration tests for benchmark module."""

    def test_run_sample_cases(self) -> None:
        """Test running 5 sample cases and verifying results format."""
        suite = TestSuite()
        runner = BenchmarkRunner(max_parallel=1)

        # Run a small sample
        sample_size = 5
        results = runner.run_sample(sample_size)

        # Verify results structure
        assert results.total_cases == sample_size
        assert len(results.scores) == sample_size

        # Verify each result has required fields
        for result in results.scores:
            assert result.test_id is not None
            assert result.test_name is not None
            assert result.category is not None
            assert 0.0 <= result.score <= 1.0
            assert result.execution_time >= 0

    def test_results_to_dict(self) -> None:
        """Test BenchmarkResults serialization."""
        from datetime import datetime

        results = BenchmarkResults(
            timestamp=datetime.utcnow(),
            total_cases=2,
            passed=1,
            failed=1,
            scores=[
                BenchmarkResult(
                    test_id="test1",
                    test_name="Test One",
                    category=TaskCategory.CODE_GEN,
                    output="code output",
                    score=0.8,
                    execution_time=1.5,
                ),
            ],
        )

        data = results.to_dict()

        assert data["total_cases"] == 2
        assert data["passed"] == 1
        assert data["failed"] == 1
        assert len(data["scores"]) == 1
        assert data["scores"][0]["test_id"] == "test1"
        assert data["scores"][0]["score"] == 0.8

    def test_suite_categories_all_present(self) -> None:
        """Test all 8 categories are represented in suite."""
        suite = TestSuite()

        category_counts = {}
        for case in suite.cases:
            cat = case.category.value if isinstance(case.category, TaskCategory) else str(case.category)
            category_counts[cat] = category_counts.get(cat, 0) + 1

        # Each category should have multiple cases
        for cat in ["code_generation", "debugging", "refactoring", "documentation",
                    "ui_design", "api_design", "review", "optimization"]:
            assert cat in category_counts, f"Missing category: {cat}"
            assert category_counts[cat] >= 5, f"Category {cat} has too few cases: {category_counts[cat]}"