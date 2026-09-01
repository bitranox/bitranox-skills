#!/usr/bin/env python3
"""PreToolUse(Task|Agent) gate: a self-declared TEXT-ONLY probe must be enforced by capability.

A baseline or pressure scenario is often dispatched with a prompt that opens "answer from this
message alone, do not use any tools". That instruction is prose, and prose does not bind a
subagent: measured, such a dispatch to `general-purpose` explored the real tree, rewrote a stored
fact, and committed to two git repositories, then reported only the text it had been asked for.

Measured a second time, from the other side: `Explore` genuinely has NO Write tool and still
created a file with `echo BREACH > path`. So Bash alone is sufficient to mutate, and "a read-only
agent type" is not a write-safe answer - only an agent whose tool list excludes Bash as well is.

So when a dispatch's own prompt declares it needs no tools, this denies it unless it uses an INERT
agent type. The trigger is the operator's own explicit declaration, which keeps false positives
low: an ordinary dispatch never says it. The deny names the safe form rather than only refusing,
because a guard that blocks the wrong action without providing the right one just gets routed
around.

Contract: reads a PreToolUse event JSON on stdin. Fail-open: any parse/IO error -> exit 0 (a
broken hook must never wedge a turn). Pure standard library; launched via run-python.sh so it
works on Windows too. ASCII only.
"""
import json
import re
import sys

SUBAGENT_TOOLS = {"Task", "Agent"}

# Agent types whose tool list excludes Bash, Write, Edit and Read, so a text-only probe cannot
# reach the filesystem at all. An agent definition's `tools:` list IS enforced (probe-verified via
# Explore, which genuinely has no Write), but an EMPTY list means UNRESTRICTED - so an inert type
# must name a minimal non-empty list. This plugin ships `agents/baseline-probe.md`; a plugin agent
# is addressed namespaced, and a bare local copy is accepted too.
INERT_AGENT_TYPES = {"baseline-probe", "bitranox:baseline-probe"}

# Only an explicit, first-person DECLARATION that this dispatch needs no tools. Prose that merely
# discusses tool use must not match, or the gate blocks ordinary review work - the classic guard
# failure is firing on text that MENTIONS the footgun it guards.
_DECLARATIONS = (
    r"answer from this (message|prompt) alone",
    r"do not use (any )?tools",
    r"don'?t use (any )?tools",
    r"reply with text only",
    r"respond with text only",
    r"do not read files, run commands",
    r"without using any tools",
)
_DECLARATION_RX = re.compile("|".join(_DECLARATIONS), re.I)

# A declaration is an IMPERATIVE opening a sentence or a line. Embedded in a subordinate clause
# ("it changes how we do not use tools that ...") it is description, not an instruction - caught
# by this module's own negative test before it ever shipped.
_SENTENCE_SPLIT = re.compile(r"[.!?\n]+")

# A declaration still OPENS the line when a list bullet or a label comes first: one "- " was enough
# to let through exactly the dispatch this gate exists to deny. At most ONE bullet and ONE label
# that ends in a colon are stripped, so prose merely discussing tool use is untouched - "Explain
# the rule that says do not use any tools" has no colon and is still not a match.
#
# The label is deliberately NOT length-capped. A cap is an arbitrary number deciding a
# security-shaped verdict, and it fails by MISSING - the direction nobody notices. The accepted
# cost is the other way: a sentence whose subject ends in a colon ("The rule we broke last week
# was: do not use any tools") now reads as a label and DENIES. That is loud, the caller can
# reword, and there is a test pinning it so it is not rediscovered as a bug.
_BULLET_OR_LABEL = re.compile(r"^\s*(?:[-*+\u2022]\s+|\d+[.)]\s+)?(?:[A-Za-z][A-Za-z ]*:\s+)?")

# "Do not use any tools OTHER THAN Read and Grep" says the opposite of a text-only declaration: the
# dispatch needs tools and names them. Denying it sends the caller to an inert type that has none
# of what the prompt just asked for. Only phrases that introduce a named exception count - "but" is
# deliberately absent, because it also opens clauses that grant nothing, and a wrong ALLOW here is
# the silent direction.
_EXCEPTION = re.compile(r"\b(other than|except|besides|apart from)\b", re.I)

# `don'?t` covered U+0027 alone, so the apostrophe every word processor produces walked past it.
_APOSTROPHES = {ord(c): "'" for c in (chr(0x2019), chr(0x02BC), chr(0xFF07))}

_DENY = (
    "TEXT-ONLY PROBE ON A TOOL-CAPABLE AGENT. This dispatch's prompt declares it needs no tools, "
    "but '{atype}' can still reach the filesystem - and that instruction is prose, which does not "
    "bind a subagent. Measured: a dispatch worded exactly this way rewrote a stored fact and "
    "committed to two git repos while reporting only the text it was asked for. Measured again: "
    "'Explore' has no Write tool and still wrote a file with 'echo > path', so excluding Write is "
    "not enough - Bash is the hole. Re-dispatch with subagent_type='bitranox:baseline-probe' (an "
    "inert type shipped by this plugin: no Bash, no Write, no Edit, no Read), or drop the "
    "text-only declaration if the agent genuinely needs tools. Do not simply re-word the prompt - "
    "that is the thing that failed. Note: agent definitions are read at SESSION START, so a "
    "freshly installed type is only selectable in a new session; until then, dispatch with tools "
    "and treat anything the agent reports about the real system as contaminating the baseline."
)


def _declares_text_only(prompt):
    """Pure: True when a SENTENCE of the prompt opens with a no-tools declaration, allowing for a
    leading list bullet or short label, and not counting one that goes on to name an exception."""
    for chunk in _SENTENCE_SPLIT.split((prompt or "").translate(_APOSTROPHES)):
        opening = _BULLET_OR_LABEL.sub("", chunk, count=1).strip()
        hit = _DECLARATION_RX.match(opening)
        if hit and not _EXCEPTION.search(opening[hit.end():]):
            return True
    return False


def assess(tool_name, tool_input=None):
    """Pure: ('deny', message) for a text-only probe on a tool-capable type, else (None, '')."""
    if tool_name not in SUBAGENT_TOOLS:
        return (None, "")
    if not isinstance(tool_input, dict):
        return (None, "")
    atype = str(tool_input.get("subagent_type") or "").strip()
    if atype.lower() in {t.lower() for t in INERT_AGENT_TYPES}:
        return (None, "")
    if not _declares_text_only(str(tool_input.get("prompt") or "")):
        return (None, "")
    return ("deny", _DENY.format(atype=atype or "the default agent"))


def main():
    try:
        event = json.load(sys.stdin)
    except Exception:  # noqa: BLE001 - no/invalid stdin: do nothing
        return 0
    if not isinstance(event, dict):
        return 0
    action, message = assess(event.get("tool_name"), event.get("tool_input"))
    if action == "deny":
        sys.stdout.write(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": message,
        }}) + "\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - a broken hook must never wedge a turn
        sys.exit(0)
