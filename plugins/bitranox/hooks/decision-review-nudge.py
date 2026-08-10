#!/usr/bin/env python3
"""Stop hook: once work has actually concluded, ask which decisions are still unsettled.

The decisions worth a second look are the ones that leave no trace in a diff - a default that
changes behaviour on upgrade, a version tier, a scope cut, a flaky test waved off. Nothing else
surfaces them: a code review reads what changed, and a verification gate asks whether a claim is
true, not whether a choice was right. The person who would ask is the person who has to remember
to ask, which is exactly what does not happen at the end of a long session.

**The trigger is a commit, a push, or an opened PR** - the moment work stops being in progress and
starts being something somebody else will live with. A file-count threshold was tried first and is
a worse proxy in both directions: it fires mid-edit on a session that has not concluded anything,
and it stays silent on a one-line fix that shipped. The detection is `shell_text.is_gated_command`,
the same predicate the repo gate blocks on, so the two cannot disagree about what counts.

It asks ONCE per session. The flag is keyed by session id, so a flag left behind by an earlier
session can never satisfy this one (a per-PROJECT flag would, and has - it demanded work for a
compaction that happened in a different session).

Pure standard library. Reads the event JSON on stdin. ALWAYS exits 0 - a nudge must never wedge
a turn.
"""

import json
import sys

import self_improve_signals as sig
import shell_text

# Transcripts reach many MB in a long session. This is a whole-file scan rather than a tail read,
# because the commit that concluded the work may be many turns back - but it runs at most once per
# session (the flag short-circuits every later turn), so the cost is paid once.
_MAX_TRANSCRIPT_BYTES = 8 * 1024 * 1024


def bash_commands(transcript_path, max_bytes=_MAX_TRANSCRIPT_BYTES):
    """Every Bash command string in the transcript, oldest first. [] when unreadable."""
    out = []
    try:
        with open(transcript_path, "r", encoding="utf-8", errors="replace") as fh:
            if fh.read(0) is None:                        # pragma: no cover - defensive
                return []
            read = 0
            for line in fh:
                read += len(line)
                if read > max_bytes:
                    break
                try:
                    msg = json.loads(line)
                except ValueError:
                    continue                              # a partial last line is normal
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
                        out.append(cmd)
    except OSError:
        return []
    return out


def reached_a_conclusion(commands):
    """True once something was committed, pushed, or opened as a PR."""
    return any(shell_text.is_gated_command(c) for c in commands)


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
    "Work concluded this session - something was committed, pushed, or opened as a PR - so the "
    "choices behind it are now somebody else's to live with. Before you stop, invoke the "
    'decision-review skill (Skill tool, name "process-review-uncertain-decisions") and answer its '
    "question: which important decisions did you make that you are NOT confident about, what "
    "alternative did you not take, and what would settle it. Leave OUT every decision that is "
    "already clearly right - the suppression is the point, and a list that includes the settled "
    "ones puts the sorting back on the reader. If nothing is genuinely unsettled, say so in one "
    "line and stop."
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
        concluded = reached_a_conclusion(bash_commands(transcript))
    except Exception:                                     # noqa: BLE001 - never wedge a turn
        return 0
    if not should_ask(concluded, was_asked=False):
        return 0
    mark_asked(session)                                   # before emitting, so a crash cannot re-nag
    sys.stdout.write(json.dumps({"decision": "block", "reason": _REASON}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
