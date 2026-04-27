"""
Circuit breaker for LLM call protection.

Extends the retry framework with circuit breaker pattern for LLM protection.
"""
from __future__ import annotations
from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable, Any
import threading
import time


class CircuitState(Enum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing — reject calls immediately
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5  # Failures before opening
    recovery_timeout: int = 60  # Seconds before trying again
    half_open_max_calls: int = 3  # Max calls in half-open state
    expected_exception: type = Exception


class CircuitBreaker:
    """Circuit breaker for protecting LLM calls from cascading failures."""

    def __init__(self, name: str, config: CircuitBreakerConfig | None = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: datetime | None = None
        self._half_open_calls = 0
        self._lock = threading.Lock()

    def call(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        """Execute func with circuit breaker protection."""
        if not self._can_execute():
            raise CircuitOpenError(f"Circuit {self.name} is OPEN")
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.config.expected_exception as e:
            self._on_failure()
            raise

    def _can_execute(self) -> bool:
        with self._lock:
            if self._state == CircuitState.CLOSED:
                return True
            if self._state == CircuitState.OPEN:
                if self._should_attempt_recovery():
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
                    return True
                return False
            if self._state == CircuitState.HALF_OPEN:
                return self._half_open_calls < self.config.half_open_max_calls

    def _on_success(self):
        with self._lock:
            self._failure_count = 0
            self._state = CircuitState.CLOSED

    def _on_failure(self):
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = datetime.now()
            if self._failure_count >= self.config.failure_threshold:
                self._state = CircuitState.OPEN

    def _should_attempt_recovery(self) -> bool:
        if self._last_failure_time is None:
            return True
        elapsed = (datetime.now() - self._last_failure_time).total_seconds()
        return elapsed >= self.config.recovery_timeout

    @property
    def state(self) -> CircuitState:
        return self._state


class CircuitOpenError(Exception):
    """Raised when circuit is open and call is rejected."""
