import pytest
import asyncio
from luminamind.utils.retry import (
    ExponentialBackoff,
    RetryError,
    with_retry,
    CircuitBreaker,
    CircuitState,
    CircuitBreakerOpen,
    circuit_breaker,
    FallbackChain,
    create_fallback_chain,
)


def test_exponential_backoff_delay():
    backoff = ExponentialBackoff(base=2, initial_delay=1, max_delay=60, jitter=False)

    assert backoff.get_delay(0) == 1
    assert backoff.get_delay(1) == 2
    assert backoff.get_delay(2) == 4
    assert backoff.get_delay(3) == 8
    assert backoff.get_delay(4) == 16


def test_exponential_backoff_max_delay():
    backoff = ExponentialBackoff(base=2, initial_delay=1, max_delay=10, jitter=False)

    assert backoff.get_delay(10) == 10  # capped
    assert backoff.get_delay(100) == 10  # still capped


def test_exponential_backoff_jitter():
    backoff = ExponentialBackoff(base=2, initial_delay=1, max_delay=60, jitter=True)

    delays = [backoff.get_delay(0) for _ in range(100)]
    # Should vary due to jitter
    assert len(set(delays)) > 1


@pytest.mark.asyncio
async def test_with_retry_success():
    call_count = {"count": 0}

    @with_retry(backoff=ExponentialBackoff(max_attempts=3))
    async def succeeds_on_third():
        call_count["count"] += 1
        if call_count["count"] < 3:
            raise ValueError("Not yet")
        return "success"

    result = await succeeds_on_third()
    assert result == "success"
    assert call_count["count"] == 3


@pytest.mark.asyncio
async def test_with_retry_all_fail():
    @with_retry(backoff=ExponentialBackoff(max_attempts=3))
    async def always_fails():
        raise ValueError("Always fails")

    with pytest.raises(RetryError) as exc_info:
        await always_fails()

    assert exc_info.value.attempts == 3


def test_circuit_breaker_initial_state():
    cb = CircuitBreaker(name="test", failure_threshold=3)
    assert cb.state == CircuitState.CLOSED
    assert cb.can_execute() is True


def test_circuit_breaker_opens_on_threshold():
    cb = CircuitBreaker(name="test", failure_threshold=3)

    cb.record_failure()
    assert cb.state == CircuitState.CLOSED
    cb.record_failure()
    assert cb.state == CircuitState.CLOSED
    cb.record_failure()  # Now at threshold

    assert cb.state == CircuitState.OPEN
    assert cb.can_execute() is False


def test_circuit_breaker_half_open_after_timeout():
    cb = CircuitBreaker(name="test", failure_threshold=1, recovery_timeout=0.1)

    cb.record_failure()
    assert cb.state == CircuitState.OPEN

    import time
    time.sleep(0.15)

    assert cb.state == CircuitState.HALF_OPEN
    assert cb.can_execute() is True


def test_circuit_breaker_half_open_to_closed():
    cb = CircuitBreaker(name="test", failure_threshold=1, recovery_timeout=0.1, half_open_max_calls=2)

    cb.record_failure()
    assert cb.state == CircuitState.OPEN

    import time
    time.sleep(0.15)

    # Half open
    assert cb.state == CircuitState.HALF_OPEN

    cb.record_success()
    assert cb.state == CircuitState.HALF_OPEN  # Need 2 successes
    cb.record_success()

    assert cb.state == CircuitState.CLOSED


def test_circuit_breaker_decorator():
    cb = CircuitBreaker(name="test", failure_threshold=2)

    call_count = {"count": 0}

    @circuit_breaker(cb)
    def failing_func():
        call_count["count"] += 1
        raise ValueError("fail")

    # First two calls fail but circuit stays closed
    failing_func()
    failing_func()

    # Third call opens circuit
    with pytest.raises(CircuitBreakerOpen):
        failing_func()

    assert cb.state == CircuitState.OPEN


@pytest.mark.asyncio
async def test_circuit_breaker_async():
    cb = CircuitBreaker(name="test-async", failure_threshold=2)

    @circuit_breaker(cb)
    async def async_fails():
        raise ValueError("async fail")

    # Open the circuit
    try:
        await async_fails()
    except ValueError:
        pass

    with pytest.raises(CircuitBreakerOpen):
        await async_fails()


def test_fallback_chain():
    call_order = {"order": []}

    def primary():
        call_order["order"].append("primary")
        raise ValueError("primary fails")

    def secondary():
        call_order["order"].append("secondary")
        return "secondary_result"

    chain = FallbackChain(primary, secondary)
    result = chain.execute_sync()

    assert result == "secondary_result"
    assert call_order["order"] == ["primary", "secondary"]


def test_fallback_chain_all_fail():
    def always_fails():
        raise ValueError("always")

    chain = FallbackChain(always_fails, always_fails)

    with pytest.raises(ValueError):
        chain.execute_sync()


def test_fallback_chain_async():
    call_order = {"order": []}

    async def async_primary():
        call_order["order"].append("primary")
        raise ValueError("primary fails")

    async def async_secondary():
        call_order["order"].append("secondary")
        return "result"

    chain = FallbackChain(async_primary, async_secondary)

    result = asyncio.run(chain.execute())

    assert result == "result"
    assert call_order["order"] == ["primary", "secondary"]
