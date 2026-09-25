"""Tests for grep_all.py - a search that cannot silently skip gitignored files.

Claude Code's `grep` routes to a gitignore-aware backend, so a repo-wide sweep under-reports
without saying so. Measured twice in one session: 17 of 43 memory levels found, and 1 of 4 files
carrying a dead reference. Both times the miss looked exactly like success.
"""
import io
import json
import os
from pathlib import PurePath
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
