#!/usr/bin/env python3
"""UserPromptSubmit hook: on each prompt, recall relevant memory from ANYWHERE into the session.

The "look in my notebook before reinventing" reflex. Reuses the existing fast grep
(meta-collect-knowledge/gather_scan.py): derive keywords from the prompt, grep across every OTHER
project's memory + the global rules layer (the current project is excluded, so what is drawn in is
de-duplicated against our own memory), and inject the top matches' bodies as advisory context - once
per session. Read-only: it surfaces prior work, it does not copy/promote (that is meta-collect-knowledge).

Pure standard library. Fail-open: every error path exits 0, so a broken or slow hook never wedges a turn.
"""

import json
import os
import re
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
_SKILL_DIR = _HOOKS_DIR.parent / "skills" / "meta-collect-knowledge"
for _d in (str(_HOOKS_DIR), str(_SKILL_DIR)):
    if _d not in sys.path:
        sys.path.insert(0, _d)

import gather_scan as gs  # noqa: E402  (the existing grep engine; also pulls in self_improve_signals)
import self_improve_signals as sig  # noqa: E402

MAX_HITS = 4
MAX_BODY = 1800
SPECIFIC_MAX = 6  # a keyword matching <= this many candidate notes is a specific (strong) signal
COMMON_FRACTION = 0.25  # a keyword in > this fraction of the whole store is a corpus-stopword (no signal)


def _state_file(cwd, sid):
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", str(sid))[:64]
    return Path.home() / ".claude" / "self-improve-audit" / ("%s.recall-%s.txt" % (sig.proj_key(cwd), safe))


def _label(path):
    """A readable source label. A native topic file / curated `facts/<slug>.md` -> its stem; a
    CLAUDE.md -> '<parent-dir>/CLAUDE.md'; a curated `index.md` -> '<project-dir>/memory' (every
    curated index is named index.md, so name it by its owning project - same fix as CLAUDE.md)."""
    p = Path(path)
    if p.name == "CLAUDE.md":
        return "%s/CLAUDE.md" % p.parent.name
    if p.name == sig.CURATED_INDEX and p.parent.name == sig.CURATED_DIRNAME:
        return "%s/memory" % p.parent.parent.name
    return p.stem


def _snippet(path, keywords, maxlen):
    """Body to inject. Small files: the whole thing (trimmed). Large files (CLAUDE.md can be tens of
    KB): a window CENTERED on the first matched keyword, so the relevant rule is shown, not just the
    file head (which often would not contain the match at all)."""
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    if Path(path).name == sig.CURATED_INDEX:      # strip the scope descriptor (meta, not a fact) from a curated index
        text = sig._strip_scope(text)
    if len(text) <= maxlen:
        return text.strip()
    low = text.lower()
    pos = min((i for i in (low.find((k or "").lower()) for k in keywords) if i != -1), default=-1)
    if pos < 0:
        return text.strip()[:maxlen]
    start = max(0, pos - maxlen // 3)
    end = start + maxlen
    return ("..." if start > 0 else "") + text[start:end].strip() + ("..." if end < len(text) else "")


def main():
    try:
        ev = json.load(sys.stdin)
    except Exception:  # noqa: BLE001 - no/invalid stdin: do nothing
        return 0
    prompt = (ev.get("prompt") or ev.get("user_prompt") or "").strip()
    if not prompt:
        return 0
    cwd = ev.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    sid = ev.get("session_id") or "default"

    try:
        keywords = gs.extract_keywords(prompt, proj=cwd)  # filler-free: global baseline + THIS project's
        if not keywords:
            return 0
        # Queue any not-yet-classified keyword for the dream-time filler classifier (deterministic,
        # no model here). Known filler is already dropped by extract_keywords; known-topical is skipped.
        # Keyed to THIS project so its learned lists never leak into another project's recall.
        sig.note_unknown_keywords(keywords, cwd)
        # other projects' memory + global rules, PLUS other projects' CLAUDE.md across the workspace
        # tree (lots of cross-project rules still live in CLAUDE.md). The current project's own memory
        # and its ancestor-chain CLAUDE.md are excluded - they are already loaded in this session.
        files = gs.discover_files(cwd) + gs.discover_claude_md(cwd) + gs.discover_curated(cwd, cwd)
        hits = gs.scan(keywords, files)
    except Exception:  # noqa: BLE001 - scan must never wedge the session
        return 0
    if not hits:
        return 0
    # Precision by keyword RARITY (specificity), not a flat count: a keyword matching FEW notes is a
    # strong/specific signal; one matching MANY is weak. df[k] = notes containing k (only matched notes
    # contain a keyword, so this IS the corpus document-frequency).
    df = {}
    for ks in hits.values():
        for k in set(ks):
            df[k] = df.get(k, 0) + 1
    ndocs = len(hits)
    # CORPUS-stopword: a keyword present in a large FRACTION of the whole store carries no signal FOR
    # THIS user (e.g. "memory" in a memory-centric store - 83%). A static filler list cannot catch a
    # word that is common only in your corpus; this can. Such keywords neither count toward specificity
    # nor score - so a note that matched ONLY corpus-common words is dropped.
    # corpus-common = a LARGE fraction AND absolutely not-rare (> SPECIFIC_MAX); the absolute floor
    # stops a tiny store - where any word is a big fraction - from treating a rare term as common.
    total = max(len(files), 1)
    common = {k for k, c in df.items() if c > SPECIFIC_MAX and c > COMMON_FRACTION * total}

    def _useful(p):
        return set(hits[p]) - common
    # inverse-frequency score over the USEFUL (non-corpus-common) matches only.
    def _score(p):
        return sum(ndocs / df[k] for k in _useful(p))
    # keep a note if its USEFUL matches are >= 2 distinct, or one that is SPECIFIC in absolute terms
    # (df <= SPECIFIC_MAX - robust for tiny candidate sets). Corpus-common matches do not qualify it.
    def _specific(p):
        u = _useful(p)
        return len(u) >= 2 or any(df[k] <= SPECIFIC_MAX for k in u)
    ranked = sorted((p for p in hits if _specific(p)), key=lambda p: (-_score(p), p))
    if not ranked:
        return 0

    state = _state_file(cwd, sid)
    try:
        already = set(state.read_text(encoding="utf-8").split("\n")) if state.exists() else set()
    except OSError:
        already = set()
    fresh = [p for p in ranked if p not in already][:MAX_HITS]
    if not fresh:
        return 0

    blocks = []
    for p in fresh:
        body = _snippet(p, hits.get(p, keywords), MAX_BODY)
        if body:
            blocks.append("### %s\n%s" % (_label(p), body))
    if not blocks:
        return 0

    try:
        state.parent.mkdir(parents=True, exist_ok=True)
        with state.open("a", encoding="utf-8") as f:
            for p in fresh:
                f.write(p + "\n")
    except OSError:
        pass

    ctx = ("Relevant prior work found in your OTHER projects' memory / CLAUDE.md / global rules - read it "
           "and draw on it before reinventing; verify any named file/flag still exists, and de-duplicate "
           "against this project's own memory:\n\n" + "\n\n".join(blocks))
    out = {
        "hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": ctx},
        "systemMessage": "Recalled %d related memory note(s) from elsewhere." % len(blocks),
        "suppressOutput": True,
    }
    sys.stdout.write(json.dumps(out))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - a broken hook must never block a session
        sys.exit(0)
