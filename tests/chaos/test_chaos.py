"""Unit tests for chaos testing module."""

import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from luminamind.chaos import (
    ChaosEngine,
    ChaosReport,
    ChaosResult,
    ChaosSuiteResult,
    FaultConfig,
    FaultInjector,
    FaultType,
    NetworkFault,
    LLMFault,
    SystemFault,
    ChaosScenario,
    ScenarioType,
    generate_chaos_report,
    get_scenario,
    list_scenarios,
    save_json_report,
    SCENARIOS,
)


class TestFaultTypes:
    """Tests for fault type enums."""

    def test_network_fault_values(self) -> None:
        """NetworkFault enum should have expected values."""
        assert NetworkFault.LATENCY is not None
        assert NetworkFault.PACKET_LOSS is not None
        assert NetworkFault.DNS_FAILURE is not None
        assert NetworkFault.CONNECTION_TIMEOUT is not None
        assert NetworkFault.BANDWIDTH_LIMIT is not None

    def test_llm_fault_values(self) -> None:
        """LLMFault enum should have expected values."""
        assert LLMFault.TIMEOUT is not None
        assert LLMFault.RATE_LIMIT is not None
        assert LLMFault.SERVER_ERROR is not None
        assert LLMFault.INVALID_RESPONSE is not None
        assert LLMFault.EMPTY_RESPONSE is not None

    def test_system_fault_values(self) -> None:
        """SystemFault enum should have expected values."""
        assert SystemFault.REDIS_UNAVAILABLE is not None
        assert SystemFault.DISK_FULL is not None
        assert SystemFault.MEMORY_PRESSURE is not None
        assert SystemFault.PROCESS_CRASH is not None


class TestFaultConfig:
    """Tests for FaultConfig dataclass."""

    def test_valid_config(self) -> None:
        """FaultConfig should accept valid parameters."""
        config = FaultConfig(
            fault_type=FaultType.LLM_TIMEOUT,
            probability=0.5,
            duration_seconds=30,
            parameters={"timeout_seconds": 30},
        )
        assert config.fault_type == FaultType.LLM_TIMEOUT
        assert config.probability == 0.5
        assert config.duration_seconds == 30

    def test_invalid_probability(self) -> None:
        """FaultConfig should reject invalid probability."""
        with pytest.raises(ValueError):
            FaultConfig(fault_type=FaultType.LLM_TIMEOUT, probability=1.5)

    def test_invalid_duration(self) -> None:
        """FaultConfig should reject negative duration."""
        with pytest.raises(ValueError):
            FaultConfig(fault_type=FaultType.LLM_TIMEOUT, duration_seconds=-1)


class TestFaultInjector:
    """Tests for FaultInjector class."""

    def test_inject_fault(self) -> None:
        """FaultInjector should register faults."""
        injector = FaultInjector()
        fault = FaultConfig(fault_type=FaultType.LLM_TIMEOUT)
        injector.inject(fault)
        assert len(injector.get_active_faults()) == 1

    def test_is_active(self) -> None:
        """FaultInjector should correctly identify active faults."""
        injector = FaultInjector()
        fault = FaultConfig(fault_type=FaultType.LLM_TIMEOUT)
        injector.inject(fault)
        assert injector.is_active(FaultType.LLM_TIMEOUT)
        assert not injector.is_active(FaultType.LLM_RATE_LIMIT)

    def test_clear_faults(self) -> None:
        """FaultInjector should clear all faults."""
        injector = FaultInjector()
        injector.inject(FaultConfig(fault_type=FaultType.LLM_TIMEOUT))
        injector.clear()
        assert len(injector.get_active_faults()) == 0

    def test_context_manager(self) -> None:
        """FaultInjector should work as context manager."""
        with FaultInjector() as injector:
            injector.inject(FaultConfig(fault_type=FaultType.LLM_TIMEOUT))
        # After exiting context, faults should be cleared
        # This tests __exit__ calls clear()

    def test_inject_network_latency(self) -> None:
        """inject_network_latency helper should create correct config."""
        injector = FaultInjector()
        config = injector.inject_network_latency(delay_ms=500)
        assert config.fault_type == FaultType.NETWORK_LATENCY
        assert config.parameters["delay_ms"] == 500

    def test_inject_llm_timeout(self) -> None:
        """inject_llm_timeout helper should create correct config."""
        injector = FaultInjector()
        config = injector.inject_llm_timeout(timeout_seconds=60)
        assert config.fault_type == FaultType.LLM_TIMEOUT
        assert config.parameters["timeout_seconds"] == 60

    def test_simulate_latency(self) -> None:
        """simulate_latency should sleep for correct duration."""
        injector = FaultInjector()
        start = time.time()
        injector.simulate_latency(delay_ms=50)
        elapsed = time.time() - start
        assert elapsed >= 0.04  # 50ms = 0.05s, allow some tolerance


class TestScenarios:
    """Tests for chaos scenarios."""

    def test_scenario_count(self) -> None:
        """Should have at least 10 pre-defined scenarios."""
        assert len(SCENARIOS) >= 10

    def test_get_scenario(self) -> None:
        """get_scenario should return correct scenario."""
        scenario = get_scenario("network_latency")
        assert scenario is not None
        assert scenario.id == "network_latency"

    def test_get_scenario_not_found(self) -> None:
        """get_scenario should return None for unknown ID."""
        assert get_scenario("nonexistent") is None

    def test_list_scenarios(self) -> None:
        """list_scenarios should return all scenarios."""
        scenarios = list_scenarios()
        assert len(scenarios) >= 10
        assert all(isinstance(s, ChaosScenario) for s in scenarios)

    def test_scenario_types(self) -> None:
        """ScenarioType should have expected values."""
        assert ScenarioType.NETWORK_FAILURE is not None
        assert ScenarioType.LLM_TIMEOUT is not None
        assert ScenarioType.LLM_RATE_LIMIT is not None
        assert ScenarioType.LLM_SERVER_ERROR is not None
        assert ScenarioType.PARTIAL_SYSTEM_FAILURE is not None
        assert ScenarioType.CASCADING_FAILURE is not None

    def test_cascading_failure_has_multiple_faults(self) -> None:
        """Cascading failure scenario should have multiple faults."""
        scenario = get_scenario("cascading_failure")
        assert scenario is not None
        assert len(scenario.faults) > 1


class TestChaosEngine:
    """Tests for ChaosEngine class."""

    def test_engine_init(self) -> None:
        """ChaosEngine should initialize correctly."""
        engine = ChaosEngine()
        assert engine is not None

    def test_run_single_scenario(self) -> None:
        """run_scenario should execute and return result."""
        engine = ChaosEngine()
        result = engine.run_scenario("network_latency", "test task")
        assert isinstance(result, ChaosResult)
        assert result.scenario_id == "network_latency"
        assert result.task == "test task"

    def test_run_unknown_scenario(self) -> None:
        """run_scenario should handle unknown scenario gracefully."""
        engine = ChaosEngine()
        result = engine.run_scenario("nonexistent", "test task")
        assert result.outcome == "failed"
        assert "Unknown scenario" in (result.error_message or "")

    def test_run_all_scenarios(self) -> None:
        """run_all_scenarios should execute all scenarios."""
        engine = ChaosEngine()
        result = engine.run_all_scenarios("test task")
        assert isinstance(result, ChaosSuiteResult)
        assert result.total_scenarios >= 10
        assert len(result.results) >= 10

    def test_get_available_scenarios(self) -> None:
        """get_available_scenarios should return scenario list."""
        engine = ChaosEngine()
        scenarios = engine.get_available_scenarios()
        assert len(scenarios) >= 10


class TestChaosResult:
    """Tests for ChaosResult dataclass."""

    def test_result_creation(self) -> None:
        """ChaosResult should be creatable with expected fields."""
        result = ChaosResult(
            scenario_id="test",
            task="test task",
            fault_injected=True,
            execution_time=1.5,
            outcome="success",
            graceful_degradation=True,
        )
        assert result.scenario_id == "test"
        assert result.fault_injected is True
        assert result.execution_time == 1.5
        assert result.outcome == "success"


class TestChaosReport:
    """Tests for ChaosReport class."""

    def test_from_suite_result(self) -> None:
        """ChaosReport should be creatable from suite result."""
        result = ChaosResult(
            scenario_id="network_latency",
            task="test",
            outcome="success",
            graceful_degradation=True,
        )
        suite_result = ChaosSuiteResult(
            results=[result],
            total_scenarios=1,
            passed=1,
            failed=0,
        )
        report = ChaosReport.from_suite_result(suite_result)
        assert report.total_scenarios == 1
        assert report.passed == 1
        assert report.failed == 0

    def test_to_dict(self) -> None:
        """ChaosReport.to_dict should produce serializable output."""
        result = ChaosResult(
            scenario_id="network_latency",
            task="test",
            outcome="success",
            graceful_degradation=True,
        )
        suite_result = ChaosSuiteResult(
            results=[result],
            total_scenarios=1,
            passed=1,
            failed=0,
        )
        report = ChaosReport.from_suite_result(suite_result)
        data = report.to_dict()
        assert isinstance(data, dict)
        assert "timestamp" in data
        assert "total_scenarios" in data


class TestGenerateReport:
    """Tests for report generation."""

    def test_generate_chaos_report(self) -> None:
        """generate_chaos_report should produce markdown."""
        result = ChaosResult(
            scenario_id="network_latency",
            task="test task",
            outcome="success",
            graceful_degradation=True,
            execution_time=1.5,
        )
        suite_result = ChaosSuiteResult(
            results=[result],
            total_scenarios=1,
            passed=1,
            failed=0,
        )
        report = generate_chaos_report(suite_result)
        assert "# Chaos Test Report" in report
        assert "Network Latency" in report

    def test_save_json_report(self) -> None:
        """save_json_report should write valid JSON file."""
        result = ChaosResult(
            scenario_id="network_latency",
            task="test",
            outcome="success",
            graceful_degradation=True,
        )
        suite_result = ChaosSuiteResult(
            results=[result],
            total_scenarios=1,
            passed=1,
            failed=0,
        )
        output_path = Path("/tmp/chaos_test_report.json")
        saved_path = save_json_report(suite_result, output_path)
        assert saved_path.exists()

        # Verify JSON is valid
        with open(saved_path) as f:
            data = json.load(f)
        assert data["total_scenarios"] == 1
        assert data["passed"] == 1

        # Clean up
        output_path.unlink(missing_ok=True)


class TestIntegration:
    """Integration tests for chaos testing."""

    def test_end_to_end_single_scenario(self) -> None:
        """Run a single scenario end-to-end."""
        engine = ChaosEngine()
        result = engine.run_scenario("network_latency", "integration test")

        assert result.scenario_id == "network_latency"
        assert result.fault_injected is True
        assert result.execution_time > 0

    def test_end_to_end_all_scenarios(self) -> None:
        """Run all scenarios end-to-end."""
        engine = ChaosEngine()
        result = engine.run_all_scenarios("integration test suite")

        assert result.total_scenarios >= 10
        assert len(result.results) == result.total_scenarios
        assert result.passed + result.failed == result.total_scenarios

    def test_run_chaos_test_function(self) -> None:
        """run_chaos_test convenience function should work."""
        from luminamind.chaos import run_chaos_test
        result = run_chaos_test(scenario_id="llm_timeout", task="test")
        assert isinstance(result, ChaosResult)
        assert result.scenario_id == "llm_timeout"