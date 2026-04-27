"""Fault injection primitives for chaos testing."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class NetworkFault(Enum):
    """Network-level fault types that can be injected."""
    LATENCY = auto()          # Add delay to network calls
    PACKET_LOSS = auto()      # Drop percentage of packets
    DNS_FAILURE = auto()      # Resolve to wrong address
    CONNECTION_TIMEOUT = auto()  # Close connections
    BANDWIDTH_LIMIT = auto()  # Throttle throughput


class LLMFault(Enum):
    """LLM/API-level fault types that can be injected."""
    TIMEOUT = auto()          # LLM takes too long
    RATE_LIMIT = auto()       # API returns 429
    SERVER_ERROR = auto()     # API returns 500
    INVALID_RESPONSE = auto()  # Malformed JSON
    EMPTY_RESPONSE = auto()  # No content returned


class SystemFault(Enum):
    """System-level fault types that can be injected."""
    REDIS_UNAVAILABLE = auto()  # Redis connection fails
    DISK_FULL = auto()        # Write fails with ENOSPC
    MEMORY_PRESSURE = auto()  # OOM warning
    PROCESS_CRASH = auto()    # Worker process dies


class FaultType(Enum):
    """Unified fault type enum for all fault categories."""
    # Network faults
    NETWORK_LATENCY = auto()
    NETWORK_PACKET_LOSS = auto()
    NETWORK_DNS_FAILURE = auto()
    NETWORK_CONNECTION_TIMEOUT = auto()
    NETWORK_BANDWIDTH_LIMIT = auto()
    # LLM faults
    LLM_TIMEOUT = auto()
    LLM_RATE_LIMIT = auto()
    LLM_SERVER_ERROR = auto()
    LLM_INVALID_RESPONSE = auto()
    LLM_EMPTY_RESPONSE = auto()
    # System faults
    SYSTEM_REDIS_UNAVAILABLE = auto()
    SYSTEM_DISK_FULL = auto()
    SYSTEM_MEMORY_PRESSURE = auto()
    SYSTEM_PROCESS_CRASH = auto()


@dataclass
class FaultConfig:
    """Configuration for a fault injection scenario.

    Attributes:
        fault_type: The type of fault to inject
        probability: Probability of fault triggering (0.0-1.0)
        duration_seconds: How long the fault should last
        parameters: Fault-specific parameters (e.g., latency_ms for LATENCY)
        target: Optional target component (e.g., 'llm', 'redis', 'filesystem')
    """
    fault_type: FaultType
    probability: float = 1.0
    duration_seconds: int = 60
    parameters: dict[str, Any] = field(default_factory=dict)
    target: str | None = None

    def __post_init__(self) -> None:
        if not 0.0 <= self.probability <= 1.0:
            raise ValueError(f"probability must be between 0.0 and 1.0, got {self.probability}")
        if self.duration_seconds < 0:
            raise ValueError(f"duration_seconds must be non-negative, got {self.duration_seconds}")


class FaultInjector:
    """Manages fault injection for chaos testing.

    Provides context managers and utilities for injecting faults
    into network, LLM, and system components.
    """

    def __init__(self) -> None:
        self._active_faults: list[FaultConfig] = []
        self._patches: list[Any] = []

    def inject(self, fault: FaultConfig) -> None:
        """Register a fault to be injected.

        Args:
            fault: FaultConfig describing the fault to inject
        """
        self._active_faults.append(fault)

    def inject_network_latency(self, delay_ms: int = 500) -> FaultConfig:
        """Create a network latency fault configuration.

        Args:
            delay_ms: Milliseconds of delay to add (default 500ms)

        Returns:
            Configured FaultConfig for network latency
        """
        return FaultConfig(
            fault_type=FaultType.NETWORK_LATENCY,
            probability=1.0,
            parameters={"delay_ms": delay_ms},
        )

    def inject_llm_timeout(self, timeout_seconds: int = 60) -> FaultConfig:
        """Create an LLM timeout fault configuration.

        Args:
            timeout_seconds: Seconds before timeout (default 60)

        Returns:
            Configured FaultConfig for LLM timeout
        """
        return FaultConfig(
            fault_type=FaultType.LLM_TIMEOUT,
            probability=1.0,
            duration_seconds=timeout_seconds,
            parameters={"timeout_seconds": timeout_seconds},
        )

    def inject_llm_rate_limit(self, retry_after: int = 60) -> FaultConfig:
        """Create an LLM rate limit fault configuration.

        Args:
            retry_after: Seconds to wait before retry (default 60)

        Returns:
            Configured FaultConfig for rate limiting
        """
        return FaultConfig(
            fault_type=FaultType.LLM_RATE_LIMIT,
            probability=1.0,
            duration_seconds=retry_after,
            parameters={"retry_after": retry_after, "status_code": 429},
        )

    def inject_redis_unavailable(self) -> FaultConfig:
        """Create a Redis unavailable fault configuration.

        Returns:
            Configured FaultConfig for Redis failure
        """
        return FaultConfig(
            fault_type=FaultType.SYSTEM_REDIS_UNAVAILABLE,
            probability=1.0,
        )

    def inject_disk_full(self) -> FaultConfig:
        """Create a disk full fault configuration.

        Returns:
            Configured FaultConfig for disk failure
        """
        return FaultConfig(
            fault_type=FaultType.SYSTEM_DISK_FULL,
            probability=1.0,
        )

    def is_active(self, fault_type: FaultType) -> bool:
        """Check if a fault type is currently active.

        Args:
            fault_type: The fault type to check

        Returns:
            True if the fault type is currently active
        """
        return any(f.fault_type == fault_type for f in self._active_faults)

    def get_active_faults(self) -> list[FaultConfig]:
        """Get all currently active faults.

        Returns:
            List of active FaultConfig objects
        """
        return list(self._active_faults)

    def clear(self) -> None:
        """Clear all registered faults."""
        self._active_faults.clear()
        self._patches.clear()

    def simulate_latency(self, delay_ms: int) -> None:
        """Simulate network latency by sleeping.

        Args:
            delay_ms: Milliseconds to sleep
        """
        time.sleep(delay_ms / 1000.0)

    def __enter__(self) -> FaultInjector:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.clear()