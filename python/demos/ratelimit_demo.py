"""Flip a failure switch on the rate limiters and watch what happens.

python demos/ratelimit_demo.py --switch burst
python demos/ratelimit_demo.py --switch clock-skew
python demos/ratelimit_demo.py --switch outage --fail open
python demos/ratelimit_demo.py --switch outage --fail closed
python demos/ratelimit_demo.py --switch herd
"""

from __future__ import annotations

import argparse

from syslab.clock import ManualClock, SkewedClock
from syslab.ratelimit import FailPolicy, GuardedLimiter, SlidingWindowLimiter, TokenBucket
from syslab.ratelimit.guard import FlakyLimiter


def burst() -> None:
    """Same sustained rate (5/s), very different burst behaviour."""
    for name, make in (
        ("token bucket cap=20 rate=5/s", lambda c: TokenBucket(20, 5, clock=c)),
        ("sliding window 5 per 1s", lambda c: SlidingWindowLimiter(5, 1.0, clock=c)),
    ):
        clock = ManualClock()
        lim = make(clock)
        ok = sum(lim.allow() for _ in range(30))
        print(f"{name:<32} instant burst of 30 -> {ok} allowed")


def clock_skew() -> None:
    for name, make in (
        ("token bucket", lambda c: TokenBucket(5, 1, clock=c)),
        ("sliding window", lambda c: SlidingWindowLimiter(5, 5.0, clock=c)),
    ):
        base = ManualClock()
        clock = SkewedClock(base)
        lim = make(clock)
        used = sum(lim.allow() for _ in range(5))
        clock.skew(+3600)
        after_fwd = sum(lim.allow() for _ in range(5))
        clock.skew(-7200)
        after_back = sum(lim.allow() for _ in range(5))
        print(
            f"{name:<15} drained {used}; +1h jump -> {after_fwd} allowed; "
            f"then -2h jump -> {after_back} allowed"
        )


def outage(policy: FailPolicy) -> None:
    flaky = FlakyLimiter(TokenBucket(3, 0, clock=ManualClock()))
    guarded = GuardedLimiter(flaky, policy)
    before = [guarded.allow() for _ in range(5)]
    flaky.down = True
    during = [guarded.allow() for _ in range(5)]
    print(f"fail {policy.value}: healthy {before}\n             outage  {during}")


def herd() -> None:
    """1000 clients rejected at t=0 all retry exactly when the bucket refills at t=0.1."""
    clock = ManualClock()
    bucket = TokenBucket(10, 10, clock=clock)
    for _ in range(10):
        bucket.allow()
    clients = 1000
    print(
        f"t=0: bucket drained, {clients} clients told to retry after "
        f"{bucket.retry_after():.1f}s (same value for all)"
    )
    clock.advance(bucket.retry_after())
    ok = sum(bucket.allow() for _ in range(clients))
    print(
        f"t=0.1s: all {clients} retry together -> {ok} allowed, {clients - ok} rejected "
        "again and retrying in lockstep (add jitter to Retry-After)"
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--switch", required=True, choices=["burst", "clock-skew", "outage", "herd"])
    ap.add_argument("--fail", choices=["open", "closed"], default="open")
    a = ap.parse_args()
    if a.switch == "burst":
        burst()
    elif a.switch == "clock-skew":
        clock_skew()
    elif a.switch == "outage":
        outage(FailPolicy(a.fail))
    else:
        herd()


if __name__ == "__main__":
    main()
