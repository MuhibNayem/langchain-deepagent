from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable


class EvictionPolicy(Enum):
    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    IMPORTANCE = "importance"  # Based on importance score
    TTL = "ttl"  # Time To Live
    HYBRID = "hybrid"  # Combination of factors


@dataclass
class EvictionCandidate:
    """A candidate for eviction from memory."""
    entry_id: str
    key: str
    last_accessed: datetime | None
    access_count: int
    importance: float
    age_hours: float
    score: float  # Lower score = more likely to evict
    
    def __init__(self, entry_id: str, key: str, last_accessed: datetime | None,
                 access_count: int, importance: float, created_at: datetime):
        self.entry_id = entry_id
        self.key = key
        self.last_accessed = last_accessed
        self.access_count = access_count
        self.importance = importance
        self.created_at = created_at
        self.age_hours = (datetime.utcnow() - created_at).total_seconds() / 3600
        self.score = self._calculate_score()
    
    def _calculate_score(self) -> float:
        """Calculate eviction score. Lower = more likely to evict."""
        # Lower access count, lower importance, older = higher eviction priority
        recency_score = 1.0 / (1.0 + (self.age_hours / 24))
        access_score = 1.0 / (1.0 + self.access_count)
        importance_score = 1.0 - self.importance
        
        # Weighted combination
        return (recency_score * 0.3) + (access_score * 0.3) + (importance_score * 0.4)


class MemoryEvictionPolicy:
    """Policy for evicting entries from memory when space is needed."""
    
    def __init__(self, policy: EvictionPolicy = EvictionPolicy.HYBRID, 
                 max_entries: int = 10000,
                 ttl_hours: int = 720):  # 30 days default
        self.policy = policy
        self.max_entries = max_entries
        self.ttl_hours = ttl_hours
    
    def select_for_eviction(self, entries: list, target_count: int) -> list[str]:
        """Select entry IDs that should be evicted.
        
        Args:
            entries: List of entries to evaluate
            target_count: Number of entries to evict
            
        Returns:
            List of entry_ids to evict
        """
        if len(entries) <= self.max_entries:
            return []
        
        candidates = []
        for entry in entries:
            if hasattr(entry, 'last_accessed') and hasattr(entry, 'importance'):
                candidate = EvictionCandidate(
                    entry_id=entry.entry_id,
                    key=entry.key,
                    last_accessed=entry.last_accessed,
                    access_count=entry.access_count,
                    importance=entry.importance,
                    created_at=entry.created_at
                )
                candidates.append(candidate)
        
        # Sort by score (lower = evict first)
        candidates.sort(key=lambda c: c.score)
        
        # Return IDs to evict
        evict_count = min(target_count, len(candidates))
        return [c.entry_id for c in candidates[:evict_count]]
    
    def is_expired(self, entry, current_time: datetime = None) -> bool:
        """Check if an entry has expired based on TTL."""
        if current_time is None:
            current_time = datetime.utcnow()
        
        if hasattr(entry, 'created_at'):
            age = current_time - entry.created_at
            return age > timedelta(hours=self.ttl_hours)
        
        return False
    
    def should_evict(self, entry, current_time: datetime = None) -> bool:
        """Determine if an entry should be evicted."""
        if self.policy == EvictionPolicy.TTL:
            return self.is_expired(entry, current_time)
        
        # For other policies, use the selection method
        candidates = self.select_for_eviction([entry], 1)
        return len(candidates) > 0 and candidates[0] == entry.entry_id
