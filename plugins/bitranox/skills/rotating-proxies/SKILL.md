---
name: rotating-proxies
description: Use when a download, scrape, or API pull is blocked or rate-limited by the target (HTTP 429, IP ban, geoblock) and must be routed through proxies, or when fetching many items from a host that throttles per IP (bulk YouTube transcripts, scraping, API harvesting). Covers building and re-testing a free-proxy pool and running a worklist through it in parallel.
---

# Rotating proxies for blocked / rate-limited fetches

When the local IP is rate-limited or blocked (HTTP 429, ban, geoblock) and you must keep
fetching, route requests through a rotating pool of proxies. Free proxies are flaky and
short-lived, so the method is: keep a persistent pool, re-test it every run, fetch in parallel
(most proxies are slow), prefer proxies that have actually worked, and keep refreshing the pool
in the background while downloading.

## When to use

- A bulk fetch starts returning 429 / "Too Many Requests", or the host bans your IP partway through.
- Client-side fixes do NOT help: changing user-agent, impersonation, or a JS runtime will not beat
  a per-IP quota. Only a different egress IP (a proxy) will. Verify the block is per-IP first.
- You need to pull many items from one throttling host (e.g. YouTube auto-caption transcripts).

## The rules (always)

1. **Persistent pool, re-tested every run.** Proxies constantly die, recover, and appear, so a
   saved list is never trusted as-is. Keep `pool.txt` (all candidates), and derive `live.txt`
   (passed reachability test) freshly each run. Never assume yesterday's live proxy still works.
2. **Discover from public lists**, merge grow-only and deduped into the pool (github raw proxy
   lists, proxyscrape API). Expect thousands of candidates; only a few percent will be usable.
3. **Validate reachability in parallel** against a cheap endpoint on the target host before using
   a proxy for real work, and **record each proxy's latency** (response time of that test) so
   selection can favour fast proxies.
4. **Download in parallel, wide.** Most free proxies are awfully slow (tens of seconds each), so
   parallelism is the only way to make progress: 8 workers minimum, 16 when the pool is large.
5. **Keep good/bad lists and weight by speed.** A proxy that completes a real download goes in
   `good.txt` (higher base weight); one that fails at the connection level goes in `bad.txt` and
   is excluded. Within the remaining pool, select proxies by **weighted random sampling where the
   weight rises as latency falls**, so faster proxies are used far more often than slow ones (the
   stored validation latency drives this; unknown-latency proxies default to the median). Rotate
   to the next proxy on any per-item failure.
6. **Refresh in the background during the download.** Run discovery + revalidation on a loop
   while the workers run, so the live/good/bad lists stay fresh and dead proxies get replaced
   without stopping the job.
7. **Resumable.** Make the worklist skip items already done, so a killed run resumes cheaply.

## Tool

`scripts/proxy_pool.py` (HTTP via `httpx2`, otherwise stdlib; cross-platform) implements all of
the above. Run it with `uv run` so the `httpx2` dependency (declared in the script's PEP-723
header) is fetched into an isolated env. Subcommands:

    # 1. build the pool (grow-only, deduped)
    uv run scripts/proxy_pool.py --store ./.proxies discover

    # 2. test reachability against the target host, grow live.txt (parallel)
    uv run scripts/proxy_pool.py --store ./.proxies validate \
        --test-url https://www.youtube.com/generate_204 --workers 150

    # 3. run a worklist through rotating proxies, 16-wide, refreshing the pool in the background
    uv run scripts/proxy_pool.py --store ./.proxies run \
        --worklist items.txt --workers 16 --per-item-proxies 8 --background-discovery \
        --test-url https://www.youtube.com/generate_204 \
        --success-glob 'out/{item}*.vtt' \
        --cmd 'yt-dlp --proxy http://{proxy} --skip-download --write-auto-subs --sub-langs en.*,en --sub-format vtt -o out/{item}.%(ext)s https://www.youtube.com/watch?v={item}'

`{proxy}` (host:port) and `{item}` are substituted per attempt. The `--cmd` is parsed once with
`shlex.split` and run as an argv list with NO shell (OS-independent, injection-safe), so it must
be a single command: no pipes, `||`, `$?`, redirects, or `case`. It runs once per proxy until one
succeeds.

### How success / failure is decided (no shell glue)

The tool classifies each attempt itself, portably:

- **success** = return code 0 AND, when `--success-glob` is given, a matching output file exists
  (many tools exit 0 without producing output, so prefer `--success-glob`) -> proxy goes in
  `good.txt`, rotation stops for that item.
- **dead proxy** = the command's combined stdout+stderr matches `--dead-regex` (connection
  refused, reset, timeout, unreachable, proxy/tunnel errors) -> proxy goes in `bad.txt`, excluded
  next time.
- **otherwise** (incl. timeout, 429, transient) -> rotate to the next proxy, do not ban it.

Pick `--test-url` and `--success-glob` to match the host and tool you are unblocking; widen
`--dead-regex` if your tool words connection failures differently.

## Notes

- Confirm the block is per-IP before reaching for proxies; if a few requests still succeed from
  your own IP, slow down instead.
- Free-proxy hit rate is low and decays within minutes; the background refresh and good/bad lists
  exist precisely because of this. Re-run `discover`+`validate` between sessions.
- Treat proxied traffic as untrusted transport: only route public, non-sensitive fetches through
  free proxies, never anything authenticated or private.
