#!/usr/bin/env python3
"""PreToolUse(Bash|PowerShell) guard against a known-always-broken git invocation:
`git rev-parse --short` with two or more revisions.

`--short` abbreviates a SINGLE revision; passing two or more makes git fail with
`fatal: Needed a single revision` (exit 128), a confusing error that is easy to
dismiss as a transient quirk. It is deterministic: drop `--short` to print full
hashes for multiple revs, or call rev-parse once per rev. This guard blocks the
broken form before it runs and names the fix, so the error never has to be
re-diagnosed.

A second, ADVISORY check covers a pathspec `git commit` (`git commit -m x -- a b`, or the paths
without `--`) over a STAGED-ONLY change. A pathspec commit records the WORKTREE copy of every
named path, so whatever the index held for that path and the worktree does not is discarded.
Measured in temp repositories: a staged `git rm --cached p` is re-added when another path rides
the same pathspec (exit 0, nothing said), a staged `update-index --chmod=+x` under
core.fileMode=false is committed as 100644, and a partial `add -p` is replaced by the whole file.
The index is read with git before the commit runs; a `git rm --cached` / `update-index` earlier in
the SAME command has not run yet, so those are matched by their operands instead. Over staged state
that already existed it is advisory, not a block: committing the whole worktree file can be the
intent. An index edit made earlier in the SAME command and then discarded by it is REFUSED: that is
never the intent, and the advisory alone let `git update-index --chmod=+x f && git commit -- f`
land 100644 in three repos in a row (2026-10-23). Contrib #35 has the corpus numbers.

A third check REFUSES `git check-ignore -q` / `--quiet` with two or more paths: git exits 128
`--quiet is only valid with a single pathname`, and a "non-zero means not ignored" reading takes
that as an answer for every path.

A fourth, ADVISORY check covers `@{u}` / `@{upstream}` (any case, bare or as `<branch>@{u}`) used as
a revision by a git command that takes one (log, rev-list, diff, reset, ...). A branch cut from a
remote-tracking ref (`git checkout -b feat origin/master`, `git worktree add -b feat <wt>
origin/master`) gets THAT ref as its upstream, and `git push origin feat` without `-u` leaves it
so; `git log @{u}..` then lists every topic commit as unpushed although origin/feat holds them
(measured 2026-11-06). The guard reads the branch and its upstream in the repo the git call runs in
(`git -C`, a leading `cd`, else the event cwd) and, when the upstream's branch name differs from the
local one, says so in one line and whether `<remote>/<branch>` exists locally. Detached HEAD, no
upstream, or matching names: silent.

Pure standard library. Reads the PreToolUse event JSON on stdin. Exit 2 blocks the
call and shows stderr to the model; the advisory is `additionalContext` on stdout with exit 0;
every other path (including any error) exits 0 so a broken guard never wedges a turn.

Decisions:
    - The `@{u}` check advises a branch that tracks a differently named branch ON PURPOSE too. Why:
      the deliberate setup and the accident are the identical configuration, so silence on one is
      silence on the other, and one line costs a reader who chose it nothing. Evidence: argued.
      Reopen if: a replay over real transcripts shows it firing mostly on deliberate setups.
      Pinned by: tests/test_git_footgun_guard.py::test_upstream_of_another_name_is_advised
    - It advises, never blocks. Why: comparing against a differently named upstream can be the
      intent (a topic measured against master), and only the reader knows. Evidence: argued.
      Reopen if: a recorded case where the advisory was read and the wrong-branch count still
      decided something. Pinned by: tests/test_git_footgun_guard.py::test_upstream_of_another_name_is_advised
    - Only revision-taking verbs (`_REV_VERBS`) are read for `@{u}`. Why: a commit message, tag or
      stash text may mention `@{u}` without naming a revision. Evidence: argued.
      Reopen if: a revision-taking verb missing from `_REV_VERBS` turns up in a miss.
      Pinned by: tests/test_git_footgun_guard.py::test_upstream_text_that_is_no_revision_is_silent
    - Rejected: reading `@{u}` in any git statement. Why: the message-taking verbs above.
      Reopen if: never on its own; widen `_REV_VERBS` instead.
"""
import json
import os
import re
import subprocess
import sys

import shell_text

# Shared with the other command-scanning guards: a heredoc body is DATA, and scanning it makes a
# guard fire on prose that merely mentions the footgun it guards. Re-exported so callers and tests
# can keep reaching it as `git_footgun_guard.strip_heredoc_bodies`.
from shell_text import (
    argv_for_match,
    blank_heredoc_bodies,
    drop_redirections,
    git_verb_dir,
    git_verb_operands,
    iter_segments,
    strip_heredoc_bodies,
)

# Split a command line into statements so a rev-parse in one segment is judged
# on its own operands, not tokens from a neighbouring command.

_REV_PARSE = frozenset({"rev-parse"})


def _revparse_operands(toks: list[str]) -> list[str] | None:
    """Tokens after `rev-parse` when it is genuinely the git SUBCOMMAND.

    Returns None when this segment is not a `git rev-parse` invocation - e.g.
    `git commit -m "...git rev-parse --short A B..."`, where the words appear
    only inside an argument.

    The walk itself now lives in `shell_text.git_verb_operands`. It started here, and it was the
    only correct answer to "what git command is this?" in the plugin while three other callers
    each got it wrong in their own way - so it moved to where they could all reach it.
    """
    return git_verb_operands(toks, _REV_PARSE)


def broken_revparse(command: str, tool_name: str | None = None) -> bool:
    # iter_segments, not SEP.split: a statement can begin inside a command substitution,
    # and `A=$(git rev-parse ...)` runs a real git command. SEP does not break at `$(`, so
    # the verb walk saw `A=$(git` and found nothing - this guard stayed quiet on a shape
    # its own advisory nudge (git-revparse-nudge) already fires on.
    for _at, segment in iter_segments(strip_heredoc_bodies(command), tool_name):
        rest = _revparse_operands(argv_for_match(segment, tool_name))
        if rest is None:
            continue
        # A `2>/dev/null`, or its target when spaced (`2> /dev/null`), is no second revision.
        # Dropped from the split words, never by a regex over the raw text: that cut a quoted
        # target with a space (`2>"/tmp/a b"`) in two and left `b"` behind as a revision.
        rest = drop_redirections(rest)
        if not any(t == "--short" or t.startswith("--short=") for t in rest):
            continue
        # Operands are the non-option tokens after rev-parse (the revisions). Redirections are
        # already stripped, and a backgrounding `&` never gets here: iter_segments ends the
        # statement at it.
        operands = [t for t in rest if not t.startswith("-")]
        if len(operands) >= 2:
            return True
    return False


_CHECK_IGNORE = frozenset({"check-ignore"})
_QUIET = frozenset({"-q", "--quiet"})


def multi_path_quiet_check_ignore(command, tool_name=None):
    """True when a statement runs `git check-ignore -q` with two or more path operands.

    `--stdin` reads the paths from input, so it is never this shape. A bundled short form
    (`-qv`) carries the q too. Redirections are dropped before the paths are counted.
    """
    for argv in _statements(command, tool_name):
        operands = git_verb_operands(argv, _CHECK_IGNORE, tool_name or "Bash")
        if operands is None:
            continue
        operands = drop_redirections(operands)
        quiet = any(t in _QUIET or (t.startswith("-") and not t.startswith("--") and "q" in t)
                    for t in operands)
        if not quiet or "--stdin" in operands:
            continue
        paths = [t for t in operands if t == "-" or not t.startswith("-")]
        if len(paths) >= 2:
            return True
    return False


_COMMIT = frozenset({"commit"})
_RM = frozenset({"rm"})
_UPDATE_INDEX = frozenset({"update-index"})

# `git commit` options that take a separate VALUE, so the token after them is not a path.
_COMMIT_VALUE_OPTS = frozenset({
    "-m", "--message", "-F", "--file", "-C", "--reuse-message", "-c", "--reedit-message",
    "--author", "--date", "--fixup", "--squash", "-t", "--template", "--cleanup", "--trailer",
    "-S", "--gpg-sign", "--pathspec-from-file",
})
# With these the index is committed as well as (or instead of) the named paths, so no staged-only
# state is lost by the pathspec.
_INDEX_KEEPING = frozenset({"-i", "--include"})
_GLOB = re.compile(r"[*?\[]")
_GIT_SCOPE_VARS = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR")
_REGULAR = frozenset({"100644", "100755"})


def _commit_pathspec(operands):
    """The paths a `git commit` names, or [] when it names none (or keeps the index anyway)."""
    paths, index, after = [], 0, False
    while index < len(operands):
        token = operands[index]
        if after:
            paths.append(token)
        elif token == "--":
            after = True
        elif token in _INDEX_KEEPING or token.startswith("--pathspec-from-file"):
            return []
        elif token in _COMMIT_VALUE_OPTS:
            index += 1
        elif not token.startswith("-"):
            paths.append(token)
        index += 1
    return paths


def _statements(command, tool_name):
    for _at, segment in iter_segments(blank_heredoc_bodies(command or ""), tool_name):
        argv = argv_for_match(segment.strip().lstrip("(").strip(), tool_name or "Bash")
        if argv:
            yield argv


_UNTRACK = "a staged untrack (`git rm --cached`) will be re-added"


def _removed_paths(argv, tool_name):
    """The operands of a plain `rm` statement (`rm -f -- a b`, `sudo rm a`), normalised; else []."""
    at = shell_text.statement_program(argv, ("rm",), tool_name or "Bash")
    if at is None:
        return []
    paths, operands_only = [], False
    for token in argv[at + 1:]:
        if token == "--" and not operands_only:
            operands_only = True
        elif operands_only or not token.startswith("-"):
            paths.append(os.path.normpath(token))
    return paths


def _same_command_index_edits(command, tool_name):
    """{path: what} for `git rm --cached` / `git update-index --chmod` BEFORE the first commit.

    An untrack whose worktree file the same command also deletes (`rm f`) is dropped: the pathspec
    commit then records the deletion, which is what the untrack was for, so nothing is re-added.
    """
    edits, removed = {}, set()
    for argv in _statements(command, tool_name):
        if git_verb_operands(argv, _COMMIT, tool_name or "Bash") is not None:
            break
        removed.update(_removed_paths(argv, tool_name))
        rm = git_verb_operands(argv, _RM, tool_name or "Bash")
        if rm is not None and "--cached" in rm:
            for token in rm:
                if not token.startswith("-"):
                    edits[token] = _UNTRACK
        upd = git_verb_operands(argv, _UPDATE_INDEX, tool_name or "Bash")
        if upd is not None and any(t.startswith("--chmod=") for t in upd):
            for token in upd:
                if not token.startswith("-"):
                    edits[token] = "a staged mode change (`update-index --chmod`) will be dropped"
    return {path: what for path, what in edits.items()
            if not (what == _UNTRACK and os.path.normpath(path) in removed)}


def _git(repo, *args, data=False):
    env = {k: v for k, v in os.environ.items() if k not in _GIT_SCOPE_VARS}
    done = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=not data,
                          encoding=None if data else "utf-8", errors=None if data else "replace",
                          timeout=5, env=env, check=False)
    return done.stdout if done.returncode == 0 else None


def _entries(text):
    """{path: (mode, sha)} from NUL-separated `ls-files -s` / `ls-tree` records."""
    found = {}
    for record in (text or "").split("\0"):
        meta, _tab, path = record.partition("\t")
        fields = meta.split()
        if path and len(fields) >= 3:
            sha = fields[1] if len(fields[1]) >= 40 else fields[2]
            found[path] = (fields[0], sha)
    return found


def _worktree_entry(root, path, head, file_mode):
    """(mode, sha) a `git add` of the worktree copy would record, or None when it is gone."""
    full = os.path.join(root, path)
    if not os.path.isfile(full):
        return None
    sha = (_git(root, "hash-object", "--", path) or "").strip()
    if not file_mode:
        mode = head[0] if head else "100644"
    else:
        mode = "100755" if os.access(full, os.X_OK) else "100644"
    return mode, sha


def _state_losses(repo, paths):
    """[(path, what)] for named paths whose STAGED state differs from what the commit records."""
    root = (_git(repo, "rev-parse", "--show-toplevel") or "").strip()
    if not root:
        return []
    staged = _git(root, "diff", "--cached", "--no-renames", "--name-status", "-z", "--",
                  *[os.path.relpath(os.path.join(repo, p), root) for p in paths])
    if not staged:
        return []
    fields = staged.split("\0")
    pairs = [(fields[i], fields[i + 1]) for i in range(0, len(fields) - 1, 2)]
    # Windows has no exec bit to read (os.access(X_OK) is always True there), so the index mode is
    # what git keeps whatever core.fileMode says; reading it as a mode change would be invented.
    file_mode = os.name != "nt" and (
        _git(root, "config", "--bool", "core.fileMode") or "true").strip() != "false"
    losses = []
    for status, path in pairs:
        head = _entries(_git(root, "ls-tree", "-z", "HEAD", "--", path)).get(path)
        index = _entries(_git(root, "ls-files", "-s", "-z", "--", path)).get(path)
        worktree = _worktree_entry(root, path, head, file_mode)
        if status == "D":
            if worktree is not None:
                losses.append((path, _UNTRACK))
            continue
        if index is None or index[0] not in _REGULAR:
            continue
        if worktree is None:
            losses.append((path, "its staged content will be committed as a DELETION"))
        elif index[1] != worktree[1]:
            losses.append((path, "a partial stage will be replaced by the whole worktree file"))
        elif index[0] != worktree[0]:
            losses.append((path, "the staged mode %s will be committed as %s" % (index[0], worktree[0])))
    return losses


def _commit_paths(command, tool_name):
    """The literal (glob-free) paths the first `git commit` of `command` names, else []."""
    for argv in _statements(command, tool_name):
        commit = git_verb_operands(argv, _COMMIT, tool_name or "Bash")
        if commit is not None:
            return [p for p in _commit_pathspec(drop_redirections(commit)) if not _GLOB.search(p)]
    return []


def same_command_losses(command, tool_name=None):
    """[(path, what)] for index edits made earlier in `command` that its pathspec commit drops."""
    paths = _commit_paths(command, tool_name)
    if not paths:
        return []
    same = _same_command_index_edits(command, tool_name)
    return [(p, same[p]) for p in paths if p in same]


def pathspec_commit_losses(command, cwd, tool_name=None):
    """[(path, what)] a pathspec `git commit` in `command` would silently discard, else []."""
    paths = _commit_paths(command, tool_name)
    if not paths:
        return []
    losses = same_command_losses(command, tool_name)
    repo = git_verb_dir(command, cwd, _COMMIT, tool_name)
    if repo and os.path.isdir(repo):
        try:
            seen = {p for p, _what in losses}
            losses += [(p, w) for p, w in _state_losses(repo, paths) if p not in seen]
        except (OSError, subprocess.SubprocessError, ValueError):
            pass
    return losses


# Verbs that take a revision, so an `@{u}` operand is one. A message-taking verb (commit, tag,
# notes, stash) is left out on purpose: its `-m` text may mention `@{u}` without naming a revision.
_REV_VERBS = frozenset({
    "log", "rev-list", "rev-parse", "diff", "show", "reset", "rebase", "merge", "cherry",
    "cherry-pick", "shortlog", "range-diff", "branch", "checkout", "switch", "format-patch",
    "describe", "merge-base", "name-rev", "for-each-ref", "whatchanged", "difftool", "restore",
    "revert", "blame", "archive",
})
# git matches the `@{upstream}` / `@{u}` suffix case-insensitively (at_mark uses strncasecmp).
_UPSTREAM_MARK = re.compile(r"([A-Za-z0-9._/+-]*)@\{(?:u|upstream)\}", re.IGNORECASE)
_CURRENT = frozenset({"", "HEAD", "@"})


def _upstream_use(command, tool_name):
    """(verb, branch-or-"" for HEAD) of the first statement using `@{u}` as a revision, else None."""
    for argv in _statements(command, tool_name):
        for verb in _REV_VERBS:
            operands = git_verb_operands(argv, frozenset({verb}), tool_name or "Bash")
            if operands is None:
                continue
            for token in drop_redirections(operands):
                found = _UPSTREAM_MARK.search(token)
                if found:
                    # `HEAD...@{u}`: the ref is what follows the last range operator.
                    ref = found.group(1).split("..")[-1].lstrip(".")
                    return verb, "" if ref in _CURRENT else ref
            break
    return None


def _branch_upstream(repo, ref):
    """(branch, remote, upstream short name, upstream's branch name) or None when unknowable."""
    if ref:
        if _git(repo, "rev-parse", "--verify", "-q", "refs/heads/" + ref) is None:
            return None
        branch = ref
    else:
        branch = (_git(repo, "symbolic-ref", "-q", "--short", "HEAD") or "").strip()
    if not branch:
        return None
    line = (_git(repo, "for-each-ref", "--format=%(upstream:remotename)%09%(upstream:remoteref)"
                 "%09%(upstream:short)", "refs/heads/" + branch) or "").strip("\n")
    remote, _tab, rest = line.partition("\t")
    remote_ref, _tab, short = rest.partition("\t")
    if not short:
        return None
    return branch, remote, short, remote_ref.removeprefix("refs/heads/")


def foreign_upstream(command, cwd, tool_name=None):
    """One advisory line when `@{u}` in `command` names a branch of another name, else None."""
    use = _upstream_use(command, tool_name)
    if use is None:
        return None
    verb, ref = use
    repo = git_verb_dir(command, cwd, frozenset({verb}), tool_name)
    if not repo or not os.path.isdir(repo):
        return None
    found = _branch_upstream(repo, ref)
    if found is None or found[3] == found[0]:
        return None
    branch, remote, short, _name = found
    own = "%s/%s" % (remote if remote and remote != "." else "origin", branch)
    head = "UPSTREAM IS ANOTHER BRANCH: `@{u}` of `%s` is `%s`, not `%s`, so it counts against " \
           "that branch (and only as of the last fetch). " % (branch, short, own)
    if _git(repo, "rev-parse", "--verify", "-q", "refs/remotes/" + own) is not None:
        return head + ("`%s` exists locally: `git fetch`, then compare with it by name "
                       "(`git rev-list --left-right --count HEAD...%s`), or "
                       "`git branch --set-upstream-to=%s %s`." % (own, own, own, branch))
    return head + ("`%s` does not exist locally (never pushed, or not fetched): `git fetch`, "
                   "then compare with the branch you pushed by name." % own)


def _pathspec_advice(losses):
    listed = "\n".join("  - %s: %s" % (path, what) for path, what in losses)
    return ("PATHSPEC COMMIT OVER A STAGED-ONLY CHANGE: `git commit <paths>` records the WORKTREE "
            "copy of each named path, so it will discard what only the index holds:\n" + listed +
            "\nIf the staged state is what you meant, commit WITHOUT a pathspec after checking "
            "`git diff --cached --stat` lists only your paths. If this commit already ran, check "
            "`git show --stat HEAD` and restage + `git commit --amend --no-edit`.")


def _advise(notes):
    sys.stdout.write(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "additionalContext": "\n\n".join(notes),
    }}) + "\n")


def _refuse_same_command(losses):
    listed = "\n".join("  - %s: %s" % (path, what) for path, what in losses)
    return shell_text.refuse(
        "PATHSPEC COMMIT DISCARDS AN INDEX EDIT MADE EARLIER IN THIS SAME COMMAND:\n" + listed +
        "\n`git commit <paths>` records the WORKTREE copy of each named path, so the edit this "
        "command just staged is thrown away (exit 0, nothing said).\n"
        "Fix: commit WITHOUT a pathspec after the edit (`git commit -F msg`), having checked that "
        "`git diff --cached --stat` lists only your paths - or make the edit in the worktree "
        "instead (chmod, git rm)."
    )


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:
        return 0
    command = (event.get("tool_input") or {}).get("command") or ""
    tool_name = event.get("tool_name")
    if multi_path_quiet_check_ignore(command, tool_name):
        return shell_text.refuse(
            "git check-ignore -q/--quiet takes a SINGLE path; with 2+ it fails `--quiet is only "
            "valid with a single pathname` (exit 128; the text is LOCALIZED - match the code), "
            "and a non-zero-means-not-ignored reading takes that as an answer for every path.\n"
            "Fix: one path per call (`git check-ignore -q -- p`), or drop -q and read which "
            "paths it prints.\n"
        )
    if not broken_revparse(command, tool_name):
        same = same_command_losses(command, tool_name)
        if same:
            return _refuse_same_command(same)
        notes = []
        try:
            losses = pathspec_commit_losses(command, event.get("cwd"), tool_name)
            if losses:
                notes.append(_pathspec_advice(losses))
        except Exception:  # noqa: BLE001 - an advisory must never wedge a turn
            pass
        try:
            upstream = foreign_upstream(command, event.get("cwd"), tool_name)
            if upstream:
                notes.append(upstream)
        except Exception:  # noqa: BLE001 - an advisory must never wedge a turn
            pass
        if notes:
            _advise(notes)
        return 0
    return shell_text.refuse(
        "git rev-parse --short takes a SINGLE revision; with 2+ revs it fails "
        "`fatal: Needed a single revision` (exit 128; the text is LOCALIZED - match the code).\n"
        "Fix: drop --short to print full hashes for multiple revs, or run "
        "rev-parse once per rev. Deterministic, not a transient quirk.\n"
    )


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
