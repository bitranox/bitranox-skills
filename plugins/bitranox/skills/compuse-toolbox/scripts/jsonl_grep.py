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
stream) and exits 2 when it read none, which turns a mistyped path from a silent all-clear into a
loud one. Unreadable files and directories found by a walk are listed as skipped rather than
dropped; a NAMED path that does not exist or cannot be opened fails the run even beside a good one,
and unparseable lines are counted in every mode.

A value is printed as itself when it is a plain string, and as JSON otherwise. A string that would
itself READ as JSON (`"1"`, `"true"`, `"null"`) is printed quoted, so the string "1" and the
number 1 never share a row, and a JSON `null` is a value (`null`), never mistaken for a missing key.
`--raw` (list mode only) prints every string bare instead, as `jq -r` does, for piping into a tool
that wants the text itself; it cannot be combined with `--count`, whose tally needs the distinction.

Run:
  `uv run scripts/jsonl_grep.py <file> [--type assistant] [--role user] [--field message.model]
                                     [--pattern REGEX]`
  `uv run scripts/jsonl_grep.py ~/.claude/projects --field message.model --count`
  `... | uv run scripts/jsonl_grep.py --field message.model [--count]`     (stdin)

NaN and Infinity are not JSON: a line holding one is unparseable on either backend (orjson or the
stdlib fallback), as is a line nested too deep to decode. A named path is read whatever kind of
file it is, so a process substitution (`jsonl_grep <(cmd)`) works.

Exit codes: 0 something matched (a hit printed, a value tallied), 1 everything named was read and
nothing matched - the filter's "no", 2 could not answer: a usage error, nothing was read (every
named path missing or unreadable, or no *.jsonl found), or a NAMED path that does not exist or
cannot be opened, even beside others that were read (what was read is still printed).
"""
from __future__ import annotations

import argparse
import fnmatch
import os
import re
import sys
from collections import Counter
from pathlib import Path

from _cli_envelope import EXIT_ERROR, EXIT_NO, EXIT_YES, guarded

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


def render(value, *, raw: bool = False) -> str:
    """One value as printed and tallied: a plain string bare, anything else as JSON.

    A string that would itself parse as JSON is quoted, so `"1"` and `1` (or `"true"` and `true`)
    never land on one row - bare strings alone made them indistinguishable in the output and
    merged them in the tally. `raw` prints every string bare (`jq -r`), giving that up on purpose.
    """
    if not isinstance(value, str):
        return _dumps(value)
    if raw:
        return value
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
    named paths that do not exist at all, and `named_unreadable` the NAMED paths (not ones a walk
    found) that exist but could not be opened - both fail the run even when something else was read.
    `hits` is how many records matched, so "read, matched nothing" is not mistaken for a match.
    """

    def __init__(self, counts, files_read: int, files_skipped, lines_skipped: int = 0,
                 missing=None, named_unreadable=None, hits: int | None = None):
        self.counts = counts
        self.files_read = files_read
        self.files_skipped = files_skipped
        self.lines_skipped = lines_skipped
        self.missing = list(missing or [])
        self.named_unreadable = list(named_unreadable or [])
        self.hits = sum(counts.values()) if hits is None else hits


def _walk_jsonl(path: Path, skipped: list, named_unreadable: list | None = None):
    """The *.jsonl below `path`, sorted; a directory it cannot list goes to `skipped`.

    `rglob` passes over an unreadable directory without a word, so the corpus shrank while the
    report said "0 skipped". `os.walk` with `onerror` names every one. The named directory ITSELF
    being unlistable goes to `named_unreadable` instead, when given: that is the caller's own
    path failing, not a corner of a corpus.
    """
    found = []

    def unreadable(exc: OSError) -> None:
        sink = named_unreadable if (named_unreadable is not None
                                    and str(exc.filename) == str(path)) else skipped
        sink.append(str(exc.filename))

    for dirpath, _dirs, names in os.walk(path, onerror=unreadable):
        found.extend(Path(dirpath) / n for n in names if fnmatch.fnmatch(n, "*.jsonl"))
    return sorted(found)


def collect_paths(paths, named_unreadable: list | None = None):
    """`(files, missing, unreadable_dirs)` for `paths`: a directory contributes its *.jsonl.

    A path that does not exist is returned in `missing` rather than dropped: beside a good path it
    used to vanish, so a typo cost its whole share of the corpus while the run exited 0. Any other
    existing path is read as a file, not only a regular one: `jsonl_grep <(cmd)` names a pipe
    (/dev/fd/63), which is neither a file nor a directory to `Path`. A named directory that cannot
    be listed lands in `named_unreadable` when that list is given (see `_walk_jsonl`).
    """
    found, missing, unreadable = [], [], []
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            found.extend(_walk_jsonl(path, unreadable, named_unreadable))
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


def _named(paths) -> set:
    """The paths the caller typed, as strings comparable with the files a collection returns."""
    return {str(Path(raw)) for raw in paths}


def _read_each(paths, consume):
    """Run `consume(path)` over every file under `paths`; a ScanResult minus counts and hits.

    A file that cannot be opened is a skip when a walk found it, and a failure of the run when the
    caller NAMED it: the first is a corner of a corpus, the second is the caller's own input.
    """
    named_unreadable: list = []
    files, missing, skipped = collect_paths(paths, named_unreadable)
    named = _named(paths)
    read, bad = 0, 0
    for path in files:
        try:
            bad += consume(path)
        except OSError:
            (named_unreadable if str(path) in named else skipped).append(str(path))
            continue
        read += 1
    return read, skipped, bad, missing, named_unreadable


def scan_corpus(paths, *, field=None, type_=None, role=None, pattern=None) -> ScanResult:
    """Tally `field`'s values across every file under `paths`, reporting what was read."""
    rx = re.compile(pattern) if pattern else None
    counts: Counter = Counter()
    read, skipped, bad_lines, missing, named_unreadable = _read_each(
        paths, lambda path: _tally(iter_file_matches(path, rx=rx, type_=type_, role=role,
                                                     field=field), counts))
    return ScanResult(counts, read, skipped, bad_lines, missing, named_unreadable)


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
    for path in res.named_unreadable:
        print(f"skipped: {path} (named, but could not be opened)", file=sys.stderr)


def _exit_code(res: ScanResult) -> int:
    """2 nothing read or a named path failed, else 0 something matched, 1 nothing did."""
    if not res.files_read or res.missing or res.named_unreadable:
        return EXIT_ERROR
    return EXIT_YES if res.hits else EXIT_NO


def _run_count(args) -> int:
    kwargs = dict(field=args.field, type_=args.type_, role=args.role, pattern=args.pattern)
    res = scan_corpus(args.paths, **kwargs) if args.paths else scan_text(_read_stdin(), **kwargs)
    _report_reach(res)
    for value, times in res.counts.most_common():
        print(f"{times}\t{value}")
    return _exit_code(res)


class _Printer:
    """Print every usable hit, counting hits and unparseable lines."""

    def __init__(self, raw: bool) -> None:
        self.raw = raw
        self.hits = 0

    def __call__(self, hits) -> int:
        bad = 0
        for hit in hits:
            if hit is _BAD:
                bad += 1
            else:
                self.hits += 1
                print(render(hit, raw=self.raw))
        return bad


def _run_list(args) -> int:
    rx = re.compile(args.pattern) if args.pattern else None
    kwargs = dict(rx=rx, type_=args.type_, role=args.role, field=args.field)
    printer = _Printer(args.raw)
    if not args.paths:
        hits = (_match(raw, **kwargs) for raw in _records(_read_stdin()))
        bad = printer(h for h in hits if h is not _MISS)
        res = ScanResult(Counter(), 1, [], bad, hits=printer.hits)
        _report_problems(res)
        return _exit_code(res)
    read, skipped, bad, missing, named_unreadable = _read_each(
        args.paths, lambda path: printer(iter_file_matches(path, **kwargs)))
    res = ScanResult(Counter(), read, skipped, bad, missing, named_unreadable, hits=printer.hits)
    _report_problems(res)
    return _exit_code(res)


@guarded("jsonl_grep", json_flags=())
def main(argv=None) -> int:
    """Filter or tally; exit 0 matched, 1 matched nothing, 2 could not answer (see module doc)."""
    ap = argparse.ArgumentParser(description="Filter/extract/tally from JSONL files or a corpus.")
    ap.add_argument("paths", nargs="*", help="*.jsonl files or dirs to walk (default: stdin)")
    ap.add_argument("--type", dest="type_")
    ap.add_argument("--role")
    ap.add_argument("--field", help="dotted path to extract (e.g. message.model)")
    ap.add_argument("--pattern", help="regex over the raw line")
    ap.add_argument("--count", action="store_true",
                    help="tally --field's values across every file (or stdin), most common first")
    ap.add_argument("--raw", action="store_true",
                    help="list mode: print strings bare, like jq -r (default quotes a string "
                         "that would read as JSON, so \"1\" and 1 differ)")
    args = ap.parse_args(argv)
    if args.count and not args.field:
        print("jsonl_grep: --count needs --field (there is nothing to tally without one)", file=sys.stderr)
        return 2
    if args.count and args.raw:
        print("jsonl_grep: --raw is for list mode; a --count tally keeps \"1\" and 1 apart",
              file=sys.stderr)
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
