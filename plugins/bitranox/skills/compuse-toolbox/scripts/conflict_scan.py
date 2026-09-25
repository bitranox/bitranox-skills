# /// script
# requires-python = ">=3.10"
# ///
"""Scan files (or a repo tree) for git merge-conflict markers, reporting file:line.

Why: after every rebase/cherry-pick the same `grep -c '^<<<<<<<'` is re-run to confirm a clean
tree; a stray marker that compiles/passes still corrupts the file. This finds all marker kinds
(<<<<<<<, |||||||, =======, >>>>>>>) at line start, so nothing is missed.

A lone ======= outside any <<<<<<< ... >>>>>>> span is the one ambiguous marker: a half-resolved
hunk can leave only the middle marker, but a Markdown setext heading underline ("Summary" over
seven equals signs) is the same line. It is skipped only in the heading shape - text above it and a
blank line (or the end of the file) below - and still counted when text sits on both sides.

Output: one `path:line: text` row per marker line, then a summary line.
Exit codes: 0 = no markers, 1 = markers found, 2 = a path or directory could not be read (or the
tool itself failed), so "no markers" cannot be claimed for it. Unreadable paths go to stderr.

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
_OPEN, _CLOSE, _MIDDLE = "<<<<<<<", ">>>>>>>", "======="


def _split_lines(text: str) -> list[str]:
    """Newline-split, as grep -n counts lines (splitlines also breaks on \\f and U+2028)."""
    lines = text.split("\n")
    if lines[-1] == "":
        lines.pop()  # the terminator of the last line is not a line of its own
    return [line[:-1] if line.endswith("\r") else line for line in lines]


def _is_setext_underline(lines: list[str], i: int) -> bool:
    """A lone ======= with text above it and a blank line or end of file below it."""
    above = lines[i - 1].strip() if i > 0 else ""
    below = lines[i + 1].strip() if i + 1 < len(lines) else ""
    return bool(above) and not _MARKER.match(lines[i - 1]) and not below


def scan_text(text: str) -> list[tuple[int, str]]:
    """[(1-based line number, the line)] for every conflict-marker line in `text`."""
    lines, hits, in_span = _split_lines(text), [], False
    for i, line in enumerate(lines):
        if not _MARKER.match(line):
            continue
        if line.startswith(_OPEN):
            in_span = True
        elif line.startswith(_CLOSE):
            in_span = False
        elif line.startswith(_MIDDLE) and not in_span and _is_setext_underline(lines, i):
            continue
        hits.append((i + 1, line))
    return hits


def _read(p) -> str:
    return Path(p).read_bytes().decode("utf-8-sig", errors="replace")


def scan_files(paths, unreadable: list[str] | None = None) -> dict[str, list[tuple[int, str]]]:
    """{path: [(line, text)]} for every file with markers; an unreadable file goes to `unreadable`.

    Pass a list as `unreadable` to learn which paths were never read - a missing or unreadable
    path must not be mistaken for a clean one.
    """
    out = {}
    for p in paths:
        try:
            text = _read(p)
        except OSError as exc:
            if unreadable is not None:
                unreadable.append("%s (%s)" % (p, exc.strerror or exc))
            continue
        hits = scan_text(text)
        if hits:
            out[str(p)] = hits
    return out


def scan_paths(paths, unreadable: list[str] | None = None) -> dict:
    """{path: [line numbers]} for every file that has markers; files without markers are omitted."""
    return {p: [ln for ln, _ in hits] for p, hits in scan_files(paths, unreadable).items()}


def _expand(targets, unreadable: list[str]) -> list[str]:
    """Every file under `targets`; a directory os.walk cannot open is recorded, not dropped."""
    def _record(err: OSError) -> None:
        unreadable.append("%s (%s)" % (err.filename, err.strerror or err))

    files = []
    for t in targets:
        pt = Path(t)
        if pt.is_dir():
            for dirpath, dirs, names in os.walk(t, onerror=_record):
                dirs[:] = [d for d in dirs if d != ".git"]
                files.extend(os.path.join(dirpath, n) for n in names)
        else:
            files.append(str(pt))
    return files


def _harden_stdout() -> None:
    """Escape what the console cannot encode (a cp1252 pipe, a non-UTF-8 filename's surrogates)
    rather than crash mid-listing. Called only when run as a script."""
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is not None:
        try:
            reconfigure(errors="backslashreplace")
        except (OSError, ValueError):  # a stream that cannot be reconfigured keeps its setting
            pass


def _main(argv) -> int:
    ap = argparse.ArgumentParser(description="Find git merge-conflict markers in files or a tree.")
    ap.add_argument("paths", nargs="*", default=["."], help="files or dirs (default: cwd)")
    args = ap.parse_args(argv)
    unreadable: list[str] = []
    res = scan_files(_expand(args.paths, unreadable), unreadable)
    for path, hits in sorted(res.items()):
        for line_no, text in hits:
            print(f"{path}:{line_no}: {text}")
    if res:
        print(f"CONFLICT MARKERS in {len(res)} file(s)")
    for entry in unreadable:
        print(f"conflict_scan: could not read {entry}", file=sys.stderr)
    if unreadable:
        return 2
    return 1 if res else 0


def main(argv=None) -> int:
    """Run the CLI. An unexpected failure exits 2, never 1 (markers found) or 0 (clean)."""
    try:
        return _main(argv)
    except Exception as exc:  # noqa: BLE001 - a crash must not read as a scan result
        print(f"conflict_scan: error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    _harden_stdout()
    sys.exit(main())
