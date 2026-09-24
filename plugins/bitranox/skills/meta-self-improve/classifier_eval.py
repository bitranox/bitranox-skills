#!/usr/bin/env python3
"""Compare the regex verdicts with Jev's per classifier site, from the shadow log.

The first-wave classifier sites (hooks/classifier.py) run in shadow mode: the hook keeps its regex
verdict and a detached child logs Jev's answers beside it, one JSON line per prompt or turn, in
~/.claude/self-improve-audit/classifier-shadow-<UTC date>.jsonl (the hook keeps the last 30 days,
at most 200 MB). `report` reads every one of those logs, oldest first, and answers, per site:

  stop_signal    per turn: both fire / regex only / Jev only / neither, split by language
  skill_router   per prompt: the keyword selection against Jev's top N skills above the threshold
  recall_rerank  per prompt: the notes injected by keyword rank against the shortlisted notes Jev
                 scores relevant, plus the spread of Jev's scores (a narrow spread means Jev is not
                 telling the notes apart)

plus latency and token percentiles, the error reasons, and how many rows each plugin release
wrote. Every disagreement can be written to a JSONL file, carrying the text it was judged on, for
adjudication against the source transcript; `locate_prompt(row)` finds the prompt record a row
was asked about there, from the transcript path and offset the hook recorded.

A disagreement is not a Jev error: either side can be the wrong one, and deciding which is the
point of adjudication. Standard library only; it reads a local file and calls no API.

Usage:
  classifier_eval.py report [--log PATH] [--threshold 0.5] [--top 2]
                            [--exclude-session PREFIX ...] [--disagreements OUT.jsonl] [--json]

Exit codes: 0 report produced, 1 the log holds no usable rows, 2 usage or IO error.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import re
import sys
from collections import Counter
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_HOOKS = _HERE.parent.parent / "hooks"
_JIGS = _HERE.parent / "compuse-toolbox" / "scripts"
for _d in (str(_HOOKS), str(_JIGS)):
    if _d not in sys.path:
        sys.path.insert(0, _d)

import classifier as cl  # noqa: E402 - the sys.path above is what makes this importable
import skill_roster  # noqa: E402 - same sys.path
import transcript_turns  # noqa: E402 - same sys.path

def default_log():
    """The audit directory the hooks log into, resolved per run so a changed HOME is honoured."""
    return Path.home() / ".claude" / "self-improve-audit"

DEFAULT_THRESHOLD = 0.5

# The threshold each site is judged at when none is given. One number for all three was always a
# placeholder: they ask different questions and their answers are distributed differently.
# Measured over 1,177 recall pair judgements, 0.5 keeps 20% of them (about 5.9 notes a prompt) and
# 0.8 keeps 4% (about 1.1), which is the order of what a prompt can actually use.
# `skill_router` was 0.7 and that was measured WRONG on 2026-09-24, against 50 prompts labelled
# blind by five judges (every pick classified, none sampled). The gate discriminates weakly - AUC
# about 0.71 on all four arms then measured - so 0.7 sat in the steep part of a shallow curve and
# discarded correct answers wholesale. Right/defensible/wrong/missed, same run, same prompts:
#
#   choice_full          0.70   2 /  7 / 1 / 8        choice_router_text  0.70   4 /  6 / 1 / 8
#   choice_full          0.50   4 / 13 / 1 / 5        choice_router_text  0.50   6 /  9 / 1 / 5
#   choice_full          0.30   4 / 15 / 1 / 5        choice_router_text  0.30   9 / 12 / 1 / 2
#
# Every arm improves as the gate drops, so this is a property of the gate and not of one arm.
# 0.5 rather than the better-scoring 0.3 because 0.5 is where the planted controls were actually
# run and passed on all six arms - positives 0.68-0.72, negatives 0.20-0.23 - so it clears both
# ways by about 0.2, where 0.3 leaves 0.07 over the negatives and has never been run.
# `nouls` is not a candidate at any of these: one number gates the turn AND sets its per-skill
# bar, so at 0.3 it makes 42 outright wrong picks.
SITE_THRESHOLDS = {"stop_signal": 0.7, "skill_router": 0.5, "recall_rerank": 0.8}

# Families whose score is LOGGED but never counted as a firing. `endorsement` was the only reason
# to fire on 12 turns across two shadow windows, every one a plain approval ("yes", "go", "lets
# try 1-4"): approving a proposal the assistant made is not a learning signal. The question stays
# in the set, so the score keeps being recorded and the judgement can be revisited on data.
NON_FIRING_FAMILIES = frozenset({"endorsement"})
DEFAULT_TOP = 2
# Rows written by a hand-run probe of a hook, not by a real session.
DEFAULT_EXCLUDE = ("probe-",)
SITES = ("stop_signal", "skill_router", "recall_rerank")


# ---- loading -------------------------------------------------------------------------------

def load_rows(path, exclude_sessions=()):
    """(rows, malformed_line_count) from one log file, or from every shadow log in a directory,
    oldest rows first. Rows whose session id starts with an excluded prefix are dropped. Raises
    OSError when a log cannot be read or the path does not exist."""
    path = Path(path)
    files = cl.shadow_log_files(path) if path.is_dir() else [path]
    rows, bad = [], 0
    for f in files:
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                row = _parse_row(line)
                if row is None:
                    bad += bool(line.strip())
                    continue
                sid = str(row.get("session_id") or "")
                if not any(sid.startswith(p) for p in exclude_sessions):
                    rows.append(row)
    return rows, bad


def _parse_row(line):
    """The JSON object on `line`, or None for a blank, malformed or non-object line."""
    if not line.strip():
        return None
    try:
        row = json.loads(line)
    except ValueError:
        return None
    return row if isinstance(row, dict) else None


# ---- joining a live row to its prompt ------------------------------------------------------

# The part of a logged prompt matched against the transcript: its end, because a capped field
# keeps head and tail, and the tail survives whole.
MATCH_TAIL = 80
# The sites a Stop hook drives. At turn end the prompt is always already written, so the row's
# prompt is the last match BEFORE the offset; a prompt-time hook may run before or after its
# prompt reaches the file, so its row takes the match nearest the offset.
TURN_END_SITES = frozenset({"stop_signal"})


def _logged_prompt(row):
    state = _first_state(row)
    text = state.get("user_prompt") or state.get("user_message") or ""
    return text.split(cl.CAP_MARK)[-1].strip()[-MATCH_TAIL:]


def _typed_spans(path):
    """(start, end, uuid, text) of every typed prompt in a transcript, by byte position."""
    spans, pos = [], 0
    with open(path, "rb") as fh:
        for raw in fh:
            start, pos = pos, pos + len(raw)
            try:
                obj = json.loads(raw.decode("utf-8", "replace"))
            except ValueError:
                continue
            text = transcript_turns.human_text(obj) if isinstance(obj, dict) else ""
            if text:
                spans.append((start, pos, obj.get("uuid"), text))
    return spans


def locate_prompt(row):
    """The uuid of the typed prompt a live shadow row was asked about, else None.

    Text alone cannot place a prompt typed several times in one session, so the match is taken
    from where the hook stood in the transcript (`transcript_offset`). A row with no location, a
    transcript that is gone, a notification row, or a prompt redaction changed answers None.
    """
    path, offset, want = row.get("transcript_path"), row.get("transcript_offset"), _logged_prompt(row)
    if not path or offset is None or not want:
        return None
    try:
        spans = [s for s in _typed_spans(path) if want in s[3]]
    except OSError:
        return None
    if row.get("site") in TURN_END_SITES:
        before = [s for s in spans if s[1] <= offset]
        return before[-1][2] if before else None
    if not spans:
        return None
    return min(spans, key=lambda s: offset - s[1] if s[1] <= offset else s[0] - offset)[2]


def _scores(result):
    """{question id: numeric value} from one logged result, or None when it was unanswered."""
    if not isinstance(result, dict):
        return None
    out = {}
    for qid, ans in (result.get("answers") or {}).items():
        value = ans.get("value") if isinstance(ans, dict) else None
        if isinstance(value, (int, float)):
            out[qid] = float(value)
    return out


def _answered(row):
    return [_scores(r) for r in row.get("results") or []]


def _first_state(row):
    states = row.get("states") or []
    return states[0] if states else {}


def _base(row):
    return {"site": row.get("site"), "ts": row.get("ts"), "session_id": row.get("session_id"),
            "lang": row.get("lang")}


# ---- stop_signal ---------------------------------------------------------------------------

def _kind(regex, jev):
    if regex and jev:
        return "both"
    if regex:
        return "regex_only"
    return "jev_only" if jev else "neither"


def summarize_stop_signal(rows, threshold):
    """Per-turn firing sets. Jev fires when any family scores at or above the threshold."""
    by_lang, disagreements, unanswered = {}, [], 0
    for row in rows:
        results = _answered(row)
        scores = results[0] if results else None
        if scores is None:
            unanswered += 1
            continue
        families = sorted(k for k, v in scores.items()
                          if v >= threshold and k not in NON_FIRING_FAMILIES)
        kind = _kind(bool((row.get("regex") or {}).get("fires")), bool(families))
        counts = by_lang.setdefault(row.get("lang") or "unknown",
                                    {"both": 0, "regex_only": 0, "jev_only": 0, "neither": 0})
        counts[kind] += 1
        if kind in ("regex_only", "jev_only"):
            disagreements.append({**_base(row), "kind": kind, "regex": row.get("regex"),
                                  "jev_families": families, "scores": scores,
                                  "state": _first_state(row)})
    return {"by_lang": by_lang, "unanswered": unanswered, "disagreements": disagreements}


# ---- skill_router --------------------------------------------------------------------------

# Router answers whose id starts with this are gate questions, never skills.
GATE_PREFIX = "_"
NEW_TASK_ID = "_new_task"


def _router_picks(scores, threshold, top):
    """Jev's suggestion: nothing when its gate says the prompt continues the current work,
    else its `top` highest-scoring skills at or above threshold. Rows from before the gate
    existed have no gate answer and are judged on the skills alone."""
    gate = scores.get(NEW_TASK_ID)
    if gate is not None and gate < threshold:
        return set()
    ranked = sorted(((v, k) for k, v in scores.items()
                     if v >= threshold and not k.startswith(GATE_PREFIX)), reverse=True)
    return {k for _v, k in ranked[:top]}


def _router_verdict(row, threshold, top):
    """(Jev's picks, the score behind each skill it could name) for one row, or None when it was
    unanswered. A row asked the choice shape is read by the production rule `choice_pick` - its
    gate plus its winner's own probability - because a choice's winner is a key, not a score, and
    reading it like a noul row would see no skill at all."""
    results = row.get("results") or []
    result = results[0] if results else None
    if not isinstance(result, dict):
        return None
    answers = result.get("answers") or {}
    if cl.PICK_ID not in answers:
        scores = _scores(result)
        return _router_picks(scores, threshold, top), scores
    winner, probs = _choice_parts(answers, cl.PICK_ID)
    pick = cl.choice_pick(_value(answers, cl.NEW_TASK_ID), winner, probs, threshold=threshold)
    return ({pick} if pick else set()), {k: float(v) for k, v in probs.items()
                                         if isinstance(v, (int, float))}


def summarize_skill_router(rows, threshold, top):
    """The keyword selection against Jev's suggestion: its `top` highest-scoring skills at or
    above threshold on a noul row, the gate-plus-choice pick on a choice row."""
    s = {"prompts": 0, "identical": 0, "regex_picks": 0, "jev_picks": 0, "agreed_picks": 0,
         "unanswered": 0, "disagreements": []}
    for row in rows:
        verdict = _router_verdict(row, threshold, top)
        if verdict is None:
            s["unanswered"] += 1
            continue
        jev, scores = verdict
        regex = set((row.get("regex") or {}).get("selected") or [])
        s["prompts"] += 1
        s["regex_picks"] += len(regex)
        s["jev_picks"] += len(jev)
        s["agreed_picks"] += len(regex & jev)
        if regex == jev:
            s["identical"] += 1
            continue
        s["disagreements"].append({**_base(row), "regex_only": sorted(regex - jev),
                                   "jev_only": sorted(jev - regex),
                                   "jev_scores": {k: scores[k] for k in sorted(regex | jev)
                                                  if k in scores},
                                   "state": _first_state(row)})
    return s


# ---- recall_rerank -------------------------------------------------------------------------

def summarize_recall(rows, threshold):
    """Injected notes against the shortlisted notes Jev scores relevant, and the score spread."""
    s = {"prompts": 0, "regex_injected": 0, "jev_relevant": 0, "agreed": 0, "unanswered": 0,
         "disagreements": []}
    spreads = []
    for row in rows:
        regex = row.get("regex") or {}
        pairs = [(note, sc.get("relevant")) for note, sc
                 in zip(regex.get("shortlist") or [], _answered(row))
                 if sc is not None and sc.get("relevant") is not None]
        if not pairs:
            s["unanswered"] += 1
            continue
        values = [v for _n, v in pairs]
        spreads.append(round(max(values) - min(values), 6))
        injected = set(regex.get("selected") or [])
        jev = {n for n, v in pairs if v >= threshold}
        s["prompts"] += 1
        s["regex_injected"] += len(injected)
        s["jev_relevant"] += len(jev)
        s["agreed"] += len(injected & jev)
        if injected != jev:
            s["disagreements"].append({**_base(row), "regex_only": sorted(injected - jev),
                                       "jev_only": sorted(jev - injected),
                                       "jev_scores": dict(pairs),
                                       "user_prompt": _first_state(row).get("user_prompt")})
    s["spread"] = percentiles(spreads)
    return s


# ---- cost, latency, errors -----------------------------------------------------------------

def percentiles(values):
    """Nearest-rank p50 / p95 / max over `values`."""
    vals = sorted(values)
    if not vals:
        return {"p50": None, "p95": None, "max": None, "n": 0}

    def rank(p):
        return vals[max(0, math.ceil(p * len(vals)) - 1)]

    return {"p50": rank(0.50), "p95": rank(0.95), "max": vals[-1], "n": len(vals)}


def _cost(rows):
    answered = [r for r in rows if any(x is not None for x in _answered(r))]
    errors = Counter()
    for r in rows:
        if r.get("reason"):
            errors[str(r["reason"])] += 1
        elif r not in answered:
            errors["no answer"] += 1
    tokens = [int(r.get("input_tokens") or 0) for r in answered]
    # Sessions on different releases share one log; rows from before the stamp existed say so.
    releases = Counter(str(r.get("plugin_version") or "unversioned") for r in rows)
    return {"rows": len(rows), "errors": dict(errors), "releases": dict(releases),
            "latency_ms": percentiles([int(r.get("latency_ms") or 0) for r in answered]),
            "input_tokens": {"total": sum(tokens),
                             "mean": round(sum(tokens) / len(tokens)) if tokens else None}}


def _group(row):
    """The report key for a row: its site, plus `@<views>` when the row records which views of
    its input the classifier was shown (every `*_view` key, joined in key order), so rows judged
    on different inputs are never pooled."""
    regex = row.get("regex") or {}
    views = [str(regex[k]) for k in sorted(regex) if k.endswith("_view") and regex[k]]
    return "%s@%s" % (row.get("site"), "+".join(views)) if views else row.get("site")


def _base_site(key):
    return key.split("@", 1)[0]


def summarize(rows, threshold, top):
    """The whole report: per site (and input view), the cost block merged with its comparison.

    `threshold` of None judges each site at its own `SITE_THRESHOLDS` default; an explicit value
    overrides every site, which is how one number is compared across them.
    """
    keys = sorted({_group(r) for r in rows if r.get("site") in SITES},
                  key=lambda k: (SITES.index(_base_site(k)), k))
    sites = {}
    for key in keys:
        site_rows = [r for r in rows if _group(r) == key]
        site = _base_site(key)
        at = SITE_THRESHOLDS[site] if threshold is None else threshold
        if site == "stop_signal":
            detail = summarize_stop_signal(site_rows, at)
        elif site == "skill_router":
            detail = summarize_skill_router(site_rows, at, top)
        else:
            detail = summarize_recall(site_rows, at)
        sites[key] = {**_cost(site_rows), **detail, "threshold": at}
    return {"threshold": threshold, "top": top, "rows": len(rows), "sites": sites}


# ---- rendering -----------------------------------------------------------------------------

def _pct(p):
    return "p50 %s  p95 %s  max %s  (n=%s)" % (p["p50"], p["p95"], p["max"], p["n"])


def render_text(rep):
    lines = ["classifier shadow report - threshold %s, router top %s, %d rows"
             % (rep["threshold"] if rep["threshold"] is not None else "per site",
                rep["top"], rep["rows"])]
    for site, s in rep["sites"].items():
        lines += ["", "== %s: %d rows at threshold %s, errors %s"
                  % (site, s["rows"], s["threshold"], s["errors"] or "none"),
                  "   releases     " + ", ".join("%s: %d" % kv for kv in sorted(s["releases"].items())),
                  "   latency ms   " + _pct(s["latency_ms"]),
                  "   input tokens total %s, mean %s" % (s["input_tokens"]["total"],
                                                         s["input_tokens"]["mean"])]
        if _base_site(site) == "stop_signal":
            for lang, c in sorted(s["by_lang"].items()):
                lines.append("   %-8s both %d  regex_only %d  jev_only %d  neither %d"
                             % (lang, c["both"], c["regex_only"], c["jev_only"], c["neither"]))
        elif _base_site(site) == "skill_router":
            lines.append("   prompts %d, identical %d; picks regex %d, jev %d, agreed %d"
                         % (s["prompts"], s["identical"], s["regex_picks"], s["jev_picks"],
                            s["agreed_picks"]))
        else:
            lines.append("   prompts %d; injected %d, jev relevant %d, agreed %d"
                         % (s["prompts"], s["regex_injected"], s["jev_relevant"], s["agreed"]))
            lines.append("   score spread " + _pct(s["spread"]))
        lines.append("   disagreements %d, unanswered %d"
                     % (len(s["disagreements"]), s["unanswered"]))
    return "\n".join(lines)


def _all_disagreements(rep):
    for s in rep["sites"].values():
        yield from s["disagreements"]


def write_disagreements(rep, out):
    with open(out, "w", encoding="utf-8") as fh:
        for d in _all_disagreements(rep):
            fh.write(json.dumps(d, ensure_ascii=False) + "\n")


# ---- CLI -----------------------------------------------------------------------------------

# ---- replay: comparing question shapes offline -----------------------------------------------
# The shadow log cannot answer "would another shape do better", because it only ever carried one.
# These arms ask the same prompts four ways over the recorded corpus, so the question shape and
# the catalogue text can each be attributed instead of shipped together and argued about.

# An arm is a shape plus two flags, deliberately not four separate builders: the only differences
# that may exist between arms are the ones named here, and a reader can check that at a glance.
ARMS = {
    "nouls": {"shape": "nouls", "short": False, "rerank": False, "body": False,
              "router_text": False},
    "choice_full": {"shape": "choice", "short": False, "rerank": False, "body": False,
                    "router_text": False},
    "choice_short": {"shape": "choice", "short": True, "rerank": False, "body": False,
                     "router_text": False},
    "choice_short_rerank": {"shape": "choice", "short": True, "rerank": True, "body": False,
                            "router_text": False},
    # The one text source never tested on a WIDE pass. `choice_short_rerank` did rank on bodies,
    # but it also moved to two requests, so the two changes were confounded and neither was
    # measured; it scored 0 right against 11 misses and the body half was never on trial. Cost is
    # what makes this testable at all: 700-char bodies are about 14,175 tokens a prompt, $5.95 per
    # 10,000 against $3.81 for descriptions, where FULL bodies would be 367,365 and $154.29.
    "choice_body": {"shape": "choice", "short": False, "rerank": False, "body": True,
                    "router_text": False},
    # Option text written FOR the router rather than for the keyword matcher, per the API's own
    # guidance: one discriminating line per option, and the documented OBJECT form
    # ({what, not_for, examples}) for options the model keeps confusing. The adjudication named
    # those: 6 of 11 misses wanted meta-context-watcher and lost to a neighbour while ranking top
    # at 0.58-0.73. Only those skills carry an entry; the rest fall back to their descriptions.
    "choice_router_text": {"shape": "choice", "short": False, "rerank": False, "body": False,
                           "router_text": True},
}
DEFAULT_SHORTLIST = 3
# A prompt this short is a continuation ("go", "yes", "weiter"), which the gate exists to
# suppress. Measured over the corpus: 595 of 1,409 typed prompts. Sampling without splitting on
# it would let one class dominate whichever way the shuffle fell.
CONTINUATION_WORDS = 3
DEFAULT_REPLAY_LOG = Path.home() / ".claude" / "self-improve-audit" / "classifier-replay.jsonl"
DEFAULT_CORPUS = "~/.claude/projects"

# Planted pair, asserted before any number from a run may be read. They must answer DIFFERENTLY:
# an arm that names a skill for everything and an arm that works are the same observation until
# a known negative separates them.
#
# The first pair carries the FULL field set, which is what a live prompt carries from a session's
# second turn on. The second pair carries the MINIMUM one: `user_prompt` and `project`, which is
# a session's FIRST prompt, since `_router_fields` leaves out a field that is empty.
#
# That second pair is here because its absence hid a defect in the gate. Posed with a bare
# `user_prompt`, the gate scored 0.66 to 0.70 against its own 0.7 threshold, and the first
# reading of that was "a control must be posed the way production poses the question". Half
# right: production poses it that way too, on every session's first prompt. Measured 2026-09-23,
# interleaved, 3 runs per arm: the old wording scored the first-prompt positive 0.65, 0.68, 0.67
# - UNDER its own threshold every time, so a real new task was suppressed rather than coin-
# flipped. 7.11.0 builds a question that names `previous_assistant_message` or `recent_activity`
# only when the request carries them, and the same prompt then scores 0.70, 0.72, 0.72 against a
# negative at 0.17 to 0.18. Mid-session was unmoved (0.90 against 0.06), which is how the run
# shows it changed only what it meant to.
#
# The positive clears by 0.02, so this pair is also a tripwire: it separates from its negative by
# about 0.53 but sits close to the threshold, and a wording change that costs a hundredth there
# will fail this control before it reaches a paid run. Naming the absence outright ("no earlier
# reply and no activity yet") was measured as the obvious repair for that margin and REJECTED: it
# inverted the gate, scoring the positive 0.24 and the negative 0.34.
_CONTEXT = {"project": "bitranox-skills: a Claude Code plugin marketplace",
            "recent_activity": "Bash: run make test; Read: classifier.py"}
REPLAY_CONTROLS = (
    {"fields": dict(_CONTEXT,
                    previous_assistant_message="Released 7.9.0 and CI is green on every cell.",
                    user_prompt="the markdown table in README.md has misaligned columns, "
                                "reformat it"),
     "expect_pick": True},
    {"fields": dict(_CONTEXT,
                    previous_assistant_message="I will run the gate now and report what it says.",
                    user_prompt="go ahead"),
     "expect_pick": False},
    {"fields": {"project": _CONTEXT["project"],
                "user_prompt": "the markdown table in README.md has misaligned columns, "
                               "reformat it"},
     "expect_pick": True},
    {"fields": {"project": _CONTEXT["project"], "user_prompt": "go ahead"},
     "expect_pick": False},
)


class ControlFailed(RuntimeError):
    """A planted control answered the wrong way, so the instrument is not measuring."""


def _value(answers, qid):
    """The scalar behind one answer, whether the transport handed back a bare value or a dict."""
    answer = (answers or {}).get(qid)
    return answer.get("value") if isinstance(answer, dict) else answer


def _choice_parts(answers, qid):
    """(winner, probabilities) for a choice answer, tolerating a transport that sends only the
    winner - `probabilities` is optional in the API and absent in several recorded rows."""
    answer = (answers or {}).get(qid)
    if isinstance(answer, dict):
        probs = answer.get("probabilities")
        return answer.get("value"), probs if isinstance(probs, dict) else {}
    return answer, {}


def _roster(skills, spec, bodies=None, router_text=None):
    """The text this arm ranks each skill on: its description, the opening clause of it, the
    skill's own body, or option text authored for the router.

    Every alternative source falls back to the descriptions per missing skill rather than to an
    empty roster: an arm silently ranking nothing answers `none_needed` for everything, which
    reads as a real null instead of a wiring mistake.
    """
    if spec.get("router_text"):
        return {k: (router_text or {}).get(k) or skills[k] for k in skills}
    if spec.get("body"):
        return {k: (bodies or {}).get(k) or skills[k] for k in skills}
    if spec.get("short"):
        return {k: cl.short_description(v) for k, v in skills.items()}
    return dict(skills)


def _noul_picks(answers, roster, threshold, top):
    scored = [(name, _value(answers, name)) for name in roster]
    over = [(n, v) for n, v in scored if isinstance(v, (int, float)) and v >= threshold]
    return [n for n, _v in sorted(over, key=lambda kv: (-kv[1], kv[0]))[:top]]


def _survivors(winner, probs, shortlist):
    """The candidates the close pass re-reads. Ranked by probability when the answer carries a
    distribution, which is the whole reason a choice is worth more than its winner; when it does
    not, the winner alone is all there is to promote."""
    ranked = sorted(((p, n) for n, p in probs.items() if n != cl.NO_SKILL_KEY), reverse=True)
    names = [n for _p, n in ranked[:shortlist]]
    return names or ([winner] if winner and winner != cl.NO_SKILL_KEY else [])


def run_arm(name, ask, fields, skills, *, threshold, top=DEFAULT_TOP,
            shortlist=DEFAULT_SHORTLIST, turn=cl.TURN_PROMPT, bodies=None, router_text=None):
    """Ask one arm about one prompt and report what it would have suggested.

    `ask(fields, questions) -> {question id: value}` is injected, so every test drives this code
    with a fake transport and none of it is patched away.

    A choice arm's winner is not thresholded on its probability to be SUGGESTED - the no-match
    option carries that judgement, which is what it is for. Its probability matters only in the
    other direction: a single-choice arm uses the production rule `classifier.choice_pick`, where a
    winner at `CHOICE_BYPASS` or above overrules a failed gate, and the row records `bypassed`.
    That value was swept on the choice's own scale; a noul at 0.7 and a choice probability at 0.7
    do not mean the same thing, since the API guarantees no comparability between primitives.
    """
    spec = ARMS[name]
    roster = _roster(skills, spec, bodies, router_text)
    build = cl.skill_router_choice_questions if spec["shape"] == "choice" else \
        cl.skill_router_questions
    questions = build(roster, fields, turn=turn)
    answers = ask(fields, questions)
    out = {"arm": name, "answered": answers is not None, "gate": None, "picks": [], "requests": 1,
           "scores": {}}
    if answers is None:
        return out
    # Every score that could move a verdict is kept, not just the verdict. A threshold is the
    # cheapest thing to get wrong and the most expensive to re-measure: judging the close pass at
    # 0.7 rather than the 0.30 its recipe uses cost a whole paid run to discover and another to
    # correct, because the run had recorded what it DECIDED and not what it was told.
    out["scores"] = {qid: (a.get("value") if isinstance(a, dict) else a)
                     for qid, a in answers.items()
                     if not isinstance(a, dict) or not isinstance(a.get("value"), str)}
    # The choice answer is recorded BEFORE the gate is applied, because it was already paid for:
    # it rode in the same request. Discarding it on a gated row made the gate's threshold
    # un-rethresholdable after the fact - an offline sweep could only ever REMOVE picks, never
    # restore one the gate had suppressed, so a flat curve read as "this arm is threshold-
    # insensitive" when it was the log that had gone blank. The noul arm never had the problem,
    # since its per-skill scores are answers like any other.
    if spec["shape"] != "nouls":
        winner, probs = _choice_parts(answers, cl.PICK_ID)
        out["winner"] = winner
        out["probabilities"] = probs
    out["gate"] = _value(answers, cl.NEW_TASK_ID)
    gated = isinstance(out["gate"], (int, float)) and out["gate"] < threshold
    if spec["shape"] != "nouls" and not spec["rerank"]:
        # The single-choice arms take the production rule, so a replay measures what the router
        # would do: the gate, or a winner sure enough to overrule it.
        pick = cl.choice_pick(out["gate"], out["winner"], out["probabilities"],
                              threshold=threshold)
        out["picks"] = [pick] if pick else []
        out["bypassed"] = bool(pick) and gated
        return out
    if gated:
        return out
    if spec["shape"] == "nouls":
        out["picks"] = _noul_picks(answers, roster, threshold, top)
        return out
    winner, probs = out["winner"], out["probabilities"]
    survivors = _survivors(winner, probs, shortlist)
    if not survivors:
        return out
    full = bodies or skills
    close = ask(fields, cl.skill_router_rerank_questions({n: full.get(n, "") for n in survivors}))
    out["requests"] = 2
    if close is None:
        out["answered"] = False
        return out
    final, _probs = _choice_parts(close, cl.PICK_ID)
    out["rerank_winner"] = final
    out["rerank_scores"] = {name: _value(close, name) for name in survivors}
    fits = _value(close, final)
    if final in (None, cl.NO_SKILL_KEY) or not isinstance(fits, (int, float)) or fits < threshold:
        return out
    out["picks"] = [final]
    return out


def run_controls(arm, ask, skills, *, threshold, **kwargs):
    """What one arm answers for each planted control, gate score included.

    The scores are reported and not just the verdict, because a control that passes at 0.71 and
    one that passes at 0.90 are the same row here and a different instrument: the defect this
    caught was a gate ANSWERING, on the right side of the threshold by 0.01.
    """
    rows = []
    for control in REPLAY_CONTROLS:
        out = run_arm(arm, ask, control["fields"], skills, threshold=threshold, **kwargs)
        rows.append({"arm": arm, "prompt": control["fields"]["user_prompt"],
                     "state": sorted(control["fields"]), "expect_pick": control["expect_pick"],
                     "gate": out["gate"], "picks": out["picks"],
                     "ok": bool(out["picks"]) == control["expect_pick"]})
    return rows


def check_controls(arm, ask, skills, *, threshold, **kwargs):
    """Raise unless the planted positives name a skill and the planted negative names none."""
    for row in run_controls(arm, ask, skills, threshold=threshold, **kwargs):
        if not row["ok"]:
            raise ControlFailed(
                "arm %r: control %r (state: %s) expected %s and got %r at gate %r - no number "
                "from this run may be read"
                % (arm, row["prompt"], ", ".join(row["state"]),
                   "a pick" if row["expect_pick"] else "no pick", row["picks"], row["gate"]))


def _is_continuation(prompt):
    return len((prompt or "").split()) <= CONTINUATION_WORDS


def prompts_from_log(path):
    """The exact prompts a previous replay ran on, in their original order.

    `stratified_prompts` samples the transcript corpus, which GROWS between runs, so the same
    seed does not name the same prompts twice. That silently breaks the one comparison a replay
    exists to support: a paid adjudication labels PROMPTS, so a later run sampled from a bigger
    corpus is scored against verdicts describing prompts it never asked about. Reading the set
    back out of an earlier run's log pins it.

    Carries the RECORDED state, and a pinned replay re-sends it verbatim rather than rebuilding
    it. Rebuilding was tried first and is wrong for this job: `_router_fields` derives `project`
    from the nearest CLAUDE.local.md and part of `skills_already_used` from live nudge state,
    and neither is frozen. Measured 2026-09-23 over these 50 prompts, rebuilding reproduced the
    recorded `project` on 39, differed on 8 because a directory had since gained its own scope
    descriptor, and could not resolve a cwd for 3.

    That is real drift in the world, not a defect to resolve harder, and it defeats the one thing
    a pinned run is for: an adjudication labels a PROMPT IN A STATE, so an arm asked about a
    different state is not answering the judged question. Holding the state fixed is also what
    makes this an A/B at all - the arm is the only thing that may differ between runs.
    """
    picked = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        state = row.get("state") or {}
        text = state.get("user_prompt")
        if not text:
            continue
        picked.append({"prompt": text, "uuid": row.get("uuid"), "source": row.get("source"),
                       "line": row.get("line"), "recorded_state": state})
    return picked


def state_drift(picked, rebuilt):
    """Which state fields a pinned replay rebuilt differently from the run that recorded them.

    A pinned run is only comparable to an earlier adjudication if the arms are asked the same
    question, and the question is built from this state. A source transcript that has been moved,
    rewritten or swept rebuilds a SHORTER state in silence, which would read as an arm changing
    its mind. Reports one entry per prompt that differs, naming the fields.
    """
    out = []
    for want, got in zip(picked, rebuilt):
        before = want.get("recorded_state") or {}
        fields = sorted(set(before) | set(got or {}))
        differing = [f for f in fields if (before.get(f) or "") != ((got or {}).get(f) or "")]
        if differing:
            out.append({"uuid": want.get("uuid"), "prompt": (want.get("prompt") or "")[:60],
                        "fields": differing})
    return out


def stratified_prompts(prompts, per_class, seed=0):
    """`per_class` continuations and `per_class` substantial prompts.

    Both classes are needed and for opposite reasons: only a continuation can show the gate
    suppressing, and only a real request can show a pick being right.
    """
    rng = random.Random(seed)
    short = [p for p in prompts if _is_continuation(p.get("prompt"))]
    long_ = [p for p in prompts if not _is_continuation(p.get("prompt"))]
    picked = []
    for group in (short, long_):
        picked += rng.sample(group, min(per_class, len(group)))
    return picked


# How much of a skill's own text the close pass re-reads. The cookbook this shape comes from uses
# 700 characters of the opening body; ours open with a heading and a purpose paragraph, which is
# the part that separates a skill that fits from one that merely sounds related.
DEFAULT_BODY_CAP = 700


def load_skill_bodies(skills_dir=None, cap=DEFAULT_BODY_CAP):
    """{skill name: the opening of its SKILL.md, front matter removed}.

    Front matter is dropped because it holds the description the WIDE pass already ranked on.
    Handing it back would make the close pass the wide pass with fewer options, which can confirm
    a mistake but never correct one.
    """
    skills_dir = Path(skills_dir) if skills_dir else _HOOKS.parent / "skills"
    out = {}
    for md in sorted(Path(skills_dir).glob("*/SKILL.md")):
        try:
            text = md.read_text(encoding="utf-8")
        except OSError:
            continue
        parts = text.split("---", 2)
        body = parts[2] if len(parts) == 3 and not parts[0].strip() else text
        body = body.strip()
        if body:
            out[md.parent.name] = body[:cap]
    return out


def _question_chars(questions):
    return len(json.dumps([q.to_api() for q in questions], ensure_ascii=False))


# A price needs a state, because a question names only the fields the request carries. This is
# the dearest case and the common one: every prompt but a session's first has all of them, and
# only the field NAMES reach the question text, so the values here stand for any content.
SIZING_FIELDS = {"previous_assistant_message": "-", "user_prompt": "-", "project": "-",
                 "recent_activity": "-", "skills_already_used": "-",
                 "task_status": "-", "task_summary": "-"}


def size_replay(skills, prompts, shortlist=DEFAULT_SHORTLIST, turn=cl.TURN_PROMPT,
                fields=None, bodies=None, router_text=None):
    """What a run would cost, calling nothing.

    Counted from the questions the arms really build rather than from a formula, so it cannot
    drift away from them the way a hand-kept constant does.
    """
    fields = SIZING_FIELDS if fields is None else fields
    names = list(skills)[:shortlist]
    close_chars = _question_chars(cl.skill_router_rerank_questions({n: skills[n] for n in names}))
    arms = {}
    for name, spec in ARMS.items():
        roster = _roster(skills, spec, bodies, router_text)
        build = cl.skill_router_choice_questions if spec["shape"] == "choice" else \
            cl.skill_router_questions
        chars = _question_chars(build(roster, fields, turn=turn))
        requests = 2 if spec["rerank"] else 1
        if spec["rerank"]:
            chars += close_chars
        arms[name] = {"chars_per_prompt": chars, "requests_per_prompt": requests,
                      "tokens": chars // 4 * prompts}
    return {"arms": arms, "prompts": prompts,
            "total_tokens": sum(a["tokens"] for a in arms.values()),
            "total_requests": sum(a["requests_per_prompt"] for a in arms.values()) * prompts}


# ---- replay: the run itself ------------------------------------------------------------------


def _load_hook(stem):
    """A hooks/ module whose filename is hyphenated, so `import` cannot reach it."""
    import importlib.util  # noqa: PLC0415 - only the CLI path loads a hook

    path = _HOOKS / ("%s.py" % stem)
    spec = importlib.util.spec_from_file_location(stem.replace("-", "_"), path)
    if spec is None or spec.loader is None:
        raise OSError("cannot load %s" % path)
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(spec.name, module)
    spec.loader.exec_module(module)
    return module


def _prefix_transcript(prompt, tmp_dir):
    """The transcript as it stood the moment this prompt arrived, written to a temp file.

    The arms must be judged on the state the live hook would have built, and the only way to be
    sure of that is to call the hook's own `_router_fields` rather than to rebuild its logic
    here. That function reads a transcript PATH, so the prefix becomes a file.
    """
    source, line = prompt.get("source"), int(prompt.get("line") or 1)
    out = Path(tmp_dir) / "prefix.jsonl"
    try:
        text = Path(source).read_text(encoding="utf-8", errors="replace")
    except OSError:
        out.write_text("", encoding="utf-8")
        return str(out)
    out.write_text("\n".join(text.splitlines()[:max(0, line - 1)]), encoding="utf-8")
    return str(out)


class Asker:
    """The real transport, with token accounting and a bounded retry on a rate limit.

    A 429 or 529 is weather, not a verdict, so it is retried; every other failure is recorded and
    the arm reports itself unanswered rather than silently scoring a prompt it never saw.
    """

    RETRY_ON = ("http 429", "http 529")

    def __init__(self, clf, attempts=3, sleep=None):
        import time  # noqa: PLC0415 - only the live path waits

        self.clf, self.attempts, self._sleep = clf, attempts, sleep or time.sleep
        self.tokens = self.latency = self.calls = 0
        self.reasons = Counter()

    def __call__(self, fields, questions):
        state, _n = cl.prepare_state(fields, key=getattr(self.clf, "key", None))
        for attempt in range(self.attempts):
            result = self.clf.ask(state, questions)
            self.calls += 1
            if result is not None:
                self.tokens += result.input_tokens
                self.latency = max(self.latency, result.latency_ms)
                return {qid: {"value": a.value, "probabilities": a.probabilities,
                              "confidence": a.confidence} for qid, a in result.answers.items()}
            reason = getattr(self.clf, "last_reason", None) or "no answer"
            self.reasons[reason] += 1
            if reason not in self.RETRY_ON or attempt == self.attempts - 1:
                return None
            self._sleep(2 ** (attempt + 1))
        return None


ROSTERS = ("shipped", "installed")


def roster_for(prompt, shipped, mode):
    """(skills, source) a replay offers this prompt.

    `shipped` is this plugin's own skills, which every run before `--roster` offered, so it stays
    the default and old runs stay comparable. `installed` is the listing of the prompt's OWN
    session, read from its source transcript: the question it answers is whether a wider roster
    closes the gap, and that session's skills are what the live router would have had.
    """
    if mode == "installed":
        listing = skill_roster.listing_from_transcript(prompt.get("source") or "")
        if listing:
            return listing, skill_roster.SOURCE_TRANSCRIPT
    return shipped, skill_roster.SOURCE_SHIPPED


def with_descriptions(offered, overrides):
    """(roster, applied): `offered` with each override's text in place of the listed description.

    An installed roster is read from the prompt's own transcript, so it carries the descriptions
    that session saw, and an edited SKILL.md never reaches a replay through it. Overrides are keyed
    by the bare skill name, because a listing names a plugin's skill both bare and prefixed.
    `applied` is returned so a row can prove the override took: a name that matched nothing leaves
    the run identical to its control and would otherwise read as "the new wording changed nothing".
    """
    if not overrides:
        return offered, []
    out = dict(offered)
    applied = [key for key in offered if key.rsplit(":", 1)[-1] in overrides]
    for key in applied:
        out[key] = overrides[key.rsplit(":", 1)[-1]]
    return out, sorted(applied)


def description_override(value):
    """argparse type for `--description SKILL=FILE`: (skill, the file's text)."""
    name, sep, path = value.partition("=")
    if not sep or not name.strip() or not path.strip():
        raise argparse.ArgumentTypeError("expected SKILL=FILE, got %r" % value)
    try:
        text = Path(path).read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise argparse.ArgumentTypeError("cannot read %s: %s" % (path, exc)) from exc
    if not text:
        raise argparse.ArgumentTypeError("%s is empty" % path)
    return name.strip(), text


def selected_arms(arm):
    """The arms a run asks: one when named, else all of them. A paid run that only needs one
    arm should not pay for six."""
    return [arm] if arm else list(ARMS)


def _replay_one(prompt, ask, skills, bodies, router, triggers, args, router_text=None):
    """The chosen arms' verdicts on one prompt, beside the keyword arm's, as one log row."""
    import tempfile  # noqa: PLC0415 - only the live path needs a prefix file

    # A pinned prompt carries the state its own run recorded, and it is re-sent verbatim: see
    # `prompts_from_log` for why rebuilding it cannot be made faithful after the fact.
    fields = prompt.get("recorded_state")
    if not fields:
        with tempfile.TemporaryDirectory() as tmp:
            fields = router._router_fields(  # noqa: SLF001 - the seam under test IS the hook's
                prompt["prompt"], prompt.get("cwd") or "", prompt.get("session_id") or "replay",
                _prefix_transcript(prompt, tmp))
    ranked = router.match(prompt["prompt"], triggers, max_skills=len(triggers) or 1)
    offered, source = roster_for(prompt, skills, getattr(args, "roster", "shipped"))
    overrides = dict(getattr(args, "description", None) or [])
    offered, applied = with_descriptions(offered, overrides)
    row = {"uuid": prompt.get("uuid"), "source": prompt.get("source"), "line": prompt.get("line"),
           "continuation": _is_continuation(prompt.get("prompt")),
           "lang": cl.detect_language(prompt.get("prompt") or ""),
           "keyword_picks": [s for s, _n in ranked[:args.top]], "state": fields,
           "roster": source, "roster_size": len(offered), "arms": {}}
    if overrides:
        row["description_overrides"] = applied
    for name in selected_arms(getattr(args, "arm", None)):
        row["arms"][name] = run_arm(name, ask, fields, offered, threshold=args.threshold,
                                    top=args.top, shortlist=args.shortlist, bodies=bodies,
                                    router_text=router_text)
    return row


def _replay_report(rows, threshold):
    """What the arms did, per arm, so a reader never has to re-derive it from the rows."""
    out = {}
    for name in [n for n in ARMS if rows and n in rows[0]["arms"]]:
        arms = [r["arms"][name] for r in rows]
        picked = [a for a in arms if a["picks"]]
        out[name] = {
            "prompts": len(arms),
            "unanswered": sum(1 for a in arms if not a["answered"]),
            "prompts_with_a_pick": len(picked),
            "picks_per_prompt": round(sum(len(a["picks"]) for a in arms) / max(1, len(arms)), 2),
            "suppressed_by_gate": sum(1 for a in arms if isinstance(a["gate"], (int, float))
                                      and not a["picks"] and a["gate"] < threshold),
            "top_picks": Counter(p for a in arms for p in a["picks"]).most_common(5),
            "agreed_with_keywords": sum(1 for r, a in zip(rows, arms)
                                        if a["picks"] and set(a["picks"]) & set(r["keyword_picks"])),
        }
    return out


def _run_replay(args):
    import corpus_prompts  # noqa: PLC0415 - only the CLI walks a corpus

    router = _load_hook("skill-router")
    skills = cl.load_skill_descriptions()
    if not skills:
        return 2, None, "no skills found - is this running from inside the plugin?"
    bodies = load_skill_bodies()
    router_text = cl.load_router_criteria(skills)
    if args.command == "size":
        return 0, size_replay(skills, args.limit * 2, bodies=bodies,
                              router_text=router_text), None
    clf = cl.get_classifier({"classifier_backend": "jev", "classifier_skill_router": "shadow"},
                            "skill_router", deadline=args.deadline)
    if getattr(clf, "key", None) is None:
        return 2, None, "no api key: %s" % getattr(clf, "last_reason", "unknown")
    if args.command == "controls":
        ask = Asker(clf)
        arms = [args.arm] if args.arm else list(ARMS)
        rows = [row for arm in arms
                for row in run_controls(arm, ask, skills, threshold=args.threshold,
                                        shortlist=args.shortlist, bodies=bodies,
                                        router_text=router_text)]
        return (0 if all(r["ok"] for r in rows) else 3), \
            {"controls": rows, "input_tokens": ask.tokens, "requests": ask.calls,
             "failures": dict(ask.reasons)}, \
            None if all(r["ok"] for r in rows) else "a planted control answered the wrong way"
    if getattr(args, "prompts", None):
        picked, found, typed = prompts_from_log(args.prompts), {"files_read": 0}, []
        if not picked:
            return 1, None, "no prompts in %s" % args.prompts
    else:
        found = corpus_prompts.collect_prompts(args.root)
        typed = [p for p in found["prompts"] if router.prompt_text.typed_by_a_person(p["prompt"])]
        picked = stratified_prompts(typed, args.limit, seed=args.seed)
        if not picked:
            return 1, None, "no typed prompts under %s" % args.root
    ask = Asker(clf)
    check_controls("choice_short_rerank", ask, skills, threshold=args.threshold,
                   shortlist=args.shortlist, bodies=bodies)
    triggers = router.load_triggers()
    rows = []
    # Written as they come, not at the end: a run costs real money and several minutes, and a
    # crash on the last prompt would otherwise discard every row before it.
    with open(args.out, "a", encoding="utf-8") as fh:
        for prompt in picked:
            row = _replay_one(prompt, ask, skills, bodies, router, triggers, args,
                              router_text)
            rows.append(row)
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            fh.flush()
    report = {"corpus": {"files_read": found["files_read"], "typed_prompts": len(typed)},
              "sampled": len(rows), "input_tokens": ask.tokens, "requests": ask.calls,
              "failures": dict(ask.reasons), "log": str(args.out),
              "roster": getattr(args, "roster", "shipped"),
              "rosters_used": dict(Counter(r["roster"] for r in rows)),
              "arms": _replay_report(rows, args.threshold)}
    if getattr(args, "description", None):
        # Rows each override reached, per skill: 0 means the run was its own control.
        report["description_overrides"] = {
            name: sum(1 for r in rows if any(k.rsplit(":", 1)[-1] == name
                                             for k in r.get("description_overrides", [])))
            for name, _text in args.description}
    if getattr(args, "prompts", None):
        drift = state_drift(picked, [r["state"] for r in rows])
        report["pinned_to"] = str(args.prompts)
        report["state_drift"] = drift
    return 0, report, None


def _parser():
    p = argparse.ArgumentParser(prog="classifier_eval.py",
                                description="Compare regex and Jev verdicts from the shadow log.")
    sub = p.add_subparsers(dest="command", required=True)
    for name, helptext in (("replay", "ask the arms over recorded prompts"),
                           ("size", "what a replay would cost, calling nothing"),
                           ("controls", "ask the planted controls only, and report their scores")):
        q = sub.add_parser(name, help=helptext)
        if name in ("controls", "replay"):
            q.add_argument("--arm", choices=sorted(ARMS), default=None,
                           help="one arm (default: every arm)")
        if name == "replay":
            q.add_argument("--roster", choices=ROSTERS, default="shipped",
                           help="the skills offered: this plugin's own (default, comparable with "
                                "earlier runs) or each prompt's session listing (installed)")
            q.add_argument("--description", type=description_override, action="append",
                           default=None, metavar="SKILL=FILE",
                           help="offer SKILL with the text of FILE as its description, to "
                                "measure a reworded description on the same prompts (repeatable)")
        q.add_argument("--root", default=DEFAULT_CORPUS, help="transcript corpus")
        if name == "replay":
            q.add_argument("--prompts", type=Path, default=None, metavar="LOG",
                           help="replay the exact prompts of an earlier run's JSONL log instead "
                                "of sampling the corpus, so the run stays comparable to an "
                                "adjudication that labelled those prompts")
        q.add_argument("--limit", type=int, default=25,
                       help="prompts PER CLASS, continuation and substantial (default 25)")
        q.add_argument("--threshold", type=float, default=SITE_THRESHOLDS["skill_router"])
        q.add_argument("--top", type=int, default=DEFAULT_TOP)
        q.add_argument("--shortlist", type=int, default=DEFAULT_SHORTLIST)
        q.add_argument("--deadline", type=float, default=cl.SHADOW_DEADLINE)
        q.add_argument("--seed", type=int, default=0)
        q.add_argument("--out", type=Path, default=DEFAULT_REPLAY_LOG)
        q.add_argument("--json", action="store_true", help="print a JSON envelope")
    r = sub.add_parser("report", help="summarise the shadow log per site")
    r.add_argument("--log", type=Path, default=None,
                   help="a log file, or a directory whose shadow logs are all read "
                        "(default: ~/.claude/self-improve-audit)")
    r.add_argument("--threshold", type=float, default=None,
                   help="judge every site at this value; omitted, each uses its own default "
                        "(%s)" % ", ".join("%s %s" % kv for kv in sorted(SITE_THRESHOLDS.items())))
    r.add_argument("--top", type=int, default=DEFAULT_TOP,
                   help="how many skills the router would suggest (default 2)")
    r.add_argument("--exclude-session", action="append", default=None, metavar="PREFIX",
                   help="drop rows whose session id starts with PREFIX (default: probe-)")
    r.add_argument("--disagreements", type=Path, metavar="OUT",
                   help="write every disagreement as JSONL to OUT")
    r.add_argument("--json", action="store_true", help="print a JSON envelope")
    return p


def render_replay(data):
    if "controls" in data:
        lines = ["spent: %d requests, %d input tokens; failures: %s"
                 % (data["requests"], data["input_tokens"], data["failures"] or "none")]
        for row in data["controls"]:
            lines.append("  %-20s gate %-5s picks %-28s %s  %s"
                         % (row["arm"], row["gate"], ", ".join(row["picks"]) or "-",
                            "PASS" if row["ok"] else "FAIL",
                            "%s | %s" % (", ".join(row["state"]), row["prompt"][:48])))
        return "\n".join(lines)
    if "arms" in data and "sampled" not in data:                      # a size estimate
        lines = ["%d prompts, %d requests, about %d input tokens in total"
                 % (data["prompts"], data["total_requests"], data["total_tokens"])]
        for name, arm in data["arms"].items():
            lines.append("  %-20s %6d chars/prompt  %d request(s)  ~%d tokens"
                         % (name, arm["chars_per_prompt"], arm["requests_per_prompt"],
                            arm["tokens"]))
        return "\n".join(lines)
    lines = ["corpus: %d files, %d typed prompts; sampled %d"
             % (data["corpus"]["files_read"], data["corpus"]["typed_prompts"], data["sampled"]),
             "spent: %d requests, %d input tokens; failures: %s"
             % (data["requests"], data["input_tokens"], data["failures"] or "none"),
             "log: %s" % data["log"]]
    for name, arm in data["arms"].items():
        lines.append("  %-20s picks/prompt %.2f  with a pick %d/%d  unanswered %d  agreed %d"
                     % (name, arm["picks_per_prompt"], arm["prompts_with_a_pick"], arm["prompts"],
                        arm["unanswered"], arm["agreed_with_keywords"]))
        lines.append("      top: %s" % (arm["top_picks"] or "none"))
    return "\n".join(lines)


def _emit(args, ok, data=None, error=None, skipped=None):
    if args.json:
        env = {"ok": ok, "command": args.command, "data": data, "skipped": skipped or {}}
        if error:
            env["error"] = error
        print(json.dumps(env, ensure_ascii=False, indent=2))
    elif ok or data is not None:
        # A failure that carries data prints it: for `controls` the rows ARE the diagnosis, and a
        # verdict line alone would say a control failed while withholding which one and at what
        # score. The error still goes to stderr, so the exit code and the stream stay separable.
        print(render_replay(data) if args.command in ("replay", "size", "controls")
              else render_text(data))
    if error and not args.json:
        print("classifier_eval: %s" % error, file=sys.stderr)


def main(argv=None):
    args = _parser().parse_args(argv)
    if args.command in ("replay", "size", "controls"):
        try:
            code, data, error = _run_replay(args)
        except ControlFailed as exc:
            _emit(args, False, error=str(exc))
            return 3
        except (OSError, ValueError) as exc:
            _emit(args, False, error="%s: %s" % (type(exc).__name__, exc))
            return 2
        _emit(args, code == 0, data=data, error=error)
        return code
    exclude = tuple(args.exclude_session if args.exclude_session is not None else DEFAULT_EXCLUDE)
    args.log = args.log or default_log()
    try:
        rows, bad = load_rows(args.log, exclude_sessions=exclude)
    except OSError as exc:
        _emit(args, False, error="cannot read %s: %s" % (args.log, exc))
        return 2
    skipped = {"malformed_lines": bad}
    if bad:
        print("classifier_eval: skipped %d malformed line(s)" % bad, file=sys.stderr)
    if not rows:
        _emit(args, False, error="no usable rows in %s" % args.log, skipped=skipped)
        return 1
    rep = summarize(rows, args.threshold, args.top)
    if args.disagreements:
        try:
            write_disagreements(rep, args.disagreements)
        except OSError as exc:
            _emit(args, False, error="cannot write %s: %s" % (args.disagreements, exc))
            return 2
    _emit(args, True, data=rep, skipped=skipped)
    return 0


if __name__ == "__main__":
    sys.exit(main())
