#!/usr/bin/env python3
"""Generate a review package: commit list, stat summary, and the net diff with
extended context, written to a file the reviewer reads in one call. Using the
recorded per-task BASE (not HEAD~1) keeps multi-commit tasks intact.

Usage: python3 review_package.py BASE HEAD [OUTFILE]
Default OUTFILE: <repo-root>/.bitranox/sdd/review-<base7>..<head7>.diff
(named per range, so a re-review after fixes gets a distinct fresh file).

BASE must be an ancestor of HEAD (swapped arguments, or a BASE rewritten away,
exit 2). A working directory outside any git repository, or a git that cannot be run,
exits 2 naming that rather than the refs. Any git failure while building the package
exits 2 and writes nothing, as does a workspace or OUTFILE that cannot be written.
The diff is kept byte-exact, so a line-ending change shows as one.
"""
import subprocess
import sys
from pathlib import Path

import sdd_workspace


class GitError(Exception):
    """A git command failed, so the package would be missing whatever it was meant to hold."""


def _git(*args):
    """Run git. Raises GitError, never OSError, when git itself cannot be started."""
    # Bytes, not text=True: universal-newline decoding turns "+a\r\n" into "+a\n" and a lone
    # "\r" into a line break, which hides exactly the CRLF regression a reviewer must see.
    try:
        return subprocess.run(["git", *args], capture_output=True)
    except OSError as exc:
        # Escaping, this was a traceback and exit 1, which the exit-code contract does not have.
        raise GitError(f"could not run git: {exc}") from exc


def _git_bytes(*args):
    """Stdout of a git command that must succeed, exactly as git wrote it."""
    proc = _git(*args)
    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", "replace").strip()
        raise GitError("git %s failed (exit %d): %s" % (" ".join(args), proc.returncode, err))
    return proc.stdout


def _git_text(*args):
    """Stdout of a git command that must succeed, decoded - for refs and counts only, never
    for content the package carries, where a replaced byte would hide an encoding change."""
    return _git_bytes(*args).decode("utf-8", "replace")


def _resolves(ref):
    # "^{commit}" forces object existence + commit-ish type; a bare full-hex string
    # would otherwise "verify" as a syntactically valid name even when absent.
    return _git("rev-parse", "--verify", "--quiet", ref + "^{commit}").returncode == 0


def _is_ancestor(base, head):
    return _git("merge-base", "--is-ancestor", base, head).returncode == 0


def build(base, head):
    """The review-package bytes for base..head. Raises GitError when any git call fails.

    Bytes end to end: git's output is copied as written, so a non-UTF-8 byte in a changed line
    reaches the reviewer as that byte, not as a U+FFFD that reads like an ordinary character.
    """
    span = "%s..%s" % (base, head)
    return b"\n".join([
        ("# Review package: %s" % span).encode("utf-8"),
        b"",
        b"## Commits",
        _git_bytes("log", "--oneline", span).rstrip(b"\n"),
        b"",
        b"## Files changed",
        _git_bytes("diff", "--stat", span).rstrip(b"\n"),
        b"",
        b"## Diff",
        _git_bytes("diff", "-U10", span).rstrip(b"\n"),
        b"",
    ])


def _tolerate_unencodable_output():
    """Replace, rather than crash on, a character the console cannot encode (cp1252 pipes)."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(errors="replace")
            except (ValueError, OSError):
                pass


def _repository_problem():
    """An error message when the working directory is not in a git repository, or None.

    Checked before the refs: outside a repository NO ref resolves, so the first ref check
    reported "bad BASE" and sent the reader to inspect a ref that was fine.
    """
    proc = _git("rev-parse", "--git-dir")
    if proc.returncode == 0:
        return None
    err = proc.stderr.decode("utf-8", "replace").strip()
    return f"not inside a git repository: {Path.cwd()} (git rev-parse: {err})"


def _check_refs(base, head):
    """An error message for no repository or an unusable BASE/HEAD pair, or None.

    Raises GitError when git cannot be run at all.
    """
    problem = _repository_problem()
    if problem:
        return problem
    if not _resolves(base):
        return "bad BASE: %s" % base
    if not _resolves(head):
        return "bad HEAD: %s" % head
    if not _is_ancestor(base, head):
        return ("BASE %s is not an ancestor of HEAD %s: the arguments are swapped, or BASE was "
                "rewritten after it was recorded" % (base, head))
    return None


def main(argv=None):
    _tolerate_unencodable_output()
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) < 2 or len(argv) > 3:
        print("usage: review_package.py BASE HEAD [OUTFILE]", file=sys.stderr)
        return 2
    base, head = argv[0], argv[1]
    try:
        problem = _check_refs(base, head)
    except GitError as exc:
        problem = str(exc)
    if problem:
        print(problem, file=sys.stderr)
        return 2
    try:
        data = build(base, head)
        commits = _git_text("rev-list", "--count", "%s..%s" % (base, head)).strip()
        if len(argv) == 3:
            out = Path(argv[2])
        else:
            short = lambda r: _git_text("rev-parse", "--short", r).strip()  # noqa: E731
            out = sdd_workspace.workspace_dir() / ("review-%s..%s.diff" % (short(base), short(head)))
    except (GitError, sdd_workspace.WorkspaceError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    try:
        out.write_bytes(data)  # bytes, so Windows does not rewrite every "\n" as "\r\n"
    except OSError as exc:
        print("cannot write the review package: %s" % exc, file=sys.stderr)
        return 2
    print("wrote %s: %s commit(s), %d bytes" % (out, commits, len(data)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
