#!/usr/bin/env python3
"""PreToolUse(Bash|PowerShell) guard against a type-check narrowed away from the tests.

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
when ALL of these hold for at least one pyright invocation in the command (every
invocation is judged, not only the first):
  - it actually invokes pyright as a check (not --version/--help);
  - pyright is given at least one positional path (no paths = the config's own
    include list = the full project = fine);
  - the directory the run lands in - the event cwd moved by every `cd` before it -
    HAS a test directory (nothing to miss otherwise; a `cd` this hook cannot follow
    leaves nothing to judge);
  - none of the given paths covers that test directory;
  - at least one given path lies inside that directory, the project root (a scratch
    file checked from elsewhere narrows nothing about the project).

Pure standard library: no jq, no shell. Reads the PreToolUse event JSON on stdin.
Exit 2 blocks the call and shows stderr to the model; every other path (including
any error) exits 0, so a broken guard never wedges a turn.
"""

import json
import re
import sys
from pathlib import Path

import shell_text

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

# A redirection ends the invocation too, but shlex keeps it as one token and it
# may carry an fd prefix ("2>/dev/null", "2>&1", ">out.txt").
_REDIRECT_RE = re.compile(r"^\d*(?:>>?|<)")

# Flags of OTHER tools that take a name/pattern as their value. Without this, a
# token that merely spells "pyright" - `find . -name pyright`, `grep -e pyright` -
# is mistaken for the executable, and whatever follows is read as its paths.
#
# The runner flags below are the same shape and bite harder, because they sit in
# the recommended invocation rather than in an unrelated command: in
# `uv run --with pyright pyright`, taking the flag's VALUE as the executable
# leaves the REAL executable as the only positional, so the guard blocks the
# no-paths form it tells you to run. This repo documents every tool that way.
_NAME_VALUE_FLAGS = frozenset(
    {
        "-name",
        "-iname",
        "-path",
        "-ipath",
        "-wholename",
        "-iwholename",
        "-regex",
        "-iregex",
        "-e",
        "--include",
        "--exclude",
        "--exclude-dir",
        "--file",
        # uv / uvx / pipx: the package to install, not a path to check.
        "--with",
        "--with-editable",
        "--from",
        "--spec",
    }
)

# Options that mean "not a type-check run".
_NON_CHECK = frozenset({"--version", "--help", "-h", "--stats", "--verifytypes"})

_TEST_DIR_NAMES = ("tests", "test")

# A statement need not BEGIN with pyright to run it: these RUN a command named by a later operand.
# Only behind one of them may pyright sit anywhere but first. Any OTHER program in front - grep,
# rg, which, test, ls, cat - is handed the word as DATA: a search pattern, a name to look up, a file
# to stat. Reading that word as the executable is what blocked `grep -rn "pyright" pyproject.toml`,
# with the file after the pattern taken as the path pyright was narrowed to.
#
# A fixed list on purpose: "any leading token is a launcher" is the bag-of-tokens reading this
# replaced. A launcher missing from here makes a real narrowed run behind it pass unblocked, so a
# replay over the real corpus, not this list, decides whether it is complete enough.
_LAUNCHERS = frozenset({
    # run the command they are handed (the same set the git guards walk past in shell_text)
    "nice", "ionice", "timeout", "sudo", "doas", "env", "stdbuf", "nohup", "setsid", "chrt",
    "taskset", "time", "exec", "command", "xargs",
    # project and package runners
    "uv", "uvx", "pipx", "poetry", "pdm", "hatch", "rye", "pixi", "conda", "mamba", "micromamba",
    "npx", "pnpm", "npm", "yarn", "bunx", "bun",
})

# A python launcher runs pyright only as `-m pyright`; `python check.py pyright` hands it a word.
_PYTHON = re.compile(r"^(?:python|pypy)\d*(?:\.\d+)*$|^py$")

# Shell words that open a statement ahead of its program: a loop or branch body, a condition, a
# brace group, a negation. `{` and `(` arrive as their own tokens only when spaced, as bash needs.
_STATEMENT_KEYWORDS = frozenset({"if", "while", "until", "do", "then", "else", "elif", "{", "(", "!"})

# `command -v pyright` and `command -V pyright` LOOK UP the program; `command pyright` runs it.
_LOOKUP_OPTIONS = frozenset({"-v", "-V"})

# PowerShell's call operator: `& C:\venv\Scripts\pyright.exe src` runs the program after it.
_CALL_OPERATOR = "&"


def _pyright_invocations(cmd: str, tool_name: str = "Bash") -> list[list[str]]:
    r"""The positional paths of EVERY pyright check run in `cmd`, one list per invocation.

    An invocation that is not a check (`--version`, `--help`, ...) contributes nothing and the scan
    goes on: ending the whole scan there let `pyright --version && pyright src` through, and judging
    only the first invocation let `pyright tests && pyright src` through. An empty list for an
    invocation means no paths were given, which is the full project. A statement whose quotes do
    not balance contributes nothing.

    Only pyright in COMMAND position counts, statement by statement - see `_LAUNCHERS`. Statements
    are cut by the shared quote-aware walk, because a newline or an unspaced `;` ends one just as a
    spaced `&&` does, and a command-position test over one undivided token list would read
    `cd sub\npyright src` as a `cd` and miss the run.

    `tool_name` picks the splitting language AND the path-separator rules, because both decide
    whether argv names pyright at all: POSIX shlex eats the separators out of a PowerShell
    `C:\venv\Scripts\pyright.exe`, and a POSIX basename over what survives still never matches.
    Either half missing lets a partial typecheck through the gate that exists to catch it.
    """
    return [positionals for positionals, _where in _pyright_runs(cmd, None, tool_name)]


def _pyright_runs(cmd: str, cwd: str | None, tool_name: str = "Bash") -> list[tuple[list[str], str | None]]:
    """(positional paths, directory it runs in) for EVERY pyright check run in `cmd`.

    The directory follows every cd-like statement before the run, read by the shared
    `shell_text.directory_change`, starting from `cwd`. It is None when a cd lands somewhere no
    static read can name (a variable, `cd -`, a bare `cd`), and such a run cannot be judged.

    The event cwd is where the SESSION sits, not where `cd <repo root> && pyright a/tests b` runs.
    Judging the paths against the session's directory blocked exactly that full-coverage run: from
    a skill dir holding its own tests/, `skills/x/tests` resolved to nothing and the skill's tests/
    read as excluded (measured on the five calls behind the report, 2026-10-05).
    """
    # Heredoc bodies first: a body is stdin DATA, so a doc or script that merely CONTAINS a narrow
    # pyright invocation is not one, and blocking it stops the footgun being written down - the
    # guard-blocks-its-own-documentation shape this gate has hit before.
    text = shell_text.strip_heredoc_bodies(cmd)
    runs: list[tuple[list[str], str | None]] = []
    here: str | None = cwd
    saved: list[str | None] = []
    segments = list(shell_text.iter_segments(text, tool_name))
    for number, (offset, segment) in enumerate(segments):
        changed, here = shell_text.directory_change(segment, here, tool_name)
        if not changed:
            run = _pyright_run(segment, tool_name)
            if run is not None:
                runs.append((run, here))
        # A cd inside a subshell ends with it: `(cd sub && pyright x); pyright y` runs y here.
        end = offset + len(segment)
        separator = text[end:segments[number + 1][0]] if number + 1 < len(segments) else ""
        if "(" in separator:
            saved.append(here)
        elif ")" in separator and saved:
            here = saved.pop()
    return runs


def _pyright_run(segment: str, tool_name: str) -> list[str] | None:
    """The positional paths of the pyright check ONE statement runs, or None when it runs none."""
    try:
        tokens = shell_text.split_for_tool(segment, tool_name, comments=True)
    except ValueError:
        return None  # unbalanced quotes: not ours to judge
    index = _pyright_index(tokens, tool_name)
    if index is None:
        return None
    return _invocation_positionals(tokens[index + 1 :])


def _is_pyright(token: str, tool_name: str) -> bool:
    return shell_text.basename_for_tool(token, tool_name) in {"pyright", "pyright.exe"}


def _pyright_index(tokens: list[str], tool_name: str) -> int | None:
    """Index of the pyright executable this ONE statement runs, or None when it runs another program.

    Leading keywords and `NAME=value` assignments are skipped. Then the program is pyright itself,
    or a known launcher with pyright later in its argv (never as another tool's flag value: the
    `--with pyright` of `uv run --with pyright pyright`), or a python launcher's `-m pyright`.
    """
    at = 0
    while at < len(tokens) and (tokens[at] in _STATEMENT_KEYWORDS or _is_assignment(tokens[at])):
        at += 1
    if at >= len(tokens):
        return None
    head = shell_text.basename_for_tool(tokens[at], tool_name)
    if head == _CALL_OPERATOR and tool_name == "PowerShell":
        at += 1
        if at >= len(tokens):
            return None
        head = shell_text.basename_for_tool(tokens[at], tool_name)
    if _is_pyright(tokens[at], tool_name):
        return at
    if _PYTHON.match(head):
        return _module_run(tokens, at)
    if head not in _LAUNCHERS:
        return None
    if head == "command" and at + 1 < len(tokens) and tokens[at + 1] in _LOOKUP_OPTIONS:
        return None
    for index in range(at + 1, len(tokens)):
        if _PYTHON.match(shell_text.basename_for_tool(tokens[index], tool_name)):
            # The launcher hands its command to python, which then decides alone: `uv run python
            # -m pyright` runs it, `env python3 gate.py --gate .venv/bin/pyright` hands a WORD to a
            # script (measured in the corpus: a gate runner told which tool to run).
            return _module_run(tokens, index)
        if not _is_pyright(tokens[index], tool_name):
            continue
        # A token that merely spells it, as the value of another tool's flag, is not the program.
        if tokens[index - 1] in _NAME_VALUE_FLAGS:
            continue
        return index
    return None


def _module_run(tokens: list[str], at: int) -> int | None:
    """Index of `pyright` in a python launcher's `-m pyright`, else None."""
    for index in range(at + 1, len(tokens) - 1):
        if tokens[index] == "-m":
            return index + 1 if tokens[index + 1] == "pyright" else None
        if not tokens[index].startswith("-"):
            return None  # a script operand: python runs that file, and the rest is its argv
    return None


def _is_assignment(token: str) -> bool:
    """True for a `NAME=value` shell assignment in front of a command."""
    name, eq, _value = token.partition("=")
    return bool(eq) and name.isidentifier()


def _invocation_positionals(args: list[str]) -> list[str] | None:
    """The paths one pyright invocation is given, or None when it is not a check run.

    Reads `args` up to the first shell operator or redirection, which ends this invocation.
    """
    positionals: list[str] = []
    skip_next = False
    for arg in args:
        if arg in _SHELL_BREAKS or _REDIRECT_RE.match(arg):
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


def _test_dir(cwd: Path) -> Path | None:
    """The project's test directory, if it has one."""
    for name in _TEST_DIR_NAMES:
        candidate = cwd / name
        if candidate.is_dir():
            return candidate
    return None


def _covers(path_arg: str, cwd: Path, tests: Path) -> bool:
    """Whether checking ``path_arg`` would reach ``tests``."""
    if "\0" in path_arg:
        # Cannot tell -> do not block. Decided here because pathlib is not consistent about it:
        # POSIX resolve() raises ValueError for an embedded NUL, Windows resolve() returns the path
        # unchanged, which then compares as "does not cover tests" and blocks.
        return True
    try:
        target = (cwd / path_arg).resolve()
        tests_resolved = tests.resolve()
    except (OSError, ValueError):
        # Cannot tell -> do not block. A ValueError escaped here once and ended the whole hook
        # instead of this one path's verdict.
        return True
    # Either the argument IS/contains the test dir, or it sits inside it.
    return target == tests_resolved or tests_resolved.is_relative_to(target) or target.is_relative_to(tests_resolved)


def _outside(path_arg: str, root: Path) -> bool:
    """Whether ``path_arg`` resolves outside the project ``root`` entirely.

    False when it cannot be told: `_covers` already lets an undecidable path through, and calling
    it outside here as well would excuse the narrowed paths beside it.
    """
    if "\0" in path_arg:
        return False
    try:
        target = (root / path_arg).resolve()
        root_resolved = root.resolve()
    except (OSError, ValueError):
        return False
    return not (target == root_resolved or target.is_relative_to(root_resolved)
                or root_resolved.is_relative_to(target))


def _excluded_tests(paths: list[str], where: str | None) -> tuple[list[str], Path] | None:
    """(paths, test dir) when a run narrowed to `paths` from `where` misses that dir's tests.

    None when the run gave no paths (the full project), when `where` cannot be read (a cd this
    hook could not follow - cannot tell, so do not block), when that directory has no tests to
    miss, when a path covers them, or when EVERY path lies outside the project. The project root
    is `where`, the directory that holds the test dir: a scratch probe elsewhere
    (`pyright /tmp/x/tcheck.py`) never had the project's tests in scope, so it narrowed nothing.
    One outside path does not excuse an inside one beside it - that run still narrows the project.
    """
    if not paths or where is None:
        return None
    base = Path(where)
    tests = _test_dir(base)
    if tests is None or any(_covers(p, base, tests) for p in paths):
        return None
    if all(_outside(p, base) for p in paths):
        return None
    return paths, tests


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

    cwd_raw = data.get("cwd")
    if not cwd_raw:
        return 0

    # Each run's result is read on its own, so each is judged on its own, from the directory it
    # runs in. Invocations with no paths use the config's include list: that IS the full project.
    runs = _pyright_runs(cmd, str(cwd_raw), data.get("tool_name") or "Bash")
    found = next((hit for hit in (_excluded_tests(paths, where) for paths, where in runs) if hit),
                 None)
    if found is None:
        return 0
    positionals, tests = found

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
