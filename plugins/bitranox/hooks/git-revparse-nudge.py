#!/usr/bin/env python3
"""PreToolUse(Bash) nudge: `git rev-parse <name>` without --verify echoes the name back.

Given a ref it cannot resolve, a plain `git rev-parse` does not fail - it prints the argument
verbatim and exits 0. So a comparison built on it succeeds against a string that was never a
commit, and the wrong answer is confident and plausible. `--verify -q` makes it resolve or fail.

The informational forms (`--show-toplevel`, `--abbrev-ref`, `--git-dir`, `--is-inside-work-tree`)
answer about the repository rather than resolving a ref, and are exactly what you should be
running when you suspect the cwd is not the repo you think - so they are left alone.

Heredoc bodies are stripped first: prose documenting this footgun must not trip the guard that
teaches it.

NON-BLOCKING: emits additionalContext and exits 0. Fail-open on any error. ASCII only.
"""
from __future__ import annotations

import json
import re
import sys

from shell_text import is_shell_tool, strip_heredoc_bodies

_REV_PARSE = re.compile(r"\bgit\s+rev-parse\b(?P<rest>[^\n;&|]*)")
# Options that either make it safe, or make it a question about the repo rather than a ref.
_SAFE_OPTS = re.compile(
    r"--verify\b|--show-toplevel\b|--abbrev-ref\b|--git-dir\b|--git-common-dir\b"
    r"|--is-inside-work-tree\b|--is-bare-repository\b|--show-prefix\b|--show-cdup\b"
    r"|--absolute-git-dir\b|--path-format\b|--parseopt\b|--sq-quote\b"
)

_NOTICE = (
    "BARE git rev-parse: given a ref it cannot resolve, this does NOT fail - it prints the "
    "argument back verbatim and exits 0, so any comparison built on it succeeds against a string "
    "that was never a commit. Add `--verify -q` so it resolves or fails. And if the answer will "
    "decide anything, put an absolute `cd /full/path &&` in THIS same call: the harness cwd both "
    "persists from an earlier cd and is sometimes reset between calls, so a bare git can answer "
    "confidently from another repository."
)


def notice(command):
    """The nudge text when a ref-resolving rev-parse lacks --verify, else None."""
    if not command or not isinstance(command, str):
        return None
    for match in _REV_PARSE.finditer(strip_heredoc_bodies(command)):
        rest = match.group("rest") or ""
        if _SAFE_OPTS.search(rest):
            continue
        if not rest.strip():
            continue          # `git rev-parse` alone asks nothing about a ref
        return _NOTICE
    return None


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:  # noqa: BLE001 - no/invalid stdin: do nothing
        return 0
    if not isinstance(event, dict) or not is_shell_tool(event.get("tool_name")):
        return 0
    message = notice((event.get("tool_input") or {}).get("command"))
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
