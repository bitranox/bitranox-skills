# /// script
# requires-python = ">=3.10"
# ///
"""Scan files (or a repo tree) for git merge-conflict markers, reporting file:line.

Why: after every rebase/cherry-pick the same `grep -c '^<<<<<<<'` is re-run to confirm a clean
tree; a stray marker that compiles/passes still corrupts the file. This finds all marker kinds
(<<<<<<<, |||||||, =======, >>>>>>>) at line start, so nothing is missed.

Run: `uv run scripts/conflict_scan.py [PATH ...]`  (a dir is walked, skipping .git)
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

# git conflict markers, ONLY at line start: the 7-char <<<<<<< / >>>>>>> / ||||||| (branch name may
# follow after a space) and the middle ======= (exactly 7 equals on its own line, allowing trailing
# whitespace). Matching only at line start avoids a marker embedded in a string/doc.
_MARKER = re.compile(r"^(?:<<<<<<<|>>>>>>>|\|\|\|\|\|\|\|)(?:\s|$)|^=======\s*$")


def scan_text(text: str) -> list[tuple[int, str]]:
    """[(1-based line number, the line)] for every conflict-marker line in `text`."""
    return [(i + 1, line) for i, line in enumerate(text.splitlines()) if _MARKER.match(line)]


def scan_paths(paths) -> dict:
    """{path: [line numbers]} for every file that has markers; files without markers are omitted."""
    out = {}
    for p in paths:
        try:
            text = Path(p).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        hits = [ln for ln, _ in scan_text(text)]
        if hits:
            out[str(p)] = hits
    return out


def _expand(targets) -> list[str]:
    files = []
    for t in targets:
        pt = Path(t)
        if pt.is_dir():
            for dirpath, dirs, names in os.walk(t):
                dirs[:] = [d for d in dirs if d != ".git"]
                files.extend(os.path.join(dirpath, n) for n in names)
        else:
            files.append(str(pt))
    return files


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Find git merge-conflict markers in files or a tree.")
    ap.add_argument("paths", nargs="*", default=["."], help="files or dirs (default: cwd)")
    args = ap.parse_args(argv)
    res = scan_paths(_expand(args.paths))
    for path, lines in sorted(res.items()):
        print(f"{path}: {', '.join(map(str, lines))}")
    if res:
        print(f"CONFLICT MARKERS in {len(res)} file(s)")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
