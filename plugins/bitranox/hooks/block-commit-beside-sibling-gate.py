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
measured: the shape is refused because nothing in it can tell. These counts are REPLAY-derived: a
replay shows each call every earlier sibling already on disk, which the live hook did not see
before the sibling ledger of 9.13.0 (below). They are an upper bound on what the live hook could
refuse, not a measured live rate.

A commit sent BEFORE its gate in the same message is not caught: nothing of the gate has run or
been recorded yet. Data regions are masked first, so a gate or a commit named inside a heredoc body
or a quoted string is text, not a command.

The siblings come from `transcript_siblings` (shared with block-write-after-sibling-cd), which asks
`sibling_ledger` first and the transcript only as a fallback. Live on Claude Code 2.1.309 the
transcript does not yet hold the earlier siblings when this hook runs, so a probe commit beside
`ruff --version` went through on 9.12.0 and is refused once the ledger is read (probed 2026-10-23,
both arms in a throwaway session). A file EDIT that fails is invisible to every PreToolUse hook; the
PostToolBatch hook publish-after-failed-edit-note covers that case after the fact. BLOCKING: exit 2
with the reason on stderr. Fail-open on any error. ASCII only.

The dependency can also point the other way: a long run that READS what a push published, sent beside
that push. `daily-topic-refresh.sh` rebases every topic from origin, so a run sent with the push it
needs validates the old topic when the push is refused or fails, and costs a re-run of its long
gates. Incident 2026-11-02: a hook refused the push, the `--force` run started anyway against the
unfixed topic. The script is named literally rather than through a vocabulary, because it is the one
script known to read pushed state and a general "reads what was pushed" cannot be seen in a command.
A push beside the run is refused in either order; the chained form in one call stays allowed.
PRICED 2026-11-02 by replaying 197,983 recorded Bash calls with their real earlier siblings: 61 runs
of the script, 1 refusal, and that one is the incident. The gate arm fired 26 times on the same walk,
so the walk does see sibling pairs.
"""

import json
import os
import sys

# `runs_a_gate` lives in shell_text beside the gate vocabulary, so block-masked-gate-exit reads the
# program word the same way when it asks whether a piped element is a gate.
import shell_text
from shell_text import (
    basename_for_tool,
    commands_only,
    is_gated_command,
    is_git_verb,
    is_shell_tool,
    iter_segments,
    program_word_at,
    runs_a_gate,
)
from transcript_siblings import siblings_for_event

PUSH_READING_SCRIPT = "daily-topic-refresh.sh"
_SCRIPT_RUNNERS = frozenset({"bash", "sh"})


def _segments(command, tool_name):
    return [seg for _at, seg in iter_segments(commands_only(command or "", tool_name), tool_name)]


def runs_push_reading_script(command, tool_name="Bash"):
    """True when a statement of `command` RUNS the script as its program, directly or through bash/sh."""
    for segment in _segments(command, tool_name):
        words = segment.split()
        at = program_word_at(words, tool_name)
        if at is None:
            continue
        if basename_for_tool(words[at], tool_name) in _SCRIPT_RUNNERS:
            at = next((i for i in range(at + 1, len(words)) if not words[i].startswith("-")), None)
            if at is None:
                continue
        if os.path.basename(words[at].strip("'\"")) == PUSH_READING_SCRIPT:
            return True
    return False


def _pushes(command, tool_name):
    return any(is_git_verb(seg.strip().lstrip("(").strip(), {"push"}, tool_name) for seg in _segments(command, tool_name))


def verdict(command, siblings, tool_name="Bash"):
    """The earlier sibling whose gate this publishing `command` would act on unread, or None."""
    if not is_gated_command(command, tool_name):
        return None
    return next((s for s in siblings if runs_a_gate(s, tool_name)), None)


def push_reader_verdict(command, siblings, tool_name="Bash"):
    """The earlier sibling that pairs a push with the script reading it, or None; one call doing both is the fix."""
    if runs_push_reading_script(command, tool_name):
        if _pushes(command, tool_name):
            return None
        return next((s for s in siblings if _pushes(s, tool_name)), None)
    if _pushes(command, tool_name):
        return next((s for s in siblings if runs_push_reading_script(s, tool_name)), None)
    return None


def push_reader_refusal(sibling):
    first = (sibling.strip().splitlines() or [""])[0][:120]
    return "\n".join([
        "BLOCKED: a push and " + PUSH_READING_SCRIPT + " in the same message. The script reads",
        "what is on origin, and calls in one message do not wait for each other: a refused or failed",
        "push does not stop the run, which then validates the old state through its long gates.",
        "",
        "  earlier sibling: " + first,
        "",
        "Do one of these instead:",
        "  - chain them in ONE call:  git push origin <branch> && ./scripts/" + PUSH_READING_SCRIPT + " --force",
        "  - or start the run in the next message, after reading that the push landed.",
    ])


def refusal(gate):
    first = (gate.strip().splitlines() or [""])[0][:120]
    return "\n".join([
        "BLOCKED: this call publishes (commit/push/PR) in the same message as a gate whose",
        "verdict nobody has read yet.",
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
    if not is_gated_command(command, tool_name) and not runs_push_reading_script(command, tool_name):
        return 0                                    # the common case never opens the transcript
    siblings = siblings_for_event(event) or []
    gate = verdict(command, siblings, tool_name)
    if gate is not None:
        return shell_text.refuse(refusal(gate))
    paired = push_reader_verdict(command, siblings, tool_name)
    if paired is not None:
        return shell_text.refuse(push_reader_refusal(paired))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - a guard must never wedge a turn
        sys.exit(0)
