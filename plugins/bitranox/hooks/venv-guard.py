#!/usr/bin/env python3
"""PreToolUse(Bash) nudge: a test/lint/build run under a FOREIGN VIRTUAL_ENV.

An ambient `VIRTUAL_ENV` - set by an IDE, or carried into the shell from another project - silently
hijacks which interpreter a bare `pytest` / `make` / `pyright` / `pip-audit` resolves. The run then
reports on the WRONG environment, and it does so in shapes that read exactly like real defects:
`ModuleNotFoundError` for a dependency that IS installed, a flood of phantom type errors in files
nobody touched, or `pip-audit` CVEs belonging to some other project's packages. The gate is not
failing; it is answering a question about a different environment.

This is a NUDGE, never a block: the command may be perfectly deliberate. It emits
`hookSpecificOutput.additionalContext`, which is what actually reaches the model - an exit-0 hook's
stdout and stderr do not. Every failure path returns 0, so a broken guard can never wedge a turn.

Fires only when ALL of these hold, which keeps it quiet in normal work:
  * the command looks like a test/lint/type-check/audit run,
  * `VIRTUAL_ENV` is set,
  * the project directory has its own `.venv`,
  * and the two are not the same directory after resolving symlinks.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

# Split on shell separators so each statement is judged on its own tokens: `cd x && pytest` must
# still be seen as a pytest run.
_SEP = re.compile(r"&&|\|\||[;\n|]")

_TOOLS = {"pytest", "pyright", "mypy", "ruff", "pip-audit", "tox", "nox"}

# `make <target>` targets that drive the test/build pipeline. A bare `make` is not enough: `make
# docs` has no interpreter stake in this.
_MAKE_TARGETS = {
    "test", "test-all", "testintegration", "testi", "ti", "push", "release", "bump",
    "cov", "coverage", "codecov", "deps",
}


def looks_like_a_gate_run(command: str) -> bool:
    """True when a statement in `command` runs tests, lint, type-check or an audit."""
    for segment in _SEP.split(command or ""):
        tokens = segment.split()
        if not tokens:
            continue
        if any(t in _TOOLS or t.rsplit("/", 1)[-1] in _TOOLS for t in tokens):
            return True
        if "make" in tokens:
            targets = [t for t in tokens[tokens.index("make") + 1:] if not t.startswith("-")]
            if any(t in _MAKE_TARGETS for t in targets):
                return True
    return False


def _resolved(path) -> str:
    """realpath without raising: an unresolvable path just compares unequal rather than crashing."""
    try:
        return os.path.realpath(str(path))
    except OSError:
        return str(path)


def _interpreter_hint(project_venv: Path) -> str:
    """The venv's python path for THIS platform - Windows puts it in Scripts/, POSIX in bin/."""
    return str(project_venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python"))


def build_notice(command: str, cwd, venv: str | None) -> str | None:
    """The nudge text, or None when nothing is wrong. PURE - no env or filesystem writes."""
    if not command or not looks_like_a_gate_run(command):
        return None
    if not venv:
        return None
    project_venv = Path(str(cwd or ".")) / ".venv"
    if not project_venv.exists():
        return None                                   # no project venv to disagree with
    if _resolved(venv) == _resolved(project_venv):
        return None                                   # already the project's own venv
    return (
        "WRONG VENV: VIRTUAL_ENV is %s but this project's venv is %s. A test, lint, type-check or "
        "audit run here resolves the WRONG interpreter, and the failure will look like a real "
        "defect - ModuleNotFoundError for an installed dependency, phantom type errors in files "
        "you did not touch, or pip-audit findings from another project's packages.\n"
        "Re-run with the ambient value dropped: `env -u VIRTUAL_ENV uv run ...`. For a Makefile "
        "gate, also point the tool at this project's interpreter: "
        "`env -u VIRTUAL_ENV BMK_PYTHON_CMD=\"%s\" make ...`.\n"
        "If the ambient venv is deliberate here, ignore this."
        % (venv, project_venv, _interpreter_hint(project_venv))
    )


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    try:
        command = str((event.get("tool_input") or {}).get("command") or "")
        notice = build_notice(command, event.get("cwd") or os.getcwd(), os.environ.get("VIRTUAL_ENV"))
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
