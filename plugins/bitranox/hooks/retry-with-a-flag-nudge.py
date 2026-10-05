#!/usr/bin/env python3
"""Catch the "same command plus a flag" retry, at the moment it is about to run again.

`process-stop-repeating-failure` states the rule this hook enforces: "Re-running the failed command
with a flag added is not on the list. If the next command is the last command plus an option, this
is you." A flag gets picked because a mechanism story sounds right, and docs say what a flag
GOVERNS, never that it governs the phase that failed.

TWO EVENTS, and the split is the whole design. A watcher that only looked BACK could report the
repeat after the retry had already run, which is the failure mode the store records as "a
retrospective watcher cannot see a retry coming; hook the pending action". So:

  * `PostToolUseFailure` RECORDS. It is the only event that says a command failed without inferring
    it, and it renders no decision at all - the tool has already failed, so there is nothing to
    block and nothing to be wrong about.
  * `PreToolUse` JUDGES the PENDING command against what was recorded, before it runs.

Neither half is useful alone: recording without judging is a log nobody reads, and judging without
recording means parsing a transcript to guess which calls failed.

WHAT COUNTS AS THE SAME COMMAND PLUS A FLAG. The pending command must have the same program and the
same non-flag operands as a command that already failed this session, and strictly more flags. That
is deliberately narrow. Ordinary iteration changes the operands, the program, or the flags in both
directions; only the "bolt an option onto the thing that just failed" shape adds flags while
touching nothing else. A changed operand means a different target and is not this.

Heredoc bodies are blanked before anything is compared, because a body is data being written and a
script that CONTAINS a failing command is not that command. Statement and pipe separators are found
on the data-masked text, so a `;` or `|` inside a quoted sed script or grep pattern is not one, and
the command is then sliced from the raw text at the same offsets. The command is split into words by
the TOOL's language (`split_for_tool`): a PowerShell `C:\\data\\logs` keeps its backslashes, where
POSIX splitting collapsed it into `C:datalogs` and two different targets compared equal.

TUNED AGAINST THE REAL CORPUS, not guessed. Replayed over 181 sessions and 32948 commands, the
first version fired 536 times - 216 in one session - and essentially every hit was a pipeline tail,
not a retry. Two constraints came out of that and both are load-bearing: a pipeline is ONE statement
(splitting on `|` makes `grep ... | head -60` into the command `head`), and a command with NO
OPERANDS is not a retry target (with operands empty, "same operands" is vacuously true and any two
invocations of a program compare equal).

NON-BLOCKING. It emits `additionalContext` and exits 0 on both events. The judgement is a heuristic
about intent, and blocking on a heuristic that cannot see why the flag was added would be wrong far
too often - a second failing attempt is sometimes exactly the right diagnostic step.

Pure standard library, ASCII only; launched via run-python.sh so it works on Windows too.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from shell_text import (
    basename_for_tool,
    blank_heredoc_bodies,
    is_shell_tool,
    iter_segments,
    mask_data_regions,
    split_for_tool,
)

# The separators that continue a PIPELINE rather than start a statement. A pipeline is ONE
# statement here: its last element is usually a filter, and asking "what command is being
# retried" of `grep ... | head -60` must not answer `head` with the flag `-60` and NO operands, or
# any two pipeline tails compare equal. Measured over 181 real sessions before this was fixed: 536
# firings, 216 of them in a single session, essentially all of them pipeline tails, not retries.
_PIPE_SEPARATORS = frozenset({"|", "|&"})

STATE_VERSION = 1
MAX_RECORDED = 60          # bound the state file on a marathon session
FIRE_CAP = 3               # nudges per session; past that the reader has stopped listening


def _state_path(session: str) -> Path:
    from self_improve_signals import session_state_path   # noqa: PLC0415 - shared, confines the id
    return session_state_path(session, ".retry-flag.json")


def _load(session: str) -> dict:
    try:
        state = json.loads(_state_path(session).read_text(encoding="utf-8"))
    except Exception:                                     # noqa: BLE001 - absent/corrupt: start fresh
        return {}
    if not isinstance(state, dict) or state.get("v") != STATE_VERSION:
        return {}
    return state


def _save(session: str, state: dict) -> None:
    try:
        path = _state_path(session)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(state), encoding="utf-8")
    except Exception:                                     # noqa: BLE001 - state must never break the hook
        pass


def _command_head(command: str, tool_name: str) -> str:
    """The raw text of the first pipeline element of the LAST statement, or "". PURE.

    Separators are FOUND by shell_text's quote-aware walk on the masked text - heredoc bodies
    blanked in place, quoted text, substitutions and comments masked, every step length-preserving
    - and the command is SLICED from the unmasked text at the same offsets, so a quoted `;` or `|`
    is data, not structure.

    The answer is the FIRST element of the last pipeline - the command being run, where the rest
    only shapes its output - and the walk's parens are read by what they open (`_HeadWalk`): a
    subshell that IS that element contributes its own last statement, so `(sed -n 1p f) | head`
    is `sed` with the operand `f`, not `(sed` with `f)`; a process substitution is an ARGUMENT, so
    `diff <(sed a x) <(sed b y)` stays the command `diff`.
    """
    text = blank_heredoc_bodies(command)
    masked = mask_data_regions(text, tool_name=tool_name)
    walk = _HeadWalk()
    previous_end = 0
    for at, segment in iter_segments(masked, tool_name):
        walk.separator(masked[previous_end:at])
        previous_end = at + len(segment)
        walk.segment(at, previous_end, bool(segment.strip()))
    span = walk.frames[0].head
    return text[span[0]:span[1]] if span else ""


# A paren the walk reports that opens an ARGUMENT, not a statement: its contents are part of the
# enclosing command's words.
_SUBSTITUTION_OPENERS = frozenset({"$(", "<(", ">(", "`"})


class _HeadWalk:
    """Track, per open group, the span of its last statement's first pipeline element.

    One frame per open group: the command itself, a subshell, or a substitution. Inside a frame a
    list separator starts a statement, a pipe continues one, and the segments of the element that
    started a statement extend its span - across a substitution, whose text is part of its words.
    """

    class _Frame:
        def __init__(self, kind, heads_parent):
            self.kind = kind                  # "top", "subshell" or "substitution"
            self.heads_parent = heads_parent  # this group IS the element the parent is waiting for
            self.head = None                  # (start, end) of the current statement's first element
            self.expect_head = True           # the next non-blank segment starts a statement
            self.in_head = False              # still inside that first element

    def __init__(self):
        self.frames = [self._Frame("top", False)]

    def separator(self, sep):
        frame = self.frames[-1]
        if sep in _SUBSTITUTION_OPENERS and not (sep == "`" and frame.kind == "backtick"):
            self.frames.append(self._Frame("backtick" if sep == "`" else "substitution", False))
        elif sep == "(":
            self.frames.append(self._Frame("subshell", frame.expect_head))
            frame.expect_head = False
        elif sep in (")", "`") and len(self.frames) > 1:
            closed = self.frames.pop()
            if closed.kind == "subshell" and closed.heads_parent:
                self.frames[-1].head, self.frames[-1].in_head = closed.head, False
        elif sep in _PIPE_SEPARATORS:
            frame.in_head = False
        elif sep:
            frame.expect_head, frame.in_head = True, False

    def segment(self, start, end, has_text):
        frame = self.frames[-1]
        if frame.kind in ("substitution", "backtick"):
            return                            # an argument's insides: part of the enclosing words
        if has_text and frame.expect_head:
            frame.head, frame.expect_head, frame.in_head = (start, end), False, True
        elif frame.in_head and frame.head:
            frame.head = (frame.head[0], end)


def shape(command, tool_name="Bash"):
    """(program, sorted flags, operands) for the LAST statement of `command`, or None. PURE.

    The last statement is the one whose failure the event reports; an earlier statement in a `&&`
    chain succeeded. Heredoc bodies are dropped first so a written script is not read as a command.
    `tool_name` picks the word-splitting and path rules (`split_for_tool`, `basename_for_tool`).

    Flags are a SET because reordering them is not a new attempt, and operands stay a LIST because
    their order is part of what the command targets.
    """
    if not command or not isinstance(command, str):
        return None
    head = _command_head(command, tool_name)
    try:
        tokens = split_for_tool(head, tool_name, comments=True)
    except ValueError:                                    # an unclosed quote: shlex refuses it
        tokens = head.split()
    if not tokens:
        return None
    program = basename_for_tool(tokens[0], tool_name)     # /usr/bin/sed, sed.exe and sed are one
    flags, operands = set(), []
    for token in tokens[1:]:
        (flags.add(token) if token.startswith("-") else operands.append(token))
    # No operand means no identifiable TARGET, so "same operands" would be vacuously true and any
    # two invocations of the program would compare equal. A retry is about a target.
    if not operands:
        return None
    return (program, tuple(sorted(flags)), tuple(operands))


def only_flags_added(pending, failed) -> bool:
    """True when `pending` is `failed` with strictly more flags and nothing else changed. PURE."""
    if not pending or not failed:
        return False
    program, flags, operands = pending
    was_program, was_flags, was_operands = failed
    if program != was_program or operands != was_operands:
        return False
    return set(was_flags) < set(flags)


def notice(pending_command, recorded, tool_name="Bash"):
    """The nudge text when this pending command re-runs a failed one with added flags, else None."""
    pending = shape(pending_command, tool_name)
    if not pending:
        return None
    for entry in recorded:
        failed = (entry[0], tuple(entry[1]), tuple(entry[2]))
        if only_flags_added(pending, failed):
            added = " ".join(sorted(set(pending[1]) - set(failed[1])))
            return (
                "This command is one that already FAILED this session with " + added + " added and "
                "nothing else changed. A flag bolted onto the command that just failed is the same "
                "attempt wearing a different hat: documentation says what an option GOVERNS, never "
                "that it governs the phase that failed. bitranox:process-stop-repeating-failure "
                "gives three options and adding a flag is not among them - change the INSTRUMENT "
                "to one with different semantics, prove the change on a scratch fixture with a "
                "before/after count first, or stop and report. If this flag addresses a "
                "DIFFERENT, identified defect, that is ordinary iteration: say which one."
            )
    return None


def _record(event) -> int:
    """PostToolUseFailure: remember the shape of the command that failed."""
    if not is_shell_tool(event.get("tool_name")) or event.get("is_interrupt"):
        return 0                                          # an interrupt is the user, not a failure
    current = shape((event.get("tool_input") or {}).get("command"), event.get("tool_name"))
    if not current:
        return 0
    # Stored as JSON reads it back - lists all the way down - so the dedup compares like with like.
    # Comparing against `list(current)`, which still holds tuples, never matched: one command
    # failing in a loop filled every slot and evicted the failure that mattered.
    entry = [current[0], list(current[1]), list(current[2])]
    session = str(event.get("session_id") or "")
    state = _load(session)
    recorded = [e for e in state.get("failed", []) if e != entry]
    recorded.append(entry)
    state.update({"v": STATE_VERSION, "failed": recorded[-MAX_RECORDED:]})
    _save(session, state)
    return 0


def _judge(event) -> int:
    """PreToolUse: warn when the pending command re-runs a failed one with a flag added."""
    if not is_shell_tool(event.get("tool_name")):
        return 0
    session = str(event.get("session_id") or "")
    state = _load(session)
    if state.get("fired", 0) >= FIRE_CAP:
        return 0
    message = notice((event.get("tool_input") or {}).get("command"), state.get("failed", []),
                     event.get("tool_name"))
    if not message:
        return 0
    state["fired"] = state.get("fired", 0) + 1
    _save(session, state)
    json.dump({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                      "additionalContext": message}}, sys.stdout)
    return 0


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:  # noqa: BLE001 - no/invalid stdin: do nothing
        return 0
    if not isinstance(event, dict):
        return 0
    if event.get("hook_event_name") == "PostToolUseFailure":
        return _record(event)
    return _judge(event)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - a broken hook must never wedge a turn
        sys.exit(0)
