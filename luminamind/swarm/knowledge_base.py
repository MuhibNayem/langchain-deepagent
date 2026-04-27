import threading
import time
from dataclasses import dataclass, field
from typing import Any, Optional
import uuid


@dataclass
class KnowledgeItem:
    id: str
    key: str
    value: Any
    ttl_seconds: Optional[int] = None
    created_at: float = field(default_factory=time.time)


class VectorStore:
    """Simple in-memory vector store for similarity search."""

    def __init__(self):
        self._vectors: dict[str, tuple[list[float], KnowledgeItem]] = {}

    def add(self, key: str, embedding: list[float], item: KnowledgeItem):
        self._vectors[key] = (embedding, item)

    def query(self, embedding: list[float], top_k: int = 5) -> list[KnowledgeItem]:
        """Find top-k nearest vectors by cosine similarity."""
        results = []
        for key, (vec, item) in self._vectors.items():
            sim = self._cosine(embedding, vec)
            results.append((sim, item))
        results.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in results[:top_k]]

    def _cosine(self, a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        return dot / (norm_a * norm_b) if norm_a and norm_b else 0


class GraphStore:
    """In-memory graph store for triple storage (subject, predicate, object)."""

    def __init__(self):
        self._triples: list[tuple[str, str, str]] = []
        self._index: dict[str, list[tuple[str, str]]] = {}  # subject -> [(predicate, object)]

    def add(self, subject: str, predicate: str, obj: str):
        self._triples.append((subject, predicate, obj))
        if subject not in self._index:
            self._index[subject] = []
        self._index[subject].append((predicate, obj))

    def query(self, subject: str) -> list[tuple[str, str]]:
        return self._index.get(subject, [])

    def find(self, subject: str, predicate: str) -> list[str]:
        """Find objects matching subject/predicate."""
        return [obj for pred, obj in self._index.get(subject, []) if pred == predicate]


class SharedKnowledge:
    """Shared knowledge base for swarm agents."""

    def __init__(self, ttl_seconds: int = 3600):
        self._kv: dict[str, KnowledgeItem] = {}
        self._vectors = VectorStore()
        self._graph = GraphStore()
        self._ttl = ttl_seconds
        self._lock = threading.Lock()

    def store(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        with self._lock:
            item = KnowledgeItem(
                id=str(uuid.uuid4()),
                key=key,
                value=value,
                ttl_seconds=ttl_seconds or self._ttl,
            )
            self._kv[key] = item

    def retrieve(self, key: str) -> Optional[Any]:
        with self._lock:
            item = self._kv.get(key)
            if not item:
                return None
            # Check TTL
            if item.ttl_seconds and (time.time() - item.created_at) > item.ttl_seconds:
                del self._kv[key]
                return None
            return item.value

    def query(self, embedding: list[float], top_k: int = 5) -> list[KnowledgeItem]:
        return self._vectors.query(embedding, top_k)

    def graph_store(self, subject: str, predicate: str, obj: str) -> None:
        self._graph.add(subject, predicate, obj)

    def graph_find(self, subject: str, predicate: str) -> list[str]:
        return self._graph.find(subject, predicate)


import threading
import time as time_module
from dataclasses import dataclass
from typing import Any


@dataclass
class Vote:
    voter_id: str
    value: Any
    timestamp: float


class ConsensusMechanism:
    """Simple voting-based consensus."""

    def __init__(self, threshold: float = 0.5, timeout_seconds: float = 30):
        self.threshold = threshold
        self.timeout = timeout_seconds
        self._votes: dict[str, list[Vote]] = {}
        self._lock = threading.Lock()
        self._decisions: dict[str, Any] = {}

    def vote(self, topic: str, voter_id: str, value: Any) -> None:
        with self._lock:
            if topic not in self._votes:
                self._votes[topic] = []
            # Replace previous vote from same voter
            self._votes[topic] = [v for v in self._votes[topic] if v.voter_id != voter_id]
            self._votes[topic].append(Vote(voter_id=voter_id, value=value, timestamp=time_module.time()))

    def get_decision(self, topic: str, required_votes: int) -> tuple[bool, Any]:
        """Get consensus decision. Returns (reached, value)."""
        with self._lock:
            votes = self._votes.get(topic, [])
            if len(votes) < required_votes:
                return False, None

            # Count votes per value
            counts: dict[Any, int] = {}
            for vote in votes:
                counts[vote.value] = counts.get(vote.value, 0) + 1

            # Check threshold
            for value, count in counts.items():
                if count / len(votes) >= self.threshold:
                    self._decisions[topic] = value
                    return True, value

            return False, None

    def wait_for_consensus(self, topic: str, required_votes: int, timeout: float = None) -> tuple[bool, Any]:
        """Wait for consensus with timeout."""
        timeout = timeout or self.timeout
        deadline = time_module.time() + timeout
        while time_module.time() < deadline:
            reached, value = self.get_decision(topic, required_votes)
            if reached:
                return True, value
            time_module.sleep(0.1)
        return False, None