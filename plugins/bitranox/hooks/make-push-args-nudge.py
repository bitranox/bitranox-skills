#!/usr/bin/env python3
"""PreToolUse(Bash|PowerShell) nudge: a bmk commit message with shell metacharacters in ARGS=.

`make push|ship|commit` takes its commit subject from `ARGS=` or trailing words, and both are
pasted into the recipe TEXT, where bash parses them again. On an unquoted recipe (`ship`, and any
older Makefile) a `(` is a syntax error with nothing committed, and a `;` truncates the subject
and runs the rest as a command while the push still goes out. On a quoted recipe make eats a `$`
and a backtick executes. `MSG="..."` is exported to bmk as BMK_COMMIT_MESSAGE and never touches a
command line, so it is the channel for anything beyond plain words (bitranox:devops-bmk).

Fires on: a `make` statement naming one of those targets whose `ARGS=` value, or whose trailing
words after the target, carry one of `; ( ) $ backtick " ' | & < >` or a newline. A message in
`MSG=` alone is the fix and stays quiet; `ARGS=` beside it still fires, because ARGS wins. Other
targets (`make test ARGS="-k (a or b)"`) pass ARGS to a tool where those characters are syntax,
and stay quiet. Heredoc bodies and quoted text are data, not commands.

Replayed over about 186,000 recorded Bash calls (2026-10-29): it fires on 7 (0.004%), which is
every recorded message-target `make` call that used `ARGS=` at all. One was a deliberate probe of
the breakage; the other six passed `ARGS="'...'"`, and all five of their subjects found in the
repos' git log carry the single quotes literally. The `MSG=` channel and plain words
never fired. A first draft fired on 51: 43 correct `MSG=` pushes whose `> log 2>&1` it read as
message words, and one printf log line whose prose followed a `$(...)` inside double quotes. Both
shapes are now skipped (redirections, and a `make` that the aligned quote mask hides).

NON-BLOCKING: emits additionalContext and exits 0. Fail-open on any error. ASCII only.
"""

import json
import re
import sys

from shell_text import (
    argv_for_match,
    blank_heredoc_bodies,
    commands_only_aligned,
    drop_redirections,
    is_shell_tool,
    iter_segments,
    statement_program,
)

_MESSAGE_TARGETS = frozenset({"push", "ship", "commit"})
# make options whose VALUE is the next token, so that token is never a target or a message word.
_VALUE_OPTS = frozenset({"-C", "-f", "-I", "-o", "-W", "--directory", "--file", "--makefile",
                         "--include-dir", "--old-file", "--what-if", "--assume-old",
                         "--assume-new", "--new-file"})
_ASSIGNMENT = re.compile(r"^(?P<name>[A-Za-z_][A-Za-z0-9_]*)=(?P<value>.*)$", re.S)
_PROGRAM_WORD = re.compile(r"(?<![\w.-])make(?![\w.-])")
_METACHARS = re.compile(r"[;()$`\"'|&<>\n]")

_NOTICE = (
    "This bmk commit message carries shell metacharacters in ARGS= (or as trailing words). Both "
    "are pasted into the Makefile recipe and parsed by bash again: on an unquoted recipe (`ship`, "
    "older Makefiles) `(` is a syntax error with nothing committed and `;` truncates the subject "
    "and runs the rest as a command while the push still goes out; on a quoted one make eats `$` "
    "and a backtick executes. Pass the message as MSG=\"...\" (exported as BMK_COMMIT_MESSAGE, "
    "never parsed) with no ARGS= and no trailing words beside it, then read "
    "`git log -1 --format=%s` back. Details: bitranox:devops-bmk."
)


def channel(command, tool_name=None):
    """Which channel carries the metacharacters - "args" or "words" - or None when neither does."""
    if not command or not isinstance(command, str):
        return None
    text = blank_heredoc_bodies(command)
    # The separator walk opens a new segment after a `$(...)` that closes INSIDE a double-quoted
    # string, so prose following it reads as a statement. The aligned mask blanks quoted text in
    # place: a `make` that is not still visible there was never going to run.
    visible = commands_only_aligned(command, tool_name)
    for at, segment in iter_segments(text, tool_name):
        if not _PROGRAM_WORD.search(visible, at, at + len(segment)):
            continue
        found = _segment_channel(argv_for_match(segment, tool_name), tool_name)
        if found:
            return found
    return None


def _segment_channel(argv, tool_name):
    idx = statement_program(argv, ("make",), tool_name)
    if idx is None:
        return None
    target_seen, words, args_value = False, [], None
    # A redirection (`>log`, `2>&1`, `*> log`, a bare `>` and its target) is consumed by the shell
    # before make runs, so it is never part of the message. Read per word, so a QUOTED word that
    # starts with `>` is taken for one too - rare, and a miss rather than a false alarm.
    operands = drop_redirections(argv[idx + 1:])
    index = 0
    while index < len(operands):
        token = operands[index]
        assignment = _ASSIGNMENT.match(token)
        if token in _VALUE_OPTS:
            index += 1                                  # skip the option's value too
        elif assignment:
            if assignment.group("name") == "ARGS":
                args_value = assignment.group("value")
        elif token.startswith("-"):
            pass
        elif not target_seen and token in _MESSAGE_TARGETS:
            target_seen = True
        elif target_seen:
            words.append(token)
        index += 1
    if not target_seen:
        return None
    if args_value is not None and _METACHARS.search(args_value):
        return "args"
    if any(_METACHARS.search(word) for word in words):
        return "words"
    return None


def notice(command, tool_name=None):
    """The nudge text when a bmk message target carries metacharacters outside MSG=, else None."""
    return _NOTICE if channel(command, tool_name) else None


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:  # noqa: BLE001 - no/invalid stdin: do nothing
        return 0
    if not isinstance(event, dict) or not is_shell_tool(event.get("tool_name")):
        return 0
    message = notice((event.get("tool_input") or {}).get("command"), event.get("tool_name"))
    if message:
        sys.stdout.write(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": message,
        }}) + "\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - a broken nudge must never wedge a turn
        sys.exit(0)
