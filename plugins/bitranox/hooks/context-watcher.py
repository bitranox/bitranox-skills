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

THE WINDOW comes from a LADDER, because each rung is exact where the next only infers. An explicit
`context_window` wins. Otherwise the session's own model id, WITH its variant, is read from an
unpinned subagent dispatch. Failing that - and this rung needs nothing but the transcript - the
model FAMILY from `message.model` fixes the ceiling (opus, fable, sonnet: 1M capable; haiku: 200K)
and the largest context observed proves which mode is running: a session that has carried more than
200K cannot be on the 200K variant. Below that the variant is genuinely unknown and 200K is assumed,
which asks early rather than going silent. Last rungs: the model this project has used most, then
200K.

The direction of every fallback is the same and deliberate. Assuming too SMALL asks early, which
costs a decline. Assuming too LARGE is silently inert - a 200K session handed a 400K threshold can
never reach it (it auto-compacts near 166K) and the misconfigured check cannot see it either,
because 166K is far under the assumed window. That failure is the one this hook exists to prevent,
so no rung may guess upward without proof.

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


# Maximum window per model FAMILY, matched on the id `message.usage` always carries. Source: the
# bundled `claude-api` skill's model table (cached 2026-06-24).
_FAMILY_MAX = (("claude-fable", 1_000_000), ("claude-mythos", 1_000_000),
               ("claude-opus", 1_000_000), ("claude-sonnet", 1_000_000),
               ("claude-haiku", 200_000), ("oss-128k", 128_000))


def family_max_window(model_id) -> int:
    """The LARGEST window this model family can run. PURE.

    `message.model` is always present and always the bare family id - this session reports
    `claude-opus-5` while running 1M - so it fixes the CEILING, never the actual window. Claude Code
    offers a 200K mode of the same family (that is why `claude-opus-4-6` and `claude-opus-4-6[1m]`
    are separate ids), and nothing in the family name says which is running.
    """
    mid = str(model_id or "").lower()
    for prefix, window in _FAMILY_MAX:
        if mid.startswith(prefix):
            return window
    return _DEFAULT_WINDOW


def window_from_evidence(model_id, peak_tokens):
    """The window PROVEN by the family ceiling plus the largest context actually observed. PURE.

    A family that cannot exceed 200K settles it outright. Otherwise the family could be running
    either mode, and the measurement decides: a session that has carried more than a 200K window can
    hold is provably on the large variant. Below that it is genuinely unknown, and 200K is the safe
    assumption - too small asks early, which costs a decline, while too large is the silently-inert
    failure where the threshold can never be reached.
    """
    ceiling = family_max_window(model_id)
    if ceiling <= _DEFAULT_WINDOW:
        return ceiling
    try:
        if int(peak_tokens or 0) > _DEFAULT_WINDOW:
            return ceiling
    except (TypeError, ValueError):
        pass
    return _DEFAULT_WINDOW


def model_from_dispatch(transcript_path, tail_bytes=_TAIL_BYTES):
    """The session's OWN model id, read from an unpinned subagent dispatch, or None. IMPURE.

    This is the only EXACT source for the current model, and it is exact because of a pairing: an
    `Agent` call whose input carries no `model` inherits the session's, and the tool result reports
    what it actually ran as `resolvedModel` - with the `[1m]` suffix that `message.model` drops.
    A dispatch that DID pin a model resolves to that model instead, so those are skipped; using them
    would report a subagent's tier as the session's.

    Absent when the session never dispatched an unpinned subagent, which is why this heads a ladder
    rather than standing alone.
    """
    try:
        size = os.path.getsize(transcript_path)
        with open(transcript_path, "rb") as handle:
            if size > tail_bytes:
                handle.seek(size - tail_bytes)
                handle.readline()
            data = handle.read()
    except (OSError, TypeError, ValueError):
        return None
    unpinned, found = set(), None
    for raw in data.splitlines():
        try:
            record = json.loads(raw.strip().decode("utf-8", "replace"))
        except (ValueError, AttributeError):
            continue
        if not isinstance(record, dict):
            continue
        for block in (record.get("message") or {}).get("content") or []:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use" and block.get("name") in ("Agent", "Task"):
                if not (block.get("input") or {}).get("model"):
                    unpinned.add(block.get("id"))
            elif block.get("type") == "tool_result" and block.get("tool_use_id") in unpinned:
                resolved = (record.get("toolUseResult") or {}).get("resolvedModel")
                if resolved:
                    found = resolved          # keep scanning: the LATEST unpinned one wins
    return found


def model_from_project(cwd, config_path=None):
    """The model this project has used MOST, or None. IMPURE (reads ~/.claude.json).

    `lastModelUsage` is keyed by the full model id - the one place the `[1m]` suffix survives - but
    it ACCUMULATES across sessions and models, so the entry is picked by cache-read volume rather
    than by window size. The dominant entry is the main session model by a wide margin (subagents
    contribute orders of magnitude less), and unlike "widest window ever recorded" it follows a
    switch to a smaller model instead of claiming the old one forever.
    """
    try:
        path = config_path or (pathlib.Path.home() / ".claude.json")
        projects = json.loads(pathlib.Path(path).read_text(encoding="utf-8")).get("projects") or {}
    except (OSError, ValueError, TypeError):
        return None
    here = str(cwd or "")
    candidates = [k for k in projects if here == k or here.startswith(k.rstrip("/") + "/")]
    if not candidates:
        return None
    entry = projects[max(candidates, key=len)]
    used = entry.get("lastModelUsage") if isinstance(entry, dict) else None
    if not isinstance(used, dict) or not used:
        return None

    def volume(item):
        stats = item[1] if isinstance(item[1], dict) else {}
        try:
            return int(stats.get("cacheReadInputTokens") or 0) + int(stats.get("inputTokens") or 0)
        except (TypeError, ValueError):
            return 0
    return max(used.items(), key=volume)[0]


def read_session(transcript_path, tail_bytes=_TAIL_BYTES):
    """(current_tokens, family_model, peak_tokens) from ONE tail read. IMPURE.

    The peak matters because it is what PROVES the large variant: a session that has carried more
    than a 200K window can hold cannot be running the 200K mode. It is taken over the tail only, so
    it is a lower bound on the true peak - which is the safe direction, since under-reporting the
    peak only makes the window assumption smaller and the ask earlier.
    """
    try:
        size = os.path.getsize(transcript_path)
        with open(transcript_path, "rb") as handle:
            if size > tail_bytes:
                handle.seek(size - tail_bytes)
                handle.readline()
            data = handle.read()
    except (OSError, TypeError, ValueError):
        return None, None, 0
    current, model, peak = None, None, 0
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
        peak = max(peak, total)
        if message.get("model"):
            model = message["model"]
    return current, model, peak


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


def resolve_window(cfg, cwd, transcript=None, model=None, peak=0):
    """(window, how it was established). IMPURE.

    A ladder, most authoritative first, because each rung is exact where the next only infers:
      1. an explicit `context_window` - the escape hatch, always wins;
      2. the session's own model id WITH its variant, from an unpinned subagent dispatch - exact;
      3. the model FAMILY (always in `message.model`) plus the largest context observed - the family
         fixes the ceiling, the measurement proves whether the large variant is running;
      4. the model this project has used most - right across sessions, stale right after a switch;
      5. the 200K default.
    """
    explicit = cfg.get("context_window") or 0
    try:
        if int(explicit) > 0:
            return int(explicit), "configured"
    except (TypeError, ValueError):
        pass
    if transcript:
        current = model_from_dispatch(transcript)
        if current:
            return window_for_model(current), "detected"
    if model:
        return window_from_evidence(model, peak), "evidenced"
    dominant = model_from_project(cwd)
    if dominant:
        return window_for_model(dominant), "inferred"
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
    tokens, model, peak = read_session(transcript)
    window, source = resolve_window(cfg, proj, transcript, model, peak)
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
