"""KV cache optimization through stable prompt segment identification.

Per phase 06-05: Identify stable prompt segments for KV cache optimization.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import hashlib


@dataclass
class CacheSegment:
    """A segment of prompt that could be cached.

    Attributes:
        content: The text content of the segment
        start_token: Starting token position
        end_token: Ending token position
        content_hash: SHA256 of content for invalidation
        stability_score: 0-1, how stable this segment is (higher = more stable)
        last_accessed: Access counter for LRU tracking
    """
    content: str
    start_token: int
    end_token: int
    content_hash: str
    stability_score: float = 1.0
    last_accessed: int = 0


@dataclass
class CacheOptimizer:
    """Optimizes KV cache by identifying stable prompt segments.

    Usage:
        optimizer = CacheOptimizer()
        segments = optimizer.identify_stable_segments([
            {"content": "You are a helpful assistant", "type": "system"},
            {"content": "Write a REST API", "type": "task"},
        ])
        cache_key = optimizer.get_cache_key(segments)
    """

    max_cache_segments: int = 50
    stability_threshold: float = 0.8

    def __post_init__(self):
        self._segments: dict[str, CacheSegment] = {}
        self._access_count = 0

    def identify_stable_segments(
        self,
        prompt_parts: list[dict[str, Any]]
    ) -> list[CacheSegment]:
        """Identify which parts of a prompt are stable (cacheable).

        Args:
            prompt_parts: List of {"content": str, "role": str, "type": str}
                where type is "system", "task", "history", "tool_result"

        Returns:
            List of CacheSegments that meet stability threshold
        """
        stable = []
        token_counter = 0

        for part in prompt_parts:
            content = part.get("content", "")
            part_type = part.get("type", "unknown")

            # Calculate content hash
            content_hash = hashlib.sha256(content.encode()).hexdigest()

            # Calculate stability based on type
            # System prompts are most stable
            if part_type == "system":
                stability = 0.95
            elif part_type == "task":
                stability = 0.85
            elif part_type == "tool_result":
                stability = 0.3  # Tool results change often
            else:
                stability = 0.5

            # Rough token estimation: 1 token ≈ 4 chars or 0.75 words
            token_estimate = len(content) // 4

            segment = CacheSegment(
                content=content,
                start_token=token_counter,
                end_token=token_counter + token_estimate,
                content_hash=content_hash,
                stability_score=stability,
            )

            if segment.stability_score >= self.stability_threshold:
                stable.append(segment)

            token_counter = segment.end_token

        return stable

    def get_cache_key(self, segments: list[CacheSegment]) -> str:
        """Generate cache key from stable segments.

        Args:
            segments: List of CacheSegments to generate key from

        Returns:
            SHA256 hash string as cache key
        """
        hashes = [s.content_hash for s in segments]
        combined = "|".join(hashes)
        return hashlib.sha256(combined.encode()).hexdigest()

    def should_cache(self, content: str, part_type: str) -> bool:
        """Quick check if content should be considered for caching.

        Args:
            content: Content to check
            part_type: Type of the content part

        Returns:
            True if content should be cached
        """
        if part_type == "tool_result":
            return False  # Tool results change constantly
        if len(content) < 100:  # Too short to benefit
            return False
        return True

    def update_access(self, content_hash: str):
        """Update access statistics for a cache segment.

        Args:
            content_hash: Hash of the content to update
        """
        self._access_count += 1
        if content_hash in self._segments:
            self._segments[content_hash].last_accessed = self._access_count

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dict with cache statistics
        """
        total = len(self._segments)
        return {
            "total_segments": total,
            "access_count": self._access_count,
            "avg_stability": sum(s.stability_score for s in self._segments.values()) / max(total, 1),
        }


__all__ = ["CacheOptimizer", "CacheSegment"]