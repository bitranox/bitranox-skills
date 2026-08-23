"""PostToolUse: after a push that LANDED, say which sha is now building and how to watch it.

Why this exists as a hook rather than as prose: the rule already exists in prose. The tree-top
`CLAUDE.md` carries "After pushing: watch CI", and its own applicability test - does this repo have
a `.github/workflows/`? - says it binds. Replaying this project's own transcript corpus priced how
far that gets:

    160 transcripts, 123 `git push` calls
     70 followed by a CI check, 53 not      -> 57% watched

So the channel exists and misses roughly two pushes in five. This hook is the deterministic half.
It cannot block (PostToolUse exit 2 only shows stderr; the tool already ran), so it does the part a
nudge is good at - arriving with the sha already resolved and the command already written - while
`ci-watch-gate.py` supplies the part a nudge cannot.

Both directions live here on purpose. The same hook that RECORDS a push also CLEARS the record when
it sees the CI actually being watched, so the two halves cannot drift into disagreeing about what
"watched" looks like.

A push is only recorded when it demonstrably LANDED. The test is local and needs no network: after
a successful push the remote-tracking ref has moved, so `HEAD` and `@{u}` agree. A push that failed
leaves the tracking ref behind and is not recorded - which matters because the usual shape here is
`git push 2>&1 | tail -3`, a pipeline that exits 0 whatever git did, so the exit code is not
evidence and the output is not parsed.

Exits 0 always, and emits nothing when it has no opinion.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import ci_watch_state as state
from shell_text import is_shell_tool, mask_data_regions

__all__ = ["main", "notice"]

_BYPASS_ENV = "BITRANOX_CI_WATCH"

# `git push`, allowing the option forms that carry their own argument before the subcommand.
_PUSH = re.compile(r"\bgit\s+(?:(?:-C|-c|--git-dir|--work-tree)[= ]\S+\s+)*push\b")
# A push that starts no CI run: nothing is uploaded, or a ref is being removed.
_NOT_A_BUILD = re.compile(r"--dry-run\b|--delete\b|\bpush\s+--delete\b")
# What looking at CI actually looks like in the record.
_WATCHING = re.compile(r"ci_wait\.py|ci_triage\.py|\bgh\s+run\s+(?:watch|list|view)\b|\bgh\s+pr\s+checks\b")

_CI_WAIT = Path(__file__).resolve().parent.parent / "skills" / "compuse-toolbox" / "scripts" / "ci_wait.py"


# `git -C <dir> push` is the shape the corpus is full of, and its repo is NOT the call's cwd.
_DASH_C = re.compile(r"\bgit\b(?:\s+-c[= ]\S+)*\s+-C[= ]\s*(\S+)")
# A path that came from an expansion cannot be resolved from the text; guessing is how the wrong
# repository gets asked. These are checked on the RAW token, at the masked token's own offsets.
_UNRESOLVABLE = ("$", "`", '"', "'")


def _repo_dir(command: str, cwd: str) -> str | None:
    """Which repository this push actually targets, or None when the text cannot say.

    Structure is read from the masked form; the VALUE is then taken from the raw text at the same
    offsets, because masking preserves length. Comparing values on the masked form would decide the
    path by its filler, not by what it says.
    """
    found = _DASH_C.search(mask_data_regions(command))
    if not found:
        return cwd
    token = command[found.start(1):found.end(1)]
    if not token or any(ch in token for ch in _UNRESOLVABLE):
        return None
    try:
        return str((Path(cwd) / token).resolve())
    except (OSError, ValueError):
        return None


def _git(args: list[str], cwd: str) -> str | None:
    """Run a read-only git command, returning stripped stdout or None. Never raises."""
    try:
        done = subprocess.run(["git", *args], cwd=cwd, capture_output=True,
                              text=True, encoding="utf-8", errors="replace", timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout.strip() if done.returncode == 0 else None


def _landed_sha(cwd: str) -> str | None:
    """The pushed commit, but only if the push actually landed.

    `--verify -q` is not decoration: a bare `git rev-parse` hands an unresolvable name straight
    back and exits 0, so a comparison built on it succeeds against a string that was never a commit.
    """
    head = _git(["rev-parse", "--verify", "-q", "HEAD"], cwd)
    upstream = _git(["rev-parse", "--verify", "-q", "@{u}"], cwd)
    if not head or not upstream or head != upstream:
        return None
    return head if re.fullmatch(r"[0-9a-f]{40}", head) else None


def _has_workflows(cwd: str) -> bool:
    """Does this repo run CI at all? The same test the tree-top rule states for itself."""
    root = _git(["rev-parse", "--show-toplevel"], cwd)
    if not root:
        return False
    try:
        workflows = Path(root) / ".github" / "workflows"
        return workflows.is_dir() and any(workflows.glob("*.y*ml"))
    except OSError:
        return False


def notice(command, cwd: str = "") -> tuple[str, str, str, str] | None:
    """The (text, sha, branch, repo) to record for this command, or None if it is not a landed push.

    Returns the sha it resolved rather than making the caller resolve it again: every lookup here
    is a subprocess, and recomputing them is how the two halves drift into disagreeing about which
    commit was pushed.
    """
    if not isinstance(command, str) or not command.strip():
        return None
    # Read STRUCTURE from the masked form so a command merely quoting "git push" cannot trigger it,
    # then take VALUES from the real repo rather than from the text.
    masked = mask_data_regions(command)
    if not _PUSH.search(masked) or _NOT_A_BUILD.search(masked):
        return None
    repo = _repo_dir(command, cwd) if cwd else None
    if not repo or not _has_workflows(repo):
        return None
    sha = _landed_sha(repo)
    if not sha:
        return None
    branch = _git(["rev-parse", "--abbrev-ref", "HEAD"], repo) or "HEAD"
    text = ("CI is now running for the push you just made: %s on %s.\n"
            "Watch it before moving on - this repo's CI blocks on every cell:\n"
            "    uv run %s --sha %s\n"
            "Exit 0 every run passed, 1 something failed, 2 could not tell."
            % (sha[:12], branch, _CI_WAIT, sha))
    return text, sha, branch, repo


def main(raw: str | None = None) -> int:
    """Record a landed push, or clear the record when CI is being watched. Always exits 0."""
    try:
        event = json.loads(raw if raw is not None else sys.stdin.read() or "{}")
    except (ValueError, TypeError, OSError):
        return 0
    if not isinstance(event, dict) or not is_shell_tool(event.get("tool_name")):
        return 0
    if os.environ.get(_BYPASS_ENV):
        return 0

    tool_input = event.get("tool_input")
    command = tool_input.get("command") if isinstance(tool_input, dict) else None
    cwd = event.get("cwd") or ""
    key = state.session_key(event)
    session = event.get("session_id") or ""
    if not isinstance(command, str):
        return 0

    try:
        masked = mask_data_regions(command)
        if _WATCHING.search(masked):
            state.clear_session(key, session)
            return 0
        found = notice(command, cwd)
        if not found:
            return 0
        text, sha, branch, repo = found
        state.record_push(key, session, sha, repo=repo, branch=branch)
    except Exception:  # noqa: BLE001 - a nudge must never wedge a turn
        return 0

    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse",
                                             "additionalContext": text}}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
