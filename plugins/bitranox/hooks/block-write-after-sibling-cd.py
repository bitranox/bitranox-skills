#!/usr/bin/env python3
"""PreToolUse(Bash|PowerShell) guard: a repo-writing call with no directory of its own, after a sibling cd.

Several shell calls in ONE assistant message do not all start where the session sat when the message
was written. A call that writes runs after the calls before it have finished, and it starts in the
directory the previous one LEFT, so a `cd` in an earlier sibling moves every later sibling that
names no directory of its own. Read-only calls run side by side and never see each other's cd;
that is why a probe with `cd ... && pwd` in two calls shows no leak while the writes still land in
the wrong repository.

Both recorded incidents had that shape and nothing else in common:

- a sibling ran `cd <planning repo> && git commit ...`, and the next sibling's bare
  `git commit scripts/... && git push` ran in the planning repo, where the pathspec matched nothing;
- a sibling ran `cd <main checkout> && python3 - <<EOF` (an edit), and the next sibling's
  `gate.py --gate "make test"` ran the test gate in the main checkout instead of a worktree, which
  rewrote nine dependency floors in its tracked pyproject.toml.

So this refuses a call that WRITES to a repository (`git commit/add/push/...`, `make`, `bmk`,
`gate.py --gate`) without an ABSOLUTE target of its own (a leading `cd /abs`, `git -C /abs`,
`make -C /abs`, `--gate-cwd /abs`) when an earlier Bash call of the same assistant message changes
directory. A relative target does not count: it resolves against the inherited directory, which is
the thing in doubt. A lone bare `git commit`, or one whose siblings never cd, stays free - the
session's own directory is then the one the author saw. A cross-call arm that also fired after a cd
in an EARLIER message was priced at one command in 22 and rejected (git-wrong-repo-nudge.py says
why); the same-message arm needs no state of its own, because the siblings are in the transcript
before this call is asked about.

PRICED before shipping, by replaying 131,293 recorded Bash calls with their real earlier siblings:
33 refusals (0.025%, about one call in 4,000). Judged by what each call printed, 5 had landed in
the wrong repository (pathspec errors, a test gate run in the main checkout) and 25 inherited the
directory their author happened to want - mostly workflow agents running `cd $W` in one call and a
bare `git add` in the next. Those 25 pay one retry with an explicit target; the shape they relied
on is the one that failed the other 5, and nothing in the command tells the two apart. These
counts are REPLAY-derived: a replay shows each call every earlier sibling already on disk, which the
live hook did not see before the sibling ledger of 9.13.0 (below). They are an upper bound on what
the live hook could refuse, not a measured live rate.

The siblings come from `transcript_siblings` (shared with block-commit-beside-sibling-gate), which
asks `sibling_ledger` first - the record `sibling-ledger.py` keeps from the hook events, per session
and per subagent - and the transcript only as a fallback: on Claude Code 2.1.309 a later sibling's
hook runs before the earlier siblings reach the transcript, which left this guard blind live
(bitranox-skills OPEN-WORK [670]). When neither knows this call's siblings, the hook passes.

The PowerShell tool is read the same way: `Set-Location`/`sl`/`cd`, `git -C` and `make -C` mean
the same there, and its calls count as siblings of each other. Siblings are parsed with the calling
tool's rules, since one session drives one shell.

Data regions are masked first, so a `cd` inside a heredoc body or a quoted string is text, not a
statement. BLOCKING: exit 2 with the reason on stderr. Fail-open on any error. ASCII only.
"""

import json
import sys

from shell_text import (
    argv_for_match,
    basename_for_tool,
    blank_heredoc_bodies,
    directory_change,
    git_segment_dir,
    is_rooted,
    is_shell_tool,
    iter_segments,
    statement_program,
)
from transcript_siblings import siblings_for_event

#: git subcommands that change a repository, its index or its remote.
WRITE_VERBS = frozenset({
    "add", "am", "apply", "checkout", "cherry-pick", "clean", "commit", "merge", "mv", "pull", "push",
    "rebase", "reset", "restore", "revert", "rm", "stash", "switch", "tag",
})
_MAKE = ("make", "gmake")
_BMK = ("bmk",)
_HELP = frozenset({"--help", "-h", "--version", "-V"})
_PYTHON = ("python", "python3", "py", "uv", "uvx")
_GATE_SCRIPT = "gate.py"


def _statements(command, tool_name="Bash"):
    """(raw text, argv) of each statement, heredoc bodies blanked so their text is not code.

    The raw text goes to the cd reader, which needs the quotes a rejoined argv would have lost."""
    for _at, segment in iter_segments(blank_heredoc_bodies(command or ""), tool_name):
        text = segment.strip()
        tokens = argv_for_match(text.lstrip("(").strip(), tool_name)
        if tokens:
            yield text, tokens


def _option_value(tokens, start, names):
    """The value of the first of `names` after `start`, as `--opt value` or `--opt=value`."""
    for index in range(start, len(tokens)):
        token = tokens[index]
        for name in names:
            if token == name and index + 1 < len(tokens):
                return tokens[index + 1]
            if token.startswith(name + "="):
                return token[len(name) + 1:]
            if name == "-C" and token.startswith("-C") and len(token) > 2:
                return token[2:]
    return None


def _absolute(path):
    # Not os.path.isabs: from Python 3.13 it answers False on Windows for a drive-less root (`/work`),
    # where Git Bash and PowerShell still land at that root. `is_rooted` is the one shared rule.
    return bool(path) and is_rooted(path)


def _write_target(tokens, here, tool_name):
    """(writes, directory or None) for one statement starting at `here` (None = inherited)."""
    is_git, where = git_segment_dir(tokens, WRITE_VERBS, here, tool_name)
    if is_git:
        return True, where
    at = statement_program(tokens, _MAKE, tool_name)
    if at is not None:
        value = _option_value(tokens, at + 1, ("-C", "--directory"))
        return True, value if _absolute(value) else here
    at = statement_program(tokens, _BMK, tool_name)
    if at is not None:
        # `bmk --version`, `bmk install --help` read nothing of the repo; a subcommand (test, push,
        # bump) does. Both read-only shapes were measured in the corpus replay.
        args = tokens[at + 1:]
        if _HELP & set(args):
            return False, here
        return any(not token.startswith("-") for token in args), here
    at = statement_program(tokens, _PYTHON, tool_name)
    if at is not None and "--gate" in tokens[at:]:
        script = next((t for t in tokens[at + 1:at + 4] if basename_for_tool(t, tool_name) == _GATE_SCRIPT), None)
        if script:
            value = _option_value(tokens, at + 1, ("--gate-cwd",))
            return True, value if _absolute(value) else here
    return False, here


def targetless_write(command, tool_name="Bash"):
    """The first statement of `command` that writes to a repository with no absolute target, or None.

    The walk starts from an UNKNOWN directory: only an absolute `cd` makes the rest of the command
    independent of where it was started.
    """
    here = None
    for text, tokens in _statements(command, tool_name):
        changed, landing = directory_change(text, here, tool_name)
        if changed:
            here = landing if _absolute(landing) else None
            continue
        writes, where = _write_target(tokens, here, tool_name)
        if writes and not _absolute(where):
            return text
    return None


def changes_directory(command, tool_name="Bash"):
    """The first cd-like statement in `command` (as text), or None."""
    for text, _tokens in _statements(command, tool_name):
        if directory_change(text, None, tool_name)[0]:
            return text
    return None


def verdict(command, siblings, tool_name="Bash"):
    """The refusal reason for `command` given the earlier Bash `siblings` of its message, or None."""
    statement = targetless_write(command, tool_name)
    if statement is None:
        return None
    moved = next((cd for cd in (changes_directory(s, tool_name) for s in siblings) if cd), None)
    if moved is None:
        return None
    return statement, moved


def refusal(statement, moved):
    return "\n".join([
        "BLOCKED: this call writes to a repository without naming one, after an earlier call in",
        "the same message changed directory. Nothing in this call ran.",
        "",
        "  writes here:       " + statement,
        "  earlier sibling:   " + moved,
        "",
        "A writing call starts where the PREVIOUS call of the message left the shell, not where the",
        "session was when the message was written, so this would run in the sibling's directory.",
        "Name the repository in this call: a leading absolute `cd /abs/repo &&`, `git -C /abs/repo`,",
        "`make -C /abs/repo`, or `gate.py --gate-cwd /abs/repo` - or put both steps in one call.",
    ])


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:  # noqa: BLE001 - no/invalid stdin: do nothing
        return 0
    tool_name = event.get("tool_name") if isinstance(event, dict) else None
    if not is_shell_tool(tool_name):
        return 0
    command = (event.get("tool_input") or {}).get("command") or ""
    if targetless_write(command, tool_name) is None:
        return 0                                    # the common case never opens the transcript
    found = verdict(command, siblings_for_event(event) or [], tool_name)
    if found is None:
        return 0
    print(refusal(*found), file=sys.stderr)
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - a guard must never wedge a turn
        sys.exit(0)
