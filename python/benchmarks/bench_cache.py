"""Micro-benchmark for LRUCache. Run: python benchmarks/bench_cache.py"""

from __future__ import annotations

import random
import time

from syslab.cache import LRUCache
from syslab.cache.faults import EvictsMostRecent, ForgetsToTouch

N = 200_000


def timed(label: str, fn) -> None:
    start = time.perf_counter()
    fn()
    elapsed = time.perf_counter() - start
    print(f"{label:<44} {N / elapsed / 1e6:6.2f} M ops/s  ({elapsed / N * 1e9:6.0f} ns/op)")


def zipf_keys(n: int, universe: int) -> list[int]:
    rng = random.Random(1)
    weights = [1 / (i + 1) for i in range(universe)]
    return rng.choices(range(universe), weights=weights, k=n)


def hit_rate(cache_cls, keys: list[int], capacity: int) -> float:
    c = cache_cls(capacity)
    for k in keys:
        if c.get(k) is None:
            c.put(k, k)
    return c.hits / (c.hits + c.misses)


def main() -> None:
    print("== throughput ==")
    c = LRUCache[int, int](10_000)
    for i in range(10_000):
        c.put(i, i)
    rng = random.Random(2)
    keys = [rng.randrange(10_000) for _ in range(N)]
    timed("get, 100% hits", lambda: [c.get(k) for k in keys])  # list-comp overhead included
    timed("put, steady-state eviction", lambda: [c.put(k + 10_000, k) for k in keys])
    ttl = LRUCache[int, int](10_000, ttl=60)
    timed("put with TTL", lambda: [ttl.put(k, k) for k in keys])

    print("\n== hit rate on a skewed (Zipf) workload, capacity 100 of 10,000 keys ==")
    ks = zipf_keys(N, 10_000)
    for cls in (LRUCache, ForgetsToTouch, EvictsMostRecent):
        print(f"{cls.__name__:<20} {hit_rate(cls, ks, 100):6.1%}")


if __name__ == "__main__":
    main()
