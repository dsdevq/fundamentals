# Fundamentals
A systems-fundamentals lab: small standard-library reference implementations of classic interview systems (an LRU cache with TTL and rate limiters), each with tests, a benchmark and failure-injection switches, plus a separate folder for the owner's hand-written solutions. The glossary covers the `syslab` Python package and the exercises rule.

## Language

**Lab**:
The agent-built `python/` part (package `syslab`), written to be read, broken and reasoned about, not copied.
_Avoid_: Python systems lab, systems fundamentals lab (README titles for the same thing)

**Exercises**:
The `exercises/` folder: the owner's hand-written rate limiter and LRU/TTL cache, starting empty with only test skeletons.

**AI reviews, never writes**:
The rule for the exercises folder: AI may review, question and suggest tests, but no AI-generated solution code goes there.

**Clock**:
An injectable zero-argument callable returning seconds as a float; every time-dependent class takes `clock=`. Production uses the monotonic clock.

**ManualClock**:
A clock that moves only when told to and may go backwards (`advance`, `set`); used by tests and demos.

**SkewedClock**:
A clock wrapper that adds an offset, simulating a wall-clock step (`skew(+3600)`, `skew(-5)`).

**LRUCache**:
A fixed-capacity cache that evicts the least recently used entry, with an optional per-entry TTL. One `OrderedDict` plus a single `RLock`.

**TTL**:
Per-entry time to live: an entry stores `expires_at = now + ttl`, is alive while `now < expires_at`, and a read does not renew it.

**Lazy expiry**:
Expired entries are dropped only when read or when they reach the eviction end; nothing runs in the background and `len()` counts dead entries. `purge_expired()` is the eager sweep.

**Single-flight**:
In `get_or_load`, concurrent misses on one key share a single loader call.
_Avoid_: request coalescing (named in the README only for the cross-process alternative)

**Thundering herd**:
Many requests missing a hot key together and all calling the backend; also the rate-limiter variant where every rejected client retries at the same instant.

**Token bucket**:
`TokenBucket(capacity, refill_rate)`: a bucket that starts full, charges `cost` tokens per request and refills lazily; allows a burst up to `capacity`, then the sustained rate.

**Sliding-window log**:
`SlidingWindowLimiter(limit, window)`: keeps timestamps of accepted requests and accepts while fewer than `limit` fall inside `window`. Exact, with O(limit) memory.

**retry_after**:
How long a rejected caller should wait before the next request would be allowed.

**Fail open / fail closed**:
The decision when the limiter itself breaks: `FailPolicy.OPEN` lets traffic through, `FailPolicy.CLOSED` rejects it.

**GuardedLimiter**:
A wrapper that applies a `FailPolicy` when its inner limiter raises, counting `errors`.

**FlakyLimiter**:
A test double with a `down` switch that makes `allow` raise, simulating a backend outage.

**Failure switch**:
A named `--switch` option on a demo that turns on one plausible failure so its effect can be observed (`wrong-victim`, `no-touch`, `clock-skew`, `herd`, `burst`, `outage`).

**Failure-injection variant**:
A single-method buggy subclass of `LRUCache` in `faults.py` (`EvictsMostRecent`, `ForgetsToTouch`) behind a failure switch.

## Relationships
- The **Lab** is studied by running a **Failure switch**, predicting the outcome, then reading the test that pins it.
- A **Failure switch** such as `wrong-victim` or `no-touch` selects a **Failure-injection variant** of **LRUCache**; `clock-skew` uses **SkewedClock**; `outage` uses **FlakyLimiter**.
- **LRUCache**, **TokenBucket** and **SlidingWindowLimiter** all take a **Clock**, which tests replace with **ManualClock**.
- **LRUCache** combines **TTL** with **Lazy expiry** and **Single-flight** loading to limit a **Thundering herd** within one process.
- A **GuardedLimiter** wraps a limiter and chooses **Fail open** or **Fail closed** via **FailPolicy**.
- The **Exercises** folder mirrors the **Lab**'s two topics but is written by hand under the **AI reviews, never writes** rule.

## Flagged ambiguities
- "Retry herd" (ratelimit/README.md failure table), "herd" (switch name) and "Thundering herd" (cache/README.md) name the same stampede pattern in two components.
- The same limiter is "fail-open / fail-closed" in prose (ratelimit/README.md), `OPEN`/`CLOSED` in `FailPolicy` (guard.py:13-15), and `--fail open|closed` on the demo.
