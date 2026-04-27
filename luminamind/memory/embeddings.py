"""Embedding providers for vector memory.

Supports OpenAI, local sentence-transformers fallback, and a simple
hash-based fallback for environments without either.
"""
from __future__ import annotations

import asyncio
import hashlib
import os
from abc import ABC, abstractmethod
from typing import Any, Optional

import numpy as np


class EmbeddingProvider(ABC):
    """Abstract base for embedding providers."""

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts into dense vectors."""

    @abstractmethod
    def dim(self) -> int:
        """Return the embedding dimension."""


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI text-embedding-3-small / 3-large provider."""

    def __init__(self, model: str = "text-embedding-3-small", api_key: str | None = None, base_url: str | None = None) -> None:
        self.model = model
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY") or os.environ.get("GLM_API_KEY")
        self.base_url = base_url or os.environ.get("GLM_API_BASE")
        self._client: Any = None
        self._dim = 1536 if "small" in model else 3072

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from openai import AsyncOpenAI
            except ImportError as exc:
                raise ImportError("openai package required for OpenAIEmbeddingProvider") from exc
            self._client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        return self._client

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        client = self._get_client()
        response = await client.embeddings.create(model=self.model, input=texts)
        return [item.embedding for item in response.data]

    def dim(self) -> int:
        return self._dim


class LocalEmbeddingProvider(EmbeddingProvider):
    """Lightweight local embedding using sentence-transformers (CPU)."""

    def __init__(self, model: str = "all-MiniLM-L6-v2") -> None:
        self.model_name = model
        self._model: Any = None
        self._dim_cache: int | None = None

    def _get_model(self) -> Any:
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise ImportError(
                    "sentence-transformers required for LocalEmbeddingProvider. "
                    "Install with: pip install sentence-transformers"
                ) from exc
            self._model = SentenceTransformer(self.model_name)
        return self._model

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        model = self._get_model()
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(None, model.encode, texts)
        return [e.tolist() for e in embeddings]

    def dim(self) -> int:
        if self._dim_cache is None:
            self._dim_cache = self._get_model().get_sentence_embedding_dimension()
        return self._dim_cache


class HashEmbeddingProvider(EmbeddingProvider):
    """Deterministic hash-based embedding fallback (no ML deps).

    Produces normalized 384-dim vectors from SHA-256 hashes.
    Not semantically meaningful, but supports exact/near-exact retrieval.
    """

    DIM = 384

    async def embed(self, texts: list[str]) -> list[list[float]]:
        results: list[list[float]] = []
        for text in texts:
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            # Expand 32 bytes to 384 dims by treating each byte as 12 floats
            # via a simple linear congruential generator seeded by the byte
            vec = np.zeros(self.DIM, dtype=np.float32)
            for i in range(self.DIM):
                seed_byte = digest[i % len(digest)]
                # Simple pseudo-random expansion
                val = ((seed_byte * 9301 + 49297 + i * 233280) % 256) / 128.0 - 1.0
                vec[i] = val
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec = vec / norm
            results.append(vec.tolist())
        return results

    def dim(self) -> int:
        return self.DIM


def create_embedding_provider(
    provider: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
) -> EmbeddingProvider:
    """Factory for embedding providers with graceful fallback.

    Priority: openai -> local -> hash
    """
    provider = (provider or os.environ.get("EMBEDDING_PROVIDER", "auto")).lower()

    if provider == "openai":
        return OpenAIEmbeddingProvider(
            model=model or "text-embedding-3-small", api_key=api_key, base_url=base_url
        )

    if provider == "local":
        return LocalEmbeddingProvider(model=model or "all-MiniLM-L6-v2")

    if provider == "hash":
        return HashEmbeddingProvider()

    # Auto-detect
    if os.environ.get("OPENAI_API_KEY") or os.environ.get("GLM_API_KEY"):
        try:
            return OpenAIEmbeddingProvider(
                model=model or "text-embedding-3-small", api_key=api_key, base_url=base_url
            )
        except ImportError:
            pass

    try:
        return LocalEmbeddingProvider(model=model or "all-MiniLM-L6-v2")
    except ImportError:
        pass

    return HashEmbeddingProvider()
