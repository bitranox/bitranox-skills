#!/usr/bin/env python3
"""SessionEnd hook: audit the whole session for learning signals the gate MISSED.

SessionEnd cannot nudge the model (the session is ending), so this hook does the
deterministic half of a two-stage loop:

  1. (here) On session end, scan the FULL transcript. Apply the STRICT gate patterns and a
     BROADER recall set (see self_improve_signals). A turn the broad set flags but the
     strict set did NOT is a CANDIDATE MISS - a likely gap in the gate. Write the candidates
     to a per-project audit file.
  2. (session-start.py) On the next SessionStart, surface that audit file as context so the
     MODEL reviews the candidates: confirm the real misses, capture learnings (self-improve),
     and extend the gate patterns in self_improve_signals.py (the self-improve meta-loop).

This never blocks anything and writes only a review note. Pure standard library; every
failure path exits 0 so a broken hook never disrupts session shutdown.
"""

import json
import os
import sys
from pathlib import Path

from self_improve_signals import audit_file, broad_matches, strict_asst_hit, strict_user_hit

# Bound how much transcript we read (sessions can be many MB); the tail covers a long
# session while keeping memory bounded.
_MAX_BYTES = 10 * 1024 * 1024
_MAX_CANDIDATES = 12       # cap surfaced candidates so the next-session note stays scannable
_SNIPPET = 160


def _text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(b["text"] for b in content if isinstance(b, dict) and isinstance(b.get("text"), str))
    return ""


def _iter_messages(transcript_path):
    """Yield (role, text) for each user/assistant message in the transcript tail."""
    try:
        size = os.path.getsize(transcript_path)
        with open(transcript_path, "rb") as fh:
            if size > _MAX_BYTES:
                fh.seek(size - _MAX_BYTES)
                fh.readline()  # drop the partial line after the seek
            data = fh.read()
    except OSError:
        return
    for raw in data.splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            obj = json.loads(line.decode("utf-8", "replace"))
        except ValueError:
            continue
        kind = obj.get("type")
        if kind in ("user", "assistant"):
            yield kind, _text(obj.get("message", {}).get("content"))


def find_candidates(transcript_path):
    """Return candidate-miss dicts: broad-recall match with no strict match."""
    candidates = []
    for role, text in _iter_messages(transcript_path):
        if not text.strip():
            continue
        strict = strict_user_hit(text) if role == "user" else strict_asst_hit(text)
        if strict:
            continue
        matched = broad_matches(role, text)
        if matched:
            snippet = " ".join(text.split())[:_SNIPPET]
            candidates.append({"role": role, "matched": matched, "snippet": snippet})
    return candidates


def render_report(candidates):
    recent = candidates[-_MAX_CANDIDATES:]
    freq = {}
    for c in candidates:
        for kw in c["matched"]:
            freq[kw] = freq.get(kw, 0) + 1
    top = sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))[:10]
    lines = [
        "<SELF-IMPROVE-AUDIT>",
        "The previous session contained %d message(s) that look like learning signals the "
        "self-improve gate did NOT catch (a broad-recall match with no strict match). Review "
        "them now: confirm the genuine misses, capture any learning with the self-improve "
        "skill, and for a real gap EXTEND the gate's family patterns in "
        "plugins/bitranox/hooks/self_improve_signals.py (do this in the bitranox-skills repo, "
        "or propagate it via self-improve's upstream loop). Ignore false positives."
        % len(candidates),
        "",
        "Recurring near-miss keywords: " + ", ".join("%s (x%d)" % (k, n) for k, n in top),
        "",
        "Candidates (most recent first):",
    ]
    for c in reversed(recent):
        lines.append('- [%s] matched %s :: "%s"' % (c["role"], "/".join(c["matched"]), c["snippet"]))
    lines.append("</SELF-IMPROVE-AUDIT>")
    return "\n".join(lines) + "\n"


def main():
    try:
        event = json.load(sys.stdin)
    except (ValueError, OSError):
        return 0
    transcript = event.get("transcript_path") or ""
    if not transcript or not Path(transcript).is_file():
        return 0
    proj = event.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    out = audit_file(proj)

    candidates = find_candidates(transcript)
    if not candidates:
        try:  # nothing to review: clear any stale report so it is not resurfaced
            out.unlink()
        except OSError:
            pass
        return 0
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render_report(candidates), encoding="utf-8")
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - a broken hook must never disrupt session shutdown
        sys.exit(0)
