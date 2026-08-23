"""Stop: refuse to end a turn that pushed to a CI repo and never looked at the result.

`ci-watch-nudge.py` records a sha when a push lands and clears it when the CI is watched. This is
the half a nudge cannot supply. PostToolUse cannot block, and the advisory channel was measured at
57% on this project's own history, so something has to make the watch non-optional. Stop is the
only event in this plugin's set that can: exit 2 or a `decision: "block"` prevents stopping and
continues the conversation.

Deliberately a ONE-SHOT block per continuation chain, not a loop. `stop_hook_active` is true when a
Stop hook already caused this continuation, and returning 0 then is what keeps a session that
genuinely cannot watch CI - `gh` broken, network down, CI never started - from being wedged with no
way out. The block therefore fires, the turn continues, and a second immediate stop is allowed
through. It still fires again on a LATER stop while the sha stays unwatched, because that is a new
chain. That is a real limit and is written down rather than overclaimed: this makes forgetting
loud, it does not make it impossible.

Only THIS session's pushes count, and only for `MAX_AGE_SECONDS`. A pending entry from an earlier
session blocking an unrelated later one is a failure mode already on the record here, from a
nap-owed gate that insisted the current session's context had been cleared when it had not.

Set BITRANOX_CI_WATCH to any value to bypass entirely.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import ci_watch_state as state

__all__ = ["enabled", "main", "sentinel_path", "verdict"]

_BYPASS_ENV = "BITRANOX_CI_WATCH"
# OPT-IN. The nudge ships on because it only injects context; blocking someone's turn on a repo
# they were deliberately not watching is a surprise that gets a plugin removed rather than
# configured, so the blocking half waits to be asked for.
_OPT_IN_NAME = ".bitranox-ci-watch-gate"
_CI_WAIT = Path(__file__).resolve().parent.parent / "skills" / "compuse-toolbox" / "scripts" / "ci_wait.py"


def sentinel_path() -> Path:
    """Where the opt-in marker lives. Resolved per call so HOME stays a real seam for tests."""
    return Path.home() / ".claude" / _OPT_IN_NAME


def enabled() -> bool:
    """Is the blocking half switched on for this machine?"""
    try:
        return sentinel_path().exists()
    except (OSError, RuntimeError):
        return False


def verdict(pending: list[dict], attempt: int = 1) -> str | None:
    """The block reason for these pending entries, or None when there is nothing to say."""
    if not pending:
        return None
    newest = max(pending, key=lambda e: float(e.get("at") or 0))
    sha = str(newest.get("sha") or "")
    if not sha:
        return None
    branch = str(newest.get("branch") or "HEAD")
    left = state.MAX_BLOCKS - attempt
    remaining = ("\nThis is the last reminder for this push; the gate releases after it."
                 if left <= 0 else
                 "\n%d further reminder(s) for this push before the gate releases." % left)
    extra = ("" if len(pending) == 1
             else "\n(%d pushes this session are still unchecked; this is the newest.)" % len(pending))
    return ("You pushed %s on %s and have not checked whether CI passed.%s\n\n"
            "A push is not the end of the change - watch the run and fix what it reports:\n"
            "    uv run %s --sha %s\n\n"
            "Exit 0 every run passed, 1 at least one did not, 2 could not tell. If it reds, fix it\n"
            "on this branch rather than leaving it for the next session to find.%s\n"
            "Set BITRANOX_CI_WATCH=1 to bypass this gate."
            % (sha[:12], branch, extra, _CI_WAIT, sha, remaining))


def main(raw: str | None = None) -> int:
    """Block the stop while a push from this session has unwatched CI. Always exits 0."""
    try:
        event = json.loads(raw if raw is not None else sys.stdin.read() or "{}")
    except (ValueError, TypeError, OSError):
        return 0
    if not isinstance(event, dict):
        return 0
    # A Stop hook already caused this continuation; blocking again is how a session gets wedged.
    if event.get("stop_hook_active"):
        return 0
    if os.environ.get(_BYPASS_ENV) or not enabled():
        return 0

    key = state.session_key(event)
    session = event.get("session_id") or ""
    if not key or not session:
        return 0

    try:
        pending = state.pending_for(key, session)
        if not pending:
            return 0
        newest = max(pending, key=lambda e: float(e.get("at") or 0))
        sha = str(newest.get("sha") or "")
        attempt = state.bump_blocks(key, sha) if sha else 1
        if attempt > state.MAX_BLOCKS:
            # Give up LOUDLY rather than silently: a gate that just stops speaking reads as broken.
            state.clear_sha(key, sha)
            print(json.dumps({"hookSpecificOutput": {
                "hookEventName": "Stop",
                "additionalContext": ("CI for %s was never checked and the watch gate has now "
                                      "released it after %d reminders. It will not ask again."
                                      % (sha[:12], state.MAX_BLOCKS))}}))
            return 0
        reason = verdict(pending, attempt)
    except Exception:  # noqa: BLE001 - a gate that crashes must not wedge a turn
        return 0
    if not reason:
        return 0

    print(json.dumps({"decision": "block", "reason": reason}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
