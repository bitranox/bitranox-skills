#!/usr/bin/env python3
"""PreToolUse(Bash|PowerShell) nudge: a long bare `sleep` waits on the CLOCK, not on the event.

Waiting a fixed span for something whose real duration you have not measured is how a run either
returns before the work finished or sits idle long after it did. The rule is to wait on a concrete
SIGNAL (a marker file, a status endpoint, a completion line, the worker process still existing),
or on a measured duration plus a small margin, and to stop and INVESTIGATE at roughly twice the
expected time rather than waiting longer.

A sleep INSIDE a polling loop is the opposite of this mistake - that is waiting on the signal, with
the sleep merely pacing the checks - so `until ... do sleep N; done` and friends are left alone
however long the pause. Short pauses are left alone too: a couple of seconds to let a service
settle is not a wait on an event.

A second shape is a WAITER or a GATE detached with a trailing `&` (a sleep, a poll loop, gate.py,
ci_wait, backstop.py, `gh run watch`, or a gate such as `make test` or pytest). Under
run_in_background the task exits at once, so nothing is armed; in a foreground call the job is
orphaned - no completion notice, its verdict only in a redirect file. A `( ... ) &` that a later
`wait` collects is exempt, and so is PowerShell, where `&` is the call operator. Corpus replay
2026-10-15 (143,483 shell commands): 21 waiter firings and 30 gate firings, 48 of them real
detached jobs.

The long sleep is a NUDGE (additionalContext, exit 0). The detached waiter or gate is a REFUSAL
(stderr, exit 2): the warning recurred while it existed, including a subagent's `make test &`, so
the user turned it into a block on 2026-10-12. Fail-open on any error. ASCII only.
"""
from __future__ import annotations

import json
import re
import sys

from shell_text import (
    BACKGROUND_GATE_RE,
    blank_heredoc_bodies,
    is_shell_tool,
    mask_data_regions,
    strip_heredoc_bodies,
)

# Below this a sleep is a settle pause, not a wait on an event.
LONG_SLEEP_SECONDS = 60

# Both spellings: POSIX `sleep 300` / `sleep 10m`, and PowerShell `Start-Sleep -Seconds 300`.
# The plugin registers this hook on a Bash|PowerShell matcher, so knowing only one of them makes
# it run on Windows and find nothing, which is as silent as never firing at all.
_SLEEP = re.compile(
    r"\b(?:start-)?sleep\s+(?:-(?P<param>seconds|milliseconds|ms|s)\s+)?"
    r"(?P<n>\d+(?:\.\d+)?)(?P<unit>[smhd])?\b",
    re.IGNORECASE,
)

# A keyword counts only at a COMMAND POSITION - start of line, or after a separator. Matching the
# bare word anywhere silenced the nudge on `sleep 300 && echo done`, which is the exact shape this
# hook exists to catch, and left `/tmp/done` looking like a loop terminator.
_DO = re.compile(r"(?:^|[;&|\n(])\s*(do)\b")
_DONE = re.compile(r"(?:^|[;&|\n(])\s*(done)\b")

# PowerShell paces a poll with a brace BLOCK instead of do/done. Applied ONLY for the PowerShell
# tool: excluding `;` from the run before the brace is not enough on its own, because an awk or jq
# program pairs a loop word with a brace and is not a loop body at all.
_BRACE_LOOP = re.compile(r"\b(?:while|until|for|foreach|do)\b[^{;\n]*\{", re.IGNORECASE)

_UNITS = {"s": 1, "m": 60, "h": 3600, "d": 86400}
# PowerShell names the unit as a parameter instead of a suffix; -Milliseconds is not seconds.
_PARAM_SCALE = {"milliseconds": 0.001, "ms": 0.001}

_NOTICE = (
    "ARBITRARY SLEEP: this waits on the CLOCK for %s seconds, not on the event. Wait on a "
    "concrete SIGNAL instead - a marker file, a status endpoint, a completion line in the log, or "
    "the worker process still existing - and check the worker is alive, because a flat derived "
    "signal cannot tell finished from aborted. If no signal exists, use a MEASURED duration plus "
    "1.3-1.5x, and stop and investigate at about 2x rather than waiting longer. A sleep pacing a "
    "polling loop is fine and is not what this is about."
)


def _seconds(match) -> float:
    param = (match.group("param") or "").lower()
    if param in _PARAM_SCALE:
        return float(match.group("n")) * _PARAM_SCALE[param]
    return float(match.group("n")) * _UNITS.get((match.group("unit") or "s").lower(), 1)


def _loop_body_spans(text):
    """Half-open spans covered by a `do ... done` loop body, honouring nesting.

    An unterminated `do` runs to the end of the text: a sleep after it is still inside the body as
    far as anything here can tell, and exempting it errs toward silence rather than a false nudge.
    """
    marks = [(m.start(1), 1) for m in _DO.finditer(text)]
    marks += [(m.start(1), -1) for m in _DONE.finditer(text)]
    marks.sort()
    spans, depth, opened = [], 0, None
    for pos, delta in marks:
        if delta == 1:
            if depth == 0:
                opened = pos
            depth += 1
        elif depth:
            depth -= 1
            if depth == 0 and opened is not None:
                spans.append((opened, pos))
                opened = None
    if depth and opened is not None:
        spans.append((opened, len(text)))
    return spans


def _brace_body_spans(text):
    """Half-open spans covered by a PowerShell loop's brace block."""
    spans = []
    for match in _BRACE_LOOP.finditer(text):
        opened = match.end() - 1
        depth = 0
        for index in range(opened, len(text)):
            if text[index] == "{":
                depth += 1
            elif text[index] == "}":
                depth -= 1
                if depth == 0:
                    spans.append((opened, index))
                    break
        else:
            spans.append((opened, len(text)))
    return spans


def notice(command, tool_name="Bash"):
    """The nudge text when a long sleep waits on the clock outside a polling loop, else None.

    `tool_name` selects the loop syntax, because a brace block is a loop BODY only in PowerShell.
    In a shell command it is an awk or jq program, and `awk '/for/ { system("sleep 300") }'` really
    does wait on the clock - exempting it would be silent, which is the failure nobody reports. An
    unknown tool gets the stricter shell reading: for a nudge, a false nudge is cheaper than a
    false silence.
    """
    if not command or not isinstance(command, str):
        return None
    text = strip_heredoc_bodies(command)
    spans = _loop_body_spans(text)
    if tool_name == "PowerShell":
        spans += _brace_body_spans(text)
    longest = 0.0
    for match in _SLEEP.finditer(text):
        if any(start <= match.start() < end for start, end in spans):
            continue  # this sleep PACES a poll: the loop is the wait, not the clock
        longest = max(longest, _seconds(match))
    if longest < LONG_SLEEP_SECONDS:
        return None
    # Not int(): a long enough literal overflows float to inf, and int(inf) raises, which the
    # top-level fail-open would turn into a silently lost nudge.
    return _NOTICE % format(longest, ".0f")


# What a backgrounded unit must be to count as a WAITER: it starts with a sleep or a loop head, or
# it runs one of the waiting jigs. A daemon (`nohup server &`) is none of these and is left alone.
_WAITER = re.compile(
    r"^\s*\(?\s*(?:sleep\s+\d|until\b|while\b)"
    r"|\bgate\.py\b|\bbackstop\.py\b|\bci_wait(?:\.py)?\b|\bgh\s+run\s+watch\b")
_LOOP_HEAD = re.compile(r"(?:^|[\s;&|(])(?:while|until|for|select)\b")
_LOOP_CLOSE = re.compile(r"(?:^|[\s;&|(])done\b")
# `\s*` sits OUTSIDE the alternation so the text after the LAST `&` - ` wait`, space first - is
# collected too; inside it, `^` had to meet `wait` with nothing between and a pair read as orphaned.
_LATER_WAIT = re.compile(r"(?:^|[;&|\n(])\s*wait\b")


def _unit_start(masked, end, *, and_or=False):
    """Where the statement backgrounded by the `&` at `end` begins.

    Walks back over a `( ... )` group and over a whole `while/until ... do ... done` loop, so
    `(sleep 600; kill $P) &` and `until X; do sleep 5; done &` are judged as one unit each.
    With `and_or`, `&&` and `||` do not end it: `make test && git push &` detaches the whole list,
    gate included, which is what the gate check must see. The waiter check keeps the narrower unit
    because its pattern is anchored at the unit's start (`cd x && sleep 600 &`).
    """
    depth, at = 0, end - 1
    while at >= 0:
        char = masked[at]
        if char == ")":
            depth += 1
        elif char == "(":
            if depth == 0:
                return at
            depth -= 1
        elif depth == 0 and (char in ";\n" or _is_lone_ampersand(masked, at)
                             or (not and_or and masked[at - 1:at + 1] in ("&&", "||"))):
            # Inside a loop the unit runs back to its HEAD: keep walking while the text after
            # this separator closes more loops than it opens.
            tail = masked[at + 1:end]
            if len(_LOOP_CLOSE.findall(tail)) <= len(_LOOP_HEAD.findall(tail)):
                return at + 1
        at -= 1
    return 0


def _is_lone_ampersand(text, at):
    """True when the `&` at `at` backgrounds a statement, not part of `&&`, `2>&1`, `&>f`, `|&`."""
    return (text[at] == "&" and (at == 0 or text[at - 1] not in "<>&|\\")
            and text[at + 1:at + 2] not in (">", "&"))


_WAITER_REFUSAL = {
    True: ("`%s` ends in `&` inside a run_in_background task, so the task exits at once and "
           "nothing is armed - the completion notice will be about the launcher, not the wait. Let "
           "the task itself BE the waiter: drop the `&`."),
    False: ("`%s` ends in `&` in a foreground call, so it is orphaned: untracked, no completion "
            "notice, its verdict only in a redirect file. Run it with run_in_background and no "
            "`&`, so the harness tells you when it ends."),
}

_REFUSAL_TAIL = (
    "If it must outlive the session (run_in_background is reaped when the session ends), put it "
    "in a script that appends its own RC to its log, launch that script with setsid nohup, and "
    "judge it by that RC. Several jobs at once are fine when a later `wait` collects them.")


def backgrounded_waiter(command, tool_name="Bash"):
    """The waiter or gate a lone `&` detaches, or None. Bash only; a later `wait` collects it.

    A gate counts as a waiter: its verdict is what the session waits for, and detaching it loses
    that verdict the same way. It is searched on the MASKED list, so a gate named in quoted text
    or a heredoc body is not one.
    """
    if tool_name != "Bash" or not command or not isinstance(command, str):
        return None
    raw = blank_heredoc_bodies(command)
    masked = mask_data_regions(raw, tool_name=tool_name)
    for at in (i for i, char in enumerate(masked) if char == "&" and _is_lone_ampersand(masked, i)):
        if _LATER_WAIT.search(masked[at + 1:]):
            continue
        unit = raw[_unit_start(masked, at):at]
        if _WAITER.search(unit.strip()):
            return " ".join(unit.split())[:100]
        start = _unit_start(masked, at, and_or=True)
        if BACKGROUND_GATE_RE.search(masked[start:at]):
            return " ".join(raw[start:at].split())[:100]
    return None


def refusal(waiter, *, background):
    """The stderr text for a refused detached waiter."""
    return "\n".join([
        "BLOCKED: a waiter or gate detached with a trailing `&`.",
        "",
        _WAITER_REFUSAL[bool(background)] % waiter,
        "",
        _REFUSAL_TAIL,
    ])


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:  # noqa: BLE001 - no/invalid stdin: do nothing
        return 0
    if not isinstance(event, dict) or not is_shell_tool(event.get("tool_name")):
        return 0
    tool_input = event.get("tool_input") or {}
    tool_name = event.get("tool_name") or "Bash"
    waiter = backgrounded_waiter(tool_input.get("command"), tool_name)
    if waiter:
        # A refusal, not a nudge: the warning recurred while it existed (user decision 2026-10-12).
        # The sleep notice is not added here - the re-sent command gets it, if it still applies.
        print(refusal(waiter, background=tool_input.get("run_in_background")), file=sys.stderr)
        return 2
    message = notice(tool_input.get("command"), tool_name)
    if message:
        # ONE document: Claude Code reads a single JSON object from a hook's stdout.
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
