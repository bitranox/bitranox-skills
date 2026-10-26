#!/usr/bin/env python3
"""PostToolUse(Write|Edit|MultiEdit) hook: report each non-ASCII character a write INTRODUCED
into a file that tell-sweep does not sweep (code, config, data - everything but prose).

The slip it catches: a backslash-u escape typed into a Write/Edit tool parameter is decoded by
JSON into the LITERAL character before the tool runs, so a Python test that was meant to hold the
six ASCII characters of an escape silently holds an Arabic-Indic digit instead. tell-sweep covers
prose files only and deliberately skips code, which is exactly where this happens.

What counts as introduced:
  - Edit: characters in `new_string` that are not in `old_string`, and not in the rest of the
    file either (the file with every occurrence of `new_string` cut out), so an umlaut added to a
    German README is quiet while a new Arabic-Indic digit in the same file still reports.
  - MultiEdit: the same, per edit.
  - Write: characters in `content` that were not in the file's previous text. The previous text is
    the tool response's `originalFile` when it carries one (the exact bytes the call replaced),
    else the git HEAD blob when the file is tracked; a new or untracked file has none, so every
    non-ASCII character in it counts.
Prose files are left to tell-sweep through the one shared decision, `tell_chars.is_prose_path`.

The report names POSITION and CODEPOINT, never the line's text (`line 31, col 64: U+0663
ARABIC-INDIC DIGIT THREE`): it stays pure ASCII, and it does not echo file content back. Columns
count characters, not bytes. An Edit whose `new_string` is no longer in the file is reported
against `new_string` itself.

PRICE, measured 2026-10-26 by replaying the local transcript corpus (5454 .jsonl, rglob) through
`findings`: 24066 Write/Edit/MultiEdit tool_use calls deduped by id, 636 dropped because their
tool_result was an error, 9471 on prose files (tell-sweep's), 13959 scanned. A Write's previous
text came from the recorded originalFile; no HEAD lookup was possible in a replay.
  - Without the rest-of-file rule for Edits: 244 firings (1.7% of scanned calls), 232 distinct
    files, 220 of them .py. 14 introduced a non-ASCII digit. A spread sample of 20, judged by hand
    from the call's own text: 7 slips (an escape decoded to the literal: Arabic-Indic digits, BOM,
    ZWSP, soft hyphen, U+2028/U+2029, RLO, U+FFFD in test data), 10 intended (German UI strings
    and regexes, deliberate glyphs, visible CJK test data), 3 undecidable. Precision 35-50%.
  - With it: 237 firings, 229 files. The replay can apply it only to the 1/3 of Edits whose result
    recorded originalFile; the hook applies it to every Edit, so the live drop is larger. The 7
    dropped: 6 intended (umlauts in German .rst docs, U+2713 in a test module already using it),
    1 a capital O-umlaut in a test that a later call removed again.
  - Not adopted: skipping Latin letters with diacritics (U+00C0-U+024F) would drop 73 more
    firings, 1 of them later removed by a fix, but also an escape-typed accented letter in test
    data, the shape this hook exists for; a false firing costs one ignored notice, nothing blocks.

Pure standard library. Reads the PostToolUse event JSON on stdin. Exit 2 shows the list to the
model (the write already happened, so nothing is blocked); every other path, any exception
included, exits 0, so a broken guard never wedges a turn. This source stays pure ASCII.
"""
import json
import os
import subprocess
import sys
import unicodedata
from collections import namedtuple

import tell_chars

_MAX_LISTED = 20
_MAX_READ = 8 * 1024 * 1024
_GIT_TIMEOUT = 5

# where: "" for a position in the file, "new_string" when the edit's text was not found in it.
Finding = namedtuple("Finding", "line col char where")


def _non_ascii(text):
    return {ch for ch in text if ord(ch) > 127}


def _positions(text, chars):
    """(line, col, char) for every occurrence of a char in `chars`, 1-based, columns in characters."""
    line, col = 1, 0
    for ch in text:
        if ch == "\n":
            line, col = line + 1, 0
            continue
        col += 1
        if ch in chars:
            yield line, col, ch


def _anchor(current, new):
    """(line, col) in `current` where `new` starts, or None when it is not there."""
    at = current.find(new) if current and new else -1
    if at < 0:
        return None
    line = current.count("\n", 0, at) + 1
    return line, at - (current.rfind("\n", 0, at) + 1) + 1


def _edit_findings(old, new, current):
    if not isinstance(new, str) or not new:
        return []
    chars = _non_ascii(new) - set(old if isinstance(old, str) else "")
    anchor = _anchor(current, new)
    if chars and anchor is not None:
        # A character the rest of the file already uses is the file's own vocabulary (a German
        # README, a test module that already holds U+2713), not a decoded escape. Every
        # occurrence of new_string is cut, so a replace_all cannot hide its own characters.
        chars -= set(current.replace(new, ""))
    if not chars:
        return []
    found = []
    for line, col, ch in _positions(new, chars):
        if anchor is None:
            found.append(Finding(line, col, ch, "new_string"))
        elif line == 1:
            found.append(Finding(anchor[0], anchor[1] + col - 1, ch, ""))
        else:
            found.append(Finding(anchor[0] + line - 1, col, ch, ""))
    return found


def findings(tool_name, tool_input, previous=None, current=None):
    """The non-ASCII characters this call introduced, as `Finding`s in reading order.

    `previous` is the file's text before a Write (None: there was none); `current` is the file's
    text now, used only to place an Edit's `new_string` in the file.
    """
    if tool_name == "Write":
        content = tool_input.get("content")
        if not isinstance(content, str):
            return []
        chars = _non_ascii(content) - set(previous or "")
        return [Finding(line, col, ch, "") for line, col, ch in _positions(content, chars)]
    if tool_name == "Edit":
        return _edit_findings(tool_input.get("old_string"), tool_input.get("new_string"), current)
    if tool_name == "MultiEdit":
        edits = tool_input.get("edits")
        if not isinstance(edits, list):
            return []
        found = []
        for edit in edits:
            if isinstance(edit, dict):
                found += _edit_findings(edit.get("old_string"), edit.get("new_string"), current)
        return found
    return []


def _head_blob(path):
    """The file's text at git HEAD, or None (untracked, not a repo, git missing or slow)."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env["LC_ALL"] = "C"
    directory, name = os.path.split(os.path.abspath(path))
    try:
        proc = subprocess.run(["git", "-C", directory, "show", "HEAD:./" + name], env=env,
                              capture_output=True, timeout=_GIT_TIMEOUT)
    except Exception:
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.decode("utf-8", errors="replace")


def _previous_text(event, path):
    response = event.get("tool_response")
    if isinstance(response, dict) and isinstance(response.get("originalFile"), str):
        return response["originalFile"]
    return _head_blob(path)


def _read(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read(_MAX_READ)
    except Exception:
        return None


def _name(ch):
    name = unicodedata.name(ch, None)
    return name if name else "(no name, category %s)" % unicodedata.category(ch)


def _report_line(found):
    where = "new_string line" if found.where else "line"
    return "%s %d, col %d: U+%04X %s" % (where, found.line, found.col, ord(found.char), _name(found.char))


def _capped(lines):
    """The first `_MAX_LISTED` lines, plus a count of the rest: a list that stops silently reads
    as complete, and the model meets a second batch it had no reason to expect."""
    shown = lines[:_MAX_LISTED]
    if len(lines) > _MAX_LISTED:
        shown = shown + ["... and %d more" % (len(lines) - _MAX_LISTED)]
    return "\n".join(shown) + "\n"


def _report(path, tool_name, found):
    first = found[0].char
    return (
        "Non-ASCII character(s) introduced into %s by this %s call (it already ran):\n" % (path, tool_name)
        + _capped([_report_line(f) for f in found])
        + "If you meant an escape: a backslash-u escape typed into a tool parameter is decoded to the "
        "literal character before the tool runs. Write it as chr(0x%04X) or an escaped literal "
        "instead, so the file stays ASCII. If the character is intended, ignore this.\n" % ord(first)
    )


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:
        return 0
    if not isinstance(event, dict):
        return 0
    tool_name = event.get("tool_name")
    tool_input = event.get("tool_input")
    if not isinstance(tool_input, dict):
        return 0
    path = tool_input.get("file_path")
    if not isinstance(path, str) or not path or tell_chars.is_prose_path(path):
        return 0
    previous = current = None
    if tool_name == "Write":
        previous = _previous_text(event, path)
    else:
        current = _read(path)
    found = findings(tool_name, tool_input, previous=previous, current=current)
    if not found:
        return 0
    sys.stderr.write(_report(path, tool_name, found))
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
