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
from shell_text import commands_only, is_shell_tool

__all__ = ["main", "notice"]

_BYPASS_ENV = "BITRANOX_CI_WATCH"

# `git push`, allowing the option forms that carry their own argument before the subcommand.
_PUSH = re.compile(r"\bgit\s+(?:(?:-C|-c|--git-dir|--work-tree)[= ]\S+\s+)*push\b")
# A push that starts no CI run: nothing is uploaded, or a ref is being removed.
_NOT_A_BUILD = re.compile(r"--dry-run\b|--delete\b|\bpush\s+--delete\b")
# What looking at CI actually looks like in the record.
_WATCHING = re.compile(r"ci_wait\.py|ci_triage\.py|\bgh\s+run\s+(?:watch|list|view)\b|\bgh\s+pr\s+checks\b")

_CI_WAIT = Path(__file__).resolve().parent.parent / "skills" / "compuse-toolbox" / "scripts" / "ci_wait.py"

# Pushing tags in bulk, versus naming refs explicitly. A tag push builds the TAG ref, which is a
# different run from its branch's - and at release time it is the run that matters most.
_BULK_TAGS = re.compile(r"--tags\b|--follow-tags\b")
# Everything after `push`, so the refspecs can be read off it. Options are dropped, not guessed at.
_AFTER_PUSH = re.compile(r"\bpush\b(?P<rest>[^\n;|&]*)")


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
    found = _DASH_C.search(commands_only(command))
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


_SCP_LIKE = re.compile(r"^[^/]+@([^:/]+):")


def _gh_hosts() -> set[str]:
    """The forges `gh` can actually query: github.com plus any enterprise host it holds auth for.

    Read with a regex rather than a YAML parser because a hook may not provision dependencies.
    Only the top-level keys are wanted and they are the sole unindented lines in hosts.yml, so
    the shapes a regex gets wrong are not present in this file.
    """
    hosts = {"github.com"}
    base = os.environ.get("GH_CONFIG_DIR") or str(Path.home() / ".config" / "gh")
    try:
        text = (Path(base) / "hosts.yml").read_text(encoding="utf-8", errors="replace")
    except (OSError, RuntimeError, ValueError):
        return hosts
    hosts.update(m.group(1) for m in re.finditer(r"^([A-Za-z0-9._-]+):", text, re.M))
    return hosts


def _url_host(url: str) -> str | None:
    """The host named by a git remote URL, or None when it names none (a filesystem path)."""
    scp = _SCP_LIKE.match(url)
    if scp:
        return scp.group(1)
    if "://" not in url:
        return None
    authority = url.split("://", 1)[1].split("/", 1)[0]
    return authority.rsplit("@", 1)[-1].split(":", 1)[0] or None


def _ssh_hostname(alias: str) -> str | None:
    """What ssh resolves an alias to, so a `Host gh` block is not mistaken for a foreign forge.

    Offline: `ssh -G` only reads the config, it opens no connection.
    """
    try:
        done = subprocess.run(["ssh", "-G", alias], capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    if done.returncode != 0:
        return None
    for line in done.stdout.splitlines():
        if line.lower().startswith("hostname "):
            return line.split(None, 1)[1].strip() or None
    return None


def _push_remote(command: str, repo: str) -> str | None:
    """The remote this push targets: the first bare word after `push`, else the branch's
    configured remote, else `origin`, which is git's own fallback."""
    rest = _AFTER_PUSH.search(commands_only(command))
    if rest:
        span = rest.span("rest")
        words = [w for w in command[span[0]:span[1]].split() if not w.startswith("-")]
        if words and not any(ch in words[0] for ch in _UNRESOLVABLE):
            return words[0]
    branch = _git(["rev-parse", "--abbrev-ref", "HEAD"], repo)
    if branch and branch != "HEAD":
        configured = _git(["config", "--get", "branch.%s.remote" % branch], repo)
        if configured:
            return configured
    return "origin"


def _targets_a_watchable_forge(command: str, repo: str) -> bool:
    """Will the forge this push LANDED on actually run the workflows `_has_workflows` found?

    `_has_workflows` asks whether the repo has CI files, which a fork that vendors upstream's
    `.github/workflows` passes even when its own pushes go to a forge with no Actions at all.
    The nudge then points at `gh`, which resolves the checkout through its remotes and asks a
    repository that has never seen the sha, so the watch can never terminate and the gate can
    never be satisfied. Measured on a fork that vendors upstream's workflows and pushes to a
    private Gitea, while `gh repo view` answers the UPSTREAM repository: the API returns 422
    "No commit found for SHA" and `gh run list --commit` returns zero rows.

    Fails toward KEEPING the nudge. Only a host we positively resolved AND that `gh` cannot
    query counts as a skip, because a lost nudge is silent while a spurious one is only noise.
    A remote naming no host at all (a filesystem path) keeps the nudge: it is what the tests
    use to stand in for a real remote, so reading it as "no CI" would decide semantics from a
    fixture's convenience.
    """
    remote = _push_remote(command, repo)
    if not remote:
        return True
    looks_like_url = "://" in remote or bool(_SCP_LIKE.match(remote))
    url = remote if looks_like_url else _git(["remote", "get-url", remote], repo)
    if not url:
        return True
    host = _url_host(url)
    if host is None:
        return True
    known = _gh_hosts()
    if host in known:
        return True
    resolved = _ssh_hostname(host)
    return bool(resolved) and resolved in known


def _resolve_ref(repo: str, name: str) -> tuple[str, str] | None:
    """(sha, display) for a ref name, tags before branches. None when it does not resolve."""
    for prefix, kind in (("refs/tags/", "tag"), ("refs/heads/", "branch")):
        sha = _git(["rev-parse", "--verify", "-q", prefix + name + "^{commit}"], repo)
        if sha and re.fullmatch(r"[0-9a-f]{40}", sha):
            return sha, ("%s %s" % (kind, name))
    return None


_STATEMENT_SEP = re.compile(r"&&|\|\||[;\n]")


def _statement_around(text: str, index: int) -> str:
    """The single statement containing `index`, so a flag in a NEIGHBOURING statement is not read
    as belonging to this one. `git push --dry-run x && git push x` is one dry run and one real
    push, and matching `--dry-run` against the whole command silenced the second."""
    start = 0
    for m in _STATEMENT_SEP.finditer(text):
        if m.start() > index:
            return text[start:m.start()]
        start = m.end()
    return text[start:]


def _pushed_ref(command: str, repo: str) -> tuple[str, str] | None:
    """What this push actually built: (sha, display), or None to fall back to the branch test.

    A refspec is read from the text after `push`; a `src:dst` pair is resolved by its SOURCE, which
    is the object being sent. Bulk `--tags` names no ref, so the newest local tag by creation date
    stands in - the tag just cut is the one whose run is wanted.
    """
    rest = _AFTER_PUSH.search(commands_only(command))
    if not rest:
        return None
    span = rest.span("rest")
    words = [w for w in command[span[0]:span[1]].split() if not w.startswith("-")]
    # The first bare word is the remote; the rest are refspecs.
    for spec in words[1:]:
        if any(ch in spec for ch in _UNRESOLVABLE):
            return None
        source = spec.split(":", 1)[0].replace("refs/tags/", "").replace("refs/heads/", "")
        found = _resolve_ref(repo, source) if source and source != "HEAD" else None
        if found:
            return found
    if _BULK_TAGS.search(commands_only(command)):
        # In `for-each-ref` the LAST --sort key is the PRIMARY one (measured, not assumed), so
        # this reads as: newest by creation date, ties broken by version order. Creation date
        # alone is not enough - tags cut in the same second tie, and the fallback is plain
        # alphabetical, where v10.0.0 sorts between v1.0.0 and v2.0.0.
        newest = _git(["for-each-ref", "--sort=-v:refname", "--sort=-creatordate", "--count=1",
                       "--format=%(refname:short)", "refs/tags"], repo)
        if newest:
            return _resolve_ref(repo, newest)
    return None


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
    masked = commands_only(command)
    # _NOT_A_BUILD must be judged on the push STATEMENT, not the whole command: a dry run in
    # one statement silenced the nudge for a genuine push in another.
    # EVERY push, not the first: scoping the flag correctly but then selecting the first match
    # still lets `git push --dry-run x && git push x` silence itself, because the first match IS
    # the dry run. The nudge is owed if ANY statement carries a real build push.
    if not any(not _NOT_A_BUILD.search(_statement_around(masked, m.start()))
               for m in _PUSH.finditer(masked)):
        return None
    repo = _repo_dir(command, cwd) if cwd else None
    if not repo or not _has_workflows(repo):
        return None
    # Having workflow FILES is not the same as pushing somewhere that runs them.
    if not _targets_a_watchable_forge(command, repo):
        return None
    pushed = _pushed_ref(command, repo)
    if pushed:
        sha, branch = pushed
    else:
        # No ref named, so this is the ordinary `git push`: the branch landed-test applies.
        sha = _landed_sha(repo)
        if not sha:
            return None
        branch = _git(["rev-parse", "--abbrev-ref", "HEAD"], repo) or "HEAD"
    text = ("CI is now running for the push you just made: %s (%s).\n"
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
        masked = commands_only(command)
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
