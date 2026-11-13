from syslab.clock import ManualClock
from syslab.ratelimit import FailPolicy, GuardedLimiter, TokenBucket
from syslab.ratelimit.guard import FlakyLimiter


def _setup(policy: FailPolicy):
    flaky = FlakyLimiter(TokenBucket(1, 0, clock=ManualClock()))
    return flaky, GuardedLimiter(flaky, policy)


def test_healthy_backend_is_just_the_limiter():
    _, g = _setup(FailPolicy.CLOSED)
    assert g.allow() and not g.allow() and g.errors == 0


def test_fail_open_lets_everything_through_during_outage():
    flaky, g = _setup(FailPolicy.OPEN)
    assert g.allow()  # uses the only token
    flaky.down = True
    assert all(g.allow() for _ in range(100))  # no protection at all
    assert g.errors == 100


def test_fail_closed_rejects_everything_during_outage():
    flaky, g = _setup(FailPolicy.CLOSED)
    flaky.down = True
    assert not any(g.allow() for _ in range(100))  # full outage for legit users too


def test_recovers_when_backend_returns():
    flaky, g = _setup(FailPolicy.CLOSED)
    flaky.down = True
    assert not g.allow()
    flaky.down = False
    assert g.allow()
