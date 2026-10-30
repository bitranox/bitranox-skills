#!/usr/bin/env python3
"""PreToolUse(Bash|PowerShell) guard: refuse a command that prints an environment dump unfiltered.

An environment dump carries the session's live tokens (a messaging token, API keys exported into
the shell), and whatever a command prints lands in the transcript. Masking a dump does not work:
a mask keyed on line syntax misses a token in the middle of a line, and a `tail -3` of a captured
`pwshpy env --jsonl` printed one in full. So the dump itself is refused unless its output goes
through a filter that narrows it to the one question being asked.

WHAT COUNTS AS A DUMP (each is a pipeline stage):

- `env` with no command to run (options and NAME=VALUE assignments only), and `printenv` with no
  variable name - both print every variable. A bare `env -i` prints the empty environment and
  passes; `command -v env` only looks the name up and passes. `sudo`, `time`, `uv run` and the
  other wrappers are seen through;
- `pwshpy env` (also as `python -m pwshpy env`, `uvx pwshpy env`, `uv run pwshpy env`,
  `uvx --from pwshpy pwshpy env`), which has no per-variable form;
- a reader (`cat`, `head`, `tail`, `tr`, `strings`, `xxd` and the like) of `/proc/<pid>/environ`;
- a reader of a file that an earlier dump in the SAME command redirected its output into
  (`pwshpy env --jsonl > out; tail -3 out`). A file written by an earlier tool call is not
  tracked: this guard keeps no state between calls.

WHEN A DUMP IS ALLOWED:

- its stdout goes to a file (`env > f`, `env | sort > f`): nothing is printed. That file is then
  remembered for the rule above;
- a later stage of its pipeline narrows it: `grep` (but not `grep -v`, which prints everything
  else), `wc`, `cut -f1` (names only), and anything this guard cannot read the effect of - `sed`,
  `awk`, `jq` with a real filter, an interpreter. Those are let through rather than judged,
  because a block on a filter that did narrow is the kind that gets routed around. Only stages
  known to pass every line on (`sort`, `head`, `tail`, `tee`, `cat`, `grep -v`, `jq .`, ...) leave
  the dump unfiltered.

Heredoc bodies are data and are not read. A dump inside `$(...)`, `bash -c '...'` or an ssh
command string is not seen. PowerShell's own forms (`Get-ChildItem env:`) are not judged; the
PowerShell tool reaches only the `pwshpy env` rule.

Pure standard library. Exit 2 blocks the call through `shell_text.refuse`; every other path,
any error included, exits 0.
"""

import json
import re
import sys

import shell_text
from shell_text import (
    argv_for_match,
    basename_for_tool,
    iter_segments,
    mask_data_regions,
    strip_heredoc_bodies,
)

__all__ = ["dump_leaks", "main"]

_PIPES = frozenset({"|", "|&"})
_KEYWORDS = frozenset({"do", "then", "else", "elif", "{", "(", "!", "exec"})
# Transparent prefixes: they run the next word as the program. Value-taking options per wrapper.
_WRAPPERS = {
    "sudo": frozenset({"-u", "-g", "-U", "-p", "-C", "-h", "-r", "-t", "--user", "--group"}),
    "doas": frozenset({"-u", "-C"}),
    "command": frozenset(),
    "nohup": frozenset(),
    # Bash's `time -p` and GNU time's `-f FORMAT` / `-o FILE` both time the program after them.
    "time": frozenset({"-f", "-o", "--format", "--output"}),
    "nice": frozenset({"-n", "--adjustment"}),
    "ionice": frozenset({"-c", "-n", "-p", "-P"}),
    "stdbuf": frozenset({"-i", "-o", "-e", "--input", "--output", "--error"}),
    "timeout": frozenset({"-s", "-k", "--signal", "--kill-after"}),
}
# `command -v NAME` / `-V NAME` looks NAME up and prints where it is; it runs nothing.
_LOOKUP_ONLY = re.compile(r"^-[pvV]*[vV][pvV]*$")
# Value-taking options of `uv run` and `uvx` (from their --help): the value is a package, a path
# or a version, never the program, so `uvx --from pwshpy pwshpy env` runs the SECOND pwshpy.
_UV_VALUE_OPTS = frozenset({
    "--from", "-w", "--with", "--with-editable", "--with-requirements", "-c", "--constraints",
    "-b", "--build-constraints", "--overrides", "--extra", "--no-extra", "--group", "--no-group",
    "--only-group", "--no-editable-package", "--env-file", "--package", "--python-platform",
    "--torch-backend", "--index", "--default-index", "-i", "--index-url", "--extra-index-url",
    "-f", "--find-links", "--index-strategy", "--keyring-provider", "-P", "--upgrade-package",
    "--upgrade-group", "--resolution", "--prerelease", "--prerelease-package", "--fork-strategy",
    "--exclude-newer", "--exclude-newer-package", "--no-sources-package", "--reinstall-package",
    "--link-mode", "-C", "--config-setting", "--config-settings-package",
    "--no-build-isolation-package", "--no-build-package", "--no-binary-package", "--cache-dir",
    "--refresh-package", "-p", "--python", "--color", "--allow-insecure-host", "--directory",
    "--project", "--config-file",
})
_ENV_VALUE_OPTS = frozenset({"-u", "--unset", "-C", "--chdir"})
# `env -i` with no assignment prints the EMPTY environment it was asked for.
_ENV_EMPTIES = re.compile(r"^(?:-|--ignore-environment|-0*i[0i]*)$")
_ENV_RUNS_A_STRING = frozenset({"-S", "--split-string"})
_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\+?=")
# `env "$(printf 'NAME=\\xff')" cmd`: the substitution expands to an assignment, not a program.
_EXPANDS_TO_ASSIGNMENT = re.compile(r"^(?:\$\(|`)[^=]*[A-Za-z_][A-Za-z0-9_]*=")
_ENVIRON = re.compile(r"/proc/[^/\s]+/environ\b")
_READERS = frozenset({"cat", "head", "tail", "less", "more", "bat", "batcat", "tac", "nl",
                      "strings", "xxd", "od", "hexdump", "column", "tr", "fold"})
# Stages that pass every line of their input on: a dump piped only through these is still a dump.
_PASS_THROUGH = frozenset({"sort", "uniq", "head", "tail", "tee", "cat", "less", "more", "column",
                           "nl", "tr", "fold", "tac", "xxd", "od", "strings", "hexdump", "bat",
                           "batcat", "expand", "unexpand", "fmt"})
_OUT_REDIRECT = re.compile(r"^(?P<fd>\d*|&)>>?\|?(?P<dest>.*)$")
_IN_REDIRECT = re.compile(r"^\d*<(?P<more><*)(?P<dest>.*)$")
_PRINTING_TARGETS = frozenset({"/dev/stdout", "/dev/stderr", "/dev/tty", "/dev/fd/1",
                               "/dev/fd/2"})


def _strip_redirections(words):
    """(words without redirections, stdout file target or None, stdout goes to a file).

    Only a STDOUT redirection to a real file stops the stage printing: `2>&1` moves stderr, and
    `>&2` sends stdout to the transcript all the same. An input redirection's file is kept as an
    operand, so `tr '\\0' '\\n' < /proc/1/environ` is read like `cat /proc/1/environ`.
    """
    kept, target, to_file = [], None, False
    i = 0
    while i < len(words):
        word = words[i]
        out = _OUT_REDIRECT.match(word)
        inp = _IN_REDIRECT.match(word)
        if out:
            fd, dest = out.group("fd"), out.group("dest")
            if not dest and i + 1 < len(words):
                dest, i = words[i + 1], i + 1
            if fd in ("", "1", "&"):
                if dest.startswith("&") or dest in _PRINTING_TARGETS:
                    to_file, target = False, None
                elif dest:
                    to_file, target = True, (None if dest == "/dev/null" else dest)
        elif inp:
            dest = inp.group("dest")
            if not dest and i + 1 < len(words):
                dest, i = words[i + 1], i + 1
            if not inp.group("more") and dest:     # `<<` and `<<<` carry data, not a file
                kept.append(dest)
        else:
            kept.append(word)
        i += 1
    return kept, target, to_file


def _past_options(words, at, value_opts):
    """Index of the first word from `at` on that is not an option or an option's value."""
    while at < len(words) and words[at].startswith("-"):
        at += 2 if words[at] in value_opts else 1
    return at


def _program_index(words, tool_name):
    """Index of the word this stage RUNS, past keywords, assignments and wrappers; None if none."""
    at = 0
    while at < len(words):
        word = words[at]
        if word in _KEYWORDS or _ASSIGNMENT.match(word):
            at += 1
            continue
        name = basename_for_tool(word, tool_name)
        # uv's global options may stand before `run` (`uv --quiet run env`, `uv --directory x
        # run env`); _UV_VALUE_OPTS holds the global ones that take a value, so x is skipped too.
        verb = _past_options(words, at + 1, _UV_VALUE_OPTS) if name == "uv" else at
        if name == "uv" and words[verb:verb + 1] == ["run"]:
            at = _past_options(words, verb + 1, _UV_VALUE_OPTS)
            continue
        if name in _WRAPPERS:
            start = at + 1
            at = _past_options(words, start, _WRAPPERS[name])
            if name == "command" and any(_LOOKUP_ONLY.match(w) for w in words[start:at]):
                return None
            if name == "timeout" and at < len(words):
                at += 1                                  # the duration
            continue
        return at
    return None


def _env_dumps(words, at, tool_name):
    """`env` at `at`: True when it prints the environment, else whether the command it runs does."""
    i, emptied, assigned = at + 1, False, False
    while i < len(words):
        word = words[i]
        if word in ("--help", "--version"):
            return False
        if word in _ENV_RUNS_A_STRING or word.startswith(("-S", "--split-string")):
            return False
        if word in _ENV_VALUE_OPTS:
            i += 2
            continue
        if word.startswith("-") or _ASSIGNMENT.match(word) or _EXPANDS_TO_ASSIGNMENT.match(word):
            emptied = emptied or bool(_ENV_EMPTIES.match(word))
            assigned = assigned or not word.startswith("-")
            i += 1
            continue
        return _stage_dumps(words[i:], tool_name)
    # An assignment's value can expand a secret (`env -i T=$TOKEN`), so only a bare `env -i` is safe.
    return not (emptied and not assigned)


def _pwshpy_env(words, at, tool_name):
    """Is the program at `at` (pwshpy itself, or a launcher of it) running `pwshpy env`?"""
    for i in range(at, min(len(words), at + 8)):
        if i > at and words[i - 1] in _UV_VALUE_OPTS:
            continue                       # `--from pwshpy`: the package, not the program run
        name = basename_for_tool(words[i], tool_name).lower()
        if name == "pwshpy" or name.startswith(("pwshpy==", "pwshpy@")):
            rest = [w for w in words[i + 1:] if not w.startswith("-")]
            options = [w for w in words[i + 1:] if w.startswith("-")]
            stops = {"-h", "--help", "--version"}
            return bool(rest) and rest[0] == "env" and not (stops & set(options))
    return False


def _stage_dumps(words, tool_name, dump_files=frozenset()):
    """Does this pipeline stage write an environment dump to its stdout?"""
    at = _program_index(words, tool_name)
    if at is None:
        return False
    name = basename_for_tool(words[at], tool_name).lower()
    if name == "env":
        return _env_dumps(words, at, tool_name)
    if name == "printenv":
        return not [w for w in words[at + 1:] if not w.startswith("-")]
    if name in ("uv", "uvx") or name.startswith(("pwshpy", "python", "py")):
        return _pwshpy_env(words, at, tool_name)      # a launcher is never also a reader
    if name in _READERS:
        operands = words[at + 1:]
        if any(_ENVIRON.search(w) for w in operands):
            return True
        return any(w in dump_files for w in operands)
    return False


def _passes_everything(words, tool_name):
    """Does this stage hand its whole input on, so a dump upstream of it still prints in full?"""
    at = _program_index(words, tool_name)
    if at is None:
        return False
    name = basename_for_tool(words[at], tool_name).lower()
    args = words[at + 1:]
    if name in _PASS_THROUGH:
        return True
    if name in ("grep", "egrep", "fgrep", "rg"):
        return any(w in ("-v", "--invert-match") or re.match(r"^-[a-zA-Z]*v", w) for w in args)
    if name == "jq":
        filters = [w for w in args if not w.startswith("-")]
        return not filters or filters[0] == "."
    if name == "cut":
        # Only the first `=`-separated field is the variable NAME; any other cut (`-c1-200`,
        # `-f2`) still prints values.
        return not _cuts_names_only(args)
    return False


def _cuts_names_only(args):
    """Is this `cut` keeping field 1 of `=`-separated lines and nothing else?"""
    delimiter, fields = None, None
    for i, word in enumerate(args):
        value = args[i + 1] if i + 1 < len(args) else ""
        if word in ("-d", "--delimiter"):
            delimiter = value
        elif word.startswith(("-d", "--delimiter=")):
            delimiter = word.split("=", 1)[1] if word.startswith("--") else word[2:]
        elif word in ("-f", "--fields"):
            fields = value
        elif word.startswith(("-f", "--fields=")):
            fields = word.split("=", 1)[1] if word.startswith("--") else word[2:]
    return delimiter == "=" and fields == "1"


def _statements(text, tool_name):
    """Pipelines of `text`: each a list of stage word lists, in order.

    Statement boundaries are read on the MASKED text, where quoted strings and substitutions are
    filled in place: the separator walk reports a `$(` as a boundary, so `X=$(mktemp) env ... cmd`
    read raw splits into a bare `X=` and an `env` with no command. The mask keeps every offset,
    so each statement's words are then taken from the original text.
    """
    masked = mask_data_regions(text, tool_name=tool_name)
    pieces = list(iter_segments(masked, tool_name))
    pipelines, current = [], []
    for k, (offset, segment) in enumerate(pieces):
        end = offset + len(segment)
        nxt = pieces[k + 1][0] if k + 1 < len(pieces) else len(masked)
        separator = masked[end:nxt].strip()
        original = text[offset:end].strip()
        words = argv_for_match(original, tool_name) if original else []
        if words:
            current.append(words)
        if separator not in _PIPES and current:
            pipelines.append(current)
            current = []
    if current:
        pipelines.append(current)
    return pipelines


def dump_leaks(command, tool_name="Bash"):
    """The pipelines of `command` that print an environment dump unfiltered, as display strings."""
    if not isinstance(command, str) or not command.strip():
        return []
    leaks, dump_files = [], set()
    for stages in _statements(strip_heredoc_bodies(command), tool_name):
        dumping = False
        for index, raw in enumerate(stages):
            words, target, to_file = _strip_redirections(raw)
            if not dumping and _stage_dumps(words, tool_name, frozenset(dump_files)):
                dumping = True
            elif dumping and not _passes_everything(words, tool_name):
                dumping = False                      # narrowed, or a stage this guard cannot read
                break
            if dumping and to_file:
                if target:
                    dump_files.add(target)
                dumping = False
                break
        if dumping:
            leaks.append(" | ".join(" ".join(stage) for stage in stages))
    return leaks


_MESSAGE = """\
BLOCKED: this command prints an environment dump unfiltered.

{lines}

An environment dump holds the session's live tokens (API keys, messaging tokens), and whatever a
command prints lands in the transcript. Masking it, or printing only a few lines with head/tail,
does not help: a token sits in the middle of a line as easily as at its end.

Ask the narrow question instead:
  - one variable:        printenv NAME     or   env | grep -c '^NAME='
  - is it set:           [ -n "$NAME" ] && echo SET || echo UNSET
  - names only:          env | cut -d= -f1
  - a captured dump:     grep -c PROBE out.txt   (never cat/head/tail the file)
If a secret was already printed, say so and recommend rotating it."""


def main(raw=None):
    """Refuse an unfiltered environment dump. Exit 2 blocks; every other path exits 0."""
    try:
        event = json.loads(raw if raw is not None else sys.stdin.read() or "{}")
        tool_input = event.get("tool_input") if isinstance(event, dict) else None
        command = tool_input.get("command") if isinstance(tool_input, dict) else None
        tool_name = event.get("tool_name") or "Bash"
        leaks = dump_leaks(command, tool_name)
    except Exception:  # noqa: BLE001 - a broken guard must never wedge a turn
        return 0
    if not leaks:
        return 0
    lines = "\n".join("    " + leak[:200] for leak in leaks[:3])
    return shell_text.refuse(_MESSAGE.format(lines=lines))


if __name__ == "__main__":
    sys.exit(main())
