#!/usr/bin/env python3
"""SubagentStop hook: don't let a subagent's learnings die in its own transcript.

The capture nudge (`self-improve-gate.py`) is a MAIN-session Stop hook. Nothing scanned a
subagent's transcript, and a named/background agent's final text is not returned to the main
session at all unless it SendMessages it - so a correction, a self-admitted miss, or a discovery a
subagent made was LOST unless the main agent happened to restate it.

A subagent cannot cleanly write curated memory itself (it is scoped to one task, and its cwd/subject
may differ from the fact's real home), so this hook only DETECTS and BUFFERS: it scans the
subagent's transcript for the same learning signals the main gate uses and queues the hits for the
main session's capture step to route (`--proj` by SUBJECT) and write.

Event shape is PROBE-VERIFIED on the live harness (`.plan/probes/probe_hook_events.py`, 2026-07-17):
`transcript_path` on a SubagentStop is the MAIN session's transcript - scanning it would read the
wrong conversation. The subagent's own transcript is `agent_transcript_path`
(`.../<session>/subagents/agent-<agent_id>.jsonl`, isSidechain). `last_assistant_message` carries the
subagent's final text for free. Re-run the probe after a Claude Code upgrade.

With `classifier_backend = jev` and `classifier_subagent_signal = shadow`, every assistant message
of the subagent is also handed to the classifier's detached shadow child, labelled with the verdict
the patterns reached (strict, broad_only or none), so the log can show how often a broad-only hit -
which still buffers, and so still blocks the main Stop - is a learning at all. The buffer itself is
never changed by it.

With `classifier_subagent_signal = decide`, Jev decides instead of the patterns: the same messages
are asked from inside the hook, in parallel and under the classifier's deadline, and a message is
buffered when either question reaches the site threshold. The site earned that by passing the
pre-registered decide rule: in a blind review of every disagreement the patterns were wrong on 24
of 30 and Jev on 6, and all seven broad-only hits in it were noise. A message Jev does not answer,
and an earlier one the request cap left out, falls back to the STRICT patterns alone - the broad
ones are what the review showed to be noise, so they never decide. One row per subagent is
appended to the shadow log, naming the path and each asked message's decision.

Pure standard library. ALWAYS exits 0 and never emits a decision: a subagent finishing must never be
blocked or wedged by this.
"""
import json
import sys

import classifier
import self_improve_signals as sig

_MAX_BYTES = 2_000_000        # tail cap: a subagent transcript is small, but never read unbounded
_SNIPPET = 200
SITE = "subagent_signal"
# Messages per shadow request set, the LAST ones kept: a subagent's report and its discoveries sit
# at the end. Measured over 30 days of transcripts: 16,089 assistant messages in 2,998 subagent
# runs, about 5.4 a run, so the cap binds only on long runs and bounds what one run can cost.
SHADOW_MAX_MESSAGES = 12


def _text(content):
    """Flatten a transcript message's content (string, or list of blocks) to text."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(b["text"] for b in content
                        if isinstance(b, dict) and isinstance(b.get("text"), str))
    return ""


def _messages(path):
    """(role, text) for each user/assistant record in the subagent transcript tail."""
    out = []
    try:
        with open(path, "rb") as fh:
            fh.seek(0, 2)
            size = fh.tell()
            start = max(0, size - _MAX_BYTES)
            if start:
                # Drop the partial line the seek landed in - unless it landed exactly on the first
                # byte of a record, which is only knowable from the byte BEFORE it. Skipping
                # unconditionally threw away one whole valid record whenever the cut fell on a
                # boundary.
                fh.seek(start - 1)
                if fh.read(1) != b"\n":
                    fh.readline()
            else:
                fh.seek(0)
            data = fh.read().decode("utf-8", "replace")
    except OSError:
        return out
    for ln in data.splitlines():
        try:
            rec = json.loads(ln)
        except ValueError:
            continue
        # One odd record (a JSON list, a string `message`) must cost only itself: an
        # AttributeError here used to abandon the whole scan, `last_assistant_message` included.
        if not isinstance(rec, dict):
            continue
        kind = rec.get("type")
        if kind not in ("user", "assistant"):
            continue
        msg = rec.get("message")
        out.append((kind, _text(msg.get("content") if isinstance(msg, dict) else None)))
    return out


def find_signals(event):
    """Learning-signal hits in this subagent's transcript + its final message. [] when none."""
    hits = []
    seen = set()
    msgs = _messages(event.get("agent_transcript_path") or "")
    final = event.get("last_assistant_message")
    if isinstance(final, str) and final.strip():
        msgs.append(("assistant", final))
    for role, text in msgs:
        # A subagent's OWN discovery lives only in its ASSISTANT output. Its user-role messages are
        # the PARENT's dispatch prompt (and tool results) - the main agent's own text, already in its
        # context - whose instruction phrasing ("always use ...", "do not ...") spuriously matches the
        # signal patterns and gets re-nudged forever. Scan assistant messages only.
        if role != "assistant":
            continue
        if not text.strip():
            continue
        matched = sig.broad_matches("assistant", text)   # broad: a subagent narrates loosely
        strict = _strict_hit(text)
        if strict:
            matched = sorted(set(matched) | {"strict"})
        if not matched:
            continue
        normalised = " ".join(text.split())
        # Containment dedup, not exact-match: `last_assistant_message` is normally the same finding
        # as the transcript's last assistant message (often a substring of it), so an exact-match
        # check buffers one discovery twice. Compared on the FULL normalised text, never on the
        # capped snippet: two different findings behind the same long opening share a snippet.
        if any(normalised in s or s in normalised for s in seen):
            continue
        seen.add(normalised)
        hits.append(_hit(event, text, matched))
    return hits


def _strict_hit(text):
    """The strict assistant patterns over `text` with its QUOTED spans blanked, as the Stop gate
    reads a reply: a subagent report citing another turn's "I was wrong" is data, not its own
    admission. Every strict check in this hook goes through here, so none can read the raw text."""
    return sig.strict_asst_hit(sig.unquoted(text))


def _hit(event, text, matched):
    """The buffer record for one assistant message and the signals it was buffered for."""
    normalised = " ".join(text.split())
    # Window the snippet on the learning itself. A head cap kept the first 200 characters, so a
    # learning stated after a long preamble was buffered with the learning cut away. A message
    # only Jev fired on has no pattern offset, and keeps the head. A quoted admission ahead of the
    # real one does not take the window (asst_said_offset).
    snippet = sig.inert_snippet(normalised, _SNIPPET, around=sig.asst_said_offset(text))
    return {"agent_id": event.get("agent_id") or "",
            "agent_type": event.get("agent_type") or "",
            "role": "assistant", "matched": matched, "snippet": snippet,
            # control signal, kept OUT of the snippet
            "escaped": sig.snippet_was_escaped(text)}


def _assistant_texts(event):
    """Every distinct non-empty assistant message of the subagent, in order, the final one last.

    Distinct by the same containment rule `find_signals` dedups by, so the final message that
    repeats the transcript's last one is asked about once.
    """
    msgs = _messages(event.get("agent_transcript_path") or "")
    final = event.get("last_assistant_message")
    if isinstance(final, str) and final.strip():
        msgs.append(("assistant", final))
    texts, seen = [], []
    for role, text in msgs:
        if role != "assistant" or not text.strip():
            continue
        normalised = " ".join(text.split())
        if any(normalised in s or s in normalised for s in seen):
            continue
        seen.append(normalised)
        texts.append(text)
    return texts


def _verdict(text):
    """What the capture's patterns say about one message, as `find_signals` judges it."""
    broad = sig.broad_matches("assistant", text)
    if _strict_hit(text):
        kind = "strict"
    elif broad:
        kind = "broad_only"
    else:
        kind = "none"
    return {"kind": kind, "buffered": kind != "none", "broad": broad}


def shadow_request(event):
    """(regex, requests) for the classifier shadow: one request per message, newest kept.

    `regex["messages"][i]` is the patterns' verdict on the text of `requests[i]`, `fires` is
    whether this subagent buffered anything at all, `dropped` how many earlier messages the cap
    left out.
    """
    return _requests_for(_assistant_texts(event))


def _requests_for(texts):
    """`shadow_request` over texts already read, so decide mode reads the transcript once."""
    verdicts = [_verdict(t) for t in texts]
    kept = texts[-SHADOW_MAX_MESSAGES:]
    regex = {"messages": verdicts[len(texts) - len(kept):],
             "fires": any(v["buffered"] for v in verdicts),
             "dropped": len(texts) - len(kept)}
    questions = classifier.subagent_signal_questions()
    return regex, [{"fields": {"assistant_reply": t}, "questions": questions} for t in kept]


def _shadow(event, session):
    """Hand the subagent's messages to the detached shadow child. Never raises, never decides."""
    with classifier.shadow_guard(SITE, session):
        if not classifier.shadow_enabled(sig.load_config(), SITE):
            return
        regex, requests = shadow_request(event)
        if requests:
            classifier.spawn_shadow(SITE, session, regex, requests,
                                    transcript=event.get("agent_transcript_path") or "")


def _jev_families(result):
    """The questions one answered message fires on, sorted: each at least the site threshold."""
    threshold = classifier.SITE_THRESHOLDS[SITE]
    answers = (result or {}).get("answers") or {}
    return sorted(k for k, a in answers.items()
                  if isinstance(a, dict) and isinstance(a.get("value"), (int, float))
                  and a["value"] >= threshold)


def _ask(session, regex, requests, cfg, transcript):
    """(row, results) from asking every request at once; results None where Jev did not answer."""
    try:
        row = classifier.ask_in_hook(SITE, session, regex, requests, cfg, transcript=transcript,
                                     workers=max(1, len(requests)))
    except Exception as exc:  # noqa: BLE001 - a failure to ask is a failure to answer
        row = classifier.error_row(SITE, session, exc)
        row["reason"] = "error: %s" % type(exc).__name__
    results = list(row.get("results") or [])
    return row, (results + [None] * len(requests))[:len(requests)]


def _decide(event, session, cfg):
    """Decide mode: buffer what Jev fires on, the strict patterns where Jev gave no answer."""
    texts = _assistant_texts(event)
    regex, requests = _requests_for(texts)
    if not texts:
        return
    transcript = event.get("agent_transcript_path") or ""
    row, results = _ask(session, regex, requests, cfg, transcript) if requests else ({}, [])
    first_asked = len(texts) - len(requests)
    decided = []
    for i, text in enumerate(texts):
        result = results[i - first_asked] if i >= first_asked else None
        if result is None:
            matched = ["strict"] if _strict_hit(text) else []
            how = "fallback-strict" if matched else "fallback-none"
        else:
            matched = ["jev:" + f for f in _jev_families(result)]
            how = "jev" if matched else "none"
        if i >= first_asked:
            decided.append(how)
        if matched:
            sig.buffer_subagent_learning(session, _hit(event, text, matched))
    if not requests:
        return
    if all(r is None for r in results):
        path = "fallback-%s" % (row.get("reason") or "no answer")
    else:
        path = "jev" if "jev" in decided else "none"
    row.update(mode="decide", decide_path=path, decided=decided)
    classifier.append_row(row)


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:                                     # noqa: BLE001 - never wedge a subagent
        return 0
    try:
        session = event.get("session_id") or ""
        if not session:
            return 0
        cfg = sig.load_config()
        if classifier.site_mode(cfg, SITE) == "decide":
            _decide(event, session, cfg)
            return 0
        for hit in find_signals(event):
            sig.buffer_subagent_learning(session, hit)
        _shadow(event, session)
    except Exception:                                     # noqa: BLE001 - fail open, always
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
