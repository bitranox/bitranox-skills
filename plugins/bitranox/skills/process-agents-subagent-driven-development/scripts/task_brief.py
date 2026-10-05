#!/usr/bin/env python3
"""Extract one task's full text from an implementation plan into a file the
implementer reads in one call, so the task text never has to be pasted
through the controller's context.

Usage: python3 task_brief.py PLAN_FILE TASK_ID [OUTFILE]
TASK_ID is the id after "Task" in the heading: 3, 3.5 or 3a.
Default OUTFILE: <repo-root>/.bitranox/sdd/task-<ID>-<plan8>-brief.md, where <plan8>
is a short hash of the plan file's path, so two plans in one working tree never
overwrite each other's brief.

The brief starts with the plan's "Global Constraints" section, verbatim, when it has one:
the writing-plans template makes every task's requirements include it, and a constraint
that names the tasks it applies to ("this applies to Tasks 1, 2 and 6") is otherwise
invisible to an implementer reading one task, whose Files list then looks complete.

Exit 0: the brief was written.
Exit 1: no heading "Task <ID>" in the plan; nothing is written.
Exit 2: bad arguments, no plan file, a plan that cannot be read or is not UTF-8, two or
more headings with that id (each is named with its line; nothing is written), no git
working tree for the default OUTFILE, or an OUTFILE or workspace that cannot be written.
"""
import hashlib
import re
import sys
from pathlib import Path

import sdd_workspace

# The whole id: "Task 3.5" and "Task 3a" are tasks of their own, not part of Task 3.
_TASK_HEADING = re.compile(r"^(#{1,6})[ \t]+Task[ \t]+([0-9]+(?:\.[0-9]+|[A-Za-z])?)\b")
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


def build_brief(plan_text, n):
    """The brief for task N: the Global Constraints section, a blank line, then the task."""
    task = extract_task(plan_text, n)
    if not task:
        return ""
    constraints = global_constraints(plan_text)
    return constraints + "\n" + task if constraints else task


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


def main(argv=None):
    _tolerate_unencodable_output()
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) < 2 or len(argv) > 3:
        print("usage: task_brief.py PLAN_FILE TASK_ID [OUTFILE]", file=sys.stderr)
        return 2
    plan = Path(argv[0])
    n = argv[1]
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
        return 1
    if len(headings) > 1:
        print("task %s is ambiguous in %s: %d headings carry that id, and one brief would hand "
              "an implementer all of them as one task. Rename all but one, then re-run:"
              % (n, plan, len(headings)), file=sys.stderr)
        for number, line in headings:
            print("  line %d: %s" % (number, line), file=sys.stderr)
        return 2
    text = build_brief(plan_text, n)
    try:
        out = Path(argv[2]) if len(argv) == 3 else default_outfile(plan, n)
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
