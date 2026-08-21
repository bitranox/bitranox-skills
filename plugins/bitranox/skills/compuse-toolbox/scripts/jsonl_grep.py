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
loud one. Unreadable files are listed as skipped rather than dropped.

Run:
  `uv run scripts/jsonl_grep.py <file> [--type assistant] [--role user] [--field message.model]
                                     [--pattern REGEX]`
  `uv run scripts/jsonl_grep.py ~/.claude/projects --field message.model --count`

Exit codes: 0 read something, 2 usage error, 3 empty corpus (nothing was read).
"""
from __future__ import annotations

import argparse
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
        return orjson.dumps(obj).decode()
except ModuleNotFoundError:                              # stdlib fallback so the script runs anywhere
    import json as _json

    def _loads(raw):
        return _json.loads(raw)

    _JSONDecodeError = _json.JSONDecodeError

    def _dumps(obj):
        return _json.dumps(obj, ensure_ascii=False)


_MISS = object()                                         # a line that matched nothing, distinct from a falsy value
_BAD = object()                                          # a line no parse could use - counted, never silently dropped


def _get(obj, dotted: str):
    cur = obj
    for key in dotted.split("."):
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
        else:
            return None
    return cur


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
    val = _get(obj, field)
    return _MISS if val is None else val


def filter_records(text: str, *, type_=None, role=None, field=None, pattern=None):
    """Return matching records (list of dicts), or - when `field` is set - the extracted values.

    `pattern` is a regex tested against the RAW line (fast pre-filter); `type_` matches the
    top-level `type`; `role` matches `message.role`. Malformed lines are skipped.
    """
    rx = re.compile(pattern) if pattern else None
    hits = (_match(raw, rx=rx, type_=type_, role=role, field=field) for raw in text.splitlines())
    return [hit for hit in hits if hit is not _MISS and hit is not _BAD]


class ScanResult:
    """What a corpus scan found AND what it read, so an empty tally cannot pass for an answer."""

    def __init__(self, counts, files_read: int, files_skipped, lines_skipped: int = 0):
        self.counts = counts
        self.files_read = files_read
        self.files_skipped = files_skipped
        self.lines_skipped = lines_skipped


def expand_paths(paths):
    """Every file named by `paths`: a directory contributes the *.jsonl below it, sorted.

    A path that does not exist contributes nothing rather than raising - the caller learns about
    it from `files_read`, which is the number that decides whether an answer was earned.
    """
    found = []
    for raw in paths:
        path = Path(raw)
        if path.is_dir():
            found.extend(sorted(path.rglob("*.jsonl")))
        elif path.is_file():
            found.append(path)
    return found


def iter_file_matches(path, *, rx=None, type_=None, role=None, field=None):
    """Stream one file line by line, yielding matches - and `_BAD` for a line nothing could read.

    A live session's last line can be a partial write, so an unusable line is a normal event; the
    caller counts them rather than dropping them, because a silently shrinking denominator is how a
    scan reports less than it should while looking complete.
    """
    with open(path, encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            hit = _match(raw, rx=rx, type_=type_, role=role, field=field)
            if hit is not _MISS:
                yield hit


def scan_corpus(paths, *, field=None, type_=None, role=None, pattern=None) -> ScanResult:
    """Tally `field`'s values across every file under `paths`, reporting what was read."""
    rx = re.compile(pattern) if pattern else None
    counts: Counter = Counter()
    read, skipped, bad_lines = 0, [], 0
    for path in expand_paths(paths):
        try:
            for hit in iter_file_matches(path, rx=rx, type_=type_, role=role, field=field):
                if hit is _BAD:
                    bad_lines += 1
                else:
                    counts[hit if isinstance(hit, str) else _dumps(hit)] += 1
        except OSError:
            skipped.append(str(path))
            continue
        read += 1
    return ScanResult(counts, read, skipped, bad_lines)


def _report_reach(res: ScanResult) -> None:
    """Say what was reached, on stderr - a count in the parsed stream would be read as data."""
    print(f"files: {res.files_read} read, {len(res.files_skipped)} skipped", file=sys.stderr)
    if res.lines_skipped:
        print(f"lines: {res.lines_skipped} unparseable line(s) skipped", file=sys.stderr)
    for path in res.files_skipped:
        print(f"skipped: {path}", file=sys.stderr)


def _run_count(args) -> int:
    res = scan_corpus(args.paths, field=args.field, type_=args.type_, role=args.role, pattern=args.pattern)
    _report_reach(res)
    if not res.files_read:
        return 3
    for value, times in res.counts.most_common():
        print(f"{times}\t{value}")
    return 0


def _run_list(args) -> int:
    rx = re.compile(args.pattern) if args.pattern else None
    kwargs = dict(rx=rx, type_=args.type_, role=args.role, field=args.field)
    if not args.paths:
        for rec in filter_records(sys.stdin.read(), type_=args.type_, role=args.role,
                                  field=args.field, pattern=args.pattern):
            print(rec if isinstance(rec, str) else _dumps(rec))
        return 0
    files = expand_paths(args.paths)
    for path in files:
        for rec in iter_file_matches(path, **kwargs):
            if rec is _BAD:
                continue
            print(rec if isinstance(rec, str) else _dumps(rec))
    return 0 if files else 3


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Filter/extract/tally from JSONL files or a corpus.")
    ap.add_argument("paths", nargs="*", help="*.jsonl files or dirs to walk (default: stdin)")
    ap.add_argument("--type", dest="type_")
    ap.add_argument("--role")
    ap.add_argument("--field", help="dotted path to extract (e.g. message.model)")
    ap.add_argument("--pattern", help="regex over the raw line")
    ap.add_argument("--count", action="store_true",
                    help="tally --field's values across every file, most common first")
    args = ap.parse_args(argv)
    if args.count and not args.field:
        print("jsonl_grep: --count needs --field (there is nothing to tally without one)", file=sys.stderr)
        return 2
    return _run_count(args) if args.count else _run_list(args)


if __name__ == "__main__":
    sys.exit(main())
