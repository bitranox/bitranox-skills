# /// script
# requires-python = ">=3.14"
# ///
"""Scan files (or a repo tree) for git merge-conflict markers, reporting file:line.

Why: after every rebase/cherry-pick the same `grep -c '^<<<<<<<'` is re-run to confirm a clean
tree; a stray marker that compiles/passes still corrupts the file. This finds all marker kinds
(<<<<<<<, |||||||, =======, >>>>>>>) at line start, so nothing is missed.

A lone ======= outside any <<<<<<< ... >>>>>>> span is the one ambiguous marker: a half-resolved
hunk can leave only the middle marker, but a Markdown setext heading underline ("Summary" over
seven equals signs) is the same line. It is skipped only in the heading shape - text above it and a
blank line (or the end of the file) below - and still counted when text sits on both sides. The
overline of an RST title (======= / Title / =======) is skipped too, but only as that whole block:
a blank line or the start of the file above, and an underline that is itself in the heading shape.

Output: one `path:line: text` row per marker line, then a summary line.
Exit codes: 0 = no markers, 1 = markers found, 2 = a path or directory could not be read (or the
tool itself failed), so "no markers" cannot be claimed for it. Unreadable paths go to stderr. A
dangling or looping symlink is not an error: it resolves to no content, so it is listed on stderr
as skipped and does not change the exit code. A symlink to a directory met inside a walked tree is
not followed (git stores the link, never merges through it) and is named on stderr; a directory
you pass as PATH is walked even when it is a link, and a link to a FILE is always read.

A walk skips what git never merges into: `.git`, every venv (`.venv`, `.venv-3.12`, ... by prefix,
and any directory holding a `pyvenv.cfg`), `node_modules`, `__pycache__` and the tool caches
(`.mypy_cache`, `.pytest_cache`, `.ruff_cache`): the set in `_vendored_dirs`, which grep_all prunes
too. Scanning them made a clean checkout with a venv report markers (a
dist-info METADATA or a compiled .pyc holds a marker-shaped line by chance) after a minute and
1.3 GB of reading. A directory you NAME is scanned whatever its name. A file with a NUL byte in its
first 4 KB is skipped as binary (git writes no markers into a file it treats as binary) and the
number skipped is printed on stderr. Every file is streamed a line at a time, so memory is bounded
by the longest line, not the largest file.

Run: `uv run scripts/conflict_scan.py [PATH ...]`  (a dir is walked, skipping the trees above)
"""

import argparse
import io
import os
import re
import sys
from pathlib import Path

from _vendored_dirs import prune_vendored

# git conflict markers, ONLY at line start: the 7-char <<<<<<< / >>>>>>> / ||||||| (branch name may
# follow after a space) and the middle ======= (exactly 7 equals on its own line, allowing trailing
# whitespace). Matching only at line start avoids a marker embedded in a string/doc.
_MARKER = re.compile(r"^(?:<<<<<<<|>>>>>>>|\|\|\|\|\|\|\|)(?:\s|$)|^=======\s*$")
_OPEN, _CLOSE, _MIDDLE = "<<<<<<<", ">>>>>>>", "======="
_BINARY_SNIFF = 4096
_LOOKAHEAD = 3
"""Lines after the current one the heading rules read: an RST overline at i checks the underline at
i + 2, whose own heading test reads the line at i + 3."""


def _split_lines(text: str) -> list[str]:
    """Newline-split, as grep -n counts lines (splitlines also breaks on \\f and U+2028)."""
    lines = text.split("\n")
    if lines[-1] == "":
        lines.pop()  # the terminator of the last line is not a line of its own
    return [line[:-1] if line.endswith("\r") else line for line in lines]


def _is_setext_underline(above: str | None, below: str | None) -> bool:
    """A lone ======= with text above it and a blank line or end of file below it.

    `above` and `below` are the neighbouring lines, None past either end of the file."""
    return (bool(above and above.strip()) and not _MARKER.match(above)
            and not (below or "").strip())


def _is_rst_overline(window: list[str | None]) -> bool:
    """A lone ======= opening an RST title: nothing or a blank line above it, the title text below
    it, and under the title an identical ======= that is itself a heading underline. Requiring the
    whole three-line block keeps a stray middle marker with plain text under it a marker.

    `window` is [line i-1, line i, ..., line i+3], None for a line past either end."""
    above, _line, title, under, below_under = window
    if (above or "").strip() or title is None or under is None:
        return False
    return (bool(title.strip()) and not _MARKER.match(title)
            and under.rstrip() == _MIDDLE and _is_setext_underline(title, below_under))


def _is_heading_rule(window: list[str | None]) -> bool:
    return _is_setext_underline(window[0], window[2]) or _is_rst_overline(window)


def _windows(lines):
    """(i, [line i-1, line i, line i+1, line i+2, line i+3]) for each line, None past the ends.

    Holds five lines at a time, so a streamed file is scanned in bounded memory."""
    it = iter(lines)
    window: list[str | None] = [None]
    window.extend(next(it, None) for _ in range(1 + _LOOKAHEAD))
    i = 0
    while window[1] is not None:
        yield i, window
        window = [*window[1:], next(it, None)]
        i += 1


def scan_lines(lines) -> list[tuple[int, str]]:
    """[(1-based line number, the line)] for every conflict-marker line in `lines`.

    `lines` is any iterable of lines without their terminators, consumed once."""
    hits, in_span = [], False
    for i, window in _windows(lines):
        line = window[1]
        if not _MARKER.match(line):
            continue
        if line.startswith(_OPEN):
            in_span = True
        elif line.startswith(_CLOSE):
            in_span = False
        elif line.startswith(_MIDDLE) and not in_span and _is_heading_rule(window):
            continue
        hits.append((i + 1, line))
    return hits


def scan_text(text: str) -> list[tuple[int, str]]:
    """[(1-based line number, the line)] for every conflict-marker line in `text`."""
    return scan_lines(_split_lines(text))


class _Binary(Exception):
    """The file holds a NUL in its first 4 KB: binary, so it carries no conflict markers."""


def _scan_file(p) -> list[tuple[int, str]]:
    """`scan_lines` over the file at `p`, streamed; raises `_Binary` for a binary file.

    `utf-8-sig` drops a BOM so a marker on line 1 still starts the line; the terminator and one
    trailing \\r come off each line, as `_split_lines` does for a whole text."""
    with open(p, "rb") as fh:
        if b"\0" in fh.read(_BINARY_SNIFF):
            raise _Binary(str(p))
        fh.seek(0)
        text = io.TextIOWrapper(fh, encoding="utf-8-sig", errors="replace", newline="\n")
        return scan_lines(_strip_terminator(line) for line in text)


def _strip_terminator(line: str) -> str:
    line = line[:-1] if line.endswith("\n") else line
    return line[:-1] if line.endswith("\r") else line


def _is_dangling_symlink(p) -> bool:
    """A symlink that resolves to nothing: its target is gone, or it loops back on itself."""
    return os.path.islink(p) and not os.path.exists(p)


def scan_files(paths, unreadable: list[str] | None = None, *,
               skipped: list[str] | None = None,
               binary: list[str] | None = None) -> dict[str, list[tuple[int, str]]]:
    """{path: [(line, text)]} for every file with markers; an unreadable file goes to `unreadable`.

    Pass a list as `unreadable` to learn which paths were never read - a missing or unreadable
    path must not be mistaken for a clean one. A dangling or looping symlink goes to `skipped`
    instead: it has no content, so it cannot hold a marker, and a stale link (a .venv's python)
    must not make a whole clean tree unprovable. A binary file goes to `binary`.
    """
    out = {}
    for p in paths:
        try:
            hits = _scan_file(p)
        except _Binary:
            if binary is not None:
                binary.append(str(p))
            continue
        except OSError as exc:
            if _is_dangling_symlink(p):
                if skipped is not None:
                    skipped.append(str(p))
            elif unreadable is not None:
                unreadable.append("%s (%s)" % (p, exc.strerror or exc))
            continue
        if hits:
            out[str(p)] = hits
    return out


def scan_paths(paths, unreadable: list[str] | None = None) -> dict:
    """{path: [line numbers]} for every file that has markers; files without markers are omitted."""
    return {p: [ln for ln, _ in hits] for p, hits in scan_files(paths, unreadable).items()}


def _expand(targets, unreadable: list[str], linked_dirs: list[str] | None = None) -> list[str]:
    """Every file under `targets`; a directory os.walk cannot open is recorded, not dropped.

    A symlink to a directory met DURING the walk is not followed - git records the link itself
    and never merges through it, and following risks loops and trees outside the repo - so it
    goes to `linked_dirs` rather than vanishing. A target you name is walked even if it is a link.
    """
    def _record(err: OSError) -> None:
        unreadable.append("%s (%s)" % (err.filename, err.strerror or err))

    files = []
    for t in targets:
        pt = Path(t)
        if pt.is_dir():
            for dirpath, dirs, names in os.walk(t, onerror=_record):
                prune_vendored(dirpath, dirs)
                if linked_dirs is not None:
                    linked_dirs.extend(os.path.join(dirpath, d) for d in dirs
                                       if os.path.islink(os.path.join(dirpath, d)))
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
    skipped: list[str] = []
    linked_dirs: list[str] = []
    binary: list[str] = []
    res = scan_files(_expand(args.paths, unreadable, linked_dirs), unreadable, skipped=skipped,
                     binary=binary)
    for path, hits in sorted(res.items()):
        for line_no, text in hits:
            print(f"{path}:{line_no}: {text}")
    if res:
        print(f"CONFLICT MARKERS in {len(res)} file(s)")
    for entry in skipped:
        print(f"conflict_scan: skipped dangling symlink {entry}", file=sys.stderr)
    if binary:
        print(f"conflict_scan: {len(binary)} binary file(s) skipped", file=sys.stderr)
    for entry in linked_dirs:
        print(f"conflict_scan: symlinked directory not followed {entry}", file=sys.stderr)
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
