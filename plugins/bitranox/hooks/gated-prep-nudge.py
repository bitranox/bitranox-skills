#!/usr/bin/env python3
"""Warn when a gated verb shares one Bash command with the prep that produces its input.

A PreToolUse gate judges the WHOLE command before any statement runs. So when a single command both
writes a file (a heredoc, a redirect) and then runs a verb a gate may block, a block discards the
write too: the retry fails on a missing `-F` input and points at the wrong cause, which is a
different and much more confusing failure than the one the gate meant to report.

Recorded eight times in this store (`feedback-repo-gate-pre-evaluates-the-pending-commit-command`).
Prose stopped working at two, so this is the escalation - a signal at the moment of the mistake.

Hit 7 wrote no file at all: `git checkout -- <f> && git commit -F msg` chained a TREE-WRITING git
command in front of the verb. That shape is sharper than the lost-input one, because the gate reads
the tree BEFORE the restore runs, so it cannot be satisfied in one command however often it is
retried.

NON-BLOCKING by construction: it emits `additionalContext` and exits 0. Blocking here would add a
second block to a command that may be perfectly fine, and a hook must never wedge a turn.

Hit 8 tested that choice and CONFIRMED it, so do not re-open it without a new signal. The nudge
fired correctly on that command; what it could not do is arrive first. `additionalContext` reaches
the model in the same turn as the tool result, so a non-blocking PreToolUse hook can only ever
EXPLAIN a block, never prevent one - which leaves a `permissionDecision: deny` as the only rung
above this one. Replaying every `Bash` tool_use command in the transcript corpus through `notice()`
and joining each to whether a gate actually blocked it prices that rung:

    60,632 commands over 1,494 transcripts
    whole hook   569 fires (0.94%)   23 gate-blocked   deny precision  4.0%
    write arm    497 fires           21 gate-blocked   deny precision  4.2%
    tree arm      68 fires            1 gate-blocked   deny precision  1.5%

A deny would block 532 commands that completed fine to prevent 23 confusing ones, and the round
trip it saves is the round trip it imposes. Narrowing it to the tree arm is worse, not better: that
arm was believed to be the shape that can never satisfy the gate, and 67 of its 68 real firings
succeeded. Re-run the measurement rather than the argument.

Hit 9 proposed the obvious refinement - keep the deny but make it TARGET-AWARE, denying a write
into the repo tree while a write into the session scratchpad stays a nudge, on the reasoning that
the scratchpad case is recoverable and a blanket deny would over-fire on it. Measured on the same
corpus (1551 transcripts, 63,217 commands, control arm first to prove the harness reproduces the
numbers above):

    whole hook (control)              604 fires (0.955%)   25 blocked   precision 4.14%
    repo-tree write -> DENY           198 fires (0.313%)    8 blocked   precision 4.04%
    complement, would stay a nudge    326 fires             15 blocked  precision 4.60%

The split does not help, and it is INVERTED against its own premise: the writes it calls
recoverable-so-keep-nudging are MORE likely to be a real block (4.60%) than the ones it would
escalate to a hard deny (4.04%). A deny on that arm blocks 187 commands that completed fine to
prevent 8. The scratchpad/repo distinction simply does not track whether the gate fires, so it
cannot make a deny safe. The DENY branch stays closed on this evidence too.

Note for anyone re-testing it: an interpreter write (`open(f, "w")`, `write_text`) exposes no
filename, so a target-aware rule cannot classify that arm at all - and that is precisely the shape
used to compose a commit message, the job that gets lost. Any future target-aware proposal has to
say what it does there before its numbers mean anything.

What that closes is the DENY branch, not the question. One mechanism was never priced: making
repo-gate LOOK AHEAD instead. Every blocked command CONTAINS the bump the gate blocks for, so a
gate that recognised it would remove the class rather than warn about it, at no cost to the 532
legitimate calls. It is unbuilt because a gate trusting a textual promise about what a command
will DO is a worse failure mode than the one it fixes - prose mentioning a bump, or a bump to the
wrong value, would pass - so it needs a design pass and its own measurement, not a prototype.

The GENERAL rule these two closures are instances of lives in the `bitranox:meta-claude-hooks`
skill, under "Before you escalate a nudge to a block, price it": measure firing rate and precision
by replaying the real corpus, run a control arm first, price the variant actually proposed, and say
what the rule cannot classify. The figures stay HERE and the method stays THERE - no number appears
in both, so they cannot disagree - but they move TOGETHER: a third escalation proposal should update
both, and `tests/test_gated_prep_nudge.py` asserts each still points at the other so a rename fails
the suite instead of rotting quietly.

The gated-verb scan runs over the command with HEREDOC BODIES STRIPPED, because a body is data: a
guard that reads it fires on prose documenting the very footgun it guards.
"""
from __future__ import annotations

import json
import re
import sys

# Shared with the other command-scanning guards - a heredoc body is DATA, not a command.
from shell_text import is_git_verb, is_shell_tool, iter_segments, strip_heredoc_bodies

# Verbs a PreToolUse gate in this plugin can block. Deliberately short: a false nudge on a safe
# command teaches the reader to ignore the channel, which costs more than the miss it prevents.
# re.M matters: a NEWLINE separates statements just as `;` does, and the verb usually sits on its
# own line under a heredoc terminator. Without it the common shape is invisible.
# `gh pr create` is gated by this repo's own commit gate, so a body file written beside it is lost
# exactly like a commit message. Verified 2026-08-09 that it slipped through.
_GATED_VERBS = frozenset({"commit", "push", "tag"})
_GH_PR_CREATE = re.compile(r"^\s*(?:\w+=\S+\s+)*gh\b.*\bpr\b.*\bcreate\b")


def _gated_start(text, tool_name="Bash"):
    """Offset of the first gated verb in `text`, or None.

    The verb is identified by TOKEN WALK, not by a regex requiring it to sit next to `git`: the
    old pattern could not see `git -C <path> commit`, so this nudge stayed silent on a shape the
    gate it exists to explain really does block. Position is returned rather than a bare yes,
    because a write AFTER the verb is not prep for it.
    """
    for start, seg in iter_segments(text, tool_name):
        body = seg.lstrip("( \t").lstrip()
        if is_git_verb(body, _GATED_VERBS) or _GH_PR_CREATE.match(body):
            return start + (len(seg) - len(body))
    return None

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
# Three verbs are deliberately absent, each for its own reason:
#
# `add` touches the index rather than the working tree, losing it to a block produces no confusing
# missing-input error (the retry simply re-adds), and `git add ... && git commit` is the single most
# common idiom before a commit - nudging on it would train the reader to ignore the channel.
#
# `clone` and `worktree` normally write OUTSIDE the tree the gate inspects (`git clone <url> /tmp/x`,
# `git worktree add ../wt`), so they change nothing repo-gate reads. Telling an inside-the-repo
# target from an outside one would take real path parsing, which a nudge does not earn.
#
# In every case a false nudge costs more than the miss it would have prevented.
_TREE_VERBS = ("checkout", "restore", "switch", "reset", "stash", "clean", "rm", "mv",
               "merge", "rebase", "cherry-pick", "revert", "am", "apply")
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
    gate_at = _gated_start(text)
    if gate_at is None:
        return None
    for m in _TREE_WRITING_GIT.finditer(text):
        if m.start() < gate_at:
            return m.group("verb")
    return None


def written_files(command: str):
    """Files this command CREATES, in order. Heredoc openers count; the bodies are not scanned.

    A `/dev/` target is not a file this command creates: `>/dev/null` discards output rather than
    producing an input for a later statement, so losing it to a block costs nothing and there is
    nothing to warn about. Counting it fired on the very common `cmd >/dev/null && git push`
    shape - 7 of 604 real firings in the transcript corpus, every one of them a false nudge.
    """
    out = []
    for rx in (_HEREDOC_TO_FILE, _REDIRECT_TO_FILE):
        for m in rx.finditer(command or ""):
            f = m.group("f")
            if f and f not in out and not f.strip("'\"").startswith("/dev/"):
                out.append(f)
    return out


def notice(command, tool_name="Bash"):
    """The warning text when this command co-locates prep with a gated verb, else None."""
    if not command or not isinstance(command, str):
        return None
    written = written_files(command)
    if written or writes_via_interpreter(command):
        # Strip bodies BEFORE looking for the gated verb: a heredoc that merely documents
        # `git commit` is prose, and nudging on it is how a guard blocks its own documentation.
        if _gated_start(strip_heredoc_bodies(command), tool_name) is not None:
            what = ", ".join(written) if written else "a file (written by an interpreter, not a redirect)"
            return (
                "This command WRITES %s and then runs a gated verb (git commit/push/tag, gh pr "
                "create) in the SAME command. A PreToolUse gate judges the whole command before "
                "any statement runs, so if it blocks, that file is never written and the retry "
                "fails on a missing input - pointing at the wrong cause. Write the file in its OWN "
                "earlier command, then run the gated verb. (Recorded eight times: "
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
            "eight times: feedback-repo-gate-pre-evaluates-the-pending-commit-command.)"
            % (verb, _mechanism(verb), verb)
        )
    return None


def main(raw=None) -> int:
    """Read the hook event, emit additionalContext when the shape matches. Always exits 0."""
    try:
        payload = json.loads(raw if raw is not None else sys.stdin.read() or "{}")
    except (ValueError, TypeError):
        return 0
    if not isinstance(payload, dict) or not is_shell_tool(payload.get("tool_name")):
        return 0
    tool_input = payload.get("tool_input")
    command = tool_input.get("command") if isinstance(tool_input, dict) else None
    try:
        text = notice(command, payload.get("tool_name"))
    except Exception:  # noqa: BLE001 - a nudge must never wedge a turn
        return 0
    if not text:
        return 0
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                             "additionalContext": text}}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
