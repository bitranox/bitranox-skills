#!/usr/bin/env python3
"""Warn when a gated verb shares one Bash command with the prep that produces its input.

A PreToolUse gate judges the WHOLE command before any statement runs. So when a single command both
writes a file (a heredoc, a redirect) and then runs a verb a gate may block, a block discards the
write too: the retry fails on a missing `-F` input and points at the wrong cause, which is a
different and much more confusing failure than the one the gate meant to report.

Recorded six times in this store (`feedback-repo-gate-pre-evaluates-the-pending-commit-command`).
Prose stopped working at two, so this is the escalation - a signal at the moment of the mistake.

NON-BLOCKING by construction: it emits `additionalContext` and exits 0. Blocking here would add a
second block to a command that may be perfectly fine, and a hook must never wedge a turn.

The gated-verb scan runs over the command with HEREDOC BODIES STRIPPED, because a body is data: a
guard that reads it fires on prose documenting the very footgun it guards.
"""
from __future__ import annotations

import json
import re
import sys

# Shared with the other command-scanning guards - a heredoc body is DATA, not a command.
from shell_text import strip_heredoc_bodies

# Verbs a PreToolUse gate in this plugin can block. Deliberately short: a false nudge on a safe
# command teaches the reader to ignore the channel, which costs more than the miss it prevents.
# re.M matters: a NEWLINE separates statements just as `;` does, and the verb usually sits on its
# own line under a heredoc terminator. Without it the common shape is invisible.
_GATED = re.compile(r"(?:^|[;&|]|\b(?:&&|\|\|)\s*)\s*git\s+(?:commit|push|tag)\b", re.M)

# A write that CREATES the file a later statement reads. Both shapes seen in practice.
_HEREDOC_TO_FILE = re.compile(r"""(?:^|[;&|]|\bcat\b)[^\n<>]*?>\s*(?P<f>[^\s;&|<>]+)\s*<<-?\s*['"]?\w+""")
_REDIRECT_TO_FILE = re.compile(r"""\b(?:printf|echo|tee)\b[^\n;&|]*?>\s*(?P<f>[^\s;&|<>]+)""")


def written_files(command: str):
    """Files this command CREATES, in order. Heredoc openers count; the bodies are not scanned."""
    out = []
    for rx in (_HEREDOC_TO_FILE, _REDIRECT_TO_FILE):
        for m in rx.finditer(command or ""):
            f = m.group("f")
            if f and f not in out:
                out.append(f)
    return out


def notice(command):
    """The warning text when this command co-locates prep with a gated verb, else None."""
    if not command or not isinstance(command, str):
        return None
    written = written_files(command)
    if not written:
        return None
    # Strip bodies BEFORE looking for the gated verb: a heredoc that merely documents `git commit`
    # is prose, and nudging on it is how a guard blocks its own documentation.
    if not _GATED.search(strip_heredoc_bodies(command)):
        return None
    return (
        "This command WRITES %s and then runs a gated verb (git commit/push/tag) in the SAME "
        "command. A PreToolUse gate judges the whole command before any statement runs, so if it "
        "blocks, that file is never written and the retry fails on a missing input - pointing at "
        "the wrong cause. Write the file in its OWN earlier command, then run the gated verb. "
        "(Recorded six times: feedback-repo-gate-pre-evaluates-the-pending-commit-command.)"
        % ", ".join(written)
    )


def main(raw=None) -> int:
    """Read the hook event, emit additionalContext when the shape matches. Always exits 0."""
    try:
        payload = json.loads(raw if raw is not None else sys.stdin.read() or "{}")
    except (ValueError, TypeError):
        return 0
    if not isinstance(payload, dict) or payload.get("tool_name") != "Bash":
        return 0
    tool_input = payload.get("tool_input")
    command = tool_input.get("command") if isinstance(tool_input, dict) else None
    try:
        text = notice(command)
    except Exception:  # noqa: BLE001 - a nudge must never wedge a turn
        return 0
    if not text:
        return 0
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                             "additionalContext": text}}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
