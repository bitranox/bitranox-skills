#!/usr/bin/env python3
"""PreToolUse(Bash|PowerShell|AskUserQuestion) nudge: a MISSING-mechanism premise needs its evidence.

"X is missing" / "X defaults off" / "X is never called" is the shape of claim that is easiest to
infer and hardest to verify: a doc comment is not a constructor, and a feature that ships OFF
behind an opt-in reads exactly like a dead path. Recorded five times, always the same way - the
claim was filed from a neighbouring fix rather than from the initialization path.

Scoped to a `memory_engine add`, which is the ENSHRINING moment: the claim goes into always-loaded
context, where every later session reads it as settled. A grep or an echo containing the same
words is somebody looking, not somebody filing, and is none of this hook's business.

Silent when the hook text already NAMES its evidence (a file, a line, a symbol) - stating where
you looked is the check being asked for, and nagging then is pure noise.

The hook text is read from every spelling the engine's argparse accepts: `--hook VALUE` and
`--hook=VALUE` in either quoting, and `--hook-file PATH` / `--hook-file=PATH`, which the memory
docs prescribe for long hooks. A hook file is read only when it already exists and is small: this
runs BEFORE the command, so a file the same command writes is not there yet and is skipped rather
than guessed at.

The second enshrining moment is a QUESTION to the user: an option built on "X cannot" or "Y is
missing" gets chosen on that premise, and the choice outlives the session. So every AskUserQuestion
call is handled with no wording match (the user chose that over a premise detector, which would
miss every shape nobody listed). additionalContext alone cannot reshape the question: probed on
CLI 2.1.289, it reaches the model together with the user's ANSWER. A deny does reach it first:
probed on interactive CLI 2.1.296, the dialog was never shown and the model quoted the reason. So
the FIRST ask of each question is refused with the premise check, and the re-send that follows -
identical or revised - passes with the after-the-fact reminder. "The previous ask of this session
was refused" is one per-session flag; a hash of the question text would refuse the revision the
refusal asks for. No session id, or a flag that cannot be stored, means no refusal: a refusal
that could not be recorded would refuse every re-send.

The memory-add check is NON-BLOCKING (additionalContext). Exits 0 always; fail-open on any
error. ASCII only.
"""
from __future__ import annotations

import json
import os
import re
import sys

from self_improve_signals import session_state_path
from shell_text import (
    argv_for_match,
    basename_for_tool,
    is_shell_tool,
    iter_segments,
    strip_heredoc_bodies,
)

_ENGINE_NAMES = frozenset({"memory_engine", "memory_engine.py"})

# The engine caps a hook at 500 characters. A file many times that size is not a hook, and this
# nudge must not read an arbitrary large file on every PreToolUse.
_HOOK_FILE_CAP = 8192

# Assertions that a mechanism does not exist or does not run. Each needs a subject next to it, so
# a bare "missing" in ordinary prose ("the missing piece was the timeout") does not match.
_CLAIM = re.compile(
    r"\bis missing\b|\bare missing\b|\bmissing entirely\b"
    r"|\bdefaults? (?:to )?off\b|\bdefault(?:s|ed)? to false\b"
    r"|\bis not used\b|\bare not used\b|\bnever used\b"
    r"|\bis never called\b|\bnever called\b|\bno caller\b|\bno callers\b"
    r"|\bnot wired\b|\bdead code\b|\bdead path\b|\bdoes not exist\b",
    re.IGNORECASE,
)

# Evidence that the init path WAS read: a concrete file, module path, or line reference.
_EVIDENCE = re.compile(
    r"\b[\w./-]+\.(?:py|rs|ts|js|go|sh|ps1|toml|json)\b|\bline \d+|\b__init__\b|\bcomposition/",
    re.IGNORECASE,
)

_NOTICE = (
    "MISSING-MECHANISM CLAIM: this memory hook asserts something is missing, defaults off, or is "
    "never called. Read the INITIALIZATION path before filing it - a doc comment is not a "
    "constructor, and an inference from a neighbouring fix is not evidence. A feature that ships "
    "OFF behind an opt-in reads exactly like a dead path, so say whether the opt-in was set. "
    "Recorded five times. If you have checked, name where (the file, the symbol, the line) in the "
    "hook itself - that turns the claim into a finding and silences this nudge."
)


QUESTION_REMINDER = (
    "QUESTION PREMISES: an option that rests on a tool/OS/library premise ('X cannot', 'Y is "
    "missing', 'Z defaults off') must have been measured with a named instrument first, or say "
    "'unverified' in the option itself. This reaches you with the answer: if the question you "
    "already answered offered such a premise unmeasured, tell the user now and re-ask after "
    "measuring; apply it before the next question."
)


QUESTION_REFUSAL = (
    "QUESTION PREMISES, checked BEFORE the user sees this question (the first ask of each question "
    "is refused once on purpose; the user chose this on 2026-10-12): read every option's "
    "description. Any premise about a tool, OS, library or the build ('X cannot', 'Y is missing', "
    "'Z defaults off', 'this will stay at N') must have been measured with a named instrument - "
    "measure it now - or the option must say 'unverified' in its own text. Then re-send the "
    "question, revised or unchanged; the re-send is not refused."
)

# Suffix of the per-session flag that says "this session's previous AskUserQuestion was refused".
_REFUSED_FLAG = ".question-refused"


def _memory_add_args(argv, tool_name):
    """The arguments after `add` when `argv` runs `memory_engine[.py] ... add`, else None."""
    for at, token in enumerate(argv):
        if basename_for_tool(token, tool_name) in _ENGINE_NAMES:
            rest = argv[at + 1:]
            return rest[rest.index("add") + 1:] if "add" in rest else None
    return None


def _read_hook_file(path, cwd):
    """The text of a hook file that already exists and is small, else None."""
    if not os.path.isabs(path) and cwd:
        path = os.path.join(cwd, path)
    try:
        if not os.path.isfile(path) or os.path.getsize(path) > _HOOK_FILE_CAP:
            return None
        with open(path, encoding="utf-8", errors="ignore") as handle:
            return handle.read()
    except (OSError, ValueError):
        return None


def _hook_texts(args, cwd):
    """Every hook text one memory add carries, from `--hook` and `--hook-file` in both spellings."""
    texts = []
    for at, arg in enumerate(args):
        name, eq, inline = arg.partition("=")
        if name not in ("--hook", "--hook-file"):
            continue
        if eq:
            value = inline
        elif at + 1 < len(args):
            value = args[at + 1]
        else:
            continue
        text = value if name == "--hook" else _read_hook_file(value, cwd)
        if text:
            texts.append(text)
    return texts


def notice(command, tool_name="Bash", cwd=None):
    """The nudge text for a memory add carrying an unevidenced missing-mechanism claim, else None.

    Both scans run over the HOOK TEXT, never the whole command: the command line always contains
    `memory_engine.py`, which the evidence pattern would read as a named file, so scanning the
    whole thing silences the nudge on every input. Caught by this module's own tests.

    The command is walked statement by statement and each is split into argv by the tool's own
    rules, so a `--hook` belongs to the memory add it follows and to nothing else: an `echo` that
    QUOTES a memory add is one argument to echo, not a filing.
    """
    if not command or not isinstance(command, str):
        return None
    # A heredoc BODY is stdin data. A doc that QUOTES a memory_engine add command is not
    # running one, and firing there blocks the writing of this nudge's own guidance.
    command = strip_heredoc_bodies(command)
    for _offset, segment in iter_segments(command, tool_name):
        args = _memory_add_args(argv_for_match(segment, tool_name), tool_name)
        if args is None:
            continue
        for text in _hook_texts(args, cwd):
            if _CLAIM.search(text) and not _EVIDENCE.search(text):
                return _NOTICE
    return None


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:  # noqa: BLE001 - no/invalid stdin: do nothing
        return 0
    if isinstance(event, dict) and event.get("tool_name") == "AskUserQuestion":
        _answer_question(event.get("session_id"))
        return 0
    if not isinstance(event, dict) or not is_shell_tool(event.get("tool_name")):
        return 0
    message = notice(
        (event.get("tool_input") or {}).get("command"),
        tool_name=event.get("tool_name"),
        cwd=event.get("cwd") if isinstance(event.get("cwd"), str) else None,
    )
    if message:
        _emit(message)
    return 0


def _answer_question(session):
    """Refuse the first ask of a question, let the re-send through with the reminder.

    Every AskUserQuestion of a session passes through here, so one flag is the whole history
    needed: set means the previous ask was refused, so this one is the re-send and passes. The
    flag is set only once it is STORED - a refusal that could not be recorded would refuse every
    re-send forever - and with no session to key it on the question simply passes.
    """
    flag = _refused_flag(session)
    if flag is None:
        _emit(QUESTION_REMINDER)
        return
    if flag.exists():
        try:
            flag.unlink()
        except OSError:
            pass
        _emit(QUESTION_REMINDER)
        return
    try:
        flag.parent.mkdir(parents=True, exist_ok=True)
        flag.write_text("refused\n", encoding="utf-8")
    except OSError:
        _emit(QUESTION_REMINDER)
        return
    _deny(QUESTION_REFUSAL)


def _refused_flag(session):
    """The session's refused-question flag path, or None when there is no usable session id."""
    if not isinstance(session, str) or not session.strip():
        return None
    try:
        return session_state_path(session, _REFUSED_FLAG)
    except Exception:  # noqa: BLE001 - no state, no refusal: the question passes
        return None


def _deny(reason):
    sys.stdout.write(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }}) + "\n")


def _emit(message):
    sys.stdout.write(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "additionalContext": message,
    }}) + "\n")


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - a broken hook must never wedge a turn
        sys.exit(0)
