"""Persistent shell history with semantic context tracking."""

from __future__ import annotations

import json
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path


@dataclass
class HistoryEntry:
    id: int
    timestamp: float
    user_input: str
    ai_response: str
    model_used: str
    intent: str
    command_executed: str
    exit_code: int | None
    context_id: str


DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    user_input TEXT NOT NULL,
    ai_response TEXT DEFAULT '',
    model_used TEXT DEFAULT '',
    intent TEXT DEFAULT '',
    command_executed TEXT DEFAULT '',
    exit_code INTEGER,
    context_id TEXT DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_history_timestamp ON history(timestamp);
CREATE INDEX IF NOT EXISTS idx_history_intent ON history(intent);
"""


class ShellHistory:
    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or Path.home() / ".osa" / "shell_history.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.executescript(DB_SCHEMA)

    def add(
        self,
        user_input: str,
        ai_response: str = "",
        model_used: str = "",
        intent: str = "",
        command_executed: str = "",
        exit_code: int | None = None,
        context_id: str = "",
    ) -> int:
        cursor = self._conn.execute(
            "INSERT INTO history (timestamp, user_input, ai_response, model_used, "
            "intent, command_executed, exit_code, context_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (time.time(), user_input, ai_response, model_used, intent,
             command_executed, exit_code, context_id),
        )
        self._conn.commit()
        return cursor.lastrowid

    def search(self, query: str, limit: int = 20) -> list[HistoryEntry]:
        cursor = self._conn.execute(
            "SELECT * FROM history WHERE user_input LIKE ? OR command_executed LIKE ? "
            "ORDER BY timestamp DESC LIMIT ?",
            (f"%{query}%", f"%{query}%", limit),
        )
        return [HistoryEntry(*row) for row in cursor.fetchall()]

    def recent(self, limit: int = 50) -> list[HistoryEntry]:
        cursor = self._conn.execute(
            "SELECT * FROM history ORDER BY timestamp DESC LIMIT ?", (limit,)
        )
        return [HistoryEntry(*row) for row in cursor.fetchall()]

    def get_context(self, context_id: str, limit: int = 10) -> list[HistoryEntry]:
        cursor = self._conn.execute(
            "SELECT * FROM history WHERE context_id = ? ORDER BY timestamp DESC LIMIT ?",
            (context_id, limit),
        )
        return [HistoryEntry(*row) for row in cursor.fetchall()]

    def stats(self) -> dict:
        total = self._conn.execute("SELECT COUNT(*) FROM history").fetchone()[0]
        by_intent = dict(self._conn.execute(
            "SELECT intent, COUNT(*) FROM history GROUP BY intent"
        ).fetchall())
        by_model = dict(self._conn.execute(
            "SELECT model_used, COUNT(*) FROM history WHERE model_used != '' GROUP BY model_used"
        ).fetchall())
        return {"total": total, "by_intent": by_intent, "by_model": by_model}

    def close(self):
        self._conn.close()
