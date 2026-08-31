#!/usr/bin/env python3
"""PreToolUse(Bash) nudge: one call, two work trees, so two gits answer about different repos.

A `cd` persists for the rest of the call. When a single call cd's into two DIFFERENT work trees and
runs git after each, the two answers have different subjects and nothing in the output says which is
which - measured in the wild as one call stepping through two worktrees running `git --no-pager
grep` in each under separate echo headings. One repo per call is the rule; this is the shape that
breaks it.

Three conditions, each one bought with measurements over 60,517 real Bash commands replayed with the
cwd they actually ran under:

- **Two or more cd's, not one.** Firing on a single cd into another work tree hit 4,718 commands
  (7.8% of everything), because a session whose cwd is a parent project working in a nested sub-repo
  is structurally identical to one reaching into an unrelated repo, and the first is routine.
- **The landings must span more than one work tree.** Firing on any two cd's hit 344, of which 131
  had every landing inside a single repository - both gits answering about the same thing, so there
  was nothing to warn about.
- **Every landing must be readable.** 1,233 cd targets in the corpus are shell variables, and others
  point at directories that no longer exist. A destination that cannot be resolved cannot be
  attributed to a repo, and a verdict built on a guessed one is invented rather than measured.
  This one has a RECALL cost, unlike the other two, and the cost is recorded here so nobody relaxes
  it without knowing what it buys: silencing a whole call because ONE landing is unreadable gives up
  3 true positives across 60,606 commands, against the 113 it keeps. That trade was accepted on
  purpose - a guessed attribution is worse than a miss, because it is wrong with confidence.

Together those leave 113 firings, 0.186% of the corpus, each one landing in two distinct real work
trees at the moment it fires.

NOT GUARDED, deliberately: the incident that motivated this hook - `cd RESEARCH && ... && echo
agentdag && git log`, whose output read as a check on a different repo - sits inside the removed
7.8%. Its hazard was the LABEL disagreeing with the cd, which is narrative rather than structure, so
no structural guard separates it from thousands of benign commands. A test pins that, so the
single-cd arm is not re-added on the belief that it covers this.

ALSO NOT GUARDED, and now PRICED rather than assumed: the CROSS-CALL shape, where one call cd's
somewhere and a LATER call runs a bare git with no cd of its own, relying on the persisted cwd. This
hook cannot see it - it holds no session state and reads one command at a time - and the fact that
motivated the hook asked for it. Replayed over the same corpus (65,810 commands by then, grown from
the 60,517 above), an arm firing on "a git in a call containing no cd and no -C" speaks on 2,961
commands: 4.499% of everything, one command in 22, against the shipped arm's 0.186%. Sampled, they
are ordinary single-repo work whose cwd was already correct. The RATE is what rejects it; precision
is not the deciding number for this hazard, because a plausible-but-wrong ANSWER is never followed
by a block, so the 0.81% guard_replay reports is measuring refusals this guard was never going to
cause. Recorded so the arm is not re-proposed as unmeasured. A stateful version tracking "where the
last cd landed" is worse than none: the harness sometimes RESETS the cwd between calls, so it would
answer confidently and wrongly.

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


_UNKNOWABLE = re.compile(r"[$`<>|\n*?]")          # a destination no static read can resolve


def _repo_root(path):
    """The work tree `path` belongs to, or None. Walks up looking for a `.git` entry.

    A linked worktree carries a `.git` FILE rather than a directory, so `exists` is the right test:
    two worktrees of one repository are two work trees here, which is what the caller is asking.
    """
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
    """The nudge text when a later git answers about a DIFFERENT work tree, else None.

    Silent unless the call's cd targets span more than one work tree: two cd's inside a single
    repository leave both gits answering about the same thing. Silent too when any destination is
    unreadable - a shell variable, or a path that is not there - because a verdict built on a
    guessed destination is invented rather than measured.
    """
    if not command or not isinstance(command, str) or not cwd:
        return None
    masked, spans = _statements(command)
    here, landed = str(cwd), []
    for start, end in spans:
        raw = command[start:end]
        cd_hit = _CD.match(masked[start:end])
        if cd_hit:
            target = raw[cd_hit.start("target"):cd_hit.end("target")]
            if _UNKNOWABLE.search(target):
                return None            # a variable or redirect: where it lands is not readable here
            here = _resolve(target, here)
            landed.append(here)
            continue
        if not _GIT.match(masked[start:end]) or len(landed) < 2:
            continue
        roots = {_repo_root(path) for path in landed}
        if None not in roots and len(roots) > 1:
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
