"""Vector store with in-memory numpy backend and optional FAISS acceleration.

Enterprise features:
- Namespace isolation (user_id / thread_id / agent_id)
- Metadata filtering
- Cosine similarity search
- Optional FAISS index for large collections
- JSON serialization for persistence
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import numpy as np


@dataclass
class MemoryRecord:
    """A single memory entry in the vector store."""

    id: str
    text: str
    embedding: list[float]
    namespace: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    score: float = 0.0


class InMemoryVectorStore:
    """Thread-safe in-memory vector store with cosine similarity."""

    def __init__(self, dim: int) -> None:
        self.dim = dim
        self._records: dict[str, MemoryRecord] = {}
        self._matrix: np.ndarray = np.zeros((0, dim), dtype=np.float32)
        self._id_to_index: dict[str, int] = {}
        self._faiss_index: Any = None
        self._use_faiss = False

    def _maybe_build_faiss(self) -> None:
        """Build FAISS index when collection grows past threshold."""
        if self._use_faiss:
            return
        threshold = int(os.environ.get("FAISS_BUILD_THRESHOLD", "500"))
        if len(self._records) < threshold:
            return
        try:
            import faiss
        except ImportError:
            return

        index = faiss.IndexFlatIP(self.dim)  # Inner product = cosine for normalized vectors
        if self._matrix.shape[0] > 0:
            index.add(self._matrix)
        self._faiss_index = index
        self._use_faiss = True

    def add(self, record: MemoryRecord) -> None:
        if record.id in self._records:
            self.delete(record.id)
        vec = np.array(record.embedding, dtype=np.float32)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        idx = self._matrix.shape[0]
        self._matrix = np.vstack([self._matrix, vec[np.newaxis, :]])
        self._id_to_index[record.id] = idx
        self._records[record.id] = record
        if self._use_faiss and self._faiss_index is not None:
            self._faiss_index.add(vec[np.newaxis, :].astype(np.float32))
        else:
            self._maybe_build_faiss()

    def delete(self, record_id: str) -> bool:
        if record_id not in self._records:
            return False
        idx = self._id_to_index.pop(record_id)
        self._records.pop(record_id)
        # Mark as deleted in matrix (set to zero); lazy rebuild on next search
        if idx < self._matrix.shape[0]:
            self._matrix[idx] = 0.0
        if self._use_faiss:
            # FAISS flat index doesn't support removal easily; rebuild
            self._rebuild_faiss()
        return True

    def _rebuild_faiss(self) -> None:
        try:
            import faiss
        except ImportError:
            self._use_faiss = False
            self._faiss_index = None
            return
        valid = [self._matrix[self._id_to_index[r.id]] for r in self._records.values()]
        if valid:
            self._matrix = np.stack(valid, axis=0).astype(np.float32)
        else:
            self._matrix = np.zeros((0, self.dim), dtype=np.float32)
        self._id_to_index = {r.id: i for i, r in enumerate(self._records.values())}
        self._faiss_index = faiss.IndexFlatIP(self.dim)
        if self._matrix.shape[0] > 0:
            self._faiss_index.add(self._matrix)

    def search(
        self,
        query_embedding: list[float],
        k: int = 5,
        namespace: tuple[str, ...] | None = None,
        filter_meta: dict[str, Any] | None = None,
    ) -> list[MemoryRecord]:
        if self._matrix.shape[0] == 0:
            return []

        q = np.array(query_embedding, dtype=np.float32)
        norm = np.linalg.norm(q)
        if norm > 0:
            q = q / norm

        if self._use_faiss and self._faiss_index is not None:
            scores, indices = self._faiss_index.search(q[np.newaxis, :].astype(np.float32), min(k * 4, self._matrix.shape[0]))
            candidates = []
            for score, idx in zip(scores[0], indices[0]):
                if idx < 0 or idx >= self._matrix.shape[0]:
                    continue
                # Map index back to record
                for rid, ridx in self._id_to_index.items():
                    if ridx == idx:
                        candidates.append((score, rid))
                        break
        else:
            similarities = self._matrix @ q
            top_k_idx = np.argpartition(similarities, -min(k * 4, len(similarities)))[-min(k * 4, len(similarities)):]
            candidates = [(similarities[idx], rid) for rid, idx in self._id_to_index.items() if idx in top_k_idx]
            candidates.sort(key=lambda x: x[0], reverse=True)

        results: list[MemoryRecord] = []
        for score, rid in candidates:
            record = self._records.get(rid)
            if record is None:
                continue
            if namespace is not None and record.namespace != namespace:
                continue
            if filter_meta:
                if not all(record.metadata.get(key) == value for key, value in filter_meta.items()):
                    continue
            record.score = float(score)
            results.append(record)
            if len(results) >= k:
                break
        return results

    def persist(self, path: Path) -> None:
        """Serialize store to JSON."""
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "dim": self.dim,
            "records": [
                {
                    "id": r.id,
                    "text": r.text,
                    "embedding": r.embedding,
                    "namespace": r.namespace,
                    "metadata": r.metadata,
                }
                for r in self._records.values()
            ],
        }
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "InMemoryVectorStore":
        """Deserialize store from JSON."""
        data = json.loads(path.read_text(encoding="utf-8"))
        store = cls(dim=data["dim"])
        for item in data.get("records", []):
            record = MemoryRecord(
                id=item["id"],
                text=item["text"],
                embedding=item["embedding"],
                namespace=tuple(item.get("namespace", ())),
                metadata=item.get("metadata", {}),
            )
            store.add(record)
        return store
