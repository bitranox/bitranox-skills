#!/usr/bin/env python3
"""PreToolUse(Bash|PowerShell) guard: refuse a `||` verdict after a tool whose failure has two causes.

Registered for both shells with its siblings; a PowerShell call is passed unjudged, since the
grep/diff exit-code contract below is a POSIX one.

grep, rg, diff and cmp report two different things through a non-zero exit:

    grep:  0 match      1 no match      2+ could not look (missing file, bad regex, bad option)
    diff:  0 same       1 different     2+ trouble (missing file, unreadable, bad option)
    cmp:   0 same       1 different     2+ trouble

`||` fires on BOTH. So a fallback that names the answer

    grep -inE 'co-authored|claude' msg.txt -P || echo "no attribution"
    diff -q a.conf b.conf 2>/dev/null || echo "different"

prints its verdict whenever the tool could not look at all - and the verdict it prints is
exactly the reassuring one ("clean", "no hits", "not found") or the alarming one ("different"),
never "I did not check". The first line above is real: `-i -E` plus `-P` makes grep exit 2
("conflicting matchers"), the fallback printed "no attribution", and the commit went out
unexamined. The same shape recurred three times in one fact's history before this guard
(mem:feedback-never-attach-a-diagnosis-to-a-bare-a-non-zero-exit-is-often-the-finding).

It is a REFUSAL, not a nudge, at the user's request after the third recurrence: a nudge sits
beside output that already reads as an answer, and the answer is what gets acted on.

What is refused, and only this:
  - a grep-family program (grep, egrep, fgrep, zgrep, rg, git grep), diff, cmp or git diff, as
    the PROGRAM of its statement or pipeline element (a launcher such as `timeout 5`, `env -u X`
    or `LC_ALL=C` in front is skipped; `which grep` and `cat grep.txt` are not grep runs);
  - followed in the same pipeline element by `|| echo|printf <label>`, optionally through an
    intermediate `&& echo ...` (`grep -q X f && echo found || echo "not found"`: the `||` arm
    still runs on rc 2);
  - where the label names a verdict: clean, no ..., none, nothing, not found, missing, absent,
    identical, same, different, differs, unchanged, empty, ok.

What passes:
  - a label that names its own uncertainty ("no match or grep error", "rc=$?", "grep failed");
  - `|| echo 0` and other counts (the count shape is `nudge-detector-footguns`' business);
  - `|| true`, `|| :`, `|| exit 1`, and a fallback that is not an echo;
  - a pipeline that does not END in the tool (`grep X f | head || ...` is head's status);
  - the tool under `!` (the negation inverts what `||` means);
  - text that is data: a quoted string, an echo operand, a comment, a heredoc body. A command
    string handed to another shell (`ssh host '...'`, `bash -c '...'`) is quoted and therefore
    NOT inspected - a deliberate miss, since this guard blocks and a quoted span is far more
    often documentation than code. `$(...)` command substitution IS inspected: it runs here.

The refusal names a command form this guard passes (pinned by a test that feeds it back): read
the exit code once and branch on it, so rc 2 cannot borrow rc 1's sentence.

Corpus replay before shipping (guard_replay.py, 2026-11-06, 205,309 recorded Bash calls): 224
firings, 0.109%. Every firing is the shape by construction, so the question was how many LIED:
joined to their recorded output, 2 printed the verdict beside grep's own error (the motivating
`-iE ... -P` conflict, and `grep -q . && echo OK || echo NO` over a missing file); 22 more sent
the tool's stderr to /dev/null first, so an error could not have shown. A random 35 of the 224
read by hand were all genuine instances, none a quoting or parsing false positive. Per program:
grep 178, git diff/grep 20, cmp 15, diff 11. Grep reading a PIPE stays in scope on purpose: the
motivating case read a pipe, and an option or pattern error needs no file.

Pure standard library. Reads the PreToolUse event JSON on stdin. Exit 2 blocks the call and
shows stderr to the model; every other path, including any internal error, exits 0, so a broken
guard never wedges a turn.
"""

import json
import re
import sys

import shell_text
from shell_text import blank_heredoc_bodies, mask_data_regions

# Where a program word can start: the start of the text, after a list or pipe separator, inside a
# subshell or group, or after a compound-command keyword. `!` is absent on purpose (see above).
_START = r"(?:^|(?<=[;&|(\n{])|(?<=\bthen)|(?<=\bdo)|(?<=\belse)|(?<=\belif)|(?<=\btime))"

# Launchers that leave the next word the real program. A leading `NAME=value` is an assignment
# prefix for the same reason.
_LAUNCHER = (
    r"(?:(?:sudo|nice|command|nohup"
    r"|stdbuf(?:\s+-\S+)+"
    r"|timeout(?:\s+-\S+)*\s+\S+"
    r"|env(?:\s+-u\s+\S+|\s+-\S+|\s+[A-Za-z_]\w*=\S*)*"
    r"|[A-Za-z_]\w*=\S*)\s+)*"
)

_PROGRAM = (
    r"(?P<prog>(?:\S*/)?(?:[efz]?grep|rg|diff|cmp)"
    r"|git(?:\s+-C\s+\S+|\s+-c\s+\S+|\s+--no-pager)*\s+(?:grep|diff))(?=[\s)]|$)"
)

# One pipeline element's worth of text: no list separator, no pipe, no newline. `2>&1`, `>&2`
# and `&>` are redirections, not separators, so they are allowed through.
_ELEMENT = r"(?:[^;&|\n]|[0-9]?>&[0-9-]?|&>)*?"

_PATTERN = re.compile(
    _START + r"\s*" + _LAUNCHER + _PROGRAM
    + r"(?P<args>" + _ELEMENT + r")"
    + r"(?:&&\s*(?:echo|printf)\b" + _ELEMENT + r")?"
    + r"(?P<op>\|\|)\s*[{(]?\s*(?P<echo>echo|printf)\b(?P<label>[^;&|\n)}]*)"
)

_VERDICT = re.compile(
    r"\b(?:clean|no|none|nothing|not[\s_-]?found|missing|absent|identical|same|different|differs?"
    r"|unchanged|empty|ok|okay)\b",
    re.IGNORECASE,
)

# A label that already says it may not have looked is honest; let it through.
_HONEST = re.compile(
    r"\b(?:err(?:or)?s?|fail(?:ed|ure|s)?|rc|exit|status|unreadable|cannot|can't|couldn't|"
    r"unknown|unverified|or\s+(?:an?\s+)?(?:error|problem))\b|\$\?|\$\{?rc\b",
    re.IGNORECASE,
)

_MAX_DEPTH = 3


def _substitutions(text: str) -> list[str]:
    """The inner text of each top-level `$(...)` in `text`, quote-aware, arithmetic excluded."""
    inner: list[str] = []
    i, size = 0, len(text)
    while i < size:
        ch = text[i]
        if ch == "'":
            close = text.find("'", i + 1)
            i = size if close < 0 else close + 1
            continue
        if ch == "\\":
            i += 2
            continue
        if text.startswith("$(", i) and not text.startswith("$((", i):
            depth, j, quote = 1, i + 2, None
            while j < size and depth:
                c = text[j]
                if quote:
                    if c == quote:
                        quote = None
                    elif c == "\\" and quote == '"':
                        j += 1
                elif c in "'\"":
                    quote = c
                elif c == "(":
                    depth += 1
                elif c == ")":
                    depth -= 1
                j += 1
            inner.append(text[i + 2:j - 1] if depth == 0 else text[i + 2:])
            i = j
            continue
        i += 1
    return inner


def _verdict_label(raw_label: str) -> bool:
    """True when an echo's operand words name a verdict and do not admit doubt."""
    words = raw_label.strip()
    if not words or not _VERDICT.search(words):
        return False
    return not _HONEST.search(words)


def _scan(text: str, depth: int = 0) -> str | None:
    masked = mask_data_regions(text, tool_name="Bash")
    for match in _PATTERN.finditer(masked):
        label = text[match.start("label"):match.end("label")]
        if _verdict_label(label):
            return text[match.start("prog"):match.end("label")].strip()
    if depth >= _MAX_DEPTH:
        return None
    for inner in _substitutions(text):
        found = _scan(inner, depth + 1)
        if found is not None:
            return found
    return None


def refused_shape(command: str, tool_name: str = "Bash") -> str | None:
    """The offending `<tool> ... || echo <verdict>` text, or None when the command passes."""
    if tool_name != "Bash" or "||" not in (command or ""):
        return None
    return _scan(blank_heredoc_bodies(command))


def _message(shape: str) -> str:
    prog = shape.split()[0].rsplit("/", 1)[-1]
    is_diff = prog in ("diff", "cmp") or shape.startswith("git") and " diff" in shape[:40]
    if is_diff:
        fix = ('diff -q A B; rc=$?; [ $rc -eq 0 ] && echo identical; [ $rc -eq 1 ] && echo different; '
               '[ $rc -gt 1 ] && echo "diff FAILED rc=$rc"')
        codes = "0 same, 1 different, 2+ trouble (missing or unreadable file, bad option)"
    else:
        fix = ('grep -n PAT FILE; rc=$?; [ $rc -eq 1 ] && echo "no match"; '
               '[ $rc -gt 1 ] && echo "grep FAILED rc=$rc"')
        codes = "0 match, 1 no match, 2+ could not look (missing file, bad regex, conflicting options)"
    return (
        f"Refused: `{shape[:120]}` prints its verdict on ANY non-zero exit. {prog} exits {codes}, "
        "and `||` fires on both, so the verdict also prints when the tool never looked - measured: "
        "`grep -i -E ... -P` exited 2 and its `|| echo` printed a clean all-clear.\n"
        f"Read the exit code once and branch on it, e.g.:\n    {fix}\n"
        "or say the doubt in the label (`|| echo \"no match or error (rc=$?)\"`)."
    )


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    try:
        command = str(event.get("tool_input", {}).get("command", ""))
        shape = refused_shape(command, str(event.get("tool_name") or "Bash"))
    except Exception:  # noqa: BLE001 - a broken guard must never wedge a turn
        return 0
    if shape is None:
        return 0
    return shell_text.refuse(_message(shape))


if __name__ == "__main__":
    sys.exit(main())
