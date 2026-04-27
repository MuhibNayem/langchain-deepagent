from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class MemoryNamespace:
    """Namespace for memory isolation (e.g., per project)."""
    namespace_id: str
    name: str
    base_path: Path
    created_at: datetime
    metadata: dict
    
    def exists(self) -> bool:
        """Check if namespace exists."""
        return self.base_path.exists()
    
    def clear(self) -> None:
        """Clear all memory in namespace."""
        import shutil
        if self.base_path.exists():
            shutil.rmtree(self.base_path)
    
    def export(self) -> dict:
        """Export namespace as dict."""
        pass
    
    def import_data(self, data: dict) -> None:
        """Import data into namespace."""
        pass


class NamespaceManager:
    """Manages multiple memory namespaces."""
    
    def __init__(self, base_path: Path = Path("~/.luminamind/namespaces")):
        self.base_path = Path(base_path).expanduser()
        self.base_path.mkdir(parents=True, exist_ok=True)
        self._namespaces: dict[str, MemoryNamespace] = {}
    
    def create(self, namespace_id: str, name: str, metadata: dict = None) -> MemoryNamespace:
        """Create a new namespace."""
        ns = MemoryNamespace(
            namespace_id=namespace_id,
            name=name,
            base_path=self.base_path / namespace_id,
            created_at=datetime.utcnow(),
            metadata=metadata or {}
        )
        ns.base_path.mkdir(parents=True, exist_ok=True)
        self._namespaces[namespace_id] = ns
        return ns
    
    def get(self, namespace_id: str) -> MemoryNamespace | None:
        """Get namespace by ID."""
        return self._namespaces.get(namespace_id)
    
    def list_namespaces(self) -> list[MemoryNamespace]:
        """List all namespaces."""
        return list(self._namespaces.values())
