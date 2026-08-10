#!/usr/bin/env python3
"""Stop hook: once work has actually concluded, ask which decisions are still unsettled.

The decisions worth a second look are the ones that leave no trace in a diff - a default that
changes behaviour on upgrade, a version tier, a scope cut, a flaky test waved off. Nothing else
surfaces them: a code review reads what changed, and a verification gate asks whether a claim is
true, not whether a choice was right. The person who would ask is the person who has to remember
to ask, which is exactly what does not happen at the end of a long session.

**What counts as concluded, in priority order:**

1. A `/goal` objective was MET. Claude Code records the objective's progress in the transcript as
   an attachment, `{"type": "goal_status", "met": <bool>, "condition": ...}`, and the LAST such
   record is the current state. Reading it is what lets this hook fire at the end of a goal rather
   than somewhere in the middle of one.
2. A goal is RUNNING and not yet met - stay silent, even after a commit. A goal run commits as it
   goes, and those commits are milestones inside the work, not the end of it. This is also the
   safe choice: Claude Code treats a blocking Stop hook as a reason to stop continuing, so
   interrupting an unmet goal would cut short the very loop the user started.
3. No goal in play - then a commit, a push, or an opened PR is the conclusion. A file-count
   threshold was tried first and is a worse proxy in both directions: it fires mid-edit on a
   session that has concluded nothing, and stays silent on a one-line fix that shipped.

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


def reached_a_conclusion(signals):
    """True once the work is somebody else's to live with - a met goal, or a commit outside one."""
    if signals.goal_state == GOAL_MET:
        return True
    if signals.goal_state == GOAL_ACTIVE:
        return False        # a goal's own commits are milestones; do not cut its loop short
    return any(shell_text.is_gated_command(c) for c in signals.commands)


def should_ask(concluded, was_asked):
    """The whole policy: work has concluded, and this session has not been asked yet."""
    return bool(concluded) and not was_asked


def asked_flag(session):
    """Session-keyed marker that the ask already fired. Keyed by session so it cannot go stale."""
    return sig.touched_file(session).with_suffix(".decisions-asked")


def already_asked(session):
    try:
        return asked_flag(session).is_file()
    except OSError:
        return False


def mark_asked(session):
    try:
        f = asked_flag(session)
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text("1\n", encoding="utf-8")
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


def main():
    try:
        event = json.load(sys.stdin)
    except Exception:                                     # noqa: BLE001 - never wedge a turn
        return 0
    session = str(event.get("session_id") or "")
    transcript = event.get("transcript_path") or ""
    if not session or not transcript:
        return 0
    if already_asked(session):
        return 0                                          # cheap: no transcript read on later turns
    try:
        concluded = reached_a_conclusion(transcript_signals(transcript))
    except Exception:                                     # noqa: BLE001 - never wedge a turn
        return 0
    if not should_ask(concluded, was_asked=False):
        return 0
    mark_asked(session)                                   # before emitting, so a crash cannot re-nag
    sys.stdout.write(json.dumps({"decision": "block", "reason": _REASON}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
