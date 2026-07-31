#!/usr/bin/env python3
"""PreToolUse(Bash) nudge for checks that silently report the wrong answer.

A check you write to VERIFY your own work is itself unverified code, and it fails in
the direction that produces a false alarm or a false all-clear - never in a direction
you notice, because you are reading its output to find out what is true.

Two such invocations are mechanically detectable and have each burned a real session.
Both are NUDGES (non-blocking `additionalContext`), not blocks: each has legitimate
uses, and the failure is a wrong ANSWER rather than a dangerous action, so the right
intervention is to tell the model what it is about to misread.

1. `find ... -newermt <relative time>`

   `bfs` (a drop-in `find` shipped as `find` on some systems) REJECTS a relative
   `-newermt` argument: "Invalid timestamp. Supported timestamp formats are ISO
   8601-like". GNU find accepts it. So a poll loop written as

       find "$DIR" -newermt '-3 minutes' | wc -l

   returns 0 on every tick under bfs - not because nothing changed, but because the
   command errored. A backstop built on it reports "NO ACTIVITY, investigate"
   forever, with equal confidence whether the thing it watches is healthy or dead.

2. `pyright` with no interpreter pinned, in a tree that has a virtualenv

   pyright resolves its environment from CONFIGURATION, not from the interpreter that
   launched it, so `.venv/bin/python -m pyright` does NOT analyse `.venv`. Every
   dependency installed only there reports `reportMissingImports`, plus a cascade of
   unknown-type errors. The output looks like a broken codebase and is a broken
   invocation. Fires only when a venv directory is actually present and no
   `--pythonpath` / `--venvpath` / `-p` / `--project` is given.

Pure standard library: no jq, no shell. Reads the PreToolUse event JSON on stdin,
writes `hookSpecificOutput.additionalContext` on stdout, and ALWAYS exits 0 - a nudge
must never wedge a turn, and every error path is swallowed for the same reason.
"""

from __future__ import annotations

import json
import re
import shlex
import sys
from pathlib import Path

# A -newermt value bfs cannot parse. ISO-like stamps are fine; these are not.
_RELATIVE_TIME_RE = re.compile(
    r"""^\s*(
        [-+]\s*\d+            |   # -3 minutes, +2 days
        \d+\s+\w+\s+ago       |   # 3 minutes ago
        yesterday | today | now | tomorrow
    )""",
    re.VERBOSE | re.IGNORECASE,
)

# Pinning the interpreter, in any of the accepted spellings.
_PYRIGHT_PIN_FLAGS = frozenset({"--pythonpath", "--venvpath", "-p", "--project"})

_VENV_DIRS = (".venv", "venv", ".virtualenv")


def _tokens(command: str) -> list[str]:
    """Split a shell line without running it; give up rather than guess."""
    try:
        return shlex.split(command, comments=True)
    except ValueError:
        return []


def find_newermt_relative(tokens: list[str]) -> str | None:
    """Return the offending -newermt value, or None."""
    if not any(t == "find" or t.endswith("/find") for t in tokens):
        return None
    for i, tok in enumerate(tokens):
        if tok == "-newermt" and i + 1 < len(tokens):
            value = tokens[i + 1]
            if _RELATIVE_TIME_RE.match(value):
                return value
    return None


def pyright_without_pinned_interpreter(tokens: list[str], cwd: Path) -> bool:
    """True when pyright runs unpinned in a tree that actually has a virtualenv."""
    if not any(t == "pyright" or t.endswith("/pyright") for t in tokens):
        return False
    if any(t in _PYRIGHT_PIN_FLAGS or t.startswith("--pythonpath=") or t.startswith("--venvpath=") for t in tokens):
        return False
    try:
        return any((cwd / d).is_dir() for d in _VENV_DIRS if d)
    except OSError:
        return False


def build_notice(command: str, cwd: Path) -> str | None:
    """The advisory text for one command, or None when nothing applies."""
    tokens = _tokens(command)
    if not tokens:
        return None
    notes: list[str] = []

    offending = find_newermt_relative(tokens)
    if offending is not None:
        notes.append(
            f"`find -newermt {offending!r}`: a relative timestamp is REJECTED by bfs (shipped as "
            "`find` on this and other systems) - the command errors and prints nothing, so a poll "
            "loop built on it reports 'no activity' whether or not anything changed. Compare "
            "mtimes yourself (`stat -c%Y`, or Python `Path.stat().st_mtime`) against a recorded "
            "baseline, or pass an ISO-8601 timestamp."
        )

    if pyright_without_pinned_interpreter(tokens, cwd):
        notes.append(
            "`pyright` with no interpreter pinned, in a tree that has a virtualenv: pyright takes "
            "its environment from CONFIG, not from the interpreter that launched it, so "
            "`python -m pyright` analyses the ambient interpreter. Every venv-only dependency then "
            "reports reportMissingImports and the output looks like a broken codebase. Add "
            "`--pythonpath <venv>/bin/python`, or set [tool.pyright] venvPath+venv."
        )

    if not notes:
        return None
    body = "\n".join(f"- {n}" for n in notes)
    return (
        "A verification command here can report the wrong answer SILENTLY:\n"
        f"{body}\n"
        "Before trusting any hand-rolled check, run it against a known negative and require it to "
        "say 'different'."
    )


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    try:
        command = str(event.get("tool_input", {}).get("command", ""))
        cwd = Path(str(event.get("cwd") or "."))
        notice = build_notice(command, cwd)
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
