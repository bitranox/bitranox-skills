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

Exit codes: 0 = a match, 1 = no match, 2 = usage error.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
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
    args = ap.parse_args(argv)

    if not args.paths:
        print("newest: no paths - did the glob match nothing?", file=sys.stderr)
        return 2

    ordered = by_mtime(args.paths)
    skipped = unreadable(args.paths)
    if skipped:
        # Always to stderr, --json included, so stdout stays a clean parseable envelope.
        print(f"newest: skipped {len(skipped)} unreadable path(s): {', '.join(skipped)}",
              file=sys.stderr)
    if not ordered:
        print("newest: nothing readable among the given paths", file=sys.stderr)
        return 1

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
