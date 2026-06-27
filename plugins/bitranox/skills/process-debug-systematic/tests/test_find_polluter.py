"""Tests for find_polluter.py.

The script's pure, testable surface is ``main(argv)``: it parses args, globs
test files (sorted, recursive), then performs a linear scan -- for each test
file it skips when the pollution path already exists, otherwise it invokes the
test runner (``_run_test``) and reports the first test after which the pollution
path appears. ``_run_test`` itself is the integration boundary (it shells out to
``npm``); we monkeypatch it so no real subprocess runs, and drive the
"is this subset failing" predicate by having the patched runner create the
pollution path on a chosen iteration.
"""
import os

import pytest

import find_polluter


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def _make_tests(tmp_path, names):
    """Create empty test files under tmp_path and return their dir."""
    for name in names:
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("// test\n")
    return tmp_path


def _glob(tmp_path, pattern):
    return os.path.join(str(tmp_path), pattern)


# --------------------------------------------------------------------------
# argument parsing
# --------------------------------------------------------------------------
def test_main_wrong_arg_count_returns_1(capsys):
    assert find_polluter.main(["prog"]) == 1
    assert find_polluter.main(["prog", "only-one"]) == 1
    assert find_polluter.main(["prog", "a", "b", "c"]) == 1
    out = capsys.readouterr().out
    assert "Usage:" in out


# --------------------------------------------------------------------------
# scan: no polluter
# --------------------------------------------------------------------------
def test_no_polluter_returns_0_and_runs_every_test(tmp_path, monkeypatch):
    _make_tests(tmp_path, ["a.test.ts", "b.test.ts", "c.test.ts"])
    pollution = tmp_path / "polluted"

    ran = []
    monkeypatch.setattr(find_polluter, "_run_test", lambda f: ran.append(f))

    rc = find_polluter.main(["prog", str(pollution), _glob(tmp_path, "*.test.ts")])

    assert rc == 0
    # every matched test was executed
    assert len(ran) == 3
    assert [os.path.basename(f) for f in ran] == ["a.test.ts", "b.test.ts", "c.test.ts"]


# --------------------------------------------------------------------------
# scan: a real polluter is detected (predicate via patched runner)
# --------------------------------------------------------------------------
def test_finds_polluter_and_returns_1(tmp_path, monkeypatch, capsys):
    _make_tests(tmp_path, ["a.test.ts", "b.test.ts", "c.test.ts"])
    pollution = tmp_path / "polluted"

    ran = []

    def runner(f):
        ran.append(f)
        # the second test (b) is the polluter: it creates the path
        if os.path.basename(f) == "b.test.ts":
            pollution.mkdir()

    monkeypatch.setattr(find_polluter, "_run_test", runner)

    rc = find_polluter.main(["prog", str(pollution), _glob(tmp_path, "*.test.ts")])

    assert rc == 1
    # it stopped after the polluter; c.test.ts must NOT have run
    assert [os.path.basename(f) for f in ran] == ["a.test.ts", "b.test.ts"]
    out = capsys.readouterr().out
    assert "FOUND POLLUTER" in out
    assert "b.test.ts" in out


def test_first_test_is_polluter(tmp_path, monkeypatch):
    _make_tests(tmp_path, ["a.test.ts", "b.test.ts"])
    pollution = tmp_path / "polluted"

    ran = []

    def runner(f):
        ran.append(f)
        pollution.mkdir()  # first one pollutes

    monkeypatch.setattr(find_polluter, "_run_test", runner)

    rc = find_polluter.main(["prog", str(pollution), _glob(tmp_path, "*.test.ts")])
    assert rc == 1
    assert [os.path.basename(f) for f in ran] == ["a.test.ts"]


# --------------------------------------------------------------------------
# scan: pollution already present before any test -> all skipped
# --------------------------------------------------------------------------
def test_pollution_preexisting_skips_all_and_returns_0(tmp_path, monkeypatch, capsys):
    _make_tests(tmp_path, ["a.test.ts", "b.test.ts"])
    pollution = tmp_path / "polluted"
    pollution.mkdir()  # exists before the scan starts

    ran = []
    monkeypatch.setattr(find_polluter, "_run_test", lambda f: ran.append(f))

    rc = find_polluter.main(["prog", str(pollution), _glob(tmp_path, "*.test.ts")])

    # nothing was run (every iteration skipped), and it is not flagged as a polluter
    assert ran == []
    assert rc == 0
    out = capsys.readouterr().out
    assert "already exists" in out


# --------------------------------------------------------------------------
# glob behaviour: empty match set
# --------------------------------------------------------------------------
def test_no_matching_files_returns_0(tmp_path, monkeypatch, capsys):
    pollution = tmp_path / "polluted"
    ran = []
    monkeypatch.setattr(find_polluter, "_run_test", lambda f: ran.append(f))

    rc = find_polluter.main(["prog", str(pollution), _glob(tmp_path, "*.nomatch")])

    assert rc == 0
    assert ran == []
    out = capsys.readouterr().out
    assert "Found 0 test files" in out


# --------------------------------------------------------------------------
# glob behaviour: recursive ** and sorted ordering
# --------------------------------------------------------------------------
def test_recursive_glob_and_sorted_order(tmp_path, monkeypatch):
    _make_tests(
        tmp_path,
        ["src/z.test.ts", "src/nested/a.test.ts", "src/m.test.ts"],
    )
    pollution = tmp_path / "polluted"

    ran = []
    monkeypatch.setattr(find_polluter, "_run_test", lambda f: ran.append(f))

    rc = find_polluter.main(
        ["prog", str(pollution), _glob(tmp_path, "src/**/*.test.ts")]
    )
    assert rc == 0
    # recursive matched all three; output order is sorted lexicographically
    assert ran == sorted(ran)
    assert len(ran) == 3


# --------------------------------------------------------------------------
# _run_test integration boundary: portable executable resolution, no shell
# --------------------------------------------------------------------------
def test_run_test_resolves_npm_via_which_and_no_shell(monkeypatch):
    """_run_test must use shutil.which (portable, npm.cmd on Windows) and must
    not invoke a shell. Capture the subprocess.run call without executing npm."""
    captured = {}

    def fake_which(name):
        captured["which_arg"] = name
        return "/fake/path/to/npm"

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["kwargs"] = kwargs

        class R:
            returncode = 0

        return R()

    monkeypatch.setattr(find_polluter.shutil, "which", fake_which)
    monkeypatch.setattr(find_polluter.subprocess, "run", fake_run)

    find_polluter._run_test("some/file.test.ts")

    assert captured["which_arg"] == "npm"
    # command is a list (argv form) -> no shell word-splitting
    assert isinstance(captured["cmd"], list)
    assert captured["cmd"] == ["/fake/path/to/npm", "test", "some/file.test.ts"]
    # shell must not be enabled
    assert captured["kwargs"].get("shell", False) is False
    # check=False so a failing test run does not raise
    assert captured["kwargs"].get("check", None) is False


def test_run_test_falls_back_to_npm_when_not_on_path(monkeypatch):
    captured = {}
    monkeypatch.setattr(find_polluter.shutil, "which", lambda name: None)

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd

        class R:
            returncode = 0

        return R()

    monkeypatch.setattr(find_polluter.subprocess, "run", fake_run)
    find_polluter._run_test("f.test.ts")
    assert captured["cmd"][0] == "npm"


# --------------------------------------------------------------------------
# non-ASCII path handling (embedded via chr, never pasted literally)
# --------------------------------------------------------------------------
def test_non_ascii_pollution_path(tmp_path, monkeypatch):
    # U+00E9 (e-acute) + U+1F600 (emoji) embedded without literal glyphs.
    weird_name = "poll" + chr(0x00E9) + chr(0x1F600)
    _make_tests(tmp_path, ["a.test.ts"])
    pollution = tmp_path / weird_name

    def runner(f):
        pollution.mkdir()

    monkeypatch.setattr(find_polluter, "_run_test", runner)
    rc = find_polluter.main(["prog", str(pollution), _glob(tmp_path, "*.test.ts")])
    assert rc == 1
    assert pollution.exists()
