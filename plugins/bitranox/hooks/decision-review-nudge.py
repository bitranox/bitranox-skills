#!/usr/bin/env python3
"""Stop hook: once work has actually concluded, ask which decisions are still unsettled.

The decisions worth a second look are the ones that leave no trace in a diff - a default that
changes behaviour on upgrade, a version tier, a scope cut, a flaky test waved off. Nothing else
surfaces them: a code review reads what changed, and a verification gate asks whether a claim is
true, not whether a choice was right. The person who would ask is the person who has to remember
to ask, which is exactly what does not happen at the end of a long session.

**What counts as concluded:**

1. A `/goal` whose record says it is met. Claude Code records progress in the transcript as an
   attachment record,
   `{"type": "attachment", "attachment": {"type": "goal_status", "met": <bool>, ...}}`,
   and the LAST one is the current state. Only that nested shape is read; a top-level
   `goal_status` record is not what the CLI writes. The record is written when the goal is SET
   (`met: false`, `sentinel: true`) and again when the goal hook judges a Stop, and that verdict
   lands AFTER this hook has read the transcript - so at the Stop that ends a goal this hook still
   reads `met: false`, and the block for a met goal comes at the next Stop.
   A RUNNING goal is not a conclusion. It gets a one-time, non-blocking reminder that claims
   nothing about the goal's state. Blocking on it was tried, on the argument that sometimes-early
   beats sometimes-never; measured over every goal session on record (2026-09-28), 13 of 16 such
   blocks were early - 3 to 160 minutes into the goal and up to 583 minutes before it was met,
   typically a turn ending to wait on background agents - and each told the model "a /goal
   objective was met" while it was not. Only 3 landed on the Stop that ended the goal.
2. Otherwise an OPENED PR is the conclusion, and a commit or a push is not. Two
   proxies were tried before this and both were wrong. A file-count threshold fires mid-edit on a
   session that has concluded nothing and stays silent on a one-line fix that shipped. Firing on
   every commit or push was measured over three weeks of transcripts (2026-09-04): it was the
   single largest trigger of instrumentation work at the END of ordinary work sessions - the walk
   raised tooling decisions, each walk ended in a memory capture, an engine fix and a plugin
   release from a project that had nothing to do with the tool, and the share grew week on week
   while the hook itself never changed. A commit is a checkpoint the author still owns; a PR is
   the moment the choices become somebody else's to live with.

A block does not end a goal run: the CLI string "Stop hook prevented continuation" belongs to a
hook setting `preventContinuation`, a different field this hook never sets; `{"decision": "block"}`
feeds a reason back and the turn carries on. Measured: the self-improve gate blocked during an
active goal in a real session and the goal still completed. The once-per-session flag also keeps
this far below the consecutive-block cap that would end a turn by override.

The command detection is `shell_text.opens_a_pr`, segmented and anchored exactly like the
predicate the repo gate blocks on (`is_gated_command`), so the two cannot disagree about what a
statement is - only about which verbs conclude.

It asks ONCE per session. The flag is keyed by session id, so a flag left behind by an earlier
session can never satisfy this one (a per-PROJECT flag would, and has - it demanded work for a
compaction that happened in a different session).

It stays quiet on `stop_hook_active`: that Stop follows a continuation some Stop hook already
forced, and asking again there stacks a second block on one turn - with an unwritable state dir,
on every one. A conclusion reached during the continuation is still in the unread window, so the
next ordinary Stop asks about it.

Pure standard library. Reads the event JSON on stdin. ALWAYS exits 0 - a nudge must never wedge
a turn.
"""

import json
import os
import sys
from typing import NamedTuple

import self_improve_signals as sig
import shell_text

# One run reads only what is NEW: it starts where the previous run stopped and remembers the
# offset it reached. That is what keeps the cap below from hiding anything - a scan that always
# restarted at byte 0 would truncate at the same place every time, so in a session longer than the
# cap NO later commit could ever be seen and the reminder would go quiet while looking healthy.
# Reading forward from the last offset also keeps each run's work proportional to what happened
# since, rather than to the size of the session.
_MAX_TRANSCRIPT_BYTES = 8 * 1024 * 1024

GOAL_NONE = "none"
GOAL_ACTIVE = "active"
GOAL_MET = "met"


class ShellCall(NamedTuple):
    """One shell command from the transcript, with the tool that ran it.

    The tool travels with the command because `shell_text` tokenises by it: PowerShell keeps
    backslashes and has its own quoting, so judging its command by the Bash reading answers a
    different question.
    """

    command: str
    tool: str


class Signals(NamedTuple):
    """What one pass over a WINDOW of the transcript found."""

    commands: list                                        # of ShellCall, in transcript order
    goal_state: str
    offset: int


def read_line(raw, commands, goal_state):
    """Fold one transcript line into the running result. Returns the goal state after it."""
    try:
        msg = json.loads(raw.decode("utf-8", "replace"))
    except ValueError:
        return goal_state                                 # a half-written line is normal
    if not isinstance(msg, dict):
        return goal_state
    attachment = msg.get("attachment")
    if isinstance(attachment, dict) and attachment.get("type") == "goal_status":
        # The LAST record wins: a goal reports `met: false` on every turn it is still running,
        # then once with `met: true`.
        goal_state = GOAL_MET if attachment.get("met") is True else GOAL_ACTIVE
    message = msg.get("message")
    if not isinstance(message, dict):
        return goal_state                                 # a string or null message has no tools
    content = message.get("content")
    if isinstance(content, list):
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            tool = block.get("name")
            if not shell_text.is_shell_tool(tool):
                continue
            tool_input = block.get("input")
            cmd = tool_input.get("command") if isinstance(tool_input, dict) else None
            if isinstance(cmd, str) and cmd:
                commands.append(ShellCall(cmd, tool))
    return goal_state


def _resume_from(transcript_path, start):
    """Where to start reading. 0 when the stored offset no longer fits the file.

    A transcript that shrank or was replaced leaves an offset past its end, and seeking past EOF
    succeeds and reads nothing - so the hook would go silent for good, and that silence looks
    exactly like "nothing concluded".
    """
    try:
        return 0 if start > os.path.getsize(transcript_path) else max(0, start)
    except OSError:
        return 0


def transcript_signals(transcript_path, start=0, max_bytes=_MAX_TRANSCRIPT_BYTES,
                       goal_state=GOAL_NONE):
    """Scan [start, EOF) and report what is there, plus the offset reached.

    `goal_state` carries the state the previous run ended on: a window holding no goal record
    means the goal has not changed, not that it went away.

    The offset stops at the last COMPLETE line. A transcript is appended to live, so its tail can
    be mid-write; consuming a partial line would mean the rest arrives later as an unparseable
    fragment, and whatever that line recorded is then lost for good rather than merely late.

    `max_bytes` ends the window BEFORE a line that would overrun it - except the window's first
    line, which is read and consumed whatever its size. Breaking before that one too meant a single
    line longer than the cap was never passed: every later run stopped at the same byte, and
    nothing after it was ever seen.
    """
    commands = []
    start = _resume_from(transcript_path, start)
    consumed = start
    try:
        # BINARY mode, deliberately. In text mode `len(line)` counts CHARACTERS while `seek` wants
        # a byte position - and only ever one that `tell` produced - so a single non-ASCII
        # character earlier in the transcript would shift the offset and resume mid-character.
        # Bytes make the offset arithmetic mean what it says.
        with open(transcript_path, "rb") as fh:
            fh.seek(start)
            read = 0
            for raw in fh:
                if read and read + len(raw) > max_bytes:
                    break                                 # the next run starts on this line
                read += len(raw)
                goal_state = read_line(raw, commands, goal_state)
                if not raw.endswith(b"\n"):
                    break                                 # parsed, but not consumed - see above
                consumed = start + read
    except OSError:
        return Signals([], goal_state, start)
    return Signals(commands, goal_state, consumed)


_GOAL_STATES = frozenset({GOAL_NONE, GOAL_ACTIVE, GOAL_MET})


def conclusion_score(signals, previous=0, previous_goal=GOAL_NONE):
    """How many times work has concluded, as a number that only ever grows within a session.

    Counting rather than answering yes/no is what lets a LATER conclusion be told from the same one
    still sitting in the transcript. Without it the repeat nudge would fire on every turn after the
    first commit, since that commit never leaves the transcript.

    The count ACCUMULATES onto the previous run's total, because each run sees only its own window.
    Recomputing from the whole file instead would make the score fall as soon as a window slid past
    an old commit, and a falling score can never exceed what was already recorded - the reminder
    would stop for good.

    A goal counts once, when it reaches met, so that transition registers as a new conclusion even
    though no command was run. A RUNNING goal counts nothing (`goal_started` covers it), and
    neither does a commit or a push - see the module docstring for the measurements behind both.
    """
    goal_met = signals.goal_state == GOAL_MET and previous_goal != GOAL_MET
    prs = sum(1 for call in signals.commands if shell_text.opens_a_pr(call.command, call.tool))
    return previous + int(goal_met) + prs


def goal_started(signals, previous_goal=GOAL_NONE):
    """True on the first Stop that sees a goal running which the previous run had not seen."""
    return signals.goal_state == GOAL_ACTIVE and previous_goal != GOAL_ACTIVE


def reached_a_conclusion(signals):
    """True once the work is somebody else's to live with - a met goal, or an opened PR."""
    return conclusion_score(signals) > 0


ASK_NONE = "none"
ASK_BLOCK = "block"
ASK_REMIND = "remind"
ASK_GOAL = "goal"


def decide(score, last_score, started_goal=False):
    """The whole policy, as one pure decision.

    The FIRST conclusion in a session blocks, because an ask that can be scrolled past is an ask
    that gets scrolled past. Every conclusion AFTER it only reminds, without blocking: a second
    block would be nagging, and repeated blocks run into the consecutive-block cap that ends a turn
    by override. So the session is stopped once and nudged thereafter.

    A goal that has just started is not a conclusion and never blocks; it gets its own reminder,
    once, because this hook cannot tell the Stop that ends a goal from one that merely pauses it.
    """
    if score > 0 and score > last_score:
        return ASK_BLOCK if last_score <= 0 else ASK_REMIND
    return ASK_GOAL if started_goal else ASK_NONE


class State(NamedTuple):
    """What the previous run left behind: how far it read, what it counted, where the goal was."""

    offset: int
    score: int
    goal: str


EMPTY_STATE = State(0, 0, GOAL_NONE)


def asked_flag(session):
    """Session-keyed state file. Keyed by session so a flag left by an older one cannot go stale."""
    return sig.touched_file(session).with_suffix(".decisions-asked")


def read_state(session):
    """The previous run's state. EMPTY_STATE when this session has none, or it is unreadable.

    A corrupt field reads as no state at all rather than raising: the file is rewritten at the end
    of this run, so starting clean repairs it, while raising would repeat on every Stop until
    someone deleted the file by hand.
    """
    try:
        raw = json.loads(asked_flag(session).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return EMPTY_STATE
    if not isinstance(raw, dict):
        return EMPTY_STATE            # an earlier bare-integer file: start clean rather than guess
    goal = raw.get("goal")
    try:
        return State(int(raw.get("offset") or 0), int(raw.get("score") or 0),
                     goal if goal in _GOAL_STATES else GOAL_NONE)
    except (TypeError, ValueError):
        return EMPTY_STATE


def write_state(session, state):
    try:
        f = asked_flag(session)
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps({"offset": state.offset, "score": state.score,
                                 "goal": state.goal}) + "\n", encoding="utf-8")
    except OSError:
        pass


_REASON = (
    "Work concluded this session - a /goal objective was met, or a PR was opened - so the choices "
    "behind it are now somebody else's to live with. Before you stop, invoke the decision-review "
    'skill (Skill tool, name "process-review-uncertain-decisions") and answer its question: which '
    "important decisions did you make that you are NOT confident about, what alternative did you "
    "not take, and what would settle it. Leave OUT every decision that is already clearly right - "
    "the suppression is the point, and a list that includes the settled ones puts the sorting back "
    "on the reader. Leave out as well every decision about the TOOLING - a bitranox hook, skill, "
    "guard or the memory engine - however unsettled: those are not this project's work, so write "
    "each as one line with `contrib_queue.py add` and let the dream decide; walking them here is "
    "how a work session ends by shipping a plugin release. Then WALK the ones you did surface: one "
    "AskUserQuestion call per point, hardest-to-reverse first, each option carrying its upside AND "
    "its downside and the recommended one first - never a batch of questions, and never the next "
    "before this one is answered. If nothing is genuinely unsettled, say so in one line and stop."
)

# The repeat. Non-blocking, so it rides along next to the turn's result instead of stopping it -
# the same channel a PreToolUse nudge uses, which the Stop handler also accepts.
_REMINDER = (
    "More work concluded since the decision review. If any of it involved a call you are not "
    'confident about, say so now - `bitranox:process-review-uncertain-decisions` carries the '
    "question. Only the unsettled ones; silence is the right answer when there are none."
)

# A running goal. It claims nothing about the goal's state, because at the Stop that ends a goal
# the record still reads met=false, and at every other Stop the goal really is unfinished.
_GOAL_REMINDER = (
    "A /goal is running. If you are ending this turn because you believe the goal is done, first "
    "name any decision behind the work that you are NOT confident about - "
    "`bitranox:process-review-uncertain-decisions` carries the question; only the unsettled ones, "
    "tooling decisions go to `contrib_queue.py add`. If the turn is ending for any other reason, "
    "such as waiting on background work, ignore this."
)


def main():
    try:
        event = json.load(sys.stdin)
    except Exception:                                     # noqa: BLE001 - never wedge a turn
        return 0
    if not isinstance(event, dict) or event.get("stop_hook_active"):
        return 0
    session = str(event.get("session_id") or "")
    transcript = event.get("transcript_path") or ""
    if not session or not transcript:
        return 0
    seen = read_state(session)
    try:
        signals = transcript_signals(transcript, start=seen.offset, goal_state=seen.goal)
        score = conclusion_score(signals, previous=seen.score, previous_goal=seen.goal)
    except Exception:                                     # noqa: BLE001 - never wedge a turn
        return 0
    verdict = decide(score, seen.score, started_goal=goal_started(signals, seen.goal))
    # The offset advances even on a quiet turn, so the next run scans only what is new. Skipping
    # this when nothing was found would re-scan the same window forever and, once the window hit
    # the cap, never reach anything past it.
    write_state(session, State(signals.offset, score, signals.goal_state))
    if verdict == ASK_NONE:
        return 0
    if verdict == ASK_BLOCK:
        sys.stdout.write(json.dumps({"decision": "block", "reason": _REASON}))
    else:
        reminder = _GOAL_REMINDER if verdict == ASK_GOAL else _REMINDER
        sys.stdout.write(json.dumps({"hookSpecificOutput": {
            "hookEventName": "Stop", "additionalContext": reminder}}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:                                     # noqa: BLE001 - never wedge a turn
        sys.exit(0)
