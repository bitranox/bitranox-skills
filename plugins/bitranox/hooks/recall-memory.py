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


def _state_file(cwd, sid):
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", str(sid))[:64]
    return Path.home() / ".claude" / "self-improve-audit" / ("%s.recall-%s.txt" % (sig.proj_key(cwd), safe))


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
        keywords = gs.extract_keywords(prompt)
        if not keywords:
            return 0
        hits = gs.scan(keywords, gs.discover_files(cwd))  # other projects + global; current excluded
    except Exception:  # noqa: BLE001 - scan must never wedge the session
        return 0
    # Precision: require a real match, not one common token. With >=2 keywords, demand >=2 distinct
    # hits; with a single keyword, that one must hit. Cuts broad-token noise (e.g. just "test").
    need = 2 if len(keywords) >= 2 else 1
    hits = {p: ks for p, ks in hits.items() if len(ks) >= need}
    if not hits:
        return 0

    # strongest first (most keywords matched), stable by path
    ranked = sorted(hits, key=lambda p: (-len(hits[p]), p))

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
        try:
            body = Path(p).read_text(encoding="utf-8", errors="replace").strip()[:MAX_BODY]
        except OSError:
            continue
        if body:
            blocks.append("### %s\n%s" % (Path(p).stem, body))
    if not blocks:
        return 0

    try:
        state.parent.mkdir(parents=True, exist_ok=True)
        with state.open("a", encoding="utf-8") as f:
            for p in fresh:
                f.write(p + "\n")
    except OSError:
        pass

    ctx = ("Relevant prior work found in your OTHER project memory / global rules - read it and draw on "
           "it before reinventing; verify any named file/flag still exists, and de-duplicate against this "
           "project's own memory:\n\n" + "\n\n".join(blocks))
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
