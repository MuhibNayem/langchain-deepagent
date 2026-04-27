"""Tests for Task 1: LifecycleEvent enum and HookContext dataclass."""

import pytest
from luminamind.hooks import (
    LifecycleEvent,
    HookContext,
)


def test_lifecycle_event_enum():
    """Test: LifecycleEvent enum has all required events."""
    assert hasattr(LifecycleEvent, 'ON_INIT')
    assert hasattr(LifecycleEvent, 'ON_START')
    assert hasattr(LifecycleEvent, 'ON_STEP')
    assert hasattr(LifecycleEvent, 'ON_COMPLETE')
    assert hasattr(LifecycleEvent, 'ON_ERROR')
    assert hasattr(LifecycleEvent, 'ON_EXIT')


def test_lifecycle_event_values():
    """Test: LifecycleEvent enum has correct string values."""
    assert LifecycleEvent.ON_INIT.value == "on_init"
    assert LifecycleEvent.ON_START.value == "on_start"
    assert LifecycleEvent.ON_STEP.value == "on_step"
    assert LifecycleEvent.ON_COMPLETE.value == "on_complete"
    assert LifecycleEvent.ON_ERROR.value == "on_error"
    assert LifecycleEvent.ON_EXIT.value == "on_exit"


def test_hook_context_fields():
    """Test: HookContext includes agent_id, session_id, event_type, timestamp."""
    ctx = HookContext(
        agent_id="agent-1",
        session_id="session-1",
        thread_id="thread-1",
        event_type=LifecycleEvent.ON_START,
    )
    assert ctx.agent_id == "agent-1"
    assert ctx.session_id == "session-1"
    assert ctx.thread_id == "thread-1"
    assert ctx.event_type == LifecycleEvent.ON_START
    assert ctx.timestamp is not None


def test_hook_context_metadata_dict():
    """Test: HookContext includes additional metadata dict."""
    ctx = HookContext(
        event_type=LifecycleEvent.ON_ERROR,
        metadata={"error": "Timeout", "retry_count": 3},
    )
    assert ctx.metadata["error"] == "Timeout"
    assert ctx.metadata["retry_count"] == 3
    assert isinstance(ctx.metadata, dict)


def test_hook_context_defaults():
    """Test: HookContext has appropriate defaults."""
    ctx = HookContext(event_type=LifecycleEvent.ON_INIT)
    assert ctx.agent_id is None
    assert ctx.session_id is None
    assert ctx.thread_id is None
    assert ctx.timestamp is not None
    assert ctx.metadata == {}
