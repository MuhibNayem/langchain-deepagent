"""Browser session manager for Playwright MCP bridge."""
import asyncio
import time
from dataclasses import dataclass, field
from typing import Any
from contextlib import asynccontextmanager

from luminamind.evaluator.playwright_mcp_bridge import PlaywrightMCPBridge


@dataclass
class BrowserSession:
    """Represents a browser session with lifecycle management."""
    bridge: PlaywrightMCPBridge
    created_at: float = field(default_factory=time.time)
    last_used: float = field(default_factory=time.time)
    ttl_seconds: float = 300.0  # 5 minute default TTL


class BrowserSessionManager:
    """Manages browser sessions with reuse and cleanup.
    
    Features:
    - Session reuse within TTL to avoid browser startup overhead
    - Automatic cleanup of stale sessions
    - Concurrent session isolation
    """
    
    def __init__(self, ttl_seconds: float = 300.0, max_sessions: int = 5):
        self.ttl_seconds = ttl_seconds
        self.max_sessions = max_sessions
        self._sessions: dict[str, BrowserSession] = {}
        self._lock = asyncio.Lock()
        self._session_counter = 0
    
    @asynccontextmanager
    async def acquire(self, session_id: str | None = None):
        """Acquire a browser session.
        
        Args:
            session_id: Optional session ID for reuse. If None, creates new session.
            
        Yields:
            BrowserSession with connected PlaywrightMCPBridge
        """
        async with self._lock:
            if session_id and session_id in self._sessions:
                session = self._sessions[session_id]
                if time.time() - session.created_at < session.ttl_seconds:
                    session.last_used = time.time()
                    yield session
                    return
                else:
                    # Session expired, cleanup
                    await self._cleanup_session(session_id)
            
            # Create new session
            if len(self._sessions) >= self.max_sessions:
                # Evict oldest session
                oldest_id = min(self._sessions, key=lambda k: self._sessions[k].last_used)
                await self._cleanup_session(oldest_id)
            
            self._session_counter += 1
            new_id = session_id or f"session-{self._session_counter}"
            
            bridge = PlaywrightMCPBridge()
            await bridge.connect()
            
            session = BrowserSession(
                bridge=bridge,
                created_at=time.time(),
                last_used=time.time(),
                ttl_seconds=self.ttl_seconds,
            )
            self._sessions[new_id] = session
            yield session
    
    async def _cleanup_session(self, session_id: str) -> None:
        """Cleanup a session."""
        if session_id in self._sessions:
            session = self._sessions[session_id]
            try:
                await session.bridge.disconnect()
            except Exception:
                pass
            del self._sessions[session_id]
    
    async def cleanup_stale(self) -> int:
        """Cleanup all stale sessions. Returns count of cleaned sessions."""
        async with self._lock:
            current_time = time.time()
            stale_ids = [
                sid for sid, sess in self._sessions.items()
                if current_time - sess.last_used >= sess.ttl_seconds
            ]
            for sid in stale_ids:
                await self._cleanup_session(sid)
            return len(stale_ids)
    
    async def shutdown(self) -> None:
        """Shutdown all sessions."""
        async with self._lock:
            for sid in list(self._sessions.keys()):
                await self._cleanup_session(sid)


__all__ = ["BrowserSessionManager", "BrowserSession"]
