#!/usr/bin/env python3
"""PreToolUse(Bash|PowerShell) guard: refuse a call that RUNS a Python program splicing a file
between two found anchors - `s[:a] + new + s[b:]` after two `.index()` / `.find()` calls, written
back. Registered beside the other shell guards; a PowerShell call is passed through unjudged.

Why a refusal and not only the nudge: `toolbox-nudge.py` already pointed at `anchor_edit` on this
shape, and the mistake recurred with the nudge in place - an end marker that also occurred inside
a deeper-indented line matched early, and the rest of the old function stayed in the file as dead
code that still parsed. Every failure of the shape is silent: `.find` returns -1 on a miss, which
slices from the END of the string, and a wrong match deletes or keeps a region with exit 0.
`anchor_edit.py replace-span` refuses each of those: an absent or repeated start, an end that is
not unique after the start, a region bigger than the stated line count, a named survivor removed.

What is refused: a heredoc body that a Python interpreter reads as its program (`python3 - <<EOF`,
`uv run python - <<EOF`), when the parsed program cuts one expression at a head and a different
tail bound inside a `+` chain, calls find/index twice and writes. The detector is
`splice_span.unchecked_splices`, shared with the nudge's `SPAN_SHAPE`.

The exemption (user decision 2026-10-30): a program that checks EVERY find/index anchor it uses
is unique - `assert s.count(A) == 1`, or `if s.count(A) != 1: raise ...` - is let through,
because that check is exactly what catches a repeated end marker. A partly checked program is
refused, and an anchor that cannot be paired with its count (an f-string, a value built in a
loop) counts as unchecked. Replayed over the transcript corpus: 29 of 1,287 splices checked
every anchor this way.

What is NOT refused, and why the nudge stays for it: a script AUTHORED through Write/Edit or
`cat > f.py <<EOF` (that is how a tool which legitimately splices, `anchor_edit.py` itself among
them, gets written), an insert at one anchor (`t[:i] + x + t[i:]`, anchor_edit `insert`), a splice
that only appears in a string or an `assert`, a `python -c` one-liner (measured twice in the
transcript corpus, neither an edit), and a program that does not parse. The nudge speaks on all
of the authored ones.

Exit 2 through `shell_text.refuse`, which adds the whole-call footer; every other path, any error
included, exits 0. Pure standard library.
"""

import json
import re
import sys
from pathlib import Path

import shell_text
import splice_span

__all__ = ["anchor_edit_path", "assess", "main"]


def anchor_edit_path():
    """The shipped `anchor_edit.py`, resolved relative to this hook so it names the running
    plugin version rather than a path with a version in it."""
    return (Path(__file__).resolve().parent.parent / "skills" / "compuse-toolbox" / "scripts"
            / "anchor_edit.py")


# A conflict marker run (seven `<` or `>`). A program cutting between those is resolving merge
# hunks, which conflict_resolve does by rule per hunk - 69 of the 1,278 replayed refusals were that.
_CONFLICT_MARKER = re.compile(r"<{7}|>{7}")


def _conflict_pointer():
    tool = anchor_edit_path().with_name("conflict_resolve.py")
    return ("\nThis program resolves merge-conflict hunks: `uv run %s FILE --list` shows them, then "
            "`--hunk N=ours|theirs|both|base|file:PATH` (or `--all RULE`) resolves each by rule and "
            "refuses what it cannot place." % tool)


def _message():
    tool = anchor_edit_path()
    return (
        "INDEX-SPLICE GUARD: this call runs a Python program that splices a file between two "
        "found anchors (`s[:a] + new + s[b:]` after `.index()`/`.find()`). Every way that goes "
        "wrong is silent: a `.find` miss returns -1 and slices from the END, and an end marker "
        "that also occurs in a deeper-indented line matches early and leaves the rest of the old "
        "region behind as dead code that still parses.\n"
        "Do the edit with anchor_edit, which refuses an absent or repeated start, an end that is "
        "not unique after the start, a region bigger than you state, and a named survivor that "
        "got removed. Put the exact start and end marker text and the new text in files, then:\n"
        f"  uv run {tool} replace-span /abs/path/to/file.py --start-file start.txt "
        "--end-file end.txt --new-file new.txt --expect-removed-lines 12 "
        "--must-keep 'def survivor('\n"
        "The region runs from the start marker up to (not including) the end marker; add "
        "`--dry-run` to see the line delta first. An insert at one anchor is `insert F "
        "--anchor-file a.txt --new-file n.txt --before|--after`, and many exact replacements "
        "across files are `batch --spec edits.json`.\n"
        "Or keep the script and check EVERY anchor it finds is unique before cutting "
        "(`assert s.count(START) == 1 and s.count(END) == 1`, or `if s.count(X) != 1: raise "
        "...`): a program that checks them all is let through."
    )


def assess(command, tool_name="Bash"):
    """The refusal message for `command`, or None when it may run. PURE.

    `tool_name` other than Bash is never judged: a PowerShell here-string is not a Python stdin
    program, and the detector reads Bash heredocs.

    Examples:
        >>> assess("git status") is None
        True
    """
    if tool_name != "Bash" or not command:
        return None
    spliced = splice_span.unchecked_splices(command)
    if not spliced:
        return None
    hunks = any(_CONFLICT_MARKER.search(program) for program in spliced)
    return _message() + (_conflict_pointer() if hunks else "")


def main():
    try:
        event = json.load(sys.stdin)
    except ValueError:                                   # no or invalid stdin: nothing to judge
        return 0
    if not isinstance(event, dict):
        return 0
    command = (event.get("tool_input") or {}).get("command") or ""
    message = assess(command, event.get("tool_name") or "")
    return shell_text.refuse(message) if message else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:                                    # a broken guard must never wedge a turn
        sys.exit(0)
