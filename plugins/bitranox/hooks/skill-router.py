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

import classifier  # noqa: E402
import self_improve_signals as sig  # noqa: E402
import transcript_turns  # noqa: E402

MIN_HITS = 2
MAX_SKILLS = 2
# The router's shadow input beyond the prompt: project scope, recent tool activity, skills in use
# and the "new task or continuation?" gate question. Recorded in every log line.
ROUTER_VIEW = "ctx-v1"
PROJECT_CAP = 200


def _state_file(cwd, sid):
    """Per-project, per-session router state. Both keys are confined by their shared helper:
    `proj_key` hashes the project, `session_key` flattens the id to one filename component."""
    return sig._audit_dir() / ("%s.skillrouter-%s.txt" % (sig.proj_key(cwd), sig.session_key(sid)))


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


def _project_line(cwd):
    """`<dir>: <WHAT line>` from the nearest CLAUDE.local.md scope descriptor at or above `cwd`,
    else just the cwd's own name. Tells the router which domain the session is in."""
    here = Path(cwd)
    for d in (here, *here.parents):
        try:
            text = (d / "CLAUDE.local.md").read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for line in text.splitlines():
            if line.startswith("WHAT:"):
                return transcript_turns.excerpt(
                    "%s: %s" % (d.name, line[len("WHAT:"):].strip()), PROJECT_CAP)
    return here.name


def _already_nudged(cwd, sid):
    try:
        return {s for s in _state_file(cwd, sid).read_text(encoding="utf-8").split("\n") if s}
    except OSError:
        return set()


def _router_fields(prompt, cwd, sid, transcript):
    """The router's state: the prompt plus what it replies to and where the session is. Empty
    context is left out, so no question is asked about a field that says nothing."""
    fields = {"user_prompt": prompt, "project": _project_line(cwd)}
    activity = transcript_turns.recent_activity(transcript)
    if activity:
        fields["recent_activity"] = activity
    in_use = sorted(_already_nudged(cwd, sid) | set(transcript_turns.skills_used(transcript)))
    if in_use:
        fields["skills_already_used"] = ", ".join(in_use)
    return classifier.with_previous(fields, transcript_turns.last_reply(transcript))


def _shadow_skill_router(prompt, sid, triggers, transcript="", cwd=""):
    """Hand this prompt to the classifier's detached shadow child: the new-task gate plus one
    noul per skill beside the keyword ranking, with the context the prompt needs to be read.
    Never changes the nudge and never raises."""
    try:
        if not classifier.shadow_enabled(sig.load_config(), "skill_router"):
            return
        ranked = match(prompt, triggers, max_skills=len(triggers) or 1)
        regex = {"selected": [s for s, _n in ranked[:MAX_SKILLS]],
                 "scores": {s: n for s, n in ranked}, "context_view": classifier.CONTEXT_VIEW,
                 "router_view": ROUTER_VIEW}
        questions = classifier.skill_router_questions(classifier.load_skill_descriptions())
        classifier.spawn_shadow("skill_router", sid, regex,
                                [{"fields": _router_fields(prompt, cwd or os.getcwd(), sid,
                                                           transcript),
                                  "questions": questions}])
    except Exception:  # noqa: BLE001 - shadow mode must never wedge a prompt
        pass


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
        triggers = load_triggers()
        hits = match(prompt, triggers)
        # Opt-in shadow comparison (off by default), before the per-session dedup so every
        # prompt is compared.
        _shadow_skill_router(prompt, sid, triggers, ev.get("transcript_path") or "", cwd)
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
