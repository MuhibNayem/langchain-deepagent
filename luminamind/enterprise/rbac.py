from enum import Enum
from dataclasses import dataclass
from typing import Set


class Permission(Enum):
    # Queue permissions
    QUEUE_READ = "queue:read"
    QUEUE_WRITE = "queue:write"
    QUEUE_DELETE = "queue:delete"
    # Scheduler permissions
    SCHEDULER_READ = "scheduler:read"
    SCHEDULER_WRITE = "scheduler:write"
    # Swarm permissions
    SWARM_READ = "swarm:read"
    SWARM_WRITE = "swarm:write"
    SWARM_ADMIN = "swarm:admin"  # Can kill agents
    # Admin permissions
    ADMIN_TENANT = "admin:tenant"
    ADMIN_RBAC = "admin:rbac"
    ADMIN_AUDIT = "admin:audit"


ROLE_PERMISSIONS = {
    "viewer": {
        Permission.QUEUE_READ,
        Permission.SCHEDULER_READ,
        Permission.SWARM_READ,
    },
    "operator": {
        Permission.QUEUE_READ,
        Permission.QUEUE_WRITE,
        Permission.SCHEDULER_READ,
        Permission.SCHEDULER_WRITE,
        Permission.SWARM_READ,
        Permission.SWARM_WRITE,
    },
    "admin": {
        Permission.QUEUE_READ,
        Permission.QUEUE_WRITE,
        Permission.QUEUE_DELETE,
        Permission.SCHEDULER_READ,
        Permission.SCHEDULER_WRITE,
        Permission.SWARM_READ,
        Permission.SWARM_WRITE,
        Permission.SWARM_ADMIN,
        Permission.ADMIN_TENANT,
        Permission.ADMIN_RBAC,
        Permission.ADMIN_AUDIT,
    },
}


@dataclass
class Role:
    name: str
    permissions: Set[Permission]


class RBACEngine:
    """Role-based access control engine."""

    def __init__(self):
        self._user_roles: dict[str, dict[str, Role]] = {}  # user_id -> tenant_id -> role

    def assign_role(self, user_id: str, tenant_id: str, role_name: str) -> bool:
        if role_name not in ROLE_PERMISSIONS:
            return False

        if user_id not in self._user_roles:
            self._user_roles[user_id] = {}

        perms = ROLE_PERMISSIONS[role_name]
        self._user_roles[user_id][tenant_id] = Role(name=role_name, permissions=perms)
        return True

    def check_permission(self, user_id: str, tenant_id: str, permission: Permission) -> bool:
        if user_id not in self._user_roles:
            return False
        if tenant_id not in self._user_roles[user_id]:
            return False

        role = self._user_roles[user_id][tenant_id]
        return permission in role.permissions

    def get_user_roles(self, user_id: str) -> dict[str, Role]:
        return self._user_roles.get(user_id, {})
