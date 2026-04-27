"""Tests for memory embeddings."""
import pytest
from luminamind.memory.embeddings import HashEmbeddingProvider, create_embedding_provider


@pytest.mark.asyncio
async def test_hash_embedding():
    provider = HashEmbeddingProvider()
    assert provider.dim() == 384
    embeddings = await provider.embed(["hello", "world"])
    assert len(embeddings) == 2
    assert len(embeddings[0]) == 384
    # Verify normalization
    import math
    assert math.isclose(math.sqrt(sum(x * x for x in embeddings[0])), 1.0, rel_tol=1e-5)


@pytest.mark.asyncio
async def test_hash_embedding_consistency():
    provider = HashEmbeddingProvider()
    e1 = await provider.embed(["test"])
    e2 = await provider.embed(["test"])
    assert e1[0] == e2[0]


def test_create_embedding_provider_fallback():
    provider = create_embedding_provider(provider="hash")
    assert isinstance(provider, HashEmbeddingProvider)
