"""Benchmark runner for executing test cases against DeepAgent.

This module provides the BenchmarkRunner class that executes test cases
and collects results, supporting parallel execution.
"""
from __future__ import annotations

import asyncio
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from luminamind.benchmark.test_suite import TestCase, TestSuite, TaskCategory

# Optional DeepAgent import with graceful degradation
try:
    from luminamind.deep_agent import DeepAgent
except ImportError:
    DeepAgent = None


@dataclass
class BenchmarkResult:
    """Result of a single test case execution.

    Attributes:
        test_id: The test case identifier
        test_name: Human-readable test name
        category: Task category
        output: The agent's output
        score: Numeric score (0.0-1.0)
        execution_time: Time taken in seconds
        error: Error message if execution failed
        timestamp: When the test was run
    """

    test_id: str
    test_name: str
    category: TaskCategory
    output: str = ""
    score: float = 0.0
    execution_time: float = 0.0
    error: str | None = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "test_id": self.test_id,
            "test_name": self.test_name,
            "category": self.category.value if isinstance(self.category, TaskCategory) else str(self.category),
            "output": self.output,
            "score": self.score,
            "execution_time": self.execution_time,
            "error": self.error,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class BenchmarkResults:
    """Results from a full benchmark run.

    Attributes:
        timestamp: When the benchmark was run
        total_cases: Total number of test cases
        passed: Number of test cases that passed (score >= 0.7)
        failed: Number of test cases that failed (score < 0.7)
        scores: List of individual test results
        aggregate_scores: Aggregated scores by category
        total_execution_time: Total time for all tests
    """

    timestamp: datetime
    total_cases: int = 0
    passed: int = 0
    failed: int = 0
    scores: list[BenchmarkResult] = field(default_factory=list)
    aggregate_scores: dict[str, float] = field(default_factory=dict)
    total_execution_time: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "total_cases": self.total_cases,
            "passed": self.passed,
            "failed": self.failed,
            "scores": [s.to_dict() for s in self.scores],
            "aggregate_scores": self.aggregate_scores,
            "total_execution_time": self.total_execution_time,
            "pass_rate": self.passed / self.total_cases if self.total_cases > 0 else 0.0,
        }


class BenchmarkRunner:
    """Runner for executing benchmark test cases.

    Executes test cases against DeepAgent and collects results
    with support for parallel execution.

    Attributes:
        deep_agent: DeepAgent instance to run tests against
        max_parallel: Maximum parallel executions (default 4)
    """

    def __init__(self, deep_agent: Any | None = None, max_parallel: int = 4):
        """Initialize the benchmark runner.

        Args:
            deep_agent: DeepAgent instance (lazy-loaded if None)
            max_parallel: Maximum parallel test executions
        """
        self._deep_agent = deep_agent
        self.max_parallel = max_parallel

    @property
    def deep_agent(self) -> Any:
        """Get the DeepAgent instance, lazy-loading if needed."""
        if self._deep_agent is None:
            if DeepAgent is None:
                raise RuntimeError("DeepAgent not available. Install luminamind with all dependencies.")
            self._deep_agent = DeepAgent()
        return self._deep_agent

    def run(self, test_suite: TestSuite, output_dir: Path | str | None = None) -> BenchmarkResults:
        """Run all test cases in the suite.

        Args:
            test_suite: TestSuite containing cases to run
            output_dir: Optional directory to save results

        Returns:
            BenchmarkResults containing all test results
        """
        output_dir_path = Path(output_dir) if output_dir else None
        return self._run_tests(test_suite.cases, output_dir_path)

    def run_sample(self, n: int, **kwargs: Any) -> BenchmarkResults:
        """Run a random sample of test cases.

        Args:
            n: Number of cases to sample
            **kwargs: Optional filters (category, difficulty)

        Returns:
            BenchmarkResults for the sampled cases
        """
        suite = TestSuite()
        cases = suite.sample(n, **kwargs)
        return self._run_tests(cases, None)

    def run_category(self, category: TaskCategory, **kwargs: Any) -> BenchmarkResults:
        """Run all test cases in a specific category.

        Args:
            category: Category to run
            **kwargs: Optional additional filters

        Returns:
            BenchmarkResults for the category
        """
        suite = TestSuite()
        cases = suite.get_by_category(category)
        if "difficulty" in kwargs:
            cases = [c for c in cases if c.difficulty == kwargs["difficulty"]]
        return self._run_tests(cases, None)

    def _run_tests(self, cases: list[TestCase], output_dir: Path | None) -> BenchmarkResults:
        """Run a list of test cases.

        Args:
            cases: List of TestCase to run
            output_dir: Optional directory for output

        Returns:
            BenchmarkResults containing all results
        """
        start_time = time.time()
        results: list[BenchmarkResult] = []

        if self.max_parallel > 1 and len(cases) > 1:
            results = self._run_parallel(cases)
        else:
            results = self._run_sequential(cases)

        total_time = time.time() - start_time

        # Calculate aggregates
        aggregate_scores: dict[str, list[float]] = {}
        for result in results:
            cat = result.category.value if isinstance(result.category, TaskCategory) else str(result.category)
            if cat not in aggregate_scores:
                aggregate_scores[cat] = []
            aggregate_scores[cat].append(result.score)

        agg_dict: dict[str, float] = {}
        for cat, scores in aggregate_scores.items():
            agg_dict[cat] = sum(scores) / len(scores) if scores else 0.0

        benchmark_results = BenchmarkResults(
            timestamp=datetime.utcnow(),
            total_cases=len(results),
            passed=sum(1 for r in results if r.score >= 0.7),
            failed=sum(1 for r in results if r.score < 0.7),
            scores=results,
            aggregate_scores=agg_dict,
            total_execution_time=total_time,
        )

        if output_dir:
            self._save_results(benchmark_results, output_dir)

        return benchmark_results

    def _run_sequential(self, cases: list[TestCase]) -> list[BenchmarkResult]:
        """Run test cases sequentially.

        Args:
            cases: List of TestCase to run

        Returns:
            List of BenchmarkResult
        """
        results = []
        for case in cases:
            result = self._execute_test_case(case)
            results.append(result)
        return results

    def _run_parallel(self, cases: list[TestCase]) -> list[BenchmarkResult]:
        """Run test cases in parallel.

        Args:
            cases: List of TestCase to run

        Returns:
            List of BenchmarkResult in same order as input
        """
        results: list[BenchmarkResult | None] = [None] * len(cases)
        with ThreadPoolExecutor(max_workers=self.max_parallel) as executor:
            future_to_index = {
                executor.submit(self._execute_test_case, case): i
                for i, case in enumerate(cases)
            }
            for future in as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    results[index] = future.result()
                except Exception as e:
                    case = cases[index]
                    results[index] = BenchmarkResult(
                        test_id=case.id,
                        test_name=case.name,
                        category=case.category,
                        error=str(e),
                        execution_time=0.0,
                    )
        return [r for r in results if r is not None]

    def _execute_test_case(self, case: TestCase) -> BenchmarkResult:
        """Execute a single test case.

        Args:
            case: TestCase to execute

        Returns:
            BenchmarkResult for the test
        """
        start_time = time.time()
        output = ""
        error = None

        try:
            # Run the agent on the task
            result = self.deep_agent.run(case.task)
            output = str(result) if result else ""
        except Exception as e:
            error = str(e)
            output = ""

        execution_time = time.time() - start_time

        # Score the output
        score = case.score(output) if not error else 0.0

        return BenchmarkResult(
            test_id=case.id,
            test_name=case.name,
            category=case.category,
            output=output,
            score=score,
            execution_time=execution_time,
            error=error,
        )

    def _save_results(self, results: BenchmarkResults, output_dir: Path) -> None:
        """Save results to output directory.

        Args:
            results: BenchmarkResults to save
            output_dir: Directory to save to
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp_str = results.timestamp.strftime("%Y%m%d_%H%M%S")
        result_file = output_dir / f"benchmark_results_{timestamp_str}.json"
        with open(result_file, "w") as f:
            json.dump(results.to_dict(), f, indent=2)


def run_benchmark(
    test_suite: TestSuite | None = None,
    output_dir: Path | str | None = None,
    deep_agent: Any | None = None,
    max_parallel: int = 4,
) -> BenchmarkResults:
    """Convenience function to run a benchmark.

    Args:
        test_suite: TestSuite to run (creates default if None)
        output_dir: Optional output directory
        deep_agent: Optional DeepAgent instance
        max_parallel: Maximum parallel executions

    Returns:
        BenchmarkResults from the run
    """
    if test_suite is None:
        test_suite = TestSuite()
    runner = BenchmarkRunner(deep_agent=deep_agent, max_parallel=max_parallel)
    return runner.run(test_suite, output_dir)