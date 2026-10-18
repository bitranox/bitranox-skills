#!/usr/bin/env python3
"""PreToolUse(Task|Agent) nudge: a brief that tells a subagent to run pyright must pin its interpreter.

pyright takes its Python environment from CONFIGURATION, not from the binary that launched it, so
`.venv/bin/pyright` and `.venv/bin/python -m pyright` analyse whatever interpreter the config
resolves. Every dependency installed only in the venv then reports `reportMissingImports` plus a
cascade of unknown types, and the run reads like a broken codebase. Only `--pythonpath
<venv>/bin/python` (or `[tool.pyright] venvPath` + `venv`) pins it.

WHY A BRIEF CHECK AND NOT ONLY THE BASH ARM. `nudge-detector-footguns` already warns on an unpinned
pyright run, and it has since 2026-07-31. It did not stop five refactor subagents on 2026-10-16
from running bare `.venv/bin/pyright`, getting hundreds of environment errors, and reporting or
chasing them as findings: the subagent follows the gate line its brief spells out, and a warning
next to its own Bash call arrives after it has already been told what the gate is. The fix belongs
where the instruction is written, which is the dispatch.

WHAT COUNTS. The brief is prose, so this reads it as prose rather than as a command line. pyright
counts only in COMMAND SHAPE - after a venv `bin/` or `Scripts\\`, `python -m`, `uv run`, `uvx`,
`npx`, a shell operator, or opening a backtick span - and not where it names the checker in a
sentence ("pyright strict", "pyright caught it"). Any pin anywhere in the brief silences it: one
pinned gate line covers the rest of the brief, and a brief that discusses the pin is already
carrying it.

`uv run pyright` does NOT count: it puts the project venv first on PATH, where pyright looks for
`python`. Measured 2026-10-18 in soundtouch-watchdog over the same 235 files: bare
`.venv/bin/pyright` 3904 errors, `uv run --no-sync pyright` 0, `--pythonpath .venv/bin/python` 0.

Replayed before shipping (2026-10-18) over every Task/Agent tool_use prompt under
`~/.claude/projects` (rglob, deduped by tool_use id): 75 of 2565 dispatches fire (2.9%). A random
sample of 40 firings read by hand held 3 false positives, all briefs DISCUSSING hook design that
quote a pyright command; the other 37 were real, unpinned gate lines. The exclusions on the right of
`_RUN` (`pyright: ignore`, `pyright/ruff`, `pyright 0`, a bare `;`) each removed a class seen in an
earlier sample. Re-run the replay with the predicate `unpinned_pyright_snippet` before widening it.

Non-blocking by design: emits additionalContext only, never a permissionDecision. Contract: reads
a PreToolUse event JSON on stdin. Fail-open: any parse/IO error -> exit 0 (a broken hook must
never wedge a turn). Pure standard library; launched via run-python.sh so it works on Windows too.
ASCII only.
"""

import json
import re
import sys

SUBAGENT_TOOLS = {"Task", "Agent"}

# A pin anywhere in the brief. `venvPath` is the config spelling; a brief that names it is either
# pinning through the config or telling the agent to.
_PIN = re.compile(r"--pythonpath\b|--venvpath\b|\bvenvPath\b", re.IGNORECASE)

# pyright in COMMAND SHAPE. The left side lists what may stand directly before the program word;
# the right side refuses a hyphenated or longer word (`pyright-strict`, `pyrightconfig`) and the
# handful of verbs and adjectives that mean the sentence is ABOUT pyright rather than running it.
_RUN = re.compile(
    r"""
    (?: `                                  # opening a code span: `pyright ...`
      | ^[ \t]*(?:\$[ \t]+)?               # a line that starts with the command, prompt or not
      | \.venv[\w.-]*/bin/                 # .venv/bin/pyright, .venv-win/bin/pyright
      | \bScripts[\\/]                     # .venv\Scripts\pyright.exe
      | -m[ \t]+                           # python -m pyright
      | \buvx[ \t]+(?:--?\S+[ \t]+)*       # uvx [opts] pyright
      | \bnpx[ \t]+                        # npx pyright
      | (?:&&|\|\|)[ \t]*                  # after && or || (a bare `;` is far likelier prose)
    )
    pyright(?:\.exe)?
    (?![\w-])
    (?![:/])                               # `pyright: ignore` pragma, `pyright/ruff` list
    (?![`"']?[ \t]+\d)                     # a reported result: "pyright 0"
    (?![`"']?[ \t]+(?:strict|strictness|caught|catches|reports?|says|flags|found|finds)\b)
    """,
    re.IGNORECASE | re.MULTILINE | re.VERBOSE,
)

_ADVICE = (
    "This brief tells the subagent to run pyright WITHOUT pinning its interpreter{where}. pyright "
    "takes its environment from configuration, not from the binary that launched it, so "
    "`.venv/bin/pyright` and `python -m pyright` analyse the ambient interpreter: every venv-only "
    "dependency reports reportMissingImports, and a subagent reports or chases those as findings "
    "(five refactor agents did, 2026-10-16). The subagent follows the gate line you write, so put "
    "the pin IN the brief: `.venv/bin/pyright --pythonpath \"$PWD/.venv/bin/python\"` (use the "
    "venv the subagent will actually run in), or name [tool.pyright] venvPath + venv."
)


def unpinned_pyright_snippet(prompt) -> str | None:
    """The command-shaped pyright mention a brief makes without any pin, else None. PURE.

    Returns a short excerpt around the first match so the advice can show which line it means.
    A non-string prompt is a malformed event and answers None.
    """
    if not isinstance(prompt, str) or not prompt:
        return None
    if _PIN.search(prompt):
        return None
    match = _RUN.search(prompt)
    if match is None:
        return None
    start = max(0, match.start() - 40)
    end = min(len(prompt), match.end() + 40)
    return " ".join(prompt[start:end].split())


def assess(tool_name, tool_input) -> str | None:
    """The advice for a dispatch whose brief runs pyright unpinned, else None. PURE."""
    if not isinstance(tool_name, str) or tool_name not in SUBAGENT_TOOLS:
        return None
    if not isinstance(tool_input, dict):
        return None
    snippet = unpinned_pyright_snippet(tool_input.get("prompt"))
    if snippet is None:
        return None
    return _ADVICE.format(where=f" (near: {snippet!r})")


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:  # noqa: BLE001 - no/invalid stdin: do nothing
        return 0
    if not isinstance(event, dict):
        return 0
    message = assess(event.get("tool_name"), event.get("tool_input"))
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
