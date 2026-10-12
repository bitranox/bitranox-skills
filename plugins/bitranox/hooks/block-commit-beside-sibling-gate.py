#!/usr/bin/env python3
"""PreToolUse(Bash|PowerShell) guard: a commit or push sent beside the gate it depends on.

Tool calls in ONE assistant message do not wait for each other's verdict. They run one after
another, but a refusal, an error or a red result in one never stops the next: each was decided
before any of them ran. So a message holding a test run AND a `git commit` commits whatever the
test said, and nobody has read what it said.

The incident, 2026-10-12: a doc edit was followed by one message with two calls, the cooldown test
module and `git add -A && git commit`. block-masked-gate-exit refused the test call (it piped
pytest into `tail`); the commit ran anyway. That was the fourth recorded miss of the written rule
"gate in the same && chain as the action, or read the gate before acting" - and none of the
earlier guards could see it, because each judges one call alone.

So this refuses a call that PUBLISHES - a `git commit`, `git push` or `gh pr create`
(`shell_text.is_gated_command`) - when an EARLIER shell call of the same message runs a recognised
gate (`shell_text.GATE_RE`, or the gate.py jig). The two allowed shapes are the fix: put the gate in
the same call, chained with `&&` so a red gate stops the commit, or send the commit in the NEXT
message, after reading the gate's real exit code.

PRICED before shipping, by replaying 131,830 recorded shell calls with their real earlier siblings
(4,663 of them commit, push or PR): 19 refusals, about one call in 7,000. All 19 were read in full,
and every one had an earlier sibling that really ran a gate (`make test`, `pytest`, `ruff check`,
`pyright`, the gate.py jig) followed by a commit nobody had checked against it; four of the 19
were found by reading the siblings back, since a heredoc edit and a commit-message write sat in the
same calls. Each costs one retry in the next message. Whether those 19 gates were red was not
measured: the shape is refused because nothing in it can tell.

A commit sent BEFORE its gate in the same message is not caught: the first call's hook finds
nothing of its message in the transcript yet (probed on 2.1.296). Data regions are masked first, so
a gate or a commit named inside a heredoc body or a quoted string is text, not a command.

The siblings come from `transcript_siblings` (shared with block-write-after-sibling-cd), which reads
a subagent's own transcript when the event carries an `agent_id`. BLOCKING: exit 2 with the reason
on stderr. Fail-open on any error. ASCII only.
"""
from __future__ import annotations

import json
import sys

from shell_text import (
    GATE_JIG_RE,
    GATE_RE,
    basename_for_tool,
    commands_only,
    is_gated_command,
    is_shell_tool,
    iter_segments,
)
from transcript_siblings import siblings_for_event


# Words that run the program after them. Their own operands sit in between and are skipped: the
# value of a short option that takes one (`env -u NAME`, `nice -n 19`, `env -C DIR`), a long
# option's value (`uv run --with pytest`), a duration (`timeout 900`), `run` after `uv`, and
# `NAME=value` assignments (`env A=1 make test`).
_LAUNCHERS = frozenset({
    "env", "timeout", "nice", "ionice", "nohup", "setsid", "stdbuf", "time", "command", "exec",
    "sudo", "doas", "uv", "uvx", "python", "python3", "py",
})
_SHORT_WITH_VALUE = frozenset({"-u", "-n", "-C", "-c", "-k", "-s", "-S", "-p", "-o"})
_SCAN_LIMIT = 16


def _is_assignment(word):
    name, sep, _value = word.partition("=")
    return bool(sep) and name.replace("_", "a").isalnum() and not name[:1].isdigit()


def _program_at(words, tool_name):
    """Index of the word a statement RUNS, past assignments and launchers; None when there is none.

    `python -m X` runs X. `python -c ...` runs code, never a gate by name, so it answers None.
    """
    at = 0
    for _ in range(_SCAN_LIMIT):
        while at < len(words) and _is_assignment(words[at]):
            at += 1
        if at >= len(words):
            return None
        program = basename_for_tool(words[at], tool_name).lower()
        if program not in _LAUNCHERS and not program.startswith("python"):
            return at
        at += 1
        while at < len(words) and (words[at].startswith("-") or words[at] == "run"
                                   or words[at][:1].isdigit() or _is_assignment(words[at])):
            word = words[at]
            if word == "-c" and program.startswith(("python", "py")):
                return None
            if word == "-m":
                return at + 1 if at + 1 < len(words) else None
            at += 2 if (word in _SHORT_WITH_VALUE or (word.startswith("--") and "=" not in word)) else 1
    return None


def runs_a_gate(command, tool_name="Bash"):
    """True when a statement of `command` RUNS a recognised gate as its program.

    A gate that is only text - inside a heredoc body or quotes, or an argument of another program
    (`grep -rn pytest docs/`, `cat pytest.ini`) - does not count.
    """
    for _at, segment in iter_segments(commands_only(command or "", tool_name), tool_name):
        words = segment.split()
        at = _program_at(words, tool_name)
        if at is None:
            continue
        if GATE_JIG_RE.search(words[at]) or GATE_RE.match(" ".join(words[at:at + 3])):
            return True
    return False


def verdict(command, siblings, tool_name="Bash"):
    """The earlier sibling whose gate this publishing `command` would act on unread, or None."""
    if not is_gated_command(command, tool_name):
        return None
    return next((s for s in siblings if runs_a_gate(s, tool_name)), None)


def refusal(gate):
    first = (gate.strip().splitlines() or [""])[0][:120]
    return "\n".join([
        "BLOCKED: this call publishes (commit/push/PR) in the same message as a gate whose",
        "verdict nobody has read yet. Nothing in this call ran.",
        "",
        "  earlier sibling (the gate): " + first,
        "",
        "Calls in one message do not wait for each other's result: a refused, failed or red gate",
        "does not stop the call after it, so this would commit whatever the gate said.",
        "",
        "Do one of these instead:",
        "  - chain them in ONE call so a red gate stops the commit:  <gate> && git commit ...",
        "  - or send the commit in the next message, after reading the gate's real exit code.",
    ])


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:  # noqa: BLE001 - no/invalid stdin: do nothing
        return 0
    if not isinstance(event, dict):
        return 0
    tool_name = event.get("tool_name")
    if not is_shell_tool(tool_name):
        return 0
    command = (event.get("tool_input") or {}).get("command") or ""
    if not is_gated_command(command, tool_name):
        return 0                                    # the common case never opens the transcript
    gate = verdict(command, siblings_for_event(event) or [], tool_name)
    if gate is None:
        return 0
    print(refusal(gate), file=sys.stderr)
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - a guard must never wedge a turn
        sys.exit(0)
