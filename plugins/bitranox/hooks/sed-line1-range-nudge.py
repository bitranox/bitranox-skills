#!/usr/bin/env python3
"""PreToolUse(Bash) nudge: `sed '1,/re/d'` deletes one block more than you meant.

sed's `1,/re/` range starts hunting for the END pattern at line 2. So on a file whose line 1 is the
opening delimiter, the range already closes on the CLOSING delimiter - the frame is gone in ONE
pass, and a second chained sed then runs from the new line 1 to EOF and takes the payload with it.

Measured 2026-08-02: two curated memory bodies stripped this way lost their whole content (33 -> 15
and 28 -> 13 lines). Both still parsed and still rendered as valid entries, so the loss was
invisible until the line counts were compared against the originals. That silence is why this is
worth a hook rather than another line of prose.

NUDGE, not a block: `1,/re/d` has legitimate uses, and a guard that false-fires on a correct command
teaches the reader to ignore the channel. It emits `additionalContext` and exits 0.

Only the DELETE form is flagged. `1,/re/p` shows you what it selected, so an off-by-one is visible
rather than silent. An exact `1,5d` has no regex end and cannot overshoot.

The scan runs with heredoc bodies stripped: a body is DATA, and a guard that reads it fires on prose
documenting the very footgun it guards.
"""
from __future__ import annotations

import json
import re
import sys

from shell_text import is_shell_tool, strip_heredoc_bodies

# `sed`/`gsed` at a command position, then a 1,/regex/ range ending in `d`. The end pattern is
# matched non-greedily up to an unescaped `/`, so `1,/^---$/d` and `1,/^BEGIN$/d` both hit while
# `1,5d` (no regex) and `2,/re/d` (not anchored at line 1) do not.
_TRAP = re.compile(
    r"""(?:^|[;&|]|\s)g?sed\b(?:\s+-[^\s]+)*\s*['"]?\s*1\s*,\s*/(?P<end>(?:\\.|[^/\\])+)/\s*d""",
    re.M,
)


def notice(command):
    """The warning text when this command uses the trap range, else None."""
    if not command or not isinstance(command, str):
        return None
    try:
        # Heredoc bodies only. NOT blank_unexpanded_text: a real sed range is itself written
        # single-quoted (`sed -i '1,/^---$/d'`), so blanking single quotes deletes exactly what
        # this nudge looks for - measured, it took four tests down.
        #
        # KNOWN AND NOT FIXED: `echo 'never use sed 1,/^---$/d ...'` still fires. At this level a
        # single-quoted argument to echo is indistinguishable from the sed script that runs;
        # telling them apart needs the ENCLOSING command, not the quote.
        text = strip_heredoc_bodies(command)
    except Exception:  # noqa: BLE001 - a nudge must never wedge a turn
        return None
    match = _TRAP.search(text)
    if not match:
        return None
    return (
        "`sed '1,/%s/d'` deletes ONE BLOCK MORE than you mean: sed's `1,/re/` range starts hunting "
        "for the end pattern at LINE 2, so when line 1 is the opening delimiter the range closes on "
        "the CLOSING one and the frame is already gone in a single pass. Chaining a second sed then "
        "runs to EOF and takes the payload with it - measured as two memory bodies truncated 33->15 "
        "and 28->13 lines, both still parsing so the loss was invisible. To unwrap a YAML frame use "
        "Python: `raw.split(\"\\n---\\n\", 1)[1]`. If you really want the shell form, verify the "
        "output size against the input before using it."
        % match.group("end")
    )


def main(raw=None) -> int:
    """Read the hook event, emit additionalContext when the shape matches. Always exits 0."""
    try:
        payload = json.loads(raw if raw is not None else sys.stdin.read() or "{}")
    except (ValueError, TypeError):
        return 0
    if not isinstance(payload, dict) or not is_shell_tool(payload.get("tool_name")):
        return 0
    tool_input = payload.get("tool_input")
    command = tool_input.get("command") if isinstance(tool_input, dict) else None
    try:
        text = notice(command)
    except Exception:  # noqa: BLE001
        return 0
    if not text:
        return 0
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                             "additionalContext": text}}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
