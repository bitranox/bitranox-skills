#!/usr/bin/env python3
"""Extract one task's full text from an implementation plan into a file the
implementer reads in one call, so the task text never has to be pasted
through the controller's context.

Usage: python3 task_brief.py PLAN_FILE TASK_ID [OUTFILE]
TASK_ID is the id after "Task" in the heading: 3, 3.5 or 3a.
Default OUTFILE: <repo-root>/.bitranox/sdd/task-<ID>-<plan8>-brief.md, where <plan8>
is a short hash of the plan file's path, so two plans in one working tree never
overwrite each other's brief. A task that is not found writes nothing (exit 3).
"""
import hashlib
import re
import sys
from pathlib import Path

import sdd_workspace

# The whole id: "Task 3.5" and "Task 3a" are tasks of their own, not part of Task 3.
_TASK_HEADING = re.compile(r"^(#{1,6})[ \t]+Task[ \t]+([0-9]+(?:\.[0-9]+|[A-Za-z])?)\b")
_ANY_HEADING = re.compile(r"^(#{1,6})(?:[ \t]|$)")
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


def extract_task(plan_text, n):
    """The lines of task N: from its `Task N` heading up to the next task heading, or the next
    heading at the same or a higher level (a trailing "## Notes" is not part of the last task).

    A heading inside a fenced block (``` or ~~~, closed per CommonMark) does not start or end a
    task. Lines are split on newline only: splitlines() would also break on form feed and
    U+2028 and turn mid-line text into a heading.
    """
    out = []
    fence = _Fence()
    level = None  # the heading level of task N while inside it
    lines = plan_text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()  # the final newline ends the last line; it does not start another
    for line in lines:
        if not fence.feed(line):
            task = _TASK_HEADING.match(line)
            heading = _ANY_HEADING.match(line)
            if task:
                level = len(task.group(1)) if _same_id(task.group(2), n) else None
            elif heading and level is not None and len(heading.group(1)) <= level:
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
    # utf-8-sig: a BOM would otherwise sit in front of the first heading and hide it.
    text = extract_task(plan.read_text(encoding="utf-8-sig"), n)
    if not text:
        # Nothing is written: truncating an existing brief would destroy a good one.
        print("task %s not found in %s (no heading matching 'Task %s')" % (n, plan, n),
              file=sys.stderr)
        return 3
    out = Path(argv[2]) if len(argv) == 3 else default_outfile(plan, n)
    out.write_text(text, encoding="utf-8")
    print("wrote %s: %d lines" % (out, len(text.split("\n")) - 1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
