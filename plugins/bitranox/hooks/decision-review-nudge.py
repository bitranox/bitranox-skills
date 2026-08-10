#!/usr/bin/env python3
"""Stop hook: after a session that actually built something, ask which decisions are unsettled.

The decisions worth a second look are the ones that leave no trace in a diff - a default that
changes behaviour on upgrade, a version tier, a scope cut, a flaky test waved off. Nothing else
surfaces them: a code review reads what changed, and a verification gate asks whether a claim is
true, not whether a choice was right. The person who would ask is the person who has to remember
to ask, which is exactly what does not happen at the end of a long session.

So the ask fires on its own, ONCE per session, when the session has written enough to have made
real choices. It never blocks twice: the flag it writes is keyed by session id, so a flag left by
an earlier session can never satisfy this one (a per-PROJECT flag would, and has - it demanded
work for a compaction that happened in a different session).

The signal is the distinct-file count from `touched-paths.py`, the PostToolUse recorder that
already logs what each turn wrote. Reusing it keeps this hook from re-deriving "did real work
happen" a second way, and it is why the threshold is files rather than a parsed git command.

Pure standard library. Reads the event JSON on stdin. ALWAYS exits 0 - a nudge must never wedge
a turn.
"""

import json
import sys

import self_improve_signals as sig

# Below this, a session is answering questions or reading, not choosing. Three distinct files is
# the point where a turn has committed to something a reader cannot reconstruct from the diff.
_MIN_TOUCHED_PATHS = 3

_REASON = (
    "This session has written several files, so it has made choices that no diff shows. Before "
    "you stop, invoke the decision-review skill (Skill tool, name "
    '"process-review-uncertain-decisions") and answer its question: which important decisions '
    "did you make that you are NOT confident about, what alternative did you not take, and what "
    "would settle it. Leave OUT every decision that is already clearly right - the suppression is "
    "the point, and a list that includes the settled ones puts the sorting back on the reader. If "
    "nothing is genuinely unsettled, say so in one line and stop."
)


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


def should_ask(touched_count, was_asked, min_paths=_MIN_TOUCHED_PATHS):
    """The whole policy, as one pure decision: enough work done, and not asked yet this session."""
    return touched_count >= min_paths and not was_asked


def main():
    try:
        event = json.load(sys.stdin)
    except Exception:                                     # noqa: BLE001 - never wedge a turn
        return 0
    session = str(event.get("session_id") or "")
    if not session:
        return 0
    try:
        touched = len(sig.read_touched_paths(session))
    except Exception:                                     # noqa: BLE001 - never wedge a turn
        return 0
    if not should_ask(touched, already_asked(session)):
        return 0
    mark_asked(session)                                   # before emitting, so a crash cannot re-nag
    sys.stdout.write(json.dumps({"decision": "block", "reason": _REASON}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
