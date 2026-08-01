#!/usr/bin/env python3
"""PreToolUse(Bash) nudge: remote PowerShell passed inline as `-Command` over SSH.

`ssh <host> 'powershell -Command "... | ..."'` is handed to the Windows side through `cmd.exe`,
which consumes pipes and quotes before PowerShell ever parses the string. The command does not
error; it runs a MANGLED version of what you wrote, so the output looks like a real result and the
mistake surfaces later as wrong data. Escaping harder does not fix it - the mangling happens in a
layer you are not quoting for.

Write the script to a `.ps1` file and run it with `-File`, which passes the file path instead of a
command string and so has nothing for `cmd.exe` to eat. It also gets you local syntax checking and
a diff-able artifact.

This is a NUDGE, never a block: it emits `hookSpecificOutput.additionalContext`, which is what
reaches the model (an exit-0 hook's stdout and stderr do not). Every failure path returns 0.

Known limit, stated rather than hidden: the command text is matched as a whole, so a heredoc that
merely DOCUMENTS this footgun can trip it. Two shipped guards carry heredoc-stripping helpers that
have since diverged from each other, so this file deliberately does not add a third copy. The cost
of a false fire here is one extra line of context, never a blocked command.
"""
from __future__ import annotations

import json
import re
import sys

# `pwsh` is PowerShell 7+; both take -Command/-c and both are reached the same way over ssh.
_SHELL_RX = re.compile(r"\b(?:powershell(?:\.exe)?|pwsh(?:\.exe)?)\b", re.IGNORECASE)
_SSH_RX = re.compile(r"\bssh\b", re.IGNORECASE)
# -Command / -c introduce a command STRING. PowerShell accepts unambiguous prefixes (-Comm, -Com).
_COMMAND_FLAG_RX = re.compile(r"(?<![\w-])-(?:c|com|comm|comma|comman|command)(?![\w-])", re.IGNORECASE)
_FILE_FLAG_RX = re.compile(r"(?<![\w-])-(?:f|fi|fil|file)(?![\w-])", re.IGNORECASE)

_NOTICE = (
    "INLINE REMOTE POWERSHELL: this sends a PowerShell command STRING through ssh, where the "
    "Windows side hands it to cmd.exe first. cmd.exe consumes the pipes and quotes before "
    "PowerShell parses anything, so the command does not fail - it runs a MANGLED version and "
    "returns output that looks real. More escaping does not help, because the mangling happens in "
    "a layer you are not quoting for.\n"
    "Write the script to a .ps1 file, copy it over, and run it with -File <path>: a file path has "
    "nothing for cmd.exe to eat, and you get local syntax checking plus an artifact you can diff. "
    "Detail: bitranox:compuse-ssh."
)


def build_notice(command: str) -> str | None:
    """The nudge text, or None. PURE over the command string - no IO, no environment."""
    if not command:
        return None
    if not _SSH_RX.search(command) or not _SHELL_RX.search(command):
        return None
    if _FILE_FLAG_RX.search(command):
        return None                                   # already the -File form this nudge asks for
    if not _COMMAND_FLAG_RX.search(command):
        return None                                   # no command string to be mangled
    return _NOTICE


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    try:
        notice = build_notice(str((event.get("tool_input") or {}).get("command") or ""))
        if notice:
            json.dump(
                {"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": notice}},
                sys.stdout,
            )
    except Exception:  # noqa: BLE001 - a nudge must never wedge a turn
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
