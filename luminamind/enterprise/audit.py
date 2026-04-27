from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
import json


@dataclass
class AuditEntry:
    id: str
    user_id: str
    tenant_id: str
    action: str
    resource: str
    resource_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    details: dict = field(default_factory=dict)
    ip_address: Optional[str] = None


class AuditLog:
    """Audit logging for admin actions."""

    def __init__(self, storage_backend):
        self._storage = storage_backend
        self._log: list[AuditEntry] = []

    def log(self, entry: AuditEntry):
        """Log an audit entry."""
        self._log.append(entry)
        # Persist to storage
        self._storage.save(f"audit:{entry.id}", entry)

    def query(
        self,
        tenant_id: str,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        from_time: Optional[datetime] = None,
        to_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[AuditEntry]:
        """Query audit log entries."""
        results = []
        for entry in self._log:
            if entry.tenant_id != tenant_id:
                continue
            if user_id and entry.user_id != user_id:
                continue
            if action and entry.action != action:
                continue
            if from_time and entry.timestamp < from_time:
                continue
            if to_time and entry.timestamp > to_time:
                continue
            results.append(entry)

        return sorted(results, key=lambda e: e.timestamp, reverse=True)[:limit]

    def export(self, tenant_id: str, format: str = "json") -> str:
        """Export audit log for compliance."""
        entries = self.query(tenant_id=tenant_id, limit=10000)
        if format == "json":
            return json.dumps([{
                "id": e.id,
                "user_id": e.user_id,
                "action": e.action,
                "resource": e.resource,
                "timestamp": e.timestamp.isoformat(),
                "details": e.details,
            } for e in entries], indent=2)
        return str(entries)
