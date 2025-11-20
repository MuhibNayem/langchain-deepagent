from __future__ import annotations

import os
import pickle
from pathlib import Path
from typing import Any

from langgraph.checkpoint.memory import MemorySaver

try:
    from redis import Redis
    from redis.exceptions import RedisError
except ImportError:  # pragma: no cover
    Redis = None  # type: ignore[assignment]
    RedisError = Exception  # type: ignore[misc,assignment]

REDIS_KEY = os.environ.get("CHECKPOINT_REDIS_KEY", "langgraph:checkpoints")


def _load_state(target: MemorySaver, payload: bytes) -> None:
    try:
        data = pickle.loads(payload)
    except Exception:
        return
    storage = data.get("storage")
    if storage:
        target.storage.clear()
        target.storage.update(storage)
    writes = data.get("writes")
    if writes:
        target.writes.clear()
        target.writes.update(writes)
    blobs = data.get("blobs")
    if blobs:
        target.blobs.clear()
        target.blobs.update(blobs)


def _dump_state(target: MemorySaver) -> bytes:
    return pickle.dumps(
        {
            "storage": target.storage,
            "writes": target.writes,
            "blobs": target.blobs,
        }
    )


class RedisBackedMemorySaver(MemorySaver):
    """MemorySaver that persists checkpoints into Redis."""

    def __init__(self, client: Redis, key: str = REDIS_KEY) -> None:
        super().__init__()
        self.redis = client
        self.key = key
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        try:
            payload = self.redis.get(self.key)
        except RedisError:
            return
        if payload:
            _load_state(self, payload)

    def _persist(self) -> None:
        try:
            self.redis.set(self.key, _dump_state(self))
        except RedisError:
            pass

    def get_tuple(self, config):
        self._ensure_loaded()
        return super().get_tuple(config)

    def list(self, config, *, filter=None, before=None, limit=None):
        self._ensure_loaded()
        return super().list(config, filter=filter, before=before, limit=limit)

    def put(self, config, checkpoint, metadata, new_versions):
        self._ensure_loaded()
        result = super().put(config, checkpoint, metadata, new_versions)
        self._persist()
        return result

    def put_writes(self, config, writes, task_id, task_path=""):
        self._ensure_loaded()
        result = super().put_writes(config, writes, task_id, task_path)
        self._persist()
        return result

    def delete_thread(self, thread_id: str) -> None:
        self._ensure_loaded()
        super().delete_thread(thread_id)
        self._persist()


class FileBackedMemorySaver(MemorySaver):
    """MemorySaver that persists checkpoints to a binary file on disk."""

    def __init__(self, directory: str | Path) -> None:
        super().__init__()
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.file = self.dir / "checkpoints.pkl"
        self._load()

    def _load(self) -> None:
        if not self.file.exists():
            return
        try:
            payload = self.file.read_bytes()
        except OSError:
            return
        if payload:
            _load_state(self, payload)

    def _persist(self) -> None:
        try:
            self.file.write_bytes(_dump_state(self))
        except OSError:
            pass

    def put(self, config, checkpoint, metadata, new_versions):
        result = super().put(config, checkpoint, metadata, new_versions)
        self._persist()
        return result

    def put_writes(self, config, writes, task_id, task_path=""):
        result = super().put_writes(config, writes, task_id, task_path)
        self._persist()
        return result

    def delete_thread(self, thread_id: str) -> None:
        super().delete_thread(thread_id)
        self._persist()


def create_checkpointer() -> MemorySaver:
    """Factory mirroring original JS logic."""
    redis_url = os.environ.get("CHECKPOINT_REDIS_URL")
    if redis_url:
        if Redis is None:
            raise ImportError("redis package required for RedisBackedMemorySaver")
        client = Redis.from_url(redis_url, decode_responses=False)
        return RedisBackedMemorySaver(client, REDIS_KEY)

    directory = os.environ.get("CHECKPOINT_DIR")
    if directory:
        return FileBackedMemorySaver(directory)

    return MemorySaver()


__all__ = ["create_checkpointer", "FileBackedMemorySaver", "RedisBackedMemorySaver"]
