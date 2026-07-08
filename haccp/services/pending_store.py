from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

from haccp.config import get_settings
from haccp.models.state import EntryType, MissingField


@dataclass
class PendingEntry:
    chat_id: str
    entry_type: EntryType
    entry_id: str
    sheet_name: str
    row_number: int
    missing: list[MissingField]
    asked_at: float


class PendingStore:
    """SQLite-backed store for missing-field follow-up conversations."""

    def __init__(self, db_path: str | None = None) -> None:
        settings = get_settings()
        self.db_path = Path(db_path or settings.sqlite_path)
        self.ttl_seconds = settings.pending_ttl_seconds
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS pending_entries (
                    chat_id TEXT PRIMARY KEY,
                    entry_type TEXT NOT NULL,
                    entry_id TEXT NOT NULL,
                    sheet_name TEXT NOT NULL,
                    row_number INTEGER NOT NULL,
                    missing_json TEXT NOT NULL,
                    asked_at REAL NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id TEXT,
                    user_id TEXT,
                    entry_type TEXT,
                    entry_id TEXT,
                    action TEXT,
                    details TEXT,
                    created_at REAL NOT NULL
                )
                """
            )

    def save(self, pending: PendingEntry) -> None:
        import json

        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO pending_entries
                (chat_id, entry_type, entry_id, sheet_name, row_number, missing_json, asked_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    pending.chat_id,
                    pending.entry_type,
                    pending.entry_id,
                    pending.sheet_name,
                    pending.row_number,
                    json.dumps([m.model_dump() for m in pending.missing], ensure_ascii=False),
                    pending.asked_at,
                ),
            )

    def get(self, chat_id: str) -> PendingEntry | None:
        import json

        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM pending_entries WHERE chat_id = ?", (chat_id,)
            ).fetchone()
        if not row:
            return None
        if time.time() - row["asked_at"] > self.ttl_seconds:
            self.clear(chat_id)
            return None
        missing = [MissingField(**item) for item in json.loads(row["missing_json"])]
        return PendingEntry(
            chat_id=row["chat_id"],
            entry_type=row["entry_type"],
            entry_id=row["entry_id"],
            sheet_name=row["sheet_name"],
            row_number=row["row_number"],
            missing=missing,
            asked_at=row["asked_at"],
        )

    def clear(self, chat_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM pending_entries WHERE chat_id = ?", (chat_id,))

    def log(
        self,
        *,
        chat_id: str,
        user_id: str,
        entry_type: str,
        entry_id: str,
        action: str,
        details: str = "",
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO audit_log (chat_id, user_id, entry_type, entry_id, action, details, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (chat_id, user_id, entry_type, entry_id, action, details, time.time()),
            )
