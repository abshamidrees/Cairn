"""The indexer cursor, which is infrastructure and so lives outside memory.

Brief part 10 draws the line: if a fact influences a verdict it belongs in Sibyl
Memory, and if it is infrastructure it does not. A block cursor influences no
verdict, it only stops the indexer rescanning what it already read, so it is
kept here in a plain SQLite file rather than in a dossier.

Postgres is the production home for this alongside the chain event cache and the
rate-limit counters. SQLite keeps a cold clone runnable without standing a
database up first, and the interface is the same either way.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from types import TracebackType

SCHEMA = """
CREATE TABLE IF NOT EXISTS indexer_cursor (
    name       TEXT PRIMARY KEY,
    block      INTEGER NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
)
"""


class CursorStore:
    """Where the indexer left off, per named stream."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._path)
        self._conn.execute(SCHEMA)
        self._conn.commit()

    def get(self, name: str) -> int | None:
        row = self._conn.execute(
            "SELECT block FROM indexer_cursor WHERE name = ?", (name,)
        ).fetchone()
        return int(row[0]) if row else None

    def set(self, name: str, block: int) -> None:
        self._conn.execute(
            "INSERT INTO indexer_cursor (name, block) VALUES (?, ?) "
            "ON CONFLICT(name) DO UPDATE SET block = excluded.block, "
            "updated_at = datetime('now')",
            (name, block),
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> CursorStore:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()
