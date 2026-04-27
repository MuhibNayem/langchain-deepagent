"""Comprehensive unit tests for lifecycle hooks.

Tests cover:
1. LifecycleEvent enum
2. HookContext model with metadata
3. Registration and emission
4. Multiple event registration
5. Sync vs async callbacks
6. Unregistration
7. Error handling in callbacks
"""

import pytest
import asyncio

from luminamind.hooks import (
    HookEmitter,
    HookContext,
    LifecycleEvent,
    on_init,
    on_start,
    on_step,
    on_complete,
    on_error,
    on_exit,
    get_emitter,
)


@pytest.fixture
def emitter():
    return HookEmitter()


def test_lifecycle_event_enum():
    """Test: LifecycleEvent enum has all required events."""
    assert LifecycleEvent.ON_INIT.value == "on_init"
    assert LifecycleEvent.ON_START.value == "on_start"
    assert LifecycleEvent.ON_STEP.value == "on_step"
    assert LifecycleEvent.ON_COMPLETE.value == "on_complete"
    assert LifecycleEvent.ON_ERROR.value == "on_error"
    assert LifecycleEvent.ON_EXIT.value == "on_exit"


def test_hook_context():
    """Test: HookContext includes agent_id, session_id, event_type, timestamp."""
    ctx = HookContext(
        agent_id="agent-1",
        session_id="session-1",
        event_type=LifecycleEvent.ON_START,
    )
    assert ctx.agent_id == "agent-1"
    assert ctx.session_id == "session-1"
    assert ctx.event_type == LifecycleEvent.ON_START
    assert ctx.timestamp is not None


def test_hook_context_with_metadata():
    """Test: HookContext includes additional metadata dict."""
    ctx = HookContext(
        event_type=LifecycleEvent.ON_ERROR,
        metadata={"error": "Timeout", "retry_count": 3},
    )
    assert ctx.metadata["error"] == "Timeout"
    assert ctx.metadata["retry_count"] == 3


@pytest.mark.asyncio
async def test_register_and_emit(emitter):
    """Test: Register callback for specific event and emit."""
    received = []

    async def callback(ctx: HookContext):
        received.append(ctx)

    emitter.register(callback, [LifecycleEvent.ON_START])
    await emitter.emit(LifecycleEvent.ON_START, agent_id="test")

    assert len(received) == 1
    assert received[0].agent_id == "test"
    assert received[0].event_type == LifecycleEvent.ON_START


@pytest.mark.asyncio
async def test_register_multiple_events(emitter):
    """Test: Register callback for multiple events."""
    received = []

    async def callback(ctx: HookContext):
        received.append(ctx.event_type)

    emitter.register(callback, [LifecycleEvent.ON_START, LifecycleEvent.ON_COMPLETE])
    await emitter.emit(LifecycleEvent.ON_START)
    await emitter.emit(LifecycleEvent.ON_COMPLETE)

    assert len(received) == 2
    assert LifecycleEvent.ON_START in received
    assert LifecycleEvent.ON_COMPLETE in received


@pytest.mark.asyncio
async def test_sync_callback(emitter):
    """Test: Sync callbacks work correctly."""
    received = []

    def sync_callback(ctx: HookContext):
        received.append(ctx.event_type)

    emitter.register(sync_callback, [LifecycleEvent.ON_STEP])
    await emitter.emit(LifecycleEvent.ON_STEP)

    assert len(received) == 1
    assert received[0] == LifecycleEvent.ON_STEP


@pytest.mark.asyncio
async def test_unregister(emitter):
    """Test: Unregister removes callback."""
    received = []

    async def callback(ctx: HookContext):
        received.append(ctx)

    emitter.register(callback, [LifecycleEvent.ON_START])
    emitter.unregister(callback, [LifecycleEvent.ON_START])
    await emitter.emit(LifecycleEvent.ON_START)

    assert len(received) == 0


@pytest.mark.asyncio
async def test_error_in_callback_doesnt_break_emitter(emitter):
    """Verify that callback errors are logged but don't stop emission."""
    errors_received = []

    async def error_callback(ctx: HookContext):
        if ctx.event_type == LifecycleEvent.ON_ERROR:
            raise ValueError("Test error")

    async def ok_callback(ctx: HookContext):
        errors_received.append(ctx)

    emitter.register(error_callback, [LifecycleEvent.ON_ERROR])
    emitter.register(ok_callback, [LifecycleEvent.ON_ERROR])

    # Should not raise
    await emitter.emit(LifecycleEvent.ON_ERROR, metadata={"error": "test"})

    # OK callback should still have been called
    assert len(errors_received) == 1


def test_get_handlers(emitter):
    """Test: Get registered handlers for an event."""
    async def callback1(ctx: HookContext): pass
    async def callback2(ctx: HookContext): pass

    emitter.register(callback1, [LifecycleEvent.ON_STEP])
    emitter.register(callback2, [LifecycleEvent.ON_STEP])

    handlers = emitter.get_handlers(LifecycleEvent.ON_STEP)
    assert len(handlers) == 2


@pytest.mark.asyncio
async def test_context_timestamp_updated_on_emit(emitter):
    """Test: Context timestamp is updated when emit is called."""
    received = []

    async def callback(ctx: HookContext):
        received.append(ctx)

    emitter.register(callback, [LifecycleEvent.ON_INIT])
    await emitter.emit(LifecycleEvent.ON_INIT)

    assert len(received) == 1
    assert received[0].timestamp is not None


@pytest.mark.asyncio
async def test_context_overrides_kwargs(emitter):
    """Test: Explicit context overrides kwargs in emit."""
    received = []

    async def callback(ctx: HookContext):
        received.append(ctx)

    explicit_context = HookContext(
        agent_id="explicit-agent",
        event_type=LifecycleEvent.ON_START,
    )

    emitter.register(callback, [LifecycleEvent.ON_START])
    await emitter.emit(
        LifecycleEvent.ON_START,
        context=explicit_context,
        agent_id="should-be-ignored",
    )

    assert len(received) == 1
    assert received[0].agent_id == "explicit-agent"


@pytest.mark.asyncio
async def test_all_six_lifecycle_events_fire(emitter):
    """Test: All six lifecycle events can be emitted."""
    received = []

    async def callback(ctx: HookContext):
        received.append(ctx.event_type)

    emitter.register(callback, [
        LifecycleEvent.ON_INIT,
        LifecycleEvent.ON_START,
        LifecycleEvent.ON_STEP,
        LifecycleEvent.ON_COMPLETE,
        LifecycleEvent.ON_ERROR,
        LifecycleEvent.ON_EXIT,
    ])

    await emitter.emit(LifecycleEvent.ON_INIT)
    await emitter.emit(LifecycleEvent.ON_START)
    await emitter.emit(LifecycleEvent.ON_STEP)
    await emitter.emit(LifecycleEvent.ON_COMPLETE)
    await emitter.emit(LifecycleEvent.ON_ERROR)
    await emitter.emit(LifecycleEvent.ON_EXIT)

    assert len(received) == 6
    assert LifecycleEvent.ON_INIT in received
    assert LifecycleEvent.ON_START in received
    assert LifecycleEvent.ON_STEP in received
    assert LifecycleEvent.ON_COMPLETE in received
    assert LifecycleEvent.ON_ERROR in received
    assert LifecycleEvent.ON_EXIT in received


@pytest.mark.asyncio
async def test_multiple_callbacks_same_event(emitter):
    """Test: Multiple callbacks can be registered for same event."""
    received1 = []
    received2 = []

    async def callback1(ctx: HookContext):
        received1.append(ctx)

    async def callback2(ctx: HookContext):
        received2.append(ctx)

    emitter.register(callback1, [LifecycleEvent.ON_COMPLETE])
    emitter.register(callback2, [LifecycleEvent.ON_COMPLETE])
    await emitter.emit(LifecycleEvent.ON_COMPLETE)

    assert len(received1) == 1
    assert len(received2) == 1


@pytest.mark.asyncio
async def test_async_and_sync_mixed(emitter):
    """Test: Both async and sync callbacks work in same emitter."""
    async_received = []
    sync_received = []

    async def async_cb(ctx: HookContext):
        async_received.append(ctx.event_type)

    def sync_cb(ctx: HookContext):
        sync_received.append(ctx.event_type)

    emitter.register(async_cb, [LifecycleEvent.ON_STEP])
    emitter.register(sync_cb, [LifecycleEvent.ON_STEP])
    await emitter.emit(LifecycleEvent.ON_STEP)

    assert LifecycleEvent.ON_STEP in async_received
    assert LifecycleEvent.ON_STEP in sync_received
