#!/usr/bin/env python3
"""Offline: would Jev have pointed at a toolbox jig where the keyword rules were silent, and which
recurring chores have no jig at all?

Jig suggestion today is `toolbox-nudge.py`, a regex over the pending command or the file being
written. It works well for what it knows - measured 917 surfacings against 3 from the prompt
router - but a regex can only match shapes somebody already wrote down. Two consequences: the jigs
with no rule can never be suggested however well they fit, and a NEW jig is by definition a shape
no rule describes, so the channel that suggests tools cannot discover one.

This asks the question OFFLINE, against tool calls already recorded in the transcript corpus, so
it costs no session tokens and touches no hot path.

ONE request per call, not a gate plus a choice. A two-stage shape was tried first, copying the
router's `_new_task` gate, and it failed its own control: `pgrep -f ...` scored 0.12 on "is this a
hand-rolled chore", because the gate's own exclusion ("answer no for ordinary use of a normal
program") describes `pgrep` exactly. The gate that works for SKILLS asks about the turn; a gate
about a COMMAND runs into the command's own vocabulary. The choice stage needed no such help -
measured on nine hand-labelled commands it answered procsig, procsig, ordinary, ordinary,
ordinary, git_state and uncovered as labelled, and its two disagreements were defensible readings
rather than errors.

The two "no tool" answers are kept apart on purpose. `none_ordinary` is work no tool would
improve; `none_uncovered` is a real chore that nothing listed does, and THAT is the answer to
"should we build one". Collapsing them into one silence loses the reason this probe exists.

Run:
  jig_probe.py size --limit 200            # what it would ask and cost, calls nothing
  jig_probe.py run  --limit 200            # asks, appends rows to the log
  jig_probe.py report                      # reads the log back

Exit codes: 0 fine, 1 nothing to report, 2 usage or IO error, 3 a control failed (the instrument
is wrong, so no number from the run may be read).
"""

import argparse
import json
import random
import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_HOOKS = _HERE.parent.parent / "hooks"
_JIGS = _HERE.parent / "compuse-toolbox" / "scripts"
for _d in (str(_HOOKS), str(_JIGS)):
    if _d not in sys.path:
        sys.path.insert(0, _d)

from classifier import Question, get_classifier, prepare_state  # noqa: E402

__all__ = [
    "CHOICE_ID", "CONTROLS", "ControlFailed", "ORDINARY_KEY", "UNCOVERED_KEY", "check_controls",
    "choice_question", "collect_calls", "decide", "jig_catalogue", "main", "regex_jig",
    "stratified_sample", "summarize", "toolbox_nudge",
]

CHOICE_ID = "which_jig"
ORDINARY_KEY = "none_ordinary"
UNCOVERED_KEY = "none_uncovered"
JIG_LOG = "jig-probe.jsonl"
# Charged per call at the rate the diagnostic measured: the state is one command, the criteria are
# the whole catalogue. Deliberately an over-estimate, since the point is to refuse a surprise.
CALL_TOKENS = 3200
_SENTENCE = re.compile(r"^(.+?[.!?])(?:\s|$)", re.S)


class ControlFailed(RuntimeError):
    """A planted control answered the wrong way, so the instrument is not measuring."""


# Asserted before any real number is read. A detector that fires on everything and a detector that
# works are indistinguishable without a known NEGATIVE.
CONTROLS = (
    {"command": "pgrep -f 'my-daemon --serve'", "cwd": "/tmp", "expect": "procsig"},
    {"command": "echo hello", "cwd": "/tmp", "expect": None},
)


def jig_catalogue(scripts_dir=None):
    """{jig name: its first sentence} from each shipped script's module docstring."""
    d = Path(scripts_dir) if scripts_dir else _JIGS
    out = {}
    for path in sorted(d.glob("*.py")):
        if path.stem.startswith("__"):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        doc = re.search(r'"""(.*?)"""', text, re.S)
        if not doc:
            continue
        body = doc.group(1).strip()
        match = _SENTENCE.match(body)
        summary = " ".join((match.group(1) if match else body).split())
        if summary:
            out[path.stem] = summary
    return out


def choice_question(catalogue):
    """One request: which jig does this command's job, or which kind of nothing."""
    criteria = {
        ORDINARY_KEY: "Ordinary work: a one-off, or straightforward use of a program for its own "
                      "purpose. No small tool would make it more reliable.",
        UNCOVERED_KEY: "A repeated chore that a small tool WOULD do more reliably - parsing, "
                       "scanning, polling, waiting, comparing, counting - but no tool listed here "
                       "does this job.",
    }
    criteria.update(catalogue)
    return Question(
        CHOICE_ID, "choice",
        "Which of these does the job that `command` is doing? Choose a named tool only when it "
        "genuinely does this job; one that merely sounds related is wrong. Otherwise choose %r or "
        "%r." % (ORDINARY_KEY, UNCOVERED_KEY), criteria=criteria)


def decide(choice):
    """The suggestion for one call: a jig name, `UNCOVERED_KEY`, or None for ordinary work.

    `UNCOVERED_KEY` is deliberately not None: a chore with no tool is the answer to "should we
    build one", and collapsing it into silence loses exactly the signal this probe exists for.
    """
    if choice in (None, ORDINARY_KEY):
        return None
    return choice


def collect_calls(root, tool="Bash"):
    """Every distinct recorded call of `tool`, via guard_replay's own walk - it already dedupes by
    tool_use id, which a resumed or forked session otherwise double-counts."""
    import guard_replay  # noqa: PLC0415 - a shipped jig, imported here so --help needs no corpus

    collected = []

    def collect(command, cwd=None):
        collected.append({"id": None, "command": command, "cwd": cwd})
        return False

    guard_replay.replay(str(root), collect, tool=tool)
    for i, call in enumerate(collected):
        call["id"] = "%s-%d" % (tool, i)
    return collected


def stratified_sample(calls, already_covered, per_class, seed=0):
    """`per_class` calls the keyword rules already speak on and `per_class` they are silent on.

    Both classes are needed: only the silent ones can show a gap, and only the covered ones can
    show whether Jev agrees with a channel that is known to work.
    """
    rng = random.Random(seed)
    covered, silent = [], []
    for call in calls:
        (covered if already_covered(call) else silent).append(call)
    picked = []
    for group in (covered, silent):
        picked += rng.sample(group, min(per_class, len(group)))
    return picked


def _ask(clf, command, cwd, question):
    """(choice, tokens) for one call."""
    state, _n = prepare_state({"command": command, "cwd": cwd or ""}, key=getattr(clf, "key", None))
    result = clf.ask(state, [question])
    if result is None:
        return None, 0
    return result.answers[CHOICE_ID].value, result.input_tokens


def check_controls(clf, catalogue):
    """Raise unless the planted positive names a jig and the planted negative names none."""
    question = choice_question(catalogue)
    positive, negative = CONTROLS
    for control, label in ((positive, "known positive"), (negative, "known negative")):
        choice, _t = _ask(clf, control["command"], control["cwd"], question)
        got = decide(choice)
        if control["expect"] is None and got is not None:
            raise ControlFailed(
                "the %s (%r) was answered %r; a detector that speaks on ordinary commands cannot "
                "measure anything" % (label, control["command"], got))
        if control["expect"] is not None and got in (None, UNCOVERED_KEY):
            raise ControlFailed(
                "the %s (%r) was answered %r, expected %r"
                % (label, control["command"], got, control["expect"]))


def summarize(rows):
    """The four ways the two channels can land, plus the chores no jig covers, plus the cost."""
    rep = {"rows": len(rows), "agreed": 0, "both_but_different": 0, "regex_only": 0,
           "jev_only": 0, "neither": 0, "chore_without_a_jig": 0, "uncovered_examples": [],
           "input_tokens": sum(int(r.get("input_tokens") or 0) for r in rows), "by_jig": {}}
    for row in rows:
        regex, jev = row.get("regex_jig"), row.get("jev_jig")
        if jev == UNCOVERED_KEY:
            rep["chore_without_a_jig"] += 1
            rep["uncovered_examples"].append({"command": row["command"], "cwd": row.get("cwd")})
            jev = None
        if jev:
            rep["by_jig"][jev] = rep["by_jig"].get(jev, 0) + 1
        if regex and jev:
            rep["agreed" if regex == jev else "both_but_different"] += 1
        elif regex:
            rep["regex_only"] += 1
        elif jev:
            rep["jev_only"] += 1
        else:
            rep["neither"] += 1
    return rep


# ---- the keyword channel, as the thing to compare against ------------------------------------

_NUDGE = None


def toolbox_nudge():
    """The shipped hook, loaded by path because its filename is hyphenated."""
    global _NUDGE
    if _NUDGE is None:
        import importlib.util  # noqa: PLC0415 - hyphenated module, so it loads by path
        spec = importlib.util.spec_from_file_location("toolbox_nudge", _HOOKS / "toolbox-nudge.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules["toolbox_nudge"] = module
        spec.loader.exec_module(module)
        _NUDGE = module
    return _NUDGE


def regex_jig(call, tool="Bash"):
    """What `toolbox-nudge.py` would ACTUALLY say about this call, or None.

    Through the hook's own two pure seams, never a private rule list: `extract_text` blanks
    heredoc bodies and unexpanded quoted text first, so a chore merely NAMED inside a written
    document is not a firing. Matching the raw command instead measured a more trigger-happy
    matcher than the one that ships, and charged Jev with disagreeing with rules that had not
    spoken.
    """
    nudge = toolbox_nudge()
    text = nudge.extract_text(tool, {"command": call.get("command") or ""})
    if text is None:
        return None
    hit = nudge.match_tool(text, tool_name=tool)
    return hit[0] if hit else None


# ---- CLI --------------------------------------------------------------------------------------

def _envelope(ok, command, data=None, error=None):
    out = {"ok": ok, "command": command, "data": data or {}, "skipped": []}
    if error:
        out["error"] = error
    return out


def _log_path(named):
    return Path(named) if named else Path.home() / ".claude" / "self-improve-audit" / JIG_LOG


def _size(args):
    calls = collect_calls(args.root, args.tool)
    asked = min(args.limit, len(calls)) * 2
    return {"calls_in_corpus": len(calls), "would_ask_about": asked,
            "estimated_input_tokens": asked * CALL_TOKENS,
            "note": "one request per call, charged at the rate the diagnostic measured"}


def _run(args):
    catalogue = jig_catalogue()
    clf = get_classifier({"classifier_backend": "jev", "classifier_" + args.site: "shadow"},
                         args.site, deadline=args.deadline)
    # Ask the OBJECT, never the API: a probe request sent to find out whether we may spend is
    # itself spending.
    if getattr(clf, "key", None) is None:
        raise LookupError("no classifier: %s" % clf.last_reason)
    check_controls(clf, catalogue)
    question = choice_question(catalogue)
    calls = collect_calls(args.root, args.tool)
    picked = stratified_sample(calls, lambda c: regex_jig(c) is not None, args.limit, args.seed)
    rows, log = [], _log_path(args.log)
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as fh:
        for call in picked:
            choice, tokens = _ask(clf, call["command"], call.get("cwd"), question)
            row = {"command": call["command"][:2000], "cwd": call.get("cwd"),
                   "regex_jig": regex_jig(call), "choice": choice, "jev_jig": decide(choice),
                   "input_tokens": tokens}
            rows.append(row)
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return summarize(rows)


def _report(args):
    rows = [json.loads(x) for x in
            _log_path(args.log).read_text(encoding="utf-8").splitlines() if x.strip()]
    if not rows:
        raise LookupError("no rows in %s" % _log_path(args.log))
    return summarize(rows)


def _parse(argv):
    p = argparse.ArgumentParser(prog="jig_probe.py", description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("size", "run"):
        s = sub.add_parser(name)
        s.add_argument("--root", default=str(Path.home() / ".claude" / "projects"))
        s.add_argument("--tool", default="Bash")
        s.add_argument("--limit", type=int, default=100, help="calls per class")
        s.add_argument("--seed", type=int, default=0)
        s.add_argument("--json", action="store_true")
        if name == "run":
            s.add_argument("--site", default="skill_router",
                           help="which site's config knob authorises the spend")
            s.add_argument("--deadline", type=float, default=25.0)
            s.add_argument("--log", default=None)
    r = sub.add_parser("report")
    r.add_argument("--log", default=None)
    r.add_argument("--json", action="store_true")
    return p.parse_args(argv)


def main(argv=None):
    args = _parse(argv if argv is not None else sys.argv[1:])
    try:
        data = {"size": _size, "run": _run, "report": _report}[args.cmd](args)
    except ControlFailed as exc:
        print(json.dumps(_envelope(False, args.cmd, error=str(exc))))
        return 3
    except LookupError as exc:
        print(json.dumps(_envelope(False, args.cmd, error=str(exc))))
        return 1
    except OSError as exc:
        print(json.dumps(_envelope(False, args.cmd, error=str(exc))))
        return 2
    if getattr(args, "json", False):
        print(json.dumps(_envelope(True, args.cmd, data), ensure_ascii=False))
    else:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
