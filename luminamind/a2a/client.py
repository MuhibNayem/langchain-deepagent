"""A2A client for communicating with remote agents.

Uses JSON-RPC 2.0 over HTTP(S) as per the A2A protocol spec.
"""
from __future__ import annotations

import asyncio
from typing import Any

import httpx

from luminamind.a2a.types import AgentCard, Message, Task, TaskState


class A2AClient:
    """Client for A2A protocol communication."""

    def __init__(self, agent_card: AgentCard, timeout: float = 60.0) -> None:
        self.card = agent_card
        self.timeout = timeout
        self._client = httpx.AsyncClient(timeout=timeout)

    async def close(self) -> None:
        await self._client.aclose()

    async def send_task(self, task_id: str, message: Message) -> Task:
        """Send a task to the agent."""
        payload = {
            "jsonrpc": "2.0",
            "id": task_id,
            "method": "tasks/send",
            "params": {
                "id": task_id,
                "message": message.to_dict(),
            },
        }
        response = await self._client.post(self.card.url, json=payload)
        response.raise_for_status()
        data = response.json()
        if "error" in data:
            raise A2AError(data["error"].get("message", "Unknown A2A error"), data["error"])
        return Task.from_dict(data["result"])

    async def send_subscribe(self, task_id: str, message: Message) -> Any:
        """Subscribe to streaming task updates via SSE."""
        payload = {
            "jsonrpc": "2.0",
            "id": task_id,
            "method": "tasks/sendSubscribe",
            "params": {
                "id": task_id,
                "message": message.to_dict(),
            },
        }
        async with self._client.stream("POST", self.card.url, json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data:"):
                    yield line[5:].strip()

    async def get_task(self, task_id: str) -> Task:
        """Get current task state."""
        payload = {
            "jsonrpc": "2.0",
            "id": task_id,
            "method": "tasks/get",
            "params": {"id": task_id},
        }
        response = await self._client.post(self.card.url, json=payload)
        response.raise_for_status()
        data = response.json()
        if "error" in data:
            raise A2AError(data["error"].get("message", "Unknown A2A error"), data["error"])
        return Task.from_dict(data["result"])

    async def cancel_task(self, task_id: str) -> Task:
        """Cancel a running task."""
        payload = {
            "jsonrpc": "2.0",
            "id": task_id,
            "method": "tasks/cancel",
            "params": {"id": task_id},
        }
        response = await self._client.post(self.card.url, json=payload)
        response.raise_for_status()
        data = response.json()
        if "error" in data:
            raise A2AError(data["error"].get("message", "Unknown A2A error"), data["error"])
        return Task.from_dict(data["result"])

    async def send_push_notification(self, task_id: str, notification: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "jsonrpc": "2.0",
            "id": task_id,
            "method": "tasks/pushNotification/set",
            "params": {"id": task_id, "notification": notification},
        }
        response = await self._client.post(self.card.url, json=payload)
        response.raise_for_status()
        data = response.json()
        if "error" in data:
            raise A2AError(data["error"].get("message", "Unknown A2A error"), data["error"])
        return data["result"]


class A2AError(Exception):
    """A2A protocol error."""

    def __init__(self, message: str, error_data: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.error_data = error_data or {}
