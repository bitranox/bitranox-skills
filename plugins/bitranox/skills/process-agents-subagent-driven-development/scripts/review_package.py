#!/usr/bin/env python3
"""Generate a review package: commit list, stat summary, and the net diff with
extended context, written to a file the reviewer reads in one call. Using the
recorded per-task BASE (not HEAD~1) keeps multi-commit tasks intact.

Usage: python3 review_package.py BASE HEAD [OUTFILE]
Default OUTFILE: <repo-root>/.bitranox/sdd/review-<base7>..<head7>.diff
(named per range, so a re-review after fixes gets a distinct fresh file).
"""
import subprocess
import sys
from pathlib import Path

import sdd_workspace


def _git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True)


def _resolves(ref):
    # "^{commit}" forces object existence + commit-ish type; a bare full-hex string
    # would otherwise "verify" as a syntactically valid name even when absent.
    return _git("rev-parse", "--verify", "--quiet", ref + "^{commit}").returncode == 0


def build(base, head):
    """The review-package text for base..head."""
    span = "%s..%s" % (base, head)
    return "\n".join([
        "# Review package: %s" % span,
        "",
        "## Commits",
        _git("log", "--oneline", span).stdout.rstrip("\n"),
        "",
        "## Files changed",
        _git("diff", "--stat", span).stdout.rstrip("\n"),
        "",
        "## Diff",
        _git("diff", "-U10", span).stdout.rstrip("\n"),
        "",
    ])


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) < 2 or len(argv) > 3:
        print("usage: review_package.py BASE HEAD [OUTFILE]", file=sys.stderr)
        return 2
    base, head = argv[0], argv[1]
    if not _resolves(base):
        print("bad BASE: %s" % base, file=sys.stderr)
        return 2
    if not _resolves(head):
        print("bad HEAD: %s" % head, file=sys.stderr)
        return 2
    if len(argv) == 3:
        out = Path(argv[2])
    else:
        short = lambda r: _git("rev-parse", "--short", r).stdout.strip()  # noqa: E731
        out = sdd_workspace.workspace_dir() / ("review-%s..%s.diff" % (short(base), short(head)))
    text = build(base, head)
    out.write_text(text, encoding="utf-8")
    commits = _git("rev-list", "--count", "%s..%s" % (base, head)).stdout.strip()
    print("wrote %s: %s commit(s), %d bytes" % (out, commits, len(text.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
