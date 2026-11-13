import math

import pytest

from syslab.clock import ManualClock
from syslab.ratelimit import SlidingWindowLimiter


def test_allows_limit_then_rejects():
    w = SlidingWindowLimiter(3, 10, clock=ManualClock())
    assert [w.allow() for _ in range(4)] == [True, True, True, False]


def test_boundary_request_leaves_window_exactly_at_t_plus_window():
    clock = ManualClock()
    w = SlidingWindowLimiter(1, 10, clock=clock)
    assert w.allow()
    clock.set(9.999)
    assert not w.allow()
    clock.set(10)
    assert w.allow()


def test_is_exact_across_a_fixed_window_boundary():
    # A fixed window of 10s would allow 3 at t=9 and 3 more at t=11 (6 in 2s). Not here.
    clock = ManualClock()
    w = SlidingWindowLimiter(3, 10, clock=clock)
    clock.set(9)
    assert [w.allow() for _ in range(3)] == [True] * 3
    clock.set(11)
    assert not w.allow()
    clock.set(19)
    assert w.allow()


def test_rejected_requests_are_not_recorded():
    clock = ManualClock()
    w = SlidingWindowLimiter(1, 10, clock=clock)
    assert w.allow()
    clock.set(5)
    assert not w.allow()  # must not push the window forward
    clock.set(10)
    assert w.allow()


def test_limit_zero_and_one():
    assert not SlidingWindowLimiter(0, 1, clock=ManualClock()).allow()
    assert SlidingWindowLimiter(0, 1, clock=ManualClock()).retry_after() == math.inf
    w = SlidingWindowLimiter(1, 1, clock=ManualClock())
    assert w.allow() and not w.allow()


def test_retry_after():
    clock = ManualClock()
    w = SlidingWindowLimiter(1, 10, clock=clock)
    assert w.retry_after() == 0
    w.allow()
    clock.set(4)
    assert w.retry_after() == pytest.approx(6)


def test_clock_backwards_freezes_time_and_never_loosens():
    clock = ManualClock(100)
    w = SlidingWindowLimiter(2, 10, clock=clock)
    assert w.allow() and w.allow()
    clock.set(0)  # stepped back 100s
    assert not w.allow()
    clock.set(105)
    assert not w.allow()
    clock.set(110)
    assert w.allow()


def test_memory_is_bounded_by_limit():
    clock = ManualClock()
    w = SlidingWindowLimiter(5, 10, clock=clock)
    for i in range(1000):
        clock.set(i * 0.01)
        w.allow()
    assert len(w._stamps) <= 5


def test_invalid_args():
    with pytest.raises(ValueError):
        SlidingWindowLimiter(-1, 1)
    with pytest.raises(ValueError):
        SlidingWindowLimiter(1, 0)
