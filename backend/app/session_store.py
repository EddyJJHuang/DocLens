"""Session-scoped runtime storage for uploaded documents and chat state.

DocLens is intentionally not a long-term memory product. Uploaded files,
retrieval indexes, and conversation history are kept per browser session and
are deleted either when the client ends the session or when the TTL expires.
"""
from __future__ import annotations

import re
import shutil
import threading
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

from app.api.schemas import DocumentResponse, MessageBase
from app.config import settings


SESSION_ID_RE = re.compile(r"^[A-Za-z0-9_-]{12,96}$")


@dataclass
class SessionState:
    id: str
    created_at: datetime
    touched_at: datetime
    storage_dir: Path
    conversations: Dict[str, List[MessageBase]] = field(default_factory=dict)
    documents: List[DocumentResponse] = field(default_factory=list)
    vectorstore: Optional[object] = None
    bm25_retriever: Optional[object] = None
    total_upload_bytes: int = 0

    @property
    def uploads_dir(self) -> Path:
        return self.storage_dir / "uploads"

    @property
    def faiss_dir(self) -> Path:
        return self.storage_dir / "faiss_index"

    @property
    def bm25_path(self) -> Path:
        return self.storage_dir / "bm25_index" / "bm25_retriever.pkl"


class SessionStore:
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.sessions_dir = root_dir / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._sessions: Dict[str, SessionState] = {}

    def get_or_create(self, session_id: str) -> SessionState:
        if not SESSION_ID_RE.match(session_id):
            raise ValueError("Invalid session id.")

        now = _now()
        with self._lock:
            self.cleanup_expired(now=now)
            session = self._sessions.get(session_id)
            if session is None:
                if len(self._sessions) >= settings.max_active_sessions:
                    raise RuntimeError("Too many active sessions. Please try again later.")
                session = SessionState(
                    id=session_id,
                    created_at=now,
                    touched_at=now,
                    storage_dir=self.sessions_dir / session_id,
                )
                session.uploads_dir.mkdir(parents=True, exist_ok=True)
                self._sessions[session_id] = session
            else:
                session.touched_at = now
            return session

    def get_existing(self, session_id: str) -> Optional[SessionState]:
        with self._lock:
            return self._sessions.get(session_id)

    def end(self, session_id: str) -> bool:
        with self._lock:
            session = self._sessions.pop(session_id, None)
        if session is None:
            # The process may have restarted; remove any matching on-disk cache.
            path = self.sessions_dir / session_id
            removed = path.exists()
            _remove_tree(path)
            return removed
        _remove_tree(session.storage_dir)
        return True

    def cleanup_expired(self, now: Optional[datetime] = None) -> int:
        now = now or _now()
        ttl = timedelta(minutes=settings.session_ttl_minutes)
        expired: list[SessionState] = []
        with self._lock:
            for session_id, session in list(self._sessions.items()):
                if now - session.touched_at > ttl:
                    expired.append(self._sessions.pop(session_id))

        for session in expired:
            _remove_tree(session.storage_dir)

        return len(expired)

    def clear_all(self) -> None:
        with self._lock:
            self._sessions.clear()
        _remove_tree(self.sessions_dir)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _remove_tree(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)


session_store = SessionStore(Path(settings.data_dir))
