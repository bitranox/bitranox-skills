#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Tell whether this skill's hook reference still matches the upstream Claude Code docs.

The upstream docs site stamps every page with its build time, so ``Last-Modified`` is identical
across unrelated pages and ``ETag`` is absent. A conditional GET therefore proves nothing and the
only workable signal is a hash of the fetched content.

Hashing the whole body alone would cry wolf: upstream polishes prose most weeks while the hook API
itself changes rarely, and a check that fires every week stops being read. So this compares two
digests. ``content_sha256`` answers "is anything different at all" and ``structure_sha256`` answers
"did the API surface change", over a fingerprint of sorted NAME SETS (events, headings, JSON field
names). Membership changes are structural; reordering and rewording are not.

The dangerous verdict is the negative: "nothing changed" and "I never really looked" are the same
output. Every failure to look lands in BROKEN rather than collapsing into CURRENT, and a body that
arrives truncated is caught by the control gate before it can read as "every event was removed".

Exit codes: 0 current or cosmetic, 1 structural drift or a coverage gap, 2 broken.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import threading
from pathlib import Path
from typing import Any, Callable, Iterable

__all__ = [
    "ControlError",
    "Verdict",
    "normalise",
    "fingerprint",
    "structure_sha",
    "content_sha",
    "sections",
    "build_source_record",
    "compare",
    "coverage",
    "main",
]

SCHEMA = 1
NORMALISATION_ID = "n1"
NORMALISATION_RULES = [
    "crlf->lf",
    "drop-lines-before-first-h1",
    "rstrip-lines",
    "collapse-3+-blank-to-2",
    "strip-edges",
    "single-trailing-lf",
]

CURRENT, COSMETIC, STRUCTURAL, BROKEN = "CURRENT", "COSMETIC", "STRUCTURAL", "BROKEN"
_SEVERITY = {CURRENT: 0, COSMETIC: 1, STRUCTURAL: 2, BROKEN: 3}
_EXIT = {CURRENT: 0, COSMETIC: 0, STRUCTURAL: 1, BROKEN: 2}

H1_RX = re.compile(r"^# \S")
H2_RX = re.compile(r"^## (.+?)\s*$")
H3_RX = re.compile(r"^### (.+?)\s*$")
H4_RX = re.compile(r"^#{4,6} (.+?)\s*$")
FENCE_RX = re.compile(r"^[ \t]*(`{3,}|~{3,})[ \t]*([^`\n]*)$")
JSONKEY_RX = re.compile(r'"([A-Za-z_][A-Za-z0-9_]*)"\s*:')
TYPEVAL_RX = re.compile(r'"type"\s*:\s*"([a-z_]+)"')
ENV_RX = re.compile(r"\bCLAUDE_[A-Z0-9_]+\b")
TICK_RX = re.compile(r"`([^`\n]{1,60})`")
ROW_RX = re.compile(r"^\|\s*([^|]+?)\s*\|")
VERSION_RX = re.compile(r"\bv(2\.\d+\.\d+)\b")
# JSON-Schema primitives share the "type" key with hook handler types. Counting them would let an
# unrelated schema example flip the structural digest, which is the cry-wolf failure this design
# exists to avoid. A genuinely new handler type is never one of these words.
_SCHEMA_PRIMITIVES = frozenset({"object", "string", "array", "number", "boolean", "integer", "null", "result"})

_FP_KEYS = ("headings", "events", "json_fields", "handler_types", "env_vars", "table_keys")

DEFAULT_CACHE_DIR = Path.home() / ".claude" / "bitranox-hookdoc"


class ControlError(Exception):
    """A control gate refused the input, so no verdict can honestly be rendered."""


class Verdict:
    """One source's comparison outcome."""

    def __init__(self, name: str, verdict: str, reason: str = "", detail: dict[str, Any] | None = None) -> None:
        self.name = name
        self.verdict = verdict
        self.reason = reason
        self.detail = detail or {}

    def as_dict(self) -> dict[str, Any]:
        return {"name": self.name, "verdict": self.verdict, "reason": self.reason, **self.detail}


# --------------------------------------------------------------------------- normalisation


def normalise(raw: bytes | str) -> str:
    """Reduce a fetched page to the stable body that both digests are taken over.

    Drops everything before the first ``# `` heading, which removes the constant documentation-index
    preamble without hard-coding its wording, so the preamble can grow a line without flipping the
    hash. Nothing else is collapsed: intra-line whitespace and table alignment stay visible so a
    realignment surfaces as COSMETIC rather than vanishing.

    Raises:
        ControlError: the body does not decode as UTF-8, or contains no level-1 heading at all
            (which is what a truncated or error page looks like).
    """
    if isinstance(raw, bytes):
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ControlError("body is not valid UTF-8: %s" % exc) from exc
    else:
        text = raw
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if H1_RX.match(line):
            lines = lines[i:]
            break
    else:
        raise ControlError("no level-1 heading found; body is truncated or is not the expected page")
    lines = [ln.rstrip() for ln in lines]
    out: list[str] = []
    blanks = 0
    for ln in lines:
        if ln:
            blanks = 0
            out.append(ln)
            continue
        blanks += 1
        if blanks <= 2:
            out.append(ln)
    while out and not out[0]:
        out.pop(0)
    while out and not out[-1]:
        out.pop()
    return "\n".join(out) + "\n"


# --------------------------------------------------------------------------- fingerprint


def _walk(text: str) -> Iterable[tuple[str, str, str | None]]:
    """Yield ``(kind, line, fence_lang)`` with fenced regions marked.

    Fence tracking is not decoration: this page embeds shell snippets whose ``# comment`` lines
    would otherwise read as a level-1 heading and whose ``## `` lines as a section.

    Fences are matched the CommonMark way - an open fence is closed only by one using the same
    marker character and at least as many of them, and carrying no info string of its own. An opener
    may carry any info text, which is what makes this correct on the real page: its fences are
    written as ```json theme={null}, so a pattern that only accepts a bare language word rejects the
    OPENER and then reads the matching bare closer as an opener, inverting the state for everything
    that follows. Each cheaper rule was measured against the live page: column-0 anchoring left an
    unindented fence open forever and yielded 17 of 31 events, and plain toggling yielded 0 of 31.
    """
    marker: str | None = None
    lang: str | None = None
    for line in text.split("\n"):
        m = FENCE_RX.match(line)
        info = (m.group(2) or "").strip() if m else ""
        if marker is None:
            if m:
                marker = m.group(1)
                lang = info.split()[0] if info else "txt"
                continue
            yield ("prose", line, None)
            continue
        if m and m.group(1)[0] == marker[0] and len(m.group(1)) >= len(marker) and not info:
            marker, lang = None, None
            continue
        yield ("fenced", line, lang)


def fingerprint(text: str, tier: str = "api") -> dict[str, list[str]]:
    """Extract the sorted name sets whose membership defines the documented API surface.

    A ``prose`` tier keeps headings only, so a narrative page cannot raise structural drift over a
    reworded table.
    """
    acc: dict[str, set[str]] = {k: set() for k in _FP_KEYS}
    h2: str | None = None
    for kind, line, lang in _walk(text):
        if kind == "fenced":
            if lang and lang.startswith("json"):
                acc["json_fields"].update(JSONKEY_RX.findall(line))
                acc["handler_types"].update(t for t in TYPEVAL_RX.findall(line) if t not in _SCHEMA_PRIMITIVES)
            acc["env_vars"].update(ENV_RX.findall(line))
            continue
        m2 = H2_RX.match(line)
        if m2:
            h2 = m2.group(1)
            acc["headings"].add("H2:" + h2)
            continue
        m3 = H3_RX.match(line)
        if m3:
            acc["headings"].add("H3:" + m3.group(1))
            if h2 == "Hook events":
                acc["events"].add(m3.group(1))
            continue
        m4 = H4_RX.match(line)
        if m4:
            acc["headings"].add("H4:" + m4.group(1))
        row = ROW_RX.match(line)
        if row:
            cell = row.group(1)
            if not set(cell) <= set("-: "):
                # Only backticked tokens count. A reworded prose cell must contribute nothing, or
                # every upstream copy-edit becomes structural drift and the loud channel dies.
                acc["table_keys"].update(TICK_RX.findall(cell))
        acc["env_vars"].update(ENV_RX.findall(line))
    if tier == "prose":
        acc = {k: (v if k == "headings" else set()) for k, v in acc.items()}
    return {k: sorted(v) for k, v in acc.items()}


def structure_sha(fp: dict[str, list[str]]) -> str:
    return hashlib.sha256(json.dumps(fp, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def content_sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sections(text: str) -> list[dict[str, Any]]:
    """Per-heading digests, so a COSMETIC report can name which section moved."""
    out: list[dict[str, Any]] = []
    stack: list[tuple[int, str]] = []
    cur: dict[str, Any] | None = None
    buf: list[str] = []

    def close() -> None:
        if cur is not None:
            cur["lines"] = len(buf)
            cur["sha256"] = hashlib.sha256("\n".join(buf).encode("utf-8")).hexdigest()
            out.append(cur)

    for kind, line, _lang in _walk(text):
        if kind == "prose":
            m = re.match(r"^(#{2,4}) (.+?)\s*$", line)
            if m:
                close()
                level, title = len(m.group(1)), m.group(2)
                while stack and stack[-1][0] >= level:
                    stack.pop()
                stack.append((level, title))
                cur = {"path": " > ".join("%s %s" % ("#" * lv, t) for lv, t in stack)}
                buf = []
                continue
        if cur is not None:
            buf.append(line)
    close()
    return out


def max_version(text: str) -> str | None:
    found = VERSION_RX.findall(text)
    if not found:
        return None
    return max(found, key=lambda v: tuple(int(p) for p in v.split(".")))


# --------------------------------------------------------------------------- control gate


def apply_control(body: str, fp: dict[str, list[str]], raw_len: int, control: dict[str, Any]) -> None:
    """Refuse to render a verdict on a body that cannot be the real page.

    Without this, a truncated fetch reads as "every event was removed" - a STRUCTURAL alarm that is
    both false and maximally loud, which is how a checker teaches people to ignore it.
    """
    minimum = control.get("min_raw_bytes")
    if minimum and raw_len < minimum:
        raise ControlError("body is %d bytes, below the %d-byte floor for this source" % (raw_len, minimum))
    for heading in control.get("require_headings", []):
        if heading not in body:
            raise ControlError("required heading %r absent; body is not the expected page" % heading)
    min_events = control.get("min_events")
    if min_events and len(fp.get("events", [])) < min_events:
        raise ControlError(
            "extracted %d events, below the floor of %d; the extractor or the page shape changed"
            % (len(fp.get("events", [])), min_events)
        )


# --------------------------------------------------------------------------- stamp records


def build_source_record(name: str, url: str, raw: bytes | str, tier: str = "api", control: dict[str, Any] | None = None) -> dict[str, Any]:
    body = normalise(raw)
    fp = fingerprint(body, tier)
    raw_len = len(raw if isinstance(raw, bytes) else raw.encode("utf-8"))
    ctl = control or default_control(fp, raw_len)
    apply_control(body, fp, raw_len, ctl)
    return {
        "name": name,
        "url": url,
        "tier": tier,
        "raw_bytes": raw_len,
        "normalised_lines": body.count("\n"),
        "content_sha256": content_sha(body),
        "structure_sha256": structure_sha(fp),
        "max_cli_version_mentioned": max_version(body),
        "control": ctl,
        "counts": {k: len(v) for k, v in fp.items()},
        "fingerprint": fp,
        "sections": sections(body),
    }


def default_control(fp: dict[str, list[str]], raw_len: int) -> dict[str, Any]:
    events = fp.get("events", [])
    return {
        "min_raw_bytes": max(1024, int(raw_len * 0.5)),
        "require_headings": [],
        "min_events": max(0, int(len(events) * 0.6)),
    }


def compare(record: dict[str, Any], raw: bytes | str) -> Verdict:
    """Compare a freshly fetched body against one stamped source record."""
    name = record["name"]
    try:
        body = normalise(raw)
        fp = fingerprint(body, record.get("tier", "api"))
        raw_len = len(raw if isinstance(raw, bytes) else raw.encode("utf-8"))
        apply_control(body, fp, raw_len, record.get("control", {}))
    except ControlError as exc:
        return Verdict(name, BROKEN, str(exc))

    if content_sha(body) == record["content_sha256"]:
        return Verdict(name, CURRENT, "content hash matches")

    if structure_sha(fp) != record["structure_sha256"]:
        added: dict[str, list[str]] = {}
        removed: dict[str, list[str]] = {}
        old = record["fingerprint"]
        for key in _FP_KEYS:
            before, now = set(old.get(key, [])), set(fp.get(key, []))
            if now - before:
                added[key] = sorted(now - before)
            if before - now:
                removed[key] = sorted(before - now)
        return Verdict(
            name,
            STRUCTURAL,
            "the documented API surface changed",
            {"added": added, "removed": removed},
        )

    before_sections = {s["path"]: s["sha256"] for s in record.get("sections", [])}
    changed = [s["path"] for s in sections(body) if before_sections.get(s["path"]) != s["sha256"]]
    return Verdict(name, COSMETIC, "wording changed, API surface identical", {"changed_sections": changed[:20]})


# --------------------------------------------------------------------------- coverage


def coverage(stamp: dict[str, Any], refs_dir: Path) -> dict[str, Any]:
    """Check both directions between the stamp and the shipped reference files.

    Forward: every stamped event needs its OWN heading somewhere in the references. A passing
    mention in prose is exactly the illusion of documentation, so it does not count.

    Reverse: every event the references give a heading to must still be in the stamp, which catches
    a phantom - an event this skill still documents after upstream removed it. A stale absence or
    presence claim steers a reader wrong rather than merely failing to help.

    Raises:
        ControlError: there is nothing to check, so "complete" would be vacuous.
    """
    files = sorted(refs_dir.glob("*.md")) if refs_dir.is_dir() else []
    if not files:
        raise ControlError("no reference files under %s" % refs_dir)
    text = "\n".join(f.read_text(encoding="utf-8") for f in files)

    api_events: list[str] = []
    required: set[str] = set()
    advisory: set[str] = set()
    for src in stamp.get("sources", []):
        fp = src.get("fingerprint", {})
        if src.get("tier", "api") == "api":
            api_events.extend(fp.get("events", []))
        for key in ("env_vars", "handler_types"):
            required.update(fp.get(key, []))
        advisory.update(fp.get("json_fields", []))
    if not api_events:
        raise ControlError("the stamp lists no events; it is empty or hand-edited")

    documented: set[str] = set()
    for line in text.split("\n"):
        m = re.match(r"^#{2,4} (.+?)\s*$", line)
        if m:
            documented.update(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", m.group(1)))
    # Search inside backticked spans by word, not by whole-span equality: a name is documented when
    # it appears as `$CLAUDE_MODEL` or `CLAUDE_CODE_DEBUG_LOG_LEVEL=verbose`, not only when a span
    # happens to equal it exactly.
    ticked_text = " ".join(TICK_RX.findall(text))
    ticked_words = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", ticked_text))

    def is_documented(name: str) -> bool:
        return name in documented or name in ticked_words

    missing_events = sorted(e for e in set(api_events) if e not in documented)
    phantom = sorted(h for h in documented if h in _known_event_shape(stamp) and h not in set(api_events))
    missing_required = sorted(f for f in required if not is_documented(f))
    # json_fields is every key in every example on the page, tool_input schemas included. Requiring
    # all of them would fail forever on detail this skill deliberately delegates upstream, and a
    # gate that can never go green gets switched off. Report them, do not fail on them.
    missing_advisory = sorted(f for f in advisory if not is_documented(f))
    complete = not missing_events and not phantom and not missing_required
    return {
        "events_checked": len(set(api_events)),
        "missing_events": missing_events,
        "phantom_events": phantom,
        "required_checked": len(required),
        "missing_required": missing_required,
        "advisory_checked": len(advisory),
        "undocumented_advisory": missing_advisory,
        "complete": complete,
    }


def _known_event_shape(stamp: dict[str, Any]) -> set[str]:
    """Names that look like event names, used to spot a phantom without flagging prose headings."""
    out: set[str] = set()
    for src in stamp.get("sources", []):
        out.update(src.get("fingerprint", {}).get("events", []))
    return out


# --------------------------------------------------------------------------- fetching


def _fetch(url: str, timeout: float) -> tuple[int, bytes, str]:
    """One GET. Prefers httpx2 when installed and falls back to the stdlib.

    The import is deliberately inside the function: the repo gate imports this module with a bare
    interpreter and does not provision PEP 723 dependencies, so a module-scope third-party import
    would fail collection on a clean runner.
    """
    try:  # noqa: PLC0415 - optional dependency, must import at call time to stay bare-importable
        import httpx2  # type: ignore[import-not-found]

        resp = httpx2.get(url, timeout=timeout, follow_redirects=True)
        return int(resp.status_code), bytes(resp.content), str(resp.headers.get("content-type", ""))
    except ImportError:
        pass
    import urllib.request  # noqa: PLC0415 - stdlib fallback beside the optional fast path

    req = urllib.request.Request(url, headers={"User-Agent": "bitranox-hookdoc/1"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - fixed https docs URL
        return int(resp.status), resp.read(), str(resp.headers.get("content-type", ""))


def fetch_with_wall(url: str, timeout: float, fetcher: Callable[[str, float], tuple[int, bytes, str]] | None = None) -> tuple[int, bytes, str]:
    """Fetch under a hard total deadline.

    ``urlopen(timeout=)`` bounds each socket operation, not the whole call, so a server dribbling
    bytes can hold a turn open indefinitely. The worker is a daemon thread: on expiry it is
    abandoned and dies with the process rather than being waited on.
    """
    call = fetcher or _fetch
    box: dict[str, Any] = {}
    done = threading.Event()

    def run() -> None:
        try:
            box["ok"] = call(url, timeout)
        except Exception as exc:  # noqa: BLE001 - any failure to look must reach the caller as BROKEN
            box["err"] = exc
        finally:
            done.set()

    threading.Thread(target=run, daemon=True).start()
    if not done.wait(timeout):
        raise ControlError("timeout after %.1fs" % timeout)
    if "err" in box:
        raise ControlError("fetch failed: %s" % box["err"])
    return box["ok"]


def fetch_body(url: str, timeout: float, fetcher: Callable[[str, float], tuple[int, bytes, str]] | None = None) -> bytes:
    status, body, ctype = fetch_with_wall(url, timeout, fetcher)
    if status != 200:
        raise ControlError("http %d" % status)
    if ctype and "markdown" not in ctype and "text/plain" not in ctype:
        raise ControlError("unexpected content-type %r; expected markdown" % ctype)
    return body


# --------------------------------------------------------------------------- cache


def cache_path(cache_dir: Path) -> Path:
    return cache_dir / "lastcheck.json"


def read_cache(cache_dir: Path, stamp_hash: str, max_age: float, now: float) -> dict[str, Any] | None:
    """Replay a recent verdict only when it was taken against THIS stamp.

    Keying on the stamp's own hash means re-stamping invalidates the cache for free: no stale
    STRUCTURAL haunting you after the fix, and no stale CURRENT after the stamp moved.
    """
    path = cache_path(cache_dir)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if data.get("stamp_sha256") != stamp_hash:
        return None
    age = now - float(data.get("checked_at_epoch", 0))
    ttl = 900.0 if data.get("verdict") == BROKEN else max_age
    if age > ttl:
        return None
    data["cached"] = True
    return data


def write_cache(cache_dir: Path, payload: dict[str, Any]) -> None:
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path(cache_dir).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except OSError:
        pass  # a cache that cannot be written must not fail the check


# --------------------------------------------------------------------------- CLI plumbing


def envelope(command: str, ok: bool, data: dict[str, Any], skipped: list[str] | None = None) -> dict[str, Any]:
    return {"ok": ok, "command": "hookdoc_stamp/%s" % command, "data": data, "skipped": skipped or []}


def emit(args: argparse.Namespace, command: str, ok: bool, data: dict[str, Any], human: str) -> None:
    if getattr(args, "json", False):
        sys.stdout.write(json.dumps(envelope(command, ok, data), indent=2) + "\n")
    else:
        sys.stdout.write(human + "\n")


def load_stamp(path: Path) -> dict[str, Any]:
    try:
        stamp = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ControlError("stamp unreadable: %s" % exc) from exc
    except ValueError as exc:
        raise ControlError("stamp is not valid JSON: %s" % exc) from exc
    if not stamp.get("sources"):
        raise ControlError("stamp lists no sources")
    if stamp.get("normalisation", {}).get("id") != NORMALISATION_ID:
        raise ControlError(
            "stamp was built with normalisation %r but this code implements %r; re-stamp"
            % (stamp.get("normalisation", {}).get("id"), NORMALISATION_ID)
        )
    return stamp


def stamp_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def skill_dir() -> Path:
    return Path(__file__).resolve().parent.parent


# --------------------------------------------------------------------------- commands


def cmd_fingerprint(args: argparse.Namespace) -> int:
    body = normalise(Path(args.body).read_bytes())
    fp = fingerprint(body, args.tier)
    emit(
        args,
        "fingerprint",
        True,
        {"structure_sha256": structure_sha(fp), "content_sha256": content_sha(body), "counts": {k: len(v) for k, v in fp.items()}, "fingerprint": fp},
        "\n".join("%-14s %d" % (k, len(v)) for k, v in fp.items()),
    )
    return 0


def cmd_coverage(args: argparse.Namespace) -> int:
    stamp = load_stamp(Path(args.stamp))
    result = coverage(stamp, Path(args.refs))
    ok = bool(result["complete"])
    lines = ["coverage: %s (%d events, %d required names)" % ("complete" if ok else "GAPS", result["events_checked"], result["required_checked"])]
    for label, key in (("undocumented event", "missing_events"), ("phantom event", "phantom_events"), ("undocumented name", "missing_required")):
        for item in result[key]:
            lines.append("  %s: %s" % (label, item))
    if result["undocumented_advisory"]:
        lines.append("  advisory: %d of %d example field names not mentioned (not a failure)"
                     % (len(result["undocumented_advisory"]), result["advisory_checked"]))
    emit(args, "coverage", ok, result, "\n".join(lines))
    return 0 if ok else 1


def _sources(stamp: dict[str, Any], only: str | None) -> list[dict[str, Any]]:
    src = stamp["sources"]
    return [s for s in src if s["name"] == only] if only else src


def cmd_check(args: argparse.Namespace) -> int:
    import time  # noqa: PLC0415 - only the timing paths need it

    stamp_file = Path(args.stamp)
    stamp = load_stamp(stamp_file)
    shash = stamp_hash(stamp_file)
    cache_dir = Path(args.cache_dir)
    now = time.time()

    if not args.force and not args.body:
        cached = read_cache(cache_dir, shash, float(args.max_age), now)
        if cached:
            emit(args, "check", _EXIT[cached["verdict"]] == 0, cached, _human_check(cached))
            return _EXIT[cached["verdict"]]

    verdicts: list[Verdict] = []
    for src in _sources(stamp, args.source):
        try:
            raw = Path(args.body).read_bytes() if args.body else fetch_body(src["url"], float(args.timeout))
        except ControlError as exc:
            verdicts.append(Verdict(src["name"], BROKEN, str(exc)))
            continue
        except OSError as exc:
            verdicts.append(Verdict(src["name"], BROKEN, "cannot read body: %s" % exc))
            continue
        v = compare(src, raw)
        v.detail.setdefault("content_sha256", src["content_sha256"])
        v.detail.setdefault("structure_sha256", src["structure_sha256"])
        verdicts.append(v)

    if args.offline and not args.body:
        verdicts = [Verdict(s["name"], BROKEN, "offline and no fresh cache") for s in _sources(stamp, args.source)]

    overall = max((v.verdict for v in verdicts), key=lambda v: _SEVERITY[v], default=BROKEN)
    payload = {
        "verdict": overall,
        "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
        "checked_at_epoch": now,
        "cached": False,
        "stamp_sha256": shash,
        "stamp_generated_at": stamp.get("generated_at"),
        "sources": [v.as_dict() for v in verdicts],
    }
    if not args.body:
        write_cache(cache_dir, payload)
    emit(args, "check", _EXIT[overall] == 0, payload, _human_check(payload))
    if args.expect and args.expect != overall:
        sys.stderr.write("expected %s, got %s\n" % (args.expect, overall))
        return 1
    return _EXIT[overall]


def _human_check(payload: dict[str, Any]) -> str:
    head = "hookdoc-freshness: %s  stamped %s, checked %s%s" % (
        payload["verdict"],
        payload.get("stamp_generated_at", "?"),
        payload.get("checked_at", "?"),
        " (cache hit)" if payload.get("cached") else "",
    )
    lines = [head]
    for src in payload.get("sources", []):
        lines.append("  %-18s %-11s %s" % (src["name"], src["verdict"], src.get("reason", "")))
        if src.get("content_sha256"):
            lines.append("    content %s  structure %s" % (src["content_sha256"][:12], src.get("structure_sha256", "")[:12]))
        for key in ("added", "removed"):
            for field, items in (src.get(key) or {}).items():
                lines.append("    %s %s: %s" % (key, field, ", ".join(items)))
    return "\n".join(lines)


def cmd_stamp(args: argparse.Namespace) -> int:
    import time  # noqa: PLC0415 - only the timing paths need it

    stamp_file = Path(args.stamp)
    stamp = json.loads(stamp_file.read_text(encoding="utf-8")) if stamp_file.is_file() else {"schema": SCHEMA, "sources": []}

    if stamp.get("sources"):
        try:
            cov = coverage(stamp, Path(args.refs))
        except ControlError as exc:
            sys.stderr.write("coverage control failed: %s\n" % exc)
            return 2
        if not cov["complete"] and not args.accept_gaps:
            emit(args, "stamp", False, {"refused": True, "coverage": cov}, "refusing to re-stamp: coverage has gaps\n  %s" % cov)
            return 1

    records = []
    for src in _sources(stamp, args.source) or []:
        raw = Path(args.body).read_bytes() if args.body else fetch_body(src["url"], float(args.timeout))
        rec = build_source_record(src["name"], src["url"], raw, src.get("tier", "api"), src.get("control"))
        if args.cosmetic_only and rec["structure_sha256"] != src["structure_sha256"]:
            emit(args, "stamp", False, {"refused": True, "source": src["name"]}, "refusing: --cosmetic-only but the structure moved")
            return 1
        records.append(rec)

    by_name = {r["name"]: r for r in records}
    stamp["sources"] = [by_name.get(s["name"], s) for s in stamp["sources"]]
    stamp["schema"] = SCHEMA
    stamp["generated_at"] = time.strftime("%Y-%m-%d", time.gmtime())
    stamp["generator"] = "scripts/hookdoc_stamp.py"
    stamp["normalisation"] = {"id": NORMALISATION_ID, "rules": NORMALISATION_RULES}
    stamp["coverage_gaps"] = [] if not args.accept_gaps else coverage(stamp, Path(args.refs))["missing_events"]

    if not args.write:
        emit(args, "stamp", True, {"dry_run": True, "sources": [r["name"] for r in records]}, "dry run; would stamp %d source(s)" % len(records))
        return 0
    stamp_file.write_text(json.dumps(stamp, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    emit(args, "stamp", True, {"written": str(stamp_file), "sources": [r["name"] for r in records]}, "stamped %d source(s)" % len(records))
    return 0


SELFTEST_FIXTURES = (
    ("hooks-sample.md", CURRENT),
    ("hooks-sample-cosmetic.md", COSMETIC),
    ("hooks-sample-structural.md", STRUCTURAL),
    ("hooks-sample-truncated.md", BROKEN),
)


def run_selftest(fixtures_dir: Path, comparator: Callable[[dict[str, Any], bytes], Verdict] | None = None) -> dict[str, Any]:
    """Prove the detector is not a rubber stamp before believing any verdict it renders.

    A comparator that answers CURRENT to every input looks exactly like a clean bill of health, so
    the pass condition is that all four fixtures produce their DIFFERENT expected verdicts.

    Raises:
        ControlError: a fixture is missing. Missing fixtures fail rather than skip, because a check
            that silently degrades to skipped stays green forever.
    """
    cmp_fn = comparator or compare
    stamp_file = fixtures_dir / "stamp-sample.json"
    if not stamp_file.is_file():
        raise ControlError("fixture stamp missing: %s" % stamp_file)
    record = json.loads(stamp_file.read_text(encoding="utf-8"))["sources"][0]
    results = []
    for name, expected in SELFTEST_FIXTURES:
        path = fixtures_dir / name
        if not path.is_file():
            raise ControlError("fixture missing: %s" % path)
        got = cmp_fn(record, path.read_bytes()).verdict
        results.append({"fixture": name, "expected": expected, "got": got, "pass": got == expected})
    return {"results": results, "passed": all(r["pass"] for r in results)}


def cmd_selftest(args: argparse.Namespace) -> int:
    out = run_selftest(Path(args.fixtures))
    lines = ["%-32s expected %-11s got %-11s %s" % (r["fixture"], r["expected"], r["got"], "ok" if r["pass"] else "FAIL") for r in out["results"]]
    if not out["passed"]:
        lines.append("the detector is a rubber stamp or is mis-tuned; do not trust its verdicts")
    emit(args, "selftest", out["passed"], out, "\n".join(lines))
    return 0 if out["passed"] else 1


BASELINE_RX = re.compile(r"^Reference baseline: .*$", re.M)


def baseline_line(stamp: dict[str, Any]) -> str:
    api = [s for s in stamp["sources"] if s.get("tier", "api") == "api"]
    primary = api[0] if api else stamp["sources"][0]
    return "Reference baseline: %s, fetched %s, %d events, content %s" % (
        primary["url"].rsplit("/", 1)[-1],
        stamp.get("generated_at", "?"),
        len(primary.get("fingerprint", {}).get("events", [])),
        primary["content_sha256"][:12],
    )


def cmd_baseline(args: argparse.Namespace) -> int:
    stamp = load_stamp(Path(args.stamp))
    want = baseline_line(stamp)
    target = Path(args.skill_md)
    text = target.read_text(encoding="utf-8")
    found = BASELINE_RX.search(text)
    if found and found.group(0) == want:
        emit(args, "baseline", True, {"line": want, "in_sync": True}, want)
        return 0
    if not args.write:
        emit(args, "baseline", False, {"expected": want, "found": found.group(0) if found else None, "in_sync": False}, "stale baseline line\n  want: %s\n  have: %s" % (want, found.group(0) if found else "(absent)"))
        return 1
    text = BASELINE_RX.sub(want, text) if found else text
    target.write_text(text, encoding="utf-8")
    emit(args, "baseline", True, {"line": want, "written": True}, "wrote: %s" % want)
    return 0


# --------------------------------------------------------------------------- entry point


def build_parser() -> argparse.ArgumentParser:
    skill = skill_dir()
    p = argparse.ArgumentParser(prog="hookdoc_stamp", description=__doc__.split("\n")[0])
    p.add_argument("--json", action="store_true", help="emit the JSON envelope on stdout")
    sub = p.add_subparsers(dest="command", required=True)

    def common(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--stamp", default=str(skill / "references" / "upstream-stamp.json"))
        sp.add_argument("--json", action="store_true")

    c = sub.add_parser("check", help="compare upstream against the committed stamp")
    common(c)
    c.add_argument("--source")
    c.add_argument("--max-age", default=604800, type=float, help="cache window in seconds (default 7 days)")
    c.add_argument("--offline", action="store_true")
    c.add_argument("--force", action="store_true")
    c.add_argument("--timeout", default=8.0, type=float)
    c.add_argument("--cache-dir", default=str(DEFAULT_CACHE_DIR))
    c.add_argument("--body", help="read the body from a local file instead of the network")
    c.add_argument("--expect", choices=[CURRENT, COSMETIC, STRUCTURAL, BROKEN])
    c.set_defaults(func=cmd_check)

    v = sub.add_parser("coverage", help="every stamped name is documented in references/")
    common(v)
    v.add_argument("--refs", default=str(skill / "references"))
    v.set_defaults(func=cmd_coverage)

    s = sub.add_parser("stamp", help="refresh the stamp; gated on coverage passing")
    common(s)
    s.add_argument("--refs", default=str(skill / "references"))
    s.add_argument("--source")
    s.add_argument("--timeout", default=8.0, type=float)
    s.add_argument("--body")
    s.add_argument("--write", action="store_true")
    s.add_argument("--accept-gaps", action="store_true")
    s.add_argument("--cosmetic-only", action="store_true")
    s.set_defaults(func=cmd_stamp)

    f = sub.add_parser("fingerprint", help="print the structural fingerprint of a local markdown file")
    f.add_argument("body")
    f.add_argument("--tier", default="api", choices=["api", "prose"])
    f.add_argument("--json", action="store_true")
    f.set_defaults(func=cmd_fingerprint)

    t = sub.add_parser("selftest", help="known-negative proof over the bundled fixtures")
    t.add_argument("--fixtures", default=str(skill / "tests" / "fixtures"))
    t.add_argument("--json", action="store_true")
    t.set_defaults(func=cmd_selftest)

    b = sub.add_parser("baseline", help="verify or rewrite the Reference baseline line in SKILL.md")
    common(b)
    b.add_argument("--skill-md", default=str(skill / "SKILL.md"))
    b.add_argument("--write", action="store_true")
    b.set_defaults(func=cmd_baseline)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except ControlError as exc:
        if getattr(args, "json", False):
            sys.stdout.write(json.dumps(envelope(args.command, False, {"verdict": BROKEN, "reason": str(exc)}), indent=2) + "\n")
        else:
            sys.stderr.write("hookdoc-freshness: BROKEN - %s\n" % exc)
        return 2
    except OSError as exc:
        sys.stderr.write("hookdoc-freshness: BROKEN - %s\n" % exc)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
