# /// script
# requires-python = ">=3.10"
# dependencies = ["orjson"]
# ///
"""Filter a JSONL stream (a Claude Code transcript or any JSONL) by top-level type / message.role,
extract a dotted field, or regex over the raw line - the general form of transcript_tail's parsing.
With `--count` it does the same over a whole CORPUS of files and tallies the values.

Why: reading a JSONL by hand (`for line in open(...): json.loads(line)`) and picking fields is a
recurring chore in probe/self-mining work; an ad-hoc parser gets the varied content shapes wrong.

Why the corpus mode: "what values does this field actually take across every transcript?" is the
DIRECT instrument for questions that otherwise get answered by inference, and answering it meant
hand-rolling a walk over ~1500 files every time. Reaching for the indirect answer instead has cost
real work - one session built three designs for a value the corpus could have named in one command.

A NEGATIVE is the dangerous result here, because "the field holds nothing" and "I never really
looked" print the same. So the scan reports how many files it READ (on stderr, never in the parsed
stream) and exits 3 when it read none, which turns a mistyped path from a silent all-clear into a
loud one. Unreadable files and directories are listed as skipped rather than dropped, a named path
that does not exist fails the run even beside a good one, and unparseable lines are counted in
every mode.

A value is printed as itself when it is a plain string, and as JSON otherwise. A string that would
itself READ as JSON (`"1"`, `"true"`, `"null"`) is printed quoted, so the string "1" and the
number 1 never share a row, and a JSON `null` is a value (`null`), never mistaken for a missing key.

Run:
  `uv run scripts/jsonl_grep.py <file> [--type assistant] [--role user] [--field message.model]
                                     [--pattern REGEX]`
  `uv run scripts/jsonl_grep.py ~/.claude/projects --field message.model --count`
  `... | uv run scripts/jsonl_grep.py --field message.model [--count]`     (stdin)

NaN and Infinity are not JSON: a line holding one is unparseable on either backend (orjson or the
stdlib fallback), as is a line nested too deep to decode. A named path is read whatever kind of
file it is, so a process substitution (`jsonl_grep <(cmd)`) works.

Exit codes: 0 read something, 2 usage error or a named path that does not exist beside others that
were read, 3 nothing was read (every named path missing or unreadable, or no *.jsonl found).
"""
from __future__ import annotations

import argparse
import fnmatch
import os
import re
import sys
from collections import Counter
from pathlib import Path

try:                                                     # fast path when available (uv run installs it)
    import orjson

    def _loads(raw):
        return orjson.loads(raw)

    _JSONDecodeError = orjson.JSONDecodeError

    def _dumps(obj):
        """orjson's serialiser stops far shallower than its reader ("Recursion limit reached", a
        TypeError), so a value it read is written by the stdlib in orjson's compact form."""
        try:
            return orjson.dumps(obj).decode()
        except TypeError:
            import json  # noqa: PLC0415 - only a value nested past orjson's writer needs it
            return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
except ModuleNotFoundError:                              # stdlib fallback so the script runs anywhere
    import json as _json

    _JSONDecodeError = _json.JSONDecodeError

    def _reject_constant(name):
        raise _JSONDecodeError(f"{name} is not JSON", name, 0)

    _MAX_DEPTH = 1024                                    # orjson reads 1024 levels and refuses 1025

    def _deeper_than(obj, limit: int) -> bool:
        """Whether `obj` nests containers more than `limit` levels, walked without recursion."""
        stack = [(obj, 1)]
        while stack:
            node, depth = stack.pop()
            if not isinstance(node, (dict, list)):
                continue
            if depth > limit:
                return True
            children = node.values() if isinstance(node, dict) else node
            stack.extend((child, depth + 1) for child in children)
        return False

    def _loads(raw):
        """Read strictly as orjson does, so the backend never decides what a line holds: NaN and
        Infinity are refused, and nesting past orjson's 1024 levels is an unparseable line. The
        depth has to be checked, not left to the stack: CPython 3.14 reads 100,000 levels without
        a RecursionError and then fails serialising them, while older builds fail reading."""
        try:
            value = _json.loads(raw, parse_constant=_reject_constant)
        except RecursionError:
            raise _JSONDecodeError("nesting too deep", raw[:40], 0) from None
        opens = raw.count("[" if isinstance(raw, str) else b"[") + raw.count(
            "{" if isinstance(raw, str) else b"{")
        if opens > _MAX_DEPTH and _deeper_than(value, _MAX_DEPTH):  # the count skips every ordinary line
            raise _JSONDecodeError("nesting too deep", raw[:40], 0)
        return value

    def _dumps(obj):
        return _json.dumps(obj, ensure_ascii=False)


_MISS = object()                                         # a line that matched nothing, distinct from a falsy value
_BAD = object()                                          # a line no parse could use - counted, never silently dropped


def _get(obj, dotted: str):
    """The value at `dotted`, or `_MISS` when a key is absent - never None, which is JSON null.

    Returning None for both made a field that is `null` on every record read as a field no record
    has: the tally came back empty over real data and looked like a confident "no values".
    """
    cur = obj
    for key in dotted.split("."):
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
        else:
            return _MISS
    return cur


def render(value) -> str:
    """One value as printed and tallied: a plain string bare, anything else as JSON.

    A string that would itself parse as JSON is quoted, so `"1"` and `1` (or `"true"` and `true`)
    never land on one row - bare strings alone made them indistinguishable in the output and
    merged them in the tally.
    """
    if not isinstance(value, str):
        return _dumps(value)
    try:
        _loads(value)
    except (ValueError, RecursionError):
        return value
    return _dumps(value)


def _records(text: str):
    """JSONL records split on newline ONLY: U+2028, form feed and the other separators
    `str.splitlines` honours are legal raw inside a JSON string and must not cut a record."""
    return text.split("\n")


def _match(raw, *, rx=None, type_=None, role=None, field=None):
    """The record for one raw line - or the extracted field value - else `_MISS`."""
    raw = raw.strip()
    if not raw:
        return _MISS
    if rx and not rx.search(raw):
        return _MISS
    try:
        obj = _loads(raw)
    except _JSONDecodeError:
        return _BAD
    if not isinstance(obj, dict):                        # a bare array parses, then obj.get would raise
        return _BAD
    if type_ is not None and obj.get("type") != type_:
        return _MISS
    if role is not None and _get(obj, "message.role") != role:
        return _MISS
    if not field:
        return obj
    return _get(obj, field)


def filter_records(text: str, *, type_=None, role=None, field=None, pattern=None):
    """Return matching records (list of dicts), or - when `field` is set - the extracted values.

    `pattern` is a regex tested against the RAW line (fast pre-filter); `type_` matches the
    top-level `type`; `role` matches `message.role`. Malformed lines are skipped.
    """
    rx = re.compile(pattern) if pattern else None
    hits = (_match(raw, rx=rx, type_=type_, role=role, field=field) for raw in _records(text))
    return [hit for hit in hits if hit is not _MISS and hit is not _BAD]


class ScanResult:
    """What a corpus scan found AND what it read, so an empty tally cannot pass for an answer.

    `files_skipped` holds files and directories that exist but could not be read; `missing` holds
    named paths that do not exist at all, which fail the run even when something else was read.
    """

    def __init__(self, counts, files_read: int, files_skipped, lines_skipped: int = 0,
                 missing=None):
        self.counts = counts
        self.files_read = files_read
        self.files_skipped = files_skipped
        self.lines_skipped = lines_skipped
        self.missing = list(missing or [])


def _walk_jsonl(path: Path, skipped: list):
    """The *.jsonl below `path`, sorted; a directory it cannot list goes to `skipped`.

    `rglob` passes over an unreadable directory without a word, so the corpus shrank while the
    report said "0 skipped". `os.walk` with `onerror` names every one.
    """
    found = []
    for dirpath, _dirs, names in os.walk(path, onerror=lambda exc: skipped.append(str(exc.filename))):
        found.extend(Path(dirpath) / n for n in names if fnmatch.fnmatch(n, "*.jsonl"))
    return sorted(found)


def collect_paths(paths):
    """`(files, missing, unreadable_dirs)` for `paths`: a directory contributes its *.jsonl.

    A path that does not exist is returned in `missing` rather than dropped: beside a good path it
    used to vanish, so a typo cost its whole share of the corpus while the run exited 0. Any other
    existing path is read as a file, not only a regular one: `jsonl_grep <(cmd)` names a pipe
    (/dev/fd/63), which is neither a file nor a directory to `Path`.
    """
    found, missing, unreadable = [], [], []
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            found.extend(_walk_jsonl(path, unreadable))
        elif path.exists():
            found.append(path)
        else:
            missing.append(str(path))
    return found, missing, unreadable


def expand_paths(paths):
    """Every file named by `paths`: a directory contributes the *.jsonl below it, sorted."""
    return collect_paths(paths)[0]


def iter_file_matches(path, *, rx=None, type_=None, role=None, field=None):
    """Stream one file line by line, yielding matches - and `_BAD` for a line nothing could read.

    A live session's last line can be a partial write, so an unusable line is a normal event; the
    caller counts them rather than dropping them, because a silently shrinking denominator is how a
    scan reports less than it should while looking complete. `utf-8-sig`, because a BOM would
    otherwise make the first record unparseable.
    """
    with open(path, encoding="utf-8-sig", errors="replace", newline="\n") as handle:
        for raw in handle:
            hit = _match(raw, rx=rx, type_=type_, role=role, field=field)
            if hit is not _MISS:
                yield hit


def _tally(hits, counts: Counter) -> int:
    """Add each hit to `counts`; return how many were unparseable."""
    bad = 0
    for hit in hits:
        if hit is _BAD:
            bad += 1
        else:
            counts[render(hit)] += 1
    return bad


def scan_corpus(paths, *, field=None, type_=None, role=None, pattern=None) -> ScanResult:
    """Tally `field`'s values across every file under `paths`, reporting what was read."""
    rx = re.compile(pattern) if pattern else None
    counts: Counter = Counter()
    files, missing, skipped = collect_paths(paths)
    read, bad_lines = 0, 0
    for path in files:
        try:
            bad_lines += _tally(iter_file_matches(path, rx=rx, type_=type_, role=role, field=field),
                                counts)
        except OSError:
            skipped.append(str(path))
            continue
        read += 1
    return ScanResult(counts, read, skipped, bad_lines, missing)


def scan_text(text: str, *, field=None, type_=None, role=None, pattern=None) -> ScanResult:
    """`scan_corpus` over one already-read text (stdin), counted as one source read."""
    rx = re.compile(pattern) if pattern else None
    counts: Counter = Counter()
    hits = (_match(raw, rx=rx, type_=type_, role=role, field=field) for raw in _records(text))
    bad = _tally((h for h in hits if h is not _MISS), counts)
    return ScanResult(counts, 1, [], bad)


def _read_stdin() -> str:
    """stdin as UTF-8 whatever the console code page, BOM dropped, undecodable bytes replaced.

    Read through the byte buffer: a cp1252 text stdin raised UnicodeDecodeError on the first byte
    that code page leaves undefined (0x81), killing the read mid-stream.
    """
    buffer = getattr(sys.stdin, "buffer", None)
    if buffer is None:
        return sys.stdin.read()
    return buffer.read().decode("utf-8-sig", errors="replace")


def _report_reach(res: ScanResult) -> None:
    """Say what was reached, on stderr - a count in the parsed stream would be read as data."""
    skipped = len(res.files_skipped) + len(res.missing)
    print(f"files: {res.files_read} read, {skipped} skipped", file=sys.stderr)
    _report_problems(res)


def _report_problems(res: ScanResult) -> None:
    if res.lines_skipped:
        print(f"lines: {res.lines_skipped} unparseable line(s) skipped", file=sys.stderr)
    for path in res.files_skipped:
        print(f"skipped: {path}", file=sys.stderr)
    for path in res.missing:
        print(f"skipped: {path} (no such file or directory)", file=sys.stderr)


def _exit_code(res: ScanResult) -> int:
    if not res.files_read:
        return 3
    return 2 if res.missing else 0


def _run_count(args) -> int:
    kwargs = dict(field=args.field, type_=args.type_, role=args.role, pattern=args.pattern)
    res = scan_corpus(args.paths, **kwargs) if args.paths else scan_text(_read_stdin(), **kwargs)
    _report_reach(res)
    if not res.files_read:
        return 3
    for value, times in res.counts.most_common():
        print(f"{times}\t{value}")
    return _exit_code(res)


def _print_hits(hits) -> int:
    """Print every usable hit; return how many lines were unparseable."""
    bad = 0
    for hit in hits:
        if hit is _BAD:
            bad += 1
        else:
            print(render(hit))
    return bad


def _run_list(args) -> int:
    rx = re.compile(args.pattern) if args.pattern else None
    kwargs = dict(rx=rx, type_=args.type_, role=args.role, field=args.field)
    if not args.paths:
        hits = (_match(raw, **kwargs) for raw in _records(_read_stdin()))
        res = ScanResult(Counter(), 1, [], _print_hits(h for h in hits if h is not _MISS))
        _report_problems(res)
        return 0
    files, missing, skipped = collect_paths(args.paths)
    read, bad = 0, 0
    for path in files:
        try:
            bad += _print_hits(iter_file_matches(path, **kwargs))
        except OSError:
            skipped.append(str(path))
            continue
        read += 1
    res = ScanResult(Counter(), read, skipped, bad, missing)
    _report_problems(res)
    return _exit_code(res)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Filter/extract/tally from JSONL files or a corpus.")
    ap.add_argument("paths", nargs="*", help="*.jsonl files or dirs to walk (default: stdin)")
    ap.add_argument("--type", dest="type_")
    ap.add_argument("--role")
    ap.add_argument("--field", help="dotted path to extract (e.g. message.model)")
    ap.add_argument("--pattern", help="regex over the raw line")
    ap.add_argument("--count", action="store_true",
                    help="tally --field's values across every file (or stdin), most common first")
    args = ap.parse_args(argv)
    if args.count and not args.field:
        print("jsonl_grep: --count needs --field (there is nothing to tally without one)", file=sys.stderr)
        return 2
    if args.pattern:
        try:
            re.compile(args.pattern)
        except re.error as exc:
            print(f"jsonl_grep: invalid --pattern {args.pattern!r}: {exc}", file=sys.stderr)
            return 2
    return _run_count(args) if args.count else _run_list(args)


def _utf8_stdout() -> None:
    """Emit UTF-8 whatever the console code page: a cp1252 stdout (Windows, redirected) crashed
    mid-output on the first em dash or emoji. Skipped for a stream that cannot be reconfigured."""
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is not None:
        try:
            reconfigure(encoding="utf-8", errors="backslashreplace")
        except (ValueError, OSError):
            pass


if __name__ == "__main__":
    _utf8_stdout()
    sys.exit(main())
