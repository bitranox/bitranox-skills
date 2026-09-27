#!/usr/bin/env python3
"""UserPromptSubmit hook: raise the RIGHT skill's salience at the moment its trigger fires.

The available-skills list is a MENU (discretionary - a matching skill still gets skipped under
momentum). This router is the deterministic complement: match the prompt against the derived
trigger map (`skill_triggers.json`, built from the skills' own trigger-first descriptions by
`build_skill_triggers.py`) and inject a one-line pointed nudge for the top matches - moving the
match from the weak menu channel into injected context exactly when it is relevant, instead of a
big always-on banner. It nudges; the deny-hard guards (skill-edit, store-edit, repo-gate) enforce.

Precision rules: a skill fires only on >= MIN_HITS distinct keyword matches (word-boundary, with
letters and digits of any script as word characters), at most MAX_SKILLS NEW skills per prompt
(skills already nudged in this session are dropped before the cap, so they never hold a slot), and
each skill nudges at most once per session (state file). Fail-open: every error path exits 0. Pure
standard library; launched via run-python.sh.

With `classifier_skill_router = decide` (and `classifier_backend = jev`) Jev decides a typed
prompt instead: the hook asks the shadow comparison's own gate-plus-choice question in-process,
under the classifier's DEFAULT_DEADLINE, and nudges the ONE skill `classifier.choice_pick` returns
- or nothing, when Jev answered and picked nothing. Only when Jev does not answer, or picks a skill
from a cached roster that cannot be confirmed installed, does the keyword match decide, exactly as
with the classifier off; a task notification goes that way too. Each decide prompt appends one
shadow-log row saying which path nudged, so `classifier_eval.py report` reads decide sessions like
shadow ones.
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
import prompt_text  # noqa: E402
import self_improve_signals as sig  # noqa: E402
import skill_roster  # noqa: E402
import transcript_turns  # noqa: E402

MIN_HITS = 2
MAX_SKILLS = 2
# The router's shadow input beyond the prompt: project scope, recent tool activity, skills in use
# and the "new task or continuation?" gate question. Recorded in every log line.
ROUTER_VIEW = "ctx-v1"
# The SHAPE of the skill question: the gate plus one choice over the roster. The replays preferred
# it on accuracy over one noul per skill, which the rows before this tag carry, so their picks are
# read by a different rule and must never pool with these.
QUESTION_VIEW = "choice-v1"
# Which KEYWORD matcher produced the row's regex arm. The `*_view` tags say what the classifier
# was shown; this says what it is being compared AGAINST, and that half changes too. 7.6.0 stopped
# scoring machine turns and non-prose while the input views stayed the same, which left 15
# notification rows judged by the old matcher pooling with typed prompts in one report group.
# prose-v2: the word boundary is Unicode-aware, so an umlaut no longer splits a German compound.
MATCHER_VIEW = "prose-v2"
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


# What a keyword may not touch on either side: a letter or digit of ANY script. An ASCII class
# treated an umlaut as a word break, so "file" matched inside a German compound. Same rule as
# gather_scan.scan.
_WORD_CHAR = r"[^\W_]"


def _hit_count(keywords, text):
    """Distinct keywords found in `text` at a word boundary.

    A compound keyword and its own component both count on one token ("lib_layered_config" is
    also "config", "package.json" also "json"), so one distinctive identifier clears MIN_HITS on
    its own. That is kept on purpose: a replay of 1,311 typed prompts found no false nudge from it,
    while counting such a token once dropped real ones ("do we have lib_layered_config implemented
    here ?" lost coding-python-layered-config)."""
    return sum(1 for k in set(keywords)
               if k and re.search("(?<!%s)%s(?!%s)" % (_WORD_CHAR, re.escape(k), _WORD_CHAR), text))


def match(prompt, triggers, min_hits=MIN_HITS, max_skills=MAX_SKILLS):
    """[(skill, hit_count)] for skills whose distinct keyword hits reach min_hits, best first
    (ties alphabetical), at most `max_skills` of them (None: all).

    Only the PROSE of a typed prompt is scored (`prompt_text.scorable_prose`): a machine-generated
    turn scores nothing, and a path, an id or a tag inside a real prompt is not a topic. Keeping
    this inside `match` is what makes the nudge and the shadow's keyword baseline agree.
    """
    low = prompt_text.scorable_prose(prompt).lower()
    scored = []
    for skill, kws in triggers.items():
        hits = _hit_count(kws, low)
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
    """Skills this session was already nudged about, by the name the Skill tool takes
    (`bitranox:<name>` for this plugin's). One identity for both paths: a keyword nudge and a Jev
    nudge of the same skill spend it once, and a same-named skill from elsewhere, which the
    listing keeps apart by that prefix, is a different skill. Read with errors="replace": one
    undecodable byte must not raise and silence the router for the rest of the session."""
    try:
        text = _state_file(cwd, sid).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return set()
    return {s for s in text.split("\n") if s}


def _turn_fields(prompt):
    """What the turn itself contributes: a typed prompt, or a notification's own fields - never
    the notification envelope dressed up as a prompt."""
    return prompt_text.notification_fields(prompt) or {"user_prompt": prompt}


def _router_fields(prompt, cwd, sid, transcript):
    """The router's state: the turn plus what it replies to and where the session is. Empty
    context is left out, so no question is asked about a field that says nothing."""
    fields = dict(_turn_fields(prompt), project=_project_line(cwd))
    activity = transcript_turns.recent_activity(transcript)
    if activity:
        fields["recent_activity"] = activity
    # Bare, the form `skills_used` reports, so one skill reads the same from either source.
    nudged = {s.rsplit(":", 1)[-1] for s in _already_nudged(cwd, sid)}
    in_use = sorted(nudged | set(transcript_turns.skills_used(transcript)))
    if in_use:
        fields["skills_already_used"] = ", ".join(in_use)
    return classifier.with_previous(fields, transcript_turns.last_reply(transcript))


def _router_request(prompt, sid, triggers, transcript, cwd):
    """(regex, request, roster): the keyword ranking a log row carries, the ONE request - the
    new-task gate plus one choice over the installed roster, with the context the prompt needs to
    be read - and that roster. Shadow and decide both build it here, so they ask the same thing."""
    ranked = match(prompt, triggers, max_skills=len(triggers) or 1)
    regex = {"selected": [s for s, _n in ranked[:MAX_SKILLS]],
             "scores": {s: n for s, n in ranked}, "context_view": classifier.CONTEXT_VIEW,
             "router_view": ROUTER_VIEW, "matcher_view": MATCHER_VIEW,
             "question_view": QUESTION_VIEW}
    notification = bool(prompt_text.notification_fields(prompt))
    if notification:
        # Its own field set, so the eval never pools these rows with typed-prompt rows.
        regex["notify_view"] = classifier.NOTIFY_VIEW
    # The questions are built from the SAME dict this request will carry, so neither can name
    # a field the other leaves out.
    cwd = cwd or os.getcwd()
    fields = _router_fields(prompt, cwd, sid, transcript)
    skills, regex["roster"] = skill_roster.installed_skills(transcript, cwd)
    regex["roster_size"] = len(skills)
    questions = classifier.skill_router_choice_questions(
        skills, fields,
        turn=classifier.TURN_NOTIFICATION if notification else classifier.TURN_PROMPT)
    return regex, {"fields": fields, "questions": questions}, skills


def _shadow_skill_router(prompt, sid, triggers, transcript="", cwd=""):
    """Hand this prompt to the classifier's detached shadow child. Never changes the nudge and
    never raises; a failure is logged as an error row."""
    with classifier.shadow_guard("skill_router", sid):
        if not classifier.shadow_enabled(sig.load_config(), "skill_router"):
            return
        regex, request, _skills = _router_request(prompt, sid, triggers, transcript, cwd)
        classifier.spawn_shadow("skill_router", sid, regex, [request], transcript=transcript)


def _ask_jev(prompt, sid, triggers, transcript, cwd, cfg):
    """(row, path, pick, roster) for decide mode. `path` is "jev" with the option key Jev picked,
    "none" when it answered and picked nothing, or "fallback-<reason>" when it did not answer -
    including "fallback-stale pick", a pick from a cached roster the session may no longer have,
    which would send the model after a skill that does not exist."""
    regex, request, skills = _router_request(prompt, sid, triggers, transcript, cwd)
    row = classifier.ask_in_hook("skill_router", sid, regex, [request], cfg, transcript=transcript)
    result = (row.get("results") or [None])[0]
    if result is None:
        return row, "fallback-%s" % (row.get("reason") or "no answer"), None, skills
    gate, winner, probabilities = classifier.choice_answer(result)
    # The production rule the blind panel scored, at the threshold the eval judges the site at.
    pick = classifier.choice_pick(gate, winner, probabilities,
                                  threshold=classifier.SITE_THRESHOLDS["skill_router"],
                                  bypass=classifier.CHOICE_BYPASS)
    if pick and not skill_roster.is_live(pick, skills, regex.get("roster")):
        return row, "fallback-stale pick", None, skills
    return row, ("jev" if pick else "none"), pick, skills


def _fresh_keyword_hits(hits, already):
    """The keyword picks to nudge: dedup BEFORE the MAX_SKILLS cap, so skills nudged earlier
    never hold the slots of a fresh skill that matches this prompt."""
    names = ["bitranox:" + s for s, _n in hits]
    return [n for n in names if n not in already][:MAX_SKILLS]


def _nudge(cwd, sid, picks):
    """Record each skill in `picks` (by the name the Skill tool takes) as nudged this session and
    print the router block naming them. Nothing is printed for an empty `picks`."""
    if not picks:
        return
    state = _state_file(cwd, sid)
    state.parent.mkdir(parents=True, exist_ok=True)
    with state.open("a", encoding="utf-8") as f:
        for name in picks:
            f.write(name + "\n")
    lines = ["<BITRANOX-SKILL-ROUTER>"]
    for name in picks:
        lines.append("This prompt matches the skill `%s` - if it applies (even a 1%% "
                     "chance), invoke it via the Skill tool BEFORE responding." % name)
    lines.append("</BITRANOX-SKILL-ROUTER>")
    out = {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
                                  "additionalContext": "\n".join(lines)},
           "suppressOutput": True}
    sys.stdout.write(json.dumps(out))


def _decide(prompt, sid, triggers, hits, transcript, cwd, cfg):
    """Decide mode: Jev's pick, nothing when it picked nothing, the keyword hits when it did not
    answer; then the comparison row, written after the nudge so it adds no latency before it."""
    failure = None
    try:
        row, path, pick, skills = _ask_jev(prompt, sid, triggers, transcript, cwd, cfg)
    except Exception as exc:  # noqa: BLE001 - a failure to ask is a failure to answer
        failure = exc
        row, path, pick, skills = None, "fallback-error: %s" % type(exc).__name__, None, {}
    already = _already_nudged(cwd, sid)
    if path == "jev":
        name = skill_roster.invocation_name(pick, skills)
        picks = [] if name in already else [name]
    elif path == "none":
        picks = []  # "no skill" is an answer; the keyword hits it overruled were judged noise
    else:
        picks = _fresh_keyword_hits(hits, already)
    _nudge(cwd, sid, picks)
    try:
        row = row if failure is None else classifier.error_row("skill_router", sid, failure)
        row.update(mode="decide", decide_path=path, nudged=picks)
        classifier.append_row(row)
    except Exception:  # noqa: BLE001 - a comparison row is never worth a failed hook
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
        # Every matching skill, uncapped: the per-session dedup runs BEFORE the MAX_SKILLS cap, so
        # skills nudged earlier never hold the slots of a fresh skill that matches this prompt.
        hits = match(prompt, triggers, max_skills=None)
        transcript = ev.get("transcript_path") or ""
        cfg = sig.load_config()
        # A task notification is not a prompt, and no blind judgement has covered one, so decide
        # mode acts on typed prompts only; a notification goes the way it does with the site off.
        if (classifier.site_mode(cfg, "skill_router") == "decide"
                and not prompt_text.notification_fields(prompt)):
            _decide(prompt, sid, triggers, hits, transcript, cwd, cfg)
            return 0
        # Opt-in shadow comparison (off by default), before the per-session dedup so every
        # prompt is compared.
        _shadow_skill_router(prompt, sid, triggers, transcript, cwd)
        if not hits:
            return 0
        _nudge(cwd, sid, _fresh_keyword_hits(hits, _already_nudged(cwd, sid)))
    except Exception:  # noqa: BLE001 - the router must never wedge a prompt
        return 0
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001
        sys.exit(0)
