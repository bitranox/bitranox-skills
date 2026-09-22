#!/usr/bin/env python3
"""Compare the regex verdicts with Jev's per classifier site, from the shadow log.

The first-wave classifier sites (hooks/classifier.py) run in shadow mode: the hook keeps its regex
verdict and a detached child logs Jev's answers beside it, one JSON line per prompt or turn, in
~/.claude/self-improve-audit/classifier-shadow.jsonl. `report` reads that log and answers, per site:

  stop_signal    per turn: both fire / regex only / Jev only / neither, split by language
  skill_router   per prompt: the keyword selection against Jev's top N skills above the threshold
  recall_rerank  per prompt: the notes injected by keyword rank against the shortlisted notes Jev
                 scores relevant, plus the spread of Jev's scores (a narrow spread means Jev is not
                 telling the notes apart)

plus latency and token percentiles and the error reasons. Every disagreement can be written to a
JSONL file, carrying the text it was judged on, for adjudication against the source transcript.

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
import sys
from collections import Counter
from pathlib import Path

DEFAULT_LOG = Path.home() / ".claude" / "self-improve-audit" / "classifier-shadow.jsonl"
DEFAULT_THRESHOLD = 0.5

# The threshold each site is judged at when none is given. One number for all three was always a
# placeholder: they ask different questions and their answers are distributed differently.
# Measured over 1,177 recall pair judgements, 0.5 keeps 20% of them (about 5.9 notes a prompt) and
# 0.8 keeps 4% (about 1.1), which is the order of what a prompt can actually use.
SITE_THRESHOLDS = {"stop_signal": 0.7, "skill_router": 0.7, "recall_rerank": 0.8}

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
    """(rows, malformed_line_count). Rows whose session id starts with an excluded prefix are
    dropped. Raises OSError when the log cannot be read."""
    rows, bad = [], 0
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except ValueError:
                bad += 1
                continue
            if not isinstance(row, dict):
                bad += 1
                continue
            sid = str(row.get("session_id") or "")
            if any(sid.startswith(p) for p in exclude_sessions):
                continue
            rows.append(row)
    return rows, bad


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


def summarize_skill_router(rows, threshold, top):
    """The keyword selection against Jev's `top` highest-scoring skills at or above threshold."""
    s = {"prompts": 0, "identical": 0, "regex_picks": 0, "jev_picks": 0, "agreed_picks": 0,
         "unanswered": 0, "disagreements": []}
    for row in rows:
        results = _answered(row)
        scores = results[0] if results else None
        if scores is None:
            s["unanswered"] += 1
            continue
        regex = set((row.get("regex") or {}).get("selected") or [])
        jev = _router_picks(scores, threshold, top)
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
    return {"rows": len(rows), "errors": dict(errors),
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

def _parser():
    p = argparse.ArgumentParser(prog="classifier_eval.py",
                                description="Compare regex and Jev verdicts from the shadow log.")
    sub = p.add_subparsers(dest="command", required=True)
    r = sub.add_parser("report", help="summarise the shadow log per site")
    r.add_argument("--log", type=Path, default=DEFAULT_LOG)
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


def _emit(args, ok, data=None, error=None, skipped=None):
    if args.json:
        env = {"ok": ok, "command": args.command, "data": data, "skipped": skipped or {}}
        if error:
            env["error"] = error
        print(json.dumps(env, ensure_ascii=False, indent=2))
    elif ok:
        print(render_text(data))
    else:
        print("classifier_eval: %s" % error, file=sys.stderr)


def main(argv=None):
    args = _parser().parse_args(argv)
    exclude = tuple(args.exclude_session if args.exclude_session is not None else DEFAULT_EXCLUDE)
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
