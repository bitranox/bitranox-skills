#!/usr/bin/env python3
# /// script
# requires-python = ">=3.9"
# dependencies = ["httpx2"]
# ///
"""Rotating free-proxy pool: discover, validate, and run a worklist through proxies.

Run with `uv run proxy_pool.py ...` so uv fetches httpx2 into an isolated env.
HTTP uses httpx2 (HTTP/2, sync + async, clean proxy support); everything else is
stdlib, portable across Linux/macOS/Windows. The proxy pool is a persistent
store that is RE-TESTED every run, because free proxies constantly die, recover,
and appear. These files live under --store (default ./.proxies):

  pool.txt    all discovered candidate IP:PORT (grow-only, deduped)
  live.txt    candidates that passed reachability validation this/last run
  good.txt    proxies that actually completed a real download (weighted up)
  bad.txt     proxies that failed at the connection level (excluded)
  speeds.tsv  measured validation latency per proxy (proxy<TAB>seconds); selection
              weights faster proxies up so they are picked more often

Subcommands:
  discover   fetch public proxy lists -> merge into pool.txt
  validate   test pool entries for reachability -> grow live.txt (parallel)
  run        run a worklist through rotating proxies, N-wide parallel, good-first,
             optionally with a background discover+validate loop refreshing live.txt

OS-independent by design: --cmd is parsed into an argv list and run WITHOUT a shell
(no shell=True), so it behaves the same on Linux/macOS/Windows and is injection-safe.
Do not put shell operators (|, ||, $?, redirects) in --cmd; success is decided by the
tool here, not by shell glue:
  - success  = return code 0 AND, if --success-glob is given, a matching output file exists
               (many tools exit 0 without producing output, so prefer --success-glob)
               -> record proxy in good.txt, stop rotating this item
  - dead     = the proxy failed at the connection level (return code matched the tool's
               combined stdout+stderr against --dead-regex) -> record in bad.txt, skip next time
  - otherwise (incl. timeout / 429 / transient) -> rotate to the next proxy, do not ban

The --cmd template may contain {proxy} (host:port) and {item}. Example:
  uv run proxy_pool.py run --worklist ids.txt --workers 16 --success-glob 'out/{item}*.vtt'
     --cmd 'yt-dlp --proxy http://{proxy} --skip-download --write-auto-subs
            --sub-langs en.*,en --sub-format vtt -o out/{item}.%(ext)s
            https://www.youtube.com/watch?v={item}'
"""
import argparse, concurrent.futures as cf, glob, os, random, re, shlex, subprocess, threading, time
import httpx2

DEAD_DEFAULT = r"connection refused|connection reset|timed out|cannot connect|unreachable|EOF occurred|proxy|tunnel|ProxyError"

IPPORT = re.compile(r"(?:\d{1,3}\.){3}\d{1,3}:\d{1,5}")
DEFAULT_SOURCES = [
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://raw.githubusercontent.com/proxifly/free-proxy-list/main/proxies/protocols/http/data.txt",
    "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
    "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country=all",
]
_lock = threading.Lock()


def _p(store, name):
    return os.path.join(store, name)


def _read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return {l.strip() for l in f if l.strip()}
    except FileNotFoundError:
        return set()


def _grow(path, items):
    """Atomic grow-only merge: never shrinks the file."""
    with _lock:
        cur = _read(path)
        cur |= set(items)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write("\n".join(sorted(cur)) + "\n")
        os.replace(tmp, path)


def _append(path, line):
    with _lock:
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")


def discover(store, sources):
    found = set()
    for url in sources:
        try:
            r = httpx2.get(url, timeout=25, headers={"User-Agent": "Mozilla/5.0"}, follow_redirects=True)
            hits = set(IPPORT.findall(r.text))
            found |= hits
            print(f"  {len(hits):5d} from {url[:60]}")
        except Exception as e:
            print(f"  ERR  {url[:60]}: {e}")
    found.discard("0.0.0.0:80")
    _grow(_p(store, "pool.txt"), found)
    print(f"pool now: {len(_read(_p(store, 'pool.txt')))} candidates")


def _read_speeds(path):
    d = {}
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                a = line.rstrip("\n").split("\t")
                if len(a) == 2:
                    try:
                        d[a[0]] = float(a[1])
                    except ValueError:
                        pass
    except FileNotFoundError:
        pass
    return d


def _upsert_speeds(path, new):
    if not new:
        return
    with _lock:
        d = _read_speeds(path)
        d.update(new)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            for p, s in sorted(d.items()):
                f.write(f"{p}\t{s:.3f}\n")
        os.replace(tmp, path)


def _median(xs):
    xs = sorted(x for x in xs if x)
    if not xs:
        return 0.0
    n, m = len(xs), len(xs) // 2
    return xs[m] if n % 2 else (xs[m - 1] + xs[m]) / 2


def _reachable(proxy, test_url, timeout):
    """Return (ok, latency_seconds). latency is None on failure."""
    t0 = time.perf_counter()
    try:
        with httpx2.Client(proxy=f"http://{proxy}", timeout=timeout, follow_redirects=True) as c:
            ok = c.get(test_url).status_code in (200, 204)
    except Exception:
        return (False, None)
    return (ok, time.perf_counter() - t0)


def validate(store, test_url, workers, timeout, need=None):
    """Test pool candidates for reachability, growing live.txt.

    ``need`` right-sizes the work: stop as soon as ``need`` live proxies are found this run and
    cancel the rest, instead of testing the whole pool. A small job (a handful of requests) only
    needs a few live proxies plus a flakiness margin - pass ``need = concurrency + margin`` rather
    than validating thousands. ``need=None`` tests every candidate (the exhaustive default).
    """
    pool = _read(_p(store, "pool.txt"))
    live = _read(_p(store, "live.txt"))
    bad = _read(_p(store, "bad.txt"))
    todo = sorted(pool - live - bad)  # only test ones we have not already cleared
    goal = f", stopping at +{need} live" if need else ""
    print(f"validating up to {len(todo)} candidates against {test_url} ({workers}-wide){goal}...")
    winners, speeds = [], {}
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(_reachable, p, test_url, timeout): p for p in todo}
        try:
            for fut in cf.as_completed(futures):
                ok, lat = fut.result()
                if ok:
                    winners.append(futures[fut])
                    speeds[futures[fut]] = lat
                    if need and len(winners) >= need:
                        break  # right-sized: enough live found, do not test the rest
        finally:
            for fut in futures:  # cancel any not-yet-started work after an early stop
                fut.cancel()
    _grow(_p(store, "live.txt"), winners)
    _upsert_speeds(_p(store, "speeds.tsv"), speeds)
    med = _median(list(speeds.values()))
    print(f"+{len(winners)} live (median latency {med:.2f}s); live total now {len(_read(_p(store, 'live.txt')))}")


def _pick(store, n):
    """Weighted sample of n proxies. Faster proxies (lower latency) and proven-good
    proxies are picked more often, via Efraimidis-Spirakis weighted sampling without
    replacement (key = U**(1/weight), take the top n)."""
    bad = _read(_p(store, "bad.txt"))
    speeds = _read_speeds(_p(store, "speeds.tsv"))
    good = _read(_p(store, "good.txt")) - bad
    live = _read(_p(store, "live.txt")) - bad
    cands = {p: 1.0 for p in live}
    for p in good:
        cands[p] = 3.0                  # proven proxies get a higher base weight
    if not cands:
        return []
    default_lat = _median(list(speeds.values())) or 3.0
    keyed = []
    for p, base in cands.items():
        lat = speeds.get(p) or default_lat
        weight = base / max(lat, 0.05)  # faster -> larger weight -> picked more often
        u = random.random() or 1e-12
        keyed.append((u ** (1.0 / weight), p))
    keyed.sort(reverse=True)
    return [p for _, p in keyed[:n]]


def _weighted_lru_pick(weights, last_used, now, cooldown, n):
    """Efraimidis-Spirakis weighted pick of up to n proxies that also SPREADS load.

    ``weights`` maps proxy -> selection weight (higher = fitter, e.g. faster). A proxy
    used within ``cooldown`` seconds is RESTED (held out) so no single fast proxy gets
    hammered back-to-back; the pick is drawn from the rested remainder by weight so fast
    proxies are still favoured among the eligible. If cool-down would leave fewer than n
    eligible, the most-rested recently-used proxies (oldest ``last_used`` first) are added
    back until n are available, so a small pool never starves. Pure and deterministic given
    the ``random`` state; holds no shared state and does no I/O."""
    if not weights or n <= 0:
        return []
    eligible = [p for p in weights if now - last_used.get(p, float("-inf")) >= cooldown]
    if len(eligible) < n:
        resting = sorted((p for p in weights if p not in eligible), key=lambda p: last_used.get(p, float("-inf")))
        eligible += resting[: n - len(eligible)]
    keyed = []
    for p in eligible:
        w = max(weights[p], 1e-9)
        u = random.random() or 1e-12
        keyed.append((u ** (1.0 / w), p))
    keyed.sort(reverse=True)
    return [p for _, p in keyed[:n]]


def _swap_candidate(pool_speed, in_use, candidate_speed):
    """Return the in-pool proxy a fresh candidate should replace, or None.

    Steady state is the N FASTEST healthy proxies. A fresh candidate measured at
    ``candidate_speed`` (latency, seconds) swaps out the SLOWEST currently-idle in-pool
    proxy when it is strictly faster than that one; a proxy that is mid-request (in
    ``in_use``) is never swapped out. Returns None when no idle member is slower than the
    candidate, so a swap only ever raises pool speed. Pure; no shared state, no I/O."""
    idle = [(lat, p) for p, lat in pool_speed.items() if p not in in_use]
    if not idle:
        return None
    slowest_lat, slowest = max(idle)
    return slowest if candidate_speed < slowest_lat else None


def _is_flaky(successes, failures, min_samples=4, max_fail_ratio=0.5):
    """True when a proxy fails intermittently past the tolerated ratio.

    Requires at least ``min_samples`` recorded attempts before judging (so one early
    failure does not evict an otherwise-good proxy), then flags it when the failure
    fraction exceeds ``max_fail_ratio``. A flaky proxy is evicted and replaced just like a
    hard-dead one. Pure; no shared state, no I/O."""
    total = successes + failures
    if total < min_samples:
        return False
    return failures / total > max_fail_ratio


class ProxyPool:
    """Self-optimizing in-memory working set of proxies for one ``run``.

    Holds the ``need`` fastest healthy proxies as the ACTIVE set and hands them out
    rotated (cool-down / weighted-LRU via ``_weighted_lru_pick``) so load spreads instead
    of hammering the single fastest exit-IP. Tracks per-proxy latency, last-used time,
    in-flight status, and success/failure counts; a proxy that goes hard-dead OR turns
    flaky (``_is_flaky``) is evicted and backfilled from the live pool. A background
    benchmark loop (``benchmark_loop``) continuously re-times active proxies and trials
    fresh candidates, swapping a faster fresh one in for the slowest idle member
    (``_swap_candidate``) so steady state stays the N fastest.

    All mutation is guarded by ``self._lock``; the decision logic lives in the pure module
    functions so it is unit-testable without threads. ``self._lock`` and the module-level
    ``_lock`` (used by ``_append`` / ``_upsert_speeds``) are distinct objects that are
    never held in a cycle, so calling those helpers while holding ``self._lock`` is safe."""

    def __init__(self, store, need, test_url=None, vtimeout=7.0, cooldown=5.0,
                 flaky_min_samples=4, flaky_max_fail_ratio=0.5, bench_batch=25):
        self.store = store
        self.need = need or 0
        self.test_url = test_url
        self.vtimeout = vtimeout
        self.cooldown = cooldown
        self.flaky_min_samples = flaky_min_samples
        self.flaky_max_fail_ratio = flaky_max_fail_ratio
        self.bench_batch = bench_batch
        self._lock = threading.Lock()
        self._speed = _read_speeds(_p(store, "speeds.tsv"))
        self._last_used = {}
        self._in_use = set()
        self._ok = {}
        self._fail = {}
        self._banned = set()
        self._active = set()
        with self._lock:
            self._refill_active_locked()

    # -- internal helpers; caller must hold self._lock -----------------------
    def _candidates_locked(self):
        bad = _read(_p(self.store, "bad.txt"))
        live = _read(_p(self.store, "live.txt"))
        good = _read(_p(self.store, "good.txt"))
        return (live | good) - bad - self._banned

    def _refill_active_locked(self):
        cands = self._candidates_locked()
        default_lat = _median(list(self._speed.values())) or 3.0
        ranked = sorted(cands, key=lambda p: self._speed.get(p) or default_lat)
        target = self.need or len(ranked)
        self._active = set(ranked[:target])

    def _weights_locked(self):
        good = _read(_p(self.store, "good.txt")) - self._banned
        default_lat = _median(list(self._speed.values())) or 3.0
        weights = {}
        for p in self._active:
            base = 3.0 if p in good else 1.0
            lat = self._speed.get(p) or default_lat
            weights[p] = base / max(lat, 0.05)
        return weights

    def _ban_locked(self, proxy):
        self._banned.add(proxy)
        self._active.discard(proxy)
        self._in_use.discard(proxy)

    def _try_swap_locked(self, candidate, cand_lat):
        target = self.need or (len(self._active) + 1)
        if len(self._active) < target:
            self._active.add(candidate)
            return
        default_lat = _median(list(self._speed.values())) or 3.0
        pool_speed = {p: (self._speed.get(p) or default_lat) for p in self._active}
        victim = _swap_candidate(pool_speed, self._in_use, cand_lat)
        if victim is not None:
            self._active.discard(victim)
            self._active.add(candidate)

    # -- public API ----------------------------------------------------------
    def active(self):
        with self._lock:
            return set(self._active)

    def acquire(self, n):
        """Pick up to n proxies for one item, rotated so no proxy is hammered.

        Refills the active set first if it has dropped below target, then draws a
        speed-weighted, cool-down-respecting pick and stamps each with the current time so
        the next acquire rests them. Returns the ordered fallback chain to try for the item."""
        now = time.monotonic()
        with self._lock:
            if len(self._active) < (self.need or 1):
                self._refill_active_locked()
            picks = _weighted_lru_pick(self._weights_locked(), self._last_used, now, self.cooldown, n)
            for p in picks:
                self._last_used[p] = now
            return picks

    def mark_in_use(self, proxy):
        with self._lock:
            self._in_use.add(proxy)

    def record(self, proxy, ok):
        """Record an attempt's outcome; evict + backfill if the proxy has turned flaky."""
        with self._lock:
            self._in_use.discard(proxy)
            counter = self._ok if ok else self._fail
            counter[proxy] = counter.get(proxy, 0) + 1
            if _is_flaky(self._ok.get(proxy, 0), self._fail.get(proxy, 0),
                         self.flaky_min_samples, self.flaky_max_fail_ratio):
                self._ban_locked(proxy)
                _append(_p(self.store, "bad.txt"), proxy)
                self._refill_active_locked()

    def ban(self, proxy):
        """Evict a hard-dead proxy (connection-level failure), persist it, and backfill."""
        with self._lock:
            self._ban_locked(proxy)
            _append(_p(self.store, "bad.txt"), proxy)
            self._refill_active_locked()

    def benchmark_once(self):
        """Re-time active proxies (evicting any gone dead) and trial fresh candidates,
        swapping a faster fresh one in for the slowest idle member (swap-up)."""
        if not self.test_url:
            return
        with self._lock:
            members = list(self._active)
            fresh = list(self._candidates_locked() - self._active)[: self.bench_batch]
        for p in members:
            ok, lat = _reachable(p, self.test_url, self.vtimeout)
            with self._lock:
                if ok and lat is not None:
                    self._speed[p] = lat
                elif not ok:
                    self._ban_locked(p)
                    _append(_p(self.store, "bad.txt"), p)
        for c in fresh:
            ok, lat = _reachable(c, self.test_url, self.vtimeout)
            if not ok or lat is None:
                continue
            with self._lock:
                self._speed[c] = lat
                self._try_swap_locked(c, lat)
        with self._lock:
            snapshot = {p: self._speed[p] for p in members + fresh if p in self._speed}
        _upsert_speeds(_p(self.store, "speeds.tsv"), snapshot)

    def benchmark_loop(self, stop, interval=120):
        while not stop.is_set():
            if stop.wait(interval):
                break
            try:
                self.benchmark_once()
            except Exception as e:
                print(f"benchmark error: {e}")


def _bg_refresh(store, test_url, workers, timeout, stop, need=None):
    """Keep live.txt healthy while a job runs. Proxies that die get banned to bad.txt by the worker,
    which shrinks the effective pool (live - bad); this loop refills it. With ``need`` set it tops up
    ONLY to the target (validating just the deficit), so it replaces proxies that went away without
    re-over-provisioning; with ``need=None`` it re-validates the whole pool (exhaustive)."""
    while not stop.is_set():
        if stop.wait(600):              # every 10 min
            break
        try:
            discover(store, DEFAULT_SOURCES)
            if need is None:
                validate(store, test_url, workers, timeout)
                continue
            available = _read(_p(store, "live.txt")) - _read(_p(store, "bad.txt"))
            deficit = need - len(available)
            if deficit > 0:             # one (or more) went away -> top back up to the target
                validate(store, test_url, workers, timeout, need=deficit)
        except Exception as e:
            print(f"bg refresh error: {e}")


def _run_item(store, item, argv_tpl, per_item, item_timeout, success_glob, dead_re, pool=None):
    # With a ProxyPool the chain is drawn rotated (cool-down/weighted-LRU) and outcomes are
    # fed back for flaky tracking; without one it falls back to the stateless speed-weighted pick.
    proxies = pool.acquire(per_item) if pool is not None else _pick(store, per_item)
    for proxy in proxies:
        if pool is not None:
            pool.mark_in_use(proxy)
        # argv list, NO shell: identical behaviour on Linux/macOS/Windows, injection-safe.
        argv = [tok.replace("{proxy}", proxy).replace("{item}", item) for tok in argv_tpl]
        try:
            r = subprocess.run(argv, capture_output=True, text=True, timeout=item_timeout)
            rc, out = r.returncode, (r.stdout or "") + (r.stderr or "")
        except subprocess.TimeoutExpired:
            rc, out = 124, ""
        except FileNotFoundError:
            print(f"cmd not found: {argv[0]!r}")
            return (item, None)
        ok = rc == 0
        if ok and success_glob:
            ok = bool(glob.glob(success_glob.replace("{item}", item)))
        if ok:
            _append(_p(store, "good.txt"), proxy)
            if pool is not None:
                pool.record(proxy, True)
            return (item, proxy)
        if dead_re.search(out):          # connection-level failure: ban this proxy
            if pool is not None:
                pool.ban(proxy)
            else:
                _append(_p(store, "bad.txt"), proxy)
        elif pool is not None:           # transient / blocked (e.g. 429): rotate, count as a failure
            pool.record(proxy, False)
    return (item, None)


def run(store, worklist, cmd, workers, per_item, item_timeout, bg, test_url, vworkers, vtimeout,
        success_glob, dead_regex, need=None, cooldown=5.0, bench_interval=120, flaky_fail_ratio=0.5):
    argv_tpl = shlex.split(cmd)          # parse template once; substituted per attempt, no shell
    dead_re = re.compile(dead_regex, re.I)
    items = [l.strip() for l in open(worklist, encoding="utf-8") if l.strip()]
    # Self-optimizing working set: rotates the pick (no hammering), tracks flaky proxies,
    # and (with --background-discovery) benchmarks + swaps fresh fast proxies in for slow ones.
    pool = ProxyPool(store, need, test_url=test_url, vtimeout=vtimeout, cooldown=cooldown,
                     flaky_max_fail_ratio=flaky_fail_ratio)
    stop = threading.Event()
    if bg:
        refresh_t = threading.Thread(target=_bg_refresh, args=(store, test_url, vworkers, vtimeout, stop, need), daemon=True)
        bench_t = threading.Thread(target=pool.benchmark_loop, args=(stop, bench_interval), daemon=True)
        refresh_t.start()
        bench_t.start()
        print("background discover+validate and benchmark+swap loops started")
    ok = 0
    try:
        with cf.ThreadPoolExecutor(max_workers=workers) as ex:
            futs = [ex.submit(_run_item, store, it, argv_tpl, per_item, item_timeout, success_glob, dead_re, pool) for it in items]
            for fut in cf.as_completed(futs):
                item, proxy = fut.result()
                if proxy:
                    ok += 1
                    print(f"OK {item} via {proxy}  ({ok}/{len(items)})")
    finally:
        stop.set()
    print(f"done: {ok}/{len(items)} succeeded; good={len(_read(_p(store,'good.txt')))} bad={len(_read(_p(store,'bad.txt')))}")


def main():
    ap = argparse.ArgumentParser(description="Rotating free-proxy pool harness.")
    ap.add_argument("--store", default="./.proxies")
    sub = ap.add_subparsers(dest="action", required=True)
    d = sub.add_parser("discover"); d.add_argument("--sources", nargs="*", default=DEFAULT_SOURCES)
    v = sub.add_parser("validate")
    v.add_argument("--test-url", default="https://www.youtube.com/generate_204")
    v.add_argument("--workers", type=int, default=150); v.add_argument("--timeout", type=float, default=7)
    v.add_argument("--need", type=int, default=None,
                   help="stop once N live proxies are found (right-size: N = concurrency + margin); "
                        "omit to test the whole pool")
    r = sub.add_parser("run")
    r.add_argument("--worklist", required=True); r.add_argument("--cmd", required=True)
    r.add_argument("--workers", type=int, default=8); r.add_argument("--per-item-proxies", type=int, default=8)
    r.add_argument("--item-timeout", type=float, default=90)
    r.add_argument("--success-glob", default=None, help="path glob (may contain {item}) that must exist for success")
    r.add_argument("--dead-regex", default=DEAD_DEFAULT, help="regex on cmd output marking a dead proxy")
    r.add_argument("--background-discovery", action="store_true")
    r.add_argument("--test-url", default="https://www.youtube.com/generate_204")
    r.add_argument("--vworkers", type=int, default=150); r.add_argument("--vtimeout", type=float, default=7)
    r.add_argument("--need", type=int, default=None,
                   help="target live-pool size to maintain (right-size: concurrency + margin); the "
                        "background refresh tops up to this when proxies die, instead of re-validating all")
    r.add_argument("--cooldown", type=float, default=5.0,
                   help="seconds a proxy rests between uses so no single fast exit-IP is hammered")
    r.add_argument("--bench-interval", type=float, default=120,
                   help="seconds between background re-benchmark + swap-up passes (needs --background-discovery)")
    r.add_argument("--flaky-fail-ratio", type=float, default=0.5,
                   help="evict a proxy once its failure fraction exceeds this (after a few attempts)")
    a = ap.parse_args()
    os.makedirs(a.store, exist_ok=True)
    if a.action == "discover":
        discover(a.store, a.sources)
    elif a.action == "validate":
        validate(a.store, a.test_url, a.workers, a.timeout, a.need)
    elif a.action == "run":
        run(a.store, a.worklist, a.cmd, a.workers, a.per_item_proxies, a.item_timeout,
            a.background_discovery, a.test_url, a.vworkers, a.vtimeout, a.success_glob, a.dead_regex,
            a.need, a.cooldown, a.bench_interval, a.flaky_fail_ratio)


if __name__ == "__main__":
    main()
