#!/usr/bin/env python3
"""PreToolUse(Bash|PowerShell) nudge for checks that silently report the wrong answer.

A check you write to VERIFY your own work is itself unverified code, and it fails in
the direction that produces a false alarm or a false all-clear - never in a direction
you notice, because you are reading its output to find out what is true.

Four such invocations are mechanically detectable and have each burned a real session.
All are NUDGES (non-blocking `additionalContext`), not blocks: each has legitimate
uses, and the failure is a wrong ANSWER rather than a dangerous action, so the right
intervention is to tell the model what it is about to misread.

1. `find ... -newermt <relative time>`

   `bfs` (a drop-in `find` shipped as `find` on some systems) REJECTS a relative
   `-newermt` argument: "Invalid timestamp. Supported timestamp formats are ISO
   8601-like". GNU find accepts it. So a poll loop written as

       find "$DIR" -newermt '-3 minutes' | wc -l

   returns 0 on every tick under bfs - not because nothing changed, but because the
   command errored. A backstop built on it reports "NO ACTIVITY, investigate"
   forever, with equal confidence whether the thing it watches is healthy or dead.

2. `pyright` with no interpreter pinned, in a tree that has a virtualenv

   pyright resolves its environment from CONFIGURATION, not from the interpreter that
   launched it, so `.venv/bin/python -m pyright` does NOT analyse `.venv`. Every
   dependency installed only there reports `reportMissingImports`, plus a cascade of
   unknown-type errors. The output looks like a broken codebase and is a broken
   invocation. Fires only when a venv directory is actually present and no
   `--pythonpath` / `--venvpath` / `-p` / `--project` is given.

3. `grep -c PAT FILE || echo 0`

   grep -c PRINTS 0 and EXITS 1 when nothing matches, so the fallback runs as well and the
   captured value is "0\\n0". A numeric test on it errors and the check it guards is skipped.
   Corpus replay (103,932 shell commands): 29 firings, 23 outputs visibly doubled.

4. `git status --porcelain && echo CLEAN` - a state label chained on a command whose exit status
   does not encode that state

   git status / diff (without --quiet or --exit-code) / ls-files (without --error-unmatch) / log,
   `find` and `gh ... list` exit 0 whatever they found, so the label prints when it is false.
   Corpus replay: 323 such chains; 249 were reading hints ("(no output = clean)") and are left
   alone; of the 74 bare claims several printed CLEAN directly under ` M` lines. After excluding
   progress markers and `||` fallbacks the shipped matcher fires 67 times (0.06%); read one by
   one, all but one ("backup ok") are bare state claims.

Pure standard library: no jq, no shell. Reads the PreToolUse event JSON on stdin,
writes `hookSpecificOutput.additionalContext` on stdout, and ALWAYS exits 0 - a nudge
must never wedge a turn, and every error path is swallowed for the same reason.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from shell_text import (
    argv_for_match,
    basename_for_tool,
    iter_segments,
    mask_data_regions,
    strip_heredoc_bodies,
)

# `grep ... -c ... || echo 0` inside ONE pipeline element: a `|` after grep hands the fallback a
# different command's status, so it is excluded by the character class.
_GREP_COUNT_FALLBACK = re.compile(
    r"\bgrep\b[^;&\n|]*?\s(?:-[A-Za-z]*c[A-Za-z]*|--count)\b[^;&\n|]*(?P<op>\|\|)\s*echo\s+[\"']?0\b")

# A command whose exit status says it RAN, not what it found, chained to an echo.
_UNENCODED = re.compile(
    r"(?P<prog>\bgit(?:\s+-C\s+\S+)?\s+(?:status|diff|ls-files|log)\b|\bfind\b"
    r"|\bgh\s+(?:run|pr|issue)\s+list\b)(?P<args>[^;&|\n]*?)"
    r"(?P<op>&&)\s*echo\s+(?P<label>[^;&|\n]*)")
_ENCODES = re.compile(r"--exit-code|--quiet|(?<!\S)-q\b|--error-unmatch|--check\b")
_STATE_WORD = re.compile(
    r"\b(?:CLEAN|EMPTY|NONE|NOTHING|NO[ _-]?CHANGES?|NO[ _-]?DIFF|UNCHANGED|DIRTY|UNTRACKED|"
    r"TRACKED|MISSING|ABSENT|PRESENT|EXISTS?|FOUND|NOT[ _-]?FOUND|IGNORED|SAME|IDENTICAL|"
    r"DIFFERS?|DIFFERENT|OK|PUSHED)\b", re.IGNORECASE)
# A label that tells the READER how to judge the output above it is not a claim. Measured: 249 of
# 323 chains were this, e.g. "(no output = clean)", "--- (empty above = clean) ---". A progress
# marker ("CLEAN-CHECK-DONE") says a step ran, which the status does vouch for.
_READING_HINT = re.compile(
    r"above|if\b|=|means|expect|should|\?|---|===|empty|blank|\(|done|checked|\bcheck\b", re.I)

# A -newermt value bfs cannot parse. ISO-like stamps are fine; these are not.
_RELATIVE_TIME_RE = re.compile(
    r"""^\s*(
        [-+]\s*\d+            |   # -3 minutes, +2 days
        \d+\s+\w+\s+ago       |   # 3 minutes ago
        yesterday | today | now | tomorrow
    )""",
    re.VERBOSE | re.IGNORECASE,
)

# Pinning the interpreter, in any of the accepted spellings.
_PYRIGHT_PIN_FLAGS = frozenset({"--pythonpath", "--venvpath", "-p", "--project"})

_VENV_DIRS = (".venv", "venv", ".virtualenv")


def _tokens(command: str, tool_name: str = "Bash") -> list[list[str]]:
    """One argv per STATEMENT, split the way the tool's own shell would split it.

    Segmenting comes first because a flat token stream loses the boundaries that decide whose flag
    is whose: shlex never emits a newline token, keeps `sub&&pyright` as one word, and with
    `comments=True` cuts at a mid-word `#` (`docs#tag`) and drops the rest of the line. The shared
    quote-aware walk knows all three. Heredoc bodies are data, so they are dropped before it.

    Each statement's argv comes from `argv_for_match`, which splits by the TOOL's rules - the
    PowerShell arm keeps `C:\\...\\pyright.exe` intact - and removes a real, word-initial comment.
    """
    statements: list[list[str]] = []
    for _offset, segment in iter_segments(strip_heredoc_bodies(command or ""), tool_name):
        argv = argv_for_match(segment, tool_name)
        if argv:
            statements.append(argv)
    return statements


def _invocation_tokens(
    statements: list[list[str]], program: str, tool_name: str = "Bash"
) -> list[list[str]]:
    """The arguments after each invocation of `program`, one list per invocation.

    A flag belongs to the command it FOLLOWS, and only within its own statement. Scanning every
    token on the line instead attributes another command's flag to this one, in both directions:
    it invents a `find -newermt` nobody wrote, and it reads `mkdir -p`'s flag as pyright's pin so a
    genuinely unpinned run goes unnudged. The second is a MISS, which is the worse half.

    The program is matched by basename with `.exe` dropped, so `/usr/bin/find`,
    `C:\\Python312\\Scripts\\pyright.exe` and `python -m pyright` all count.
    """
    runs: list[list[str]] = []
    for argv in statements:
        for at, tok in enumerate(argv):
            if basename_for_tool(tok, tool_name).lower() == program:
                runs.append(argv[at + 1:])
                break
    return runs


def find_newermt_relative(statements: list[list[str]], tool_name: str = "Bash") -> str | None:
    """Return the offending -newermt value, or None."""
    for run in _invocation_tokens(statements, "find", tool_name):
        for i, tok in enumerate(run):
            if tok == "-newermt" and i + 1 < len(run):
                value = run[i + 1]
                if _RELATIVE_TIME_RE.match(value):
                    return value
    return None


def pyright_without_pinned_interpreter(
    statements: list[list[str]], cwd: Path, tool_name: str = "Bash"
) -> bool:
    """True when pyright runs unpinned in a tree that actually has a virtualenv."""
    runs = _invocation_tokens(statements, "pyright", tool_name)
    if not runs:
        return False
    # A pin flag counts only if it is PYRIGHT's. `-p` is also mkdir's, and reading `mkdir -p build
    # && pyright` as pinned silenced the nudge on an unpinned run.
    if any(t in _PYRIGHT_PIN_FLAGS or t.startswith(("--pythonpath=", "--venvpath="))
           for run in runs for t in run):
        return False
    # `Path.is_dir` swallows only some errnos before Python 3.14: a parent directory that denies
    # search permission raises PermissionError there (measured on 3.10, 3.12 and 3.13).
    try:
        return any((cwd / d).is_dir() for d in _VENV_DIRS if d)
    except OSError:
        return False


def _executed_matches(pattern, command: str, tool_name: str, *anchors: str):
    """Matches of `pattern` whose program word and every named operator group are CODE.

    The pattern runs on the heredoc-stripped text, and each anchor position is checked against the
    masked view of the same text (equal length), where quoted strings, assignment values and echo
    operands are filler: `echo "git status && echo CLEAN"` documents the chain and runs none of it.
    """
    text = strip_heredoc_bodies(command or "")
    masked = mask_data_regions(text, tool_name=tool_name)
    for match in pattern.finditer(text):
        spots = [match.start()] + [match.start(a) for a in anchors]
        if all(masked[at:at + 2] == text[at:at + 2] for at in spots):
            yield match


def grep_count_fallback(command: str, tool_name: str = "Bash") -> bool:
    """True when a `grep -c ... || echo 0` appears outside a heredoc body.

    Quoted text is NOT excluded, unlike the state-label check. Replayed both ways over the corpus:
    every firing a quote-aware view dropped (5 of 29) was a real count inside a quoted command line
    another shell runs - `ssh host '... $(grep -c X f || echo 0) ...'`, `bash -lc '...'` - and the
    only firing the raw view added was a Python string quoting the shape. A nudge that misses the
    remote half of the defect is the worse error.
    """
    del tool_name  # the pattern is the same under either shell; kept for the replay's signature
    return _GREP_COUNT_FALLBACK.search(strip_heredoc_bodies(command or "")) is not None


def unencoded_state_label(command: str, tool_name: str = "Bash") -> str | None:
    """The `<cmd> && echo <STATE>` chain whose label the command's exit status cannot vouch for."""
    for match in _executed_matches(_UNENCODED, command, tool_name, "op"):
        if _ENCODES.search(match.group("args")):
            continue
        label = match.group("label")
        if _STATE_WORD.search(label) and not _READING_HINT.search(label):
            return match.group(0).strip()
    return None


def build_notice(command: str, cwd: Path, tool_name: str = "Bash") -> str | None:
    """The advisory text for one command, or None when nothing applies."""
    statements = _tokens(command, tool_name)
    if not statements:
        return None
    notes: list[str] = []

    if grep_count_fallback(command, tool_name):
        notes.append(
            "`grep -c PAT FILE || echo 0`: grep -c PRINTS 0 and EXITS 1 when nothing matches, so "
            "the fallback runs too and the captured value is '0\\n0' - a numeric test on it errors "
            "and the check is skipped. Write `n=$(grep -c PAT FILE || true); n=${n:-0}`."
        )

    chain = unencoded_state_label(command, tool_name)
    if chain is not None:
        notes.append(
            f"`{chain[:80]}`: that command exits 0 whatever it found (git status/diff/ls-files/log, "
            "find, gh ... list), so the label prints even when it is false - measured, CLEAN printed "
            "directly under ` M` lines. Test the property instead: `test -z \"$(git status "
            "--porcelain)\"`, `git diff --quiet`, `git ls-files --error-unmatch`, or read the output."
        )

    offending = find_newermt_relative(statements, tool_name)
    if offending is not None:
        notes.append(
            f"`find -newermt {offending!r}`: a relative timestamp is REJECTED by bfs (shipped as "
            "`find` on this and other systems) - the command errors and prints nothing, so a poll "
            "loop built on it reports 'no activity' whether or not anything changed. Compare "
            "mtimes yourself (`stat -c%Y`, or Python `Path.stat().st_mtime`) against a recorded "
            "baseline, or pass an ISO-8601 timestamp."
        )

    if pyright_without_pinned_interpreter(statements, cwd, tool_name):
        notes.append(
            "`pyright` with no interpreter pinned, in a tree that has a virtualenv: pyright takes "
            "its environment from CONFIG, not from the interpreter that launched it, so "
            "`python -m pyright` analyses the ambient interpreter. Every venv-only dependency then "
            "reports reportMissingImports and the output looks like a broken codebase. Add "
            "`--pythonpath <venv>/bin/python`, or set [tool.pyright] venvPath+venv."
        )

    if not notes:
        return None
    body = "\n".join(f"- {n}" for n in notes)
    return (
        "A verification command here can report the wrong answer SILENTLY:\n"
        f"{body}\n"
        "Before trusting any hand-rolled check, run it against a known negative and require it to "
        "say 'different'."
    )


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    try:
        command = str(event.get("tool_input", {}).get("command", ""))
        cwd = Path(str(event.get("cwd") or "."))
        notice = build_notice(command, cwd, str(event.get("tool_name") or "Bash"))
        if notice:
            json.dump(
                {"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": notice}},
                sys.stdout,
            )
    except Exception:  # noqa: BLE001 - a nudge must never wedge a turn
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
