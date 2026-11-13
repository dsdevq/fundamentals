"""Micro-benchmark for the rate limiters. Run: python benchmarks/bench_ratelimit.py"""

from __future__ import annotations

import time

from syslab.clock import ManualClock
from syslab.ratelimit import SlidingWindowLimiter, TokenBucket

N = 500_000


def bench(label: str, limiter, clock: ManualClock) -> None:
    allowed = 0
    start = time.perf_counter()
    for _ in range(N):
        clock.advance(0.0001)  # 10k req/s offered
        allowed += limiter.allow()
    elapsed = time.perf_counter() - start
    print(
        f"{label:<34} {N / elapsed / 1e6:5.2f} M calls/s  "
        f"({elapsed / N * 1e9:5.0f} ns/call)  allowed {allowed / N:6.1%}"
    )


def main() -> None:
    print("offered load: 10,000 req/s of simulated time; limit: 1,000 req/s")
    c = ManualClock()
    bench("token bucket (cap 1000, 1000/s)", TokenBucket(1000, 1000, clock=c), c)
    c = ManualClock()
    bench("sliding window (1000 per 1s)", SlidingWindowLimiter(1000, 1.0, clock=c), c)

    print("\nmemory shape: window log keeps up to `limit` timestamps; bucket keeps 2 floats")
    c = ManualClock()
    w = SlidingWindowLimiter(100_000, 1.0, clock=c)
    for _ in range(100_000):
        c.advance(1e-6)
        w.allow()
    print(f"sliding window after 100k accepted requests: {len(w._stamps):,} timestamps held")


if __name__ == "__main__":
    main()
