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
and appear. Three stores live under --store (default ./.proxies):

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
import httpx2 as httpx

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
            r = httpx.get(url, timeout=25, headers={"User-Agent": "Mozilla/5.0"}, follow_redirects=True)
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
        with httpx.Client(proxy=f"http://{proxy}", timeout=timeout, follow_redirects=True) as c:
            ok = c.get(test_url).status_code in (200, 204)
    except Exception:
        return (False, None)
    return (ok, time.perf_counter() - t0)


def validate(store, test_url, workers, timeout):
    pool = _read(_p(store, "pool.txt"))
    live = _read(_p(store, "live.txt"))
    bad = _read(_p(store, "bad.txt"))
    todo = sorted(pool - live - bad)  # only test ones we have not already cleared
    print(f"validating {len(todo)} candidates against {test_url} ({workers}-wide)...")
    winners, speeds = [], {}
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        for proxy, (ok, lat) in zip(todo, ex.map(lambda p: _reachable(p, test_url, timeout), todo)):
            if ok:
                winners.append(proxy)
                speeds[proxy] = lat
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


def _bg_refresh(store, test_url, workers, timeout, stop):
    while not stop.is_set():
        if stop.wait(600):              # every 10 min
            break
        try:
            discover(store, DEFAULT_SOURCES)
            validate(store, test_url, workers, timeout)
        except Exception as e:
            print(f"bg refresh error: {e}")


def _run_item(store, item, argv_tpl, per_item, item_timeout, success_glob, dead_re):
    for proxy in _pick(store, per_item):
        # argv list, NO shell: identical behaviour on Linux/macOS/Windows, injection-safe.
        argv = [tok.replace("{proxy}", proxy).replace("{item}", item) for tok in argv_tpl]
        try:
            r = subprocess.run(argv, capture_output=True, text=True, timeout=item_timeout)
            rc, out = r.returncode, (r.stdout or "") + (r.stderr or "")
        except subprocess.TimeoutExpired:
            rc, out = 124, ""
        except FileNotFoundError:
            print(f"cmd not found: {argv[0]!r}"); return (item, None)
        ok = rc == 0
        if ok and success_glob:
            ok = bool(glob.glob(success_glob.replace("{item}", item)))
        if ok:
            _append(_p(store, "good.txt"), proxy)
            return (item, proxy)
        if dead_re.search(out):          # connection-level failure: ban this proxy
            _append(_p(store, "bad.txt"), proxy)
        # otherwise transient / blocked (e.g. 429): rotate to next proxy, do not ban
    return (item, None)


def run(store, worklist, cmd, workers, per_item, item_timeout, bg, test_url, vworkers, vtimeout, success_glob, dead_regex):
    argv_tpl = shlex.split(cmd)          # parse template once; substituted per attempt, no shell
    dead_re = re.compile(dead_regex, re.I)
    items = [l.strip() for l in open(worklist, encoding="utf-8") if l.strip()]
    stop = threading.Event()
    bg_t = None
    if bg:
        bg_t = threading.Thread(target=_bg_refresh, args=(store, test_url, vworkers, vtimeout, stop), daemon=True)
        bg_t.start()
        print("background discover+validate loop started (every 10 min)")
    ok = 0
    try:
        with cf.ThreadPoolExecutor(max_workers=workers) as ex:
            futs = [ex.submit(_run_item, store, it, argv_tpl, per_item, item_timeout, success_glob, dead_re) for it in items]
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
    r = sub.add_parser("run")
    r.add_argument("--worklist", required=True); r.add_argument("--cmd", required=True)
    r.add_argument("--workers", type=int, default=8); r.add_argument("--per-item-proxies", type=int, default=8)
    r.add_argument("--item-timeout", type=float, default=90)
    r.add_argument("--success-glob", default=None, help="path glob (may contain {item}) that must exist for success")
    r.add_argument("--dead-regex", default=DEAD_DEFAULT, help="regex on cmd output marking a dead proxy")
    r.add_argument("--background-discovery", action="store_true")
    r.add_argument("--test-url", default="https://www.youtube.com/generate_204")
    r.add_argument("--vworkers", type=int, default=150); r.add_argument("--vtimeout", type=float, default=7)
    a = ap.parse_args()
    os.makedirs(a.store, exist_ok=True)
    if a.action == "discover":
        discover(a.store, a.sources)
    elif a.action == "validate":
        validate(a.store, a.test_url, a.workers, a.timeout)
    elif a.action == "run":
        run(a.store, a.worklist, a.cmd, a.workers, a.per_item_proxies, a.item_timeout,
            a.background_discovery, a.test_url, a.vworkers, a.vtimeout, a.success_glob, a.dead_regex)


if __name__ == "__main__":
    main()
