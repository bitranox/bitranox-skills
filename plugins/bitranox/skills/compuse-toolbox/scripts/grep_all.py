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
"Ignored" is judged from where the search started: a match in a nested repo or linked worktree
that sits in a directory the outer repo ignores counts as hidden when you pointed this at the
outer repo, and as visible when you pointed it inside the nested one. A FILE named on the command
line is never hidden, since a gitignore-aware search (rg) searches a file it is given regardless.
A `.git` entry is never searched, whether the repo's directory or a linked worktree's gitdir file.

Exit codes are format-independent: 0 at least one match, 1 no match, 2 the search could not run
(bad regex, missing path), was incomplete (a file or directory could not be read AND nothing
matched), or git could not say which matches are ignored (the count is printed as UNKNOWN,
never as 0) - because "nothing matched" and "the pattern never compiled" must not look alike.
Every unread path is listed on stderr and in the JSON `skipped` list, beside the binary files
that were skipped by rule; `files_scanned` counts only the files actually searched. A search that
could not run still emits the same envelope, with `ignored_matches` null (unknown) and an `error`.

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
_SKIP_FILES = {".git"}
"""A `.git` FILE is a linked worktree's or submodule's gitdir pointer - never content."""
_BINARY_SNIFF = 4096


def walk(paths, glob=None, unreadable=None):
    """Every file under `paths`, ignoring .gitignore entirely.

    A directory the walk cannot enter is appended to `unreadable` ("path: reason") when a list
    is given, instead of vanishing: a match inside it would otherwise just be missing, and a
    zero-match answer would read as "not there"."""
    def record(exc: OSError) -> None:
        if unreadable is not None:
            unreadable.append("%s: %s (directory not read)" % (exc.filename, type(exc).__name__))

    out = []
    for p in paths:
        if p.is_file():
            out.append(p)
            continue
        for dirpath, dirnames, filenames in os.walk(p, onerror=record):
            dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
            for name in filenames:
                if name not in _SKIP_FILES:
                    out.append(Path(dirpath) / name)
    if glob:
        out = [f for f in out if f.match(glob)]
    return sorted(set(out))


class GitUnavailable(Exception):
    """git could not answer, so the gitignored count is UNKNOWN - never zero."""


def gitignored(files, roots=None):
    r"""The subset git would consider ignored, as a set. Empty when nothing is a repo.

    Raises GitUnavailable when git cannot be run, times out, or fails outright - including a
    rev-parse that fails beside a `.git` entry (dubious ownership, a broken gitdir file): "0 of
    them are gitignored" is the finding, so a count git never gave must not print as one.

    `roots` are the paths the search was pointed at. A match is hidden when it is hidden from
    the view of the DEEPEST root holding it, which is where a gitignore-aware search of those
    paths would reach it: its own repo is asked, and so is every enclosing repo whose worktree
    that root spans - a nested repo or linked worktree sitting in a directory the outer repo
    ignores is never entered from the outer repo. Without `roots` only the file's own repo is
    asked. A file that IS one of the roots is never hidden: rg searches a named file whatever
    .gitignore says.

    Each path is handed to check-ignore ABSOLUTE (resolved like git's own toplevel). A path
    relative to the caller's cwd means something else to `git -C <toplevel>`: from a
    subdirectory an anchored `/sub/x.md` rule never matched, and `..` left the repo (exit 128).

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
    views = [_view_of(r) for r in roots or ()]
    toplevel = _ToplevelCache()
    # repo toplevel -> {path sent to that repo's check-ignore -> the matched files it decides}
    asks: dict[str, dict[str, set]] = {}
    for f in files:
        subject = _absolute(f)
        view = _deepest_view(Path(subject), views)
        if view == Path(subject):
            continue                # named on the command line, so searched regardless
        repo = toplevel(Path(subject).parent)
        while repo is not None:
            asks.setdefault(repo, {}).setdefault(subject, set()).add(f)
            if view is None or not _strictly_below(Path(repo), view):
                break
            # The search started above this repo, so the enclosing repo's rules decide whether
            # the walk ever entered it: ask that repo about this repo's own directory.
            outer = toplevel(Path(repo).parent)
            if outer is None or not _strictly_below(Path(repo), Path(outer)):
                break               # no enclosing repo (or GIT_DIR pins one repo): stop climbing
            subject, repo = repo, outer
    ignored = set()
    for repo, sent in asks.items():
        for echoed in _check_ignore(repo, list(sent)):
            ignored |= sent.get(echoed, set())
    return ignored


def _view_of(root: Path) -> Path:
    """A search root spelled the way `_absolute` spells a match, so the two compare."""
    return Path(_absolute(root)) if root.is_file() else root.resolve()


def _deepest_view(subject: Path, views: list[Path]) -> Path | None:
    """The deepest search root at or above `subject`, or None when none holds it."""
    holding = [v for v in views if v == subject or v in subject.parents]
    return max(holding, key=lambda v: len(v.parts)) if holding else None


def _strictly_below(repo: Path, view: Path) -> bool:
    return view in repo.parents


def _absolute(f: Path) -> str:
    """`f` with its DIRECTORY resolved (as git resolves its toplevel) but its own name kept:
    resolving a symlinked file itself could land outside the repo, where check-ignore refuses
    the whole batch."""
    return str(f.parent.resolve() / f.name)


class _ToplevelCache:
    """`_toplevel` per directory, asked once: a nested repo's parent is asked for every match."""

    def __init__(self) -> None:
        self._seen: dict[str, str | None] = {}

    def __call__(self, directory: Path) -> str | None:
        key = str(directory)
        if key not in self._seen:
            self._seen[key] = _toplevel(directory)
        return self._seen[key]


def _toplevel(directory: Path) -> str | None:
    """The repo toplevel holding `directory` (already resolved), or None when it is in no repo.

    rev-parse exits 128 both for "no repo here" and for a repo it refuses to read (dubious
    ownership, a gitdir file pointing nowhere, a .git without HEAD), and its message is
    localised. So the filesystem decides which: with no `.git` entry at or above the directory
    it is no repo; with one, a failure is git failing - and a gitignore-aware search still
    honours the .gitignore beside that `.git`, so the count is unknown, never zero."""
    try:
        root = subprocess.run(["git", "-C", str(directory), "rev-parse", "--show-toplevel"],
                              capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=30)
    except (OSError, subprocess.SubprocessError) as exc:
        raise GitUnavailable("git rev-parse: %s" % exc) from exc
    if root.returncode == 0:
        return root.stdout.strip()
    if not _has_git_entry(directory):
        return None
    raise GitUnavailable(f"git rev-parse in {directory} exited {root.returncode}: "
                         f"{root.stderr.strip()}")


def _has_git_entry(directory: Path) -> bool:
    """A `.git` dir or file at or above `directory`. lexists never raises: an unreadable
    ancestor answers False, as it would for git."""
    return any(os.path.lexists(os.path.join(p, ".git")) for p in (directory, *directory.parents))


def _check_ignore(root: str, paths: list[str]) -> list[str]:
    payload = "".join("%s\0" % p for p in paths).encode("utf-8", "surrogateescape")
    try:
        res = subprocess.run(["git", "-C", root, "check-ignore", "-z", "--stdin"],
                             input=payload, capture_output=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as exc:
        raise GitUnavailable("git check-ignore: %s" % exc) from exc
    if res.returncode not in (0, 1):          # 1 = nothing ignored, which is an answer
        raise GitUnavailable("git check-ignore exited %d: %s" % (
            res.returncode, res.stderr.decode("utf-8", "replace").strip()))
    return [raw for raw in res.stdout.decode("utf-8", "surrogateescape").split("\0") if raw]


def search(files, rx, unreadable=None, binary=None):
    """[(path, lineno, text)] for every matching line in a text file.

    Files not searched are recorded ("path: reason") in the lists given: a read error goes to
    `unreadable`, a NUL in the first 4 KB to `binary` (the usual text-file rule; winlog is the
    jig for UTF-16). Lines are split on "\\n" only, so a form feed or U+2028 inside a line does
    not shift the numbers off grep's; a leading BOM is dropped so `^pattern` matches line 1."""
    hits = []
    for f in files:
        try:
            raw = f.read_bytes()
        except OSError as exc:
            if unreadable is not None:
                unreadable.append("%s: %s" % (f, type(exc).__name__))
            continue
        if b"\0" in raw[:_BINARY_SNIFF]:
            if binary is not None:
                binary.append("%s: binary" % f)
            continue
        for n, line in enumerate(raw.decode("utf-8-sig", "replace").split("\n"), 1):
            line = line.rstrip("\r")
            if rx.search(line):
                hits.append((f, n, line.strip()))
    return hits


def path_problem(p: Path) -> str | None:
    """Why `p` cannot be searched, or None when it can be looked at.

    Not Path.exists(): before Python 3.14 it RAISES PermissionError for a path under an
    unreadable directory, and the traceback's exit 1 reads as "no match". Since 3.14 it answers
    False, which would print "does not exist" for a path that is merely unreachable. Both halves
    of the answer must be exit 2, and each must say which it is."""
    try:
        os.stat(p)
    except (FileNotFoundError, NotADirectoryError):
        return f"path does not exist: {p}"
    except (OSError, ValueError) as exc:
        return f"path cannot be accessed ({type(exc).__name__}): {p}"
    return None


def _tolerate_unencodable(stream) -> None:
    """Escape what the stream cannot encode rather than crash: a cp1252 Windows pipe meeting an
    arrow in a matched line, or a strict UTF-8 stream meeting a filename that is not UTF-8. A
    crash exits 1, which reads as "no match"."""
    reconfigure = getattr(stream, "reconfigure", None)
    if reconfigure is None:
        return
    try:
        reconfigure(errors="backslashreplace")
    except (ValueError, OSError):
        pass


def main(argv=None, out=None, err=None) -> int:
    out = out or sys.stdout
    err = err or sys.stderr
    _tolerate_unencodable(out)
    _tolerate_unencodable(err)
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
                              "data": {"matches": [], "ignored_matches": None,
                                       "files_scanned": 0},
                              "skipped": [], "error": msg}, indent=2), file=out)
        return 2

    try:
        rx = re.compile(args.pattern, re.I if args.ignore_case else 0)
    except re.error as exc:
        return fail("bad regex %r: %s" % (args.pattern, exc))

    paths = [Path(p) for p in (args.paths or ["."])]
    problems = [problem for problem in map(path_problem, paths) if problem]
    if problems:
        return fail("; ".join(problems))

    unread_dirs: list[str] = []
    files = walk(paths, args.glob, unreadable=unread_dirs)
    unread_files: list[str] = []
    binary: list[str] = []
    hits = search(files, rx, unreadable=unread_files, binary=binary)
    scanned = len(files) - len(unread_files) - len(binary)      # only files actually searched
    unread = unread_dirs + unread_files
    try:
        ignored = gitignored({f for f, _, _ in hits}, roots=paths)
        git_problem = None
    except GitUnavailable as exc:
        ignored, git_problem = set(), str(exc)
    matches = [{"path": str(f), "line": n, "text": t,
                "gitignored": None if git_problem else f in ignored} for f, n, t in hits]
    hidden = None if git_problem else sum(1 for m in matches if m["gitignored"])

    if args.json:
        print(json.dumps({"ok": bool(matches) and not git_problem, "command": "grep-all",
                          "data": {"matches": matches, "ignored_matches": hidden,
                                   "files_scanned": scanned},
                          "skipped": unread + binary}, indent=2), file=out)
    else:
        for m in matches:
            print("%s:%d:%s" % (m["path"], m["line"], m["text"]), file=out)
    _report(err, matches, scanned, hidden, git_problem, unread, binary)
    if git_problem or (unread and not matches):
        return 2
    return 0 if matches else 1


def _report(err, matches, scanned, hidden, git_problem, unread, binary) -> None:
    """The stderr summary: what was searched, what was not, and the gitignored count - or why
    that count is unknown. Unread paths are listed one per line, since any could hold a match."""
    for item in unread:
        print("grep_all: NOT READ %s" % item, file=err)
    if binary:
        print("grep_all: skipped %d binary file(s) (NUL in the first 4 KB)" % len(binary),
              file=err)
    if git_problem:
        print("grep_all: %d match(es) in %d file(s) scanned; the gitignored count is UNKNOWN - "
              "git could not answer (%s)" % (len(matches), scanned, git_problem), file=err)
        return
    print("grep_all: %d match(es) in %d file(s) scanned; %d of them are gitignored, so a "
          "gitignore-aware search would have missed them" % (len(matches), scanned, hidden),
          file=err)
    if unread and not matches:
        print("grep_all: %d path(s) could not be read, so 'no match' is unproven" % len(unread),
              file=err)


if __name__ == "__main__":
    raise SystemExit(main())
