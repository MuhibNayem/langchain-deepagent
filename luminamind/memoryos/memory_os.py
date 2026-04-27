from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional
import json
import sqlite3


class ContextLevel(Enum):
    GLOBAL = "global"      # System-wide knowledge
    PROJECT = "project"    # Project-specific knowledge
    TASK = "task"          # Task-specific context
    SESSION = "session"    # Current session


@dataclass
class ContextEntry:
    """An entry in the memory hierarchy."""
    entry_id: str
    level: ContextLevel
    key: str
    value: str
    created_at: datetime
    updated_at: datetime
    access_count: int = 0
    last_accessed: datetime | None = None
    importance: float = 0.5  # 0.0 - 1.0
    source: str = "manual"  # manual, distilled, imported
    tags: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class ContextHierarchy:
    """Hierarchical context structure."""
    global_context: dict[str, str]
    project_context: dict[str, str]
    task_context: dict[str, str]
    session_context: dict[str, str]
    
    def to_prompt_context(self) -> str:
        """Convert hierarchy to prompt-friendly format."""
        parts = []
        if self.global_context:
            parts.append("## Global Context\n" + self._format_dict(self.global_context))
        if self.project_context:
            parts.append("## Project Context\n" + self._format_dict(self.project_context))
        if self.task_context:
            parts.append("## Task Context\n" + self._format_dict(self.task_context))
        if self.session_context:
            parts.append("## Session Context\n" + self._format_dict(self.session_context))
        return "\n\n".join(parts)
    
    def _format_dict(self, d: dict) -> str:
        return "\n".join(f"- {k}: {v}" for k, v in d.items())


class MemoryOS:
    """Filesystem-based hierarchical memory OS.
    
    Provides context hierarchy: global → project → task → session
    NOT a flat vector store (explicitly required per phase spec)
    """
    
    def __init__(self, base_path: Path = Path("~/.luminamind/memory")):
        self.base_path = Path(base_path).expanduser()
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Setup directory structure
        for level in ContextLevel:
            (self.base_path / level.value).mkdir(exist_ok=True)
        
        # SQLite index for fast lookup
        self._db_path = self.base_path / "memoryos.db"
        self._init_db()
    
    def _init_db(self) -> None:
        """Initialize SQLite index."""
        conn = sqlite3.connect(self._db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS entries (
                entry_id TEXT PRIMARY KEY,
                level TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT,
                created_at TEXT,
                updated_at TEXT,
                access_count INTEGER DEFAULT 0,
                last_accessed TEXT,
                importance REAL DEFAULT 0.5,
                source TEXT DEFAULT 'manual',
                tags TEXT,
                metadata TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_level ON entries(level)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_key ON entries(key)")
        conn.commit()
        conn.close()
    
    def store(self, level: ContextLevel, key: str, value: str,
              tags: list[str] = None, importance: float = 0.5,
              source: str = "manual") -> str:
        """Store an entry in the memory hierarchy."""
        entry_id = f"{level.value}:{key}"
        now = datetime.utcnow().isoformat()
        
        conn = sqlite3.connect(self._db_path)
        conn.execute("""
            INSERT OR REPLACE INTO entries 
            (entry_id, level, key, value, created_at, updated_at, access_count, 
             last_accessed, importance, source, tags, metadata)
            VALUES (?, ?, ?, ?, 
                    COALESCE((SELECT created_at FROM entries WHERE entry_id = ?), ?),
                    ?, 0, NULL, ?, ?, ?, '{}')
        """, (entry_id, level.value, key, value, entry_id, now, now, importance, source,
              json.dumps(tags or [])))
        conn.commit()
        conn.close()
        
        # Also write to filesystem for persistence
        self._write_to_filesystem(entry_id, value)
        
        return entry_id
    
    def retrieve(self, level: ContextLevel, key: str) -> str | None:
        """Retrieve a specific entry."""
        conn = sqlite3.connect(self._db_path)
        cursor = conn.execute(
            "SELECT value FROM entries WHERE level = ? AND key = ?",
            (level.value, key)
        )
        row = cursor.fetchone()
        conn.close()
        
        if row:
            self._update_access(entry_id=f"{level.value}:{key}")
            return row[0]
        return None
    
    def query(self, level: ContextLevel, pattern: str = "*", 
              limit: int = 100) -> list[ContextEntry]:
        """Query entries at a level with glob pattern."""
        conn = sqlite3.connect(self._db_path)
        cursor = conn.execute("""
            SELECT entry_id, level, key, value, created_at, updated_at,
                   access_count, last_accessed, importance, source, tags, metadata
            FROM entries
            WHERE level = ? AND (key LIKE ? OR ? = '*')
            ORDER BY importance DESC, access_count DESC
            LIMIT ?
        """, (level.value, pattern.replace('*', '%'), pattern, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [self._row_to_entry(row) for row in rows]
    
    def get_hierarchy(self, project: str = "default", 
                     task_id: str = None, session_id: str = None) -> ContextHierarchy:
        """Get full context hierarchy for a given scope."""
        return ContextHierarchy(
            global_context=self._level_to_dict(ContextLevel.GLOBAL),
            project_context=self._level_to_dict(ContextLevel.PROJECT, project),
            task_context=self._level_to_dict(ContextLevel.TASK, task_id) if task_id else {},
            session_context=self._level_to_dict(ContextLevel.SESSION, session_id) if session_id else {}
        )
    
    def _level_to_dict(self, level: ContextLevel, scope: str = None) -> dict[str, str]:
        """Convert a level to a dictionary."""
        entries = self.query(level, limit=1000)
        result = {}
        for entry in entries:
            if scope is None or scope in entry.key:
                result[entry.key] = entry.value
        return result
    
    def _update_access(self, entry_id: str) -> None:
        """Update access statistics."""
        conn = sqlite3.connect(self._db_path)
        conn.execute("""
            UPDATE entries 
            SET access_count = access_count + 1, last_accessed = ?
            WHERE entry_id = ?
        """, (datetime.utcnow().isoformat(), entry_id))
        conn.commit()
        conn.close()
    
    def _write_to_filesystem(self, entry_id: str, value: str) -> None:
        """Write entry value to filesystem."""
        path = self.base_path / entry_id.replace(':', '/')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value)
    
    def _row_to_entry(self, row: tuple) -> ContextEntry:
        """Convert DB row to ContextEntry."""
        return ContextEntry(
            entry_id=row[0],
            level=ContextLevel(row[1]),
            key=row[2],
            value=row[3],
            created_at=datetime.fromisoformat(row[4]),
            updated_at=datetime.fromisoformat(row[5]),
            access_count=row[6],
            last_accessed=datetime.fromisoformat(row[7]) if row[7] else None,
            importance=row[8],
            source=row[9],
            tags=json.loads(row[10]) if row[10] else [],
            metadata=json.loads(row[11]) if row[11] else {}
        )
    
    def distill_from_task(self, task_id: str, task_result: 'TaskResult') -> list[ContextEntry]:
        """Distill knowledge from task execution into memory.
        
        Extracts reusable patterns, decisions, and lessons.
        """
        # Extract key decisions and patterns
        entries = []
        
        # Store successful patterns
        if task_result.success:
            self.store(
                level=ContextLevel.TASK,
                key=f"{task_id}:pattern:{len(task_result.patterns)}",
                value=json.dumps(task_result.patterns),
                source="distilled",
                importance=0.7,
                tags=["pattern", "task"]
            )
        
        return entries
