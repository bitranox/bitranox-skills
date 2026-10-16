#!/usr/bin/env python3
"""PreToolUse(Bash|PowerShell) nudge: name bitranox:devops-bmk the first time a session runs a bmk gate.

A bmk gate (`make test`, `make push`, a bump or a release in a project whose Makefile bmk wrote)
is usually run as the last step of unrelated work, so the devops-bmk skill is not loaded when its
output needs reading. Its failure modes look like defects in the change being gated: a stage that
fails with no captured output, a tool env rebuilt under a running gate, a Makefile and dependency
floors rewritten by the gate itself. The prompt router never sees that moment because the command
is issued mid-turn; the command is the only signal, so this hook watches for it.

Fires on: `make <gate target>` where the Makefile in the directory the command runs in starts with
bmk's `# BMK MAKEFILE` header (the cwd, a leading `cd`, or `make -C <dir>`), and on running `bmk`
or `uvx bmk...` directly. Heredoc bodies are stripped first, and only the program a statement
actually runs counts, so prose and commit messages that mention `make test` stay silent.

NON-BLOCKING: emits additionalContext once per session and exits 0. Fail-open on any error.
"""

import json
import os
import sys

from shell_text import (
    argv_for_match, basename_for_tool, directory_change, is_rooted, is_shell_tool, iter_segments,
    statement_program, strip_heredoc_bodies,
)

_GATE_TARGETS = frozenset({
    "test", "test-all", "testintegration", "push", "deps", "release",
    "bump", "bump-patch", "bump-minor", "bump-major",
})
_PROGRAMS = frozenset({"make", "bmk", "uvx"})
_HEADER = "# BMK MAKEFILE"
_MARKER = ".bmk-gate-nudged"

_NOTICE = (
    "This runs a bmk gate. Load bitranox:devops-bmk (Skill tool) before acting on its result: it "
    "documents what bmk changes in the working tree (the Makefile and dependency floors), the "
    "project venv it syncs, and the reds that come from bmk's own environment rather than from "
    "the change being gated. Said once per session."
)


def _is_bmk_makefile(directory):
    """True when `directory` holds a Makefile whose first line is bmk's header."""
    if not directory:
        return False
    try:
        with open(os.path.join(directory, "Makefile"), encoding="utf-8", errors="replace") as fh:
            return fh.readline().startswith(_HEADER)
    except OSError:
        return False


def _make_dir_and_targets(args, here):
    """(directory make runs in, its targets) from the words after `make`."""
    directory, targets, skip = here, [], False
    for i, word in enumerate(args):
        if skip:
            skip = False
            continue
        if word in ("-C", "--directory", "-f", "--file", "--makefile"):
            if word in ("-C", "--directory") and i + 1 < len(args):
                directory = _join(here, args[i + 1])
            skip = True
        elif word.startswith("--directory="):
            directory = _join(here, word.split("=", 1)[1])
        elif word.startswith("-C") and len(word) > 2:
            directory = _join(here, word[2:])
        elif not word.startswith("-") and "=" not in word:
            targets.append(word)
    return directory, targets


def _join(here, target):
    if is_rooted(target):   # not os.path.isabs: from 3.13 on Windows it rejects /work/x
        return target
    return os.path.join(here, target) if here else None


def _runs_bmk(tokens, idx, tool_name):
    """True when the program at `idx` is bmk itself, or `uvx` launching it."""
    program = basename_for_tool(tokens[idx], tool_name)
    if program == "bmk":
        return True
    if program != "uvx":
        return False
    rest = [t for t in tokens[idx + 1:] if not t.startswith("-")]
    return bool(rest) and (rest[0] == "bmk" or rest[0].startswith("bmk@") or rest[0].startswith("bmk=="))


def notice(command, cwd, tool_name=None):
    """The nudge text when `command` runs a bmk gate, else None."""
    if not command or not isinstance(command, str):
        return None
    here = cwd
    for _at, segment in iter_segments(strip_heredoc_bodies(command), tool_name):
        changed, landing = directory_change(segment, here, tool_name)
        if changed:
            here = landing
            continue
        tokens = argv_for_match(segment, tool_name or "Bash")
        idx = statement_program(tokens, _PROGRAMS, tool_name or "Bash")
        if idx is None:
            continue
        if _runs_bmk(tokens, idx, tool_name or "Bash"):
            return _NOTICE
        if basename_for_tool(tokens[idx], tool_name or "Bash") != "make":
            continue
        directory, targets = _make_dir_and_targets(tokens[idx + 1:], here)
        if any(t in _GATE_TARGETS for t in targets) and _is_bmk_makefile(directory):
            return _NOTICE
    return None


def _already_nudged(session):
    """Once per session; with no session id every matching call nudges (the safer failure)."""
    if not session:
        return False
    try:
        from self_improve_signals import session_state_path  # noqa: PLC0415 - shared, confines the id
        flag = session_state_path(session, _MARKER)
        if flag.exists():
            return True
        flag.parent.mkdir(parents=True, exist_ok=True)
        flag.write_text("1\n", encoding="utf-8")
        return False
    except Exception:  # noqa: BLE001 - dedup must never break the hook
        return False


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:  # noqa: BLE001 - no/invalid stdin: do nothing
        return 0
    if not isinstance(event, dict) or not is_shell_tool(event.get("tool_name")):
        return 0
    message = notice((event.get("tool_input") or {}).get("command"), event.get("cwd"),
                     event.get("tool_name"))
    if not message or _already_nudged(event.get("session_id") or ""):
        return 0
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
