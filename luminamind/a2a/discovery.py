"""Agent discovery for A2A protocol.

Supports well-known URL discovery (`/.well-known/agent.json`)
and registry-based lookups.
"""
from __future__ import annotations

import json
from typing import Any

import httpx

from luminamind.a2a.types import AgentCard


class AgentDiscovery:
    """Discover A2A agents via well-known URLs and registries."""

    def __init__(self, timeout: float = 10.0) -> None:
        self.timeout = timeout

    async def discover(self, base_url: str) -> AgentCard | None:
        """Discover an agent at a base URL via well-known endpoint."""
        well_known = f"{base_url.rstrip('/')}/.well-known/agent.json"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(well_known)
                response.raise_for_status()
                data = response.json()
                return AgentCard.from_dict(data)
            except Exception:
                # Fallback: try /a2a/agent.json
                fallback = f"{base_url.rstrip('/')}/a2a/agent.json"
                try:
                    response = await client.get(fallback)
                    response.raise_for_status()
                    return AgentCard.from_dict(response.json())
                except Exception:
                    return None

    async def register_with_registry(
        self,
        registry_url: str,
        agent_card: AgentCard,
        api_key: str | None = None,
    ) -> bool:
        """Register an agent card with an external registry."""
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{registry_url.rstrip('/')}/agents",
                    json=agent_card.to_dict(),
                    headers=headers,
                )
                return response.status_code in {200, 201}
            except Exception:
                return False

    async def search_registry(
        self,
        registry_url: str,
        query: str,
        api_key: str | None = None,
    ) -> list[AgentCard]:
        """Search an agent registry."""
        headers: dict[str, str] = {}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(
                    f"{registry_url.rstrip('/')}/agents/search",
                    params={"q": query},
                    headers=headers,
                )
                response.raise_for_status()
                data = response.json()
                return [AgentCard.from_dict(a) for a in data.get("agents", [])]
            except Exception:
                return []
