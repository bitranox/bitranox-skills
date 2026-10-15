#!/usr/bin/env python3
"""PreToolUse(EnterWorktree) refusal: the first EnterWorktree of a session is refused ONCE, with a note.

Once a session is isolated in a worktree, every git aimed at another checkout is refused - the main
checkout included, and a `!` command the user types as well. So any git the session asked the user
to run in the main checkout (a pull, a fast-forward, a commit) has to happen BEFORE the switch, and
a note that arrives after it is too late. Measured twice (2026-10-08, 2026-10-12): a session entered
a worktree while a fast-forward it had asked the user for was still pending, and could not finish it.

The user chose a refusal over a note in the git-worktrees skill and over additionalContext
(2026-10-12): it is deterministic and lands before the switch. The cost is one extra call in a
session that uses EnterWorktree, even when nothing is pending. The re-call passes, and so does every
later EnterWorktree of the session - by `name` or by `path` alike.

Probe, interactive CLI 2.1.300 with a throwaway --settings deny hook: the deny stopped the call
before the switch - no worktree, no branch, the cwd unchanged - and the model quoted the reason.

The flag is set only once it is STORED: a refusal that could not be recorded would refuse every
re-call forever, so an unwritable store, a missing session id or any error lets the call through.
Exit 0 always; the refusal is a permissionDecision on stdout. ASCII only.
"""
from __future__ import annotations

import json
import sys

from self_improve_signals import session_state_path

_REFUSED_FLAG = ".enter-worktree-refused"

REFUSAL = (
    "Refused once per session, before the switch: once this session is in a worktree, every git "
    "aimed at another checkout is refused - the main checkout included, and a `!` command the user "
    "types as well. If you asked the user to run git in the main checkout (a pull, a fast-forward, "
    "a commit) and it has not happened yet, have them do it now; if you still need git there "
    "yourself, do it first, or plan an ExitWorktree with action keep to return for it. Then call "
    "EnterWorktree again - it passes."
)


def _flag(session):
    """The session's refused flag path, or None when there is no usable session id."""
    if not isinstance(session, str) or not session.strip():
        return None
    try:
        return session_state_path(session, _REFUSED_FLAG)
    except Exception:  # noqa: BLE001 - no state, no refusal: the entry passes
        return None


def should_refuse(session):
    """True for the first EnterWorktree of `session`, recording that it was refused.

    False for every later one, and whenever the refusal could not be recorded.
    """
    flag = _flag(session)
    if flag is None or flag.exists():
        return False
    try:
        flag.parent.mkdir(parents=True, exist_ok=True)
        flag.write_text("refused\n", encoding="utf-8")
    except OSError:
        return False
    return True


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:  # noqa: BLE001 - no/invalid stdin: do nothing
        return 0
    if not isinstance(event, dict) or event.get("tool_name") != "EnterWorktree":
        return 0
    if should_refuse(event.get("session_id")):
        sys.stdout.write(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": REFUSAL,
        }}) + "\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - a broken hook must never wedge a turn
        sys.exit(0)
