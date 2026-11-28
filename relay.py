"""Delivery orchestration.

The HTTP call is injected (``post``) so the loop can be tested without a
network. Every attempt sends the same ``Idempotency-Key`` derived from the
event id, so the upstream can de-duplicate retries.
"""

from __future__ import annotations

from typing import Callable

from . import backoff
from .queue import RelayQueue, DELIVERED


class DeliveryError(Exception):
    """Raised by a post function when the upstream rejects the event."""


class Relay:
    def __init__(self, queue: RelayQueue, post: Callable[[dict, str], None],
                 max_attempts: int = 8, base_ms: int = 500) -> None:
        self.queue = queue
        self.post = post
        self.max_attempts = max_attempts
        self.base_ms = base_ms

    def drain(self, limit: int = 10) -> dict[str, int]:
        """One pass: claim, attempt, ack or reschedule."""
        self.queue.reclaim_expired()
        events = self.queue.claim(limit=limit)
        done = failed = 0

        for event in events:
            attempt = event["attempts"] + 1
            try:
                self.post(event, event["id"])  # id doubles as idempotency key
            except Exception as exc:  # noqa: BLE001 - one bad event must not
                delay = backoff.delay_ms(        # stop the whole batch
                    attempt, base_ms=self.base_ms
                ) / 1000.0
                self.queue.fail(event["id"], str(exc), delay,
                                max_attempts=self.max_attempts)
                failed += 1
            else:
                self.queue.ack(event["id"])
                done += 1

        return {"delivered": done, "failed": failed,
                "state": "ok" if not failed else "degraded"}

    def state_of(self, event_id: str) -> str | None:
        row = self.queue.conn.execute(
            "SELECT state FROM events WHERE id = ?", (event_id,)
        ).fetchone()
        return row["state"] if row else None

    def is_delivered(self, event_id: str) -> bool:
        return self.state_of(event_id) == DELIVERED
