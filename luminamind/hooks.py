"""Lifecycle hooks for agent observability and extension.

This module provides a hook system that fires callbacks on agent lifecycle events:
on_init, on_start, on_step, on_complete, on_error, on_exit.

Purpose: Enable observability, debugging, and extension of agent behavior at key
lifecycle points.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Callable

from pydantic import BaseModel, ConfigDict, Field


class HookContext(BaseModel):
    """Context passed to hook callbacks."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    agent_id: str | None = None
    session_id: str | None = None
    thread_id: str | None = None
    event_type: LifecycleEvent
    timestamp: datetime = Field(default_factory=lambda: datetime.now())
    metadata: dict[str, Any] = Field(default_factory=dict)


# Type alias for hook callbacks
HookCallback = Annotated[
    Callable[[HookContext], Any],
    "Async or sync callback that receives HookContext",
]


class HookEmitter:
    """Emit lifecycle events to registered callbacks."""

    def __init__(self) -> None:
        self._handlers: dict[LifecycleEvent, list[HookCallback]] = {
            event: [] for event in LifecycleEvent
        }

    def register(
        self,
        callback: HookCallback,
        events: list[LifecycleEvent] | None = None,
    ) -> None:
        """Register a callback for specific events or all events.

        Args:
            callback: Function taking HookContext, returns anything
            events: List of events to register for, or None for all
        """
        if events is None:
            events = list(LifecycleEvent)

        for event in events:
            if callback not in self._handlers[event]:
                self._handlers[event].append(callback)

    def unregister(
        self,
        callback: HookCallback,
        events: list[LifecycleEvent] | None = None,
    ) -> None:
        """Unregister a callback."""
        if events is None:
            events = list(LifecycleEvent)

        for event in events:
            if callback in self._handlers[event]:
                self._handlers[event].remove(callback)

    async def emit(
        self,
        event: LifecycleEvent,
        context: HookContext | None = None,
        **kwargs: Any,
    ) -> None:
        """Emit an event to all registered callbacks.

        Args:
            event: The lifecycle event
            context: HookContext (created from kwargs if not provided)
            **kwargs: Fields to include in HookContext
        """
        if context is None:
            context = HookContext(event_type=event, **kwargs)
        else:
            context.event_type = event

        context.timestamp = datetime.utcnow()

        for callback in self._handlers[event]:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(context)
                else:
                    callback(context)
            except Exception as e:
                # Log but don't fail - hooks shouldn't break agent
                import logging

                logging.getLogger(__name__).warning(f"Hook callback error for {event}: {e}")

    def get_handlers(self, event: LifecycleEvent) -> list[HookCallback]:
        """Get registered handlers for an event."""
        return list(self._handlers[event])


# Module-level singleton
_emitter = HookEmitter()


# Convenience decorators
def on_init(callback: HookCallback) -> HookCallback:
    """Decorator to register on_init hook."""
    _emitter.register(callback, [LifecycleEvent.ON_INIT])
    return callback


def on_start(callback: HookCallback) -> HookCallback:
    """Decorator to register on_start hook."""
    _emitter.register(callback, [LifecycleEvent.ON_START])
    return callback


def on_step(callback: HookCallback) -> HookCallback:
    """Decorator to register on_step hook."""
    _emitter.register(callback, [LifecycleEvent.ON_STEP])
    return callback


def on_complete(callback: HookCallback) -> HookCallback:
    """Decorator to register on_complete hook."""
    _emitter.register(callback, [LifecycleEvent.ON_COMPLETE])
    return callback


def on_error(callback: HookCallback) -> HookCallback:
    """Decorator to register on_error hook."""
    _emitter.register(callback, [LifecycleEvent.ON_ERROR])
    return callback


def on_exit(callback: HookCallback) -> HookCallback:
    """Decorator to register on_exit hook."""
    _emitter.register(callback, [LifecycleEvent.ON_EXIT])
    return callback


def get_emitter() -> HookEmitter:
    """Get the global hook emitter."""
    return _emitter


# Example hooks - can be used as reference implementation

async def log_hook(context: HookContext) -> None:
    """Example: Log all lifecycle events."""
    import logging

    logger = logging.getLogger(__name__)
    extra = {
        "agent_id": context.agent_id,
        "session_id": context.session_id,
        "event": context.event_type.value,
    }
    logger.info(f"Lifecycle event: {context.event_type.value}", extra=extra)


_step_counts: dict[str, int] = {}


def step_counter_hook(context: HookContext) -> None:
    """Example: Count steps per session."""
    if context.event_type == LifecycleEvent.ON_STEP:
        _step_counts[context.session_id] = _step_counts.get(context.session_id, 0) + 1


def get_step_count(session_id: str) -> int:
    """Get step count for a session."""
    return _step_counts.get(session_id, 0)


async def error_logger_hook(context: HookContext) -> None:
    """Example: Log errors with full context."""
    if context.event_type == LifecycleEvent.ON_ERROR:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(
            f"Agent error in session {context.session_id}: {context.metadata.get('error')}",
            extra={"context": context.metadata},
        )


async def metrics_hook(context: HookContext) -> None:
    """Example: Emit metrics for each event."""
    if context.event_type == LifecycleEvent.ON_COMPLETE:
        # Would emit to Prometheus in real implementation
        pass
