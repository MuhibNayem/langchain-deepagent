"""Enterprise memory manager with dual-layer architecture.

- Hot path: recent conversation turns in context window
- Cold path: vector store for semantic retrieval across sessions

Supports episodic, semantic, and procedural memory with
multi-scope isolation (user_id, agent_id, thread_id).
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from luminamind.memory.embeddings import EmbeddingProvider, create_embedding_provider
from luminamind.memory.vector_store import InMemoryVectorStore, MemoryRecord


DEFAULT_MEMORY_ROOT = Path.home() / ".luminamind" / "memory"


class MemoryScope:
    """Namespace keys for memory isolation."""

    def __init__(
        self,
        user_id: str | None = None,
        agent_id: str | None = None,
        thread_id: str | None = None,
    ) -> None:
        self.user_id = user_id or "default"
        self.agent_id = agent_id or "default"
        self.thread_id = thread_id or "global"

    def to_tuple(self) -> tuple[str, str, str]:
        return (self.user_id, self.agent_id, self.thread_id)

    def to_dict(self) -> dict[str, str]:
        return {
            "user_id": self.user_id,
            "agent_id": self.agent_id,
            "thread_id": self.thread_id,
        }


class MemoryManager:
    """Central memory orchestrator for the agent harness."""

    def __init__(
        self,
        provider: EmbeddingProvider | None = None,
        root_dir: Path | None = None,
    ) -> None:
        self.provider = provider or create_embedding_provider()
        self.root = root_dir or Path(os.environ.get("LUMINAMIND_MEMORY_ROOT", str(DEFAULT_MEMORY_ROOT)))
        self.root.mkdir(parents=True, exist_ok=True)
        self._store: InMemoryVectorStore | None = None
        self._loaded = False

    def _store_path(self) -> Path:
        return self.root / "vector_store.json"

    def _load(self) -> None:
        if self._loaded:
            return
        path = self._store_path()
        if path.exists():
            try:
                self._store = InMemoryVectorStore.load(path)
            except Exception:
                self._store = InMemoryVectorStore(dim=self.provider.dim())
        else:
            self._store = InMemoryVectorStore(dim=self.provider.dim())
        self._loaded = True

    def _save(self) -> None:
        if self._store is not None:
            self._store.persist(self._store_path())

    async def add_memory(
        self,
        text: str,
        memory_type: str = "episodic",
        scope: MemoryScope | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Add a memory entry and embed it.

        Args:
            text: The content to remember.
            memory_type: episodic | semantic | procedural
            scope: Namespace isolation scope.
            metadata: Arbitrary metadata.

        Returns:
            The memory record ID.
        """
        self._load()
        assert self._store is not None
        scope = scope or MemoryScope()
        embeddings = await self.provider.embed([text])
        record_id = str(uuid.uuid4())
        record = MemoryRecord(
            id=record_id,
            text=text,
            embedding=embeddings[0],
            namespace=scope.to_tuple(),
            metadata={
                "memory_type": memory_type,
                "created_at": datetime.now(timezone.utc).isoformat(),
                **(metadata or {}),
                **scope.to_dict(),
            },
        )
        self._store.add(record)
        self._save()
        return record_id

    async def search(
        self,
        query: str,
        k: int = 5,
        scope: MemoryScope | None = None,
        memory_type: str | None = None,
    ) -> list[MemoryRecord]:
        """Semantic search over memories.

        Args:
            query: Search query text.
            k: Number of results.
            scope: Optional namespace filter.
            memory_type: Filter by memory type.

        Returns:
            List of memory records sorted by relevance.
        """
        self._load()
        if self._store is None or self._store._matrix.shape[0] == 0:
            return []
        embeddings = await self.provider.embed([query])
        filter_meta = {}
        if memory_type:
            filter_meta["memory_type"] = memory_type
        ns = scope.to_tuple() if scope else None
        return self._store.search(embeddings[0], k=k, namespace=ns, filter_meta=filter_meta or None)

    async def search_sessions(
        self,
        query: str,
        k: int = 5,
        user_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search across all sessions for a user and return formatted results."""
        scope = MemoryScope(user_id=user_id, thread_id="global")
        results = await self.search(query, k=k, scope=scope)
        return [
            {
                "id": r.id,
                "text": r.text,
                "score": r.score,
                "thread_id": r.metadata.get("thread_id"),
                "memory_type": r.metadata.get("memory_type"),
                "created_at": r.metadata.get("created_at"),
            }
            for r in results
        ]

    def delete_memory(self, record_id: str) -> bool:
        self._load()
        if self._store is None:
            return False
        ok = self._store.delete(record_id)
        if ok:
            self._save()
        return ok

    def stats(self) -> dict[str, Any]:
        self._load()
        if self._store is None:
            return {"total_memories": 0, "dim": self.provider.dim()}
        types: dict[str, int] = {}
        for r in self._store._records.values():
            mt = r.metadata.get("memory_type", "unknown")
            types[mt] = types.get(mt, 0) + 1
        return {
            "total_memories": len(self._store._records),
            "dim": self._store.dim,
            "provider_dim": self.provider.dim(),
            "by_type": types,
        }


# Singleton accessor
_manager: MemoryManager | None = None


def get_memory_manager() -> MemoryManager:
    global _manager
    if _manager is None:
        _manager = MemoryManager()
    return _manager
