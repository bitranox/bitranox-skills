#!/usr/bin/env python3
"""Stop hook: once work has actually concluded, ask which decisions are still unsettled.

The decisions worth a second look are the ones that leave no trace in a diff - a default that
changes behaviour on upgrade, a version tier, a scope cut, a flaky test waved off. Nothing else
surfaces them: a code review reads what changed, and a verification gate asks whether a claim is
true, not whether a choice was right. The person who would ask is the person who has to remember
to ask, which is exactly what does not happen at the end of a long session.

**What counts as concluded:**

1. A `/goal` is in play at all - met, or still running. Claude Code records progress in the
   transcript as `{"type": "goal_status", "met": <bool>, "condition": ...}`, and the LAST record
   is the current state. Firing on EITHER state is deliberate, and it is the fix for a real lag:
   the goal's verdict is emitted DURING Stop-hook processing, so at the instant this hook reads
   the transcript the record still says `met: false` and the `met: true` line lands moments later.
   Waiting for it costs a whole turn, and a session that ends there never gets asked at all.
   Since the ask happens once per session, the choice is between sometimes-early and
   sometimes-never, and early is the better failure.
2. No goal in play - then a commit, a push, or an opened PR is the conclusion. A file-count
   threshold was tried first and is a worse proxy in both directions: it fires mid-edit on a
   session that has concluded nothing, and stays silent on a one-line fix that shipped.

Blocking during a running goal is safe, which an earlier version of this hook got wrong. The CLI
string "Stop hook prevented continuation" belongs to a hook setting `preventContinuation`, a
different field this hook never sets; `{"decision": "block"}` feeds a reason back and the turn
carries on. Measured: the self-improve gate blocked during an active goal in a real session and
the goal still completed. The once-per-session flag also keeps this far below the consecutive-block
cap that would end a turn by override.

The command detection is `shell_text.is_gated_command`, the same predicate the repo gate blocks
on, so the two cannot disagree about what counts.

It asks ONCE per session. The flag is keyed by session id, so a flag left behind by an earlier
session can never satisfy this one (a per-PROJECT flag would, and has - it demanded work for a
compaction that happened in a different session).

Pure standard library. Reads the event JSON on stdin. ALWAYS exits 0 - a nudge must never wedge
a turn.
"""

import json
import sys
from typing import NamedTuple

import self_improve_signals as sig
import shell_text

# Transcripts reach many MB in a long session. This is a whole-file scan rather than a tail read,
# because the commit or the goal record that concluded the work may be many turns back - but it
# runs at most once per session (the flag short-circuits every later turn), so the cost is paid
# once.
_MAX_TRANSCRIPT_BYTES = 8 * 1024 * 1024

GOAL_NONE = "none"
GOAL_ACTIVE = "active"
GOAL_MET = "met"


class Signals(NamedTuple):
    """What one pass over the transcript found."""

    commands: list
    goal_state: str


def transcript_signals(transcript_path, max_bytes=_MAX_TRANSCRIPT_BYTES):
    """Bash commands and the CURRENT goal state, from a single read. Empty when unreadable."""
    commands = []
    goal_state = GOAL_NONE
    try:
        with open(transcript_path, "r", encoding="utf-8", errors="replace") as fh:
            read = 0
            for line in fh:
                read += len(line)
                if read > max_bytes:
                    break
                try:
                    msg = json.loads(line)
                except ValueError:
                    continue                              # a partial last line is normal
                attachment = msg.get("attachment")
                if isinstance(attachment, dict) and attachment.get("type") == "goal_status":
                    # The LAST record wins: a goal reports `met: false` on every turn it is still
                    # running, then once with `met: true`.
                    goal_state = GOAL_MET if attachment.get("met") is True else GOAL_ACTIVE
                content = (msg.get("message") or {}).get("content")
                if not isinstance(content, list):
                    continue
                for block in content:
                    if not isinstance(block, dict) or block.get("type") != "tool_use":
                        continue
                    if block.get("name") != "Bash":
                        continue
                    cmd = (block.get("input") or {}).get("command")
                    if isinstance(cmd, str) and cmd:
                        commands.append(cmd)
    except OSError:
        return Signals([], GOAL_NONE)
    return Signals(commands, goal_state)


_GOAL_SCORE = {GOAL_NONE: 0, GOAL_ACTIVE: 1, GOAL_MET: 2}


def conclusion_score(signals):
    """How many times work has concluded, as a number that only ever grows within a session.

    Counting rather than answering yes/no is what lets a LATER conclusion be told from the same one
    still sitting in the transcript. Without it the repeat nudge would fire on every turn after the
    first commit, since that commit never leaves the transcript.

    A goal scores 1 while running and 2 once met, so the running-to-met transition registers as a
    new conclusion even though no command was run.
    """
    return _GOAL_SCORE[signals.goal_state] + sum(
        1 for c in signals.commands if shell_text.is_gated_command(c)
    )


def reached_a_conclusion(signals):
    """True once the work is somebody else's to live with - a goal in play, or a commit."""
    return conclusion_score(signals) > 0


ASK_NONE = "none"
ASK_BLOCK = "block"
ASK_REMIND = "remind"


def decide(score, last_score):
    """The whole policy, as one pure decision.

    The FIRST conclusion in a session blocks, because an ask that can be scrolled past is an ask
    that gets scrolled past. Every conclusion AFTER it only reminds, without blocking: a second
    block would be nagging, and repeated blocks run into the consecutive-block cap that ends a turn
    by override. So the session is stopped once and nudged thereafter.
    """
    if score <= 0 or score <= last_score:
        return ASK_NONE
    return ASK_BLOCK if last_score <= 0 else ASK_REMIND


def asked_flag(session):
    """Session-keyed state holding the last conclusion score. Keyed by session so it cannot go stale."""
    return sig.touched_file(session).with_suffix(".decisions-asked")


def last_score(session):
    """The score at the previous ask. 0 when this session has never been asked."""
    try:
        return int(asked_flag(session).read_text(encoding="utf-8").strip() or 0)
    except (OSError, ValueError):
        return 0


def record_score(session, score):
    try:
        f = asked_flag(session)
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("%d\n" % score, encoding="utf-8")
    except OSError:
        pass


_REASON = (
    "Work concluded this session - a /goal objective was met, or something was committed, pushed "
    "or opened as a PR - so the choices behind it are now somebody else's to live with. Before "
    'you stop, invoke the decision-review skill (Skill tool, name '
    '"process-review-uncertain-decisions") and answer its question: which important decisions did '
    "you make that you are NOT confident about, what alternative did you not take, and what would "
    "settle it. Leave OUT every decision that is already clearly right - the suppression is the "
    "point, and a list that includes the settled ones puts the sorting back on the reader. If "
    "nothing is genuinely unsettled, say so in one line and stop."
)

# The repeat. Non-blocking, so it rides along next to the turn's result instead of stopping it -
# the same channel a PreToolUse nudge uses, which the Stop handler also accepts.
_REMINDER = (
    "More work concluded since the decision review. If any of it involved a call you are not "
    'confident about, say so now - `bitranox:process-review-uncertain-decisions` carries the '
    "question. Only the unsettled ones; silence is the right answer when there are none."
)


def main():
    try:
        event = json.load(sys.stdin)
    except Exception:                                     # noqa: BLE001 - never wedge a turn
        return 0
    session = str(event.get("session_id") or "")
    transcript = event.get("transcript_path") or ""
    if not session or not transcript:
        return 0
    try:
        score = conclusion_score(transcript_signals(transcript))
    except Exception:                                     # noqa: BLE001 - never wedge a turn
        return 0
    seen = last_score(session)
    verdict = decide(score, seen)
    if verdict == ASK_NONE:
        return 0
    record_score(session, score)                          # before emitting, so a crash cannot re-nag
    if verdict == ASK_BLOCK:
        sys.stdout.write(json.dumps({"decision": "block", "reason": _REASON}))
    else:
        sys.stdout.write(json.dumps({"hookSpecificOutput": {
            "hookEventName": "Stop", "additionalContext": _REMINDER}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
