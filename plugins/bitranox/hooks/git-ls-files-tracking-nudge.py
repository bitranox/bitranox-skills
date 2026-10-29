#!/usr/bin/env python3
"""PreToolUse(Bash|PowerShell) nudge: a bare `git ls-files <path>` used as a tracking test.

`git ls-files <path>` exits 0 whether or not the path is tracked: for an untracked or ignored path
it just prints nothing. So `git ls-files f && echo TRACKED`, `|| echo untracked` and
`if git ls-files f; then` all decide nothing - the branch is fixed before git runs, and the
answer is confident and wrong. Measured: it printed TRACKED for a gitignored CLAUDE.md and nearly
put a false "committed" claim into a commit message. `--error-unmatch` makes the exit status
mean something (0 tracked, 1 not); `git check-ignore -q` answers the separate ignored question.

What counts as a TEST of the status, given a pathspec and no --error-unmatch: the statement is
an `if`/`elif`/`while`/`until` condition or negated with `!`; or `||` follows it (except
`|| true` / `|| :`, which swallow a failure rather than test for one); or `&&` follows it AND
either its stdout goes to /dev/null (the status is all anything downstream sees) or the next
statement prints or returns a verdict (echo, printf, exit, return, false). A plain `&&` chain to
another step is NOT a test: the listing is on screen and the chain only sequences work. Also
left alone: testing the OUTPUT (`[ -n "$(git ls-files f)" ]`, `| grep -q .`), and a call with
no pathspec. Heredoc bodies and quoted text are data, not commands.

Replayed over about 186,000 recorded Bash calls (2026-10-29): the rule above fires on 2
(0.001%), one of them the motivating `git ls-files CLAUDE.md && echo CLAUDE_TRACKED`, the other
an `&& echo "label:"` between two listings. The first draft, which counted any `&&` as a test, fired
on 21 and 20 of those were chained listings (`git ls-files -s f && git add f`), so a nudge on
that rule would have spoken mostly on correct work.

NON-BLOCKING, like git-revparse-nudge, its closest sibling (a git query whose exit status
misleads): it emits additionalContext and exits 0. Fail-open on any error. ASCII only.
"""

import json
import re
import sys

from shell_text import (
    argv_for_match,
    git_verb_operands,
    is_shell_tool,
    iter_segments,
    strip_heredoc_bodies,
)

_VERB = frozenset({"ls-files"})
# Options whose VALUE is the next token, so that token is not a pathspec.
_VALUE_OPTS = frozenset({"-x", "-X", "--exclude", "--exclude-from", "--exclude-per-directory",
                         "--with-tree", "--format"})
# A redirection token: `>/dev/null`, `2>&1`, `&>out`, `<in`, or a bare `>` whose target follows.
_REDIR = re.compile(r"^(?:&|\d+)?(?:>>?|<)(?P<target>.*)$")
_CONDITION_WORDS = frozenset({"if", "elif", "while", "until", "!"})
_SWALLOWS = (["true"], [":"])
# A next statement that turns the exit status into a stated answer.
_VERDICT_PROGRAMS = frozenset({"echo", "printf", "print", "exit", "return", "false",
                               "Write-Host", "Write-Output"})
_NULL_SINKS = frozenset({"/dev/null", "$null", "NUL"})

_NOTICE = (
    "BARE git ls-files as a tracking test: `git ls-files <path>` exits 0 whether or not the path "
    "is tracked - for an untracked or gitignored path it just prints nothing - so `&&`, `||` or "
    "`if` on its exit status decide nothing and the branch you print is fixed before git runs. "
    "Use `git ls-files --error-unmatch -- <path>` (exit 0 tracked, 1 not), and "
    "`git check-ignore -q -- <path>` (exit 0 ignored) when the question is whether it is ignored."
)


def _stdout_discarded(token, target):
    """True when this redirection sends STDOUT (not only stderr) to a null sink."""
    return target in _NULL_SINKS and not token.startswith(("2", "<"))


def _read_operands(operands):
    """(pathspecs, stdout discarded) of a ls-files call; no pathspecs with --error-unmatch."""
    paths, discarded, index, literal = [], False, 0, False
    while index < len(operands):
        token = operands[index]
        redirect = _REDIR.match(token)
        if literal and not redirect:
            paths.append(token)
        elif token == "--":
            literal = True
        elif token == "--error-unmatch":
            return [], discarded
        elif redirect:
            target = redirect.group("target")
            if not target and index + 1 < len(operands):
                index += 1                                  # a bare `>` takes the next token
                target = operands[index]
            discarded = discarded or _stdout_discarded(token, target)
        elif token in _VALUE_OPTS:
            index += 1
        elif not token.startswith("-"):
            paths.append(token)
        index += 1
    return paths, discarded


def _tests_the_status(argv, gap, following, discarded):
    """True when the statement's exit status decides something (see the module docstring)."""
    if argv and argv[0] in _CONDITION_WORDS:
        return True
    separator = gap.strip()
    if separator == "||":
        return following not in _SWALLOWS
    if separator != "&&":
        return False
    return discarded or bool(following) and following[0] in _VERDICT_PROGRAMS


def notice(command, tool_name=None):
    """The nudge text when a bare `git ls-files <path>` is used as a tracking test, else None."""
    if not command or not isinstance(command, str):
        return None
    text = strip_heredoc_bodies(command)
    segments = list(iter_segments(text, tool_name))
    for position, (at, segment) in enumerate(segments):
        argv = argv_for_match(segment, tool_name)
        operands = git_verb_operands(argv, _VERB, tool_name)
        if operands is None:
            continue
        paths, discarded = _read_operands(operands)
        if not paths:
            continue
        following, gap = None, ""
        if position + 1 < len(segments):
            next_at, next_segment = segments[position + 1]
            gap = text[at + len(segment):next_at]
            following = argv_for_match(next_segment, tool_name)
        if _tests_the_status(argv, gap, following, discarded):
            return _NOTICE
    return None


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:  # noqa: BLE001 - no/invalid stdin: do nothing
        return 0
    if not isinstance(event, dict) or not is_shell_tool(event.get("tool_name")):
        return 0
    message = notice((event.get("tool_input") or {}).get("command"), event.get("tool_name"))
    if message:
        sys.stdout.write(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": message,
        }}) + "\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - a broken nudge must never wedge a turn
        sys.exit(0)
