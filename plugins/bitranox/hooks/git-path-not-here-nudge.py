#!/usr/bin/env python3
"""PreToolUse(Bash) nudge: a path-status question answered from a directory the path is not in.

The Bash tool's working directory PERSISTS across calls, so a call carrying no `cd` of its own runs
wherever an earlier call left the shell. When that call asks git a question ABOUT A PATH, and the
path is not in that directory, git answers rc 1 - and rc 1 from these verbs is shaped like a
VERDICT ("untracked", "not ignored") rather than like "no such file here". The wrong answer is
therefore indistinguishable from a real one, which is what makes this shape worth a nudge at all.

Measured incident: a session left the shell in a nested sub-repo, then ran
`git ls-files --error-unmatch handover.md` and `git check-ignore -q handover.md` with no `cd`. Both
returned rc 1, read as "untracked AND not ignored" - a combination that is impossible for a real
file, because an untracked non-ignored file must appear as `??` in `git status`. The true meaning
was "that file is not in this repository at all".

Scope, and why it is drawn here rather than wider:

- **Only the path-status verbs**: `ls-files --error-unmatch`, `check-ignore`, `check-attr`. These
  ask a question about ONE working-tree path, so an absent path produces a verdict-shaped answer.
  A pathspec on another verb is excluded on purpose - `git log -- <path>` about a DELETED file is
  routine and correct, and firing there would be noise.
- **Only a call with NO `cd` of its own.** An explicit `cd` states the subject; the two-work-tree
  shape belongs to the sibling `git-wrong-repo-nudge`. This hook covers the half that hook cannot
  see, because it fires on the cd's inside one call and this failure has none.
- **The path must exist in an ANCESTOR of the cwd.** Absent everywhere is a typo, which is not this
  hook's business and leaves nothing to point at. Present above is the signature of the trap: the
  file you mean is in the project you think you are in.
- **Readable, relative paths only.** A shell variable or a glob cannot be attributed to a location,
  and a verdict built on a guessed one is invented rather than measured.

Priced over 65,573 real Bash calls replayed with the cwd they actually ran under (the cwd field is
present on 100% of them): 350 use a path-status verb, 133 of those carry no `cd`, 13 name a path
absent under their cwd, and 3 of those find it in an ancestor. Those 3 are the firings - 0.0046% of
all commands - and all 3 are true positives from two unrelated sessions: the measured incident
above, plus a worktree cwd asking about `.claude` and `EXECUTION-USER-REVIEW.md`, both of which
live in the parent checkout. Replay understates recall, since a path deleted since cannot be found
in an ancestor today; that cost is accepted for the same reason the sibling hook accepts it.

Data regions are masked before the structure is read, so a command inside a heredoc or a quoted
string is text rather than a statement - prose documenting this footgun must not trip the guard for
it.

NON-BLOCKING: emits additionalContext and exits 0. Fail-open on any error. ASCII only.
"""
from __future__ import annotations

import json
import os
import re
import sys

from shell_text import is_shell_tool, mask_data_regions, strip_heredoc_bodies

_SEPARATOR = re.compile(r"&&|\|\||;|\n|\|")
_CD = re.compile(r"^\s*(?:\w+=\S*\s+)*cd(?:\s|$)")
_VERB = re.compile(
    r"^\s*(?:\w+=\S*\s+)*(?:sudo\s+|timeout\s+\S+\s+)*git\s+"
    r"(?P<verb>ls-files|check-ignore|check-attr)(?P<rest>\s.*)?$"
)
# a path no static read can resolve, or that is not a plain path at all
_UNKNOWABLE = re.compile(r"[$`<>*?]")
_REDIRECT = re.compile(r"^\d*[<>]")


def _statements(command):
    """(masked_text, [(start, end)]) for each statement, offsets valid in the RAW string too."""
    masked = mask_data_regions(strip_heredoc_bodies(command))
    spans, start = [], 0
    for hit in _SEPARATOR.finditer(masked):
        spans.append((start, hit.start()))
        start = hit.end()
    spans.append((start, len(masked)))
    return masked, spans


def _path_arguments(rest, verb):
    """The bare path tokens of a path-status verb, in order.

    Read from the RAW slice, never the masked one: a quoted `"$FILE"` must keep its `$` so it can
    be rejected as unreadable rather than silently treated as a literal name.
    """
    tokens, skip_attribute = [], (verb == "check-attr")
    for token in rest.split():
        if token.startswith("-") or _REDIRECT.match(token):
            continue
        if skip_attribute:                 # `check-attr <attr> <path>`: the first bare token names
            skip_attribute = False         # the attribute, not a file
            continue
        tokens.append(token.strip("'\""))
    return [t for t in tokens if t]


def _ancestor_holding(path, cwd):
    """The nearest ancestor of `cwd` that has `path` under it, or None."""
    current = os.path.abspath(cwd)
    while True:
        parent = os.path.dirname(current)
        if parent == current:
            return None
        if os.path.exists(os.path.join(parent, path)):
            return parent
        current = parent


def notice(command, cwd):
    """The nudge text when a path-status verb asks about a path that is not here, else None."""
    if not command or not isinstance(command, str) or not cwd:
        return None
    masked, spans = _statements(command)
    if any(_CD.match(masked[start:end]) for start, end in spans):
        return None                        # an explicit cd states the subject
    for start, end in spans:
        hit = _VERB.match(masked[start:end])
        if not hit:
            continue
        raw_rest = command[start:end][hit.start("rest"):hit.end("rest")] if hit.group("rest") else ""
        if hit.group("verb") == "ls-files" and "--error-unmatch" not in raw_rest:
            continue                       # a listing, not a question about one path
        for path in _path_arguments(raw_rest, hit.group("verb")):
            if _UNKNOWABLE.search(path) or os.path.isabs(path):
                continue
            if os.path.exists(os.path.join(cwd, path)):
                continue
            elsewhere = _ancestor_holding(path, cwd)
            if elsewhere:
                return _notice(path, cwd, elsewhere)
    return None


def _notice(path, cwd, elsewhere):
    return (
        f"PATH NOT IN THIS DIRECTORY: this call carries no `cd`, so it runs in {cwd}, where "
        f"'{path}' does not exist - but it does under {elsewhere}. The Bash tool's cwd PERSISTS "
        "from an earlier call, so you are probably answering about the wrong repository. These "
        "verbs return rc 1 for a missing path, which reads as a VERDICT ('untracked', 'not "
        "ignored') and not as 'no such file here' - rc 1 from BOTH `ls-files --error-unmatch` and "
        "`check-ignore` is that signature, not a contradiction. Add an absolute `cd /full/path &&`."
    )


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:  # noqa: BLE001 - no/invalid stdin: do nothing
        return 0
    if not isinstance(event, dict) or not is_shell_tool(event.get("tool_name")):
        return 0
    cwd = event.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    message = notice((event.get("tool_input") or {}).get("command"), cwd)
    if message:
        sys.stdout.write(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": message,
        }}) + "\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - a broken hook must never wedge a turn
        sys.exit(0)
