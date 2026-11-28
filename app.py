"""Intake HTTP server + worker loop.

Two modes:
  python -m src.app            # serve :8080 and run the worker in a thread
  python -m src.app --once     # drain the queue once and exit (cron friendly)

Deliberately stdlib-only so the repo runs on a bare Droplet with no packages.
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .queue import RelayQueue
from .relay import Relay

DB_PATH = os.environ.get("RELAY_DB", "relay.db")
UPSTREAM_URL = os.environ.get("UPSTREAM_URL", "")
MAX_ATTEMPTS = int(os.environ.get("MAX_ATTEMPTS", "8"))
BASE_DELAY_MS = int(os.environ.get("BASE_DELAY_MS", "500"))

queue = RelayQueue(DB_PATH)


def http_post(event: dict, idempotency_key: str) -> None:
    """Real delivery: POST the stored payload upstream."""
    if not UPSTREAM_URL:
        raise RuntimeError("UPSTREAM_URL is not set")
    body = json.dumps({
        "source": event["source"],
        "payload": json.loads(event["payload"]),
        "event_id": event["id"],
    }).encode()
    req = urllib.request.Request(
        UPSTREAM_URL, data=body, method="POST",
        headers={"Content-Type": "application/json",
                 "Idempotency-Key": idempotency_key},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status >= 300:
                raise RuntimeError(f"upstream {resp.status}")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"upstream {exc.code}") from exc


relay = Relay(queue, http_post, max_attempts=MAX_ATTEMPTS, base_ms=BASE_DELAY_MS)


class Handler(BaseHTTPRequestHandler):
    server_version = "RelayQueue/1.0"

    def _json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802 - stdlib naming
        if self.path.startswith("/hooks/"):
            source = self.path.rsplit("/", 1)[-1] or "unnamed"
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b"{}"
            try:
                payload = json.loads(raw or b"{}")
            except json.JSONDecodeError:
                return self._json(400, {"error": "invalid json"})

            event_id = queue.enqueue(source, payload)
            # 202 only AFTER the row is durable
            return self._json(202, {"accepted": True, "event_id": event_id})

        if self.path.startswith("/dead-letter/") and self.path.endswith("/replay"):
            event_id = self.path.split("/")[2]
            return self._json(200, {"replayed": queue.replay(event_id)})

        return self._json(404, {"error": "not found"})

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            return self._json(200, {"ok": True, "queue": queue.stats()})
        if self.path == "/stats":
            return self._json(200, queue.stats())
        return self._json(404, {"error": "not found"})

    def log_message(self, fmt: str, *args) -> None:
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))


def worker_loop(stop: threading.Event, interval: float = 1.0) -> None:
    while not stop.is_set():
        try:
            relay.drain()
        except Exception as exc:  # noqa: BLE001
            print(f"[worker] {exc}", file=sys.stderr)
        stop.wait(interval)


def main() -> None:
    if "--once" in sys.argv:
        print(relay.drain(limit=50))
        return

    stop = threading.Event()
    t = threading.Thread(target=worker_loop, args=(stop,), daemon=True)
    t.start()
    print(f"intake on :8080, upstream={UPSTREAM_URL or '(unset)'}")
    try:
        ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        time.sleep(0.1)
        queue.close()


if __name__ == "__main__":
    main()
