---
name: coding-resilience
description: Use when code depends on any external resource that can be absent, slow, flaky, rate-limited, or vanish mid-run - a network connection, remote service or HTTP/REST API, proxy, DNS name, database or connection pool, mount, disk space, CPU/memory headroom, or SSH/VNC session. Keywords - retry, backoff, jitter, timeout, health check, circuit breaker, graceful degradation, self-healing, pool eviction, rate limit, 429, connection reset, flaky, hang. For where resilience lives in a layered app see coding-python-clean-architecture; for library picks see coding-python-use-modern-libraries.
---

# Design for self-healing; never assume an external resource is up

## Overview

No external resource is guaranteed. A connection, remote service, API, proxy, DNS name, disk,
CPU/memory, mount, or DB pool can be absent, slow, flaky, rate-limited, or vanish mid-run. Never
treat one as granted or stable. Build the self-healing in from the start instead of coding the
happy path and bolting on error handling later. Resilience lives at the I/O boundary (the adapter),
not in the domain - see `bitranox:coding-python-clean-architecture`.

## When to use

- Calling a network service, HTTP/REST API, proxy, or DNS name.
- Reading/writing a DB, connection pool, mount, or remote filesystem.
- Driving a remote host over SSH (`bitranox:compuse-ssh`) or VNC (`bitranox:compuse-vnc`).
- Bulk-fetching from a host that throttles per IP (see `bitranox:net-rotating-proxies`).
- A heavy step that needs disk / CPU / memory headroom that may not be there.
- Any adapter sitting at an I/O boundary.

## Patterns

For the modern Python pick behind each, see `bitranox:coding-python-use-modern-libraries`.

- **Retry with backoff + jitter, always under a hard timeout.** Retry only transient failures
  (timeouts, connection resets, 429/503); never retry a deterministic 4xx. Exponential backoff with
  random jitter avoids a thundering herd. Cap the attempts AND put a timeout on every individual
  wait and on the whole operation - an unbounded retry with no timeout is a hang, not resilience.
  Python: `tenacity` (`@retry(stop=stop_after_attempt(n), wait=wait_exponential_jitter())`); set an
  explicit client timeout (`httpx2.Client(timeout=...)`) and `asyncio.wait_for(coro, timeout=)`.
- **Health-check, evict, replace.** Probe a member before/while using it; drop a faulty, flaky, or
  slow one and pull in a fresh one. Track per-member success/failure and evict on a failure ratio,
  not just on a hard-dead connection.
- **Maintain a pool at a target size with margin.** Keep ~100% spare so the fast healthy members
  carry the load and the rest are warm backup; rotate so no single member is hammered. Worked
  example: `bitranox:net-rotating-proxies` (right-sized, speed-weighted pick, evict-on-failure).
- **Rediscover; do not trust a cached list.** Re-resolve / re-validate endpoints each run -
  yesterday's live host may be dead now. A cached endpoint list is a stale assumption.
- **Top up to the target in the background** so attrition is invisible to the running work.
- **Circuit breaker for a repeatedly-failing dependency.** After N consecutive failures, OPEN the
  circuit: fail fast (or serve a fallback) instead of hammering a dead service; after a cool-off,
  try one probe (HALF-OPEN) and CLOSE on success. Stops one sick dependency cascading into a stall.
- **Before automating a DISRUPTIVE remedy (reboot, driver reload, service restart), check whether
  past occurrences STARTED during that same remedy.** A remedy that is also a trigger can loop: each
  reboot "fixes" the hang by inducing the next one. Climb cheaper rungs first (probe, soft reset,
  service restart) before the disruptive one, cap the number of remedy attempts per episode so a
  loop cannot run forever, and order the refusal/guard checks so every refusal branch is actually
  REACHABLE - a broad earlier check that shadows a narrower one placed after it means that branch
  never fires and the disruptive remedy runs anyway.
- **Degrade gracefully.** On partial failure return a partial result + a clear warning + a non-zero
  exit - never a silent wrong answer. If a target resolves somewhere unexpected (e.g. a public host
  to an internal IP), say so.
- **Guard resources.** Cap concurrency, memory, and payload/collection size (unbounded input is a
  DoS vector - see `bitranox:coding-input-sanitization`). Check disk / CPU / memory headroom before
  a heavy step (`shutil.disk_usage`, `os.cpu_count`, load) rather than assuming it is there; stream
  or paginate large data instead of materializing it whole.
- **ISOLATE each item in a batch of INDEPENDENT tasks.** A loop over N unrelated units (sync 38
  apps, poll 20 hosts) must not let one failure end the run. `set -euo pipefail` around such a loop
  does exactly that: the FIRST failing unit aborts the script, every later unit silently never runs,
  and the log shows no error because nothing errored - it stopped. The symptom is "sometimes only
  some of them updated", which reads like a flaky dependency and is not. Catch per unit, record the
  failure with the unit's name, keep going, and exit non-zero at the END with a tally. Reserve
  fail-fast for a genuine DEPENDENCY chain, where later steps are meaningless once one fails.

## Python asyncio: two shutdowns that hang instead of failing

Both raise nothing: `stop()` simply never returns, and the service manager kills the process when
its stop timeout expires. Bound every wait in the stop path (`asyncio.timeout(...)`), keeping their
sum under that stop timeout (systemd `TimeoutStopSec`), so the hang becomes an error, and check
these two first.

- **A cancel of a task that is awaiting another task arrives THROUGH the awaited child.**
  `parent.cancel()` cancels the child the parent is suspended on, and the parent then sees the
  child's `CancelledError`. So `try: await child except CancelledError:`, written for "the child
  was cancelled, restart it", also catches the parent's OWN cancellation and swallows it; the
  parent loops on, and whatever gathers it waits forever. Prefer waiting without raising the
  child's outcome: the two cancels can then never be confused, and a crash arrives as
  `child.exception()` to inspect rather than an exception to catch. Re-raising when the cancel was
  aimed at you also works:

  ```python
  child = asyncio.create_task(work())
  try:
      await asyncio.wait({child})   # never raises the child's CancelledError
  finally:
      child.cancel()                # WE were cancelled: take the child down too (no-op if done)
  if child.cancelled():
      ...                           # someone else cancelled the child: restart it

  # or keep `await child` and tell the two cancels apart:
  except asyncio.CancelledError:
      task = asyncio.current_task()
      if task is not None and task.cancelling():   # 3.11+: a cancel is pending on US
          raise
  ```

- **`Server.wait_closed()` waits for every client connection (from 3.12.0; on 3.11 it returned at
  once).** After `server.close()` it returns only when every accepted client transport has closed,
  so one client that stays connected and idle - a handler parked in `readline()`, a peer that
  never sends EOF - hangs the teardown forever. A server being stopped must close its clients. On
  3.12 that means tracking them: the handler does `clients.add(writer)` on entry and
  `clients.discard(writer)` plus `writer.close()` in its `finally`.

  A graceful close is not enough on its own: a client that stopped READING while the server still
  has data buffered for it never lets its transport finish closing, so `wait_closed()` hangs after
  `close_clients()` or `writer.close()` too. Close gracefully, then abort what is left:

  ```python
  server.close()                            # stops listening only
  if hasattr(server, "close_clients"):      # 3.13+
      server.close_clients()                # graceful: tries to flush buffered writes first
  else:                                     # 3.12: the tracked writers
      for writer in list(clients):
          writer.close()
  try:
      async with asyncio.timeout(5):
          await server.wait_closed()
  except TimeoutError:                      # a peer stopped reading: its buffer never drains
      if hasattr(server, "abort_clients"):  # 3.13+
          server.abort_clients()
      else:
          for writer in list(clients):
              writer.transport.abort()
      async with asyncio.timeout(5):
          await server.wait_closed()
  ```

## Common mistakes

| Mistake                                         | Do instead                                                                  |
|-------------------------------------------------|-----------------------------------------------------------------------------|
| Assuming a resource is always up / stable       | Treat every external call as fallible; health-check, retry, have a fallback |
| Unbounded retries with no timeout               | Cap attempts AND bound every wait + the whole op with a timeout             |
| Retrying a deterministic error (4xx, bad input) | Retry only transient failures; fail fast on permanent ones                  |
| Fixed-interval retry from many clients          | Exponential backoff WITH jitter, to avoid a thundering herd                 |
| Trusting a cached endpoint / host list          | Rediscover and re-validate each run                                         |
| Hammering a dependency that keeps failing       | Circuit breaker: fail fast while OPEN, probe on HALF-OPEN                   |
| Silent degradation (partial result looks whole) | Partial result + explicit warning + non-zero exit                           |
| No headroom / concurrency / size checks         | Bound concurrency, memory, payload; check disk/CPU before a heavy step      |
