import math

import pytest

from syslab.clock import ManualClock
from syslab.ratelimit import TokenBucket


def test_starts_full_allows_burst_then_rejects():
    b = TokenBucket(3, 1, clock=ManualClock())
    assert [b.allow() for _ in range(4)] == [True, True, True, False]


def test_refills_at_rate_and_caps_at_capacity():
    clock = ManualClock()
    b = TokenBucket(3, 2, clock=clock)  # 2 tokens/s
    for _ in range(3):
        b.allow()
    clock.advance(0.5)
    assert b.allow() and not b.allow()  # exactly one token earned
    clock.advance(1000)
    assert b.tokens == 3  # never above capacity: idle time cannot be banked


def test_boundary_exactly_enough_time_for_one_token():
    clock = ManualClock()
    b = TokenBucket(1, 1, clock=clock)
    assert b.allow()
    clock.advance(0.999)
    assert not b.allow()
    clock.advance(0.001)
    assert b.allow()


def test_capacity_zero_never_allows():
    clock = ManualClock()
    b = TokenBucket(0, 100, clock=clock)
    clock.advance(10)
    assert not b.allow()


def test_capacity_one():
    clock = ManualClock()
    b = TokenBucket(1, 1, clock=clock)
    assert b.allow() and not b.allow()
    clock.advance(1)
    assert b.allow()


def test_cost_larger_than_capacity_is_never_allowed():
    b = TokenBucket(2, 1, clock=ManualClock())
    assert not b.allow(3)
    assert b.retry_after(3) == math.inf
    assert b.allow(2)


def test_retry_after():
    clock = ManualClock()
    b = TokenBucket(2, 4, clock=clock)
    b.allow(2)
    assert b.retry_after() == pytest.approx(0.25)
    clock.advance(0.25)
    assert b.retry_after() == 0


def test_clock_backwards_grants_nothing_and_does_not_freeze():
    clock = ManualClock(100)
    b = TokenBucket(5, 1, clock=clock)
    for _ in range(5):
        b.allow()
    clock.set(40)  # stepped back 60s
    assert not b.allow()  # no tokens from negative elapsed time
    clock.set(42)  # 2s after the new anchor
    assert b.allow() and b.allow() and not b.allow()


def test_forward_jump_refills_fully_clock_skew_hazard():
    clock = ManualClock()
    b = TokenBucket(5, 1, clock=clock)
    for _ in range(5):
        b.allow()
    clock.advance(3600)  # a skew / NTP step forward
    assert b.tokens == 5  # the whole burst is available again


def test_invalid_args():
    with pytest.raises(ValueError):
        TokenBucket(-1, 1)
    with pytest.raises(ValueError):
        TokenBucket(1, -1)
