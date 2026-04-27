"""Tests for Task 3: Example hooks for logging and metrics."""

import pytest
from luminamind.hooks import (
    LifecycleEvent,
    HookContext,
    log_hook,
    step_counter_hook,
    get_step_count,
    error_logger_hook,
    metrics_hook,
)


@pytest.mark.asyncio
async def test_log_hook():
    """Test: log_hook produces expected output structure."""
    ctx = HookContext(
        agent_id="test-agent",
        session_id="test-session",
        event_type=LifecycleEvent.ON_START,
    )
    # log_hook should not raise - it logs to the logging module
    await log_hook(ctx)


@pytest.mark.asyncio
async def test_step_counter_hook():
    """Test: step_counter_hook increments counter per session."""
    # Reset counter for test session
    test_session = "test-session-counter"

    ctx1 = HookContext(
        session_id=test_session,
        event_type=LifecycleEvent.ON_STEP,
    )
    ctx2 = HookContext(
        session_id=test_session,
        event_type=LifecycleEvent.ON_STEP,
    )

    step_counter_hook(ctx1)
    step_counter_hook(ctx2)

    assert get_step_count(test_session) == 2


@pytest.mark.asyncio
async def test_step_counter_hook_ignores_non_step_events():
    """Test: step_counter_hook only counts ON_STEP events."""
    test_session = "test-session-non-step"

    ctx_init = HookContext(
        session_id=test_session,
        event_type=LifecycleEvent.ON_INIT,
    )
    ctx_step = HookContext(
        session_id=test_session,
        event_type=LifecycleEvent.ON_STEP,
    )

    step_counter_hook(ctx_init)
    step_counter_hook(ctx_step)

    assert get_step_count(test_session) == 1


@pytest.mark.asyncio
async def test_error_logger_hook():
    """Test: error_logger_hook handles error events."""
    ctx = HookContext(
        session_id="test-session",
        event_type=LifecycleEvent.ON_ERROR,
        metadata={"error": "Test error message"},
    )
    # error_logger_hook should not raise
    await error_logger_hook(ctx)


@pytest.mark.asyncio
async def test_metrics_hook():
    """Test: metrics_hook handles complete events."""
    ctx = HookContext(
        session_id="test-session",
        event_type=LifecycleEvent.ON_COMPLETE,
        metadata={"score": 0.95},
    )
    # metrics_hook should not raise (placeholder for Prometheus)
    await metrics_hook(ctx)


@pytest.mark.asyncio
async def test_metrics_hook_ignores_non_complete_events():
    """Test: metrics_hook only processes ON_COMPLETE events."""
    ctx = HookContext(
        session_id="test-session",
        event_type=LifecycleEvent.ON_STEP,
    )
    # Should not raise, but also not emit metrics
    await metrics_hook(ctx)
