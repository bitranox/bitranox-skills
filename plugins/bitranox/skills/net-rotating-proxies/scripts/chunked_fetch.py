"""Download one large file as byte-range chunks spread over a rotating proxy pool.

Used by ``proxy_pool.py fetch``. The pool is a parameter - anything with acquire(n),
mark_in_use(p), record(p, ok), ban(p) and active(), i.e. proxy_pool.ProxyPool - so this module
never imports proxy_pool and its tests drive the real pool.

Why chunks: through free proxies a large file is rarely carried end to end by one exit-IP. A
ban or a dropped session mid-transfer is the normal case, so the file is split into ranges,
each range is retried on a fresh proxy, and the bytes a cut attempt already delivered are kept
(the next attempt asks only for the rest). Every reply is checked for being the requested slice
of the same object BEFORE any byte is written: a proxy that answers with an injected page, a
stale cache or the wrong range is banned instead of corrupting the file.
"""
import concurrent.futures as cf
import hashlib
import json
import os
import re
import sys
import threading
import time

import httpx2

# [0-9], not \d: \d also matches non-ASCII digits, which int() then accepts.
_CONTENT_RANGE = re.compile(r"bytes ([0-9]+)-([0-9]+)/([0-9]+)")
_SIZE = re.compile(r"([0-9]+)([KMG]?)", re.IGNORECASE)
_UNITS = {"": 1, "K": 1024, "M": 1024**2, "G": 1024**3}
_THROTTLED = {403, 407, 429}
_BAN = {"dead", "wrong-object", "identity"}
_FAIL = {"throttled", "cut", "overrun"}


class FetchError(Exception):
    """The download cannot be done as asked (exit 2): hash mismatch, mismatching manifest."""


class HashMismatch(FetchError):
    pass


class ManifestMismatch(FetchError):
    pass


def parse_size(text):
    """Bytes for '8M', '512K', '1G' or a plain number (binary units); ValueError otherwise."""
    m = _SIZE.fullmatch(text)
    if not m or int(m.group(1)) == 0:
        raise ValueError(f"not a size: {text!r} (use e.g. 8M, 512K, 1G)")
    return int(m.group(1)) * _UNITS[m.group(2).upper()]


def plan_chunks(total, size):
    """Inclusive (start, end) ranges covering 0..total-1; the last one may be shorter."""
    return [(s, min(s + size, total) - 1) for s in range(0, total, size)]


def parse_content_range(value):
    """(start, end, total) from 'bytes a-b/n', or None for anything else ('*' included)."""
    m = _CONTENT_RANGE.fullmatch((value or "").strip())
    return tuple(int(g) for g in m.groups()) if m else None


def identity_of(headers):
    """The validators that name ONE version of the object, as the probe saw them."""
    return {"etag": headers.get("etag"), "last_modified": headers.get("last-modified")}


def reply_problem(status, headers, start, end, total, identity):
    """Why a reply to 'Range: bytes=start-end' is not that slice of the object, or None.

    'throttled' is a status the proxy or the origin may lift later (rotate, never ban);
    'wrong-object' and 'identity' mean the proxy is serving something else - an injected page, a
    stale cache, the wrong range - so trusting its bytes would corrupt the file.
    """
    if status in _THROTTLED or status >= 500:
        return "throttled"
    if status != 206 or parse_content_range(headers.get("content-range")) != (start, end, total):
        return "wrong-object"
    seen = identity_of(headers)
    # A validator the probe never saw cannot be compared; one it saw must come back unchanged.
    if any(want and seen[key] != want for key, want in identity.items()):
        return "identity"
    return None


def action_for(reason):
    """The pool call an attempt's reason earns: 'ok' -> record success, 'ban' -> bad.txt,
    'fail' -> record a failure (flaky eviction for this run, never bad.txt). An unknown reason
    raises: mapped to 'fail' it would silently spare a proxy that a misspelt reason meant to ban."""
    if reason == "ok":
        return "ok"
    if reason in _BAN:
        return "ban"
    if reason in _FAIL:
        return "fail"
    raise ValueError(f"unknown attempt reason: {reason!r}")


def _stderr(message):
    # Warnings never share stdout with the progress lines a caller may parse.
    print(message, file=sys.stderr)


def _client(proxy, timeout):
    # trust_env=False: a machine-wide HTTP_PROXY / NO_PROXY must never reroute or bypass the
    # proxy this attempt was given.
    limits = httpx2.Timeout(timeout, connect=min(timeout, 15.0))
    return httpx2.Client(proxy=f"http://{proxy}", timeout=limits, trust_env=False)


def attempt(url, proxy, offset, end, total, identity, path, timeout):
    """One GET of bytes offset..end through proxy, written into path at offset.

    Returns (reason, written). The reply is classified before the file is opened, so a wrong
    object never touches it; bytes past `end` are dropped ('overrun'); a transfer cut short
    keeps what arrived ('cut'), and the caller asks for the rest on the next attempt.
    """
    want, written = end - offset + 1, 0
    headers = {"Range": f"bytes={offset}-{end}", "Accept-Encoding": "identity"}
    try:
        with _client(proxy, timeout) as client, client.stream("GET", url, headers=headers) as reply:
            problem = reply_problem(reply.status_code, reply.headers, offset, end, total, identity)
            if problem:
                return problem, 0
            with open(path, "r+b") as f:
                f.seek(offset)
                try:
                    for block in reply.iter_raw():      # raw: nothing may be decoded in between
                        take = block[:want - written]
                        f.write(take)
                        written += len(take)
                        if len(take) < len(block):
                            return "overrun", written
                finally:
                    f.flush()
                    os.fsync(f.fileno())   # the manifest records `written` only once it is on disk
    except (httpx2.ConnectError, httpx2.ConnectTimeout, httpx2.ProxyError):
        return "dead", written
    except httpx2.TransportError:
        return "cut", written
    return ("ok" if written == want else "cut"), written


class FetchResult:
    def __init__(self, ok, done=0, chunks=0, counts=None, note=""):
        self.ok, self.done, self.chunks, self.counts, self.note = ok, done, chunks, counts or {}, note


class _Probe:
    def __init__(self, total, identity, ranged):
        self.total, self.identity, self.ranged = total, identity, ranged


def _probe_once(url, proxy, timeout):
    headers = {"Range": "bytes=0-0", "Accept-Encoding": "identity"}
    with _client(proxy, timeout) as client, client.stream("GET", url, headers=headers) as reply:
        return reply.status_code, reply.headers


def _vote_key(status, headers):
    """What one probe reply says about the object, or None when it says nothing usable.

    Key = (ranged, total, etag, last_modified). Only an exact 'bytes 0-0/N' counts as ranged: a
    proxy answering some other range would otherwise plant a bogus size.
    """
    ident = identity_of(headers)
    found = parse_content_range(headers.get("content-range"))
    if status == 206 and found and found[:2] == (0, 0):
        return (True, found[2], ident["etag"], ident["last_modified"])
    if status == 416 and (headers.get("content-range") or "").strip() == "bytes */0":
        return (True, 0, ident["etag"], ident["last_modified"])
    if status == 200:
        length = headers.get("content-length")
        total = int(length) if length and length.isascii() and length.isdigit() else None
        return (False, total, ident["etag"], ident["last_modified"])
    return None


def probe(url, pool, timeout, attempts, warn=None):
    """Size, identity and Range support of the object, decided by votes across proxies.

    One proxy's answer is not trusted alone: an injecting proxy answers 200 with a page, and one
    that rewrites ETag would plant an identity every honest proxy then fails, getting them all
    banned. So each reply is a vote, and the probe decides when two distinct proxies agree, or
    when every proxy still active has answered (most votes wins, a ranged answer wins a tie, and
    a decision only one proxy backs is logged as not cross-checked). Returns a _Probe, or None
    when nobody answered within `attempts`.
    """
    votes = {}
    for _ in range(attempts):
        picks = pool.acquire(1)
        if not picks:
            break
        proxy = picks[0]
        pool.mark_in_use(proxy)
        try:
            status, headers = _probe_once(url, proxy, timeout)
        except (httpx2.ConnectError, httpx2.ConnectTimeout, httpx2.ProxyError):
            pool.ban(proxy)
            continue
        except httpx2.TransportError:
            pool.record(proxy, False)
            continue
        key = _vote_key(status, headers)
        pool.record(proxy, key is not None)
        if key is None:
            continue
        votes.setdefault(key, set()).add(proxy)
        if len(votes[key]) >= 2:
            return _decide(key)
        voters = set().union(*votes.values())
        if pool.active() <= voters:
            break
    if not votes:
        return None
    key = max(votes, key=lambda k: (len(votes[k]), k[0]))
    if len(votes[key]) < 2:
        (warn or _stderr)("probe: only one proxy answered; its view of the object was not "
                          "cross-checked - pass --sha256 to verify the result")
    return _decide(key)


def _decide(key):
    ranged, total, etag, last_modified = key
    return _Probe(total, {"etag": etag, "last_modified": last_modified}, ranged)


def _load_manifest(path, expected):
    """The saved progress, or a fresh one; refuses a manifest for another object or plan."""
    if not os.path.exists(path):
        return dict(expected, received=[0] * expected["chunks"])
    with open(path, encoding="utf-8") as f:
        saved = json.load(f)
    differs = [key for key in expected if saved.get(key) != expected[key]]
    if differs:
        raise ManifestMismatch(f"{path} belongs to another download ({', '.join(differs)} differ); "
                               f"delete it and the .part file to start over")
    return saved


def _save_manifest(path, state):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f)
    os.replace(tmp, path)


def _sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _settle(pool, proxy, reason, on_success):
    action = action_for(reason)
    if action == "ok":
        pool.record(proxy, True)
        if on_success:
            on_success(proxy)
    elif action == "ban":
        pool.ban(proxy)
    else:
        pool.record(proxy, False)


def _finish(part, out, sha256, manifest=None):
    """Verify and move the part into place; on a wrong hash drop the manifest, keep the part."""
    if sha256 and _sha256_of(part) != sha256.lower():
        if manifest and os.path.exists(manifest):
            os.remove(manifest)
        raise HashMismatch(f"sha256 of the downloaded file does not match; kept it as {part}")
    os.replace(part, out)
    if manifest and os.path.exists(manifest):
        os.remove(manifest)


def fetch(url, out, pool, *, chunk_size, workers=8, sha256=None, timeout=120.0, max_attempts=20,
          on_success=None, log=print, warn=None):
    """Download url to out through pool; see the module docstring. Returns a FetchResult.

    `log` gets the progress/report lines (stdout by default), `warn` the warnings (stderr).
    """
    info = probe(url, pool, timeout, max_attempts, warn)
    if info is None:
        return FetchResult(False, note="no proxy answered the probe")
    if not info.ranged:                       # Task 4 replaces this with the whole-file download
        return FetchResult(False, note="the origin ignores Range")
    part, manifest = out + ".part", out + ".part.json"
    chunks = plan_chunks(info.total, chunk_size)
    state = _load_manifest(manifest, {"url": url, "total": info.total, "identity": info.identity,
                                      "chunk_size": chunk_size, "chunks": len(chunks)})
    if not os.path.exists(part):
        state["received"] = [0] * len(chunks)   # progress without its bytes is no progress
    with open(part, "a+b") as f:
        f.truncate(info.total)
    lock, counts = threading.Lock(), {}

    def run_chunk(index):
        start, end = chunks[index]
        for _ in range(max_attempts):
            offset = start + state["received"][index]
            if offset > end:
                return True
            picks = pool.acquire(1)
            if not picks:
                with lock:
                    counts["no-proxy"] = counts.get("no-proxy", 0) + 1
                time.sleep(0.2)
                continue
            pool.mark_in_use(picks[0])
            reason, written = attempt(url, picks[0], offset, end, info.total, info.identity, part,
                                      timeout)
            with lock:
                state["received"][index] += written
                counts[reason] = counts.get(reason, 0) + 1
                _save_manifest(manifest, state)
            _settle(pool, picks[0], reason, on_success)
        return start + state["received"][index] > end

    with cf.ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        done = sum(ex.map(run_chunk, range(len(chunks))))
    log(f"chunks {done}/{len(chunks)}, attempts {sum(counts.values())}: "
        + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    if done < len(chunks):
        _save_manifest(manifest, state)
        return FetchResult(False, done, len(chunks), counts, "chunks still missing; rerun to resume")
    _finish(part, out, sha256, manifest)
    return FetchResult(True, done, len(chunks), counts)
