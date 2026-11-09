#!/usr/bin/env python3
"""PreToolUse(Bash|PowerShell) guard: refuse an unbounded `find /`.

Without `-maxdepth` a walk from the filesystem root on this kind of host visits every mount: it
exceeds the Bash tool timeout, gets moved to the background and needs a TaskStop, and the answer
it was after still has not arrived. Searching the roots that can actually hold the file is both
faster and answers the question, so this refuses and names them.

What is refused: a `find` statement with `/` among its starting points and no `-maxdepth`, unless
the statement is wrapped in `timeout`. `-xdev` is not a bound: it only stops at a mount boundary,
and the root filesystem alone is still a full walk. A `find` inside `ssh ...` or another quoted
argument is not read: it runs elsewhere, under that host's own limits. PowerShell's `find` is a
different program and is not judged.

Exit 2 through `shell_text.refuse`; every other path, any error included, exits 0. ASCII only.
"""

import json
import sys

import shell_text
from shell_text import argv_for_match, basename_for_tool, iter_segments, statement_program

__all__ = ["assess", "main"]

_PATH_OPTIONS = frozenset({"-H", "-L", "-P"})
_MESSAGE = (
    "UNBOUNDED FIND: `find /` with no -maxdepth walks every mount and runs past the Bash timeout. "
    "Search a root that can hold the file - the project tree, $HOME, ~/.claude/plugins/cache, "
    "/usr/lib, /etc - or bound it with -maxdepth N or a leading `timeout 30`. -xdev does not "
    "bound the walk."
)


def _roots(args):
    """The starting points of a find invocation: the words before the first expression token."""
    roots = []
    for word in args:
        if word in _PATH_OPTIONS:
            continue
        if word.startswith(("-", "(", "!")):
            break
        roots.append(word)
    return roots


def _walks_root_unbounded(tokens, tool_name):
    at = statement_program(tokens, ("find",), tool_name)
    if at is None or "/" not in _roots(tokens[at + 1:]):
        return False
    if any(token == "-maxdepth" for token in tokens[at + 1:]):
        return False
    return not any(basename_for_tool(word, tool_name) == "timeout" for word in tokens[:at])


def assess(command, tool_name="Bash"):
    """The refusal message for `command`, or None when it may run. PURE."""
    if tool_name != "Bash" or not command or "find" not in command:
        return None
    text = shell_text.strip_heredoc_bodies(command)
    for _at, segment in iter_segments(text, tool_name):
        tokens = argv_for_match(segment.strip(), tool_name)
        if tokens and _walks_root_unbounded(tokens, tool_name):
            return _MESSAGE
    return None


def main():
    try:
        event = json.load(sys.stdin)
    except ValueError:                                   # no or invalid stdin: nothing to judge
        return 0
    if not isinstance(event, dict):
        return 0
    command = (event.get("tool_input") or {}).get("command") or ""
    message = assess(command, event.get("tool_name") or "")
    return shell_text.refuse(message) if message else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:                                    # a broken guard must never wedge a turn
        sys.exit(0)
