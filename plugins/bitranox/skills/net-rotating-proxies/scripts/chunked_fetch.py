"""Download one large file as byte-range chunks spread over a rotating proxy pool.

Used by ``proxy_pool.py fetch``. The pool is a parameter - anything with acquire(n),
mark_in_use(p), record(p, ok), evict(p), ban(p) and active(), i.e. proxy_pool.ProxyPool - so
this module never imports proxy_pool and its tests drive the real pool.

Why chunks: through free proxies a large file is rarely carried end to end by one exit-IP. A
ban or a dropped session mid-transfer is the normal case, so the file is split into ranges,
each range is retried on a fresh proxy, and the bytes a cut attempt already delivered are kept
(the next attempt asks only for the rest). Every reply is checked for being the requested slice
of the same object BEFORE any byte is written. A reply that is not - an injected page, another
range, a changed ETag, a 404 - may be the proxy lying or the origin having changed, and one
proxy's word cannot tell which: that proxy is evicted for this run only, and when a second proxy
reports the same answer the run stops (OriginChanged) rather than burn the pool on it. Only a
proxy that gave no HTTP answer at all is banned to the permanent bad.txt. An origin that ignores
Range gets one whole-file stream per attempt, rotated over the same pool, with no resume.
"""
import concurrent.futures as cf
import contextlib
import hashlib
import json
import os
import re
import sys
import threading
import time
import typing
import urllib.parse

import httpcore2
import httpx2

# [0-9], not \d: \d also matches non-ASCII digits, which int() then accepts.
_CONTENT_RANGE = re.compile(r"bytes ([0-9]+)-([0-9]+)/([0-9]+)")
_SIZE = re.compile(r"([0-9]+)([KMG]?)", re.IGNORECASE)
_CONNECT_STATUS = re.compile(r"([0-9]{3})(?: |$)")
_UNITS = {"": 1, "K": 1024, "M": 1024**2, "G": 1024**3}
_THROTTLED = {403, 407, 429}
_BAN = {"dead"}
_SUSPECT = {"wrong-object", "identity"}
_FAIL = {"throttled", "cut", "overrun"}
# Enough for a release-asset or mirror-redirector chain (one to three hops); a loop ends here.
MAX_REDIRECTS = 8


class FetchError(Exception):
    """The download cannot be done as asked (exit 2): hash mismatch, mismatching manifest."""


class HashMismatch(FetchError):
    pass


class ManifestMismatch(FetchError):
    pass


class OriginChanged(FetchError):
    """Two proxies agree the origin no longer answers what the probe saw."""


class BadUrl(FetchError):
    pass


class Outcome(typing.NamedTuple):
    """One attempt: its reason, the bytes it wrote, and - for a suspect reply - what it says the
    origin now answers (two proxies with the same `answer` stop the run)."""
    reason: str
    written: int = 0
    answer: str | None = None


def check_url(url):
    """Refuse anything but an absolute http(s) URL, before any proxy is asked.

    httpx2 would raise UnsupportedProtocol inside every attempt instead, which reads as a cut:
    the run would spend the pool and end with 'no proxy answered' for what is a typo."""
    try:
        parts = urllib.parse.urlsplit(url)
        host = parts.hostname
    except ValueError:              # an unbalanced '[' in the host
        host = None
    if host is None or parts.scheme.lower() not in ("http", "https"):
        raise BadUrl(f"not an http or https URL: {url!r} (write it as https://host/path)")


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


def ranged_verdict(status, headers, start, end, total, identity):
    """(reason, answer) for a reply to 'Range: bytes=start-end'; (None, None) when it is that slice.

    'throttled' is a status the proxy or the origin may lift later (rotate, never ban).
    'wrong-object' and 'identity' are suspect: the reply is not the slice, and it may be the
    proxy's doing (an injected page, a stale cache, a rewritten header) or the origin's (the file
    was replaced, the URL removed). `answer` then says what the origin would now be answering, in
    words that name no chunk offset, so two proxies on different chunks can agree on it.
    """
    if status in _THROTTLED or status >= 500:
        return "throttled", None
    if status != 206:
        return "wrong-object", f"HTTP {status}"
    found = parse_content_range(headers.get("content-range"))
    if found and found[2] != total:
        return "wrong-object", f"size {found[2]} (the probe saw {total})"
    if found != (start, end, total):
        return "wrong-object", "HTTP 206 for another range than the one asked for"
    return _body_verdict(headers, identity)


def whole_verdict(status, headers, total, identity):
    """(reason, answer) for a plain GET (no Range); (None, None) when it is the whole object.

    The reasons and answers mean what they mean in ranged_verdict. An injected page answers 200
    as well, so a Content-Length other than the probed size is 'wrong-object'; a reply without one
    is accepted here and its length is counted while it streams.
    """
    if status in _THROTTLED or status >= 500:
        return "throttled", None
    if status != 200:
        return "wrong-object", f"HTTP {status}"
    length = headers.get("content-length")
    if total is not None and length is not None and length.strip() != str(total):
        return "wrong-object", f"size {length.strip()} (the probe saw {total})"
    return _body_verdict(headers, identity)


def reply_problem(status, headers, start, end, total, identity):
    """The reason alone of ranged_verdict, or None."""
    return ranged_verdict(status, headers, start, end, total, identity)[0]


def whole_reply_problem(status, headers, total, identity):
    """The reason alone of whole_verdict, or None."""
    return whole_verdict(status, headers, total, identity)[0]


def _body_verdict(headers, identity):
    # Compressed bytes written as content would line up with nothing. Suspect, not dead: a proxy
    # may ignore 'Accept-Encoding: identity', but so may an origin backend (a .gz served with
    # 'Content-Encoding: gzip' by one server behind a balancer), and bad.txt is permanent.
    encoding = (headers.get("content-encoding") or "identity").strip().lower()
    if encoding != "identity":
        return "wrong-object", f"Content-Encoding {encoding}"
    seen = identity_of(headers)
    # A validator the probe never saw cannot be compared; one it saw must come back unchanged.
    compared = [key for key, want in identity.items() if want]
    if any(seen[key] != identity[key] for key in compared):
        labels = {"etag": "ETag", "last_modified": "Last-Modified"}
        now = ", ".join(f"{labels[k]} {seen[k] or '(none)'}" for k in compared)
        was = ", ".join(f"{labels[k]} {identity[k]}" for k in compared)
        return "identity", f"{now} (the probe saw {was})"
    return None, None


def action_for(reason):
    """The pool call an attempt's reason earns: 'ok' -> record success, 'ban' -> bad.txt,
    'suspect' -> evict for this run and count its answer toward an origin change, 'fail' ->
    record a failure (flaky eviction for this run, never bad.txt). An unknown reason raises:
    mapped to 'fail' it would silently spare a proxy that a misspelt reason meant to ban."""
    if reason == "ok":
        return "ok"
    if reason in _BAN:
        return "ban"
    if reason in _SUSPECT:
        return "suspect"
    if reason in _FAIL:
        return "fail"
    raise ValueError(f"unknown attempt reason: {reason!r}")


def connect_status(exc):
    """The 4xx/5xx status of a CONNECT the proxy refused, or None when the error carries none.

    httpcore2 raises ProxyError(f"{status} {reason}") for any non-2xx CONNECT reply
    (httpcore2/_sync/http_proxy.py lines 285-290 in 2.16.0) and nothing else of its http proxy
    raises one; _httpx2_errors below keeps that message. So the status exists only as the text's
    first three digits. A 3xx refusal, or a SOCKS error worded otherwise, gives None.
    """
    m = _CONNECT_STATUS.match(str(exc))
    status = int(m.group(1)) if m else 0
    return status if 400 <= status <= 599 else None


def _stderr(message):
    # Warnings never share stdout with the progress lines a caller may parse.
    print(message, file=sys.stderr)


class _DeadlineStream(httpcore2.NetworkStream):
    """A socket stream whose every operation is cut short at one wall-clock deadline.

    httpx2's own timeouts bound each read, not the attempt: a proxy sending one header byte per
    read timeout, or stalling after its last body byte, outlives any budget checked between body
    blocks. Clamping each operation's timeout to what is left of the budget ends it in time with
    no watchdog thread, and the error is the ordinary timeout the caller already handles."""

    def __init__(self, inner, deadline):
        self._inner, self._deadline = inner, deadline

    def _left(self, timeout, spent):
        left = self._deadline - time.monotonic()
        if left <= 0:
            raise spent("the attempt's time budget is spent")
        return left if timeout is None else min(timeout, left)

    def read(self, max_bytes, timeout=None):
        return self._inner.read(max_bytes, self._left(timeout, httpcore2.ReadTimeout))

    def write(self, buffer, timeout=None):
        self._inner.write(buffer, self._left(timeout, httpcore2.WriteTimeout))

    def close(self):
        self._inner.close()

    def start_tls(self, ssl_context, server_hostname=None, timeout=None):
        tls = self._inner.start_tls(ssl_context, server_hostname,
                                    self._left(timeout, httpcore2.ConnectTimeout))
        return _DeadlineStream(tls, self._deadline)

    def get_extra_info(self, info):
        return self._inner.get_extra_info(info)


class _DeadlineBackend(httpcore2.NetworkBackend):
    def __init__(self, deadline):
        self._inner, self._deadline = httpcore2.SyncBackend(), deadline

    def connect_tcp(self, host, port, timeout=None, local_address=None, socket_options=None):
        left = self._deadline - time.monotonic()
        if left <= 0:
            raise httpcore2.ConnectTimeout("the attempt's time budget is spent")
        timeout = left if timeout is None else min(timeout, left)
        stream = self._inner.connect_tcp(host, port, timeout, local_address, socket_options)
        return _DeadlineStream(stream, self._deadline)

    def sleep(self, seconds):
        self._inner.sleep(seconds)


@contextlib.contextmanager
def _httpx2_errors():
    # The httpx2 class of the same name, as httpx2's own transport maps them (its table pairs
    # every httpcore2 class with the httpx2 one of that name), so callers catch httpx2 classes.
    # The message is kept: connect_status reads the refused CONNECT's status out of it.
    try:
        yield
    except Exception as exc:
        if not type(exc).__module__.startswith("httpcore2"):
            raise
        for cls in type(exc).__mro__:
            mapped = getattr(httpx2, cls.__name__, None)
            if isinstance(mapped, type) and issubclass(mapped, httpx2.TransportError):
                raise mapped(str(exc)) from exc
        raise


class _ReplyStream(httpx2.SyncByteStream):
    def __init__(self, stream):
        self._stream = stream

    def __iter__(self):
        with _httpx2_errors():
            yield from self._stream

    def close(self):
        with _httpx2_errors():
            self._stream.close()


class _DeadlineTransport(httpx2.BaseTransport):
    """httpx2's proxy transport, rebuilt on the public httpcore2 API with a _DeadlineBackend.

    httpx2.HTTPTransport takes no network backend, so it cannot carry the deadline."""

    def __init__(self, proxy, deadline):
        # trust_env=False: SSL_CERT_FILE / SSL_CERT_DIR must not swap the trust store either.
        self._pool = httpcore2.HTTPProxy(proxy_url=f"http://{proxy}",
                                         ssl_context=httpx2.create_ssl_context(trust_env=False),
                                         network_backend=_DeadlineBackend(deadline))

    def handle_request(self, request):
        url = httpcore2.URL(scheme=request.url.raw_scheme, host=request.url.raw_host,
                            port=request.url.port, target=request.url.raw_path)
        core = httpcore2.Request(method=request.method, url=url, headers=request.headers.raw,
                                 content=request.stream, extensions=request.extensions)
        with _httpx2_errors():
            reply = self._pool.handle_request(core)
        return httpx2.Response(status_code=reply.status, headers=reply.headers,
                               stream=_ReplyStream(reply.stream), extensions=reply.extensions)

    def close(self):
        self._pool.close()


def _client(proxy, timeout):
    # `timeout` bounds each read AND, through the transport's deadline, the whole attempt from
    # connect to last byte, redirects included. trust_env=False: a machine-wide HTTP_PROXY /
    # NO_PROXY must never reroute or bypass the proxy this attempt was given. Redirects are
    # followed (through the same proxy): release assets and mirror redirectors answer 302, and
    # every check below applies to the final reply.
    limits = httpx2.Timeout(timeout, connect=min(timeout, 15.0))
    return httpx2.Client(transport=_DeadlineTransport(proxy, time.monotonic() + timeout),
                         timeout=limits, trust_env=False, follow_redirects=True,
                         max_redirects=MAX_REDIRECTS)


def _refused_connect(exc, verdict):
    """The Outcome of a ProxyError: a refusal with a 4xx/5xx status counts as that status would
    over plain http (verdict(status) - a 502 for an unreachable origin is no dead proxy); one
    without such a status is a proxy that will not carry the request at all."""
    status = connect_status(exc)
    if status is None:
        return Outcome("dead")
    reason, answer = verdict(status)
    return Outcome(reason, 0, answer)


def attempt(url, proxy, offset, end, total, identity, path, timeout):
    """One GET of bytes offset..end through proxy, written into path at offset. Returns an Outcome.

    The reply is classified before the file is opened, so a wrong object never touches it; bytes
    past `end` are dropped ('overrun'); a transfer cut short keeps what arrived ('cut'), and the
    caller asks for the rest on the next attempt.

    `timeout` bounds each read AND is the budget of the whole attempt, connect to last byte (see
    _DeadlineStream). Running out of it is a 'cut' - the bytes already written stay and the next
    attempt resumes after them.
    """
    want, written = end - offset + 1, 0
    headers = {"Range": f"bytes={offset}-{end}", "Accept-Encoding": "identity"}
    try:
        with _client(proxy, timeout) as client, client.stream("GET", url, headers=headers) as reply:
            reason, answer = ranged_verdict(reply.status_code, reply.headers, offset, end, total,
                                            identity)
            if reason:
                return Outcome(reason, 0, answer)
            with open(path, "r+b") as f:
                f.seek(offset)
                try:
                    for block in reply.iter_raw():      # raw: nothing may be decoded in between
                        take = block[:want - written]
                        f.write(take)
                        written += len(take)
                        if len(take) < len(block):
                            return Outcome("overrun", written)
                finally:
                    f.flush()
                    os.fsync(f.fileno())   # the manifest records `written` only once it is on disk
    except httpx2.ProxyError as exc:
        return _refused_connect(exc, lambda status: ranged_verdict(status, {}, offset, end, total,
                                                                   identity))
    except (httpx2.ConnectError, httpx2.ConnectTimeout):
        return Outcome("dead", written)
    except httpx2.TooManyRedirects:
        return Outcome("wrong-object", written, f"more than {MAX_REDIRECTS} redirects")
    except httpx2.TransportError:
        return Outcome("cut", written)
    return Outcome("ok" if written == want else "cut", written)


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
    if (headers.get("content-encoding") or "identity").strip().lower() != "identity":
        return None                         # a compressed reply describes no byte offsets
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
    that rewrites ETag would plant an identity every honest proxy then contradicts. So each reply
    is a vote, and the probe stops at `attempts` probes, at once when a view reaches two distinct
    proxies, or when every proxy still active has voted. Otherwise, at the end, the view with the
    most votes wins, and a ranged view wins a tie against whole-file ones; a top count shared by
    two ranged views (or two whole-file ones) is no decision, and the probe refuses rather than
    let whichever answered first plant its view. A view resting on one proxy is warned as not
    cross-checked. Returns a _Probe, or None when nobody answered or the views tie.
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
        except httpx2.ProxyError as exc:
            # A refusal with a 4xx/5xx status casts no vote, exactly as that status would over
            # plain http (_vote_key gives None for it); one without such a status is a dead proxy.
            if connect_status(exc) is None:
                pool.ban(proxy)
            else:
                pool.record(proxy, False)
            continue
        except (httpx2.ConnectError, httpx2.ConnectTimeout):
            pool.ban(proxy)
            continue
        except (httpx2.TransportError, httpx2.TooManyRedirects):
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
    top = max(len(v) for v in votes.values())
    tied = [k for k in votes if len(votes[k]) == top]
    winners = [k for k in tied if k[0]] or tied     # a ranged view beats whole-file ones on a tie
    if len(winners) > 1:
        (warn or _stderr)(f"probe: proxies disagree about the object ({len(votes)} distinct "
                          f"views); refusing to guess - rerun later or use --sha256")
        return None
    if len(set().union(*votes.values())) == 1:
        (warn or _stderr)("probe: only one proxy answered; its view of the object was not "
                          "cross-checked - pass --sha256 to verify the result")
    elif len(votes[winners[0]]) == 1:
        # A ranged view that won a tie against whole-file ones still has ONE voter: its size and
        # identity were never confirmed by a second proxy.
        (warn or _stderr)("probe: proxies disagreed; took the ranged view of one proxy, not "
                          "cross-checked - pass --sha256 to verify the result")
    return _decide(winners[0])


def _decide(key):
    ranged, total, etag, last_modified = key
    return _Probe(total, {"etag": etag, "last_modified": last_modified}, ranged)


class _Witnesses:
    """Suspect answers, each with the distinct proxies that gave it.

    One proxy's odd answer may be that proxy or the origin. Banning on it wrote every clean proxy
    into the permanent bad.txt whenever it was the origin (a replaced file, a removed URL), so it
    only evicts; two distinct proxies giving the same answer is the origin, and the run stops."""

    def __init__(self):
        self._lock, self._seen, self.answer = threading.Lock(), {}, None

    def report(self, answer, proxy):
        """Record proxy's answer; True once some answer has two distinct proxies behind it."""
        with self._lock:
            proxies = self._seen.setdefault(answer, set())
            proxies.add(proxy)
            if self.answer is None and len(proxies) >= 2:
                self.answer = answer
            return self.answer is not None

    def error(self, url, kept):
        return OriginChanged(f"two proxies report that {url} now answers {self.answer}; stopped "
                             f"without banning either. {kept}")


def _load_manifest(path, expected):
    """The saved progress, or a fresh one; refuses a manifest for another object or plan, and
    one that is damaged (a crash mid-write, a hand edit) rather than trusting its offsets."""
    if not os.path.exists(path):
        return dict(expected, received=[0] * expected["chunks"])
    try:
        with open(path, encoding="utf-8") as f:
            saved = json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise _damaged(path, f"it is not valid JSON ({exc})") from exc
    if not isinstance(saved, dict):
        raise _damaged(path, "it is not a JSON object")
    differs = [key for key in expected if saved.get(key) != expected[key]]
    if differs:
        raise ManifestMismatch(f"{path} belongs to another download ({', '.join(differs)} differ); "
                               f"delete it and {path.removesuffix('.json')} to start over")
    problem = _received_problem(saved.get("received"), expected)
    if problem:
        raise _damaged(path, problem)
    return saved


def _damaged(path, why):
    return ManifestMismatch(f"{path} is damaged: {why}; delete it and "
                            f"{path.removesuffix('.json')} to start over")


def _received_problem(received, expected):
    """Why `received` cannot be this plan's per-chunk byte counts, or None."""
    if not isinstance(received, list) or len(received) != expected["chunks"]:
        return f"'received' is not a list of {expected['chunks']} counts"
    total, size = expected["total"], expected["chunk_size"]
    for index, value in enumerate(received):
        length = min(size, total - index * size)
        # bool is an int subclass, and True would read as one byte received.
        if type(value) is not int or not 0 <= value <= length:
            return f"'received'[{index}] is {value!r}, not a count between 0 and {length}"
    return None


# Mirrors proxy_pool._retry_sharing_violation; this module must never import proxy_pool.
_SHARING_RETRY_DELAYS = (0.01, 0.02, 0.05, 0.1, 0.2, 0.4)


def _retry_sharing_violation(op, windows=os.name == "nt", sleep=time.sleep):
    """Return op(), retrying while Windows reports a sharing violation (PermissionError).

    A reader or a virus scanner holding the manifest open makes os.replace onto it fail for a few
    milliseconds on Windows; off Windows a PermissionError is an access right, raised at once."""
    for delay in _SHARING_RETRY_DELAYS:
        try:
            return op()
        except PermissionError:
            if not windows:
                raise
            sleep(delay)
    return op()


def _save_manifest(path, state):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f)
        f.flush()
        os.fsync(f.fileno())     # on disk before it replaces the old one, or a crash leaves it empty
    _retry_sharing_violation(lambda: os.replace(tmp, path))


def _sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _settle(pool, proxy, outcome, on_success, witnesses):
    """Make the pool call the outcome earns; True when it settled that the origin changed."""
    action = action_for(outcome.reason)
    if action == "ok":
        pool.record(proxy, True)
        if on_success:
            on_success(proxy)
    elif action == "ban":
        pool.ban(proxy)
    elif action == "suspect":
        pool.evict(proxy)
        return witnesses.report(outcome.answer, proxy)
    else:
        pool.record(proxy, False)
    return False


def _finish(part, out, sha256, manifest=None, retry=_retry_sharing_violation):
    """Verify and move the part into place; on a wrong hash drop the manifest, keep the part.

    Both the move and the removal go through `retry`: on Windows a scanner or indexer that just
    opened the finished part makes them fail for a moment, as it does for _save_manifest."""
    if sha256 and _sha256_of(part) != sha256.lower():
        if manifest and os.path.exists(manifest):
            retry(lambda: os.remove(manifest))
        raise HashMismatch(f"sha256 of the downloaded file does not match; kept it as {part}")
    retry(lambda: os.replace(part, out))
    if manifest and os.path.exists(manifest):
        retry(lambda: os.remove(manifest))


def _stream_whole(url, proxy, part, info, timeout):
    """One plain GET of the whole object through proxy, written into part from byte 0.

    Returns an Outcome whose `written` is always 0: without Range there is no way to ask for the
    rest, so the bytes of a failed attempt are never resumed and the next one rewrites part from
    byte 0. The reply is classified before part is opened, and `timeout` is the whole attempt's
    budget as in attempt (a trickling proxy would otherwise hold the run).
    """
    total, written = info.total, 0
    try:
        with _client(proxy, timeout) as client, \
                client.stream("GET", url, headers={"Accept-Encoding": "identity"}) as reply:
            reason, answer = whole_verdict(reply.status_code, reply.headers, total, info.identity)
            if reason:
                return Outcome(reason, 0, answer)
            with open(part, "wb") as f:
                for block in reply.iter_raw():      # raw: nothing may be decoded in between
                    if total is not None and written + len(block) > total:
                        return Outcome("overrun")   # only reachable for a reply without a length
                    f.write(block)
                    written += len(block)
    except httpx2.ProxyError as exc:
        return _refused_connect(exc, lambda status: whole_verdict(status, {}, total, info.identity))
    except (httpx2.ConnectError, httpx2.ConnectTimeout):
        return Outcome("dead")
    except httpx2.TooManyRedirects:
        return Outcome("wrong-object", 0, f"more than {MAX_REDIRECTS} redirects")
    except httpx2.TransportError:
        return Outcome("cut")
    return Outcome("ok" if total is None or written == total else "cut")


def _whole_attempts(url, part, pool, info, timeout, attempts, on_success, counts, witnesses):
    """Stream attempts until one succeeds; returns (ok, dry). Same rules as a chunk's loop:
    waiting for a proxy spends no attempt, an empty active pool stops at once, and so does an
    origin change two proxies agree on."""
    tries = 0
    while tries < attempts:
        picks = pool.acquire(1)
        if not picks:
            if not pool.active():
                return False, True
            time.sleep(0.05)
            continue
        tries += 1
        pool.mark_in_use(picks[0])
        outcome = _stream_whole(url, picks[0], part, info, timeout)
        counts[outcome.reason] = counts.get(outcome.reason, 0) + 1
        if _settle(pool, picks[0], outcome, on_success, witnesses):
            return False, False
        if outcome.reason == "ok":
            return True, False
    return False, False


def _fetch_whole(url, out, pool, sha256, timeout, attempts, on_success, info, log, warn):
    """Origin ignores Range: one whole-file stream per attempt, restarted from 0 each time.

    No manifest is kept, since there is nothing to resume. One that a ranged run left for this
    file is refused: the stream would overwrite the bytes it records as received, and a later
    ranged run trusting it would leave holes in the file.
    """
    part, manifest = out + ".part", out + ".part.json"
    if os.path.exists(manifest):
        raise ManifestMismatch(f"{manifest} belongs to a ranged download, but the origin now "
                               f"ignores Range; delete it and {part} to start over")
    log("origin ignores Range: one whole-file stream per attempt, no resume")
    if info.total is None and sha256 is None:
        # No size to count against: a cut close-delimited body or a substituted page ends as
        # cleanly as the real object, so nothing but a hash can tell them apart.
        warn("probe: the origin sent no size; a cut or substituted transfer cannot be detected "
             "- pass --sha256 to verify the result")
    counts, witnesses = {}, _Witnesses()
    ok, dry = _whole_attempts(url, part, pool, info, timeout, attempts, on_success, counts,
                              witnesses)
    log(f"whole file, attempts {sum(counts.values())}: "
        + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    if witnesses.answer:
        raise witnesses.error(url, "Rerun once the URL serves the file again.")
    if dry:
        counts["pool-dry"] = 1                  # added after the line above: it is not an attempt
        log("pool ran dry: the whole file is still missing")
    if not ok:
        return FetchResult(False, 0, 1, counts, "whole file still missing; rerun to start over")
    _finish(part, out, sha256)
    return FetchResult(True, 1, 1, counts)


def fetch(url, out, pool, *, chunk_size, workers=8, sha256=None, timeout=120.0, max_attempts=20,
          on_success=None, log=print, warn=None):
    """Download url to out through pool; see the module docstring. Returns a FetchResult.

    `log` gets the progress/report lines (stdout by default), `warn` the warnings (stderr).
    `timeout` is one attempt's whole budget, connect to last byte (see attempt). A pool emptied
    by bans and evictions stops the run at once, reported as a 'pool-dry' count, never as
    attempts. When the probe finds the origin ignores Range, the file comes as one whole stream
    per attempt instead (max_attempts in all, no manifest, no resume). Raises BadUrl before any
    network work for a URL that is not http(s), and OriginChanged when two proxies report the
    same answer that is not the probed object (the part and manifest are kept).
    """
    check_url(url)
    info = probe(url, pool, timeout, max_attempts, warn)
    if info is None:
        return FetchResult(False, note="the probe settled nothing: no proxy answered, or the "
                                       "answers disagreed")
    if not info.ranged:
        return _fetch_whole(url, out, pool, sha256, timeout, max_attempts, on_success, info, log,
                            warn or _stderr)
    part, manifest = out + ".part", out + ".part.json"
    chunks = plan_chunks(info.total, chunk_size)
    state = _load_manifest(manifest, {"url": url, "total": info.total, "identity": info.identity,
                                      "chunk_size": chunk_size, "chunks": len(chunks)})
    if not os.path.exists(part):
        state["received"] = [0] * len(chunks)   # progress without its bytes is no progress
    with open(part, "a+b") as f:
        f.truncate(info.total)
    lock, counts, dry, stop = threading.Lock(), {}, threading.Event(), threading.Event()
    witnesses = _Witnesses()

    def run_chunk(index):
        start, end = chunks[index]
        tries = 0
        # A wait for a proxy is not an attempt: counted, it burnt max_attempts per chunk while
        # every proxy was busy, and spun the whole budget once the pool was empty.
        while tries < max_attempts and not dry.is_set() and not stop.is_set():
            offset = start + state["received"][index]
            if offset > end:
                return True
            picks = pool.acquire(1)
            if not picks:
                if not pool.active():
                    dry.set()          # nothing left to ask: every worker stops taking attempts
                    break
                time.sleep(0.05)
                continue
            tries += 1
            pool.mark_in_use(picks[0])
            outcome = attempt(url, picks[0], offset, end, info.total, info.identity, part, timeout)
            with lock:
                state["received"][index] += outcome.written
                counts[outcome.reason] = counts.get(outcome.reason, 0) + 1
                _save_manifest(manifest, state)
            if _settle(pool, picks[0], outcome, on_success, witnesses):
                stop.set()             # the origin changed: no more attempts on any chunk
        return start + state["received"][index] > end

    with cf.ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        try:
            done = sum(ex.map(run_chunk, range(len(chunks))))
        except BaseException:
            # A Ctrl-C lands here; map cancels the queued chunks, but leaving the with-block joins
            # the running ones, which would spend their whole attempt budget first. Stopping them
            # after their current attempt bounds the wait to one attempt.
            stop.set()
            raise
    log(f"chunks {done}/{len(chunks)}, attempts {sum(counts.values())}: "
        + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    if witnesses.answer:
        _save_manifest(manifest, state)
        raise witnesses.error(url, f"The bytes received so far stay in {part}: rerun once the URL "
                                   f"serves the file again (if the file itself changed, the rerun "
                                   f"refuses the old manifest and names the files to delete).")
    if dry.is_set():
        counts["pool-dry"] = 1                  # added after the line above: it is not an attempt
        log(f"pool ran dry: {len(chunks) - done} chunk(s) left")
    if done < len(chunks):
        _save_manifest(manifest, state)
        return FetchResult(False, done, len(chunks), counts, "chunks still missing; rerun to resume")
    _finish(part, out, sha256, manifest)
    return FetchResult(True, done, len(chunks), counts)
