"""A2A server wrapper for LuminaMind agents.

Mounts JSON-RPC endpoints onto a FastAPI app so other A2A agents
can discover and communicate with this harness.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from luminamind.a2a.types import AgentCard, Message, Task, TaskState


class A2AServer:
    """A2A server exposing LuminaMind as an interoperable agent."""

    def __init__(self, agent_card: AgentCard) -> None:
        self.card = agent_card
        self._tasks: dict[str, Task] = {}
        self.router = APIRouter(prefix="/a2a")
        self._setup_routes()

    def _setup_routes(self) -> None:
        @self.router.get("/agent.json")
        async def agent_card() -> dict[str, Any]:
            return self.card.to_dict()

        @self.router.post("/")
        async def rpc_handler(request: Request) -> JSONResponse:
            body = await request.json()
            method = body.get("method", "")
            params = body.get("params", {})
            req_id = body.get("id", "")
            try:
                result = await self._dispatch(method, params)
                return JSONResponse({"jsonrpc": "2.0", "id": req_id, "result": result})
            except Exception as exc:
                return JSONResponse(
                    {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {"code": -32603, "message": str(exc)},
                    },
                    status_code=500,
                )

    async def _dispatch(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        if method == "tasks/send":
            return await self._handle_send(params)
        elif method == "tasks/get":
            return await self._handle_get(params)
        elif method == "tasks/cancel":
            return await self._handle_cancel(params)
        elif method == "tasks/sendSubscribe":
            raise NotImplementedError("Streaming not supported in base server")
        else:
            raise ValueError(f"Unknown method: {method}")

    async def _handle_send(self, params: dict[str, Any]) -> dict[str, Any]:
        task_id = params["id"]
        message = Message.from_dict(params["message"])
        task = Task(id=task_id, state=TaskState.WORKING, messages=[message])
        self._tasks[task_id] = task
        # TODO: integrate with actual DeepAgent execution
        # For now, mark as completed with echo response
        task.state = TaskState.COMPLETED
        task.messages.append(
            Message(role="agent", parts=[{"type": "text", "text": f"Echo: {message.parts[0].text if message.parts else ''}"}])
        )
        return task.to_dict()

    async def _handle_get(self, params: dict[str, Any]) -> dict[str, Any]:
        task_id = params["id"]
        task = self._tasks.get(task_id)
        if task is None:
            raise ValueError(f"Task not found: {task_id}")
        return task.to_dict()

    async def _handle_cancel(self, params: dict[str, Any]) -> dict[str, Any]:
        task_id = params["id"]
        task = self._tasks.get(task_id)
        if task is None:
            raise ValueError(f"Task not found: {task_id}")
        task.state = TaskState.CANCELED
        return task.to_dict()


def create_a2a_server(
    name: str = "LuminaMind Agent",
    description: str = "Enterprise deep autonomy agent harness",
    base_url: str = "http://localhost:8000",
) -> A2AServer:
    """Factory to create an A2A server for this harness."""
    card = AgentCard(
        name=name,
        description=description,
        url=f"{base_url.rstrip('/')}/a2a/",
        capabilities={"streaming": False, "pushNotifications": False},
        skills=[
            {
                "id": "code-analysis",
                "name": "Code Analysis",
                "description": "Analyze and refactor codebases",
                "tags": ["code", "analysis"],
            },
            {
                "id": "web-research",
                "name": "Web Research",
                "description": "Research topics using web search and crawling",
                "tags": ["research", "web"],
            },
        ],
    )
    return A2AServer(card)
