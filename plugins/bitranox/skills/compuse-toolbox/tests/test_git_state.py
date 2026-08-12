"""Tests for git_state.py - parse `git status --porcelain=v2 --branch` output, walk for repos,
and the error / None-branch behaviour. ASCII only."""
import json
import os
import subprocess

import git_state as G


# --- --files mode: per-file tracked/ignored/untracked/no-repo classification -----------------


def _git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True, timeout=60,
                          capture_output=True, encoding="utf-8", errors="replace")


def _commit(repo, *paths, message="init"):
    _git(repo, "add", "-f", "--", *paths)
    subprocess.run(["git", "-C", str(repo), "-c", "user.email=t@example.com",
                    "-c", "user.name=Test", "commit", "-q", "-m", message],
                   check=True, timeout=60, capture_output=True)


def _five_state_repo(tmp_path, name="repo"):
    """One repo exercising all five states plus the tracked-AND-ignored precedence case.

    clean.md              tracked, never touched after commit         -> tracked-clean
    modified.md            tracked, edited (unstaged) after commit     -> tracked-modified
    staged_new.md          newly `git add`ed, never committed          -> tracked-modified
    tracked_but_ignored.md tracked (force-added) AND matched by a      -> tracked-clean
                            .gitignore pattern, unchanged since commit    (TRACKED WINS)
    ignored.md             not tracked, matched by .gitignore          -> ignored
    loose.md               not tracked, no pattern match               -> untracked
    """
    repo = tmp_path / name
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / ".gitignore").write_text("ignored.md\ntracked_but_ignored.md\n", encoding="utf-8")
    (repo / "clean.md").write_text("clean\n", encoding="utf-8")
    (repo / "modified.md").write_text("before\n", encoding="utf-8")
    (repo / "tracked_but_ignored.md").write_text("tracked anyway\n", encoding="utf-8")
    _commit(repo, ".gitignore", "clean.md", "modified.md", "tracked_but_ignored.md")
    (repo / "modified.md").write_text("after\n", encoding="utf-8")   # unstaged edit
    (repo / "ignored.md").write_text("hidden\n", encoding="utf-8")
    (repo / "loose.md").write_text("plain\n", encoding="utf-8")
    (repo / "staged_new.md").write_text("brand new\n", encoding="utf-8")
    _git(repo, "add", "--", "staged_new.md")                          # staged, never committed
    return repo


def _states(files):
    return {f["path"].rsplit(os.sep, 1)[-1]: f["state"] for f in files}


def test_classifies_all_five_states_in_one_pass(tmp_path):
    repo = _five_state_repo(tmp_path)
    data = G.classify_files("*.md", root=repo)
    states = _states(data["files"])
    assert states["clean.md"] == "tracked-clean"
    assert states["modified.md"] == "tracked-modified"
    assert states["staged_new.md"] == "tracked-modified"
    assert states["ignored.md"] == "ignored"
    assert states["loose.md"] == "untracked"


def test_tracked_and_ignored_precedence_tracked_wins(tmp_path):
    """The whole point of the tool: a file that is BOTH tracked and matched by a .gitignore
    pattern must classify as tracked (here tracked-clean, since it is unmodified), never
    "ignored" - getting this backwards is the exact defect the tool exists to prevent."""
    repo = _five_state_repo(tmp_path)
    data = G.classify_files("*.md", root=repo)
    states = _states(data["files"])
    assert states["tracked_but_ignored.md"] == "tracked-clean"


def test_no_repo_is_distinct_from_untracked(tmp_path):
    """A file with no enclosing git repo at all must never be conflated with "inside a repo,
    not tracked, not ignored" - they are different facts about the file."""
    repo = _five_state_repo(tmp_path)
    plain = tmp_path / "plain"
    plain.mkdir()
    (plain / "orphan.md").write_text("no repo here\n", encoding="utf-8")
    data = G.classify_files("*.md", root=tmp_path)
    states = _states(data["files"])
    assert states["orphan.md"] == "no-repo"
    assert states["loose.md"] == "untracked"          # the in-repo sibling stays untracked
    assert states["orphan.md"] != states["loose.md"]


def test_repo_with_no_commits_yet_reports_tracked_as_modified(tmp_path):
    """No HEAD to diff against - every tracked file necessarily differs from its (nonexistent)
    history, so it must classify as tracked-modified, not crash or report tracked-clean."""
    repo = tmp_path / "fresh"
    repo.mkdir()
    _git(repo, "init", "-q")
    (repo / "new.md").write_text("brand new, uncommitted repo\n", encoding="utf-8")
    _git(repo, "add", "--", "new.md")
    data = G.classify_files("*.md", root=repo)
    states = _states(data["files"])
    assert states["new.md"] == "tracked-modified"


def test_multiple_repos_under_one_root_do_not_cross_contaminate(tmp_path):
    a = _five_state_repo(tmp_path, name="a")
    b = _five_state_repo(tmp_path, name="b")
    data = G.classify_files("clean.md", root=tmp_path)
    repos = {f["path"]: f["repo"] for f in data["files"]}
    assert len(data["files"]) == 2
    for path, repo in repos.items():
        assert path.startswith(repo)
        assert (str(a) == repo) or (str(b) == repo)


def test_glob_filters_to_matching_files_only(tmp_path):
    repo = _five_state_repo(tmp_path)
    (repo / "other.txt").write_text("not markdown\n", encoding="utf-8")
    data = G.classify_files("*.md", root=repo)
    names = {f["path"].rsplit(os.sep, 1)[-1] for f in data["files"]}
    assert "other.txt" not in names
    assert "clean.md" in names


def test_paths_with_spaces_unicode_and_leading_dash(tmp_path):
    repo = tmp_path / "weird"
    repo.mkdir()
    _git(repo, "init", "-q")
    tricky_tracked = repo / "file with spaces αβγ.md"
    tricky_tracked.write_text("tracked\n", encoding="utf-8")
    dash = repo / "-dashfile.md"
    dash.write_text("tracked\n", encoding="utf-8")
    _commit(repo, "file with spaces αβγ.md", "-dashfile.md")
    loose = repo / "-loose αβγ.md"
    loose.write_text("untracked\n", encoding="utf-8")
    data = G.classify_files("*.md", root=repo)
    states = _states(data["files"])
    assert states["file with spaces αβγ.md"] == "tracked-clean"
    assert states["-dashfile.md"] == "tracked-clean"
    assert states["-loose αβγ.md"] == "untracked"


def test_batches_git_calls_per_repo_not_per_file(tmp_path, monkeypatch):
    """The efficiency requirement: classifying N files in one repo must not spawn 2*N git
    subprocesses. Wrap subprocess.run to count calls; six files in one repo must stay well
    under a per-file count (12)."""
    repo = _five_state_repo(tmp_path)   # 6 candidate .md files
    calls = []
    real_run = subprocess.run

    def counting_run(*args, **kwargs):
        calls.append(args)
        return real_run(*args, **kwargs)

    monkeypatch.setattr(G.subprocess, "run", counting_run)
    data = G.classify_files("*.md", root=repo)
    assert len(data["files"]) == 6
    assert len(calls) <= 4          # ls-files, check-ignore, rev-parse HEAD, diff - not 12


def test_json_envelope_lists_each_file_with_its_state(tmp_path, capsys):
    repo = _five_state_repo(tmp_path)
    rc = G.main(["--files", "*.md", "--root", str(repo), "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True and payload["command"] == "git-state"
    states = _states(payload["data"]["files"])
    assert states["clean.md"] == "tracked-clean"
    assert states["ignored.md"] == "ignored"


def test_plain_output_matches_existing_tabular_style(tmp_path, capsys):
    repo = _five_state_repo(tmp_path)
    rc = G.main(["--files", "clean.md", "--root", str(repo)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "tracked-clean" in out
    assert "clean.md" in out


def test_warnings_and_summary_go_to_stderr_not_stdout(tmp_path, capsys):
    repo = _five_state_repo(tmp_path)
    rc = G.main(["--files", "*.md", "--root", str(repo), "--json"])
    assert rc == 0
    captured = capsys.readouterr()
    json.loads(captured.out)          # stdout must stay pure, parseable JSON
    assert captured.err.strip()       # the match-count summary landed on stderr


def test_exit_1_when_nothing_matches_the_glob(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    rc = G.main(["--files", "*.md", "--root", str(empty)])
    assert rc == 1


def test_exit_0_when_files_matched(tmp_path):
    repo = _five_state_repo(tmp_path)
    rc = G.main(["--files", "clean.md", "--root", str(repo)])
    assert rc == 0


def test_exit_2_when_root_path_does_not_exist(tmp_path):
    rc = G.main(["--files", "*.md", "--root", str(tmp_path / "nope")])
    assert rc == 2


def test_exit_2_when_every_matched_repo_fails_to_classify(tmp_path, monkeypatch):
    """A candidate matched the glob but every git call for its repo failed outright - that
    must be reported as broken (exit 2), not as a silent empty result (which would look
    exactly like "nothing matched")."""
    repo = _five_state_repo(tmp_path)

    def always_fails(*args, **kwargs):
        raise OSError("simulated git failure")

    monkeypatch.setattr(G.subprocess, "run", always_fails)
    rc = G.main(["--files", "clean.md", "--root", str(repo)])
    assert rc == 2


def test_repo_field_names_the_owning_repo_root(tmp_path):
    repo = _five_state_repo(tmp_path)
    data = G.classify_files("clean.md", root=repo)
    assert data["files"][0]["repo"] == str(repo)


def test_parse_clean_in_sync():
    out = (
        "# branch.oid abc123\n"
        "# branch.head master\n"
        "# branch.upstream origin/master\n"
        "# branch.ab +0 -0\n"
    )
    s = G.parse_branch_status(out)
    assert s["branch"] == "master"
    assert s["upstream"] == "origin/master"
    assert s["ahead"] == 0 and s["behind"] == 0
    assert s["dirty"] == 0 and s["staged"] == []
    assert s["in_sync"] is True


def test_parse_dirty_ahead_and_staged():
    out = (
        "# branch.head feature\n"
        "# branch.upstream origin/feature\n"
        "# branch.ab +2 -1\n"
        "1 M. N... 100644 100644 100644 aa bb tools/x.py\n"   # staged (index modified)
        "1 .M N... 100644 100644 100644 aa bb tools/y.py\n"   # worktree-modified, not staged
        "? untracked.txt\n"
    )
    s = G.parse_branch_status(out)
    assert s["branch"] == "feature"
    assert s["ahead"] == 2 and s["behind"] == 1
    assert s["in_sync"] is False
    assert s["dirty"] == 3            # 2 tracked changes + 1 untracked
    assert "tools/x.py" in s["staged"] and "tools/y.py" not in s["staged"]


def test_parse_detached_no_upstream():
    out = "# branch.head (detached)\n"
    s = G.parse_branch_status(out)
    assert s["branch"] == "(detached)"
    assert s["upstream"] is None
    assert s["in_sync"] is False      # no upstream -> not verifiably in sync


def test_git_state_on_non_repo_returns_error(tmp_path):
    s = G.git_state(str(tmp_path))     # a plain dir, not a git repo
    assert "error" in s
    assert s["repo"] == str(tmp_path)


def test_find_repos_discovers_git_dirs_and_skips_nested_git(tmp_path):
    (tmp_path / "a" / ".git").mkdir(parents=True)
    (tmp_path / "b" / "sub" / ".git").mkdir(parents=True)
    (tmp_path / "b" / "sub" / ".git" / "modules").mkdir()   # must NOT be walked into
    (tmp_path / "plain").mkdir()                             # no .git -> not a repo
    found = G.find_repos(str(tmp_path))
    assert os.path.join(str(tmp_path), "a") in found
    assert os.path.join(str(tmp_path), "b", "sub") in found
    assert not any("plain" in p for p in found)
    assert not any(".git" in p for p in found)              # never reports a .git internal dir


def test_main_error_path_exits_nonzero_and_does_not_crash(tmp_path, capsys):
    rc = G.main([str(tmp_path)])       # not a git repo -> error path -> rc 1, no crash
    assert rc == 1
    assert "ERROR" in capsys.readouterr().out


def test_main_survives_none_branch(monkeypatch, capsys):
    # regression: a repo whose parsed branch is None must not crash the f-string formatting
    monkeypatch.setattr(G, "git_state", lambda repo: {
        "repo": repo, "branch": None, "upstream": None, "ahead": 0, "behind": 0,
        "dirty": 0, "staged": [], "in_sync": False,
    })
    rc = G.main(["somerepo"])
    assert rc == 1                     # no-upstream -> out of sync
    assert "None" in capsys.readouterr().out   # printed, did not raise
