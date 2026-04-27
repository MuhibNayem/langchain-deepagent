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
