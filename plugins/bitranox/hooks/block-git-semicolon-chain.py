#!/usr/bin/env python3
"""PreToolUse(Bash) guard: two or more state-changing git verbs joined by `;` instead of `&&`.

`;` means "run the next one regardless". Chain `git commit ; git merge ; git push` and a commit
that refused still lets the merge and the push run - and those two answer a no-op with git's
calmest output, `Already up to date` and `Everything up-to-date`, both exit 0. The failure is
loud at step one and invisible everywhere after it, so the transcript reads like a completed
ship while the working tree never moved.

`&&` stops the chain where it broke. That is the whole fix, and it costs one character.

Two shapes are exempt because they already say "continue deliberately":

- `set -e` (or `-euo pipefail`, or `-o errexit`) anywhere in the command, which makes the shell
  itself abort on the first failure, so `;` and `&&` behave the same;
- an explicit `|| true` / `|| :` immediately before the `;`, which states that this particular
  step is allowed to fail - `git tag -d v1 || true ; git push --delete origin v1` is a real
  cleanup pattern, not a mistake.

Pure standard library. Reads the PreToolUse event JSON on stdin. Exit 2 blocks the call and shows
stderr to the model; every other path (including any error) exits 0 so a broken guard never wedges
a turn.
"""
import json
import re
import sys

# Shared with the other command-scanning guards: a heredoc body is DATA, and scanning it makes a
# guard fire on prose that merely mentions the footgun it guards.
from shell_text import blank_unexpanded_text, strip_heredoc_bodies

# Verbs whose failure invalidates whatever the author wrote next. Read-only verbs (status, log,
# diff, rev-parse) are deliberately absent: a failed `git log` does not make the following step
# wrong, so chaining those with `;` is ordinary and must not be blocked.
STATE_CHANGING = frozenset(
    {
        "commit",
        "merge",
        "push",
        "tag",
        "reset",
        "rebase",
        "revert",
        "cherry-pick",
        "checkout",
        "switch",
    }
)

# git global options that consume a SEPARATE following token, so the subcommand search does not
# mistake their value for the subcommand (`git -C /repo commit` must read as `commit`).
GIT_VALUE_OPTS = frozenset(
    {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path", "--config-env"}
)

# Split while KEEPING the separators, because which one joined two statements is the entire
# question. `&&` and `||` must be tried before the single `|`, or they split into two pipes.
SEP_SPLIT = re.compile(r"(&&|\|\||[;\n]|\|)")

# Only these continue past a failure. `&&` stops, `||` runs only ON failure, `|` is a pipeline.
CONTINUES_AFTER_FAILURE = frozenset({";", "\n"})

# `set -e`, `set -euo pipefail`, `set -o errexit`. `set -u` alone must NOT match.
ERREXIT = re.compile(r"^set\s+(?:-[a-zA-Z]*e|-o\s+errexit)")


def _git_verb(segment: str) -> str | None:
    """The state-changing git subcommand this statement runs, or None.

    None covers everything that is not a state-changing git command: another program, a read-only
    git verb, and a `git` appearing only inside an argument (the quote and heredoc blanking has
    already removed those regions, so what reaches here is a real statement).
    """
    tokens = segment.strip().lstrip("(").strip().split()
    index = 0
    while index < len(tokens) and "=" in tokens[index] and not tokens[index].startswith("-"):
        index += 1  # leading VAR=value environment assignments
    if index >= len(tokens) or tokens[index].rsplit("/", 1)[-1] != "git":
        return None
    index += 1
    while index < len(tokens) and tokens[index].startswith("-"):
        if tokens[index] in GIT_VALUE_OPTS:
            index += 1
        index += 1
    if index >= len(tokens):
        return None
    verb = tokens[index]
    return verb if verb in STATE_CHANGING else None


def _has_errexit(parts: list[str]) -> bool:
    """True when the command sets errexit, which makes `;` abort like `&&` anyway."""
    return any(ERREXIT.match(part.strip()) for part in parts[::2])


def _deliberate_continuation(parts: list[str], start: int, stop: int) -> bool:
    """True when a `|| true` / `|| :` sits in the separator run between two statements.

    That is an author stating this step is allowed to fail, so the `;` after it is intentional.
    """
    for index in range(start, stop):
        if parts[index] == "||" and parts[index + 1].strip() in {"true", ":"}:
            return True
    return False


def chained_state_changes(command: str) -> list[str] | None:
    """The first pair of state-changing git verbs joined across an unguarded `;`, or None.

    Consecutive pairs are enough to cover every pair: any two state-changing statements are
    separated by at least one adjacent gap, so if every adjacent gap uses `&&` there is no `;`
    between any of them.
    """
    text = blank_unexpanded_text(strip_heredoc_bodies(command or ""), blank_double=True)
    parts = SEP_SPLIT.split(text)
    if _has_errexit(parts):
        return None

    # (index into parts, verb) for each statement running a state-changing git verb.
    found = [(i, _git_verb(parts[i])) for i in range(0, len(parts), 2)]
    found = [(i, verb) for i, verb in found if verb]

    for (index_a, verb_a), (index_b, verb_b) in zip(found, found[1:]):
        separators = [parts[i] for i in range(index_a + 1, index_b, 2)]
        if not any(sep in CONTINUES_AFTER_FAILURE for sep in separators):
            continue
        if _deliberate_continuation(parts, index_a + 1, index_b):
            continue
        return [verb_a, verb_b]
    return None


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:
        return 0
    command = (event.get("tool_input") or {}).get("command") or ""
    verbs = chained_state_changes(command)
    if not verbs:
        return 0
    sys.stderr.write(
        f"`git {verbs[0]}` and `git {verbs[1]}` are joined by `;`, so the second runs even when "
        f"the first FAILED.\n"
        "The steps after it then report their no-op as success - `Already up to date`, "
        "`Everything up-to-date`, exit 0 - and the transcript reads like a completed ship while "
        "nothing landed.\n"
        "Fix: join them with `&&` so the chain stops where it broke. If a step is genuinely "
        "allowed to fail, say so with `|| true` before the `;`; if the whole command should abort "
        "on any failure, start it with `set -e`.\n"
        "Then confirm the END STATE (`git rev-parse --verify -q origin/master`, "
        "`git show --name-only`), not the messages.\n"
    )
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
