import sys

sys.path.insert(0, ".")

from src.queue import RelayQueue, PENDING, DELIVERED, DEAD  # noqa: E402
from src.relay import Relay  # noqa: E402


def make_queue():
    return RelayQueue(":memory:")


def test_enqueue_persists_before_ack():
    q = make_queue()
    eid = q.enqueue("orders", {"order_id": 1})
    assert q.stats()[PENDING] == 1
    row = q.conn.execute("SELECT payload FROM events WHERE id=?", (eid,)).fetchone()
    assert '"order_id": 1' in row["payload"]


def test_claim_moves_to_inflight():
    q = make_queue()
    q.enqueue("orders", {})
    claimed = q.claim(limit=5)
    assert len(claimed) == 1
    assert q.stats()["inflight"] == 1


def test_claim_does_not_double_lease():
    q = make_queue()
    q.enqueue("orders", {})
    first = q.claim(limit=5)
    second = q.claim(limit=5)
    assert len(first) == 1
    assert second == []


def test_ack_marks_delivered():
    q = make_queue()
    eid = q.enqueue("orders", {})
    q.claim()
    q.ack(eid)
    assert q.stats()[DELIVERED] == 1


def test_fail_schedules_retry():
    q = make_queue()
    eid = q.enqueue("orders", {})
    q.claim()
    state = q.fail(eid, "boom", next_delay_s=0.0, max_attempts=8)
    assert state == PENDING
    assert q.conn.execute(
        "SELECT attempts FROM events WHERE id=?", (eid,)
    ).fetchone()["attempts"] == 1


def test_fail_dead_letters_after_max_attempts():
    q = make_queue()
    eid = q.enqueue("orders", {})
    state = None
    for _ in range(3):
        q.claim()
        state = q.fail(eid, "boom", next_delay_s=0.0, max_attempts=3)
    assert state == DEAD
    assert len(q.dead_letters()) == 1


def test_reclaim_returns_expired_lease_to_pending():
    q = make_queue()
    q.enqueue("orders", {})
    q.claim(lease_seconds=-1)  # already expired
    reclaimed = q.reclaim_expired()
    assert reclaimed == 1
    assert q.stats()[PENDING] == 1


def test_replay_requeues_dead_letter():
    q = make_queue()
    eid = q.enqueue("orders", {})
    q.claim()
    q.fail(eid, "boom", 0.0, max_attempts=1)
    assert q.replay(eid) is True
    assert q.stats()[PENDING] == 1


def test_relay_delivers_and_acks():
    q = make_queue()
    seen = []
    relay = Relay(q, lambda event, key: seen.append(key))
    eid = q.enqueue("orders", {"n": 1})
    result = relay.drain()
    assert result["delivered"] == 1
    assert relay.is_delivered(eid)
    assert seen == [eid]  # idempotency key equals event id


def test_relay_retries_failed_delivery():
    q = make_queue()

    def boom(event, key):
        raise RuntimeError("upstream 503")

    relay = Relay(q, boom, max_attempts=3, base_ms=10)
    eid = q.enqueue("orders", {})
    relay.drain()
    assert relay.state_of(eid) == PENDING


def test_relay_one_bad_event_does_not_stop_batch():
    q = make_queue()
    calls = []

    def flaky(event, key):
        calls.append(key)
        if len(calls) == 1:
            raise RuntimeError("first fails")

    relay = Relay(q, flaky, max_attempts=5)
    a = q.enqueue("orders", {})
    b = q.enqueue("orders", {})
    result = relay.drain()
    assert result["delivered"] == 1
    assert result["failed"] == 1
    assert relay.is_delivered(b) or relay.is_delivered(a)
