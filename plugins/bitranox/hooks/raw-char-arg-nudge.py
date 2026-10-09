#!/usr/bin/env python3
"""PreToolUse nudge: a raw control or invisible character in what a tool is about to write.

Tool arguments travel as JSON, and JSON decodes a backslash-u escape itself. So an escape typed
into an argument meaning Python source text - a test value, a docstring, a commit message, a
subagent's brief - arrives as the character it names. For a printable character that is a lint
finding at worst. For an invisible one it is worse: a RIGHT-TO-LEFT OVERRIDE (U+202E) written
into test source is a trojan-source hazard, and nothing local shows it, because the tool call
LOOKS like it carried the escape.

Measured: three times in one session (a heredoc of pytest parameters, a Python edit script, a
commit message file) after the same trap had been recorded twice before as a memory rule. Only
the backslash-u form decodes - an x-escape and the eight-digit form arrived as typed in the same
heredoc - so the habit "escapes are safe in a script" holds for some escapes and not others.

This hook reads the DECODED argument, so it sees exactly the character that will land. It names
each one by code point and Unicode name and says how to write the escape instead. It checks only
what a tool WRITES: Write content, Edit/MultiEdit new_string, NotebookEdit new_source, a shell
command, a subagent prompt. An Edit's old_string is left alone, since matching a raw character
already in a file is how you remove it.

Flagged: C0 controls except tab, line feed and carriage return; DEL and the C1 controls; Unicode
format characters (bidi overrides and isolates, zero-width characters, the soft hyphen, BOM, tag
characters); the line and paragraph separators. Printable non-ASCII (umlauts, CJK, emoji) is
never flagged.

NON-BLOCKING: emits additionalContext and exits 0, because a raw character can be meant (a file
that must hold a BOM). Fail-open on any error. ASCII only.
"""
from __future__ import annotations

import json
import sys
import unicodedata

#: The argument fields each tool WRITES. Anything else (paths, old_string, descriptions) is not
#: content that lands somewhere.
_FIELDS = {
    "Write": ("content",),
    "Edit": ("new_string",),
    "NotebookEdit": ("new_source",),
    "Bash": ("command",),
    "PowerShell": ("command",),
    "Task": ("prompt",),
    "Agent": ("prompt",),
}
_FLAGGED_CATEGORIES = frozenset({"Cf", "Zl", "Zp"})
_ALLOWED_CONTROLS = frozenset("\t\n\r")

_ADVICE = (
    "If you meant the ESCAPE text (Python source, a test value, a doc), JSON decoded it on the way: "
    "build the backslash in a script instead - `B = chr(92)`, then `B + 'u202e'`, or "
    "`chr(0x202E)` for the character itself - so no backslash-u plus hex ever appears in a tool "
    "argument. Check the file afterwards with `LC_ALL=C grep -nP '[^\\x00-\\x7F]' <file>`. If the "
    "raw character is meant (a BOM a format requires), go ahead."
)


def _flagged(character: str) -> bool:
    category = unicodedata.category(character)
    if category == "Cc":
        return character not in _ALLOWED_CONTROLS
    return category in _FLAGGED_CATEGORIES


def _label(character: str) -> str:
    code = ord(character)
    name = unicodedata.name(character, "") or ("control character" if code < 0xA0 else "unnamed")
    return f"U+{code:04X} {name}"


def _texts(tool_name: str, tool_input: object) -> list[tuple[str, str]]:
    """(field, text) for every argument this tool writes."""
    if not isinstance(tool_input, dict):
        return []
    if tool_name == "MultiEdit":
        edits = tool_input.get("edits")
        if not isinstance(edits, list):
            return []
        return [(f"edits[{i}].new_string", edit["new_string"]) for i, edit in enumerate(edits)
                if isinstance(edit, dict) and isinstance(edit.get("new_string"), str)]
    return [(field, tool_input[field]) for field in _FIELDS.get(tool_name, ())
            if isinstance(tool_input.get(field), str)]


def notice(tool_name: str, tool_input: object) -> str | None:
    """The nudge text when an argument this tool writes holds a flagged character, else None."""
    reports = []
    for field, text in _texts(tool_name, tool_input):
        counts: dict[str, int] = {}
        for character in text:
            if _flagged(character):
                counts[character] = counts.get(character, 0) + 1
        if counts:
            found = ", ".join(f"{_label(c)}" + (f" x{n}" if n > 1 else "") for c, n in counts.items())
            reports.append(f"{field}: {found}")
    if not reports:
        return None
    return (f"RAW INVISIBLE OR CONTROL CHARACTER in this {tool_name} call - " + "; ".join(reports)
            + ". " + _ADVICE)


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:  # noqa: BLE001 - no/invalid stdin: do nothing
        return 0
    if not isinstance(event, dict) or not isinstance(event.get("tool_name"), str):
        return 0
    message = notice(event["tool_name"], event.get("tool_input"))
    if message:
        sys.stdout.write(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": message,
        }}) + "\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - a broken hook must never wedge a turn
        sys.exit(0)
