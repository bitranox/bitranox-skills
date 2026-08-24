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

THE WINDOW comes from the model FAMILY, which `message.model` carries on every assistant record.
That id never includes Claude Code's `[1m]` suffix, and it does not need to: measured across 1485
local transcripts, every non-haiku family has actually carried far more than a 200K window can hold
(opus-5 999,946; opus-4-8 999,911; fable-5 997,450; sonnet-5 665,313), while haiku peaked at
119,393. The peaks stopping just under 1,000,000 is the window boundary showing itself in the data.
So the family settles it: opus, fable, sonnet and mythos are 1M; haiku is 200K.

THE ASSUMPTION IN THAT TABLE, stated because its failure is silent. Those transcripts come from ONE
machine and one account tier, so the table asserts that current opus, fable, sonnet and mythos run
1M for EVERYONE. If some tier or plan runs a 200K opus, that session gets a 400K threshold it can
never reach - it would compact near 166K - and the misconfigured check below cannot catch it either,
because 166K is far under the 1M being assumed. The symptom is the hook simply never speaking, which
is the symptom nobody reports.

The remedy is `context_window`: setting it to a real token count overrides the table entirely. A
deliberate trade - the alternative was to assume 200K until each session proved otherwise, which is
correct for every tier but asks early on every genuine 1M session.

When the measured context exceeds the window in use, that IS reported rather than ignored - a
threshold nothing can cross is indistinguishable from a watcher that works. It catches an
over-large explicit knob; it cannot catch an over-large assumption, per the paragraph above.

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

# Context window per model FAMILY, matched on the id `message.model` carries. Measured over 1485
# local transcripts rather than inferred: every non-haiku family has carried far more than a 200K
# window could hold, and the observed peaks stop just under 1,000,000. Claude Code's `[1m]` suffix
# appears in `~/.claude.json` but never in `message.model`, and it turns out to be redundant - the
# current families run 1M regardless. Source for the roster: the bundled `claude-api` skill's model
# table (cached 2026-06-24).
_FAMILY_WINDOWS = (("claude-fable", 1_000_000), ("claude-mythos", 1_000_000),
                   ("claude-opus", 1_000_000), ("claude-sonnet", 1_000_000),
                   ("claude-haiku", 200_000), ("oss-128k", 128_000))


def window_for_model(model_id) -> int:
    """The context window this model family runs. PURE.

    An unknown family falls back to 200K, which errs SMALL on purpose: too small asks early and
    costs a decline, while too large sets a threshold the session can never reach and the hook goes
    silently inert - the failure this whole check exists to prevent.
    """
    mid = str(model_id or "").lower()
    if mid.endswith("[1m]"):                  # `~/.claude.json` spells it this way; harmless here
        mid = mid[:-4]
    for prefix, window in _FAMILY_WINDOWS:
        if mid.startswith(prefix):
            return window
    return _DEFAULT_WINDOW


def read_session(transcript_path, tail_bytes=_TAIL_BYTES):
    """(current_tokens, family_model) from ONE tail read. IMPURE.

    Both come from the same records, so reading them together avoids a second pass over a
    multi-megabyte transcript on every turn.
    """
    try:
        size = os.path.getsize(transcript_path)
        with open(transcript_path, "rb") as handle:
            if size > tail_bytes:
                handle.seek(size - tail_bytes)
                handle.readline()
            data = handle.read()
    except (OSError, TypeError, ValueError):
        return None, None
    current, model = None, None
    for raw in data.splitlines():
        try:
            record = json.loads(raw.strip().decode("utf-8", "replace"))
        except (ValueError, AttributeError):
            continue
        if not isinstance(record, dict):
            continue
        message = record.get("message") or {}
        usage = message.get("usage")
        if not isinstance(usage, dict):
            continue
        try:
            total = (int(usage.get("input_tokens") or 0)
                     + int(usage.get("cache_creation_input_tokens") or 0)
                     + int(usage.get("cache_read_input_tokens") or 0))
        except (TypeError, ValueError):
            continue
        current = total                       # the LAST one wins; the loop runs forward
        if message.get("model"):
            model = message["model"]
    return current, model


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


def resolve_window(cfg, model=None):
    """(window, how it was established). PURE.

    An explicit `context_window` wins - the escape hatch for a model the table has not met.
    Otherwise the family decides, and failing that the 200K default.
    """
    explicit = cfg.get("context_window") or 0
    try:
        if int(explicit) > 0:
            return int(explicit), "configured"
    except (TypeError, ValueError):
        pass
    if model:
        return window_for_model(model), "detected"
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
    tokens, model = read_session(transcript)
    window, source = resolve_window(cfg, model)
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
