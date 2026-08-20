#!/usr/bin/env python3
"""Warn when a gated verb shares one Bash command with the prep that produces its input.

A PreToolUse gate judges the WHOLE command before any statement runs. So when a single command both
writes a file (a heredoc, a redirect) and then runs a verb a gate may block, a block discards the
write too: the retry fails on a missing `-F` input and points at the wrong cause, which is a
different and much more confusing failure than the one the gate meant to report.

Recorded seven times in this store (`feedback-repo-gate-pre-evaluates-the-pending-commit-command`).
Prose stopped working at two, so this is the escalation - a signal at the moment of the mistake.

Hit 7 wrote no file at all: `git checkout -- <f> && git commit -F msg` chained a TREE-WRITING git
command in front of the verb. That shape is sharper than the lost-input one, because the gate reads
the tree BEFORE the restore runs, so it cannot be satisfied in one command however often it is
retried.

NON-BLOCKING by construction: it emits `additionalContext` and exits 0. Blocking here would add a
second block to a command that may be perfectly fine, and a hook must never wedge a turn.

The gated-verb scan runs over the command with HEREDOC BODIES STRIPPED, because a body is data: a
guard that reads it fires on prose documenting the very footgun it guards.
"""
from __future__ import annotations

import json
import re
import sys

# Shared with the other command-scanning guards - a heredoc body is DATA, not a command.
from shell_text import strip_heredoc_bodies

# Verbs a PreToolUse gate in this plugin can block. Deliberately short: a false nudge on a safe
# command teaches the reader to ignore the channel, which costs more than the miss it prevents.
# re.M matters: a NEWLINE separates statements just as `;` does, and the verb usually sits on its
# own line under a heredoc terminator. Without it the common shape is invisible.
# `gh pr create` is gated by this repo's own commit gate, so a body file written beside it is lost
# exactly like a commit message. Verified 2026-08-09 that it slipped through.
_GATED = re.compile(
    r"(?:^|[;&|]|\b(?:&&|\|\|)\s*)\s*(?:git\s+(?:commit|push|tag)|gh\s+pr\s+create)\b", re.M)

# A write that CREATES the file a later statement reads. Both shapes seen in practice.
_HEREDOC_TO_FILE = re.compile(r"""(?:^|[;&|]|\bcat\b)[^\n<>]*?>\s*(?P<f>[^\s;&|<>]+)\s*<<-?\s*['"]?\w+""")
_REDIRECT_TO_FILE = re.compile(r"""\b(?:printf|echo|tee)\b[^\n;&|]*?>\s*(?P<f>[^\s;&|<>]+)""")

# An INTERPRETER that writes with an API rather than a redirect - `python3 - <<PY ... PY` or
# `python3 -c '...'` calling open(f, "w") or Path(f).write_text(). There is no `>` to match, so the
# redirect patterns above never see it, and this is a shape used constantly for exactly the job
# that gets lost: composing a commit message. Verified 2026-08-09 that it slipped through.
_INTERPRETER = re.compile(r"\b(?:python3?|perl|ruby|node)\b")
_WRITE_API = re.compile(
    r"""open\s*\([^)]*['"][wa]|\.write_text\s*\(|\bwriteFileSync\b|\bwrite_bytes\s*\(""")


def writes_via_interpreter(command: str) -> bool:
    """True when an interpreter in this command writes a file through an API, not a redirect.

    Scanned over the RAW command, bodies included - asymmetric to the gated-verb scan on purpose.
    The write LIVES in the heredoc body, so stripping bodies here would blind the check; the verb
    scan strips them because prose must not be able to fake a verb.
    """
    text = command or ""
    return bool(_INTERPRETER.search(text) and _WRITE_API.search(text))


# Git subcommands that change what a gate SEES. There are two families, because repo-gate reads
# `git diff --name-only origin/master` PLUS `git ls-files --others`: its verdict moves with the
# WORKING TREE, and equally with the `origin/master` REF it compares against. A `git fetch` writes
# no file at all and still invalidates the answer.
#
# `add` is deliberately absent: it touches the index rather than the working tree, losing it to a
# block produces no confusing missing-input error (the retry simply re-adds), and
# `git add ... && git commit` is the single most common idiom before a commit - nudging on it would
# train the reader to ignore the channel, which costs more than the miss.
_TREE_VERBS = ("checkout", "restore", "switch", "reset", "stash", "clean", "rm", "mv",
               "merge", "rebase", "cherry-pick", "revert", "am", "apply", "clone", "worktree")
_REF_VERBS = ("fetch",)   # moves origin/master without touching the working tree
_BOTH_VERBS = ("pull",)   # merges into the working tree AND moves the ref
# Longest-first, so a short alternative can never shadow a longer one sharing its prefix.
_PREP_VERBS = tuple(sorted(_TREE_VERBS + _REF_VERBS + _BOTH_VERBS, key=len, reverse=True))
_TREE_WRITING_GIT = re.compile(
    r"(?:^|[;&|]|\b(?:&&|\|\|)\s*)\s*git\s+(?P<verb>" + "|".join(_PREP_VERBS) + r")\b", re.M)


def _mechanism(verb: str) -> str:
    """How this verb invalidates the gate's reading - named precisely, so the nudge stays credible."""
    if verb in _BOTH_VERBS:
        return "changes the working tree and moves `origin/master`, the ref the gate compares against"
    if verb in _REF_VERBS:
        return "moves `origin/master`, the ref the gate compares against"
    return "changes the working tree"


def tree_prep_before_gate(command: str):
    """The tree-writing git verb that PRECEDES a gated verb in this command, or None.

    Scanned with heredoc bodies stripped, like the gated-verb scan: a git command is a command, so
    prose documenting this footgun must not be able to trip it.

    Order is load-bearing. A cleanup AFTER a commit is not prep for it, and nudging on that would be
    a false positive on an ordinary sequence.
    """
    text = strip_heredoc_bodies(command or "")
    gate = _GATED.search(text)
    if not gate:
        return None
    for m in _TREE_WRITING_GIT.finditer(text):
        if m.start() < gate.start():
            return m.group("verb")
    return None


def written_files(command: str):
    """Files this command CREATES, in order. Heredoc openers count; the bodies are not scanned."""
    out = []
    for rx in (_HEREDOC_TO_FILE, _REDIRECT_TO_FILE):
        for m in rx.finditer(command or ""):
            f = m.group("f")
            if f and f not in out:
                out.append(f)
    return out


def notice(command):
    """The warning text when this command co-locates prep with a gated verb, else None."""
    if not command or not isinstance(command, str):
        return None
    written = written_files(command)
    if written or writes_via_interpreter(command):
        # Strip bodies BEFORE looking for the gated verb: a heredoc that merely documents
        # `git commit` is prose, and nudging on it is how a guard blocks its own documentation.
        if _GATED.search(strip_heredoc_bodies(command)):
            what = ", ".join(written) if written else "a file (written by an interpreter, not a redirect)"
            return (
                "This command WRITES %s and then runs a gated verb (git commit/push/tag, gh pr "
                "create) in the SAME command. A PreToolUse gate judges the whole command before "
                "any statement runs, so if it blocks, that file is never written and the retry "
                "fails on a missing input - pointing at the wrong cause. Write the file in its OWN "
                "earlier command, then run the gated verb. (Recorded seven times: "
                "feedback-repo-gate-pre-evaluates-the-pending-commit-command.)"
                % what
            )
    verb = tree_prep_before_gate(command)
    if verb:
        return (
            "This command runs `git %s`, which %s, and then a gated verb (git commit/push/tag, gh "
            "pr create) in the SAME command. A PreToolUse gate judges the whole command before any "
            "statement runs, so it reads its answer BEFORE your `git %s` - which means this shape "
            "can never satisfy the gate however many times you retry it, and a block discards the "
            "prep too. Run the prep in its OWN earlier command, then the gated verb. (Recorded "
            "seven times: feedback-repo-gate-pre-evaluates-the-pending-commit-command.)"
            % (verb, _mechanism(verb), verb)
        )
    return None


def main(raw=None) -> int:
    """Read the hook event, emit additionalContext when the shape matches. Always exits 0."""
    try:
        payload = json.loads(raw if raw is not None else sys.stdin.read() or "{}")
    except (ValueError, TypeError):
        return 0
    if not isinstance(payload, dict) or payload.get("tool_name") != "Bash":
        return 0
    tool_input = payload.get("tool_input")
    command = tool_input.get("command") if isinstance(tool_input, dict) else None
    try:
        text = notice(command)
    except Exception:  # noqa: BLE001 - a nudge must never wedge a turn
        return 0
    if not text:
        return 0
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                             "additionalContext": text}}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
