from typing import AsyncIterator
import asyncio
from datetime import datetime
import uuid
import json

from luminamind.events.schema import AgentEvent, EventSubscription, ToolEvent, TokenEvent, ErrorEvent
from luminamind.events.buffer import EventBuffer


class SSEHandler:
    """Server-Sent Events handler for event streaming."""

    def __init__(self, event_buffer: 'EventBuffer'):
        self.event_buffer = event_buffer
        self._subscribers: dict[str, asyncio.Queue] = {}
        self._subscriptions: dict[str, EventSubscription] = {}

    async def add_subscriber(self, subscription: EventSubscription) -> str:
        """Add a new subscriber. Returns subscriber_id."""
        subscriber_id = str(uuid.uuid4())
        self._subscribers[subscriber_id] = asyncio.Queue()
        self._subscriptions[subscriber_id] = subscription
        return subscriber_id

    async def remove_subscriber(self, subscriber_id: str) -> None:
        """Remove a subscriber."""
        if subscriber_id in self._subscribers:
            del self._subscribers[subscriber_id]
        if subscriber_id in self._subscriptions:
            del self._subscriptions[subscriber_id]

    async def stream(self, subscriber_id: str) -> AsyncIterator[str]:
        """Yield SSE-formatted events for a subscriber.

        Format: data: {json_event}\n\n
        """
        if subscriber_id not in self._subscribers:
            return

        queue = self._subscribers[subscriber_id]
        subscription = self._subscriptions.get(subscriber_id)

        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30)
                # Format as SSE
                yield f"data: {json.dumps(self._event_to_dict(event), default=str)}\n\n"
            except asyncio.TimeoutError:
                # Send heartbeat
                yield f": heartbeat\n\n"
            except asyncio.CancelledError:
                break

    async def broadcast(self, event: AgentEvent) -> None:
        """Broadcast event to all matching subscribers."""
        for subscriber_id, subscription in self._subscriptions.items():
            if self._matches(subscription, event):
                if subscriber_id in self._subscribers:
                    await self._subscribers[subscriber_id].put(event)

    def _matches(self, subscription: EventSubscription, event: AgentEvent) -> bool:
        """Check if event matches subscription filter."""
        if subscription.session_id and event.session_id != subscription.session_id:
            return False
        if subscription.task_id and event.task_id != subscription.task_id:
            return False
        if subscription.agent_id and event.agent_id != subscription.agent_id:
            return False
        if subscription.event_types and event.event_type not in subscription.event_types:
            return False
        return True

    def _event_to_dict(self, event: AgentEvent | ToolEvent | TokenEvent | ErrorEvent) -> dict:
        """Convert event to dict for JSON serialization."""
        result = {}
        if isinstance(event, AgentEvent):
            result = {
                'event_id': event.event_id,
                'event_type': event.event_type.value if hasattr(event.event_type, 'value') else str(event.event_type),
                'agent_id': event.agent_id,
                'timestamp': event.timestamp.isoformat() if isinstance(event.timestamp, datetime) else str(event.timestamp),
                'data': event.data,
                'session_id': event.session_id,
                'task_id': event.task_id,
            }
        elif isinstance(event, ToolEvent):
            result = {
                'event_id': event.event_id,
                'event_type': 'tool_event',
                'agent_id': event.agent_id,
                'timestamp': event.timestamp.isoformat() if isinstance(event.timestamp, datetime) else str(event.timestamp),
                'tool_name': event.tool_name,
                'tool_input': event.tool_input,
                'tool_output': event.tool_output,
                'duration_ms': event.duration_ms,
                'session_id': event.session_id,
                'task_id': event.task_id,
                'error': event.error,
            }
        elif isinstance(event, TokenEvent):
            result = {
                'event_id': event.event_id,
                'event_type': 'token_event',
                'agent_id': event.agent_id,
                'timestamp': event.timestamp.isoformat() if isinstance(event.timestamp, datetime) else str(event.timestamp),
                'token': event.token,
                'token_type': event.token_type,
                'session_id': event.session_id,
                'task_id': event.task_id,
                'is_final': event.is_final,
            }
        elif isinstance(event, ErrorEvent):
            result = {
                'event_id': event.event_id,
                'event_type': 'error_event',
                'agent_id': event.agent_id,
                'timestamp': event.timestamp.isoformat() if isinstance(event.timestamp, datetime) else str(event.timestamp),
                'error_type': event.error_type,
                'error_message': event.error_message,
                'stack_trace': event.stack_trace,
                'session_id': event.session_id,
                'task_id': event.task_id,
                'recovered': event.recovered,
            }
        return result


class WebSocketHandler:
    """WebSocket handler for bidirectional event streaming."""

    def __init__(self, event_buffer: 'EventBuffer'):
        self.event_buffer = event_buffer
        self._connections: dict[str, tuple] = {}  # connection_id -> (websocket, subscription)
        self._counter = 0

    async def connect(self, websocket, subscription: EventSubscription) -> str:
        """Accept WebSocket connection with subscription."""
        self._counter += 1
        connection_id = f"ws_{self._counter}"
        self._connections[connection_id] = (websocket, subscription)
        return connection_id

    async def disconnect(self, connection_id: str) -> None:
        """Handle WebSocket disconnect."""
        if connection_id in self._connections:
            del self._connections[connection_id]

    async def send(self, connection_id: str, event: AgentEvent) -> None:
        """Send event to specific connection."""
        if connection_id not in self._connections:
            return
        websocket, _ = self._connections[connection_id]
        try:
            await websocket.send_json(self._event_to_dict(event))
        except Exception:
            pass

    async def broadcast(self, event: AgentEvent) -> None:
        """Broadcast to all connections."""
        for connection_id, (websocket, subscription) in self._connections.items():
            if self._matches(subscription, event):
                try:
                    await websocket.send_json(self._event_to_dict(event))
                except Exception:
                    pass

    def _matches(self, subscription: EventSubscription, event: AgentEvent) -> bool:
        """Check if event matches subscription filter."""
        if subscription.session_id and event.session_id != subscription.session_id:
            return False
        if subscription.task_id and event.task_id != subscription.task_id:
            return False
        if subscription.agent_id and event.agent_id != subscription.agent_id:
            return False
        if subscription.event_types and event.event_type not in subscription.event_types:
            return False
        return True

    def _event_to_dict(self, event: AgentEvent | ToolEvent | TokenEvent | ErrorEvent) -> dict:
        """Convert event to dict for JSON serialization."""
        result = {}
        if isinstance(event, AgentEvent):
            result = {
                'event_id': event.event_id,
                'event_type': event.event_type.value if hasattr(event.event_type, 'value') else str(event.event_type),
                'agent_id': event.agent_id,
                'timestamp': event.timestamp.isoformat() if isinstance(event.timestamp, datetime) else str(event.timestamp),
                'data': event.data,
                'session_id': event.session_id,
                'task_id': event.task_id,
            }
        elif isinstance(event, ToolEvent):
            result = {
                'event_id': event.event_id,
                'event_type': 'tool_event',
                'agent_id': event.agent_id,
                'timestamp': event.timestamp.isoformat() if isinstance(event.timestamp, datetime) else str(event.timestamp),
                'tool_name': event.tool_name,
                'tool_input': event.tool_input,
                'tool_output': event.tool_output,
                'duration_ms': event.duration_ms,
                'session_id': event.session_id,
                'task_id': event.task_id,
                'error': event.error,
            }
        elif isinstance(event, TokenEvent):
            result = {
                'event_id': event.event_id,
                'event_type': 'token_event',
                'agent_id': event.agent_id,
                'timestamp': event.timestamp.isoformat() if isinstance(event.timestamp, datetime) else str(event.timestamp),
                'token': event.token,
                'token_type': event.token_type,
                'session_id': event.session_id,
                'task_id': event.task_id,
                'is_final': event.is_final,
            }
        elif isinstance(event, ErrorEvent):
            result = {
                'event_id': event.event_id,
                'event_type': 'error_event',
                'agent_id': event.agent_id,
                'timestamp': event.timestamp.isoformat() if isinstance(event.timestamp, datetime) else str(event.timestamp),
                'error_type': event.error_type,
                'error_message': event.error_message,
                'stack_trace': event.stack_trace,
                'session_id': event.session_id,
                'task_id': event.task_id,
                'recovered': event.recovered,
            }
        return result


class EventStream:
    """Main event streaming service combining SSE and WebSocket."""

    def __init__(self, buffer_size: int = 10000):
        self.buffer = EventBuffer(max_size=buffer_size)
        self.sse = SSEHandler(self.buffer)
        self.websocket = WebSocketHandler(self.buffer)
        self._lock = asyncio.Lock()

    async def publish(self, event: AgentEvent | ToolEvent | TokenEvent | ErrorEvent) -> None:
        """Publish an event to all subscribers and buffer."""
        async with self._lock:
            # Add to buffer
            if isinstance(event, AgentEvent):
                self.buffer.append(event)
            # Broadcast to SSE subscribers
            await self.sse.broadcast(event)
            # Broadcast to WebSocket subscribers
            await self.websocket.broadcast(event)

    async def subscribe(self, subscription: EventSubscription, transport: str = "sse") -> str:
        """Create subscription. Returns subscription_id."""
        if transport == "sse":
            return await self.sse.add_subscriber(subscription)
        elif transport == "websocket":
            return str(uuid.uuid4())  # WebSocket uses connect/disconnect
        return ""

    async def unsubscribe(self, subscription_id: str) -> None:
        """Remove subscription."""
        await self.sse.remove_subscriber(subscription_id)

    def replay(self, session_id: str, from_event_id: str | None = None) -> list[AgentEvent]:
        """Get buffered events for replay."""
        return self.buffer.replay(session_id, from_event_id)