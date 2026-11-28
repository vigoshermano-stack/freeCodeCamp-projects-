# Architecture

## Why local-first

A webhook is a promise. The sender believes it was received. If the receiver
acknowledges before persisting, a crash in that window breaks the promise
silently. The whole design here is one rule:

> **Persist before you acknowledge. Always.**

## The four states

| State | Meaning | Leaves via |
|---|---|---|
| `pending` | Stored, waiting for a worker | `claim()` |
| `inflight` | Leased by a worker right now | `ack()` / `fail()` / lease expiry |
| `delivered` | Upstream confirmed | terminal |
| `dead_letter` | Attempts exhausted | `replay()` |

## Why a lease instead of a lock

A lock needs a lock server. A lease is a timestamp: "I own this until T". If the
worker dies, `reclaim_expired()` returns the row to `pending` once T passes. No
broker, no distributed lock, and restart is safe by construction.

Trade-off: an event can be delivered twice if a worker dies *after* the upstream
accepted it but before `ack()`. That is why every attempt carries
`Idempotency-Key: <event_id>` — deduplication is the receiver's job, and it is
cheap when the key is stable.

## Edge tier

The Worker buffers to KV before forwarding. This buys two things:

1. The sender sees a 202 in milliseconds regardless of origin latency.
2. A burst that outruns the origin does not lose events — the KV copy is the
   backup, and the cron re-drives it.

## Failure matrix

| Failure | Effect | Recovery |
|---|---|---|
| Upstream 5xx | Event retried with backoff | Automatic |
| Upstream timeout | Same | Automatic |
| Worker crash mid-delivery | Row stuck `inflight` | Lease expiry → `pending` |
| Origin down entirely | Edge KV holds events | Cron re-drive |
| Persistent bad payload | `dead_letter` after N attempts | Manual `replay` after a fix |

## Backpressure

`claim(limit=...)` is the throttle. If the upstream is slow, the worker simply
claims fewer per pass, and `pending` grows — which is visible in `/stats`. That
is a deliberate design choice: **the queue is the buffer**, so a slow upstream
shows up as a metric instead of a dropped event.
