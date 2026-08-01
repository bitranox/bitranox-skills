#!/usr/bin/env python3
"""PreToolUse(Bash) guard against a known-always-broken git invocation:
`git rev-parse --short` with two or more revisions.

`--short` abbreviates a SINGLE revision; passing two or more makes git fail with
`fatal: Needed a single revision` (exit 128), a confusing error that is easy to
dismiss as a transient quirk. It is deterministic: drop `--short` to print full
hashes for multiple revs, or call rev-parse once per rev. This guard blocks the
broken form before it runs and names the fix, so the error never has to be
re-diagnosed.

Pure standard library. Reads the PreToolUse event JSON on stdin. Exit 2 blocks the
call and shows stderr to the model; every other path (including any error) exits 0
so a broken guard never wedges a turn.
"""
import json
import re
import sys

# Shared with the other command-scanning guards: a heredoc body is DATA, and scanning it makes a
# guard fire on prose that merely mentions the footgun it guards. Re-exported so callers and tests
# can keep reaching it as `git_footgun_guard.strip_heredoc_bodies`.
from shell_text import strip_heredoc_bodies  # noqa: F401

# Split a command line into statements so a rev-parse in one segment is judged
# on its own operands, not tokens from a neighbouring command.
SEP = re.compile(r"&&|\|\||[;\n|]")

# Strip shell redirections BEFORE counting operands, else a `2>/dev/null` (or its
# target when spaced, `2> /dev/null`) is miscounted as a second revision and the
# guard false-fires on a valid single-rev command. Covers `2>/dev/null`, `> out`,
# `>>out`, `2>&1`, `&>out`, `<in` (operator + attached or space-separated target).
REDIR = re.compile(r"(?:&|\d+)?>>?(?:&\d+|\s*\S+)|<\s*\S+")

# git global options that consume a SEPARATE following token, so the subcommand
# search does not mistake their value for the subcommand.
GIT_VALUE_OPTS = frozenset(
    {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--config-env"}
)


def _revparse_operands(toks: list[str]) -> list[str] | None:
    """Tokens after `rev-parse` when it is genuinely the git SUBCOMMAND.

    Returns None when this segment is not a `git rev-parse` invocation - e.g.
    `git commit -m "...git rev-parse --short A B..."`, where the words appear
    only inside an argument.
    """
    idx = 0
    while idx < len(toks) and "=" in toks[idx] and not toks[idx].startswith("-"):
        idx += 1  # leading VAR=value environment assignments
    if idx >= len(toks) or toks[idx].rsplit("/", 1)[-1] != "git":
        return None
    idx += 1
    while idx < len(toks) and toks[idx].startswith("-"):
        if toks[idx] in GIT_VALUE_OPTS:
            idx += 1
        idx += 1
    if idx >= len(toks) or toks[idx] != "rev-parse":
        return None
    return toks[idx + 1 :]


def broken_revparse(command: str) -> bool:
    for segment in SEP.split(strip_heredoc_bodies(command)):
        segment = REDIR.sub(" ", segment)
        rest = _revparse_operands(segment.split())
        if rest is None:
            continue
        if not any(t == "--short" or t.startswith("--short=") for t in rest):
            continue
        # Operands are the non-option tokens after rev-parse (the revisions);
        # redirections are already stripped, `&` is backgrounding, not a revision.
        operands = [t for t in rest if not t.startswith("-") and t != "&"]
        if len(operands) >= 2:
            return True
    return False


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:
        return 0
    command = (event.get("tool_input") or {}).get("command") or ""
    if not broken_revparse(command):
        return 0
    sys.stderr.write(
        "git rev-parse --short takes a SINGLE revision; with 2+ revs it fails "
        "`fatal: Needed a single revision` (exit 128; the text is LOCALIZED - match the code).\n"
        "Fix: drop --short to print full hashes for multiple revs, or run "
        "rev-parse once per rev. Deterministic, not a transient quirk.\n"
    )
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
