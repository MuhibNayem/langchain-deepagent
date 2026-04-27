"""Tests for in-memory vector store."""
import pytest
from luminamind.memory.vector_store import InMemoryVectorStore, MemoryRecord


@pytest.fixture
def store():
    return InMemoryVectorStore(dim=3)


def test_add_and_search(store):
    r1 = MemoryRecord(id="a", text="hello world", embedding=[1.0, 0.0, 0.0])
    r2 = MemoryRecord(id="b", text="goodbye world", embedding=[0.0, 1.0, 0.0])
    store.add(r1)
    store.add(r2)
    results = store.search([1.0, 0.0, 0.0], k=1)
    assert len(results) == 1
    assert results[0].id == "a"
    assert results[0].score > 0.99


def test_namespace_filter(store):
    r1 = MemoryRecord(id="a", text="hello", embedding=[1.0, 0.0, 0.0], namespace=("user1",))
    r2 = MemoryRecord(id="b", text="hello", embedding=[1.0, 0.0, 0.0], namespace=("user2",))
    store.add(r1)
    store.add(r2)
    results = store.search([1.0, 0.0, 0.0], k=2, namespace=("user1",))
    assert len(results) == 1
    assert results[0].id == "a"


def test_persist_and_load(tmp_path):
    store = InMemoryVectorStore(dim=3)
    store.add(MemoryRecord(id="x", text="test", embedding=[0.0, 1.0, 0.0]))
    path = tmp_path / "store.json"
    store.persist(path)
    loaded = InMemoryVectorStore.load(path)
    assert loaded.dim == 3
    assert len(loaded._records) == 1
