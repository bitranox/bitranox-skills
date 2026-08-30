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
from shell_text import argv_for_match, git_verb_operands, iter_segments, strip_heredoc_bodies

# Split a command line into statements so a rev-parse in one segment is judged
# on its own operands, not tokens from a neighbouring command.

# Strip shell redirections BEFORE counting operands, else a `2>/dev/null` (or its
# target when spaced, `2> /dev/null`) is miscounted as a second revision and the
# guard false-fires on a valid single-rev command. Covers `2>/dev/null`, `> out`,
# `>>out`, `2>&1`, `&>out`, `<in` (operator + attached or space-separated target).
REDIR = re.compile(r"(?:&|\d+)?>>?(?:&\d+|\s*\S+)|<\s*\S+")

_REV_PARSE = frozenset({"rev-parse"})


def _revparse_operands(toks: list[str]) -> list[str] | None:
    """Tokens after `rev-parse` when it is genuinely the git SUBCOMMAND.

    Returns None when this segment is not a `git rev-parse` invocation - e.g.
    `git commit -m "...git rev-parse --short A B..."`, where the words appear
    only inside an argument.

    The walk itself now lives in `shell_text.git_verb_operands`. It started here, and it was the
    only correct answer to "what git command is this?" in the plugin while three other callers
    each got it wrong in their own way - so it moved to where they could all reach it.
    """
    return git_verb_operands(toks, _REV_PARSE)


def broken_revparse(command: str, tool_name: str | None = None) -> bool:
    # iter_segments, not SEP.split: a statement can begin inside a command substitution,
    # and `A=$(git rev-parse ...)` runs a real git command. SEP does not break at `$(`, so
    # the verb walk saw `A=$(git` and found nothing - this guard stayed quiet on a shape
    # its own advisory nudge (git-revparse-nudge) already fires on.
    for _at, segment in iter_segments(strip_heredoc_bodies(command), tool_name):
        segment = REDIR.sub(" ", segment)
        rest = _revparse_operands(argv_for_match(segment, tool_name))
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
    if not broken_revparse(command, event.get("tool_name")):
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
