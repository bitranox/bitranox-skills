#!/usr/bin/env python3
"""PreToolUse(Bash|PowerShell) nudge: `tail -N` with two or more files exits 1 on uutils tail.

The obsolete count form (`-1`, `-5f`, `+2`) is accepted by GNU tail with any number of files, but
uutils tail - the coreutils of Ubuntu 26.04 - accepts it with ONE file only. With two or more it
prints "unexpected argument '-1' found" and exits 1. `tail -n N` works everywhere and is the
POSIX spelling.

Why a hook and not a line of prose: the trap sits in a READ-BACK line, chained after the real work
(`run a > a.out; run b > b.out; tail -1 a.out b.out`). Its exit 1 becomes the call's exit code, so
work that succeeded reads as failed. A memory fact recorded it and it recurred anyway.

NUDGE, not a block: on GNU tail the command is correct, and a guard that refuses a working command
teaches the reader to ignore the channel. It emits `additionalContext` and exits 0.

The scan walks TOKENS, never a regex over the whole command: a nested quantifier there backtracks
exponentially on a non-matching line, and a hook that hangs stops the session. Heredoc bodies are
stripped first, because they are data.
"""

import json
import re
import sys

from shell_text import (argv_for_match, basename_for_tool, is_shell_tool, iter_segments,
                        program_word_at, strip_heredoc_bodies)

# One TOKEN, matched whole: `-1`, `+2`, `-5f`, `-1q`, `-10c`. No nested quantifier, and fullmatch
# keeps it from reading the digits inside `-n1` or a file name.
_OBSOLETE_COUNT = re.compile(r"[-+][0-9]+[bcl]?[fqrv]?")
# Options whose value may be the NEXT token. Skipping it keeps `-n 1` from counting `1` as a file.
_TAKES_VALUE = frozenset({"-n", "-c", "-s", "--lines", "--bytes", "--pid", "--sleep-interval",
                          "--max-unchanged-stats"})
# A redirect token: `>`, `2>`, `>>`, `&>`, `<`, with or without its target glued on.
_REDIRECT = re.compile(r"[0-9&]?[<>]")
_PROGRAM = "tail"


def _count_and_files(args):
    """(saw an obsolete count, how many file operands) for the words after `tail`. PURE."""
    obsolete, files, skip, operands_only = False, 0, False, False
    for word in args:
        if skip:
            skip = False
            continue
        if operands_only:
            files += 1
        elif _REDIRECT.match(word):
            skip = word.rstrip("0123456789&<>") == ""  # a bare `>` names its target next
        elif word == "--":
            operands_only = True
        elif _OBSOLETE_COUNT.fullmatch(word):
            obsolete = True
        elif word in _TAKES_VALUE:
            skip = True
        elif word.startswith("-") and word != "-":
            continue
        else:
            files += 1
    return obsolete, files


def notice(command, tool_name=None):
    """The warning text when a statement runs `tail -N` on two or more files, else None."""
    if not command or not isinstance(command, str):
        return None
    tool = tool_name or "Bash"
    try:
        for _at, segment in iter_segments(strip_heredoc_bodies(command), tool_name):
            words = argv_for_match(segment.strip(), tool)
            at = program_word_at(words, tool)
            if at is None or basename_for_tool(words[at], tool).lower() != _PROGRAM:
                continue
            obsolete, files = _count_and_files(words[at + 1:])
            if obsolete and files >= 2:
                return _message(" ".join(words[at:]))
    except Exception:  # noqa: BLE001 - a nudge must never wedge a turn
        return None
    return None


def _message(statement):
    return (
        "`%s` uses tail's obsolete count form (`-N`/`+N`) with TWO OR MORE files. uutils tail (the "
        "coreutils of Ubuntu 26.04) rejects that with exit 1 \"unexpected argument\", and in a "
        "read-back line that exit 1 becomes the call's exit code, so work that succeeded reads as "
        "failed. Write `tail -n 1` (or `tail -n +2`): it works on GNU and uutils alike."
        % statement
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
    command = tool_input.get("command") if isinstance(tool_input, dict) else None
    try:
        text = notice(command, payload.get("tool_name"))
    except Exception:  # noqa: BLE001
        return 0
    if not text:
        return 0
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                             "additionalContext": text}}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
