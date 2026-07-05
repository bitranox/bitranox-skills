#!/usr/bin/env python3
"""UserPromptSubmit hook: raise the RIGHT skill's salience at the moment its trigger fires.

The available-skills list is a MENU (discretionary - a matching skill still gets skipped under
momentum). This router is the deterministic complement: match the prompt against the derived
trigger map (`skill_triggers.json`, built from the skills' own trigger-first descriptions by
`build_skill_triggers.py`) and inject a one-line pointed nudge for the top matches - moving the
match from the weak menu channel into injected context exactly when it is relevant, instead of a
big always-on banner. It nudges; the deny-hard guards (skill-edit, store-edit, repo-gate) enforce.

Precision rules: a skill fires only on >= MIN_HITS distinct keyword matches (word-boundary), at
most MAX_SKILLS per prompt, and each skill nudges at most once per session (state file). Fail-open:
every error path exits 0. Pure standard library; launched via run-python.sh.
"""
import json
import os
import re
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

import self_improve_signals as sig  # noqa: E402

MIN_HITS = 2
MAX_SKILLS = 2


def _state_file(cwd, sid):
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", str(sid))[:64]
    return (Path.home() / ".claude" / "self-improve-audit"
            / ("%s.skillrouter-%s.txt" % (sig.proj_key(cwd), safe)))


def load_triggers():
    try:
        return json.loads((_HOOKS_DIR / "skill_triggers.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def match(prompt, triggers, min_hits=MIN_HITS, max_skills=MAX_SKILLS):
    """[(skill, hit_count)] for skills whose distinct keyword hits reach min_hits, best first."""
    low = (prompt or "").lower()
    scored = []
    for skill, kws in triggers.items():
        hits = sum(1 for k in kws
                   if re.search(r"(?<![a-z0-9])" + re.escape(k) + r"(?![a-z0-9])", low))
        if hits >= min_hits:
            scored.append((skill, hits))
    scored.sort(key=lambda x: (-x[1], x[0]))
    return scored[:max_skills]


def main():
    try:
        ev = json.load(sys.stdin)
    except Exception:  # noqa: BLE001
        return 0
    prompt = (ev.get("prompt") or ev.get("user_prompt") or "").strip()
    if not prompt:
        return 0
    cwd = ev.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    sid = ev.get("session_id") or "default"
    try:
        hits = match(prompt, load_triggers())
        if not hits:
            return 0
        state = _state_file(cwd, sid)
        try:
            already = set(state.read_text(encoding="utf-8").split("\n")) if state.exists() else set()
        except OSError:
            already = set()
        fresh = [(s, n) for s, n in hits if s not in already]
        if not fresh:
            return 0
        state.parent.mkdir(parents=True, exist_ok=True)
        with state.open("a", encoding="utf-8") as f:
            for s, _n in fresh:
                f.write(s + "\n")
        lines = ["<BITRANOX-SKILL-ROUTER>"]
        for s, _n in fresh:
            lines.append("This prompt matches the skill `bitranox:%s` - if it applies (even a 1%% "
                         "chance), invoke it via the Skill tool BEFORE responding." % s)
        lines.append("</BITRANOX-SKILL-ROUTER>")
        out = {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
                                      "additionalContext": "\n".join(lines)},
               "suppressOutput": True}
        sys.stdout.write(json.dumps(out))
    except Exception:  # noqa: BLE001 - the router must never wedge a prompt
        return 0
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001
        sys.exit(0)
