#!/usr/bin/env python3
"""PreToolUse(Bash) nudge: a git command in this call answers from ANOTHER repository.

A `cd` persists for the rest of the call, so every git after it reports on wherever it landed -
and that output is indistinguishable from the session repo's. Measured shape: a call did
`cd RESEARCH && ... && echo agentdag && git log && git fetch origin`. All of it ran in RESEARCH,
so `git log` printed RESEARCH's commits under an agentdag heading and read as correct. Only
`origin does not appear to be a git repository` exposed it, and that was luck - RESEARCH happened
to have no remote. With remotes on both, the whole block would have passed as an agentdag check.

The sibling `git-revparse-nudge.py` cannot see this: no `rev-parse` need appear anywhere.

Two shapes fire, both structural:

- a `cd` whose destination is in a DIFFERENT git work tree than the session's, with a git command
  after it. Comparing REPO ROOTS rather than paths is what keeps this quiet: `cd src/ && git log`
  inside one repo answers about that same repo and is not worth a word.
- two or more `cd` statements with a git after them, whatever their repos - one repo per call, and
  after the second cd every later git answers from there.

Deliberately silent when the cd lands in the SESSION's own repo. That is the form the rev-parse
nudge explicitly recommends, and a guard that fires on its sibling's advice teaches nothing.

Data regions are masked before the structure is read, so a cd inside a heredoc or a quoted string
is text rather than a statement - prose documenting this footgun must not trip the guard for it.

NON-BLOCKING: emits additionalContext and exits 0. Fail-open on any error. ASCII only.
"""
from __future__ import annotations

import json
import os
import re
import sys

from shell_text import is_shell_tool, mask_data_regions, strip_heredoc_bodies

_SEPARATOR = re.compile(r"&&|\|\||;|\n|\|")
# `cd` as the statement's own verb, optionally behind env assignments. `cd -` and a bare `cd`
# go somewhere this hook cannot know, so they are treated as a directory change with no target.
_CD = re.compile(r"^\s*(?:\w+=\S*\s+)*cd\s+(?P<target>[^\s;&|]+)")
_GIT = re.compile(r"^\s*(?:\w+=\S*\s+)*(?:sudo\s+|timeout\s+\S+\s+)*git\b")


def _statements(command):
    """(start, end) offsets of each statement, read from the MASKED text.

    Structure comes from the mask; the caller slices the RAW string at these offsets, because a
    path compared on masked text would be compared as filler characters.
    """
    masked = mask_data_regions(strip_heredoc_bodies(command))
    spans, start = [], 0
    for hit in _SEPARATOR.finditer(masked):
        spans.append((start, hit.start()))
        start = hit.end()
    spans.append((start, len(masked)))
    return masked, spans


def _repo_root(path):
    """The work tree `path` belongs to, or None. Walks up looking for a `.git` entry."""
    try:
        current = os.path.abspath(path)
    except (TypeError, ValueError):
        return None
    while True:
        if os.path.exists(os.path.join(current, ".git")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            return None
        current = parent


def _resolve(target, base):
    """Where `cd target` lands, starting from `base`."""
    expanded = os.path.expanduser(target.strip().strip("'\""))
    if os.path.isabs(expanded):
        return os.path.normpath(expanded)
    return os.path.normpath(os.path.join(base, expanded))


def notice(command, cwd):
    """The nudge text when a git in this call answers from another repo, else None."""
    if not command or not isinstance(command, str) or not cwd:
        return None
    session_root = _repo_root(cwd)
    masked, spans = _statements(command)
    here, changes = str(cwd), 0
    for start, end in spans:
        raw = command[start:end]
        cd_hit = _CD.match(masked[start:end])
        if cd_hit:
            changes += 1
            target = raw[cd_hit.start("target"):cd_hit.end("target")]
            here = _resolve(target, here)
            continue
        if not _GIT.match(masked[start:end]):
            continue
        if changes >= 2:
            return _multi_cd_notice(here)
        if changes and _repo_root(here) != session_root:
            return _elsewhere_notice(here)
    return None


def _elsewhere_notice(where):
    return (
        "WRONG-REPO GIT: this call cd's into a different work tree, so every git after that point "
        f"answers from {where} - not from the session's repository. The output is indistinguishable "
        "from the session repo's, so a heading or a summary naming the other one reads as correct. "
        "State which repo the answer is about, and if you meant the session repo, drop the cd or "
        "cd back before the git."
    )


def _multi_cd_notice(where):
    return (
        "TWO DIRECTORY CHANGES, ONE CALL: a cd persists for the rest of the command, so each git "
        f"answers from whichever cd last ran - here {where}. One repo per call is the rule; split "
        "this into one call per repository so each answer has an unambiguous subject."
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
