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

A classifier request that FAILS (an outage, a timeout) is never read as Jev saying nothing: the row
is logged with the failure's reason and counted as `unanswered`, outside the four-way comparison,
and a run or report holding any such row exits 2.

Exit codes: 0 fine, 1 nothing to report (an empty corpus or log), 2 usage, IO or classifier error
(no key, a failed request, a missing root, a bad flag, a malformed log line, an unexpected crash),
3 a control failed (the instrument is wrong, so no number from the run may be read).
"""

import argparse
import json
import random
import re
import sys
import traceback
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_HOOKS = _HERE.parent.parent / "hooks"
_JIGS = _HERE.parent / "compuse-toolbox" / "scripts"
for _d in (str(_HOOKS), str(_JIGS)):
    if _d not in sys.path:
        sys.path.insert(0, _d)

from classifier import Question, get_classifier, prepare_state  # noqa: E402

__all__ = [
    "CHOICE_ID", "CONTROLS", "ClassifierFailed", "ClassifierUnavailable", "ControlFailed",
    "NothingToReport", "ORDINARY_KEY", "UNCOVERED_KEY", "check_controls", "choice_question",
    "collect_calls", "decide", "jig_catalogue", "main", "regex_jig", "stratified_sample",
    "summarize", "toolbox_nudge",
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


class ClassifierFailed(RuntimeError):
    """A request got no answer (outage, timeout). Not an answer of "no jig" - no answer at all."""


class ClassifierUnavailable(RuntimeError):
    """No classifier can be asked here (no key, backend off): setup, not "nothing to report"."""


class NothingToReport(Exception):
    """An empty corpus or an empty log: the documented exit 1.

    Its own class rather than LookupError, because a stray KeyError is a LookupError too and
    would otherwise report a crash as "nothing to report".
    """


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
    """(calls, skipped): every distinct recorded call of `tool`, and every transcript that could
    not be read.

    Via guard_replay's own walk - it already dedupes by tool_use id, which a resumed or forked
    session otherwise double-counts. Its `skipped` list is passed on rather than dropped, so an
    unreadable transcript is visible instead of a silently smaller corpus. A root that does not
    exist is refused (FileNotFoundError, exit 2) rather than read as an empty corpus.
    """
    import guard_replay  # noqa: PLC0415 - a shipped jig, imported here so --help needs no corpus

    base = Path(root).expanduser()
    if not base.exists():
        raise FileNotFoundError("no transcript corpus at %s" % base)
    collected = []

    def collect(command, cwd=None):
        collected.append({"id": None, "command": command, "cwd": cwd})
        return False

    report = guard_replay.replay(str(base), collect, tool=tool)
    for i, call in enumerate(collected):
        call["id"] = "%s-%d" % (tool, i)
    return collected, list(report.get("skipped") or [])


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
    """(choice, tokens, failure) for one call; `failure` is None when the request was answered.

    A None result is the classifier FAILING (JevClassifier.ask returns None on an HTTP error or a
    timeout), which is not the same fact as Jev choosing nothing - so it carries the reason.
    """
    state, _n = prepare_state({"command": command, "cwd": cwd or ""}, key=getattr(clf, "key", None))
    result = clf.ask(state, [question])
    answer = None if result is None else result.answers.get(CHOICE_ID)
    if answer is None:
        return None, 0, str(getattr(clf, "last_reason", None) or "no answer")
    return answer.value, result.input_tokens, None


def check_controls(clf, catalogue):
    """Raise unless the planted positive names its EXPECTED jig and the planted negative names none.

    Raises ClassifierFailed when a control gets no answer at all: an outage would otherwise pass
    the negative control, whose expected answer is silence.
    """
    question = choice_question(catalogue)
    positive, negative = CONTROLS
    for control, label in ((positive, "known positive"), (negative, "known negative")):
        choice, _t, failure = _ask(clf, control["command"], control["cwd"], question)
        if failure is not None:
            raise ClassifierFailed("the %s (%r) got no answer: %s"
                                   % (label, control["command"], failure))
        got = decide(choice)
        if control["expect"] is None and got is not None:
            raise ControlFailed(
                "the %s (%r) was answered %r; a detector that speaks on ordinary commands cannot "
                "measure anything" % (label, control["command"], got))
        if control["expect"] is not None and got != control["expect"]:
            raise ControlFailed(
                "the %s (%r) was answered %r, expected %r"
                % (label, control["command"], got, control["expect"]))


def summarize(rows):
    """The four ways the two channels can land, plus the chores no jig covers, plus the cost.

    A row whose request got no answer (`choice` null) is counted as `unanswered` and kept OUT of
    the four-way comparison: counted there it read as Jev being silent, which inflated
    `regex_only` and `neither` - the probe's headline numbers - with an outage.
    """
    rep = {"rows": len(rows), "agreed": 0, "both_but_different": 0, "regex_only": 0,
           "jev_only": 0, "neither": 0, "chore_without_a_jig": 0, "uncovered_examples": [],
           "unanswered": 0,
           "input_tokens": sum(int(r.get("input_tokens") or 0) for r in rows), "by_jig": {}}
    for row in rows:
        if row.get("choice") is None:
            rep["unanswered"] += 1
            continue
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
    import guard_replay  # noqa: PLC0415 - a shipped jig, imported here so --help needs no corpus

    # `call["command"]` holds the tool's PAYLOAD (a Write's content, an Edit's new_string), so it
    # goes back under that tool's own field: keyed as "command", a Write read as empty text and
    # the keyword arm never spoke, disagreeing with the hook it stands in for.
    nudge = toolbox_nudge()
    payload = {guard_replay.payload_field(tool): call.get("command") or ""}
    text = nudge.extract_text(tool, payload)
    if text is None:
        return None
    hit = nudge.match_tool(text, tool_name=tool)
    return hit[0] if hit else None


# ---- CLI --------------------------------------------------------------------------------------

def _envelope(ok, command, data=None, error=None, skipped=None):
    out = {"ok": ok, "command": command, "data": data or {}, "skipped": list(skipped or [])}
    if error:
        out["error"] = error
    return out


class _Outcome:
    """What a subcommand produced: the data, what it could not read, and why it is not clean."""

    def __init__(self, data, skipped=(), problem=None):
        self.data, self.skipped, self.problem = data, list(skipped), problem


def _log_path(named):
    return Path(named) if named else Path.home() / ".claude" / "self-improve-audit" / JIG_LOG


def _calls_or_nothing(args):
    calls, skipped = collect_calls(args.root, args.tool)
    if not calls:
        raise NothingToReport("no %s calls under %s" % (args.tool, args.root))
    return calls, skipped


def _size(args):
    calls, skipped = _calls_or_nothing(args)
    asked = min(args.limit, len(calls)) * 2
    return _Outcome({"calls_in_corpus": len(calls), "would_ask_about": asked,
                     "estimated_input_tokens": asked * CALL_TOKENS,
                     "note": "one request per call, charged at the rate the diagnostic measured"},
                    skipped)


def _run(args):
    catalogue = jig_catalogue()
    clf = get_classifier({"classifier_backend": "jev", "classifier_" + args.site: "shadow"},
                         args.site, deadline=args.deadline)
    # Ask the OBJECT, never the API: a probe request sent to find out whether we may spend is
    # itself spending.
    if getattr(clf, "key", None) is None:
        raise ClassifierUnavailable("no classifier: %s" % clf.last_reason)
    # The corpus is read BEFORE the paid control asks, so a mistyped --root costs nothing.
    calls, skipped = _calls_or_nothing(args)
    check_controls(clf, catalogue)
    question = choice_question(catalogue)
    picked = stratified_sample(calls, lambda c: regex_jig(c, args.tool) is not None, args.limit,
                               args.seed)
    rows, log = [], _log_path(args.log)
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as fh:
        for call in picked:
            choice, tokens, failure = _ask(clf, call["command"], call.get("cwd"), question)
            row = {"command": call["command"][:2000], "cwd": call.get("cwd"),
                   "regex_jig": regex_jig(call, args.tool), "choice": choice,
                   "jev_jig": decide(choice), "input_tokens": tokens}
            if failure is not None:
                row["failed"] = failure
            rows.append(row)
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return _with_unanswered(summarize(rows), skipped)


def _with_unanswered(data, skipped, problem=None):
    if data["unanswered"] and problem is None:
        problem = ("%d of %d classifier requests got no answer; they are counted as unanswered "
                   "and excluded from the comparison" % (data["unanswered"], data["rows"]))
    return _Outcome(data, skipped, problem)


def _report(args):
    path = _log_path(args.log)
    # utf-8-sig: a BOM would otherwise break the first row. split("\n") rather than splitlines():
    # rows are written with ensure_ascii=False, so a U+2028 inside a command sits raw in its line.
    text = path.read_text(encoding="utf-8-sig")
    rows, malformed = [], []
    for number, line in enumerate(text.split("\n"), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError as exc:
            malformed.append("%s line %d: %s" % (path, number, exc))
            continue
        if isinstance(row, dict):
            rows.append(row)
        else:
            malformed.append("%s line %d: not a JSON object" % (path, number))
    if not rows and not malformed:
        raise NothingToReport("no rows in %s" % path)
    data = summarize(rows)
    data["malformed_lines"] = len(malformed)
    problem = ("%d malformed line(s) in %s were skipped" % (len(malformed), path)
               if malformed else None)
    return _with_unanswered(data, malformed, problem)


def _at_least_one(text):
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError("not a whole number: %r" % text) from None
    if value < 1:
        raise argparse.ArgumentTypeError("%r must be at least 1" % text)
    return value


def _parse(argv):
    p = argparse.ArgumentParser(prog="jig_probe.py", description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("size", "run"):
        s = sub.add_parser(name)
        s.add_argument("--root", default=str(Path.home() / ".claude" / "projects"))
        s.add_argument("--tool", default="Bash")
        s.add_argument("--limit", type=_at_least_one, default=100, help="calls per class")
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


def _fail(command, exc, code):
    # ensure_ascii (the default) on stdout: a cp1252 console cannot encode most of Unicode.
    print(json.dumps(_envelope(False, command, error=str(exc))))
    return code


def main(argv=None):
    args = _parse(argv if argv is not None else sys.argv[1:])
    try:
        outcome = {"size": _size, "run": _run, "report": _report}[args.cmd](args)
    except ControlFailed as exc:
        return _fail(args.cmd, exc, 3)
    except NothingToReport as exc:
        return _fail(args.cmd, exc, 1)
    except (ClassifierUnavailable, ClassifierFailed, OSError, ValueError) as exc:
        # ValueError covers guard_replay.UnsupportedTool and a JSONDecodeError alike.
        return _fail(args.cmd, exc, 2)
    except Exception as exc:  # noqa: BLE001 - a crash must not exit 1, which means "nothing to report"
        traceback.print_exc(file=sys.stderr)
        return _fail(args.cmd, "unexpected %s: %s" % (type(exc).__name__, exc), 2)
    ok = outcome.problem is None
    if getattr(args, "json", False):
        print(json.dumps(_envelope(ok, args.cmd, outcome.data, error=outcome.problem,
                                   skipped=outcome.skipped)))
    else:
        print(json.dumps(outcome.data, indent=2))
        for item in outcome.skipped:
            print("skipped: %s" % item, file=sys.stderr)
        if outcome.problem:
            print("error: %s" % outcome.problem, file=sys.stderr)
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
