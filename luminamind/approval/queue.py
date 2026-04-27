from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import uuid


class ApprovalStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class ApprovalRequest:
    """A request requiring human approval."""
    request_id: str | None
    created_at: datetime
    operation_type: str  # e.g., "file_write", "code_execution", "api_call"
    description: str  # Human-readable description
    payload: dict[str, Any]  # Operation details
    priority: int = 0  # Higher = more urgent
    status: ApprovalStatus = ApprovalStatus.PENDING
    requested_by: str = "harness"  # Who/what requested approval
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    review_notes: str | None = None
    expires_at: datetime | None = None  # If None, never expires

    def __post_init__(self):
        if self.request_id is None:
            self.request_id = str(uuid.uuid4())


class ApprovalQueue:
    """Queue of approval requests, backed by Redis."""

    def __init__(self, redis_client=None):
        self.redis = redis_client
        self._key = "approval:queue"
        self._pending_key = "approval:pending"

    def enqueue(self, request: ApprovalRequest) -> str:
        """Add a request to the approval queue.
        Returns request_id.
        """
        import pickle
        data = pickle.dumps(request)

        # Add to sorted set by priority (higher = earlier)
        self.redis.zadd(self._key, {request.request_id: -request.priority})
        self.redis.hset(self._pending_key, request.request_id, data)

        return request.request_id

    def dequeue(self, timeout: int = 0) -> ApprovalRequest | None:
        """Get highest priority pending request.

        Args:
            timeout: Seconds to wait for a request (0 = don't wait)

        Returns:
            ApprovalRequest or None if queue empty
        """
        # Get highest priority request_id
        result = self.redis.zrange(self._key, 0, 0)
        if not result:
            return None
        request_id = result[0].decode() if isinstance(result[0], bytes) else result[0]

        # Get request data
        data = self.redis.hget(self._pending_key, request_id)
        if not data:
            return None

        import pickle
        request = pickle.loads(data)
        return request

    def approve(self, request_id: str, reviewer: str, notes: str | None = None) -> bool:
        """Approve a request."""
        return self._update_status(request_id, ApprovalStatus.APPROVED, reviewer, notes)

    def reject(self, request_id: str, reviewer: str, notes: str | None = None) -> bool:
        """Reject a request."""
        return self._update_status(request_id, ApprovalStatus.REJECTED, reviewer, notes)

    def _update_status(self, request_id: str, status: ApprovalStatus, reviewer: str, notes: str | None) -> bool:
        import pickle
        data = self.redis.hget(self._pending_key, request_id)
        if not data:
            return False

        request = pickle.loads(data)
        request.status = status
        request.reviewed_by = reviewer
        request.reviewed_at = datetime.now()
        request.review_notes = notes

        # Update in Redis
        self.redis.hset(self._pending_key, request_id, pickle.dumps(request))
        self.redis.zrem(self._key, request_id)

        return True

    def get_status(self, request_id: str) -> ApprovalStatus | None:
        """Get current status of a request."""
        data = self.redis.hget(self._pending_key, request_id)
        if not data:
            return None
        import pickle
        request = pickle.loads(data)
        return request.status

    def list_pending(self, limit: int = 100) -> list[ApprovalRequest]:
        """List all pending requests, sorted by priority."""
        import pickle
        request_ids = self.redis.zrange(self._key, 0, limit - 1)
        requests = []
        for rid in request_ids:
            rid = rid.decode() if isinstance(rid, bytes) else rid
            data = self.redis.hget(self._pending_key, rid)
            if data:
                requests.append(pickle.loads(data))
        return requests
