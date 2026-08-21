#!/usr/bin/env python3
"""Stop hook: offer a handover before the session's context degrades or the harness compacts it.

A long session gets worse before it gets full, and nothing says so. Chroma's 2025 study measured
accuracy falling from roughly 300-400k tokens on a 1M window and from about 50k on a 200k one, with
the lost-in-the-middle effect costing 30% or more on retrieval. Claude Code's own auto-compact does
not act until roughly 83% of the window, and that ceiling is a hard cap - CLAUDE_AUTOCOMPACT_PCT_
OVERRIDE only lowers it. So there is a long stretch where the session is measurably worse than it
reads, and when the harness finally does act it COMPACTS, which discards working detail rather than
preserving it.

This repo already handles compaction, but only in retrospect: `PreCompact` salvages learning signals
and `PostCompact` nudges `meta-dream-nap` to tidy MEMORY. Neither watches context approaching the
wall, and neither writes down TASK STATE - the nap deliberately prunes that as noise.

HOW THE SIZE IS MEASURED, which is the part that had to be discovered rather than assumed. NO hook
event carries a token count: the only token fields in the whole hook contract are `max_output_tokens`
as a StopFailure error type and a subagent's `totalTokens`, neither of which is session context. But
the transcript records real per-request usage, so the last record carrying `message.usage` gives

    input_tokens + cache_creation_input_tokens + cache_read_input_tokens

which is the context that request actually carried - a measurement, not a bytes/4 proxy. It also
self-corrects after a compaction, because the next request's usage drops on its own.

WHAT CANNOT BE MEASURED is the window. The transcript records the model as `claude-opus-5`, never
the `[1m]` suffix that distinguishes a 1M window from a 200k one, so the limit has to be configured
(`context_window`). That asymmetry is why the mis-set case is reported loudly rather than silently:
a window smaller than the context we just measured is a threshold that can never be crossed, and a
watcher that can never fire is indistinguishable from one that works.

THE THRESHOLD is min(percentage of the window, absolute cap), because the two research findings
disagree on a big window and both are worth honouring. The percentage leg keeps a cushion below
auto-compact so there is room to actually write the handover; the absolute leg catches the case the
percentage misses entirely - a 1M session sailing past the measured rot onset while only 40% full.

Blocks at most ONCE per session, and yields entirely when a post-compaction nap is already owed:
the Stop gate refuses to stop on that obligation, and stacking a second block would make the two
fight over the same turn. Fail-open on every error path - a broken watcher must never wedge a turn.

Pure standard library, ASCII only; launched via run-python.sh so it works on Windows too.
"""
from __future__ import annotations

import json
import os
import sys

import self_improve_signals as sig

# Enough tail to reach a recent assistant record even when the last turn wrote a large tool result,
# while staying a single bounded read on a multi-megabyte transcript.
_TAIL_BYTES = 2 * 1024 * 1024


def context_tokens(transcript_path, tail_bytes=_TAIL_BYTES):
    """Context carried by the most recent request, or None when it cannot be read. IMPURE (reads).

    The three fields sum to what the request actually sent: fresh input, whatever was written to
    cache this turn, and whatever was read from cache. Omitting the cache legs would report a
    handful of tokens on a session hundreds of thousands deep, because almost all of a long
    session's context arrives as a cache read.

    Scans the tail BACKWARDS and stops at the first usage record, so the answer is the latest one.
    """
    try:
        size = os.path.getsize(transcript_path)
        with open(transcript_path, "rb") as handle:
            if size > tail_bytes:
                handle.seek(size - tail_bytes)
                handle.readline()             # drop the partial line the seek landed in
            data = handle.read()
    except (OSError, TypeError, ValueError):
        return None
    for raw in reversed(data.splitlines()):
        line = raw.strip()
        if not line:
            continue
        try:
            record = json.loads(line.decode("utf-8", "replace"))
        except ValueError:
            continue                          # a tail read can start mid-line
        if not isinstance(record, dict):
            continue
        usage = (record.get("message") or {}).get("usage")
        if not isinstance(usage, dict):
            continue
        try:
            return (int(usage.get("input_tokens") or 0)
                    + int(usage.get("cache_creation_input_tokens") or 0)
                    + int(usage.get("cache_read_input_tokens") or 0))
        except (TypeError, ValueError):
            return None
    return None


def threshold(window, pct, cap):
    """The token count at which a handover is offered. PURE.

    Whichever leg bites first. Both are floored at 1 so a nonsensical config cannot produce a
    threshold of zero, which would fire on every session from its first turn.
    """
    try:
        by_pct = int(window) * int(pct) // 100
        return max(1, min(by_pct, int(cap)))
    except (TypeError, ValueError):
        return None


def verdict(tokens, window, pct, cap):
    """('quiet'|'offer'|'misconfigured', detail dict). PURE - all the arithmetic, no IO.

    `misconfigured` is a real answer, not an error: measuring more context than the window is
    supposed to hold means `context_window` is wrong (a 1M model left on the 200k default), and
    saying so is the difference between a watcher that reports and one that silently never fires.
    """
    limit = threshold(window, pct, cap)
    if tokens is None or limit is None:
        return "quiet", {}
    detail = {"tokens": tokens, "window": int(window), "limit": limit,
              "pct": int(pct), "cap": int(cap)}
    if tokens > int(window):
        return "misconfigured", detail
    if tokens >= limit:
        return "offer", detail
    return "quiet", detail


def _asked_flag(session):
    """Session-keyed flag, so one left by an older session can never suppress this one."""
    return sig.touched_file(session).with_suffix(".handover-asked")


def already_asked(session) -> bool:
    try:
        return _asked_flag(session).is_file()
    except OSError:
        return False


def mark_asked(session) -> None:
    try:
        flag = _asked_flag(session)
        flag.parent.mkdir(parents=True, exist_ok=True)
        flag.write_text("1\n", encoding="utf-8")
    except OSError:
        pass                                  # an unwritable flag means it may ask twice, not wedge


def _offer(detail) -> str:
    return (
        "This session is carrying %(tokens)s tokens of context, past the %(limit)s at which a "
        "handover is worth writing (%(pct)s%% of a %(window)s window, capped at %(cap)s). Quality "
        "degrades well before the window fills, and the harness will not compact until about 83%% - "
        "at which point it DISCARDS working detail rather than preserving it.\n\n"
        "Ask the user whether to write `handover.md` now and start a fresh session. If they agree, "
        "invoke bitranox:meta-context-watcher, which says what the file must contain. If they "
        "decline, carry on - this is asked once per session and will not interrupt again."
    ) % {k: format(v, ",") if isinstance(v, int) and k != "pct" else v for k, v in detail.items()}


def _misconfigured(detail) -> str:
    return (
        "The context watcher measured %(tokens)s tokens, which is MORE than the %(window)s window "
        "it was told to measure against - so `context_window` is wrong and the handover threshold "
        "can never be reached. This is reported rather than ignored because a threshold nothing "
        "can cross looks exactly like a watcher that works.\n\n"
        "Tell the user to set `context_window` to their real window (1000000 on a 1M model) via "
        "bitranox:meta-memory-settings. Until then this check is inert."
    ) % {k: format(v, ",") if isinstance(v, int) and k != "pct" else v for k, v in detail.items()}


def decide(event, cfg):
    """The block reason for this Stop event, or None to stay quiet. IMPURE (reads the transcript)."""
    session = str(event.get("session_id") or "")
    transcript = event.get("transcript_path") or ""
    if not session or not transcript:
        return None
    if not cfg.get("nudges", True):
        return None
    if already_asked(session):
        return None
    # A post-compaction nap is already an obligation the Stop gate refuses to stop on. Two blocks
    # on one turn would fight over it and burn the consecutive-block budget, so this one yields.
    proj = event.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    try:
        if sig.is_nap_owed(proj):
            return None
    except Exception:                         # noqa: BLE001 - a missing helper must not wedge a turn
        pass
    state, detail = verdict(context_tokens(transcript),
                            cfg.get("context_window", 200000),
                            cfg.get("context_handover_pct", 70),
                            cfg.get("context_handover_cap", 400000))
    if state == "offer":
        mark_asked(session)
        return _offer(detail)
    if state == "misconfigured":
        mark_asked(session)
        return _misconfigured(detail)
    return None


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:                         # noqa: BLE001 - no/invalid stdin: do nothing
        return 0
    if not isinstance(event, dict):
        return 0
    try:
        reason = decide(event, sig.load_config())
    except Exception:                         # noqa: BLE001 - a broken watcher must never wedge a turn
        return 0
    if reason:
        sys.stdout.write(json.dumps({"decision": "block", "reason": reason}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:                         # noqa: BLE001 - fail open
        sys.exit(0)
