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

from self_improve_signals import (audit_file, broad_matches, is_test_fixture_noise, skills_invoked,
                                  strict_asst_hit, strict_user_hit, tool_matches)

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


# Fields of a tool_use whose VALUE can carry the discovery (the command that was run, the path
# that was edited). The rest of the input is payload, not signal.
_TOOL_INPUT_FIELDS = ("command", "description", "file_path", "skill")


def _tool_text(content):
    """Text from tool_use inputs and tool_result outputs - the blocks _text() cannot see.

    A tooling learning often exists ONLY here: the model runs a flag that does not exist and the
    tool_result says so, with no prose anywhere. Scanning just `text` blocks structurally misses
    that whole class.
    """
    if not isinstance(content, list):
        return ""
    out = []
    for b in content:
        if not isinstance(b, dict):
            continue
        kind = b.get("type")
        if kind == "tool_use":
            inp = b.get("input")
            if isinstance(inp, dict):
                out.extend(str(inp[f]) for f in _TOOL_INPUT_FIELDS if isinstance(inp.get(f), str))
        elif kind == "tool_result":
            c = b.get("content")
            if isinstance(c, str):
                out.append(c)
            elif isinstance(c, list):
                out.extend(x["text"] for x in c
                           if isinstance(x, dict) and isinstance(x.get("text"), str))
    return " ".join(out)


def _iter_messages(transcript_path):
    """Yield (role, text) per message: the prose roles, plus a synthetic "tool" role.

    "tool" carries tool_use/tool_result text and is matched against the TOOL signal set, not the
    prose sets - a command line is not a sentence and the prose patterns do not apply to it.
    """
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
            content = obj.get("message", {}).get("content")
            yield kind, _text(content)
            tool = _tool_text(content)
            if tool:
                yield "tool", tool


def find_candidates(transcript_path):
    """Return candidate-miss dicts: a broad/tool match the strict gate did NOT catch."""
    candidates = []
    for role, text in _iter_messages(transcript_path):
        if not text.strip():
            continue
        if role == "tool":
            # No strict counterpart: the gate never looks at tool blocks at all, so every tool
            # signal is by definition a miss - EXCEPT pytest/test-fixture output, where those
            # phrases appear as literal test DATA (reading test_*.py, RED pytest tails) and would
            # flood the audit with phantom misses when the session's own work is this very code.
            matched = [] if is_test_fixture_noise(text) else tool_matches(text)
        else:
            strict = strict_user_hit(text) if role == "user" else strict_asst_hit(text)
            if strict:
                continue
            matched = broad_matches(role, text)
        if matched:
            snippet = " ".join(text.split())[:_SNIPPET]
            candidates.append({"role": role, "matched": matched, "snippet": snippet})
    return candidates


def _skill_tally(transcript_path):
    """{skill: count} for the transcript tail; {} on any read problem (never fatal)."""
    try:
        size = os.path.getsize(transcript_path)
        with open(transcript_path, "rb") as fh:
            if size > _MAX_BYTES:
                fh.seek(size - _MAX_BYTES)
                fh.readline()
            data = fh.read()
    except OSError:
        return {}
    return skills_invoked(data.decode("utf-8", "replace"))


def render_report(candidates, skills=None):
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
    if skills:
        lines += [
            "",
            "Skills invoked last session: "
            + ", ".join("%s (x%d)" % (k, n) for k, n in sorted(skills.items())),
            "If one of the candidates above is a bug that shipped DESPITE one of these skills, that "
            "is the skill's coverage gap - flag it for review and fix the skill (pattern/test), per "
            "flag-a-skill-when-a-real-bug-slips-past-it.",
        ]
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
    skills = _skill_tally(transcript)
    if not candidates:
        try:  # nothing to review: clear any stale report so it is not resurfaced
            out.unlink()
        except OSError:
            pass
        return 0
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render_report(candidates, skills), encoding="utf-8")
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - a broken hook must never disrupt session shutdown
        sys.exit(0)
