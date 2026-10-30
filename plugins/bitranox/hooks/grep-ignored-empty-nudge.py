#!/usr/bin/env python3
"""PostToolUse(Bash|PowerShell|Monitor) nudge: a recursive grep came back EMPTY under Claude Code's grep shim.

In a Claude Code Bash session `grep` is a shell FUNCTION, not the binary: it runs Claude Code's
bundled ugrep with `--ignore-files`, so every gitignored file is skipped. A recursive search over
several repos printed nothing and exited as a plain "no match" while `bash -c` with the same
arguments - a fresh shell without the function - found seven hits. Nothing in the output tells
the two apart, so the miss is silent.

When it fires: the Bash call's stdout is empty (whitespace only counts as empty), and one of its
statements runs the WORD `grep` with a recursive option (`-r`, `-R`, a cluster holding either,
`--recursive`, `--dereference-recursive`, `-d recurse`, `--directories=recurse`). A chain or a
pipeline counts as long as the whole call printed nothing: `cd x && grep -rn p .` and
`grep -rn p . | head` both qualify, `grep -rn p . || echo none` does not, because it printed.
A grep inside `$(...)` or backticks counts as well: the function runs there too, and
`if [ -n "$(grep -rl p .)" ]; then echo found; fi` printing nothing is the same silent miss.

What stays silent, and why:
- anything that runs the BINARY rather than the function sees ignored files already: `bash -c`,
  `sh -c`, `command grep`, a path such as `/usr/bin/grep`, and every launcher (`sudo`, `timeout`,
  `env`, `nice`, `xargs`, `find -exec`). `grep_all` runs as `uv run .../grep_all.py`.
- arguments the shim itself hands to the real grep (`-z`/`-Z` in any short cluster, `--null`,
  `--null-data`, `--config`, `--pager`, ...), mirrored from the shim Claude Code 2.1.314 defines.
- `-q`/`--quiet`/`--silent` and `-L`/`--files-without-match`: their empty output says nothing
  about which files held a match.
- interrupted or backgrounded calls, whose stdout is not the search's result.
- PowerShell and Monitor calls: no shim there. The matcher names them only because hooks.json keeps
  one PostToolUse group per matcher and every Bash matcher is paired with PowerShell.

The payload this reads was measured with a probe hook on Claude Code 2.1.314: a PostToolUse(Bash)
hook receives `tool_response` = {stdout, stderr, interrupted, isImage, noOutputExpected}, plus
`returnCodeInterpretation: "No matches found"` when grep exited 1. The exit status itself is not
delivered, and a grep exiting 2 (a missing path) fires PostToolUseFailure, not this event.

Nothing in the payload says whether `grep` IS the shim in this shell, so the text states the shim
premise conditionally and names the check (`declare -F grep`) rather than asserting it.

A genuinely empty search fires too; the text says what to do only if completeness matters. NUDGE,
never a block: the command already ran. It emits `additionalContext`, which Claude Code places next
to the tool result, and always exits 0.
"""

import fnmatch
import json
import sys

from shell_text import argv_for_match, iter_segments, strip_heredoc_bodies

_PROGRAM = "grep"
# Words that may stand before the program of a statement and still let the shell FUNCTION run:
# grouping, negation, a condition keyword, the `time` keyword. A launcher (`sudo`, `env`) is not
# here on purpose - it execs the binary, which is not the shim.
_LEADING_SYNTAX = frozenset({"(", "{", "!", "if", "while", "until", "do", "then", "else", "elif",
                             "time"})
# grep's short options whose VALUE follows: the rest of the cluster, or the next word.
_SHORT_WITH_VALUE = frozenset("efmABCdD")
# grep's long options that take their value as the NEXT word when written without `=`.
_LONG_WITH_VALUE = frozenset({
    "--regexp", "--file", "--max-count", "--after-context", "--before-context", "--context",
    "--directories", "--devices", "--include", "--exclude", "--exclude-from", "--exclude-dir",
    "--label", "--binary-files", "--group-separator",
})
_RECURSIVE_LONG = frozenset({"--recursive", "--dereference-recursive"})
_EMPTY_IS_UNINFORMATIVE_LONG = frozenset({"--quiet", "--silent", "--files-without-match"})
# The `case` patterns of the shim's own pass-through branch: any argument matching one makes it
# run `command grep`, which reads gitignored files like any other.
_SHIM_PASSTHROUGH = ("-*-filter*", "-*-pager*", "-*-view*", "-*-format-open*", "-*-config*",
                     "---*", "-@*", "-*-save-config*", "-[Zz]*", "-[!-]*[Zz]*", "--null",
                     "--null-data")

# Conditional on purpose: the payload cannot show whether grep is the shim in this shell, so the
# text names the check instead of asserting the premise.
MESSAGE = (
    "`%s` returned no output. If grep is Claude Code's shim (check: declare -F grep), it skips "
    "gitignored files; if this search must be complete, re-run it with bash -c grep or "
    "compuse-toolbox grep_all (an empty result can also be genuine)."
)


def _program_at(words):
    """Index of the statement's program word past assignments and leading syntax, else None."""
    at = 0
    while at < len(words):
        word = words[at]
        if word in _LEADING_SYNTAX or _is_assignment(word):
            at += 1
        elif word.startswith("(") and len(word) > 1:
            words[at] = word.lstrip("(")
        else:
            return at
    return None


def _is_assignment(word):
    name, sep, _value = word.partition("=")
    return bool(sep) and name.replace("_", "a").isalnum() and not name[:1].isdigit()


def _short_flags(word):
    """(flags, value pending) for a short cluster such as `-rni` or `-A3`."""
    flags = set()
    for index, char in enumerate(word[1:], start=1):
        if char in _SHORT_WITH_VALUE:
            flags.add(char)
            return flags, index == len(word) - 1, word[index + 1:]
        flags.add(char)
    return flags, False, ""


def _option_facts(args):
    """(recursive, empty output is uninformative) from grep's arguments. PURE."""
    recursive, uninformative, skip_next, directories_value = False, False, False, False
    for word in args:
        if skip_next:
            recursive |= directories_value and word == "recurse"
            skip_next = directories_value = False
            continue
        if word == "--":
            break
        if word.startswith("--"):
            name, sep, value = word.partition("=")
            recursive |= name in _RECURSIVE_LONG or (name == "--directories" and value == "recurse")
            uninformative |= name in _EMPTY_IS_UNINFORMATIVE_LONG
            skip_next = not sep and name in _LONG_WITH_VALUE
            directories_value = skip_next and name == "--directories"
        elif word.startswith("-") and len(word) > 1:
            flags, pending, value = _short_flags(word)
            recursive |= bool(flags & {"r", "R"}) or ("d" in flags and value == "recurse")
            uninformative |= bool(flags & {"q", "L"})
            skip_next, directories_value = pending, pending and "d" in flags
    return recursive, uninformative


def _shim_passes_through(args):
    return any(fnmatch.fnmatchcase(word, pattern) for word in args for pattern in _SHIM_PASSTHROUGH)


def recursive_grep_statement(command):
    """The first statement that runs the grep shim recursively with informative output, else None."""
    if not command or not isinstance(command, str):
        return None
    for _at, segment in iter_segments(strip_heredoc_bodies(command), "Bash"):
        words = argv_for_match(segment.strip(), "Bash")
        at = _program_at(words)
        if at is None or words[at] != _PROGRAM:
            continue
        args = words[at + 1:]
        recursive, uninformative = _option_facts(args)
        if recursive and not uninformative and not _shim_passes_through(args):
            return " ".join(words[at:])
    return None


def _empty_foreground_output(payload):
    """True when the call ran in the foreground, finished, and printed nothing on stdout."""
    response = payload.get("tool_response")
    tool_input = payload.get("tool_input")
    if not isinstance(response, dict) or not isinstance(tool_input, dict):
        return False
    stdout = response.get("stdout")
    if not isinstance(stdout, str) or response.get("interrupted") or response.get("backgroundTaskId"):
        return False
    return not tool_input.get("run_in_background") and not stdout.strip()


def notice(payload):
    """The nudge text for one PostToolUse payload, else None. Never raises."""
    try:
        if not isinstance(payload, dict) or payload.get("tool_name") != "Bash":
            return None
        if not _empty_foreground_output(payload):
            return None
        statement = recursive_grep_statement(payload["tool_input"].get("command"))
    except (TypeError, ValueError, AttributeError, IndexError, KeyError, RecursionError):
        return None
    return MESSAGE % statement if statement else None


def main(raw=None) -> int:
    """Read the hook event, emit additionalContext when the shape matches. Always exits 0."""
    try:
        payload = json.loads(raw if raw is not None else sys.stdin.read() or "{}")
    except (ValueError, TypeError):
        return 0
    text = notice(payload)
    if text:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse",
                                                 "additionalContext": text}}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
