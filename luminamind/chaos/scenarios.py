"""Chaos scenario definitions for fault injection testing."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from luminamind.chaos.faults import (
    FaultConfig,
    FaultType,
    SystemFault,
    LLMFault,
    NetworkFault,
)


class ScenarioType(Enum):
    """Categories of chaos scenarios."""
    NETWORK_FAILURE = auto()
    LLM_TIMEOUT = auto()
    LLM_RATE_LIMIT = auto()
    LLM_SERVER_ERROR = auto()
    PARTIAL_SYSTEM_FAILURE = auto()
    CASCADING_FAILURE = auto()


@dataclass
class ChaosScenario:
    """A chaos testing scenario with fault injection configuration.

    Attributes:
        id: Unique identifier for the scenario
        name: Human-readable name
        description: What this scenario tests
        scenario_type: Category of the scenario
        faults: List of fault configurations to inject
        expected_behavior: What the system should do under this fault
        graceful_degradation: Whether graceful degradation is expected
        severity: How severe the fault is (1-5, 5 being most severe)
    """
    id: str
    name: str
    description: str
    scenario_type: ScenarioType
    faults: list[FaultConfig] = field(default_factory=list)
    expected_behavior: str = ""
    graceful_degradation: bool = True
    severity: int = 3

    def add_fault(self, fault: FaultConfig) -> None:
        """Add a fault configuration to this scenario.

        Args:
            fault: FaultConfig to add
        """
        self.faults.append(fault)


# Pre-defined chaos scenarios
SCENARIOS: dict[str, ChaosScenario] = {}


def _init_scenarios() -> dict[str, ChaosScenario]:
    """Initialize the pre-defined chaos scenarios.

    Returns:
        Dictionary mapping scenario IDs to ChaosScenario objects
    """
    scenarios = {}

    # 1. Network Latency - 500ms added to all HTTP calls
    scenarios["network_latency"] = ChaosScenario(
        id="network_latency",
        name="Network Latency",
        description="All HTTP calls have 500ms added latency",
        scenario_type=ScenarioType.NETWORK_FAILURE,
        faults=[
            FaultConfig(
                fault_type=FaultType.NETWORK_LATENCY,
                probability=1.0,
                parameters={"delay_ms": 500},
                target="http",
            )
        ],
        expected_behavior="System remains functional but slower",
        graceful_degradation=True,
        severity=2,
    )

    # 2. DNS Failure - All DNS lookups fail
    scenarios["dns_failure"] = ChaosScenario(
        id="dns_failure",
        name="DNS Failure",
        description="All DNS lookups fail completely",
        scenario_type=ScenarioType.NETWORK_FAILURE,
        faults=[
            FaultConfig(
                fault_type=FaultType.NETWORK_DNS_FAILURE,
                probability=1.0,
                target="dns",
            )
        ],
        expected_behavior="Cached results used or error message shown",
        graceful_degradation=True,
        severity=4,
    )

    # 3. LLM Timeout - LLM takes 60+ seconds
    scenarios["llm_timeout"] = ChaosScenario(
        id="llm_timeout",
        name="LLM Timeout",
        description="LLM takes longer than expected to respond",
        scenario_type=ScenarioType.LLM_TIMEOUT,
        faults=[
            FaultConfig(
                fault_type=FaultType.LLM_TIMEOUT,
                probability=1.0,
                duration_seconds=60,
                parameters={"timeout_seconds": 60},
                target="llm",
            )
        ],
        expected_behavior="Timeout handling kicks in, error reported gracefully",
        graceful_degradation=True,
        severity=3,
    )

    # 4. LLM Rate Limit - API returns 429
    scenarios["llm_rate_limit"] = ChaosScenario(
        id="llm_rate_limit",
        name="LLM Rate Limit",
        description="API returns 429 Too Many Requests",
        scenario_type=ScenarioType.LLM_RATE_LIMIT,
        faults=[
            FaultConfig(
                fault_type=FaultType.LLM_RATE_LIMIT,
                probability=1.0,
                duration_seconds=60,
                parameters={"retry_after": 60, "status_code": 429},
                target="llm",
            )
        ],
        expected_behavior="Retry with exponential backoff",
        graceful_degradation=True,
        severity=3,
    )

    # 5. LLM Server Error - API returns 500
    scenarios["llm_server_error"] = ChaosScenario(
        id="llm_server_error",
        name="LLM Server Error",
        description="API returns 500 Internal Server Error",
        scenario_type=ScenarioType.LLM_SERVER_ERROR,
        faults=[
            FaultConfig(
                fault_type=FaultType.LLM_SERVER_ERROR,
                probability=1.0,
                parameters={"status_code": 500},
                target="llm",
            )
        ],
        expected_behavior="Graceful error handling, partial results if possible",
        graceful_degradation=True,
        severity=4,
    )

    # 6. Redis Unavailable - Redis connection fails
    scenarios["redis_unavailable"] = ChaosScenario(
        id="redis_unavailable",
        name="Redis Unavailable",
        description="Redis connection fails completely",
        scenario_type=ScenarioType.PARTIAL_SYSTEM_FAILURE,
        faults=[
            FaultConfig(
                fault_type=FaultType.SYSTEM_REDIS_UNAVAILABLE,
                probability=1.0,
                target="redis",
            )
        ],
        expected_behavior="In-memory fallback activated",
        graceful_degradation=True,
        severity=4,
    )

    # 7. Disk Full - Write operations fail
    scenarios["disk_full"] = ChaosScenario(
        id="disk_full",
        name="Disk Full",
        description="Write operations fail with ENOSPC",
        scenario_type=ScenarioType.PARTIAL_SYSTEM_FAILURE,
        faults=[
            FaultConfig(
                fault_type=FaultType.SYSTEM_DISK_FULL,
                probability=1.0,
                target="filesystem",
            )
        ],
        expected_behavior="Error handling, report disk space issue",
        graceful_degradation=True,
        severity=5,
    )

    # 8. Process Crash - Worker dies mid-task
    scenarios["process_crash"] = ChaosScenario(
        id="process_crash",
        name="Process Crash",
        description="Worker process dies unexpectedly",
        scenario_type=ScenarioType.PARTIAL_SYSTEM_FAILURE,
        faults=[
            FaultConfig(
                fault_type=FaultType.SYSTEM_PROCESS_CRASH,
                probability=1.0,
                target="worker",
            )
        ],
        expected_behavior="Recovery mechanism activates, task rescheduled",
        graceful_degradation=True,
        severity=5,
    )

    # 9. Cascading Failure - Multiple faults at once
    scenarios["cascading_failure"] = ChaosScenario(
        id="cascading_failure",
        name="Cascading Failure",
        description="Multiple failures occur simultaneously",
        scenario_type=ScenarioType.CASCADING_FAILURE,
        faults=[
            FaultConfig(
                fault_type=FaultType.NETWORK_LATENCY,
                probability=0.8,
                parameters={"delay_ms": 300},
                target="http",
            ),
            FaultConfig(
                fault_type=FaultType.LLM_TIMEOUT,
                probability=0.5,
                duration_seconds=30,
                parameters={"timeout_seconds": 30},
                target="llm",
            ),
            FaultConfig(
                fault_type=FaultType.SYSTEM_REDIS_UNAVAILABLE,
                probability=0.3,
                target="redis",
            ),
        ],
        expected_behavior="Core functions survive, degraded mode",
        graceful_degradation=True,
        severity=5,
    )

    # 10. Slow LLM - LLM responds in 30s (but not timeout)
    scenarios["slow_llm"] = ChaosScenario(
        id="slow_llm",
        name="Slow LLM Response",
        description="LLM responds after 30 seconds (but within timeout)",
        scenario_type=ScenarioType.LLM_TIMEOUT,
        faults=[
            FaultConfig(
                fault_type=FaultType.LLM_TIMEOUT,
                probability=1.0,
                duration_seconds=30,
                parameters={"latency_ms": 30000, "timeout_seconds": 60},
                target="llm",
            )
        ],
        expected_behavior="Streaming progress shown, eventual completion",
        graceful_degradation=True,
        severity=1,
    )

    # 11. Bandwidth Limit - Network throttled
    scenarios["bandwidth_limit"] = ChaosScenario(
        id="bandwidth_limit",
        name="Bandwidth Limit",
        description="Network throughput severely limited",
        scenario_type=ScenarioType.NETWORK_FAILURE,
        faults=[
            FaultConfig(
                fault_type=FaultType.NETWORK_BANDWIDTH_LIMIT,
                probability=1.0,
                parameters={"kbps": 100},
                target="http",
            )
        ],
        expected_behavior="Reduced data transfer, potential timeouts",
        graceful_degradation=True,
        severity=3,
    )

    # 12. Invalid LLM Response - Malformed JSON
    scenarios["invalid_llm_response"] = ChaosScenario(
        id="invalid_llm_response",
        name="Invalid LLM Response",
        description="LLM returns malformed response that can't be parsed",
        scenario_type=ScenarioType.LLM_SERVER_ERROR,
        faults=[
            FaultConfig(
                fault_type=FaultType.LLM_INVALID_RESPONSE,
                probability=1.0,
                parameters={"invalid_json": True},
                target="llm",
            )
        ],
        expected_behavior="Parse error handled gracefully, error message shown",
        graceful_degradation=True,
        severity=3,
    )

    return scenarios


SCENARIOS = _init_scenarios()


def get_scenario(scenario_id: str) -> ChaosScenario | None:
    """Get a scenario by ID.

    Args:
        scenario_id: The scenario identifier

    Returns:
        ChaosScenario if found, None otherwise
    """
    return SCENARIOS.get(scenario_id)


def list_scenarios() -> list[ChaosScenario]:
    """List all available scenarios.

    Returns:
        List of all ChaosScenario objects
    """
    return list(SCENARIOS.values())


def get_scenarios_by_type(scenario_type: ScenarioType) -> list[ChaosScenario]:
    """Get all scenarios of a specific type.

    Args:
        scenario_type: The type to filter by

    Returns:
        List of matching ChaosScenario objects
    """
    return [s for s in SCENARIOS.values() if s.scenario_type == scenario_type]