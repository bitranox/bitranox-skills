---
name: net-rotating-proxies
description: Use when a download, scrape, or API pull is blocked or rate-limited by the target (HTTP 429, IP ban, geoblock) and must be routed through proxies, or when fetching many items from a host that throttles per IP (bulk YouTube transcripts, scraping, API harvesting), or when one large file (an ISO, an archive) must be downloaded through proxies and bans or dropped connections keep killing it mid-transfer.
---

# Rotating proxies for blocked / rate-limited fetches

When the local IP is rate-limited or blocked (HTTP 429, ban, geoblock) and you must keep
fetching, route requests through a rotating pool of proxies. Free proxies are flaky and
short-lived, so the method is: keep a persistent pool, never trust it as-is, fetch in parallel
(most proxies are slow), prefer proxies that have actually worked, and keep refreshing the pool
in the background while downloading.

## When to use

- A bulk fetch starts returning 429 / "Too Many Requests", or the host bans your IP partway through.
- Client-side fixes do NOT help: changing user-agent, impersonation, or a JS runtime will not beat
  a per-IP quota. Only a different egress IP (a proxy) will. Verify the block is per-IP first.
- You need to pull many items from one throttling host (e.g. YouTube auto-caption transcripts).

## The rules (always)

1. **Persistent pool, disproven at use time.** Proxies constantly die, recover, and appear, so a
   saved list is never trusted as-is. Keep `pool.txt` (all candidates) and `live.txt` (passed a
   reachability test at some point). Note what `validate` actually does: it tests only
   `pool - live - bad`, so an entry already in `live.txt` is NOT re-tested on a later run - the file
   accumulates. Freshness comes from the other end instead: a proxy that fails during a job is
   banned to `bad.txt`, and every reader uses `live - bad`. So treat a live entry as
   not-yet-disproven rather than proven-good, and let the ban path do the pruning.
2. **Discover from public lists**, merge grow-only and deduped into the pool (github raw proxy
   lists, proxyscrape API). Expect thousands of candidates; only a few percent will be usable.
3. **Validate reachability in parallel** against a cheap endpoint on the target host before using
   a proxy for real work, and **record each proxy's latency** (response time of that test) so
   selection can favour fast proxies. **Right-size to the job:** pass `validate --need N` to stop as
   soon as N live proxies are found (and cancel the rest) instead of testing the whole pool - a small
   job needs only a few. Size with a generous `~100%` margin: `N ~= 2 x concurrency` (e.g. 8-wide is
   `--need ~16`, not thousands). The over-provision is what lets the speed-weighted pick run the load on
   the FASTEST proxies while the slower half idles as warm backup (effectively phased out - rarely
   picked). That warm backup is the ONLY instant replacement: a proxy that dies is banned and the
   next pick skips it immediately. The background refresh is what REFILLS the backup, and it is
   slow - with `--background-discovery` it discovers and tops up every 10 minutes (hardcoded, and
   the first pass is at t+10min, not t+0); without that flag it never runs at all. Size `--need`
   to survive ten minutes of attrition rather than to be rescued from it. Distribute requests
   across the pool so no single exit-IP is hammered.
4. **Download in parallel, wide.** Most free proxies are awfully slow (tens of seconds each), so
   parallelism is the only way to make progress: 8 workers minimum, 16 when the pool is large.
5. **Keep good/bad lists and weight by speed, but ROTATE so no proxy is hammered.** A proxy that
   completes a real download goes in `good.txt` (higher base weight); one that fails at the
   connection level goes in `bad.txt` and is excluded. Within the remaining pool, select proxies by
   **weighted random sampling where the weight rises as latency falls**, so faster proxies are used
   far more often than slow ones (the stored validation latency drives this; unknown-latency proxies
   default to the median). Layer a **cool-down / least-recently-used rest** on top of the speed
   weighting: a proxy used within the last `--cooldown` seconds is held out of the pick so the single
   fastest exit-IP is not hit back-to-back; load spreads across the fast half of the pool and the
   cool-down relaxes (oldest-rested first) if it would otherwise starve the pick. Rotate to the next
   proxy on any per-item failure.
6. **Self-optimize in the background: benchmark, swap up, and evict flaky.** While the workers run,
   a background loop keeps the working set = the N FASTEST healthy proxies:
   - discovery + revalidation tops `live.txt` back up so dead proxies get replaced without stopping
     the job (right-sized to `--need`);
   - a benchmark pass re-times the in-pool proxies and trials fresh candidates; when a fresh
     candidate is faster than the slowest **idle** in-pool proxy (never one mid-request), it swaps
     the slow one out for the fast one (`--bench-interval` controls the cadence);
   - per-proxy success/failure is tracked, and a proxy that fails intermittently past
     `--flaky-fail-ratio` is evicted from this run's working set and replaced - so steady state is
     the N fastest, still-functioning proxies. Unlike a hard-dead proxy it is NOT written to
     `bad.txt`: those failures (429, timeouts) are often the target throttling, and `bad.txt` is
     permanent.
7. **Resumable.** Make the worklist skip items already done, so a killed run resumes cheaply.

## Tool

`scripts/proxy_pool.py` (HTTP via `httpx2`, otherwise stdlib; cross-platform) implements all of
the above. Run it with `uv run` so the `httpx2` dependency (declared in the script's PEP-723
header) is fetched into an isolated env. Subcommands:

    # 1. build the pool (grow-only, deduped)
    uv run scripts/proxy_pool.py --store ./.proxies discover

    # 2. test reachability against the target host, grow live.txt (parallel)
    uv run scripts/proxy_pool.py --store ./.proxies validate \
        --test-url https://www.youtube.com/generate_204 --workers 150 --need 10   # stop at 10 live (right-size)

    # 3. run a worklist through rotating proxies, 16-wide, refreshing the pool in the background
    uv run scripts/proxy_pool.py --store ./.proxies run \
        --worklist items.txt --workers 16 --per-item-proxies 8 --need 24 --background-discovery \
        --test-url https://www.youtube.com/generate_204 \
        --success-glob 'out/{item}*.vtt' \
        --cmd 'yt-dlp --proxy http://{proxy} --skip-download --write-auto-subs --sub-langs en.*,en --sub-format vtt -o out/{item}.%(ext)s https://www.youtube.com/watch?v={item}'

`{proxy}` (host:port) and `{item}` are substituted per attempt. The `--cmd` is parsed once and
run as an argv list with NO shell (OS-independent, injection-safe), so it must be a single
command: no pipes, `||`, `$?`, redirects, or `case`. It is split by the host's own rules: POSIX
`shlex` quoting, or on Windows the `CommandLineToArgvW` rules, where a backslash in a path is
literal and only double quotes group (single quotes are ordinary characters there). It runs once
per proxy until one succeeds.

Exit codes: `run` gives 0 when every item succeeded, 1 when any did not, and 2 when it cannot do
the work at all - the `--cmd` binary is not found (the run stops at the first attempt), the
store holds no usable proxy (run `discover` and `validate` first), or an argument cannot be used
(a `--cmd` that cannot be split, an invalid `--dead-regex`, a `--worklist` that is not UTF-8).
`discover` gives 2 when no source answered; `validate` is a report and gives 0 even when no
candidate turned out live.

`run` holds a self-optimizing working set of the `--need` fastest healthy proxies - pass it, or
`--need` defaults to None and the working set is not right-sized at all: it rotates the
pick with a `--cooldown` rest so no exit-IP is hammered, evicts a proxy once its failure fraction
exceeds `--flaky-fail-ratio`, and (with `--background-discovery`) re-benchmarks the pool every
`--bench-interval` seconds, swapping a freshly-found faster proxy in for the slowest idle one.

### How success / failure is decided (no shell glue)

The tool classifies each attempt itself, portably:

- **success** = return code 0 AND, when `--success-glob` is given, a matching output file exists
  (many tools exit 0 without producing output, so prefer `--success-glob`) -> proxy goes in
  `good.txt`, rotation stops for that item.
- **dead proxy** = the command's combined stdout+stderr matches `--dead-regex` (connection
  refused, reset, timeout, unreachable, proxy/tunnel errors) -> proxy goes in `bad.txt`, excluded
  next time.
- **otherwise** (incl. timeout, 429, transient) -> rotate to the next proxy, do not ban it (one
  that keeps failing this way leaves this run's working set, but never goes in `bad.txt`).

Pick `--test-url` and `--success-glob` to match the host and tool you are unblocking; widen
`--dead-regex` if your tool words connection failures differently.

## One large file across proxies

`run` treats an item as all-or-nothing, so one big file (an ISO, an archive) restarts from byte 0
on every proxy that drops it. Use `fetch` instead: it splits the file into byte ranges, downloads
them in parallel over the pool, and keeps every byte that arrived.

    uv run scripts/proxy_pool.py --store ./.proxies fetch https://example.com/big.iso \
        -o big.iso --sha256 <published hex digest> --workers 8

`fetch` draws from the same store as `run` (`live + good - bad`), so run `discover` and `validate`
first. It has no background refresh, so validate a generous pool before a long download. Defaults:
`--chunk-size 8M`, `--chunk-timeout 120` (seconds), `--max-attempts-per-chunk 20`.

- **A cut keeps its bytes.** When a proxy drops, stalls, trickles or runs out its
  `--chunk-timeout` (the budget of one attempt, connect to last byte, headers and redirects
  included), what it delivered stays on disk and the chunk continues at the next byte on another
  proxy. A cut, a 403, 407, 429 or 5xx rotates the proxy, and so does a CONNECT that the proxy
  refuses with such a status for an https URL. Only a dead proxy is banned to `bad.txt`: one that
  cannot be connected to, fails the TLS handshake, or refuses a CONNECT without a 4xx/5xx status.
  A chunk gives up after `--max-attempts-per-chunk`.
- **One odd answer is not trusted.** A reply that is not the requested range of this object (a
  page instead of the range, another status such as 404, a wrong size, a changed ETag or
  Last-Modified, a compressed body) is the proxy lying or the origin having changed, and one
  reply cannot tell which. That proxy is dropped for the rest of this run but is not written to
  `bad.txt`. When a second proxy gives the same answer, the origin changed: `fetch` stops with
  exit 2, names what the origin now answers and bans nobody. A ranged download keeps `FILE.part`
  and `FILE.part.json`: a rerun resumes once the URL serves the probed file again, and against a
  replaced file it refuses the manifest and names the two files to delete.
- **Redirects are followed** through the same proxy, up to 8 hops, so a release asset or a mirror
  URL that answers 302 downloads; every check applies to the final target, and a longer chain
  counts as an odd answer.
- **Always pass `--sha256`.** Size and identity headers catch a proxy answering with the wrong
  file; only the hash catches bytes altered behind correct headers. Without it `fetch` warns, and
  exit 0 means only that the expected length arrived. A mismatch keeps the bytes as `FILE.part`
  and drops the manifest, so rerunning the command downloads the whole file again.
- **Resume by rerunning the same command.** Progress is in `FILE.part` plus `FILE.part.json`; one
  Ctrl-C stops after the attempts in flight. A manifest for a different download (URL, size,
  identity or `--chunk-size` changed) is refused with the two files to delete.
- **The size comes from a vote.** Before downloading, proxies are asked for byte 0, at most
  `--max-attempts-per-chunk` times. The first view (size, ETag and Last-Modified, Range support)
  that two different proxies give decides at once, even beside dissenters. When the probe ends
  without that (every active proxy answered, or the probes ran out), each view has one proxy:
  a lone ranged view beats whole-file views and is taken with a "took the ranged view of one
  proxy" warning, and a single answering proxy is taken with a not-cross-checked warning. Two
  ranged views, or two whole-file views and no ranged one, stop with exit 1 rather than guess.
  Only a dead proxy is banned during the probe.
- **No Range support** (the origin answers the whole file): each attempt streams the whole file
  from byte 0, with no resume. If the origin sends no size either, a cut transfer cannot be told
  from a complete one, so `--sha256` is the only check left.

Exit codes of `fetch`:

- **0**: the file is complete, and hash-verified when `--sha256` was given.
- **1**: chunks are still missing, or the probe settled nothing (no proxy answered, or the answers
  disagreed). Grow the pool with `validate` and rerun the same command.
- **2**: it cannot work: a bad argument (a URL that is not `http://` or `https://`, such as
  `example.com/big.iso` or `ftp://...`, is refused before any proxy is asked), no usable proxy,
  a hash mismatch, a manifest for another download, an output that cannot be written, or two
  proxies reporting the same changed origin answer.

Run `fetch --help` for the remaining flags.

## Notes

- Stay within lawful use. Only fetch content you are authorised to access, and respect the
  target's terms of service and robots directives. Rotating egress IPs spreads a legitimate bulk
  fetch past a per-IP rate limit; it is not for defeating a block meant to keep you out.
- Confirm the block is per-IP before reaching for proxies; if a few requests still succeed from
  your own IP, slow down instead.
- Free-proxy hit rate is low and decays within minutes; the background refresh and good/bad lists
  exist precisely because of this. Re-run `discover`+`validate` between sessions.
- Treat proxied traffic as untrusted transport: only route public, non-sensitive fetches through
  free proxies, never anything authenticated or private.
