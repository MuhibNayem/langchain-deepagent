from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

try:  # Optional dependency: Redis for distributed rate limits
    import redis  # type: ignore
except Exception:  # pragma: no cover - redis not installed
    redis = None  # type: ignore


class RateLimitError(Exception):
    """Raised when a rate limit is exceeded."""


@dataclass
class RateLimitConfig:
    max_calls: int
    window_seconds: int


DEFAULT_LIMITS: Dict[str, RateLimitConfig] = {
    "web_search": RateLimitConfig(max_calls=10, window_seconds=60),  # 10/min
    "shell": RateLimitConfig(max_calls=30, window_seconds=60),       # 30/min
    "web_crawl": RateLimitConfig(max_calls=20, window_seconds=60),   # 20/min
    "get_weather": RateLimitConfig(max_calls=100, window_seconds=60),# 100/min
    "fetch_as_markdown": RateLimitConfig(max_calls=60, window_seconds=60),  # 60/min
}

_lock = threading.Lock()
_in_memory_counters: Dict[str, list[float]] = {}


def _parse_limit(limit_str: str) -> RateLimitConfig:
    """Parse limits like '10/minute' or '30/second' into config."""
    parts = limit_str.split("/")
    if len(parts) != 2:
        raise ValueError(f"Invalid rate limit format: {limit_str}")
    count = int(parts[0])
    unit = parts[1].strip().lower()
    if unit.startswith("sec"):
        window = 1
    elif unit.startswith("min"):
        window = 60
    elif unit.startswith("hour"):
        window = 3600
    else:
        raise ValueError(f"Unsupported rate limit unit: {unit}")
    return RateLimitConfig(max_calls=count, window_seconds=window)


def _get_limit(tool_name: str) -> RateLimitConfig:
    """Fetch limit from env override or default map."""
    env_key = f"TOOL_RATE_LIMIT_{tool_name.upper()}"
    custom = os.getenv(env_key)
    if custom:
        try:
            return _parse_limit(custom)
        except Exception:
            pass  # fallback to default on bad config
    return DEFAULT_LIMITS.get(tool_name, RateLimitConfig(max_calls=60, window_seconds=60))


def _get_identity(identity: Optional[str]) -> str:
    return identity or os.getenv("RATE_LIMIT_ID") or "global"


def _redis_client():
    url = os.getenv("RATE_LIMIT_REDIS_URL")
    if not url or not redis:
        return None
    try:
        return redis.Redis.from_url(url)
    except Exception:
        return None


def _enforce_redis(tool_name: str, identity: str, cfg: RateLimitConfig) -> bool:
    client = _redis_client()
    if not client:
        return False

    key = f"rl:{tool_name}:{identity}"
    try:
        with client.pipeline() as pipe:
            pipe.incr(key, 1)
            pipe.ttl(key)
            count, ttl = pipe.execute()

        if ttl == -1:
            client.expire(key, cfg.window_seconds)

        if count > cfg.max_calls:
            return True
    except Exception:
        return False
    return False


def _enforce_memory(tool_name: str, identity: str, cfg: RateLimitConfig) -> bool:
    now = time.time()
    window_start = now - cfg.window_seconds
    key = f"{tool_name}:{identity}"
    with _lock:
        entries = _in_memory_counters.setdefault(key, [])
        # Drop old entries
        _in_memory_counters[key] = [ts for ts in entries if ts >= window_start]
        _in_memory_counters[key].append(now)
        return len(_in_memory_counters[key]) > cfg.max_calls


def enforce_rate_limit(tool_name: str, identity: Optional[str] = None) -> None:
    """Enforce per-tool rate limits with Redis if available, else in-process."""
    cfg = _get_limit(tool_name)
    key = _get_identity(identity)

    # Try Redis (distributed)
    exceeded = _enforce_redis(tool_name, key, cfg)
    if exceeded:
        raise RateLimitError(f"Rate limit exceeded for {tool_name}")
    if exceeded is False:
        # Fallback to in-memory when Redis absent or fails
        if _enforce_memory(tool_name, key, cfg):
            raise RateLimitError(f"Rate limit exceeded for {tool_name}")


__all__ = ["enforce_rate_limit", "RateLimitError", "RateLimitConfig"]
