# Rate limiters

`TokenBucket` ([`token_bucket.py`](token_bucket.py)), `SlidingWindowLimiter`
([`sliding_window.py`](sliding_window.py)), and `GuardedLimiter` ([`guard.py`](guard.py)) for the
fail-open / fail-closed decision. Single key each: one limiter instance per client, route or
tenant.

## How they work

**Token bucket** `TokenBucket(capacity, refill_rate)`. A bucket holds up to `capacity` tokens and
starts full. Each request takes `cost` tokens, or is rejected. Refill is computed lazily on each
call: `tokens = min(capacity, tokens + elapsed * rate)`. State is two numbers; O(1).
Allows a burst of `capacity`, then the sustained `refill_rate`. Idle time cannot be banked beyond
`capacity`.

**Sliding-window log** `SlidingWindowLimiter(limit, window)`. Keeps the timestamps of accepted
requests; drops those with `now - t >= window`; accepts if fewer than `limit` remain. Exact: no
interval of length `window` ever has more than `limit` accepted requests. O(limit) memory.
Rejected requests are not recorded.

**Guard** `GuardedLimiter(inner, FailPolicy.OPEN | CLOSED)`. If the limiter raises (think: its
Redis is down), `OPEN` allows the request and `CLOSED` rejects it.

## Failure modes

| Mode | What happens |
|---|---|
| Clock forward jump | Token bucket refills to full: a whole fresh burst. Window log expires everything. |
| Clock backward jump | Bucket grants nothing for that call and re-anchors (no freeze, no double count). Window log freezes time until the clock catches up, so it gets *stricter*. |
| Burst at the edge | A fixed-window counter allows 2x `limit` across a boundary. The window log does not; the bucket allows `capacity` by design. |
| Retry herd | Every rejected client is told the same `retry_after` and returns together. Add jitter. |
| Limiter outage | Fail open: no protection exactly when the backend may be overloaded. Fail closed: your limiter is now a single point of failure for your whole API. |
| Distributed use | These are per-process. N servers each with limit L allow N*L overall; sharing state brings races (read-modify-write needs an atomic op or a Lua script). |

## Trade-offs

| | Token bucket | Sliding-window log |
|---|---|---|
| Memory | O(1) | O(limit) |
| Burst | Up to `capacity`, tunable | None beyond `limit` per window |
| Accuracy | Rate is exact over time; bursts are permitted | Exact per window |
| Good for | APIs where short bursts are fine | Strict quotas, small limits |

Other options not implemented: fixed-window counter (cheapest, boundary 2x burst),
sliding-window counter (two counters weighted by overlap: O(1), approximate), leaky bucket (smooths
output instead of permitting bursts).

**Fail open or closed?** Open for protection that is "nice to have" (public read APIs, where an
outage of the limiter should not become an outage of the product). Closed when the limit protects
something that cannot take the overload (a payment provider, a login endpoint under brute force).

## Failure switches

`python demos/ratelimit_demo.py --switch NAME`

| Switch | Demonstrates |
|---|---|
| `burst` | Same 5/s sustained rate: bucket (cap 20) lets 20 through instantly, the window lets 5. |
| `clock-skew` | `SkewedClock`: +1h refills both fully; -2h leaves both limiters rejecting. |
| `outage --fail open` | Backend down: every request allowed, `FlakyLimiter.down = True`. |
| `outage --fail closed` | Backend down: every request rejected. |
| `herd` | 1000 clients retry at the same instant after a drained bucket: 1 allowed, 999 retry again in lockstep. |

`python benchmarks/bench_ratelimit.py` prints per-call cost and allowed fraction for both limiters
at 10x overload, and the window log's memory growth.

## Questions to be able to answer

Why lazy refill instead of a timer thread? Why is the bucket's `retry_after` the right value for a
`Retry-After` header and why does it still cause a herd? How would you make this correct across
servers (Redis `INCR`+`EXPIRE`, a Lua script, or a local bucket that periodically leases tokens)?
What does each limiter do when `cost > capacity`?
