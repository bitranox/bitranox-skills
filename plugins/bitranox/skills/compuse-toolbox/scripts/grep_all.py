#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Search every file, including gitignored ones, and say how many a normal grep would have hidden.

Why: in a Claude Code session `grep` is a shell function routing to a gitignore-aware backend, so a
repo-wide sweep silently drops ignored files and the miss looks exactly like a clean result.
Measured twice in one session: a memory-level enumeration found 17 of 43, and a sweep for a dead
doc reference found 1 of 4. Both times the under-count was acted on as if complete.

This walks the filesystem itself, so nothing is skipped for being ignored. It then asks git which
of the matches ARE ignored and reports that count on stderr, which is the number a gitignore-aware
search would have missed. A zero there means the two agree and your earlier grep was safe.

Exit codes are format-independent: 0 at least one match, 1 no match, 2 the search could not run
(bad regex, missing path) - because "nothing matched" and "the pattern never compiled" must not
look alike.

    uv run scripts/grep_all.py PATTERN [PATH ...] [--glob '*.md'] [--json] [-i]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

# Never worth searching: git's own object store, vendored trees, caches. Kept small and explicit -
# a broad skip list would reintroduce exactly the silent under-reporting this tool exists to stop.
_SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", ".venv-win", ".mypy_cache",
              ".pytest_cache", ".ruff_cache"}
_BINARY_SNIFF = 4096


def walk(paths, glob=None):
    """Every readable file under `paths`, ignoring .gitignore entirely."""
    out = []
    for p in paths:
        if p.is_file():
            out.append(p)
            continue
        for dirpath, dirnames, filenames in os.walk(p):
            dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
            for name in filenames:
                out.append(Path(dirpath) / name)
    if glob:
        out = [f for f in out if f.match(glob)]
    return sorted(set(out))


def gitignored(files):
    r"""The subset git would consider ignored, as a set. Empty when nothing is a repo.

    NUL-delimited and fed BYTES, for two separate reasons that both produced a silent "0 of
    them are gitignored" on Windows - the precise false-clean answer this tool exists to
    prevent, since the count IS the finding:

      * newline-delimited text stdin goes through subprocess's text wrapper, which translates
        "\n" to os.linesep. Git then reads "path\r", matches nothing and exits 1. Measured: the
        same call answers correctly on POSIX, so the bug is invisible to a POSIX-only run.
      * without -z, git QUOTES a path it considers unusual - a Windows path comes back as
        "C:\\Users\\..." with the backslashes doubled - so even a corrected stdin would then
        parse into a path that matches nothing.
    """
    ignored, by_root = set(), {}
    for f in files:
        try:
            root = subprocess.run(["git", "-C", str(f.parent), "rev-parse", "--show-toplevel"],
                                  capture_output=True, text=True, encoding="utf-8",
                                  errors="replace", timeout=30)
        except (OSError, subprocess.SubprocessError):
            continue
        if root.returncode != 0:
            continue
        by_root.setdefault(root.stdout.strip(), []).append(f)
    for root, group in by_root.items():
        payload = "".join("%s\0" % f for f in group).encode("utf-8", "surrogateescape")
        try:
            # check-ignore exits 1 when NOTHING is ignored, which is not an error here.
            res = subprocess.run(["git", "-C", root, "check-ignore", "-z", "--stdin"],
                                 input=payload, capture_output=True, timeout=120)
        except (OSError, subprocess.SubprocessError):
            continue
        for raw in res.stdout.decode("utf-8", "replace").split("\0"):
            if raw.strip():
                ignored.add(Path(raw))
    return ignored


def search(files, rx):
    """[(path, lineno, text)] for every matching line in a text file."""
    hits = []
    for f in files:
        try:
            raw = f.read_bytes()
        except OSError:
            continue
        if b"\0" in raw[:_BINARY_SNIFF]:
            continue
        for n, line in enumerate(raw.decode("utf-8", "replace").splitlines(), 1):
            if rx.search(line):
                hits.append((f, n, line.strip()))
    return hits


def main(argv=None, out=None, err=None) -> int:
    out = out or sys.stdout
    err = err or sys.stderr
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("pattern", help="python regex")
    ap.add_argument("paths", nargs="*", default=["."], help="files or dirs (default: .)")
    ap.add_argument("--glob", help="only files matching this glob, e.g. '*.md'")
    ap.add_argument("-i", "--ignore-case", action="store_true")
    ap.add_argument("--json", action="store_true", help="machine-readable envelope")
    args = ap.parse_args(argv)

    def fail(msg):
        print("grep_all: %s" % msg, file=err)
        if args.json:
            print(json.dumps({"ok": False, "command": "grep-all",
                              "data": {"matches": [], "ignored_matches": 0},
                              "error": msg}, indent=2), file=out)
        return 2

    try:
        rx = re.compile(args.pattern, re.I if args.ignore_case else 0)
    except re.error as exc:
        return fail("bad regex %r: %s" % (args.pattern, exc))

    paths = [Path(p) for p in (args.paths or ["."])]
    missing = [str(p) for p in paths if not p.exists()]
    if missing:
        return fail("path does not exist: %s" % ", ".join(missing))

    files = walk(paths, args.glob)
    hits = search(files, rx)
    ignored = gitignored({f for f, _, _ in hits})
    matches = [{"path": str(f), "line": n, "text": t, "gitignored": f in ignored}
               for f, n, t in hits]
    hidden = sum(1 for m in matches if m["gitignored"])

    if args.json:
        print(json.dumps({"ok": bool(matches), "command": "grep-all",
                          "data": {"matches": matches, "ignored_matches": hidden,
                                   "files_scanned": len(files)},
                          "skipped": []}, indent=2), file=out)
    else:
        for m in matches:
            print("%s:%d:%s" % (m["path"], m["line"], m["text"]), file=out)
    print("grep_all: %d match(es) in %d file(s) scanned; %d of them are gitignored, so a "
          "gitignore-aware search would have missed them" % (len(matches), len(files), hidden),
          file=err)
    return 0 if matches else 1


if __name__ == "__main__":
    raise SystemExit(main())
