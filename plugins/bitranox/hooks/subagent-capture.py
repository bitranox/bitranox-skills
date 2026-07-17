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

Pure standard library. ALWAYS exits 0 and never emits a decision: a subagent finishing must never be
blocked or wedged by this.
"""
import json
import sys

import self_improve_signals as sig

_MAX_BYTES = 2_000_000        # tail cap: a subagent transcript is small, but never read unbounded
_SNIPPET = 200


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
            fh.seek(max(0, size - _MAX_BYTES))
            if size > _MAX_BYTES:
                fh.readline()                      # drop the partial line after the seek
            data = fh.read().decode("utf-8", "replace")
    except OSError:
        return out
    for ln in data.splitlines():
        try:
            rec = json.loads(ln)
        except ValueError:
            continue
        kind = rec.get("type")
        if kind not in ("user", "assistant"):
            continue
        out.append((kind, _text((rec.get("message") or {}).get("content"))))
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
        if not text.strip():
            continue
        matched = sig.broad_matches(role, text)          # broad: a subagent narrates loosely
        strict = (sig.strict_user_hit(text) if role == "user" else sig.strict_asst_hit(text))
        if strict:
            matched = sorted(set(matched) | {"strict"})
        if not matched:
            continue
        snippet = " ".join(text.split())[:_SNIPPET]
        # Containment dedup, not exact-match: `last_assistant_message` is normally the same finding
        # as the transcript's last assistant message (often a substring of it), so an exact-match
        # check buffers one discovery twice.
        if any(snippet in s or s in snippet for s in seen):
            continue
        seen.add(snippet)
        hits.append({"agent_id": event.get("agent_id") or "",
                     "agent_type": event.get("agent_type") or "",
                     "role": role, "matched": matched, "snippet": snippet})
    return hits


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:                                     # noqa: BLE001 - never wedge a subagent
        return 0
    try:
        session = event.get("session_id") or ""
        if not session:
            return 0
        for hit in find_signals(event):
            sig.buffer_subagent_learning(session, hit)
    except Exception:                                     # noqa: BLE001 - fail open, always
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
