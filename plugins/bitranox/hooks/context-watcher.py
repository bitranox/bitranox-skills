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

THE WINDOW is DETECTED, not configured. The transcript's `message.model` is the bare
`claude-opus-5` with no variant, but `~/.claude.json` records per-project `lastModelUsage` keyed by
the FULL model id - `claude-opus-5[1m]` and `claude-opus-4-6` are separate keys - so the `[1m]`
suffix that distinguishes a 1M window from a 200k one survives there.

A project accumulates several models (subagents run haiku and sonnet), so the LARGEST window among
them is taken. That is the safe direction and the asymmetry is the reason: assuming too small makes
the threshold unreachable and the hook silently inert, while assuming too large only asks later,
where auto-compact still catches the session. `context_window` remains as an explicit override for
a machine where the detection cannot see the model.

THE THRESHOLD is min(percentage of the window, absolute cap), because the two research findings
disagree on a big window and both are worth honouring. The percentage leg keeps a cushion below
auto-compact so there is room to actually write the handover; the absolute leg catches the case the
percentage misses entirely - a 1M session sailing past the measured rot onset while only 40% full.

PROVENANCE OF THE 400k CAP, stated plainly because it gates an interruption: it is one published
finding (Chroma's 2025 context-rot study, which measured accuracy falling from roughly 300-400k on a
1M window) read second-hand from a summary, not something measured here. It is wrong in the safe
direction - too low means asking early, which costs a decline - and the knob exists to move it.

RE-ASKS are spaced by 10% of the window rather than happening once. A decline at 40% is "not yet",
not "never", and by 90% the question has changed from "quality is drifting" to "the harness is about
to discard detail". Yields entirely when a post-compaction nap is already owed: the Stop gate
refuses to stop on that obligation and stacking a second block would make the two fight over the
same turn. Fail-open on every error path - a broken watcher must never wedge a turn.

Pure standard library, ASCII only; launched via run-python.sh so it works on Windows too.
"""
from __future__ import annotations

import json
import os
import pathlib
import sys

import self_improve_signals as sig

# Enough tail to reach a recent assistant record even when the last turn wrote a large tool result,
# while staying a single bounded read on a multi-megabyte transcript.
_TAIL_BYTES = 2 * 1024 * 1024

_DEFAULT_WINDOW = 200_000
_RE_ASK_FRACTION = 10           # re-ask each time context grows another 1/10th of the window

# Models offering a 1M-context variant, which Claude Code selects with a `[1m]` suffix on the id.
# Source: the bundled `claude-api` skill's model table (cached 2026-06-24). Haiku is deliberately
# ABSENT - it is 200K with no 1M variant - so a suffix on it could only be a parsing error, and
# treating the set as an allowlist means a mis-parsed id degrades to the safe 200K rather than
# silently claiming a window five times too large.
_MILLION_CAPABLE = frozenset({
    "claude-fable-5", "claude-mythos-5",
    "claude-opus-5", "claude-opus-4-8", "claude-opus-4-7", "claude-opus-4-6",
    "claude-sonnet-5", "claude-sonnet-4-6",
})

# Non-1M windows that are not the 200K default. Everything unlisted falls back to 200K.
_MODEL_WINDOWS = {"oss-128k-claude": 128_000}


def window_for_model(model_id) -> int:
    """The context window a Claude Code model id implies. PURE.

    Claude Code marks the 1M variant with a `[1m]` suffix, and that suffix is the ONLY thing that
    distinguishes it - `claude-opus-4-6` and `claude-opus-4-6[1m]` are separate ids. The base model
    supporting 1M is not enough: without the suffix the session is running the 200K mode.
    """
    mid = str(model_id or "")
    wants_million = mid.endswith("[1m]")
    base = mid[:-4] if wants_million else mid
    if wants_million and base in _MILLION_CAPABLE:
        return 1_000_000
    return _MODEL_WINDOWS.get(base, _DEFAULT_WINDOW)


def detect_window(cwd, config_path=None):
    """The largest window among the models this project has actually used, or None. IMPURE (reads).

    `~/.claude.json` records `projects.<path>.lastModelUsage` keyed by the FULL model id, suffix
    included, which is the one place the variant survives - the transcript stores the bare name.

    The LARGEST is taken because a project accumulates several models: subagents run haiku and
    sonnet alongside the main model. The asymmetry decides the tie-break - too small makes the
    threshold unreachable and the hook silently inert, too large only asks later, where auto-compact
    still catches the session.
    """
    try:
        path = config_path or (pathlib.Path.home() / ".claude.json")
        projects = json.loads(pathlib.Path(path).read_text(encoding="utf-8")).get("projects") or {}
    except (OSError, ValueError, TypeError):
        return None
    here = str(cwd or "")
    # Exact match first, then the longest recorded ancestor - a hook can fire from a subdirectory.
    candidates = [k for k in projects if here == k or here.startswith(k.rstrip("/") + "/")]
    if not candidates:
        return None
    entry = projects[max(candidates, key=len)]
    used = entry.get("lastModelUsage") if isinstance(entry, dict) else None
    if not isinstance(used, dict) or not used:
        return None
    return max(window_for_model(m) for m in used)


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
    """Session-keyed state, so one left by an older session can never suppress this one."""
    return sig.touched_file(session).with_suffix(".handover-asked")


def already_reported(session) -> bool:
    """True once this session has been told anything - the misconfigured notice says itself once."""
    try:
        return _asked_flag(session).is_file()
    except OSError:
        return False


def asked_at(session) -> int:
    """Context level of the last ask, or 0 when this session has not been asked. IMPURE (reads)."""
    try:
        return int(_asked_flag(session).read_text(encoding="utf-8").strip() or 0)
    except (OSError, ValueError):
        return 0


def mark_asked(session, tokens) -> None:
    try:
        flag = _asked_flag(session)
        flag.parent.mkdir(parents=True, exist_ok=True)
        flag.write_text(str(int(tokens)) + "\n", encoding="utf-8")
    except (OSError, TypeError, ValueError):
        pass                                  # an unwritable flag means it may ask twice, not wedge


def due(tokens, limit, window, last_asked) -> bool:
    """True when this reading earns an ask. PURE.

    The first ask is the threshold. After that, a decline is "not yet" rather than "never", so the
    next one waits until context has grown another 1/10th of the window - by which point the
    question has genuinely changed rather than being the same one repeated.
    """
    if tokens < limit:
        return False
    if not last_asked:
        return True
    return tokens >= last_asked + max(1, int(window) // _RE_ASK_FRACTION)


def _offer(detail) -> str:
    return (
        "This session is carrying %(tokens)s tokens of context, past the %(limit)s at which a "
        "handover is worth writing (%(pct)s%% of a %(window)s window, %(source)s, capped at "
        "%(cap)s). Quality degrades well before the window fills, and the harness will not compact "
        "until about 83%% - at which point it DISCARDS working detail rather than preserving it."
        "\n\n"
        "Ask the user whether to write `handover.md` now and start a fresh session. If they agree, "
        "invoke bitranox:meta-context-watcher, which says what the file must contain. If they "
        "decline, carry on - the next ask waits until context has grown another tenth of the "
        "window, so declining costs one interruption, not a stream of them."
    ) % {k: format(v, ",") if isinstance(v, int) and k != "pct" else v for k, v in detail.items()}


def _misconfigured(detail) -> str:
    return (
        "The context watcher measured %(tokens)s tokens, which is MORE than the %(window)s window "
        "it was measuring against (%(source)s) - so the threshold can never be reached. This is "
        "reported rather than ignored because a threshold nothing can cross looks exactly like a "
        "watcher that works.\n\n"
        "The window is normally derived from the model this project has used. If that could not be "
        "read, set `context_window` to the real figure via bitranox:meta-memory-settings. Until "
        "then this check is inert."
    ) % {k: format(v, ",") if isinstance(v, int) and k != "pct" else v for k, v in detail.items()}


def already_reported(session) -> bool:
    """True once this session has been told anything - the misconfigured notice says itself once."""
    try:
        return _asked_flag(session).is_file()
    except OSError:
        return False


def asked_at(session) -> int:
    """Context level of the last ask, or 0 when this session has not been asked. IMPURE (reads)."""
    try:
        return int(_asked_flag(session).read_text(encoding="utf-8").strip() or 0)
    except (OSError, ValueError):
        return 0


def mark_asked(session, tokens) -> None:
    try:
        flag = _asked_flag(session)
        flag.parent.mkdir(parents=True, exist_ok=True)
        flag.write_text(str(int(tokens)) + "\n", encoding="utf-8")
    except (OSError, TypeError, ValueError):
        pass                                  # an unwritable flag means it may ask twice, not wedge


def due(tokens, limit, window, last_asked) -> bool:
    """True when this reading earns an ask. PURE.

    The first ask is the threshold. After that, a decline is "not yet" rather than "never", so the
    next one waits until context has grown another 1/10th of the window - by which point the
    question has genuinely changed rather than being the same one repeated.
    """
    if tokens < limit:
        return False
    if not last_asked:
        return True
    return tokens >= last_asked + max(1, int(window) // _RE_ASK_FRACTION)


def _offer(detail) -> str:
    return (
        "This session is carrying %(tokens)s tokens of context, past the %(limit)s at which a "
        "handover is worth writing (%(pct)s%% of a %(window)s window, %(source)s, capped at "
        "%(cap)s). Quality degrades well before the window fills, and the harness will not compact "
        "until about 83%% - at which point it DISCARDS working detail rather than preserving it."
        "\n\n"
        "Ask the user whether to write `handover.md` now and start a fresh session. If they agree, "
        "invoke bitranox:meta-context-watcher, which says what the file must contain. If they "
        "decline, carry on - the next ask waits until context has grown another tenth of the "
        "window, so declining costs one interruption, not a stream of them."
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


def resolve_window(cfg, cwd):
    """The window to measure against, and where it came from. IMPURE (may read the config file).

    An explicit `context_window` always wins - it is the escape hatch for a machine where detection
    cannot see the model. Otherwise the model this project has actually used decides it.
    """
    explicit = cfg.get("context_window") or 0
    try:
        if int(explicit) > 0:
            return int(explicit), "configured"
    except (TypeError, ValueError):
        pass
    detected = detect_window(cwd)
    if detected:
        return detected, "detected"
    return _DEFAULT_WINDOW, "assumed"


def decide(event, cfg):
    """The block reason for this Stop event, or None to stay quiet. IMPURE (reads the transcript)."""
    session = str(event.get("session_id") or "")
    transcript = event.get("transcript_path") or ""
    if not session or not transcript:
        return None
    if not cfg.get("nudges", True):
        return None
    # A post-compaction nap is already an obligation the Stop gate refuses to stop on. Two blocks
    # on one turn would fight over it and burn the consecutive-block budget, so this one yields.
    proj = event.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    try:
        if sig.is_nap_owed(proj):
            return None
    except Exception:                         # noqa: BLE001 - a missing helper must not wedge a turn
        pass
    window, source = resolve_window(cfg, proj)
    tokens = context_tokens(transcript)
    state, detail = verdict(tokens, window,
                            cfg.get("context_handover_pct", 70),
                            cfg.get("context_handover_cap", 400000))
    if not detail:
        return None
    detail["source"] = source
    if state == "misconfigured":
        if already_reported(session):
            return None
        mark_asked(session, tokens)
        return _misconfigured(detail)
    if state == "offer" and due(tokens, detail["limit"], window, asked_at(session)):
        mark_asked(session, tokens)
        return _offer(detail)
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
