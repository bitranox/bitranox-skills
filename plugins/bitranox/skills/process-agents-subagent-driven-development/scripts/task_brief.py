#!/usr/bin/env python3
"""Extract one task's full text from an implementation plan into a file the
implementer reads in one call, so the task text never has to be pasted
through the controller's context.

Usage: python3 task_brief.py PLAN_FILE TASK_ID [OUTFILE] [--decision TEXT ...]
                             [--decisions-file PATH]
TASK_ID is the id after "Task" in the heading: 3, 3.5, 3a or 2.1b.
Default OUTFILE: <repo-root>/.bitranox/sdd/task-<ID>-<plan8>-brief.md, where <plan8>
is a short hash of the plan file's path, so two plans in one working tree never
overwrite each other's brief.

The brief starts with the plan's "Global Constraints" section, verbatim, when it has one:
the writing-plans template makes every task's requirements include it, and a constraint
that names the tasks it applies to ("this applies to Tasks 1, 2 and 6") is otherwise
invisible to an implementer reading one task, whose Files list then looks complete.

Next comes the preamble of the section the task sits in (a milestone or phase heading above the
task's level, up to that section's first task), when it holds text: a plan that defines shared
procedures there ("P1 - privacy scan") names them in every task under it, and a brief without them
hands the implementer steps it cannot see. The plan's title section is never carried: its text is
the plan header, written for the controller.

--decision TEXT (repeatable) quotes one of the user's answered questions into the brief, verbatim,
under "## User decisions": the question, the chosen label, each chosen option's description and any
note. TEXT must occur in exactly one record's question or chosen label. The records come from
USER-DECISIONS.jsonl at the main checkout's root, where hooks/user-decision-log.py writes them, or
from --decisions-file. A plan's own summary of an option drops qualifiers, and code built and
reviewed against the summary passes review while contradicting the decision.

Exit 0: the brief was written.
Exit 1: no heading "Task <ID>" in the plan, or a --decision TEXT that matches no record or more
than one (each is named); nothing is written. When the plan has no task heading at all, the
message says so: such a plan needs restructuring, not another id.
Exit 2: bad arguments, no plan file, a plan that cannot be read or is not UTF-8, two or
more headings with that id (each is named with its line; nothing is written), no git
working tree for the default OUTFILE, or an OUTFILE or workspace that cannot be written, or a
decisions file that cannot be found or read.
"""
import argparse
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

import sdd_workspace

# The whole id: "Task 3.5", "Task 3a" and "Task 2.1b" are tasks of their own, not part of Task 3
# or Task 2. The letter may follow a dotted id: a review that splits 2.1 names the new half 2.1b.
_TASK_HEADING = re.compile(r"^(#{1,6})[ \t]+Task[ \t]+([0-9]+(?:\.[0-9]+)*[A-Za-z]?)\b")
_ANY_HEADING = re.compile(r"^(#{1,6})(?:[ \t]|$)")
_CONSTRAINTS_HEADING = re.compile(r"^(#{1,6})[ \t]+Global[ \t]+Constraints\b", re.IGNORECASE)
# CommonMark: up to three spaces of indent, then 3+ backticks or 3+ tildes.
_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")


class _Fence:
    """The open fenced block, if any, tracked the way CommonMark closes it."""

    def __init__(self):
        self.marker = None

    def feed(self, line):
        """Update state for `line`; return True while `line` is fence syntax or fenced content."""
        match = _FENCE.match(line)
        if self.marker is None:
            if match and not (match.group(1)[0] == "`" and "`" in match.group(2)):
                self.marker = match.group(1)
                return True
            return False
        # A closer uses the opener's character, is at least as long, and carries nothing else.
        if (match and match.group(1)[0] == self.marker[0]
                and len(match.group(1)) >= len(self.marker) and not match.group(2).strip()):
            self.marker = None
        return True


def _same_id(found, wanted):
    return found.lower() == str(wanted).strip().lower()


def _plan_lines(plan_text):
    """(line, fenced) per line. Split on newline only: splitlines() would also break on form feed
    and U+2028 and turn mid-line text into a heading."""
    fence = _Fence()
    lines = plan_text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()  # the final newline ends the last line; it does not start another
    for line in lines:
        yield line, fence.feed(line)


def has_task_headings(plan_text):
    """True when any heading outside a fenced block is a 'Task <id>' heading."""
    return any(not fenced and _TASK_HEADING.match(line) for line, fenced in _plan_lines(plan_text))


def task_headings(plan_text, n):
    """Every heading of task N outside a fenced block, as (1-based line number, heading line)."""
    found = []
    for number, (line, fenced) in enumerate(_plan_lines(plan_text), start=1):
        task = None if fenced else _TASK_HEADING.match(line)
        if task and _same_id(task.group(2), n):
            found.append((number, line))
    return found


def global_constraints(plan_text):
    """The plan's Global Constraints section(s), verbatim, or "" when it has none.

    A section runs from its heading to the next task heading or the next heading at its own level
    or above. The task-heading stop matters: the template writes "## Global Constraints" and then
    "### Task 1", which is DEEPER and would otherwise be swallowed into the constraints.
    """
    out = []
    level = None
    for line, fenced in _plan_lines(plan_text):
        if not fenced:
            heading = _ANY_HEADING.match(line)
            opener = _CONSTRAINTS_HEADING.match(line)
            if opener:
                level = len(opener.group(1))
            elif _TASK_HEADING.match(line) or (heading and level is not None
                                               and len(heading.group(1)) <= level):
                level = None
        if level is not None:
            out.append(line)
    while out and not out[-1].strip():
        out.pop()  # the blank lines before the next heading belong to neither
    return "\n".join(out) + ("\n" if out else "")


def section_preamble(plan_text, n):
    """The text of the section enclosing task N, from its heading to its first task, or "".

    The enclosing section is the nearest heading above task N at a strictly higher level that is
    neither a task heading nor a Global Constraints heading (that one is carried already). The
    preamble stops at the first task heading, a heading at the section's own level or above, or a
    Global Constraints heading. It is "" when the section is the plan's title (a level-1 heading
    that opens the plan, whose text is the plan header) or holds nothing but its heading line.
    """
    lines = list(_plan_lines(plan_text))
    headings = [(i, len(m.group(1))) for i, (line, fenced) in enumerate(lines)
                if not fenced and (m := _ANY_HEADING.match(line))]
    task_at = next((i for i, (line, fenced) in enumerate(lines) if not fenced
                    and (m := _TASK_HEADING.match(line)) and _same_id(m.group(2), n)), None)
    if task_at is None:
        return ""
    task_level = len(_TASK_HEADING.match(lines[task_at][0]).group(1))
    enclosing = next(((i, level) for i, level in reversed(headings)
                      if i < task_at and level < task_level
                      and not _TASK_HEADING.match(lines[i][0])), None)
    if enclosing is None or (enclosing[0] == headings[0][0] and enclosing[1] == 1):
        return ""
    start, level = enclosing
    if _CONSTRAINTS_HEADING.match(lines[start][0]):
        return ""
    out = [lines[start][0]]
    for line, fenced in lines[start + 1:]:
        if not fenced:
            heading = _ANY_HEADING.match(line)
            if heading and (len(heading.group(1)) <= level or _TASK_HEADING.match(line)
                            or _CONSTRAINTS_HEADING.match(line)):
                break
        out.append(line)
    while out and not out[-1].strip():
        out.pop()
    if not any(line.strip() for line in out[1:]):
        return ""
    return "\n".join(out) + "\n"


def build_brief(plan_text, n, decisions=()):
    """The brief for task N: the Global Constraints section, the enclosing section's preamble, the
    quoted user decisions, then the task, each separated by a blank line."""
    task = extract_task(plan_text, n)
    if not task:
        return ""
    parts = [part for part in (global_constraints(plan_text), section_preamble(plan_text, n),
                               render_decisions(decisions)) if part]
    return "\n".join(parts + [task])


class DecisionError(Exception):
    """A --decision text that matched no record, or more than one."""


def _hook_module():
    """hooks/user-decision-log.py, loaded by path: it owns where the decision log lives, so the
    reader asks it rather than re-deriving the location."""
    hooks = Path(__file__).resolve().parents[3] / "hooks"
    if str(hooks) not in sys.path:
        sys.path.insert(0, str(hooks))  # the hook imports its sibling self_improve_signals
    spec = importlib.util.spec_from_file_location("user_decision_log",
                                                  hooks / "user-decision-log.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def default_decisions_file(cwd):
    """USER-DECISIONS.jsonl at the main checkout root of the repository `cwd` is in, or None."""
    hook = _hook_module()
    root = hook.main_checkout_root(cwd)
    return None if root is None else root / hook.LOG_NAME


def load_decisions(path):
    """Every well-formed record in a USER-DECISIONS.jsonl file. A line that is not a JSON object
    is skipped: it cannot be quoted, and a text it would have matched is then refused as absent."""
    records = []
    for line in path.read_text(encoding="utf-8").split("\n"):
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if isinstance(record, dict) and isinstance(record.get("question"), str):
            records.append(record)
    return records


def select_decisions(records, texts):
    """The one record each text occurs in (question or chosen label), in the order asked.

    Raises DecisionError naming every text that matched nothing or more than one record: quoting
    the wrong decision verbatim is worse than quoting none.
    """
    chosen, problems = [], []
    for text in texts:
        # `or ""`: a record with no answer must not read as the text "None" and match "one".
        hits = [r for r in records
                if text in (r.get("question") or "") or text in str(r.get("chosen") or "")]
        if len(hits) == 1:
            chosen.append(hits[0])
        elif not hits:
            problems.append("--decision %r matches no recorded question or chosen label" % text)
        else:
            listed = "\n".join("  %s: %s" % (r.get("ts"), r.get("question")) for r in hits)
            problems.append("--decision %r matches %d records; use a longer text:\n%s"
                            % (text, len(hits), listed))
    if problems:
        raise DecisionError("\n".join(problems))
    return chosen


def _chosen_options(record):
    options = [o for o in record.get("options") or [] if isinstance(o, dict)]
    chosen = str(record.get("chosen"))
    exact = [o for o in options if o.get("label") == chosen]
    if exact or not record.get("multiSelect"):
        return exact
    picked = set(chosen.split(", "))  # the form AskUserQuestion reports a multi-select answer in
    return [o for o in options if o.get("label") in picked]


def render_decisions(records):
    """The user's own words for each decision, under one heading, or "" for none."""
    if not records:
        return ""
    out = ["## User decisions (verbatim, from USER-DECISIONS.jsonl)", "",
           "These answers bind this task. Where the plan's wording differs, these govern.", ""]
    for record in records:
        out += ["### %s" % record["question"], "", "Chosen: %s" % record.get("chosen")]
        out += ["- %s: %s" % (o.get("label"), o.get("description", ""))
                for o in _chosen_options(record)]
        if record.get("annotation"):
            out.append("Note: %s" % record["annotation"])
        out.append("")
    return "\n".join(out)


def extract_task(plan_text, n):
    """The lines of task N: from its `Task N` heading up to the next task heading, or the next
    non-task heading at a strictly HIGHER level than the task's own.

    Plans put a task's own sections (Steps, Files, a record of the run) at or below the task
    heading's level, and plan-level sections (a phase, a milestone, Self-review) above it: the
    writing-plans template writes "### Task N" and "## Self-review". So "## Task 1" followed by
    "## Steps" keeps its steps, and "### Task 6" followed by "## Self-review" ends there. A
    trailing section at the task's own level cannot be told from its Steps and stays in the brief.

    A heading inside a fenced block (``` or ~~~, closed per CommonMark) does not start or end a
    task. Two headings with the same id are both collected here; main() refuses that case
    before calling this, because the result would be two unrelated tasks in one brief.
    """
    out = []
    level = None  # the heading level of task N while inside it
    for line, fenced in _plan_lines(plan_text):
        if not fenced:
            task = _TASK_HEADING.match(line)
            heading = _ANY_HEADING.match(line)
            if task:
                level = len(task.group(1)) if _same_id(task.group(2), n) else None
            elif heading and level is not None and len(heading.group(1)) < level:
                level = None
        if level is not None:
            out.append(line)
    return "\n".join(out) + ("\n" if out else "")


def default_outfile(plan, n):
    """Per plan and task, so a second plan in the same working tree cannot clobber this brief."""
    digest = hashlib.sha1(str(plan.resolve()).encode("utf-8")).hexdigest()[:8]
    return sdd_workspace.workspace_dir() / ("task-%s-%s-brief.md" % (n, digest))


def _tolerate_unencodable_output():
    """Replace, rather than crash on, a character the console cannot encode (cp1252 pipes)."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(errors="replace")
            except (ValueError, OSError):
                pass


def _parse(argv):
    parser = argparse.ArgumentParser(prog="task_brief.py", add_help=True)
    parser.add_argument("plan")
    parser.add_argument("task_id")
    parser.add_argument("outfile", nargs="?")
    parser.add_argument("--decision", action="append", default=[], metavar="TEXT")
    parser.add_argument("--decisions-file", metavar="PATH")
    try:
        return parser.parse_args(argv)
    except SystemExit as exc:  # argparse has printed help or usage; main() returns its code
        return exc.code if isinstance(exc.code, int) else 2


def _decisions_for(args):
    """The records the --decision texts select; raises DecisionError or OSError."""
    if not args.decision:
        return []
    path = Path(args.decisions_file) if args.decisions_file else default_decisions_file(Path.cwd())
    if path is None:
        raise OSError("not inside a git work tree, so there is no main checkout to find "
                      "USER-DECISIONS.jsonl in; pass --decisions-file")
    return select_decisions(load_decisions(path), args.decision)


def main(argv=None):
    _tolerate_unencodable_output()
    args = _parse(list(sys.argv[1:] if argv is None else argv))
    if isinstance(args, int):       # --help (0) or a usage error (2), already printed
        return args
    plan = Path(args.plan)
    n = args.task_id
    if not plan.is_file():
        print("no such plan file: %s" % plan, file=sys.stderr)
        return 2
    try:
        # utf-8-sig: a BOM would otherwise sit in front of the first heading and hide it.
        plan_text = plan.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        print("cannot read the plan %s: %s" % (plan, exc), file=sys.stderr)
        return 2
    # Nothing is written on either refusal below: truncating an existing brief would destroy a
    # good one.
    headings = task_headings(plan_text, n)
    if not headings:
        print("task %s not found in %s (no heading matching 'Task %s')" % (n, plan, n),
              file=sys.stderr)
        if not has_task_headings(plan_text):
            print("the plan has no 'Task <id>' headings at all, so there is nothing to extract. "
                  "Restructure the PLAN first, content unchanged: one '### Task <id>: <name>' "
                  "heading per task, and the decisions, measured facts and design every task "
                  "relies on under a '## Global Constraints' heading. Then re-run.",
                  file=sys.stderr)
        return 1
    if len(headings) > 1:
        print("task %s is ambiguous in %s: %d headings carry that id, and one brief would hand "
              "an implementer all of them as one task. Rename all but one, then re-run:"
              % (n, plan, len(headings)), file=sys.stderr)
        for number, line in headings:
            print("  line %d: %s" % (number, line), file=sys.stderr)
        return 2
    try:
        decisions = _decisions_for(args)
    except DecisionError as exc:
        print(exc, file=sys.stderr)
        return 1
    except (OSError, UnicodeDecodeError) as exc:
        print("cannot read the decisions file: %s" % exc, file=sys.stderr)
        return 2
    text = build_brief(plan_text, n, decisions)
    try:
        out = Path(args.outfile) if args.outfile else default_outfile(plan, n)
    except sdd_workspace.WorkspaceError as exc:
        print(exc, file=sys.stderr)
        return 2
    try:
        out.write_text(text, encoding="utf-8")
    except OSError as exc:
        print("cannot write the brief: %s" % exc, file=sys.stderr)
        return 2
    print("wrote %s: %d lines" % (out, len(text.split("\n")) - 1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
