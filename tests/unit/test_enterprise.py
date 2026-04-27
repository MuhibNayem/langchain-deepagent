"""Tests for enterprise features: tenancy, RBAC, audit logging."""
import pytest


class TestTenantIsolation:
    """Test tenant creation and namespace isolation."""

    def test_tenant_creation(self):
        """Test tenant with unique ID created."""
        from luminamind.enterprise import Tenant

        tenant = Tenant(name="Acme Corp")
        assert tenant.id is not None
        assert tenant.name == "Acme Corp"
        assert tenant.plan == "basic"

    def test_tenant_unique_ids(self):
        """Test that each tenant gets a unique ID."""
        from luminamind.enterprise import Tenant

        tenant_a = Tenant(name="Tenant A")
        tenant_b = Tenant(name="Tenant B")
        assert tenant_a.id != tenant_b.id

    def test_namespace_isolation(self):
        """Test tenant A cannot access tenant B's resources."""
        from luminamind.enterprise import Namespace

        ns_a = Namespace(tenant_id="tenant-a", namespace="default")
        ns_b = Namespace(tenant_id="tenant-b", namespace="default")

        # Tenant A's isolation check passes for tenant A
        assert ns_a.isolation_check("tenant-a") is True
        # Tenant A's isolation check fails for tenant B
        assert ns_a.isolation_check("tenant-b") is False

    def test_tenant_scoped_queue_key(self):
        """Test tasks have tenant_id in namespace key."""
        from luminamind.enterprise import Namespace

        ns_a = Namespace(tenant_id="tenant-a", namespace="default")
        ns_b = Namespace(tenant_id="tenant-b", namespace="default")

        # Queue keys are tenant-scoped
        assert ns_a.queue_key("tasks") == "tenant:tenant-a:queue:tasks"
        assert ns_b.queue_key("tasks") == "tenant:tenant-b:queue:tasks"
        assert ns_a.queue_key("tasks") != ns_b.queue_key("tasks")

    def test_scheduler_key(self):
        """Test scheduler keys are tenant-scoped."""
        from luminamind.enterprise import Namespace

        ns = Namespace(tenant_id="tenant-a", namespace="default")
        assert ns.scheduler_key("cron") == "tenant:tenant-a:scheduler:cron"

    def test_swarm_key(self):
        """Test swarm keys are tenant-scoped."""
        from luminamind.enterprise import Namespace

        ns = Namespace(tenant_id="tenant-a", namespace="default")
        assert ns.swarm_key("agents") == "tenant:tenant-a:swarm:agents"


class TestTenantManager:
    """Test TenantManager functionality."""

    def test_create_tenant(self):
        """Test tenant creation via manager."""
        from luminamind.enterprise import TenantManager, Tenant

        class MockStorage:
            def save(self, key, value):
                self._store = {key: value}
            def load(self, key):
                return self._store.get(key)
            def delete(self, key):
                self._store.pop(key, None)

        manager = TenantManager(MockStorage())
        tenant = manager.create_tenant(name="Acme Corp", plan="pro")

        assert isinstance(tenant, Tenant)
        assert tenant.name == "Acme Corp"
        assert tenant.plan == "pro"

    def test_get_tenant(self):
        """Test retrieving a tenant."""
        from luminamind.enterprise import TenantManager

        class MockStorage:
            def __init__(self):
                self._store = {}
            def save(self, key, value):
                self._store[key] = value
            def load(self, key):
                return self._store.get(key)
            def delete(self, key):
                self._store.pop(key, None)

        manager = TenantManager(MockStorage())
        created = manager.create_tenant(name="Acme Corp")
        retrieved = manager.get_tenant(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == "Acme Corp"

    def test_delete_tenant(self):
        """Test deleting a tenant."""
        from luminamind.enterprise import TenantManager

        class MockStorage:
            def __init__(self):
                self._store = {}
            def save(self, key, value):
                self._store[key] = value
            def load(self, key):
                return self._store.get(key)
            def delete(self, key):
                self._store.pop(key, None)

        manager = TenantManager(MockStorage())
        tenant = manager.create_tenant(name="Acme Corp")
        assert manager.delete_tenant(tenant.id) is True
        assert manager.get_tenant(tenant.id) is None

    def test_get_or_create_namespace(self):
        """Test namespace creation."""
        from luminamind.enterprise import TenantManager, Namespace

        class MockStorage:
            pass

        manager = TenantManager(MockStorage())
        ns = manager.get_or_create_namespace("tenant-a", "default")

        assert isinstance(ns, Namespace)
        assert ns.tenant_id == "tenant-a"
        assert ns.namespace == "default"


class TestRBAC:
    """Test RBAC functionality."""

    def test_rbac_engine(self):
        """Test RBAC engine role assignment and permission checks."""
        from luminamind.enterprise import RBACEngine, Permission

        rbac = RBACEngine()
        rbac.assign_role("user1", "tenant1", "admin")

        assert rbac.check_permission("user1", "tenant1", Permission.QUEUE_WRITE) is True
        assert rbac.check_permission("user1", "tenant1", Permission.ADMIN_TENANT) is True
        assert rbac.check_permission("user1", "tenant1", Permission.QUEUE_READ) is True

    def test_rbac_viewer_permissions(self):
        """Test viewer role has limited permissions."""
        from luminamind.enterprise import RBACEngine, Permission

        rbac = RBACEngine()
        rbac.assign_role("viewer1", "tenant1", "viewer")

        assert rbac.check_permission("viewer1", "tenant1", Permission.QUEUE_READ) is True
        assert rbac.check_permission("viewer1", "tenant1", Permission.QUEUE_WRITE) is False
        assert rbac.check_permission("viewer1", "tenant1", Permission.QUEUE_DELETE) is False

    def test_rbac_operator_permissions(self):
        """Test operator role has write but not admin permissions."""
        from luminamind.enterprise import RBACEngine, Permission

        rbac = RBACEngine()
        rbac.assign_role("op1", "tenant1", "operator")

        assert rbac.check_permission("op1", "tenant1", Permission.QUEUE_WRITE) is True
        assert rbac.check_permission("op1", "tenant1", Permission.SWARM_WRITE) is True
        assert rbac.check_permission("op1", "tenant1", Permission.SWARM_ADMIN) is False

    def test_rbac_cross_tenant_isolation(self):
        """Test user cannot access another tenant's resources."""
        from luminamind.enterprise import RBACEngine, Permission

        rbac = RBACEngine()
        rbac.assign_role("user1", "tenant1", "admin")

        # No role assigned for tenant2
        assert rbac.check_permission("user1", "tenant2", Permission.QUEUE_READ) is False

    def test_get_user_roles(self):
        """Test retrieving user's roles across tenants."""
        from luminamind.enterprise import RBACEngine

        rbac = RBACEngine()
        rbac.assign_role("user1", "tenant1", "admin")
        rbac.assign_role("user1", "tenant2", "viewer")

        roles = rbac.get_user_roles("user1")
        assert "tenant1" in roles
        assert "tenant2" in roles
        assert roles["tenant1"].name == "admin"
        assert roles["tenant2"].name == "viewer"


class TestAuditLog:
    """Test audit logging functionality."""

    def test_audit_log(self):
        """Test audit log creation and query."""
        from luminamind.enterprise import AuditLog, AuditEntry

        class MockStorage:
            def save(self, key, value):
                pass
            def load(self, key):
                return None
            def delete(self, key):
                pass

        audit = AuditLog(MockStorage())
        entry = AuditEntry(
            id="1",
            user_id="user1",
            tenant_id="tenant1",
            action="queue.enqueue",
            resource="task",
            resource_id="task-123",
        )
        audit.log(entry)

        results = audit.query(tenant_id="tenant1")
        assert len(results) == 1
        assert results[0].action == "queue.enqueue"

    def test_audit_query_filters(self):
        """Test audit log query with filters."""
        from luminamind.enterprise import AuditLog, AuditEntry
        from datetime import datetime

        class MockStorage:
            def save(self, key, value):
                pass
            def load(self, key):
                return None
            def delete(self, key):
                pass

        audit = AuditLog(MockStorage())
        entry1 = AuditEntry(
            id="1",
            user_id="user1",
            tenant_id="tenant1",
            action="queue.enqueue",
            resource="task",
            resource_id="task-1",
        )
        entry2 = AuditEntry(
            id="2",
            user_id="user2",
            tenant_id="tenant1",
            action="queue.delete",
            resource="task",
            resource_id="task-2",
        )
        audit.log(entry1)
        audit.log(entry2)

        # Filter by user
        results = audit.query(tenant_id="tenant1", user_id="user1")
        assert len(results) == 1
        assert results[0].user_id == "user1"

        # Filter by action
        results = audit.query(tenant_id="tenant1", action="queue.delete")
        assert len(results) == 1
        assert results[0].action == "queue.delete"

    def test_audit_export(self):
        """Test audit log export to JSON."""
        from luminamind.enterprise import AuditLog, AuditEntry

        class MockStorage:
            def save(self, key, value):
                pass
            def load(self, key):
                return None
            def delete(self, key):
                pass

        audit = AuditLog(MockStorage())
        entry = AuditEntry(
            id="1",
            user_id="user1",
            tenant_id="tenant1",
            action="queue.enqueue",
            resource="task",
            resource_id="task-123",
        )
        audit.log(entry)

        exported = audit.export(tenant_id="tenant1", format="json")
        assert "user1" in exported
        assert "queue.enqueue" in exported
