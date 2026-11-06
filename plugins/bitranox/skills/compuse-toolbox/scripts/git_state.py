# /// script
# requires-python = ">=3.14"
# ///
"""Report git state for one or more repos: branch, HEAD vs origin (ahead/behind/diverged, or an
upstream that is GONE on the remote), dirty count, and the staged files, one indented `staged`
line each. Also answers the per-FILE question `--files` mode cannot:
across a tree, which copies of a named file are tracked-and-modified, gitignored, or outside any
repo at all - `git status --porcelain -- <path>` is EMPTY for a gitignored file and for a
tracked-clean file ALIKE, so a naive check silently conflates them and only the tracked one is
restorable with `git checkout`.

Why: the shared-checkout + snapshot-before-bulk-rewrite rules mean every risky commit/bulk op is
preceded by the same hand-typed branch / HEAD==origin / dirty check. This does it once, read-only.

Run:
  uv run scripts/git_state.py                 # the current directory
  uv run scripts/git_state.py repoA repoB     # named repos
  uv run scripts/git_state.py --fetch repoA   # `git fetch --prune` each repo first
  uv run scripts/git_state.py --root ~/src    # every repo found under a directory (a .git
                                              # directory, or the .git FILE of a linked
                                              # worktree or submodule)
  uv run scripts/git_state.py --files CLAUDE.md --root ~/src [--json]
      # every CLAUDE.md under ~/src, classified tracked-clean / tracked-modified / ignored /
      # untracked / no-repo - never via `git status`, see classify_files() for why.
  add --json in either mode for an envelope {ok, command, data, skipped}

Ahead/behind come from local refs, so they are as of each repo's LAST FETCH: a clone nobody fetched
reports a confident, precise, wrong number (measured: 2 ahead / 0 behind, 609 behind after a
fetch). Without --fetch the human output says so on stderr; JSON carries `fetched`.

A FOREIGN upstream is one whose branch name differs from the local branch's: a branch cut from a
remote-tracking ref (`git checkout -b feat origin/master`) gets that ref as its upstream, and a
`git push origin feat` without -u leaves it so. Porcelain then counts against origin/master and
reports the topic commits as unpushed although origin/feat holds them. Such a repo is flagged
(`upstream origin/master is not origin/feat`) and judged against origin/<branch> by name instead:
in sync only when that ref exists and equals HEAD, out of sync when it is absent or differs.

Exit status (repo mode) is 0 when every repo is in sync, 1 if any is out of sync (behind/ahead/
diverged, no upstream, an upstream gone on the remote, or a foreign upstream whose namesake is
absent or differs from HEAD), so this doubles as a pre-push guard, and 2 when the check itself is
incomplete: a repo git could not read, a --fetch that failed for a repo, a --root that does not
exist, holds no repo, or has a directory the walk could not read. Exit status (`--files` mode) is
format-independent: 0 at least one file matched the glob, 1 none matched, 2 the walk or every
matched repo's git calls failed outright, or the walk hit an unreadable directory and matched
nothing - because "nothing matched" and "could not classify anything" must not look alike.
Under --json, `ok` means the check ran (exit 0 or 1) and is false only on exit 2; a usage error
or a crash prints the envelope too, and exits 2.

Decisions:
    - A foreign upstream is judged against <remote>/<branch> by name: in sync only when that ref
      exists and equals HEAD, out of sync (exit 1) when it is absent or differs, and a branch that
      tracks a differently named branch on purpose is judged the same way. Why: the question a
      pre-push guard answers is "is this branch pushed under its own name", and the configuration
      cannot tell intent from accident. Evidence: measured: 2026-11-06, a worktree whose `@{u}..`
      listed 2 commits against origin/master while HEAD equalled origin/<branch>. Reopen if: a
      fleet sweep shows deliberate differently named tracking is common and the exit 1 is noise.
      Pinned by: tests/test_git_state.py::test_a_foreign_upstream_with_no_namesake_is_out_of_sync,
      tests/test_git_state.py::test_a_foreign_upstream_whose_namesake_equals_head_is_in_sync_but_flagged
    - Rejected: keep porcelain's `@{u}` counts for a foreign upstream and only add a note. Why: they
      count against another branch, so the exit code would still answer the wrong question.
      Reopen if: never while the exit code is meant as a pre-push guard.
    - Without --fetch nothing is fetched, and the human output says the counts are as of the last
      fetch (stderr; JSON carries `fetched`). Why: a read-only check by default needs no network
      and cannot hang on a credential prompt. Evidence: argued. Reopen if: callers keep acting on
      unfetched counts despite the note. Pinned by:
      tests/test_git_state.py::test_without_fetch_the_counts_are_stale_and_say_so
    - Rejected: fetching by default. Why: as above. Reopen if: as above.
    - A failed --fetch is exit 2 (the check is incomplete), the state is still read and printed.
      Why: a stale answer presented as fetched would be the defect --fetch exists to remove.
      Evidence: argued. Reopen if: never. Pinned by:
      tests/test_git_state.py::test_a_failed_fetch_is_exit_2_and_named
"""

import json
import os
import subprocess
import sys
from pathlib import Path

from _cli_envelope import EnvelopeArgumentParser, run_guarded


def parse_branch_status(text: str) -> dict:
    """Parse `git status --porcelain=v2 --branch` output into a state dict (pure; unit-testable).

    `gone` is an upstream git still names but can no longer compare against: after the branch is
    deleted on the remote and pruned, porcelain keeps `# branch.upstream` and drops
    `# branch.ab`. Reading that absent line as +0 -0 would call a branch with nowhere to push "in
    sync", so a missing ab line with an upstream is never in sync.

    Split on "\\n" only: a path can hold a form feed or U+2028, which str.splitlines() would break
    into a second, bogus record.
    """
    branch = upstream = None
    ahead = behind = dirty = 0
    saw_ab = False
    staged: list[str] = []
    for line in text.split("\n"):
        line = line.rstrip("\r")
        if line.startswith("# branch.head "):
            branch = line.split(" ", 2)[2].strip()
        elif line.startswith("# branch.upstream "):
            upstream = line.split(" ", 2)[2].strip()
        elif line.startswith("# branch.ab "):
            saw_ab = True
            for tok in line.split()[2:]:
                if tok.startswith("+"):
                    ahead = int(tok[1:])
                elif tok.startswith("-"):
                    behind = int(tok[1:])
        elif line[:2] in ("1 ", "2 "):                       # a tracked change (ordinary / renamed)
            dirty += 1
            if line[2] != ".":                               # index (staged) status is not "."
                staged.append(_changed_path(line))
        elif line[:2] in ("u ", "? "):                       # unmerged or untracked
            dirty += 1
    gone = upstream is not None and not saw_ab
    in_sync = upstream is not None and not gone and ahead == 0 and behind == 0
    return {"branch": branch, "upstream": upstream, "gone": gone, "ahead": ahead,
            "behind": behind, "dirty": dirty, "staged": staged, "in_sync": in_sync}


def _changed_path(line: str) -> str:
    """The path of a porcelain v2 "1" / "2" record, spaces and all.

    The path is the LAST field and may itself contain spaces, so split a fixed number of times:
    8 leading fields for an ordinary change, 9 for a rename (whose tail is "new<TAB>old").
    """
    if line[0] == "1":
        return line.split(" ", 8)[8]
    return line.split(" ", 9)[9].split("\t")[0]


def git_state(repo, fetch: bool = False) -> dict:
    """Run git in `repo` and return its parsed state (adds "repo" + "error").

    With `fetch`, `git fetch --prune` runs first; its failure is "fetch_error" (the state is still
    read, from the refs as they were)."""
    fetch_error = _fetch(repo) if fetch else None
    state = _read_state(repo)
    if fetch:
        state["fetch_error"] = fetch_error
    return state


def _read_state(repo) -> dict:
    try:
        # quotePath off so a staged non-ASCII name prints as itself rather than as octal escapes;
        # decoded as UTF-8 with replacement so an undecodable name cannot crash the check.
        out = subprocess.run(["git", "-c", "core.quotePath=false", "-C", str(repo), "status",
                              "--porcelain=v2", "--branch"],
                             capture_output=True, encoding="utf-8", errors="replace", timeout=30)
    except (OSError, subprocess.SubprocessError) as exc:
        return {"repo": str(repo), "error": str(exc)}
    if out.returncode != 0:
        return {"repo": str(repo), "error": (out.stderr or "not a git repo").strip()}
    state = parse_branch_status(out.stdout)
    state["repo"] = str(repo)
    _judge_own_upstream(repo, state)
    return state


_FETCH_TIMEOUT = 120


def _fetch(repo) -> str | None:
    """`git fetch --prune` in `repo`; None on success, else why it failed.

    No prompt can block it: GIT_TERMINAL_PROMPT=0 stops https credential prompts, and a new
    session (POSIX) leaves ssh no controlling terminal to ask a passphrase on. A timeout kills the
    whole group, since git's ssh child would otherwise outlive it."""
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", LC_ALL="C")
    try:
        proc = subprocess.Popen(["git", "-C", str(repo), "fetch", "--prune", "--quiet"],
                                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, env=env, encoding="utf-8",
                                errors="replace", start_new_session=os.name != "nt")
    except OSError as exc:
        return str(exc)
    try:
        _out, err = proc.communicate(timeout=_FETCH_TIMEOUT)
    except subprocess.TimeoutExpired:
        _kill_tree(proc)
        return "git fetch timed out after %ds" % _FETCH_TIMEOUT
    if proc.returncode == 0:
        return None
    lines = [line for line in (err or "").splitlines() if line.strip()]
    return lines[-1].strip() if lines else "git fetch exited %d" % proc.returncode


def _kill_tree(proc) -> None:
    try:
        if os.name != "nt":
            os.killpg(proc.pid, 9)
        else:
            proc.kill()
    except OSError:
        pass
    proc.communicate()


def _git_out(repo, *args) -> str | None:
    try:
        res = subprocess.run(["git", "-C", str(repo), *args], capture_output=True,
                             encoding="utf-8", errors="replace", timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    return res.stdout if res.returncode == 0 else None


def _judge_own_upstream(repo, state: dict) -> None:
    """Flag a FOREIGN upstream and re-judge in_sync against <remote>/<branch> (see module doc).

    Adds foreign_upstream, own_upstream, own_exists, own_ahead, own_behind (None when not
    foreign or not countable)."""
    state.update(foreign_upstream=False, own_upstream=None, own_exists=None, own_ahead=None,
                 own_behind=None)
    branch = state.get("branch")
    if not state.get("upstream") or not branch or branch == "(detached)":
        return
    line = (_git_out(repo, "for-each-ref", "--format=%(upstream:remotename)%09"
                     "%(upstream:remoteref)", "refs/heads/" + branch) or "").strip("\n")
    remote, _tab, remote_ref = line.partition("\t")
    if not remote_ref or remote_ref.removeprefix("refs/heads/") == branch:
        return
    own = "%s/%s" % (remote if remote and remote != "." else "origin", branch)
    exists = _git_out(repo, "rev-parse", "--verify", "-q", "refs/remotes/" + own) is not None
    state.update(foreign_upstream=True, own_upstream=own, own_exists=exists)
    counts = _git_out(repo, "rev-list", "--left-right", "--count",
                      "HEAD...refs/remotes/" + own) if exists else None
    if counts is not None and len(counts.split()) == 2:
        ahead, behind = (int(n) for n in counts.split())
        state.update(own_ahead=ahead, own_behind=behind)
    state["in_sync"] = state["own_ahead"] == 0 and state["own_behind"] == 0


def find_repos(root, errors: list[str] | None = None) -> list[str]:
    """Walk `root` and return every directory holding a `.git` - a directory, or the `.git` FILE
    of a linked worktree or submodule, whose gitdir lives elsewhere. Never descends into a .git
    directory. A directory the walk cannot read is appended to `errors` (when given) instead of
    being skipped in silence, since a repo under it would otherwise just be missing."""
    repos = []
    for dirpath, dirs, files in os.walk(str(root), onerror=_walk_error_sink(errors)):
        if ".git" in dirs or ".git" in files:
            repos.append(dirpath)
        dirs[:] = [d for d in dirs if d != ".git"]           # don't descend into the repo's own .git
    return sorted(repos)


def _walk_error_sink(errors: list[str] | None):
    """An os.walk onerror that records "unreadable <path>: <reason>" rather than dropping it."""
    def record(exc: OSError) -> None:
        if errors is not None:
            errors.append("unreadable %s: %s" % (exc.filename, exc.strerror or exc))
    return record


def repo_relative(path, repo_root) -> str:
    """`path` relative to `repo_root`, spelled with "/" - the separator git prints on every
    platform. A native Windows "docs\\CLAUDE.md" never equals git's "docs/CLAUDE.md", so a
    tracked file below the repo root would read as untracked."""
    return path.relative_to(repo_root).as_posix()


# --- --files mode: per-file tracked/ignored/untracked/no-repo classification ------------------
#
# The defect this exists to prevent: `git status --porcelain -- <path>` prints nothing for a
# gitignored file AND for a tracked-clean file - the two look identical, and only the tracked one
# is restorable with `git checkout`. So classification never touches `git status`; it is built
# from `git ls-files --error-unmatch` (tracked) and `git check-ignore` (ignored) instead, batched
# ONE call of each per repo (not per file) via `--` pathspecs and `--stdin`.

FILE_STATES = ("tracked-clean", "tracked-modified", "ignored", "untracked", "no-repo")


class _GitBatchError(Exception):
    """A batched git call for a repo failed outright (process could not run, or a real git
    error like a corrupted repo) - distinct from `ls-files --error-unmatch`/`check-ignore`
    returning their ORDINARY non-zero "some paths didn't match" exit status, which is not an
    error here and is read from stdout content, not the exit code."""


def _run_git(repo_root, *args):
    try:
        return subprocess.run(["git", "-C", str(repo_root), *args], capture_output=True,
                              encoding="utf-8", errors="replace", timeout=120)
    except (OSError, subprocess.SubprocessError) as exc:
        raise _GitBatchError(str(exc)) from exc


def find_files(root, pattern, errors: list[str] | None = None) -> list[Path]:
    """Every file under `root` whose path matches `pattern` (Path.match semantics: a plain name
    like "CLAUDE.md" matches by exact basename anywhere; "*.md" matches by suffix anywhere).
    Never descends into a repo's own .git, matching find_repos(). Unreadable directories go to
    `errors`, as in find_repos()."""
    root = Path(root)
    if root.is_file():
        return [root] if root.match(pattern) else []
    out = []
    for dirpath, dirs, filenames in os.walk(root, onerror=_walk_error_sink(errors)):
        dirs[:] = [d for d in dirs if d != ".git"]
        for name in filenames:
            p = Path(dirpath) / name
            if p.match(pattern):
                out.append(p)
    return sorted(out)


def _ancestor_repo_root(start: Path):
    """Walk upward from `start` for a `.git` entry (a dir, or a worktree's gitdir FILE) using
    only the filesystem - no subprocess. Seeds the enclosing repo for the common case where
    `--root` is itself a subdirectory of a repo rather than a repo (or many repos') parent."""
    for p in (start, *start.parents):
        # os.path.exists, not Path.exists: before Python 3.14 the latter RAISES PermissionError
        # for a path under an unreadable directory instead of answering False.
        if os.path.exists(p / ".git"):
            return p
    return None


def _repo_roots_for(root: Path) -> list[Path]:
    """Every repo root that can own a file under `root`: repos found BY WALKING DOWN from
    `root` (find_repos - covers `root` holding many nested repos), plus `root`'s own enclosing
    repo if it has one (covers `root` being a subdirectory INSIDE a repo). A repo whose .git
    lives outside both of those is out of scope, matching find_repos()'s own reach."""
    roots = {Path(r) for r in find_repos(root, errors=[])}   # find_files already reports them
    ancestor = _ancestor_repo_root(root if root.is_dir() else root.parent)
    if ancestor is not None:
        roots.add(ancestor)
    return sorted(roots, key=lambda p: len(p.parts))


def _owning_repo(path: Path, repo_roots: list[Path]):
    """The deepest repo root that is an ancestor of `path`, or None (no-repo)."""
    best = None
    for r in repo_roots:
        try:
            path.relative_to(r)
        except ValueError:
            continue
        if best is None or len(r.parts) > len(best.parts):
            best = r
    return best


def _batch_tracked(repo_root, rel_paths: list[str]) -> set[str]:
    """The subset of rel_paths git considers tracked, via ONE `ls-files --error-unmatch` call
    regardless of how many paths are given. Reads the TRACKED set off stdout (the paths that
    matched) rather than the exit code, because with several pathspecs the exit code only says
    "were they ALL tracked", not which ones - and stdout still lists every one that matched even
    when others did not (verified: it does not stop at the first miss)."""
    if not rel_paths:
        return set()
    res = _run_git(repo_root, "ls-files", "--error-unmatch", "-z", "--", *rel_paths)
    if res.returncode not in (0, 1):
        raise _GitBatchError((res.stderr or "git ls-files failed").strip())
    return {p for p in res.stdout.split("\0") if p}


def _batch_ignored(repo_root, rel_paths: list[str]) -> set[str]:
    """The subset of rel_paths matched by a gitignore pattern, via ONE `check-ignore --stdin`
    call. Uses `--no-index`, which matches patterns regardless of tracked status - so a tracked
    file WOULD come back "ignored" if asked about (verified: without `--no-index`, git itself
    quietly excludes tracked files from check-ignore's output, which would make the precedence
    below true by accident rather than by this tool's own decision). Callers must therefore only
    ever pass paths `_batch_tracked` did NOT report tracked - that filtering, not git's default
    behaviour, is what deliberately makes TRACKED WIN the tracked-vs-ignored precedence here."""
    if not rel_paths:
        return set()
    try:
        res = subprocess.run(["git", "-C", str(repo_root), "check-ignore", "--stdin", "-z",
                             "--no-index"],
                             input="\0".join(rel_paths), capture_output=True,
                             encoding="utf-8", errors="replace", timeout=120)
    except (OSError, subprocess.SubprocessError) as exc:
        raise _GitBatchError(str(exc)) from exc
    if res.returncode not in (0, 1):
        raise _GitBatchError((res.stderr or "git check-ignore failed").strip())
    return {p for p in res.stdout.split("\0") if p}


def _has_head(repo_root) -> bool:
    res = _run_git(repo_root, "rev-parse", "--verify", "-q", "HEAD")
    return res.returncode == 0


def _batch_modified(repo_root, rel_paths: list[str]) -> set[str]:
    """The subset of rel_paths (already known tracked) that differ from HEAD - staged or
    unstaged, since `git diff HEAD` compares the worktree straight to HEAD. A repo with no
    commits yet has no HEAD to diff against, so every tracked candidate is reported modified
    outright: nothing is committed, so everything necessarily differs from its (nonexistent)
    history."""
    if not rel_paths:
        return set()
    if not _has_head(repo_root):
        return set(rel_paths)
    res = _run_git(repo_root, "diff", "--name-only", "-z", "HEAD", "--", *rel_paths)
    if res.returncode != 0:
        raise _GitBatchError((res.stderr or "git diff failed").strip())
    return {p for p in res.stdout.split("\0") if p}


def classify_files(pattern, root=".") -> dict:
    """Find every file under `root` matching `pattern` and classify each as tracked-clean,
    tracked-modified, ignored, untracked, or no-repo (see FILE_STATES; mutually exclusive and
    exhaustive for any hit).

    Bounded git-process count: at most 4 subprocess calls PER REPO (`ls-files`, `check-ignore`
    on the non-tracked remainder, an optional HEAD-existence probe, `diff` on the tracked
    remainder) no matter how many candidate files that repo contributes - never 2 per file.

    Returns {"pattern", "root", "candidates" (files matched before classification), "files"
    ([{"path", "repo", "state"}, ...]), "skipped" (repo-level failures and unreadable
    directories, as strings), "walk_errors" (how many of those are unreadable directories)}.
    """
    root_path = Path(root).absolute()
    walk_errors: list[str] = []
    files = find_files(root_path, pattern, errors=walk_errors)
    repo_roots = _repo_roots_for(root_path)

    by_repo: dict = {}
    for f in files:
        by_repo.setdefault(_owning_repo(f, repo_roots), []).append(f)

    results = []
    skipped = list(walk_errors)
    for repo_root, group in by_repo.items():
        if repo_root is None:
            results.extend({"path": str(f), "repo": None, "state": "no-repo"} for f in group)
            continue
        rel = {f: repo_relative(f, repo_root) for f in group}
        try:
            tracked = _batch_tracked(repo_root, list(rel.values()))
            remainder = [rel[f] for f in group if rel[f] not in tracked]
            ignored = _batch_ignored(repo_root, remainder)
            tracked_rel = [rel[f] for f in group if rel[f] in tracked]
            modified = _batch_modified(repo_root, tracked_rel)
        except _GitBatchError as exc:
            skipped.append("%s: %s" % (repo_root, exc))
            continue
        for f in group:
            r = rel[f]
            if r in tracked:
                state = "tracked-modified" if r in modified else "tracked-clean"
            elif r in ignored:
                state = "ignored"
            else:
                state = "untracked"
            results.append({"path": str(f), "repo": str(repo_root), "state": state})

    results.sort(key=lambda d: d["path"])
    return {"pattern": pattern, "root": str(root_path), "candidates": len(files),
            "files": results, "skipped": skipped, "walk_errors": len(walk_errors)}


def _print_files_result(pattern, root, data, as_json, rc) -> None:
    if as_json:
        # ok is "ran without error" (exit != 2); "none matched" is exit 1 with ok true.
        print(json.dumps({"ok": rc != 2, "command": "git-state",
                          "data": data, "skipped": data["skipped"]}, indent=2))
    else:
        for f in data["files"]:
            print("%-16s %s" % (f["state"], f["path"]))
    for s in data["skipped"]:
        print("git_state: skipped %s" % s, file=sys.stderr)
    print("git_state: %d file(s) matched %r under %s" % (data["candidates"], pattern, root),
          file=sys.stderr)


def root_problem(root) -> str | None:
    """Why --root cannot be walked, or None when it can be looked at.

    Not Path.exists()/is_dir(): before Python 3.14 they RAISE PermissionError for a path under
    an unreadable directory, and the traceback's exit 1 reads as "out of sync" or "0 matched".
    Since 3.14 they answer False, which would call an unreachable root missing. Both are exit 2,
    and the message says which."""
    try:
        os.stat(root)
    except (FileNotFoundError, NotADirectoryError):
        return f"--root path does not exist: {root}"
    except (OSError, ValueError) as exc:
        return f"--root path cannot be accessed ({type(exc).__name__}): {root}"
    return None


def _main_files(pattern, root, as_json) -> int:
    root = root or "."
    msg = root_problem(root)
    if msg:
        print("git_state: %s" % msg, file=sys.stderr)
        if as_json:
            print(json.dumps({"ok": False, "command": "git-state",
                              "data": {"pattern": pattern, "root": root, "candidates": 0,
                                       "files": [], "skipped": []},
                              "skipped": [], "error": msg}, indent=2))
        return 2
    data = classify_files(pattern, root)
    rc = _files_exit(data)
    _print_files_result(pattern, root, data, as_json, rc)
    return rc


def _files_exit(data) -> int:
    if data["candidates"] == 0:
        # "none matched" is only an answer if the walk could see everything it was asked to.
        return 2 if data["walk_errors"] else 1
    if not data["files"]:                    # matched something, classified nothing
        return 2
    return 0


def main(argv=None) -> int:
    """The CLI. An uncaught exception exits 2 (envelope under --json), never 1 ("out of sync")."""
    return run_guarded(_main, argv, command="git-state")


def _main(argv=None) -> int:
    ap = EnvelopeArgumentParser(envelope_command="git-state", description="Report git branch / sync / dirty state for repos, "
                                              "or (--files) classify every matching file under a "
                                              "tree as tracked-clean/tracked-modified/ignored/"
                                              "untracked/no-repo.")
    ap.add_argument("repos", nargs="*", default=["."], help="repo paths (default: cwd)")
    ap.add_argument("--root", help="walk this dir for .git repos, or (with --files) for matches "
                                   "(default in --files mode: cwd)")
    ap.add_argument("--files", metavar="GLOB",
                    help="switch modes: classify every file under --root matching GLOB "
                         "(e.g. 'CLAUDE.md' or '*.md') instead of reporting repo state")
    ap.add_argument("--json", action="store_true", help="machine-readable envelope")
    ap.add_argument("--fetch", action="store_true",
                    help="repo mode: `git fetch --prune` each repo before reading it, so "
                         "ahead/behind are current rather than as of the last fetch")
    args = ap.parse_args(argv)
    tolerate_unencodable_stdout()
    if args.files:
        return _main_files(args.files, args.root, args.json)
    return _main_repos(args.repos, args.root, args.json, args.fetch)


def tolerate_unencodable_stdout(stream=None) -> None:
    """A Windows pipe is cp1252; a path it cannot encode must print as '?', not crash the check."""
    stream = stream if stream is not None else sys.stdout
    reconfigure = getattr(stream, "reconfigure", None)
    if reconfigure is None:
        return
    try:
        reconfigure(errors="replace")
    except (ValueError, OSError):
        pass


def _repo_targets(repos, root) -> tuple[list[str], list[str]]:
    """(repos to check, problems that make the check incomplete) - see _main_repos."""
    if not root:
        return list(repos), []
    problem = root_problem(root)
    if problem:
        return [], [problem]
    if not os.path.isdir(root):
        return [], ["--root path is not a directory: %s" % root]
    walk_errors: list[str] = []
    found = find_repos(root, errors=walk_errors)
    if not found and not walk_errors:
        walk_errors.append("no git repo found under --root %s" % root)
    return found, walk_errors


def _sync_flag(s: dict) -> str | None:
    if s.get("foreign_upstream"):
        return _foreign_flag(s)
    if s["in_sync"]:
        return None
    if not s["upstream"]:
        return "no-upstream"
    if s.get("gone"):
        return "upstream %s gone" % s["upstream"]
    return f"ahead {s['ahead']}/behind {s['behind']}"


def _foreign_flag(s: dict) -> str:
    note = "upstream %s is not %s" % (s["upstream"], s["own_upstream"])
    if not s["own_exists"]:
        return "%s (%s absent)" % (note, s["own_upstream"])
    if s["in_sync"]:
        return "OK (%s)" % note
    if s["own_ahead"] is None:
        return "%s (not countable)" % note
    return "ahead %d/behind %d vs %s (%s)" % (s["own_ahead"], s["own_behind"], s["own_upstream"],
                                              note)


def _main_repos(repos, root, as_json, fetch=False) -> int:
    """Repo mode. 0 all in sync, 1 any out of sync, 2 the check is incomplete: a repo git could
    not read or (--fetch) not fetch, or a --root that is missing, holds no repo, or has an
    unreadable directory - a pre-push guard that looked at nothing must not read as a pass."""
    targets, problems = _repo_targets(repos, root)
    rc = 2 if problems else 0
    states = []
    for repo in targets:
        s = git_state(repo, fetch=fetch)
        states.append(s)
        if "error" in s or s.get("fetch_error"):
            rc = 2
        if "error" not in s and not s["in_sync"]:
            rc = max(rc, 1)
    if as_json:
        print(json.dumps({"ok": rc != 2, "command": "git-state",
                          "data": {"root": root, "fetched": fetch, "repos": states},
                          "skipped": problems}, indent=2))
    else:
        for s in states:
            _print_repo_state(s)
        if not fetch and any(s.get("upstream") for s in states):
            print("git_state: ahead/behind are as of each repo's last fetch (--fetch refreshes)",
                  file=sys.stderr)
    for problem in problems:
        print("git_state: %s" % problem, file=sys.stderr)
    return rc


def _print_repo_state(s: dict) -> None:
    if "error" in s:
        print(f"{s['repo']:40} ERROR: {s['error']}")
        return
    flags = [f for f in (_sync_flag(s), f"dirty {s['dirty']}" if s["dirty"] else None) if f]
    print(f"{s['repo']:40} {str(s['branch']):20} {'OK' if not flags else ' '.join(flags)}")
    if s.get("fetch_error"):
        print(f"    fetch failed: {s['fetch_error']}")
    for path in s.get("staged", ()):
        print(f"    staged  {path}")


if __name__ == "__main__":
    sys.exit(main())
