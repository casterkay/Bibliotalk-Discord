from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ..domain.errors import IndexError


@dataclass(frozen=True, slots=True)
class SegmentIndexRecord:
    message_id: str
    sha256: str
    status: str


class IngestionIndex:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    @contextmanager
    def _connect(self) -> sqlite3.Connection:
        try:
            conn = sqlite3.connect(self.path)
        except sqlite3.Error as exc:  # noqa: PERF203
            raise IndexError(f"Failed to open ingestion index at {self.path}: {exc}") from exc
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA foreign_keys=ON;")
            yield conn
        finally:
            conn.close()

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sources (
                  user_id TEXT NOT NULL,
                  group_id TEXT NOT NULL,
                  source_fingerprint TEXT,
                  meta_saved INTEGER NOT NULL DEFAULT 0,
                  last_ingested_at TEXT,
                  PRIMARY KEY (user_id, group_id)
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS segments (
                  user_id TEXT NOT NULL,
                  group_id TEXT NOT NULL,
                  message_id TEXT NOT NULL,
                  seq INTEGER NOT NULL,
                  sha256 TEXT NOT NULL,
                  status TEXT NOT NULL,
                  ingested_at TEXT,
                  error_code TEXT,
                  error_message TEXT,
                  PRIMARY KEY (user_id, message_id)
                );
                """
            )
            conn.commit()

    def get_source_meta_saved(self, *, user_id: str, group_id: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT meta_saved FROM sources WHERE user_id = ? AND group_id = ?",
                (user_id, group_id),
            ).fetchone()
            return bool(row[0]) if row else False

    def set_source_meta_saved(self, *, user_id: str, group_id: str, source_fingerprint: str | None = None) -> None:
        now = datetime.now(tz=timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO sources (user_id, group_id, source_fingerprint, meta_saved, last_ingested_at)
                VALUES (?, ?, ?, 1, ?)
                ON CONFLICT(user_id, group_id)
                DO UPDATE SET
                  meta_saved=1,
                  source_fingerprint=COALESCE(excluded.source_fingerprint, sources.source_fingerprint),
                  last_ingested_at=excluded.last_ingested_at;
                """,
                (user_id, group_id, source_fingerprint, now),
            )
            conn.commit()

    def get_segment(self, *, user_id: str, message_id: str) -> SegmentIndexRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT message_id, sha256, status FROM segments WHERE user_id = ? AND message_id = ?",
                (user_id, message_id),
            ).fetchone()
            if not row:
                return None
            return SegmentIndexRecord(message_id=row[0], sha256=row[1], status=row[2])

    def upsert_segment_status(
        self,
        *,
        user_id: str,
        group_id: str,
        message_id: str,
        seq: int,
        sha256: str,
        status: str,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        now = datetime.now(tz=timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO segments (user_id, group_id, message_id, seq, sha256, status, ingested_at, error_code, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, message_id)
                DO UPDATE SET
                  group_id=excluded.group_id,
                  seq=excluded.seq,
                  sha256=excluded.sha256,
                  status=excluded.status,
                  ingested_at=excluded.ingested_at,
                  error_code=excluded.error_code,
                  error_message=excluded.error_message;
                """,
                (user_id, group_id, message_id, seq, sha256, status, now, error_code, error_message),
            )
            conn.commit()
