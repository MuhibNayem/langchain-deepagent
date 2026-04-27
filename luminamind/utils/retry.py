from __future__ import annotations
import asyncio
import random
import time
from enum import Enum
from functools import wraps
from typing import Any, Callable, TypeVar, Generic

T = TypeVar("T")

class RetryError(Exception):
    """Raised when all retry attempts fail."""
    def __init__(self, message: str, attempts: int, last_error: Exception):
        super().__init__(message)
        self.attempts = attempts
        self.last_error = last_error


class ExponentialBackoff:
    """Exponential backoff retry strategy."""

    def __init__(
        self,
        base: float = 2.0,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        max_attempts: int = 5,
        jitter: bool = True,
    ):
        self.base = base
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.max_attempts = max_attempts
        self.jitter = jitter

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number (0-indexed)."""
        delay = self.initial_delay * (self.base ** attempt)
        delay = min(delay, self.max_delay)

        if self.jitter:
            # Add random jitter of ±25%
            jitter_range = delay * 0.25
            delay = delay + random.uniform(-jitter_range, jitter_range)

        return max(0, delay)

    async def sleep(self, attempt: int) -> None:
        """Async sleep for the calculated delay."""
        delay = self.get_delay(attempt)
        await asyncio.sleep(delay)

    def sleep_sync(self, attempt: int) -> None:
        """Sync sleep for the calculated delay."""
        delay = self.get_delay(attempt)
        time.sleep(delay)


def with_retry(
    backoff: ExponentialBackoff | None = None,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to add retry logic to async or sync functions.

    Args:
        backoff: ExponentialBackoff instance (uses default if None)
        exceptions: Tuple of exception types to retry on
    """
    if backoff is None:
        backoff = ExponentialBackoff()

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs) -> T:
                last_error = None
                for attempt in range(backoff.max_attempts):
                    try:
                        return await func(*args, **kwargs)
                    except exceptions as e:
                        last_error = e
                        if attempt < backoff.max_attempts - 1:
                            await backoff.sleep(attempt)
                        else:
                            raise RetryError(
                                f"All {backoff.max_attempts} attempts failed",
                                attempts=backoff.max_attempts,
                                last_error=last_error,
                            ) from last_error
                raise RetryError("Unexpected exit", 0, last_error)

            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs) -> T:
                last_error = None
                for attempt in range(backoff.max_attempts):
                    try:
                        return func(*args, **kwargs)
                    except exceptions as e:
                        last_error = e
                        if attempt < backoff.max_attempts - 1:
                            backoff.sleep_sync(attempt)
                        else:
                            raise RetryError(
                                f"All {backoff.max_attempts} attempts failed",
                                attempts=backoff.max_attempts,
                                last_error=last_error,
                            ) from last_error
                raise RetryError("Unexpected exit", 0, last_error)

            return sync_wrapper

    return decorator


class CircuitState(str, Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is OPEN."""
    def __init__(self, name: str, reset_time: float):
        self.name = name
        self.reset_time = reset_time
        super().__init__(f"Circuit breaker '{name}' is OPEN until {reset_time}")


class CircuitBreaker:
    """Circuit breaker pattern implementation."""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_max_calls: int = 3,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: float | None = None
        self._half_open_calls = 0

    @property
    def state(self) -> CircuitState:
        """Get current state, checking for timeout transitions."""
        if self._state == CircuitState.OPEN:
            if self._last_failure_time is not None:
                if time.time() - self._last_failure_time >= self.recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
        return self._state

    def record_success(self) -> None:
        """Record a successful call."""
        if self._state == CircuitState.HALF_OPEN:
            self._half_open_calls += 1
            if self._half_open_calls >= self.half_open_max_calls:
                self._state = CircuitState.CLOSED
                self._failure_count = 0
        elif self._state == CircuitState.CLOSED:
            self._failure_count = 0

    def record_failure(self) -> None:
        """Record a failed call."""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.OPEN
        elif self._state == CircuitState.CLOSED:
            if self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN

    def can_execute(self) -> bool:
        """Check if execution is allowed."""
        return self.state != CircuitState.OPEN

    def get_reset_time(self) -> float | None:
        """Get time when circuit will attempt recovery."""
        if self._state == CircuitState.OPEN and self._last_failure_time:
            return self._last_failure_time + self.recovery_timeout
        return None


def circuit_breaker(
    cb: CircuitBreaker,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to add circuit breaker to a function.

    Args:
        cb: CircuitBreaker instance
        exceptions: Tuple of exception types that count as failures
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs) -> T:
                if not cb.can_execute():
                    raise CircuitBreakerOpen(cb.name, cb.get_reset_time() or 0)

                try:
                    result = await func(*args, **kwargs)
                    cb.record_success()
                    return result
                except exceptions as e:
                    cb.record_failure()
                    raise

            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs) -> T:
                if not cb.can_execute():
                    raise CircuitBreakerOpen(cb.name, cb.get_reset_time() or 0)

                try:
                    result = func(*args, **kwargs)
                    cb.record_success()
                    return result
                except exceptions as e:
                    cb.record_failure()
                    raise

            return sync_wrapper

    return decorator
