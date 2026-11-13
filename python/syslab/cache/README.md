# LRU cache with TTL

`LRUCache(capacity, ttl=None, clock=...)` in [`lru.py`](lru.py).

## How it works

- One `OrderedDict`: a hash map whose entries are also a doubly linked list. Newest at the right,
  eviction victim at the left. `get`, `put`, `delete` are O(1).
- `get` moves the key to the right end. `put` of a new key into a full cache evicts the left end.
  Overwriting a key refreshes its recency and its TTL.
- TTL: each entry stores `expires_at = now + ttl`. Alive while `now < expires_at`; at exactly
  `expires_at` it is already expired. `get` does **not** renew the TTL (that would be a sliding
  expiry, a different feature).
- Expiry is **lazy**: nothing runs in the background. An expired entry is dropped when it is read,
  or when it reaches the LRU end and gets evicted. `len()` counts dead entries too;
  `purge_expired()` is the O(n) eager sweep.
- `capacity=0` is legal and stores nothing. A single `RLock` guards everything.
- `get_or_load(key, loader)` is read-through with single-flight: concurrent misses on one key
  share one loader call.

## Failure modes

| Mode | What happens |
|---|---|
| Dead entries hold capacity | Lazy expiry: a cache of expired entries is "full" and evicts live ones as new keys arrive. |
| Clock stepped forward | Everything expires early: a miss storm hits the backend. |
| Clock stepped back | Entries live longer than their TTL: stale data served. Use a monotonic clock (the default), not wall time. |
| Thundering herd | A hot key expires, N requests miss together, all call the backend. |
| Loader error | Not cached. Waiters on the in-flight call get the same exception; the next caller retries. |
| Scan pollution | One pass over many cold keys flushes the whole working set. LRU has no scan resistance. |
| Global lock | One lock means reads serialise. Fine here, a bottleneck at high thread counts. |

## Trade-offs

- **Lazy vs eager expiry**: lazy is O(1) and needs no thread, at the cost of memory held by dead
  entries. Eager (timer or heap of expiry times) frees memory sooner and costs complexity.
- **LRU vs LFU vs FIFO**: LRU adapts to recency and is cheap; LFU resists scans but is slow to
  forget old hot keys; FIFO is simplest and ignores reuse entirely (see the `no-touch` switch).
- **TTL jitter**: entries written together expire together. Adding random jitter to the TTL
  spreads the misses; this lab does not, so you can see the cliff.
- **Single-flight** removes the herd within one process only. Across processes you need a lock,
  request coalescing at a proxy, or serving stale while one caller refreshes.

## Failure switches

All in `demos/cache_demo.py` (`python demos/cache_demo.py --switch NAME`). The buggy classes are in
[`faults.py`](faults.py) and are one overridden method each.

| Switch | Demonstrates |
|---|---|
| `baseline` | Correct LRU on a hot-key loop: ~100% hit rate. |
| `wrong-victim` | `EvictsMostRecent`: evicts the newest entry, so the hot key goes first. Hit rate collapses (~4%). |
| `no-touch` | `ForgetsToTouch`: `get` does not refresh recency, so it is FIFO. Same collapse on this loop. |
| `clock-skew` | `SkewedClock`: +1h step expires a live session early; -2h step serves a 60s entry long after its TTL. |
| `herd` | 20 threads miss one key; with single-flight the backend is called once. |
| `herd --no-single-flight` | The same 20 threads call the backend 20 times. |

`python benchmarks/bench_cache.py` prints throughput and the hit-rate gap between the correct
cache and both faulty ones on a skewed workload.

## Questions to be able to answer

Why `OrderedDict` and not a list? What breaks if `put` of an existing key forgets to refresh? Why
is `time.time()` the wrong default clock? How would you add per-key locking to cut contention? How
do you keep the herd from reforming when single-flight's leader fails?
