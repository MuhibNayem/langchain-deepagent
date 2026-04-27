from dataclasses import dataclass, field
from typing import Optional
import uuid


@dataclass
class Tenant:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    plan: str = "basic"  # basic, pro, enterprise
    namespaces: list[str] = field(default_factory=list)
    created_at: str = ""
    metadata: dict = field(default_factory=dict)


class Namespace:
    """Tenant-scoped resource namespace."""

    def __init__(self, tenant_id: str, namespace: str = "default"):
        self.tenant_id = tenant_id
        self.namespace = namespace

    def queue_key(self, resource: str) -> str:
        """Generate tenant-scoped Redis key."""
        return f"tenant:{self.tenant_id}:queue:{resource}"

    def scheduler_key(self, resource: str) -> str:
        return f"tenant:{self.tenant_id}:scheduler:{resource}"

    def swarm_key(self, resource: str) -> str:
        return f"tenant:{self.tenant_id}:swarm:{resource}"

    def isolation_check(self, tenant_id: str) -> bool:
        """Verify tenant can only access own resources."""
        return tenant_id == self.tenant_id


class TenantManager:
    """Manages tenants and their namespaces."""

    def __init__(self, storage_backend):
        self._storage = storage_backend
        self._tenants: dict[str, Tenant] = {}

    def create_tenant(self, name: str, plan: str = "basic") -> Tenant:
        tenant = Tenant(name=name, plan=plan)
        self._tenants[tenant.id] = tenant
        self._storage.save(f"tenant:{tenant.id}", tenant)
        return tenant

    def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        return self._tenants.get(tenant_id) or self._storage.load(f"tenant:{tenant_id}")

    def delete_tenant(self, tenant_id: str) -> bool:
        if tenant_id in self._tenants:
            del self._tenants[tenant_id]
            self._storage.delete(f"tenant:{tenant_id}")
            return True
        return False

    def get_or_create_namespace(self, tenant_id: str, namespace: str = "default") -> Namespace:
        return Namespace(tenant_id, namespace)
