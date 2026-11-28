import sys

sys.path.insert(0, ".")

from src import backoff  # noqa: E402


def test_schedule_doubles_from_base():
    assert backoff.schedule(base_ms=500, max_attempts=5) == [
        500, 1000, 2000, 4000, 8000
    ]


def test_schedule_is_capped_at_max():
    delays = backoff.schedule(base_ms=500, max_attempts=10, max_ms=5000)
    assert delays[-1] == 5000
    assert max(delays) == 5000


def test_jitter_never_shortens_the_delay():
    for _ in range(50):
        d = backoff.delay_ms(3, base_ms=500, jitter=0.3)
        assert 2000 <= d <= 2600


def test_jitter_is_bounded_by_max():
    d = backoff.delay_ms(20, base_ms=500, max_ms=10_000, jitter=1.0)
    assert d <= 10_000


def test_attempt_must_be_positive():
    try:
        backoff.delay_ms(0)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")


def test_exhausted_at_max_attempts():
    assert backoff.is_exhausted(8, 8) is True
    assert backoff.is_exhausted(7, 8) is False
