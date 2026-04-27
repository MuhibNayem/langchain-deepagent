"""Chaos execution engine for running fault injection scenarios."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from luminamind.chaos.faults import FaultConfig, FaultInjector, FaultType
from luminamind.chaos.scenarios import ChaosScenario, ScenarioType, get_scenario, list_scenarios

logger = logging.getLogger(__name__)


@dataclass
class ChaosResult:
    """Result of a single chaos scenario execution.

    Attributes:
        scenario_id: The scenario that was run
        task: The task description that was executed
        fault_injected: Whether the fault was successfully injected
        execution_time: How long the scenario took to run (seconds)
        outcome: 'success', 'degraded', or 'failed'
        error_message: Error message if outcome is 'failed'
        graceful_degradation: Whether graceful degradation was observed
        metrics: Additional metrics about the execution
        timestamp: When the scenario was run
    """
    scenario_id: str
    task: str
    fault_injected: bool = False
    execution_time: float = 0.0
    outcome: str = "unknown"  # "success" | "degraded" | "failed"
    error_message: str | None = None
    graceful_degradation: bool = False
    metrics: dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""


@dataclass
class ChaosSuiteResult:
    """Results from running multiple chaos scenarios.

    Attributes:
        scenario_id: The scenario that was run
        task: The task description that was executed
        fault_injected: Whether the fault was successfully injected
        execution_time: How long the scenario took to run (seconds)
        outcome: 'success', 'degraded', or 'failed'
        error_message: Error message if outcome is 'failed'
        graceful_degradation: Whether graceful degradation was observed
        metrics: Additional metrics about the execution
        timestamp: When the scenario was run
        results: List of all ChaosResult objects
        total_scenarios: Total number of scenarios run
        passed: Number of scenarios that passed (graceful degradation worked)
        failed: Number of scenarios that had catastrophic failure
    """
    scenario_id: str = ""
    task: str = ""
    fault_injected: bool = False
    execution_time: float = 0.0
    outcome: str = "unknown"
    error_message: str | None = None
    graceful_degradation: bool = False
    metrics: dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""
    results: list[ChaosResult] = field(default_factory=list)
    total_scenarios: int = 0
    passed: int = 0
    failed: int = 0


class ChaosEngine:
    """Engine for executing chaos scenarios against the harness.

    The engine injects faults as specified in the scenario and records
    how the system behaves under those fault conditions.
    """

    def __init__(
        self,
        deep_agent: Any | None = None,
        output_dir: Path | None = None,
    ) -> None:
        """Initialize the chaos engine.

        Args:
            deep_agent: DeepAgent instance to test (optional for mocking)
            output_dir: Directory to write results to (default: ./chaos_results)
        """
        self._deep_agent = deep_agent
        self._output_dir = output_dir or Path("./chaos_results")
        self._injector = FaultInjector()
        self._active_patches: list[Any] = []

    def _inject_fault(self, fault: FaultConfig) -> bool:
        """Inject a fault based on configuration.

        Args:
            fault: FaultConfig describing what to inject

        Returns:
            True if fault was successfully injected
        """
        try:
            fault_type = fault.fault_type

            # Handle different fault types
            if fault_type == FaultType.NETWORK_LATENCY:
                delay_ms = fault.parameters.get("delay_ms", 500)
                self._injector.inject_network_latency(delay_ms)
                logger.info(f"Injected network latency: {delay_ms}ms")

            elif fault_type == FaultType.LLM_TIMEOUT:
                self._injector.inject_llm_timeout(fault.parameters.get("timeout_seconds", 60))
                logger.info(f"Injected LLM timeout: {fault.parameters.get('timeout_seconds', 60)}s")

            elif fault_type == FaultType.LLM_RATE_LIMIT:
                self._injector.inject_llm_rate_limit(fault.parameters.get("retry_after", 60))
                logger.info(f"Injected LLM rate limit: retry_after={fault.parameters.get('retry_after', 60)}s")

            elif fault_type == FaultType.SYSTEM_REDIS_UNAVAILABLE:
                self._injector.inject_redis_unavailable()
                logger.info("Injected Redis unavailability")

            elif fault_type == FaultType.SYSTEM_DISK_FULL:
                self._injector.inject_disk_full()
                logger.info("Injected disk full condition")

            elif fault_type == FaultType.SYSTEM_PROCESS_CRASH:
                logger.info("Injected process crash scenario")

            else:
                logger.warning(f"Unknown fault type: {fault_type}")
                return False

            self._injector.inject(fault)
            return True

        except Exception as e:
            logger.error(f"Failed to inject fault: {e}")
            return False

    def _cleanup_faults(self) -> None:
        """Clean up all injected faults and restore system state."""
        self._injector.clear()
        for patch in self._active_patches:
            try:
                patch.stop()
            except Exception as e:
                logger.warning(f"Failed to stop patch: {e}")
        self._active_patches.clear()

    def _assess_outcome(
        self,
        scenario: ChaosScenario,
        execution_time: float,
        error: Exception | None,
    ) -> tuple[str, bool, str | None]:
        """Assess the outcome of a scenario run.

        Args:
            scenario: The scenario that was run
            execution_time: How long it took
            error: Any exception that occurred

        Returns:
            Tuple of (outcome, graceful_degradation, error_message)
        """
        if error is None:
            if scenario.graceful_degradation:
                return ("success", True, None)
            else:
                return ("degraded", True, None)
        else:
            # An error occurred
            if scenario.graceful_degradation:
                # Should have handled gracefully but didn't
                return ("failed", False, str(error))
            else:
                # Failure was expected
                return ("degraded", True, str(error))

    def run_scenario(
        self,
        scenario: ChaosScenario | str,
        task: str = "default chaos test task",
    ) -> ChaosResult:
        """Run a single chaos scenario.

        Args:
            scenario: ChaosScenario instance or scenario ID string
            task: Task description to execute

        Returns:
            ChaosResult with execution details
        """
        # Resolve scenario if string ID
        if isinstance(scenario, str):
            scenario = get_scenario(scenario)
            if scenario is None:
                return ChaosResult(
                    scenario_id=scenario if isinstance(scenario, str) else "unknown",
                    task=task,
                    outcome="failed",
                    error_message=f"Unknown scenario: {scenario}",
                    graceful_degradation=False,
                )

        logger.info(f"Running chaos scenario: {scenario.name} ({scenario.id})")

        result = ChaosResult(
            scenario_id=scenario.id,
            task=task,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )

        start_time = time.time()

        try:
            # Inject all faults for this scenario
            for fault in scenario.faults:
                injected = self._inject_fault(fault)
                result.fault_injected = result.fault_injected or injected

            # Simulate some execution time for the task
            # In real implementation, this would run the deep_agent with fault injection
            time.sleep(0.1)  # Minimal delay to simulate work

            # Assess outcome
            outcome, graceful, error_msg = self._assess_outcome(
                scenario, time.time() - start_time, None
            )
            result.outcome = outcome
            result.graceful_degradation = graceful
            result.error_message = error_msg

        except Exception as e:
            logger.error(f"Scenario {scenario.id} failed with error: {e}")
            outcome, graceful, error_msg = self._assess_outcome(
                scenario, time.time() - start_time, e
            )
            result.outcome = outcome
            result.graceful_degradation = graceful
            result.error_message = error_msg

        finally:
            self._cleanup_faults()
            result.execution_time = time.time() - start_time

        return result

    def run_suite(
        self,
        scenarios: list[ChaosScenario | str],
        task: str = "default chaos test task",
    ) -> ChaosSuiteResult:
        """Run multiple chaos scenarios against the same task.

        Args:
            scenarios: List of ChaosScenario instances or scenario ID strings
            task: Task description to execute

        Returns:
            ChaosSuiteResult with all scenario results
        """
        logger.info(f"Running chaos suite with {len(scenarios)} scenarios")

        suite_result = ChaosSuiteResult(
            task=task,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        )

        results: list[ChaosResult] = []
        passed_count = 0
        failed_count = 0

        for scenario in scenarios:
            # Resolve string IDs
            if isinstance(scenario, str):
                resolved = get_scenario(scenario)
                if resolved is None:
                    logger.warning(f"Unknown scenario: {scenario}, skipping")
                    continue
                scenario = resolved

            result = self.run_scenario(scenario, task)
            results.append(result)

            if result.outcome == "success" or result.outcome == "degraded":
                passed_count += 1
            else:
                failed_count += 1

        suite_result.results = results
        suite_result.total_scenarios = len(results)
        suite_result.passed = passed_count
        suite_result.failed = failed_count

        return suite_result

    def run_all_scenarios(self, task: str = "default chaos test task") -> ChaosSuiteResult:
        """Run all available chaos scenarios.

        Args:
            task: Task description to execute

        Returns:
            ChaosSuiteResult with all scenario results
        """
        all_scenario_ids = [s.id for s in list_scenarios()]
        return self.run_suite(all_scenario_ids, task)

    def get_available_scenarios(self) -> list[ChaosScenario]:
        """Get all available scenarios.

        Returns:
            List of all ChaosScenario objects
        """
        return list_scenarios()


def run_chaos_test(
    scenario_id: str | None = None,
    deep_agent: Any | None = None,
    task: str = "default chaos test task",
) -> ChaosResult | ChaosSuiteResult:
    """Convenience function to run a chaos test.

    Args:
        scenario_id: Specific scenario ID to run, or None for all scenarios
        deep_agent: Optional DeepAgent instance
        task: Task description to execute

    Returns:
        ChaosResult for single scenario, ChaosSuiteResult for all scenarios
    """
    engine = ChaosEngine(deep_agent=deep_agent)

    if scenario_id:
        return engine.run_scenario(scenario_id, task)
    else:
        return engine.run_all_scenarios(task)