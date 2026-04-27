import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import AsyncIterator, Optional
from enum import Enum
import uuid


class TokenType(Enum):
    TEXT = "text"
    THINKING = "thinking"  # Internal reasoning
    ACTION = "action"      # Tool execution
    OBSERVATION = "observation"  # Tool result
    METADATA = "metadata"   # Status updates


@dataclass
class StreamingConfig:
    """Configuration for token streaming."""
    buffer_size: int = 1000  # Tokens to buffer
    flush_interval_ms: int = 50  # How often to flush to client
    include_timestamps: bool = True
    include_token_types: bool = True
    max_token_length: int = 10000  # Max token size


@dataclass
class StreamToken:
    """A single token in the stream."""
    token_id: str
    token: str
    token_type: TokenType
    timestamp: datetime
    agent_id: str
    session_id: str
    task_id: Optional[str] = None
    is_final: bool = False
    metadata: dict = field(default_factory=dict)


class TokenStream:
    """Token-by-token streaming to clients via SSE."""

    def __init__(self, config: StreamingConfig = None):
        self.config = config or StreamingConfig()
        self._subscribers: dict[str, asyncio.Queue] = {}
        self._buffers: dict[str, list[StreamToken]] = {}
        self._flush_tasks: dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, session_id: str, task_id: str | None = None) -> str:
        """Subscribe to token stream. Returns subscription_id."""
        subscription_id = str(uuid.uuid4())
        self._subscribers[subscription_id] = asyncio.Queue(
            maxsize=self.config.buffer_size
        )
        self._buffers[subscription_id] = []
        return subscription_id

    async def unsubscribe(self, subscription_id: str) -> None:
        """Unsubscribe from stream."""
        if subscription_id in self._subscribers:
            del self._subscribers[subscription_id]
        if subscription_id in self._buffers:
            del self._buffers[subscription_id]
        if subscription_id in self._flush_tasks:
            self._flush_tasks[subscription_id].cancel()
            del self._flush_tasks[subscription_id]

    async def emit(self, token: str, token_type: TokenType, agent_id: str,
                   session_id: str, task_id: str | None = None,
                   metadata: dict = None) -> None:
        """Emit a token to all subscribers."""
        stream_token = StreamToken(
            token_id=str(uuid.uuid4()),
            token=token[:self.config.max_token_length],
            token_type=token_type,
            timestamp=datetime.utcnow(),
            agent_id=agent_id,
            session_id=session_id,
            task_id=task_id,
            metadata=metadata or {}
        )

        async with self._lock:
            for subscription_id in self._subscribers:
                try:
                    self._subscribers[subscription_id].put_nowait(stream_token)
                except asyncio.QueueFull:
                    pass  # Buffer full, skip

    async def stream_tokens(self, subscription_id: str) -> AsyncIterator[str]:
        """Yield SSE-formatted token data.

        Format: data: {"token": "...", "type": "...", "timestamp": "..."}\n\n
        """
        if subscription_id not in self._subscribers:
            return

        import json
        queue = self._subscribers[subscription_id]

        while True:
            try:
                token = await asyncio.wait_for(queue.get(), timeout=30)
                data = {
                    "token": token.token,
                    "type": token.token_type.value,
                    "timestamp": token.timestamp.isoformat(),
                    "token_id": token.token_id,
                    "agent_id": token.agent_id,
                    "session_id": token.session_id,
                    "task_id": token.task_id,
                    "is_final": token.is_final,
                    "metadata": token.metadata
                }
                yield f"data: {json.dumps(data, default=str)}\n\n"
            except asyncio.TimeoutError:
                # Send heartbeat to keep connection alive
                yield f"data: {json.dumps({'event': 'heartbeat'})}\n\n"

    async def flush_buffer(self, subscription_id: str) -> None:
        """Flush buffered tokens to subscriber."""
        if subscription_id not in self._buffers:
            return

        buffer = self._buffers[subscription_id]
        self._buffers[subscription_id] = []

        for token in buffer:
            if subscription_id in self._subscribers:
                try:
                    self._subscribers[subscription_id].put_nowait(token)
                except asyncio.QueueFull:
                    pass

    def get_stats(self, subscription_id: str) -> dict:
        """Get streaming stats for subscription."""
        return {
            'tokens_sent': len(self._buffers.get(subscription_id, [])),
            'subscriber_count': len(self._subscribers)
        }