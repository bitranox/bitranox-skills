#!/usr/bin/env python3
"""PreToolUse(Bash|PowerShell) nudge: a test/lint/build run under a FOREIGN VIRTUAL_ENV.

An ambient `VIRTUAL_ENV` - set by an IDE, or carried into the shell from another project - silently
hijacks which interpreter a bare `pytest` / `make` / `pyright` / `pip-audit` resolves. The run then
reports on the WRONG environment, and it does so in shapes that read exactly like real defects:
`ModuleNotFoundError` for a dependency that IS installed, a flood of phantom type errors in files
nobody touched, or `pip-audit` CVEs belonging to some other project's packages. The gate is not
failing; it is answering a question about a different environment.

This is a NUDGE, never a block: the command may be perfectly deliberate. It emits
`hookSpecificOutput.additionalContext`, which is what actually reaches the model - an exit-0 hook's
stdout and stderr do not. Every failure path returns 0, so a broken guard can never wedge a turn.

Fires only when ALL of these hold for one statement, which keeps it quiet in normal work:
  * the statement runs a test/lint/type-check/audit tool, or `make` with a pipeline target, in
    command position (behind launchers such as `sudo`, `timeout 600`, `nice`, `uv run`),
  * `VIRTUAL_ENV` as THAT statement will see it is set: the hook's own value, unless the command
    changes it (`env -u VIRTUAL_ENV`, a `VIRTUAL_ENV=...` prefix, an earlier `unset` or `export`,
    or on PowerShell `Remove-Item Env:VIRTUAL_ENV`),
  * the project directory has its own `.venv`, and the two are not the same directory after
    resolving symlinks,
  * the tool is not already pinned by being run from a path inside that `.venv`,
  * and it is not launched by `uv run` inside a uv project (a pyproject.toml beside the `.venv`),
    which ignores a mismatched VIRTUAL_ENV unless given `--active` or `--no-project`.

Heredoc bodies and quoted text are data, never statements. The remediation is written in the
calling tool's language: `env -u` does not exist in PowerShell.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path, PurePosixPath, PureWindowsPath

from shell_text import (
    argv_for_match,
    basename_for_tool,
    iter_segments,
    strip_heredoc_bodies,
)

_TOOLS = {"pytest", "pyright", "mypy", "ruff", "pip-audit", "tox", "nox"}

# `make <target>` targets that drive the test/build pipeline. A bare `make` is not enough: `make
# docs` has no interpreter stake in this.
_MAKE_TARGETS = {
    "test", "test-all", "testintegration", "testi", "ti", "push", "release", "bump",
    "cov", "coverage", "codecov", "deps",
}


# Tokens that stand IN FRONT of the real command rather than being it. Without this, the tool name
# has to be matched in command position or `echo pytest is great` and
# `git commit -m "fix pytest config"` both look like test runs - the guard-fires-on-prose failure.
_PREFIXES = {
    "env", "uv", "uvx", "poetry", "pdm", "hatch", "pipx", "python", "python3", "py",
    "time", "timeout", "nice", "ionice", "sudo", "doas", "run", "exec", "-m",
}

_PYTHONS = {"python", "python3", "py"}

# PowerShell's names for Remove-Item, the cmdlet that drops `Env:VIRTUAL_ENV` from the session.
_REMOVE_ITEM = {"remove-item", "ri", "rm", "del", "erase", "rd", "rmdir"}

_VAR = "VIRTUAL_ENV"

# "No change to VIRTUAL_ENV" - distinct from None, which means it is UNSET.
_KEEP = object()


def _statements(command: str, tool_name: str) -> list[list[str]]:
    """One argv per statement, heredoc bodies dropped and quoted separators left alone.

    A heredoc body is stdin data and a `;` inside quotes is part of a word, so neither may start a
    statement: splitting the raw text on separators read `git commit -m "fix; pytest now passes"`
    as a pytest run. The shared quote-aware walk knows both.
    """
    statements = []
    for _offset, segment in iter_segments(strip_heredoc_bodies(command or ""), tool_name):
        argv = argv_for_match(segment, tool_name)
        if argv:
            statements.append(argv)
    return statements


def _assignment(token: str):
    """(name, value) when `token` is a `NAME=value` shell assignment, else None."""
    if token.startswith("-"):
        return None
    name, eq, value = token.partition("=")
    if not eq or not name or "/" in name or "\\" in name:
        return None
    return name, value


def _env_option(token: str):
    """How one `env` option changes VIRTUAL_ENV: None (unset), "-u" (a name follows), or _KEEP."""
    if token in ("-i", "-", "--ignore-environment"):
        return None
    if token in ("-u", "--unset"):
        return "-u"
    for spelling in ("--unset=", "-u"):
        if token.startswith(spelling) and token[len(spelling):] == _VAR:
            return None
    return _KEEP


def _walk(tokens: list[str], tool_name: str):
    """(index of the command that owns the statement or None, this statement's VIRTUAL_ENV change).

    Walks past option flags, their values, VAR=value assignments, numeric operands (a `timeout`
    duration, a `nice` level) and known launchers, so a tool name appearing later - in an echo, a
    commit message, a grep pattern, a filename - never counts. Along the way it records what the
    statement itself does to VIRTUAL_ENV: a `VIRTUAL_ENV=...` prefix, `env VIRTUAL_ENV=...`, and
    `env -u VIRTUAL_ENV` / `--unset` / `-i`, which is this hook's own remediation.
    """
    change, previous_was_flag, in_env, unset_next = _KEEP, False, False, False
    for at, token in enumerate(tokens):
        name = basename_for_tool(token, tool_name)
        if unset_next:
            unset_next = False
            change = None if token == _VAR else change
            continue
        assignment = _assignment(token)
        if assignment is not None:
            change = (assignment[1] or None) if assignment[0] == _VAR else change
            previous_was_flag = False
            continue
        if name in _TOOLS or name == "make":
            return at, change
        option = _env_option(token) if in_env else _KEEP
        if option == "-u":
            unset_next = True
            continue
        if option is None:
            change = None
            continue
        if token.startswith("-"):
            previous_was_flag = True
            continue
        if previous_was_flag or token.isdigit():       # a flag's value, or a bare numeric operand
            previous_was_flag = False
            continue
        if name in _PREFIXES:                          # a launcher; the real command follows
            in_env = name == "env"
            continue
        return at, change                              # a different command owns this statement
    return None, change


def _session_change(tokens: list[str], tool_name: str):
    """What a statement does to VIRTUAL_ENV for every LATER statement, or _KEEP.

    Bash: `unset VIRTUAL_ENV`, `export VIRTUAL_ENV=...`, or a bare `VIRTUAL_ENV=...` (the variable
    is already exported, so assigning it changes what children see). PowerShell:
    `Remove-Item Env:VIRTUAL_ENV` and `$env:VIRTUAL_ENV = ...`, which is the remediation this hook
    gives on that tool.
    """
    activated = _activated_venv(tokens, tool_name)
    if activated is not None:
        return activated
    head = tokens[0].lower()
    if tool_name == "PowerShell":
        if head in _REMOVE_ITEM and any(_names_env_var(t) for t in tokens[1:]):
            return None
        if head == "$env:" + _VAR.lower() and len(tokens) >= 3 and tokens[1] == "=":
            value = tokens[2].strip("'\"")
            return None if value in ("", "$null") else value
        return _KEEP
    if head == "unset":
        return None if _VAR in tokens[1:] else _KEEP
    rest = tokens[1:] if head == "export" else tokens
    assignments = [_assignment(t) for t in rest]
    if rest and all(assignments):
        values = [value for name, value in assignments if name == _VAR]
        if values:
            return values[-1] or None
    return _KEEP


def _activated_venv(tokens: list[str], tool_name: str) -> str | None:
    """The venv directory a statement ACTIVATES, as written, or None when it activates nothing.

    An activate script exports VIRTUAL_ENV as its own venv for every later statement, so
    `source .venv/bin/activate && pytest` runs in the project venv whatever the ambient value was.
    Bash must SOURCE it (`source` or `.`): run as a program it sets the variable in a child that
    exits at once. PowerShell's `Activate.ps1` writes `$env:VIRTUAL_ENV`, which is process-wide, so
    it counts dot-sourced, behind `&`, or run bare. The venv is the directory holding the script's
    `bin`/`Scripts` dir; a path that names no such dir is not a venv this hook can judge.
    """
    if tool_name == "PowerShell":
        args = tokens[1:] if tokens[0] in (".", "&") else tokens
        script_name, path = "activate.ps1", PureWindowsPath(args[0]) if args else None
    else:
        args = tokens[1:] if tokens[0] in ("source", ".") else []
        script_name, path = "activate", PurePosixPath(args[0].replace("\\", "/")) if args else None
    if path is None or path.name.lower() != script_name:
        return None
    if path.parent.name.lower() not in ("bin", "scripts"):
        return None
    return str(path.parent.parent)


def _names_env_var(token: str) -> bool:
    """True for `Env:VIRTUAL_ENV` in any of PowerShell's spellings."""
    lowered = token.lower()
    if not lowered.startswith("env:"):
        return False
    return lowered[4:].lstrip("\\/") == _VAR.lower()


def _is_gate(tokens: list[str], at: int, tool_name: str) -> bool:
    name = basename_for_tool(tokens[at], tool_name)
    if name in _TOOLS:
        return True
    targets = [t for t in tokens[at + 1:] if not t.startswith("-")]
    return name == "make" and any(t in _MAKE_TARGETS for t in targets)


def _gate_runs(command: str, ambient, tool_name: str):
    """(effective VIRTUAL_ENV, argv, index of the tool) for each statement that runs a gate."""
    session = ambient
    for tokens in _statements(command, tool_name):
        change = _session_change(tokens, tool_name)
        if change is not _KEEP:
            session = change
            continue
        at, override = _walk(tokens, tool_name)
        if at is None or not _is_gate(tokens, at, tool_name):
            continue
        yield (session if override is _KEEP else override), tokens, at


def looks_like_a_gate_run(command: str, tool_name: str = "Bash") -> bool:
    """True when a statement in `command` runs tests, lint, type-check or an audit."""
    return any(True for _ in _gate_runs(command, None, tool_name))


def _within(path: str, root: str) -> bool:
    return path == root or path.startswith(root.rstrip(os.sep) + os.sep)


def _pinned_by_path(tokens: list[str], at: int, cwd, project_venv: Path, tool_name: str) -> bool:
    """True when the tool, or the python launching it, is a path inside the project's own venv.

    Such a run already uses the project's interpreter whatever VIRTUAL_ENV says: python takes its
    prefix from the executable's own location, and a venv's console script names that python in
    its shebang. pyright is the exception - it takes its environment from config and from the
    python on PATH, not from where its wrapper was installed - so its path never pins it.
    """
    if basename_for_tool(tokens[at], tool_name) == "pyright":
        return False
    root = os.path.realpath(str(project_venv))
    launchers = [t for t in tokens[:at] if basename_for_tool(t, tool_name) in _PYTHONS]
    candidates = [tokens[at], *launchers]
    for token in candidates:
        # A backslash separates path components under PowerShell, and on Windows under Bash too:
        # a quoted native path ('C:\p\.venv\Scripts\ruff.exe') reaches us with its backslashes.
        if tool_name == "PowerShell" or os.sep == "\\":
            token = token.replace("\\", "/")
        if "/" not in token:
            continue
        if _within(os.path.realpath(os.path.join(str(cwd), token)), root):
            return True
    return False


# `uv run` options that make it use VIRTUAL_ENV after all instead of the project's environment.
_UV_RUN_ACTIVE = frozenset({"--active", "--no-project"})


def _uv_run_uses_the_project(tokens: list[str], at: int, cwd, tool_name: str) -> bool:
    """True when the gate is launched by `uv run` inside a uv project, so VIRTUAL_ENV is ignored.

    Measured on uv 0.11.15 with a foreign VIRTUAL_ENV: inside a project (a pyproject.toml), `uv run`
    warns that the variable "does not match the project environment path `.venv` and will be
    ignored" and runs in the project's .venv - the hijack this hook warns about cannot happen.
    `--active` and `--no-project` DO use VIRTUAL_ENV, and with no pyproject.toml there is no
    project environment, so `uv run` uses VIRTUAL_ENV too; all three still fire. `uv tool run` /
    `uvx` are isolated tool environments, not `uv run`, and are not exempted here.
    """
    if not (Path(str(cwd or ".")) / "pyproject.toml").is_file():
        return False
    for index, token in enumerate(tokens[:at]):
        if basename_for_tool(token, tool_name) != "uv":
            continue
        between = tokens[index + 1:at]
        if "run" not in between or "tool" in between[:between.index("run")]:
            return False
        return not any(t.split("=", 1)[0] in _UV_RUN_ACTIVE for t in between)
    return False


def _interpreter_hint(project_venv: Path, windows: bool | None = None) -> str:
    """The venv's python path for THIS platform - Windows puts it in Scripts/, POSIX in bin/."""
    if windows is None:
        windows = os.name == "nt"
    return str(project_venv / ("Scripts/python.exe" if windows else "bin/python"))


def _remediation(project_venv: Path, tool_name: str) -> str:
    """The re-run advice in the TOOL's own language: `env -u` does not exist in PowerShell."""
    hint = _interpreter_hint(project_venv)
    if tool_name == "PowerShell":
        return (
            "Re-run with the ambient value dropped: `Remove-Item Env:VIRTUAL_ENV; uv run ...`. For a "
            "Makefile gate, also point the tool at this project's interpreter: "
            f"`Remove-Item Env:VIRTUAL_ENV; $env:BMK_PYTHON_CMD = \"{hint}\"; make ...`.\n"
        )
    return (
        "Re-run with the ambient value dropped: `env -u VIRTUAL_ENV uv run ...`. For a Makefile "
        "gate, also point the tool at this project's interpreter: "
        f"`env -u VIRTUAL_ENV BMK_PYTHON_CMD=\"{hint}\" make ...`.\n"
    )


def build_notice(command: str, cwd, venv: str | None, tool_name: str = "Bash") -> str | None:
    """The nudge text, or None when nothing is wrong. PURE - no env or filesystem writes.

    `venv` is the hook's own VIRTUAL_ENV. Each statement is judged against the value IT will see,
    so an override in the command itself - the hook's own `env -u VIRTUAL_ENV` remediation, a
    `VIRTUAL_ENV=...` prefix, an earlier `unset` - is honoured rather than second-guessed. An
    override whose value the shell would still expand (`$PWD/.venv`) is taken as deliberate.
    """
    if not command:
        return None
    project_venv = Path(str(cwd or ".")) / ".venv"
    if not project_venv.exists():
        return None                                   # no project venv to disagree with
    for effective, tokens, at in _gate_runs(command, venv, tool_name):
        if not effective or "$" in effective or "`" in effective:
            continue
        if _same_path(os.path.join(str(cwd or "."), effective), project_venv):
            continue                                  # already the project's own venv
        if _pinned_by_path(tokens, at, cwd or ".", project_venv, tool_name):
            continue
        if _uv_run_uses_the_project(tokens, at, cwd, tool_name):
            continue                                  # uv run ignores a mismatched VIRTUAL_ENV
        return (
            f"WRONG VENV: VIRTUAL_ENV is {effective} but this project's venv is {project_venv}. "
            "A test, lint, type-check or audit run here resolves the WRONG interpreter, and the "
            "failure will look like a real defect - ModuleNotFoundError for an installed "
            "dependency, phantom type errors in files you did not touch, or pip-audit findings "
            "from another project's packages.\n"
            f"{_remediation(project_venv, tool_name)}"
            "If the ambient venv is deliberate here, ignore this."
        )
    return None


def _same_path(a, b) -> bool:
    """Equal after resolving symlinks, so one venv reached by two paths is not a mismatch.

    `os.path.realpath` is non-strict and raises nothing for a missing or unreadable path on POSIX;
    anything it could still raise (an odd Windows error) is caught by `main` and costs one nudge.
    """
    return os.path.realpath(str(a)) == os.path.realpath(str(b))


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    try:
        command = str((event.get("tool_input") or {}).get("command") or "")
        notice = build_notice(
            command,
            event.get("cwd") or os.getcwd(),
            os.environ.get("VIRTUAL_ENV"),
            str(event.get("tool_name") or "Bash"),
        )
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
