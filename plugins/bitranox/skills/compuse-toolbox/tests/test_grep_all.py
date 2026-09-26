"""Tests for grep_all.py - a search that cannot silently skip gitignored files.

Claude Code's `grep` routes to a gitignore-aware backend, so a repo-wide sweep under-reports
without saying so. Measured twice in one session: 17 of 43 memory levels found, and 1 of 4 files
carrying a dead reference. Both times the miss looked exactly like success.
"""
import io
import json
import os
from pathlib import PurePath
import shutil
import subprocess
import sys

import pytest

import grep_all


def _repo(tmp_path):
    """A git repo with one tracked and one gitignored file, both containing the needle."""
    root = tmp_path / "r"
    (root / "sub").mkdir(parents=True)
    (root / ".gitignore").write_text("secret.md\n", encoding="utf-8")
    (root / "tracked.md").write_text("alpha NEEDLE omega\n", encoding="utf-8")
    (root / "sub" / "secret.md").write_text("hidden NEEDLE here\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True, timeout=60)
    return root


def _run(argv):
    out, err = io.StringIO(), io.StringIO()
    code = grep_all.main(argv, out=out, err=err)
    return code, out.getvalue(), err.getvalue()


def test_finds_matches_in_gitignored_files(tmp_path):
    """The whole point: the ignored file must be reported, not silently dropped."""
    root = _repo(tmp_path)
    code, out, _ = _run(["NEEDLE", str(root)])
    assert code == 0
    assert "tracked.md" in out and "secret.md" in out


def test_reports_how_many_matches_a_gitignore_aware_search_would_have_missed(tmp_path):
    """A bare count is not enough - the tool must quantify the gap it exists to close."""
    root = _repo(tmp_path)
    _, _, err = _run(["NEEDLE", str(root)])
    assert "1" in err and "ignored" in err.lower()


def test_summary_goes_to_stderr_so_the_match_stream_stays_parseable(tmp_path):
    root = _repo(tmp_path)
    _, out, err = _run(["NEEDLE", str(root)])
    for line in out.splitlines():
        assert line.count(":") >= 2, line          # path:line:text only
    assert err.strip()


def test_exit_1_when_nothing_matches_and_0_when_something_does(tmp_path):
    root = _repo(tmp_path)
    assert _run(["NEEDLE", str(root)])[0] == 0
    assert _run(["NOSUCHTOKEN", str(root)])[0] == 1


def test_json_envelope_lists_each_match_with_its_ignored_flag(tmp_path):
    root = _repo(tmp_path)
    code, out, _ = _run(["NEEDLE", str(root), "--json"])
    assert code == 0
    payload = json.loads(out)
    assert payload["ok"] is True and payload["command"] == "grep-all"
    # PurePath().name, not split("/"): the envelope carries real local paths, which are
    # backslash-separated on Windows, so splitting on "/" returns the whole path as the key.
    flags = {PurePath(m["path"]).name: m["gitignored"] for m in payload["data"]["matches"]}
    assert flags["tracked.md"] is False
    assert flags["secret.md"] is True
    assert payload["data"]["ignored_matches"] == 1


def test_json_is_still_emitted_on_the_failure_path(tmp_path):
    root = _repo(tmp_path)
    code, out, _ = _run(["NOSUCHTOKEN", str(root), "--json"])
    assert code == 1
    assert json.loads(out)["data"]["matches"] == []


def test_glob_filter_restricts_the_sweep(tmp_path):
    root = _repo(tmp_path)
    (root / "other.txt").write_text("NEEDLE in a txt\n", encoding="utf-8")
    _, out, _ = _run(["NEEDLE", str(root), "--glob", "*.md"])
    assert "other.txt" not in out and "tracked.md" in out


def test_a_bad_regex_is_an_error_not_a_silent_zero(tmp_path):
    """Exit 2, because 'no matches' and 'the pattern never compiled' must not look alike."""
    root = _repo(tmp_path)
    code, _, err = _run(["NEEDLE(", str(root)])
    assert code == 2 and err.strip()


def test_a_missing_path_is_an_error(tmp_path):
    code, _, err = _run(["NEEDLE", str(tmp_path / "nope")])
    assert code == 2 and "nope" in err


def test_works_outside_a_git_repo(tmp_path):
    """No repo means nothing is ignored - the tool must still search, not refuse."""
    plain = tmp_path / "plain"
    plain.mkdir()
    (plain / "a.md").write_text("NEEDLE\n", encoding="utf-8")
    code, out, _ = _run(["NEEDLE", str(plain)])
    assert code == 0 and "a.md" in out


def test_dot_git_internals_are_never_searched(tmp_path):
    """Objects and refs would flood the result and are never what you meant."""
    root = _repo(tmp_path)
    (root / ".git" / "planted.md").write_text("NEEDLE\n", encoding="utf-8")
    _, out, _ = _run(["NEEDLE", str(root)])
    assert "planted.md" not in out


# ---- review fixes (rank-10 slice 2, group T3) ---------------------------------------------------


def _anchored_repo(tmp_path):
    """A repo whose ignore rule is ANCHORED to the root, so only a correct path resolution
    can match it: `/sub/secret.md` against a cwd-relative `secret.md` matches nothing."""
    root = tmp_path / "r"
    (root / "sub").mkdir(parents=True)
    (root / ".gitignore").write_text("/sub/secret.md\n", encoding="utf-8")
    (root / "sub" / "secret.md").write_text("hidden NEEDLE here\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True, timeout=60)
    return root


def test_the_ignored_count_is_right_from_a_subdirectory(tmp_path, monkeypatch):
    root = _anchored_repo(tmp_path)
    monkeypatch.chdir(root / "sub")
    code, _, err = _run(["NEEDLE", "--json"])
    assert code == 0, err
    assert "1 of them are gitignored" in err


def test_a_relative_path_leaving_the_subdirectory_still_counts(tmp_path, monkeypatch):
    root = _anchored_repo(tmp_path)
    monkeypatch.chdir(root / "sub")
    code, _, err = _run(["NEEDLE", ".."])
    assert code == 0, err
    assert "1 of them are gitignored" in err


def test_git_missing_makes_the_ignored_count_unknown_not_zero(tmp_path, monkeypatch):
    root = _anchored_repo(tmp_path)
    empty = tmp_path / "nobin"
    empty.mkdir()
    monkeypatch.setenv("PATH", str(empty))
    code, out, err = _run(["NEEDLE", str(root), "--json"])
    assert code == 2
    assert "0 of them" not in err and "unknown" in err.lower()
    assert json.loads(out)["data"]["ignored_matches"] is None


def test_a_failing_check_ignore_makes_the_count_unknown(tmp_path):
    """check-ignore reads the index; a corrupt one fails it (128) while rev-parse still works,
    and that exit status was never looked at."""
    root = _anchored_repo(tmp_path)
    (root / ".git" / "index").write_bytes(b"garbage-not-an-index")
    code, out, err = _run(["NEEDLE", str(root), "--json"])
    assert code == 2
    assert "unknown" in err.lower() and "0 of them" not in err
    assert json.loads(out)["data"]["ignored_matches"] is None


@pytest.mark.skipif(sys.platform == "win32",
                    reason="Windows has no POSIX mode bits: chmod(0o000) leaves the path readable")
def test_unreadable_files_and_dirs_are_reported_not_dropped(tmp_path):
    p = tmp_path / "p"
    (p / "locked").mkdir(parents=True)
    (p / "locked" / "inner.txt").write_text("NEEDLE\n", encoding="utf-8")
    (p / "unreadable.txt").write_text("NEEDLE\n", encoding="utf-8")
    (p / "unreadable.txt").chmod(0o000)
    (p / "locked").chmod(0o000)
    try:
        if os.access(p / "locked", os.R_OK):
            pytest.skip("running with privileges that read a mode-000 path (root)")
        code, out, err = _run(["NEEDLE", str(p), "--json"])
    finally:
        (p / "locked").chmod(0o755)
        (p / "unreadable.txt").chmod(0o644)
    assert code == 2, "zero matches with paths unread is not 'no match'"
    payload = json.loads(out)
    skipped = " ".join(payload["skipped"])
    assert "unreadable.txt" in skipped and "locked" in skipped
    assert payload["data"]["files_scanned"] == 0
    assert "unreadable.txt" in err


def test_binary_files_are_listed_as_skipped_and_not_counted_as_scanned(tmp_path):
    d = tmp_path / "d"
    d.mkdir()
    (d / "a.txt").write_text("NEEDLE\n", encoding="utf-8")
    (d / "blob.bin").write_bytes(b"\0\0NEEDLE")
    code, out, _ = _run(["NEEDLE", str(d), "--json"])
    payload = json.loads(out)
    assert code == 0
    assert payload["data"]["files_scanned"] == 1
    assert any("blob.bin" in s and "binary" in s for s in payload["skipped"])


def test_a_form_feed_does_not_shift_line_numbers(tmp_path):
    (tmp_path / "ff.txt").write_bytes(b"a\x0cb\nNEEDLE\n")
    _, out, _ = _run(["NEEDLE", str(tmp_path)])
    assert "ff.txt:2:NEEDLE" in out


def test_a_bom_does_not_hide_a_match_at_the_start(tmp_path):
    (tmp_path / "bom.txt").write_bytes(b"\xef\xbb\xbfNEEDLE first\n")
    code, out, _ = _run(["^NEEDLE", str(tmp_path)])
    assert code == 0 and "bom.txt:1:NEEDLE first" in out


def test_ignore_case(tmp_path):
    (tmp_path / "a.txt").write_text("needle\n", encoding="utf-8")
    assert _run(["NEEDLE", str(tmp_path)])[0] == 1
    assert _run(["NEEDLE", str(tmp_path), "-i"])[0] == 0


def test_a_bad_regex_still_emits_json(tmp_path):
    code, out, _ = _run(["NEEDLE(", str(tmp_path), "--json"])
    assert code == 2
    assert json.loads(out)["ok"] is False


def _run_script(args, **env_extra):
    env = {**os.environ, **env_extra}
    env.pop("PYTHONUTF8", None)
    return subprocess.run([sys.executable, grep_all.__file__, *args], env=env,
                          capture_output=True, timeout=60)


def test_a_cp1252_stdout_does_not_crash_on_a_match(tmp_path):
    (tmp_path / "a.md").write_text("arrow \u2192 NEEDLE\n", encoding="utf-8")
    done = _run_script(["NEEDLE", str(tmp_path)], PYTHONIOENCODING="cp1252")
    assert b"Traceback" not in done.stderr, done.stderr
    assert done.returncode == 0


@pytest.mark.skipif(sys.platform in ("win32", "darwin"),
                    reason="Windows and macOS (APFS) refuse a filename that is not valid UTF-8")
def test_a_non_utf8_filename_does_not_crash_the_print(tmp_path):
    with open(os.path.join(os.fsencode(tmp_path), b"\xff.txt"), "wb") as fh:
        fh.write(b"NEEDLE\n")
    # An explicit utf-8 stdout is strict whatever the locale, as under a UTF-8 desktop locale;
    # only the C/C.UTF-8 locale gets surrogateescape by default.
    done = _run_script(["NEEDLE", str(tmp_path)], PYTHONIOENCODING="utf-8")
    assert b"Traceback" not in done.stderr, done.stderr
    assert done.returncode == 0


# ---- review fixes (rank-8, group GREPALL) -------------------------------------------------------


def _ignored_repo(tmp_path, name="r"):
    """A repo whose only match is gitignored, so a correct answer is "1 of them"."""
    root = tmp_path / name
    root.mkdir(parents=True)
    (root / ".gitignore").write_text("secret.md\n", encoding="utf-8")
    (root / "secret.md").write_text("NEEDLE\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True, timeout=60)
    return root


def _break_dangling_gitdir(root):
    shutil.rmtree(root / ".git")
    (root / ".git").write_text("gitdir: %s\n" % (root.parent / "gone" / "wt"), encoding="utf-8")


def _break_garbage_gitfile(root):
    shutil.rmtree(root / ".git")
    (root / ".git").write_text("garbage\n", encoding="utf-8")


def _break_missing_head(root):
    (root / ".git" / "HEAD").unlink()


@pytest.mark.parametrize("breaker", [_break_dangling_gitdir, _break_garbage_gitfile,
                                     _break_missing_head])
def test_a_repo_git_cannot_read_makes_the_count_unknown_not_zero(tmp_path, breaker):
    """rev-parse exits 128 for a broken .git as for no repo at all. A gitignore-aware search
    still honours the .gitignore beside a .git entry, so "0 of them" would be a false clean."""
    root = _ignored_repo(tmp_path)
    breaker(root)
    code, out, err = _run(["NEEDLE", str(root), "--json"])
    assert "0 of them" not in err
    assert code == 2 and "unknown" in err.lower()
    assert json.loads(out)["data"]["ignored_matches"] is None


def test_dubious_ownership_makes_the_count_unknown_not_zero(tmp_path, monkeypatch):
    root = _ignored_repo(tmp_path)
    monkeypatch.setenv("GIT_TEST_ASSUME_DIFFERENT_OWNER", "1")
    probe = subprocess.run(["git", "-C", str(root), "rev-parse", "--show-toplevel"],
                           capture_output=True, timeout=60)
    if probe.returncode == 0:
        pytest.skip("this git does not honour GIT_TEST_ASSUME_DIFFERENT_OWNER")
    code, out, err = _run(["NEEDLE", str(root), "--json"])
    assert "0 of them" not in err
    # git's own reason is localised, so assert on ours: the count is unknown, and rev-parse said so.
    assert code == 2 and "unknown" in err.lower() and "rev-parse" in err
    assert json.loads(out)["data"]["ignored_matches"] is None


def test_no_repo_anywhere_is_still_a_clean_zero(tmp_path):
    """Control: with no .git entry at or above the file, rev-parse's 128 IS the answer."""
    plain = tmp_path / "plain"
    plain.mkdir()
    (plain / "secret.md").write_text("NEEDLE\n", encoding="utf-8")
    code, out, err = _run(["NEEDLE", str(plain), "--json"])
    assert code == 0, err
    assert "0 of them are gitignored" in err
    assert json.loads(out)["data"]["ignored_matches"] == 0


def _git_ok(*args):
    subprocess.run(["git", "-c", "user.email=t@example.com", "-c", "user.name=Test", *args],
                   check=True, timeout=60, capture_output=True)


def _outer_with_nested_repos(tmp_path):
    """Our own layout: an outer repo ignoring .claude/worktrees/, with a LINKED worktree and a
    plain nested repo inside it, one nested repo the outer does NOT ignore, and one it ignores by
    a directory-only rule naming the nested repo itself."""
    outer = tmp_path / "outer"
    outer.mkdir()
    _git_ok("init", "-q", str(outer))
    (outer / ".gitignore").write_text(".claude/worktrees/\n/dironly/\n", encoding="utf-8")
    (outer / "t.md").write_text("x\n", encoding="utf-8")
    _git_ok("-C", str(outer), "add", "-A")
    _git_ok("-C", str(outer), "commit", "-q", "-m", "init")
    _git_ok("-C", str(outer), "worktree", "add", "-q", str(outer / ".claude" / "worktrees" / "wt"))
    for nested in (".claude/worktrees/plain", "vis", "dironly"):
        (outer / nested).mkdir(parents=True)
        _git_ok("init", "-q", str(outer / nested))
    for nested in (".claude/worktrees/wt", ".claude/worktrees/plain", "vis", "dironly"):
        (outer / nested / "hit.md").write_text("NEEDLE\n", encoding="utf-8")
    return outer


def _ignored_flags(out):
    return {PurePath(m["path"]).parent.name: m["gitignored"]
            for m in json.loads(out)["data"]["matches"]}


def test_a_nested_repo_under_an_outer_ignored_dir_counts_as_ignored(tmp_path):
    """Searching the OUTER repo, a gitignore-aware search never descends into an ignored dir, so
    a match in a worktree or nested repo there is hidden - even though its own repo tracks it."""
    outer = _outer_with_nested_repos(tmp_path)
    code, out, err = _run(["NEEDLE", str(outer), "--json"])
    assert code == 0, err
    assert _ignored_flags(out) == {"wt": True, "plain": True, "vis": False, "dironly": True}
    assert "3 of them are gitignored" in err


def test_searching_from_inside_the_nested_repo_uses_its_own_view(tmp_path):
    """Control: a search STARTED inside the worktree does not see the outer rule."""
    outer = _outer_with_nested_repos(tmp_path)
    code, out, err = _run(["NEEDLE", str(outer / ".claude" / "worktrees" / "wt"), "--json"])
    assert code == 0, err
    assert _ignored_flags(out) == {"wt": False}
    assert "0 of them are gitignored" in err


def test_a_match_reachable_from_a_deeper_search_path_is_not_hidden(tmp_path):
    """Given the outer repo AND the worktree, the worktree search finds its file unfiltered, so
    only matches that no given path reaches unfiltered count as missed."""
    outer = _outer_with_nested_repos(tmp_path)
    wt = outer / ".claude" / "worktrees" / "wt"
    code, out, err = _run(["NEEDLE", str(outer), str(wt), "--json"])
    assert code == 0, err
    assert _ignored_flags(out) == {"wt": False, "plain": True, "vis": False, "dironly": True}


def test_a_git_dir_pinned_by_the_environment_does_not_loop_the_climb(tmp_path):
    """With GIT_DIR/GIT_WORK_TREE set, rev-parse names the SAME repo from any directory, so the
    climb to an enclosing repo must stop rather than ask it forever. Bounded by a subprocess
    timeout, so a regression fails with a name instead of hanging the suite."""
    root = _ignored_repo(tmp_path / "parent")
    env = {"GIT_DIR": str(root / ".git"), "GIT_WORK_TREE": str(root)}
    try:
        done = _run_script(["NEEDLE", str(tmp_path / "parent")], **env)
    except subprocess.TimeoutExpired:
        pytest.fail("the climb to an enclosing repo never stopped")
    assert done.returncode == 0, done.stderr
    assert b"1 of them are gitignored" in done.stderr


@pytest.mark.skipif(sys.platform == "win32",
                    reason="Windows has no POSIX mode bits: chmod(0o000) leaves the path readable")
@pytest.mark.parametrize("extra", [[], ["--json"]])
def test_a_path_under_an_unreadable_dir_is_a_clean_refusal(tmp_path, extra):
    """Before Python 3.14 Path.exists() RAISES PermissionError here: a traceback and exit 1,
    which reads as "no match". It must be exit 2 naming why, and never "does not exist"."""
    locked = tmp_path / "locked"
    (locked / "sub").mkdir(parents=True)
    (locked / "sub" / "a.md").write_text("NEEDLE\n", encoding="utf-8")
    locked.chmod(0o000)
    try:
        if os.access(locked, os.R_OK):
            pytest.skip("running with privileges that read a mode-000 path (root)")
        code, out, err = _run(["NEEDLE", str(locked / "sub"), *extra])
    finally:
        locked.chmod(0o755)
    assert code == 2
    assert "PermissionError" in err and "does not exist" not in err
    if extra:
        assert json.loads(out)["ok"] is False


def test_a_missing_path_still_says_it_does_not_exist(tmp_path):
    """Control for the refusal above: a genuinely missing path keeps its own message."""
    code, _, err = _run(["NEEDLE", str(tmp_path / "nope")])
    assert code == 2 and "does not exist" in err and "nope" in err


# ---- review fixes (rank-8 LOW batch, group L4b) -------------------------------------------------


@pytest.mark.parametrize("argv", [["NEEDLE(", "."], ["NEEDLE", "no-such-path-l4b"]])
def test_the_failure_envelope_has_the_success_shape_and_an_unknown_count(tmp_path, monkeypatch,
                                                                        argv):
    """A caller reading `skipped` or `ignored_matches` must not get a KeyError or a false 0: on a
    failure nothing was asked of git, so the count is unknown (null), as on a git failure."""
    monkeypatch.chdir(tmp_path)
    code, out, _ = _run([*argv, "--json"])
    payload = json.loads(out)
    assert code == 2 and payload["ok"] is False
    assert payload["skipped"] == []
    assert payload["data"]["ignored_matches"] is None
    assert payload["data"]["files_scanned"] == 0


def test_an_explicitly_named_ignored_file_is_not_counted_as_hidden(tmp_path, monkeypatch):
    """rg searches a file it is GIVEN whatever .gitignore says, so a gitignore-aware search of
    that same argument would not have missed it."""
    root = _repo(tmp_path)
    monkeypatch.chdir(root / "sub")
    code, out, err = _run(["NEEDLE", "secret.md", "--json"])
    assert code == 0, err
    assert [m["gitignored"] for m in json.loads(out)["data"]["matches"]] == [False]
    assert "0 of them are gitignored" in err


def test_a_named_file_beside_its_directory_is_not_hidden_but_its_siblings_still_are(tmp_path):
    """Control: naming one ignored file does not un-hide an ignored sibling the dir walk found."""
    root = _repo(tmp_path)
    (root / "sub" / "other.md").write_text("NEEDLE too\n", encoding="utf-8")
    (root / ".gitignore").write_text("secret.md\nother.md\n", encoding="utf-8")
    code, out, err = _run(["NEEDLE", str(root), str(root / "sub" / "secret.md"), "--json"])
    assert code == 0, err
    flags = {PurePath(m["path"]).name: m["gitignored"] for m in json.loads(out)["data"]["matches"]}
    assert flags == {"tracked.md": False, "secret.md": False, "other.md": True}


def test_a_linked_worktree_gitdir_file_is_not_searched(tmp_path):
    """A `.git` FILE is the gitdir pointer of a linked worktree or submodule, never content; its
    text named the needle and read as a match (and the dangling pointer made the count UNKNOWN)."""
    plain = tmp_path / "wt"
    plain.mkdir()
    (plain / ".git").write_text("gitdir: /nowhere/NEEDLE\n", encoding="utf-8")
    (plain / "a.md").write_text("no match here\n", encoding="utf-8")
    code, out, err = _run(["NEEDLE", str(plain)])
    assert code == 1, (out, err)
    assert ".git" not in out
