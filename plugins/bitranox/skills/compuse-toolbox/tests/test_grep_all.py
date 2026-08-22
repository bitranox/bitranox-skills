"""Tests for grep_all.py - a search that cannot silently skip gitignored files.

Claude Code's `grep` routes to a gitignore-aware backend, so a repo-wide sweep under-reports
without saying so. Measured twice in one session: 17 of 43 memory levels found, and 1 of 4 files
carrying a dead reference. Both times the miss looked exactly like success.
"""
import io
import json
from pathlib import PurePath
import subprocess

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
