#!/usr/bin/env python3
"""PreToolUse(Bash) guard against a type-check narrowed away from the tests.

The recurring mistake:

    pyright src/                # clean!
    pyright src/foo.py src/bar.py   # clean!

...taken as "the project type-checks". It does not: the paths given to pyright
replace the ones its config would have checked, so `tests/` is never looked at.
A strict-mode error in a test file (an untyped lambda, an untyped fixture) then
surfaces only later, from the authoritative full run, after the narrowed one has
already been believed. The narrowed command is not wrong to run - it is wrong to
TRUST, and it reads identically to the real thing, which is why re-reading a note
about it does not help.

The block is deliberately narrow, so false positives are near zero. It fires only
when ALL of these hold:
  - the command actually invokes pyright as a check (not --version/--help);
  - pyright is given at least one positional path (no paths = the config's own
    include list = the full project = fine);
  - the project HAS a test directory (nothing to miss otherwise);
  - none of the given paths covers that test directory.

Pure standard library: no jq, no shell. Reads the PreToolUse event JSON on stdin.
Exit 2 blocks the call and shows stderr to the model; every other path (including
any error) exits 0, so a broken guard never wedges a turn.
"""

import json
import re
import shlex
import sys
from pathlib import Path

# Pyright options that consume the following token, so it is a value and not a
# path to check.
_VALUE_FLAGS = frozenset(
    {
        "-p",
        "--project",
        "--pythonpath",
        "--pythonversion",
        "--pythonplatform",
        "--typeshedpath",
        "--venvpath",
        "--level",
        "--threads",
        "--outputformat",
    }
)

# Tokens that end the pyright invocation inside a larger shell line.
_SHELL_BREAKS = frozenset({";", "&&", "||", "|", ">", ">>", "<", "&"})

# Options that mean "not a type-check run".
_NON_CHECK = frozenset({"--version", "--help", "-h", "--stats", "--verifytypes"})

_TEST_DIR_NAMES = ("tests", "test")


def _pyright_positionals(cmd: str) -> list[str] | None:
    """Positional paths handed to pyright, or None if this is not a check run."""
    try:
        tokens = shlex.split(cmd, comments=True)
    except ValueError:
        return None  # unbalanced quotes: not ours to judge

    for index, token in enumerate(tokens):
        # Match the executable itself, not a substring of some other word.
        if Path(token).name not in {"pyright", "pyright.exe"}:
            continue

        positionals: list[str] = []
        skip_next = False
        for arg in tokens[index + 1 :]:
            if arg in _SHELL_BREAKS:
                break
            if skip_next:
                skip_next = False
                continue
            if arg in _NON_CHECK:
                return None
            if arg.startswith("-"):
                skip_next = arg in _VALUE_FLAGS
                continue
            positionals.append(arg)
        return positionals
    return None


def _test_dir(cwd: Path) -> Path | None:
    """The project's test directory, if it has one."""
    for name in _TEST_DIR_NAMES:
        candidate = cwd / name
        if candidate.is_dir():
            return candidate
    return None


def _covers(path_arg: str, cwd: Path, tests: Path) -> bool:
    """Whether checking ``path_arg`` would reach ``tests``."""
    try:
        target = (cwd / path_arg).resolve()
        tests_resolved = tests.resolve()
    except OSError:
        return True  # cannot tell -> do not block
    # Either the argument IS/contains the test dir, or it sits inside it.
    return target == tests_resolved or tests_resolved.is_relative_to(target) or target.is_relative_to(tests_resolved)


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return 0
    cmd = (data.get("tool_input") or {}).get("command") or ""
    if not cmd:
        return 0

    # Fast path: only guard commands that call pyright.
    if not re.search(r"\bpyright\b", cmd):
        return 0

    positionals = _pyright_positionals(cmd)
    if not positionals:
        # None = not a check run. Empty = no paths given, so pyright uses its
        # config's include list: that IS the full project.
        return 0

    cwd_raw = data.get("cwd")
    if not cwd_raw:
        return 0
    cwd = Path(cwd_raw)
    tests = _test_dir(cwd)
    if tests is None:
        return 0  # no tests to miss

    if any(_covers(p, cwd, tests) for p in positionals):
        return 0

    rel = tests.name
    msg = [
        f"BLOCKED: this pyright run excludes '{rel}/', so a clean result would not mean the project type-checks.",
        f"  paths given: {' '.join(positionals)}",
        "",
        "Passing paths REPLACES the include list from the config, so the test files are",
        "never looked at. A strict-mode error there (untyped lambda, untyped fixture)",
        "then shows up later from the full run, after this one has been believed.",
        "",
        "Run the authoritative check instead:",
        "  pyright                 # no paths: uses the config's include list",
        f"  pyright src {rel}",
        "",
        f"To check the tests alone, name them: pyright {rel}",
    ]
    print("\n".join(msg), file=sys.stderr)
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
