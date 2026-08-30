#!/usr/bin/env python3
"""PreToolUse(Bash) nudge: a memory hook asserting a mechanism is MISSING needs the init path read.

"X is missing" / "X defaults off" / "X is never called" is the shape of claim that is easiest to
infer and hardest to verify: a doc comment is not a constructor, and a feature that ships OFF
behind an opt-in reads exactly like a dead path. Recorded five times, always the same way - the
claim was filed from a neighbouring fix rather than from the initialization path.

Scoped to a `memory_engine add`, which is the ENSHRINING moment: the claim goes into always-loaded
context, where every later session reads it as settled. A grep or an echo containing the same
words is somebody looking, not somebody filing, and is none of this hook's business.

Silent when the hook text already NAMES its evidence (a file, a line, a symbol) - stating where
you looked is the check being asked for, and nagging then is pure noise.

NON-BLOCKING: emits additionalContext and exits 0. Fail-open on any error. ASCII only.
"""
from __future__ import annotations

import json
import re
import sys

from shell_text import is_shell_tool, strip_heredoc_bodies

_MEMORY_ADD = re.compile(r"memory_engine(?:\.py)?\b[^\n]*\badd\b")

# Assertions that a mechanism does not exist or does not run. Each needs a subject next to it, so
# a bare "missing" in ordinary prose ("the missing piece was the timeout") does not match.
_CLAIM = re.compile(
    r"\bis missing\b|\bare missing\b|\bmissing entirely\b"
    r"|\bdefaults? (?:to )?off\b|\bdefault(?:s|ed)? to false\b"
    r"|\bis not used\b|\bare not used\b|\bnever used\b"
    r"|\bis never called\b|\bnever called\b|\bno caller\b|\bno callers\b"
    r"|\bnot wired\b|\bdead code\b|\bdead path\b|\bdoes not exist\b",
    re.I,
)

# Evidence that the init path WAS read: a concrete file, module path, or line reference.
_EVIDENCE = re.compile(
    r"\b[\w./-]+\.(?:py|rs|ts|js|go|sh|ps1|toml|json)\b|\bline \d+|\b__init__\b|\bcomposition/",
    re.I,
)

_NOTICE = (
    "MISSING-MECHANISM CLAIM: this memory hook asserts something is missing, defaults off, or is "
    "never called. Read the INITIALIZATION path before filing it - a doc comment is not a "
    "constructor, and an inference from a neighbouring fix is not evidence. A feature that ships "
    "OFF behind an opt-in reads exactly like a dead path, so say whether the opt-in was set. "
    "Recorded five times. If you have checked, name where (the file, the symbol, the line) in the "
    "hook itself - that turns the claim into a finding and silences this nudge."
)


_HOOK_ARG = re.compile(r'--hook\s+"([^"]*)"')


def notice(command):
    """The nudge text for a memory add carrying an unevidenced missing-mechanism claim, else None.

    Both scans run over the HOOK TEXT, never the whole command: the command line always contains
    `memory_engine.py`, which the evidence pattern would read as a named file, so scanning the
    whole thing silences the nudge on every input. Caught by this module's own tests.
    """

    # A heredoc BODY is stdin data. A doc that QUOTES a memory_engine add command is not
    # running one, and firing there blocks the writing of this nudge's own guidance.
    command = strip_heredoc_bodies(command or "")
    if not command or not isinstance(command, str):
        return None
    if not _MEMORY_ADD.search(command):
        return None
    claims = _HOOK_ARG.findall(command)
    if not claims:
        return None
    for text in claims:
        if _CLAIM.search(text) and not _EVIDENCE.search(text):
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
