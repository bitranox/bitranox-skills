#!/usr/bin/env python3
"""PreToolUse(Bash|PowerShell) nudge: a Python whose output can die in its own buffer.

Off a tty, Python's stdout is BLOCK-buffered and flushed only at exit. Usually that is harmless,
because the exit comes and the flush delivers everything. It is not harmless where the process can
be KILLED or left HANGING before that exit while somebody waits on its output:

* over ssh without `-t` - the remote stdout is a pipe, and a timeout or a dropped connection kills
  the remote process unflushed;
* detached into a log file (`run_in_background`, `nohup`, `setsid`), where the log is read while
  the process runs and stays empty for as long as it does.

Then nothing it printed arrives, not even the last line it reached, so a hang hides WHERE it hung.
That happened twice in two months to the same author, and a written rule had not stopped the
second one, which is why this is a hook.

NUDGE, not a block: most such calls finish and lose nothing, so a block would refuse correct
commands. It emits `additionalContext` and exits 0. A Python that already runs unbuffered (`-u`,
alone or in a flag cluster, or `PYTHONUNBUFFERED` anywhere in the command) is quiet, and so is
`ssh -t`, whose remote stdout is a tty.

Heredoc bodies and data-sink statements are stripped before the scan: a body is DATA, and a guard
that reads it fires on the prose documenting the very thing it guards.
"""

import json
import re
import sys

from shell_text import (
    argv_for_match,
    basename_for_tool,
    is_shell_tool,
    iter_segments,
    strip_data_sink_statements,
    strip_heredoc_bodies,
)

# `python`, `python3`, `python3.14`, `python.exe` - by basename, so a venv interpreter by path
# counts and `pythonista` or `python3.log` do not.
_PYTHON = re.compile(r"python(?:\d+(?:\.\d+)*)?(?:\.exe)?", re.IGNORECASE)

# Launchers whose own flags and operands sit between them and the program they run.
_LAUNCHERS = frozenset({
    "nice", "ionice", "timeout", "sudo", "doas", "env", "stdbuf", "nohup", "setsid",
    "chrt", "taskset", "time", "command", "exec",
})
# The launchers that DETACH the run, which is what puts the buffer at risk: its log is read while it
# runs. `timeout` is deliberately not one. It kills only a hang, and replayed over 158,597 recorded
# Bash calls it was 2,320 of 2,526 firings - routine `timeout N python -m pytest` gates whose output
# arrives at their normal exit - so it would have taught the reader to skip this channel. An ssh
# call wrapped in `timeout` is still caught by the ssh rule.
_RISKY_LAUNCHERS = frozenset({"nohup", "setsid"})
_LAUNCHER_SCAN = 6

_KEYWORDS = frozenset({"if", "while", "until", "do", "then", "else", "elif", "{", "!", "("})

# ssh options that take a value as the next token; everything else before the host is a flag.
_SSH_VALUE_OPTS = frozenset("BbcDEeFIiJLlmOoPpQRSWw")

# uv run options whose value is the next token, so the value is not read as the program.
_UV_VALUE_OPTS = frozenset({
    "--python", "-p", "--with", "-w", "--with-requirements", "--with-editable", "--project",
    "--directory", "--extra", "--group", "--env-file", "--package", "--index", "--index-url",
    "--extra-index-url", "--find-links", "-f", "--only-group", "--no-group", "--config-file",
    "--cache-dir", "--exclude-newer", "--color",
})

# Interpreter options whose value is the next token.
_PY_VALUE_OPTS = frozenset({"-W", "-X", "--check-hash-based-pycs"})

# `python -m <mod>` runs that print one line or install something: nothing to lose.
_QUIET_MODULES = frozenset({"pip", "venv", "ensurepip", "virtualenv"})

_REDIRECT = re.compile(r"(?:^|\s)(?:&>>?|\d?>>?)\s*(?!&)\S|\|\s*tee\b")


def _skip_prefix(tokens, idx):
    """Index past loop keywords and `VAR=value` assignments."""
    while idx < len(tokens) and (
        tokens[idx] in _KEYWORDS or ("=" in tokens[idx] and not tokens[idx].startswith("-"))
    ):
        idx += 1
    return idx


def _is_python(token, tool_name):
    return bool(_PYTHON.fullmatch(basename_for_tool(token, tool_name)))


def _python_buffered(args):
    """True when a Python called with `args` (after the interpreter) runs buffered and matters.

    False for `-u`, for a flag cluster holding `u`, and for the calls that print nothing worth
    keeping (`--version`, `-m pip`). Scanning stops at the first operand, `-c` or `-m`, so code
    after `-c` is never read as an interpreter flag.
    """
    idx = 0
    while idx < len(args):
        arg = args[idx]
        if arg in ("-V", "--version", "-h", "--help"):
            return False
        if arg == "-m":
            return idx + 1 < len(args) and args[idx + 1] not in _QUIET_MODULES
        if arg == "-c" or arg == "-" or not arg.startswith("-"):
            return True
        if arg in _PY_VALUE_OPTS:
            idx += 2
            continue
        if not arg.startswith("--") and "u" in arg[1:]:
            return False
        idx += 1
    return True


def _uv_run_target(tokens, idx):
    """(index of the program `uv run` starts, or None) for `tokens[idx] == 'uv'`."""
    if idx + 1 >= len(tokens) or tokens[idx + 1] != "run":
        return None
    at = idx + 2
    while at < len(tokens) and tokens[at].startswith("-"):
        at += 2 if tokens[at] in _UV_VALUE_OPTS else 1
    return at if at < len(tokens) else None


def _ssh_remote(tokens, idx):
    """(remote command text or None, whether `-t` gave it a tty) for `tokens[idx] == 'ssh'`."""
    at, tty = idx + 1, False
    while at < len(tokens) and tokens[at].startswith("-") and len(tokens[at]) > 1:
        cluster, takes_next = tokens[at][1:], False
        # Read the cluster the way ssh's getopt does: flags until the first option that takes a
        # value, whose value is the rest of the cluster or, when nothing is left, the next token.
        # So the `t` in `-oStrictHostKeyChecking=no` is part of a value, not a tty request.
        for pos, char in enumerate(cluster):
            if char in _SSH_VALUE_OPTS:
                takes_next = pos == len(cluster) - 1
                break
            tty = tty or char == "t"
        at += 2 if takes_next else 1
    at += 1                                         # the host
    return (" ".join(tokens[at:]) if at < len(tokens) else None), tty


def _scan(command, tool_name, *, remote, background, depth=0):
    """'python' / 'uv' for the first at-risk buffered Python in `command`, else None."""
    if depth > 3 or not command:
        return None
    text = strip_data_sink_statements(strip_heredoc_bodies(command), tool_name)
    for _, segment in iter_segments(text, tool_name):
        found = _scan_segment(segment, tool_name, remote=remote, background=background,
                              depth=depth)
        if found:
            return found
    return None


def _scan_segment(segment, tool_name, *, remote, background, depth):
    tokens = argv_for_match(segment, tool_name)
    idx = _skip_prefix(tokens, 0)
    risky = remote or (background and bool(_REDIRECT.search(segment)))
    seen = 0
    while idx < len(tokens) and basename_for_tool(tokens[idx], tool_name) in _LAUNCHERS:
        risky = risky or basename_for_tool(tokens[idx], tool_name) in _RISKY_LAUNCHERS
        nxt = idx + 1
        while nxt < len(tokens) and seen < _LAUNCHER_SCAN and not _runs_something(
                tokens[nxt], tool_name):
            nxt, seen = nxt + 1, seen + 1
        idx = nxt
    if idx >= len(tokens):
        return None
    program = basename_for_tool(tokens[idx], tool_name)
    if program == "ssh":
        remote_text, tty = _ssh_remote(tokens, idx)
        if tty or not remote_text:
            return None
        return _scan(remote_text, tool_name, remote=True, background=False, depth=depth + 1)
    if program in ("bash", "sh") and idx + 2 < len(tokens) and tokens[idx + 1] == "-c":
        return _scan(tokens[idx + 2], tool_name, remote=risky, background=background,
                     depth=depth + 1)
    if not risky:
        return None
    if _is_python(tokens[idx], tool_name):
        return "python" if _python_buffered(tokens[idx + 1:]) else None
    if program == "uv":
        target = _uv_run_target(tokens, idx)
        if target is None:
            return None
        if _is_python(tokens[target], tool_name):
            return "python" if _python_buffered(tokens[target + 1:]) else None
        return "uv" if tokens[target].endswith(".py") else None
    return None


def _runs_something(token, tool_name):
    """True when a token past a launcher is a program this nudge looks at."""
    name = basename_for_tool(token, tool_name)
    return bool(_PYTHON.fullmatch(name)) or name in ("uv", "ssh", "bash", "sh") \
        or name in _LAUNCHERS


def notice(command, tool_name=None, *, background=False):
    """The warning text when this command runs an at-risk buffered Python, else None.

    `background` is the tool call's `run_in_background`: a detached run writing a log is at risk,
    a detached run whose output goes to the task's own pipe is captured at exit and is not.
    """
    if not command or not isinstance(command, str) or "PYTHONUNBUFFERED" in command:
        return None
    try:
        kind = _scan(command, tool_name, remote=False, background=background)
    except Exception:  # noqa: BLE001 - a nudge must never wedge a turn
        return None
    if not kind:
        return None
    fix = ("prefix it with `PYTHONUNBUFFERED=1` (`uv run <script>.py` takes no `-u`)"
           if kind == "uv" else "run it as `python -u`, or set `PYTHONUNBUFFERED=1`")
    return (
        "This Python's stdout is not a terminal and the process may be killed or hang before it "
        "exits (over ssh without -t, or detached into a log it is read from). Off a tty Python "
        "BLOCK-buffers and flushes only at exit, so whatever it printed is lost with it - you see "
        "nothing, not even the last line it reached, which hides WHERE it hung. To keep the "
        f"output, {fix}."
    )


def main(raw=None) -> int:
    """Read the hook event, emit additionalContext when the shape matches. Always exits 0."""
    try:
        payload = json.loads(raw if raw is not None else sys.stdin.read() or "{}")
    except (ValueError, TypeError):
        return 0
    if not isinstance(payload, dict) or not is_shell_tool(payload.get("tool_name")):
        return 0
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return 0
    try:
        text = notice(tool_input.get("command"), payload.get("tool_name"),
                      background=tool_input.get("run_in_background") is True)
    except Exception:  # noqa: BLE001
        return 0
    if not text:
        return 0
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                             "additionalContext": text}}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
