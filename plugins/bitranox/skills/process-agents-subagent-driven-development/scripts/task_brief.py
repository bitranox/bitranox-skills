#!/usr/bin/env python3
"""Extract one task's full text from an implementation plan into a file the
implementer reads in one call, so the task text never has to be pasted
through the controller's context.

Usage: python3 task_brief.py PLAN_FILE TASK_NUMBER [OUTFILE]
Default OUTFILE: <repo-root>/.bitranox/sdd/task-<N>-brief.md
(per worktree; concurrent runs in the same working tree share it).
"""
import re
import sys
from pathlib import Path

import sdd_workspace

_HEADING = re.compile(r"^#+[ \t]+Task[ \t]+([0-9]+)")


def extract_task(plan_text, n):
    """The lines of task N: from its `Task N` heading up to the next task heading.

    A heading inside a ``` fence does not start or end a task (fence lines toggle
    state first, exactly like the reader of the rendered plan perceives it).
    """
    out = []
    in_fence = in_task = False
    for line in plan_text.splitlines():
        if line.startswith("```"):
            in_fence = not in_fence
        elif not in_fence:
            m = _HEADING.match(line)
            if m:
                in_task = m.group(1) == str(n)
        if in_task:
            out.append(line)
    return "\n".join(out) + ("\n" if out else "")


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) < 2 or len(argv) > 3:
        print("usage: task_brief.py PLAN_FILE TASK_NUMBER [OUTFILE]", file=sys.stderr)
        return 2
    plan = Path(argv[0])
    n = argv[1]
    if not plan.is_file():
        print("no such plan file: %s" % plan, file=sys.stderr)
        return 2
    out = Path(argv[2]) if len(argv) == 3 else sdd_workspace.workspace_dir() / ("task-%s-brief.md" % n)
    text = extract_task(plan.read_text(encoding="utf-8"), n)
    out.write_text(text, encoding="utf-8")
    if not text:
        print("task %s not found in %s (no heading matching 'Task %s')" % (n, plan, n),
              file=sys.stderr)
        return 3
    print("wrote %s: %d lines" % (out, len(text.splitlines())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
