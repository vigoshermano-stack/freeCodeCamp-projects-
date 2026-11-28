"""SQLite-backed durable queue.

State machine:

    pending --claim--> inflight --ack--> delivered
                          |
                          +--fail--> pending (retry) or dead_letter

Rows in ``inflight`` are leased. If a worker dies, ``reclaim_expired`` returns
those rows to ``pending`` once the lease elapses, which is what makes restart
safe without a separate broker.
"""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from typing import Any, Iterable

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id            TEXT PRIMARY KEY,
    source        TEXT NOT NULL,
    payload       TEXT NOT NULL,
    state         TEXT NOT NULL DEFAULT 'pending',
    attempts      INTEGER NOT NULL DEFAULT 0,
    next_attempt  REAL NOT NULL DEFAULT 0,
    leased_until  REAL,
    last_error    TEXT,
    created_at    REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_ready
    ON events (state, next_attempt);
"""

PENDING = "pending"
INFLIGHT = "inflight"
DELIVERED = "delivered"
DEAD = "dead_letter"


class RelayQueue:
    def __init__(self, path: str = ":memory:") -> None:
        self.conn = sqlite3.connect(path, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)

    # ---------- intake ----------

    def enqueue(self, source: str, payload: dict[str, Any]) -> str:
        """Persist an event and return its id. Must be called *before* acking
        the sender, so an accepted webhook can never be lost."""
        event_id = uuid.uuid4().hex
        self.conn.execute(
            "INSERT INTO events (id, source, payload, created_at) "
            "VALUES (?, ?, ?, ?)",
            (event_id, source, json.dumps(payload, sort_keys=True), time.time()),
        )
        return event_id

    # ---------- worker ----------

    def claim(self, limit: int = 10, lease_seconds: float = 60.0) -> list[dict]:
        """Atomically lease up to ``limit`` ready events."""
        now = time.time()
        rows = self.conn.execute(
            "SELECT * FROM events WHERE state = ? AND next_attempt <= ? "
            "ORDER BY next_attempt LIMIT ?",
            (PENDING, now, limit),
        ).fetchall()

        claimed = []
        for row in rows:
            cur = self.conn.execute(
                "UPDATE events SET state = ?, leased_until = ? "
                "WHERE id = ? AND state = ?",
                (INFLIGHT, now + lease_seconds, row["id"], PENDING),
            )
            if cur.rowcount == 1:  # only the worker that won the update owns it
                claimed.append(dict(row))
        return claimed

    def ack(self, event_id: str) -> None:
        self.conn.execute(
            "UPDATE events SET state = ?, leased_until = NULL, last_error = NULL "
            "WHERE id = ?",
            (DELIVERED, event_id),
        )

    def fail(self, event_id: str, error: str, next_delay_s: float,
             max_attempts: int = 8) -> str:
        """Record a failed attempt and schedule the retry (or dead-letter)."""
        row = self.conn.execute(
            "SELECT attempts FROM events WHERE id = ?", (event_id,)
        ).fetchone()
        if row is None:
            raise KeyError(event_id)

        attempts = row["attempts"] + 1
        state = DEAD if attempts >= max_attempts else PENDING
        self.conn.execute(
            "UPDATE events SET state = ?, attempts = ?, last_error = ?, "
            "leased_until = NULL, next_attempt = ? WHERE id = ?",
            (state, attempts, str(error)[:500], time.time() + next_delay_s,
             event_id),
        )
        return state

    # ---------- recovery ----------

    def reclaim_expired(self, now: float | None = None) -> int:
        """Return crashed workers' leases to pending.

        This is the whole crash-safety story: no broker, no external lock.
        """
        now = time.time() if now is None else now
        cur = self.conn.execute(
            "UPDATE events SET state = ?, leased_until = NULL "
            "WHERE state = ? AND leased_until IS NOT NULL AND leased_until < ?",
            (PENDING, INFLIGHT, now),
        )
        return cur.rowcount

    # ---------- inspection ----------

    def stats(self) -> dict[str, int]:
        rows = self.conn.execute(
            "SELECT state, COUNT(*) AS n FROM events GROUP BY state"
        ).fetchall()
        base = {PENDING: 0, INFLIGHT: 0, DELIVERED: 0, DEAD: 0}
        base.update({r["state"]: r["n"] for r in rows})
        return base

    def replay(self, event_id: str) -> bool:
        cur = self.conn.execute(
            "UPDATE events SET state = ?, attempts = 0, next_attempt = 0, "
            "last_error = NULL WHERE id = ? AND state = ?",
            (PENDING, event_id, DEAD),
        )
        return cur.rowcount == 1

    def dead_letters(self) -> Iterable[dict]:
        rows = self.conn.execute(
            "SELECT * FROM events WHERE state = ? ORDER BY created_at", (DEAD,)
        ).fetchall()
        return [dict(r) for r in rows]

    def close(self) -> None:
        self.conn.close()
