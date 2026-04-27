"""Enterprise cost tracker with SQLite persistence and Prometheus metrics.

Tracks per-session, per-model, and per-tool token usage with
real-time cost calculation and historical reporting.
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from luminamind.cost.prices import ModelPricing, get_pricing


DEFAULT_DB_PATH = Path.home() / ".luminamind" / "costs.db"


@dataclass
class UsageRecord:
    """A single LLM call usage record."""

    id: str
    timestamp: str
    session_id: str
    thread_id: str
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float
    tool_name: str | None = None
    latency_ms: float | None = None


class CostTracker:
    """Thread-safe cost tracker with SQLite backend."""

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or Path(os.environ.get("LUMINAMIND_COST_DB", str(DEFAULT_DB_PATH)))
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _init_db(self) -> None:
        conn = self._conn()
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS usage (
                id TEXT PRIMARY KEY,
                timestamp TEXT,
                session_id TEXT,
                thread_id TEXT,
                model TEXT,
                provider TEXT,
                input_tokens INTEGER,
                output_tokens INTEGER,
                total_tokens INTEGER,
                cost_usd REAL,
                tool_name TEXT,
                latency_ms REAL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_session ON usage(session_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_thread ON usage(thread_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_timestamp ON usage(timestamp)"
        )
        conn.commit()

    def record(
        self,
        session_id: str,
        thread_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        provider: str = "unknown",
        tool_name: str | None = None,
        latency_ms: float | None = None,
    ) -> UsageRecord:
        """Record a single usage event and return the record."""
        pricing = get_pricing(model)
        cost = pricing.calculate(input_tokens, output_tokens)
        record = UsageRecord(
            id=os.urandom(8).hex(),
            timestamp=datetime.now(timezone.utc).isoformat(),
            session_id=session_id,
            thread_id=thread_id,
            model=model,
            provider=provider or pricing.provider,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost_usd=cost,
            tool_name=tool_name,
            latency_ms=latency_ms,
        )
        conn = self._conn()
        conn.execute(
            """
            INSERT INTO usage (id, timestamp, session_id, thread_id, model, provider,
                               input_tokens, output_tokens, total_tokens, cost_usd,
                               tool_name, latency_ms)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.id,
                record.timestamp,
                record.session_id,
                record.thread_id,
                record.model,
                record.provider,
                record.input_tokens,
                record.output_tokens,
                record.total_tokens,
                record.cost_usd,
                record.tool_name,
                record.latency_ms,
            ),
        )
        conn.commit()
        return record

    def session_summary(self, session_id: str) -> dict[str, Any]:
        conn = self._conn()
        row = conn.execute(
            """
            SELECT SUM(input_tokens), SUM(output_tokens), SUM(total_tokens), SUM(cost_usd), COUNT(*)
            FROM usage WHERE session_id = ?
            """,
            (session_id,),
        ).fetchone()
        if row is None or row[0] is None:
            return {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "cost_usd": 0.0, "calls": 0}
        return {
            "input_tokens": row[0],
            "output_tokens": row[1],
            "total_tokens": row[2],
            "cost_usd": round(row[3], 6),
            "calls": row[4],
        }

    def thread_summary(self, thread_id: str) -> dict[str, Any]:
        conn = self._conn()
        row = conn.execute(
            """
            SELECT SUM(input_tokens), SUM(output_tokens), SUM(total_tokens), SUM(cost_usd), COUNT(*)
            FROM usage WHERE thread_id = ?
            """,
            (thread_id,),
        ).fetchone()
        if row is None or row[0] is None:
            return {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "cost_usd": 0.0, "calls": 0}
        return {
            "input_tokens": row[0],
            "output_tokens": row[1],
            "total_tokens": row[2],
            "cost_usd": round(row[3], 6),
            "calls": row[4],
        }

    def global_summary(self, since: str | None = None) -> dict[str, Any]:
        conn = self._conn()
        sql = """
            SELECT SUM(input_tokens), SUM(output_tokens), SUM(total_tokens), SUM(cost_usd), COUNT(*)
            FROM usage
        """
        params: tuple = ()
        if since:
            sql += " WHERE timestamp >= ?"
            params = (since,)
        row = conn.execute(sql, params).fetchone()
        if row is None or row[0] is None:
            return {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0, "cost_usd": 0.0, "calls": 0}
        return {
            "input_tokens": row[0],
            "output_tokens": row[1],
            "total_tokens": row[2],
            "cost_usd": round(row[3], 6),
            "calls": row[4],
        }

    def recent(self, limit: int = 50) -> list[UsageRecord]:
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM usage ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [UsageRecord(**dict(r)) for r in rows]

    def top_models(self, limit: int = 10) -> list[dict[str, Any]]:
        conn = self._conn()
        rows = conn.execute(
            """
            SELECT model, SUM(cost_usd) as total_cost, SUM(total_tokens) as total_tokens, COUNT(*) as calls
            FROM usage GROUP BY model ORDER BY total_cost DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


# Singleton
_tracker: CostTracker | None = None


def get_cost_tracker() -> CostTracker:
    global _tracker
    if _tracker is None:
        _tracker = CostTracker()
    return _tracker
