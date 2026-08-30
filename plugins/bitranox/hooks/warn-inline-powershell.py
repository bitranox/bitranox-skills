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

Text that the shell will not execute is removed before matching - heredoc bodies, and statements
whose program stores or prints its argument rather than running it. Both strips are shared with the
other command-scanning guards rather than copied here, because two private copies had already
drifted apart once. The cost of a false fire here is one extra line of context, never a blocked
command.
"""
from __future__ import annotations

import json
import re
import sys

from shell_text import strip_data_sink_statements, strip_heredoc_bodies

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
    "Wrap that pair in a script of your own once - syntax-check the .ps1 with `pwsh -NoProfile "
    "-Command \"$null = [ScriptBlock]::Create((Get-Content -Raw <file>))\"`, then scp it and run "
    "it with -File - so you are not hand-rolling the copy every time. Detail: bitranox:compuse-ssh."
)


def _strip_data_regions(command: str, tool_name=None) -> str:
    """Every DATA region the shell will not execute - heredoc bodies AND quoted arguments.

    Without this the nudge fires on its own documentation and on its own test fixtures: a heredoc
    that WRITES an example of the wrong form is not an instance of the wrong form. Measured while
    hardening this hook - appending a test whose fixture string contained
    `ssh host powershell -Command ...` tripped it.

    Heredoc bodies and DATA-SINK STATEMENTS - deliberately not `commands_only`, which also masks
    quoted strings. This hook's whole subject is a command inside a QUOTED ARGUMENT that ssh
    executes remotely, so masking quotes deletes the thing it exists to find: measured, `ssh host
    \'powershell -command "Get-Process"\'` stopped firing entirely and took six tests with it.

    The sink strip is the right instrument for the other half, because it asks a different question
    than the mask does. Not "is this text quoted?" - the ssh argument is quoted too - but "which
    program does the quote belong to?". `echo` and `git commit` store or print their argument;
    `ssh` runs it. So `echo \'ssh host powershell -command x\'` and a commit message describing the
    footgun are now silent, while the ssh form is untouched.
    """
    return strip_data_sink_statements(strip_heredoc_bodies(command), tool_name)


def _powershell_invocation(command: str) -> str | None:
    """The text of the PowerShell invocation itself, or None.

    Both flag searches used to run over the WHOLE command line, which is wrong in both directions:
    `ssh win 'powershell.exe job.ps1' && wc -c out.txt` took `wc`'s `-c` as PowerShell's -Command
    and warned about a footgun nobody wrote, while `ssh -f win '...'` took SSH's backgrounding
    flag as PowerShell's -File and went SILENT on the exact inline -Command shape this hook
    exists to catch. The span runs from the shell name to the end of its own statement.
    """
    m = _SHELL_RX.search(command)
    if not m:
        return None
    rest = command[m.start():]
    for sep in ("&&", chr(124) + chr(124), ";", "\n"):
        cut = rest.find(sep)
        if cut != -1:
            rest = rest[:cut]
    return rest


def build_notice(command: str, tool_name=None) -> str | None:
    """The nudge text, or None. PURE over the command string - no IO, no environment.

    `tool_name` picks the argv split the sink strip uses; see `shell_text.split_for_tool` for why
    the TOOL and not the host decides it.
    """
    if not command:
        return None
    command = _strip_data_regions(command, tool_name)
    if not _SSH_RX.search(command) or not _SHELL_RX.search(command):
        return None
    # Both flag tests must look at the PowerShell call, not the whole line - see
    # `_powershell_invocation` for the two directions this was wrong in.
    invocation = _powershell_invocation(command)
    if invocation is None:
        return None
    if _FILE_FLAG_RX.search(invocation):
        return None                                   # already the -File form this nudge asks for
    if not _COMMAND_FLAG_RX.search(invocation):
        return None                                   # no command string to be mangled
    return _NOTICE


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    try:
        notice = build_notice(str((event.get("tool_input") or {}).get("command") or ""),
                              event.get("tool_name"))
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
