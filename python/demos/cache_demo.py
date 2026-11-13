"""Flip a failure switch on the cache and watch what happens.

python demos/cache_demo.py --switch wrong-victim
python demos/cache_demo.py --switch no-touch
python demos/cache_demo.py --switch clock-skew
python demos/cache_demo.py --switch herd
python demos/cache_demo.py --switch herd --no-single-flight
"""

from __future__ import annotations

import argparse
import threading
import time

from syslab.cache import LRUCache
from syslab.cache.faults import EvictsMostRecent, ForgetsToTouch
from syslab.clock import ManualClock, SkewedClock


def loop_workload(cache) -> None:
    """A hot key (0) read between every cold write: the textbook LRU-friendly pattern."""
    cache.put(0, "hot")
    for cold in range(1, 50):
        cache.put(cold, "cold")
        cache.get(0)
    print(f"hit rate {cache.hits / (cache.hits + cache.misses):.0%}, evictions {cache.evictions}")


def clock_skew() -> None:
    clock = ManualClock(1000)
    skewed = SkewedClock(clock)
    cache = LRUCache[str, str](4, ttl=60, clock=skewed)
    cache.put("session", "alice")
    print("t=0s    session ->", cache.get("session"))
    skewed.skew(+3600)
    print("clock stepped +1h  ->", cache.get("session"), "(valid session thrown away early)")
    cache.put("session", "alice")
    skewed.skew(-7200)
    clock.advance(500)
    print(
        "clock stepped -2h, 500s real time later ->",
        cache.get("session"),
        "(60s TTL entry still served: stale data)",
    )


def herd(single_flight: bool, threads: int = 20) -> None:
    cache = LRUCache[str, int](8)
    calls = 0
    lock = threading.Lock()

    def slow_backend(key: str) -> int:
        nonlocal calls
        with lock:
            calls += 1
        time.sleep(0.2)
        return 1

    workers = [
        threading.Thread(target=cache.get_or_load, args=("k", slow_backend, single_flight))
        for _ in range(threads)
    ]
    for t in workers:
        t.start()
    for t in workers:
        t.join()
    print(f"{threads} concurrent misses, single_flight={single_flight}: backend called {calls}x")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument(
        "--switch",
        required=True,
        choices=["baseline", "wrong-victim", "no-touch", "clock-skew", "herd"],
    )
    ap.add_argument("--no-single-flight", action="store_true")
    a = ap.parse_args()
    if a.switch == "baseline":
        loop_workload(LRUCache(3))
    elif a.switch == "wrong-victim":
        loop_workload(EvictsMostRecent(3))
    elif a.switch == "no-touch":
        loop_workload(ForgetsToTouch(3))
    elif a.switch == "clock-skew":
        clock_skew()
    else:
        herd(single_flight=not a.no_single_flight)


if __name__ == "__main__":
    main()
