#!/usr/bin/env python3
"""PreToolUse(Bash) nudge: two directory changes in one call, so a git answers from whichever ran last.

A `cd` persists for the rest of the call. When a single call cd's twice and runs git after each, the
two answers have different subjects and nothing in the output says which is which - measured in the
wild as one call stepping through two worktrees, running `git --no-pager grep` in each under
separate echo headings. One repo per call is the rule; this is the shape that breaks it.

WHAT THIS DELIBERATELY DOES NOT GUARD, and why: the neighbouring shape - ONE cd into a different
work tree, then git - is not distinguishable from routine work. Replayed over 60,517 real Bash
commands it fired 4,718 times, 7.8% of everything, because a session whose cwd is a parent project
working in a nested sub-repo looks exactly like a session reaching into an unrelated repo. The
motivating incident (`cd RESEARCH && ... && echo agentdag && git log`, whose output read as an
agentdag check) is in that same 7.8%: its hazard was the LABEL disagreeing with the cd, which is
narrative, not structure. A nudge at that rate is tuned out, so the arm was removed rather than
shipped noisy. Do not re-add it believing it covers the label case; a test pins that.

The surviving trigger fired 176 times over the same corpus - 0.29%, rare enough to mean something.

Data regions are masked before the structure is read, so a `cd` inside a heredoc or a quoted string
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


def _resolve(target, base):
    """Where `cd target` lands, starting from `base`."""
    expanded = os.path.expanduser(target.strip().strip("'\""))
    if os.path.isabs(expanded):
        return os.path.normpath(expanded)
    return os.path.normpath(os.path.join(base, expanded))


def notice(command, cwd):
    """The nudge text when a second cd has moved what a later git answers about, else None."""
    if not command or not isinstance(command, str) or not cwd:
        return None
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
        if _GIT.match(masked[start:end]) and changes >= 2:
            return _multi_cd_notice(here)
    return None


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
