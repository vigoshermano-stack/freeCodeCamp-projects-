"""Exponential backoff with jitter.

Kept dependency-free and deterministic (when a seed is supplied) so the retry
schedule is unit-testable.
"""

from __future__ import annotations

import random

DEFAULT_BASE_MS = 500
DEFAULT_MAX_MS = 300_000
DEFAULT_JITTER = 0.30


def delay_ms(attempt: int, base_ms: int = DEFAULT_BASE_MS,
             max_ms: int = DEFAULT_MAX_MS,
             jitter: float = DEFAULT_JITTER,
             rng: random.Random | None = None) -> int:
    """Return the delay before retry number ``attempt`` (1-based).

    The nominal delay doubles each attempt. Jitter is applied *upward only*
    (a fraction of the nominal delay is added) so the delay is never shorter
    than the published schedule.
    """
    if attempt < 1:
        raise ValueError("attempt must be >= 1")
    if base_ms <= 0:
        raise ValueError("base_ms must be positive")
    if jitter < 0:
        raise ValueError("jitter must be >= 0")

    nominal = base_ms * (2 ** (attempt - 1))
    nominal = min(nominal, max_ms)

    if jitter == 0:
        return int(nominal)

    r = rng or random
    extra = nominal * jitter * r.random()
    return int(min(nominal + extra, max_ms))


def is_exhausted(attempt: int, max_attempts: int) -> bool:
    """True when no further retry should be scheduled."""
    return attempt >= max_attempts


def schedule(base_ms: int = DEFAULT_BASE_MS, max_attempts: int = 8,
             max_ms: int = DEFAULT_MAX_MS) -> list[int]:
    """Deterministic (no jitter) schedule, useful for docs and assertions."""
    out = []
    for attempt in range(1, max_attempts + 1):
        out.append(delay_ms(attempt, base_ms=base_ms, max_ms=max_ms, jitter=0))
    return out
