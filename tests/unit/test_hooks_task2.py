"""Tests for Task 2: HookEmitter with registration and emission."""

import pytest
import asyncio
from luminamind.hooks import (
    HookEmitter,
    HookContext,
    LifecycleEvent,
)


@pytest.fixture
def emitter():
    return HookEmitter()


@pytest.mark.asyncio
async def test_register_callback_for_specific_event(emitter):
    """Test: Register callback for specific event."""
    received = []

    async def callback(ctx: HookContext):
        received.append(ctx)

    emitter.register(callback, [LifecycleEvent.ON_START])
    await emitter.emit(LifecycleEvent.ON_START, agent_id="test")

    assert len(received) == 1
    assert received[0].agent_id == "test"
    assert received[0].event_type == LifecycleEvent.ON_START


@pytest.mark.asyncio
async def test_register_callback_for_multiple_events(emitter):
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
async def test_emit_calls_all_registered_callbacks(emitter):
    """Test: Emit calls all registered callbacks."""
    received1 = []
    received2 = []

    async def callback1(ctx: HookContext):
        received1.append(ctx)

    async def callback2(ctx: HookContext):
        received2.append(ctx)

    emitter.register(callback1, [LifecycleEvent.ON_STEP])
    emitter.register(callback2, [LifecycleEvent.ON_STEP])
    await emitter.emit(LifecycleEvent.ON_STEP)

    assert len(received1) == 1
    assert len(received2) == 1


@pytest.mark.asyncio
async def test_callbacks_receive_correct_hook_context(emitter):
    """Test: Callbacks receive correct HookContext."""
    received = None

    async def callback(ctx: HookContext):
        nonlocal received
        received = ctx

    emitter.register(callback, [LifecycleEvent.ON_INIT])
    await emitter.emit(
        LifecycleEvent.ON_INIT,
        agent_id="my-agent",
        session_id="my-session",
        thread_id="my-thread",
        metadata={"key": "value"},
    )

    assert received is not None
    assert received.agent_id == "my-agent"
    assert received.session_id == "my-session"
    assert received.thread_id == "my-thread"
    assert received.metadata["key"] == "value"
    assert received.event_type == LifecycleEvent.ON_INIT


@pytest.mark.asyncio
async def test_async_callbacks_awaited_properly(emitter):
    """Test: Async callbacks awaited properly."""
    call_order = []

    async def async_callback(ctx: HookContext):
        call_order.append("async")

    def sync_callback(ctx: HookContext):
        call_order.append("sync")

    emitter.register(async_callback, [LifecycleEvent.ON_START])
    emitter.register(sync_callback, [LifecycleEvent.ON_START])
    await emitter.emit(LifecycleEvent.ON_START)

    assert "async" in call_order
    assert "sync" in call_order


@pytest.mark.asyncio
async def test_unregister_callback(emitter):
    """Test: Unregister removes callback."""
    received = []

    async def callback(ctx: HookContext):
        received.append(ctx)

    emitter.register(callback, [LifecycleEvent.ON_START])
    emitter.unregister(callback, [LifecycleEvent.ON_START])
    await emitter.emit(LifecycleEvent.ON_START)

    assert len(received) == 0


@pytest.mark.asyncio
async def test_unregister_from_multiple_events(emitter):
    """Test: Unregister from multiple events."""
    received = []

    async def callback(ctx: HookContext):
        received.append(ctx)

    emitter.register(callback, [LifecycleEvent.ON_START, LifecycleEvent.ON_COMPLETE])
    emitter.unregister(callback, [LifecycleEvent.ON_START])
    await emitter.emit(LifecycleEvent.ON_START)
    await emitter.emit(LifecycleEvent.ON_COMPLETE)

    assert len(received) == 1
    assert received[0].event_type == LifecycleEvent.ON_COMPLETE


@pytest.mark.asyncio
async def test_register_all_events_when_events_none(emitter):
    """Test: Register for all events when events param is None."""
    received = []

    async def callback(ctx: HookContext):
        received.append(ctx.event_type)

    emitter.register(callback, None)
    await emitter.emit(LifecycleEvent.ON_INIT)
    await emitter.emit(LifecycleEvent.ON_START)
    await emitter.emit(LifecycleEvent.ON_STEP)

    assert len(received) == 3


@pytest.mark.asyncio
async def test_get_handlers(emitter):
    """Test: Get registered handlers for an event."""
    async def callback1(ctx: HookContext): pass
    async def callback2(ctx: HookContext): pass

    emitter.register(callback1, [LifecycleEvent.ON_STEP])
    emitter.register(callback2, [LifecycleEvent.ON_STEP])

    handlers = emitter.get_handlers(LifecycleEvent.ON_STEP)
    assert len(handlers) == 2


def test_emitter_initializes_all_event_handlers():
    """Test: Emitter initializes empty handler list for all events."""
    emitter = HookEmitter()
    for event in LifecycleEvent:
        handlers = emitter.get_handlers(event)
        assert handlers == []
