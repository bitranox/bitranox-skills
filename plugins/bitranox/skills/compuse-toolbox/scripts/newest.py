# /// script
# requires-python = ">=3.10"
# ///
"""Pick the latest timestamped file or directory by MTIME, never by name sort.

The trap this ends: `ls <glob> | sort | tail -1` looks like "the newest" and is not. A longer
name sharing the same prefix sorts AFTER a shorter one, so an extra word beats the date - for
example `nightly-snapshot-with-extra-notes-20260708` sorts after `nightly-snapshot-20260804`
even though the second is ten months newer. Pruning the wrong file is loud and gets noticed;
VERIFYING against the wrong baseline is silent, which is the expensive half.

It also prints the AGE of what it picked, because the newest member of a stale set is still
stale, and a bare path gives you no way to notice that.

Run:
  `uv run scripts/newest.py /backups/nightly-*`          # newest, with its age
  `uv run scripts/newest.py --all /backups/nightly-*`    # every match, newest first
  `uv run scripts/newest.py --json /backups/nightly-*`
  `uv run scripts/newest.py --name-timestamp /backups/samples-*.gz`

MTIME IS THE WRONG KEY when a later pass rewrote the files - compression, re-encoding, a fixup
job. Then mtime records when THAT pass ran, not when the content was produced, so the set is
ordered by the wrong event: rotated samples gzipped off the hot path carry mtimes hours after
the data they hold ended, and every rate computed across a file boundary used the wrong
neighbour, with no error. `--name-timestamp` keys on a fixed-width stamp in the filename
instead. The default run WARNS when the two keys disagree about the answer, which is exactly
when the choice of key matters.

Exit codes: 0 = a match, 1 = no match, 2 = usage error.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def _mtime(path: Path) -> float | None:
    """The path's mtime, or None when it cannot be read (a dangling symlink, a race)."""
    try:
        return path.stat().st_mtime
    except OSError:
        return None


def _readable(raw) -> tuple[Path, float] | None:
    """(path, mtime) when the path can be stat'd, else None - never guessed at."""
    path = Path(raw)
    mtime = _mtime(path)
    return None if mtime is None else (path, mtime)


# Fixed-width stamps only, longest first: a 14-digit form must not be read as its own 8-digit
# prefix. Anything narrower than a full date is ambiguous with a version or a counter, so it is
# not matched at all - guessing here would reintroduce the silent wrong answer this tool exists
# to stop.
_STAMP_PATTERNS = (
    (re.compile(r"(?<!\d)(\d{8})[T_-](\d{6})(?!\d)"), "%Y%m%d%H%M%S"),
    (re.compile(r"(?<!\d)(\d{8})(\d{6})(?!\d)"), "%Y%m%d%H%M%S"),
    (re.compile(r"(?<!\d)(\d{8})(?!\d)"), "%Y%m%d"),
)


def parse_name_stamp(name) -> float | None:
    """The epoch seconds of a fixed-width timestamp in `name`, or None when there is none.

    Use this when a LATER pass rewrote the files - compression, re-encoding, a fixup job. Then
    mtime records when THAT pass ran rather than when the content was produced, so it orders the
    set by the wrong event and the tool answers confidently with the wrong file.

    The digits must be a real date: a number of the right WIDTH is not a timestamp, and reading
    `build-20261345.log` as a date would be a fresh way to get the same silent wrong answer. The
    FIRST parseable stamp wins when a name carries more than one.
    """
    text = str(name)
    for pattern, fmt in _STAMP_PATTERNS:
        for hit in pattern.finditer(text):
            joined = "".join(hit.groups())
            try:
                parsed = datetime.strptime(joined, fmt)
            except ValueError:
                continue                       # right width, not a real date
            return parsed.replace(tzinfo=timezone.utc).timestamp()
    return None


def by_name_stamp(paths) -> list[Path]:
    """Every path carrying a parseable name stamp, NEWEST FIRST by that stamp.

    Paths with no stamp are EXCLUDED rather than sorted to one end: their position would be an
    invention, and an invented order is what this whole tool refuses to produce. `unstamped()`
    names them so the caller can report them.
    """
    stamped = []
    for raw in paths or []:
        stamp = parse_name_stamp(Path(raw).name)
        if stamp is not None:
            stamped.append((Path(raw), stamp))
    stamped.sort(key=lambda pair: pair[1], reverse=True)
    return [path for path, _ in stamped]


def newest_by_name_stamp(paths) -> Path | None:
    """The path whose NAME carries the latest timestamp, or None when none does."""
    ordered = by_name_stamp(paths)
    return ordered[0] if ordered else None


def unstamped(paths) -> list[str]:
    """Raw path strings carrying no parseable fixed-width timestamp."""
    return [str(raw) for raw in (paths or []) if parse_name_stamp(Path(raw).name) is None]


def keys_disagree(paths) -> bool:
    """Whether mtime and the name stamp pick DIFFERENT files.

    This is the warning condition, and it deliberately has no threshold. "The mtimes are much
    later than the stamps" needs a cutoff nobody can justify, and a set can be wholly rewritten
    without changing the answer. The two keys disagreeing is precisely the case where the choice
    of key changes the result, which is the only case worth interrupting for.
    """
    by_time = newest(paths)
    by_name = newest_by_name_stamp(paths)
    if by_time is None or by_name is None:
        return False
    return Path(by_time).resolve() != Path(by_name).resolve()


def by_mtime(paths) -> list[Path]:
    """Every readable path, NEWEST FIRST.

    Unreadable entries are skipped, never guessed at. A tie in mtime (possible - resolution
    varies by filesystem and OS) breaks by INPUT ORDER: Python's sort is stable, so among equal
    mtimes the path that came first in `paths` sorts first. This is deterministic, not an
    artifact of directory-listing order.
    """
    stamped = [pair for pair in (_readable(raw) for raw in paths or []) if pair is not None]
    stamped.sort(key=lambda pair: pair[1], reverse=True)
    return [path for path, _ in stamped]


def newest(paths) -> Path | None:
    """The single most recently modified path, or None when nothing is readable."""
    ordered = by_mtime(paths)
    return ordered[0] if ordered else None


def unreadable(paths) -> list[str]:
    """Raw path strings that could not be stat'd - missing, a dangling symlink, or denied."""
    return [str(raw) for raw in (paths or []) if _readable(raw) is None]


def age_seconds(path: Path, now: float | None = None) -> float:
    """How old the path is, so a stale pick is visible rather than implied."""
    mtime = _mtime(path)
    if mtime is None:
        return float("inf")
    return (time.time() if now is None else now) - mtime


def _human_age(seconds: float) -> str:
    if seconds == float("inf"):
        return "unknown"
    for unit, size in (("d", 86400), ("h", 3600), ("m", 60)):
        if seconds >= size:
            return f"{seconds / size:.1f}{unit}"
    return f"{seconds:.0f}s"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Newest path by mtime (shell expands the glob; never sorts by name).")
    ap.add_argument("paths", nargs="*", help="paths, usually from a shell glob")
    ap.add_argument("--all", action="store_true", help="list every match, newest first")
    ap.add_argument("--json", action="store_true", help="machine-readable envelope")
    ap.add_argument("--name-timestamp", action="store_true",
                    help="key on a fixed-width timestamp in the FILENAME, not mtime - "
                         "correct when a later pass rewrote the files")
    args = ap.parse_args(argv)

    if not args.paths:
        print("newest: no paths - did the glob match nothing?", file=sys.stderr)
        return 2

    if args.name_timestamp:
        ordered = by_name_stamp(args.paths)
        skipped = unstamped(args.paths)
        if skipped:
            print(f"newest: skipped {len(skipped)} path(s) with no fixed-width name stamp: "
                  f"{', '.join(skipped)}", file=sys.stderr)
        if not ordered:
            # Never fall back to mtime here. A silent fallback answers the question the caller
            # explicitly said was the wrong one, which is the defect this flag exists to fix.
            print("newest: no path carries a parseable fixed-width name stamp "
                  "(YYYYMMDDTHHMMSSZ, YYYYMMDD-HHMMSS or YYYYMMDD)", file=sys.stderr)
            return 1
    else:
        ordered = by_mtime(args.paths)
        skipped = unreadable(args.paths)
        if skipped:
            # Always to stderr, --json included, so stdout stays a clean parseable envelope.
            print(f"newest: skipped {len(skipped)} unreadable path(s): {', '.join(skipped)}",
                  file=sys.stderr)
        if not ordered:
            print("newest: nothing readable among the given paths", file=sys.stderr)
            return 1
        if keys_disagree(args.paths):
            print("newest: mtime and the name stamps pick DIFFERENT files - a later pass "
                  "(compression, re-encoding, a fixup job) likely rewrote these, so mtime "
                  "records that pass and not the content. Re-run with --name-timestamp.",
                  file=sys.stderr)

    data = [{"path": str(p), "age_seconds": round(age_seconds(p), 3)} for p in ordered]
    if not args.all:
        data = data[:1]

    if args.json:
        print(json.dumps({"ok": True, "command": "newest", "skipped": skipped, "data": data},
                          indent=2))
    else:
        for item in data:
            print(f"{item['path']}  (age {_human_age(item['age_seconds'])})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
