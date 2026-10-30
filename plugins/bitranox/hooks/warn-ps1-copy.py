#!/usr/bin/env python3
"""PreToolUse(Bash|PowerShell) nudge: a local .ps1 copied to a remote host to run there.

A hand-written .ps1 that is copied over and run with `-File` meets its first parser on the REMOTE
host. A syntax error then surfaces as a remote failure, after the copy and often after a partial
run, instead of before anything left this machine. The recorded miss was exactly that: an scp'd
script run with -File, never syntax-checked locally. `warn-inline-powershell` cannot see it,
because it fires only on an inline `-Command` string.

The shapes that count as a copy of a LOCAL .ps1 to a REMOTE host:

* `scp` / `rsync` whose last operand is remote (`[user@]host:path`, `host::module`, a `scp://` or
  `rsync://` URL) and one of whose sources is a local path ending in `.ps1`. Option values (`-i`,
  `-P`, `-o`, `-e`, `--exclude ...`) are skipped, so `--exclude '*.ps1'` is not a source.
* `ssh` reading a local .ps1 on stdin, by `< x.ps1` or by `cat x.ps1 | ssh ...`: whether the
  remote side writes it to a file or feeds it to `powershell -Command -`, the script runs there
  with no local parse first.

A single-letter "host" is a Windows drive (`C:/temp`), not a host, so it reads as local.

This is a NUDGE, never a block: it emits `hookSpecificOutput.additionalContext` and exits 0 on
every path. A command that already syntax-checks a script in the same call
(`[ScriptBlock]::Create`, `[Parser]::ParseFile`/`ParseInput`, `Invoke-ScriptAnalyzer`) is quiet;
a check made in an EARLIER call cannot be seen from here, which is the price of a stateless nudge.

Heredoc bodies and data-sink statements (`echo`, a commit message) are stripped before the scan,
with the helpers the other command-scanning hooks share, so prose describing the shape is silent.
"""

import json
import re
import sys

from shell_text import (
    argv_for_match,
    basename_for_tool,
    drop_redirections,
    is_shell_tool,
    iter_segments,
    statement_program,
    strip_data_sink_statements,
    strip_heredoc_bodies,
)

_PS1 = re.compile(r"\.ps1$", re.IGNORECASE)

# `[user@]host:path` with a host of two or more characters (so `C:/temp` stays a local drive),
# a bracketed IPv6 literal, `host::module` (rsync daemon), or a URL scheme scp/rsync accept.
_REMOTE = re.compile(
    r"^(?:(?:scp|sftp|rsync)://"
    r"|(?:[^@/\\\s]+@)?(?:\[[^\]/]+\]|[^/\\:\s\[]{2,}):)",
    re.IGNORECASE,
)

# A local syntax check of the script, written in the same command as the copy.
_ALREADY_CHECKED = re.compile(
    r"ScriptBlock\]::Create|Parser\]::Parse(?:File|Input)|Invoke-ScriptAnalyzer", re.IGNORECASE
)

_COPIERS = frozenset({"scp", "rsync"})
_PROGRAMS = frozenset({"scp", "rsync", "ssh", "sshpass"})
_PIPE_SOURCES = frozenset({"cat", "type", "get-content", "gc"})

# scp options taking a value: -c cipher, -D sftp path, -F config, -i key, -J jump, -l limit,
# -o option, -P port, -S program, -X sftp option. Every other letter is a flag.
_SCP_VALUE_OPTS = frozenset("cDFiJloPSX")
# rsync short options taking a value: -e rsh, -f filter, -B block size, -T temp dir, -M remote opt.
_RSYNC_VALUE_OPTS = frozenset("efBTM")
_RSYNC_LONG_VALUE_OPTS = frozenset({
    "--rsh", "--exclude", "--include", "--filter", "--exclude-from", "--include-from",
    "--files-from", "--rsync-path", "--partial-dir", "--temp-dir", "--compare-dest",
    "--copy-dest", "--link-dest", "--chmod", "--chown", "--log-file", "--log-file-format",
    "--password-file", "--port", "--timeout", "--contimeout", "--bwlimit", "--max-size",
    "--min-size", "--block-size", "--backup-dir", "--suffix", "--out-format", "--info",
    "--debug", "--usermap", "--groupmap", "--sockopts", "--outbuf", "--remote-option",
    "--modify-window", "--iconv", "--checksum-choice", "--compress-choice",
    "--compress-level", "--skip-compress", "--max-delete", "--stop-after", "--stop-at",
    "--address", "--protocol", "--checksum-seed", "--early-input",
})
# sshpass options taking a value; the program it runs follows them.
_SSHPASS_VALUE_OPTS = frozenset({"-f", "-d", "-p", "-P"})

_NOTICE = (
    "PS1 COPIED TO A REMOTE HOST: this sends a local .ps1 to another machine to run there, so its "
    "first parse happens on the REMOTE side and a syntax error surfaces only after the copy, "
    "sometimes after a partial run. Prefer pwshpy (bitranox:coding-python-pwshpy): typed Python "
    "over native bindings, with real exceptions and exit codes and no .ps1 to break. If it must "
    "stay a .ps1, syntax-check it locally first: `pwsh -NoProfile -Command \"$null = "
    "[ScriptBlock]::Create((Get-Content -Raw <file>))\"` - a parse error then fails here, before "
    "anything is copied."
)


def _is_remote(operand):
    return bool(_REMOTE.match(operand))


def _is_local_ps1(operand):
    return bool(_PS1.search(operand)) and not _is_remote(operand)


def _scp_operands(args):
    """The non-option operands of an scp call, getopt-style: a value option ends its cluster."""
    operands, at = [], 0
    while at < len(args):
        arg = args[at]
        at += 1
        if arg == "--":
            return operands + args[at:]
        if not arg.startswith("-") or len(arg) == 1:
            operands.append(arg)
            continue
        for pos, char in enumerate(arg[1:]):
            if char in _SCP_VALUE_OPTS:
                at += 1 if pos == len(arg) - 2 else 0     # value is the next token or the rest
                break
    return operands


def _rsync_operands(args):
    """The non-option operands of an rsync call; long options with a separate value skip it."""
    operands, at = [], 0
    while at < len(args):
        arg = args[at]
        at += 1
        if arg == "--":
            return operands + args[at:]
        if arg.startswith("--"):
            at += 1 if arg in _RSYNC_LONG_VALUE_OPTS else 0
        elif arg.startswith("-") and len(arg) > 1:
            for pos, char in enumerate(arg[1:]):
                if char in _RSYNC_VALUE_OPTS:
                    at += 1 if pos == len(arg) - 2 else 0
                    break
        else:
            operands.append(arg)
    return operands


def _copies_ps1_out(program, args):
    """True when an scp/rsync call with `args` sends a local .ps1 to a remote destination."""
    operands = _scp_operands(args) if program == "scp" else _rsync_operands(args)
    if len(operands) < 2 or not _is_remote(operands[-1]):
        return False
    return any(_is_local_ps1(source) for source in operands[:-1])


def _stdin_is_ps1(tokens):
    """True when the statement's stdin is redirected from a .ps1 (`< x.ps1` or `<x.ps1`)."""
    for at, token in enumerate(tokens):
        if token in ("<", "0<"):
            target = tokens[at + 1] if at + 1 < len(tokens) else ""
        elif re.match(r"^0?<(?![<&>])", token):
            target = token.split("<", 1)[1]
        else:
            continue
        if _PS1.search(target):
            return True
    return False


def _program(tokens, tool_name):
    """(program basename, index) of the scp/rsync/ssh the statement runs, through sshpass."""
    idx = statement_program(tokens, _PROGRAMS, tool_name)
    if idx is None:
        return None, None
    name = basename_for_tool(tokens[idx], tool_name).lower()
    if name != "sshpass":
        return name, idx
    at = idx + 1
    while at < len(tokens) and tokens[at].startswith("-"):
        at += 2 if tokens[at] in _SSHPASS_VALUE_OPTS else 1
    if at >= len(tokens):
        return None, None
    inner = basename_for_tool(tokens[at], tool_name).lower()
    return (inner, at) if inner in _COPIERS | {"ssh"} else (None, None)


def _pipes_ps1(segment, tool_name):
    """True when `segment` is `cat x.ps1` (or Get-Content/type) - a .ps1 written to a pipe."""
    tokens = drop_redirections(argv_for_match(segment, tool_name))
    if not tokens or basename_for_tool(tokens[0], tool_name).lower() not in _PIPE_SOURCES:
        return False
    return any(_PS1.search(t) for t in tokens[1:] if not t.startswith("-"))


def _segment_fires(segment, piped_from_ps1, tool_name):
    tokens = argv_for_match(segment, tool_name)
    program, idx = _program(tokens, tool_name)
    if program in _COPIERS:
        return _copies_ps1_out(program, drop_redirections(tokens[idx + 1:]))
    if program == "ssh":
        return piped_from_ps1 or _stdin_is_ps1(tokens[idx + 1:])
    return False


def _scan(text, tool_name):
    previous, previous_end = None, 0
    for offset, segment in iter_segments(text, tool_name):
        gap = text[previous_end:offset].strip()
        piped = previous is not None and gap in ("|", "|&") and _pipes_ps1(previous, tool_name)
        if _segment_fires(segment, piped, tool_name):
            return True
        previous, previous_end = segment, offset + len(segment)
    return False


def notice(command, tool_name=None):
    """The nudge text when `command` copies a local .ps1 to a remote host, else None.

    PURE over the command string. `tool_name` picks the argv rules (`Bash` is POSIX, `PowerShell`
    is a Windows command line); see `shell_text.split_for_tool`.
    """
    if not command or not isinstance(command, str) or ".ps1" not in command.lower():
        return None
    if _ALREADY_CHECKED.search(command):
        return None
    # No tool name means the Bash reading. The shared splitter treats a missing name as neither
    # shell, which keeps `\<newline>` as a statement break: replayed, an scp written over three
    # continuation lines went silent when called without the tool name the hook event carries.
    tool_name = tool_name or "Bash"
    try:
        text = strip_data_sink_statements(strip_heredoc_bodies(command), tool_name)
        return _NOTICE if _scan(text, tool_name) else None
    except ValueError:  # an unparseable fragment; the shim keeps any other crash at exit 0
        return None


def main() -> int:
    """Read the hook event, emit additionalContext when the shape matches. Always exits 0."""
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    if not isinstance(event, dict) or not is_shell_tool(event.get("tool_name")):
        return 0
    tool_input = event.get("tool_input")
    if not isinstance(tool_input, dict):
        return 0
    text = notice(tool_input.get("command"), event.get("tool_name"))
    if text:
        json.dump(
            {"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": text}},
            sys.stdout,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
