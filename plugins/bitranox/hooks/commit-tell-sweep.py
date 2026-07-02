#!/usr/bin/env python3
"""PreToolUse(Bash) guard against AI-writing typographic / invisible tells in a git
commit / merge / tag MESSAGE passed inline.

The `tell-sweep` PostToolUse hook catches tells in prose FILES, but a commit message
(`git commit -m "..."`) is not a file edit, so it slips through - and a commit message is
exactly where an em-dash or a curly quote leaks into permanent git history. This hook scans
the inline message of any git command (`-m`/`--message`, or the file named by `-F`/`--file`)
using the SAME `tell_chars.RANGES`, and BLOCKS the commit before it runs so the message can be
fixed. Tells inside backtick code spans are ignored (a message that references the character
itself in backticks is fine).

It cannot see an editor-composed message (a bare `git commit` opens $EDITOR after the tool
returns) - that path relies on the humanizer skill; the inline `-m`/`-F` form is the common
Claude Code case and the one this closes.

Pure standard library. Reads the PreToolUse event JSON on stdin. Exit 2 blocks the call and
shows stderr to the model; every other path (including any error) exits 0, so a broken guard
never wedges a turn.
"""
import json
import shlex
import sys
from pathlib import Path

import tell_chars


def _messages(command):
    """Inline commit/merge/tag messages in a git command: the values of -m/--message and the
    contents of the file named by -F/--file. Empty unless the command is a git command."""
    try:
        toks = shlex.split(command)
    except ValueError:
        return []
    if "git" not in toks:
        return []
    msgs, i = [], 0
    while i < len(toks):
        t = toks[i]
        if t in ("-m", "--message") and i + 1 < len(toks):
            msgs.append(toks[i + 1]); i += 2; continue
        if t.startswith("--message="):
            msgs.append(t.split("=", 1)[1])
        elif t.startswith("-m") and len(t) > 2:            # attached form: -m"msg"
            msgs.append(t[2:])
        elif t in ("-F", "--file") and i + 1 < len(toks):
            try:
                msgs.append(Path(toks[i + 1]).read_text(encoding="utf-8", errors="replace"))
            except OSError:
                pass
            i += 2; continue
        elif t.startswith("--file="):
            try:
                msgs.append(Path(t.split("=", 1)[1]).read_text(encoding="utf-8", errors="replace"))
            except OSError:
                pass
        i += 1
    return msgs


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:
        return 0
    command = (event.get("tool_input") or {}).get("command") or ""
    hits = []
    for msg in _messages(command):
        hits += tell_chars.find_tell_lines(msg)
    if not hits:
        return 0
    sys.stderr.write(
        "AI-writing tell(s) in the git message (em/en-dash, curly quote, ellipsis, NBSP, "
        "ZWSP, BOM, etc.). Rewrite with ASCII (use - , . : () ...) before committing:\n"
    )
    sys.stderr.write("\n".join(hits[:20]) + "\n")
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
