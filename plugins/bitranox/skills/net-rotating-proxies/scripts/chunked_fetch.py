"""Download one large file as byte-range chunks spread over a rotating proxy pool.

Used by ``proxy_pool.py fetch``. The pool is a parameter - anything with acquire(n),
mark_in_use(p), record(p, ok) and ban(p), i.e. proxy_pool.ProxyPool - so this module never
imports proxy_pool and its tests drive the real pool.

Why chunks: through free proxies a large file is rarely carried end to end by one exit-IP. A
ban or a dropped session mid-transfer is the normal case, so the file is split into ranges,
each range is retried on a fresh proxy, and the bytes a cut attempt already delivered are kept
(the next attempt asks only for the rest). Every reply is checked for being the requested slice
of the same object BEFORE any byte is written: a proxy that answers with an injected page, a
stale cache or the wrong range is banned instead of corrupting the file.
"""
import re

# [0-9], not \d: \d also matches non-ASCII digits, which int() then accepts.
_CONTENT_RANGE = re.compile(r"bytes ([0-9]+)-([0-9]+)/([0-9]+)")
_SIZE = re.compile(r"([0-9]+)([KMG]?)", re.IGNORECASE)
_UNITS = {"": 1, "K": 1024, "M": 1024**2, "G": 1024**3}
_THROTTLED = {403, 407, 429}
_BAN = {"dead", "wrong-object", "identity"}


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
    'fail' -> record a failure (flaky eviction for this run, never bad.txt)."""
    if reason == "ok":
        return "ok"
    return "ban" if reason in _BAN else "fail"
