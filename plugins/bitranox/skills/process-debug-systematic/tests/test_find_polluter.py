"""Tests for find_polluter.py.

``main(argv, run_test=...)`` takes the test runner as an injected seam: a callable returning
``(exit code, output)`` for one test file. The fakes here create the pollution path on a chosen
file, or answer the way a broken npm does, so no real npm runs. ``_run_test`` itself is the
integration boundary and is exercised against ``subprocess.run`` / ``shutil.which`` (true
external edges) and once against a real child process.

Exit contract: 0 clean, 1 found, 2 error (usage, empty glob, runner never ran), 3 cannot check
(the path exists before any test runs).
"""
import os
import subprocess
import sys

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


class Runner:
    """Records each test file and answers like npm would; optionally creates the pollution."""

    def __init__(self, pollution=None, polluter=None, rc=0, output=""):
        self.ran = []
        self.pollution = pollution
        self.polluter = polluter
        self.rc = rc
        self.output = output

    def __call__(self, test_file):
        self.ran.append(test_file)
        if self.polluter is not None and os.path.basename(test_file) == self.polluter:
            self.pollution.mkdir()
        return self.rc, self.output

    def names(self):
        return [os.path.basename(f) for f in self.ran]


# --------------------------------------------------------------------------
# argument parsing
# --------------------------------------------------------------------------
def test_main_wrong_arg_count_is_a_usage_error(capsys):
    """Usage used to share exit 1 with "found", so a typo read as a polluter."""
    assert find_polluter.main(["prog"], run_test=Runner()) == 2
    assert find_polluter.main(["prog", "only-one"], run_test=Runner()) == 2
    assert find_polluter.main(["prog", "a", "b", "c"], run_test=Runner()) == 2
    assert "Usage:" in capsys.readouterr().err


# --------------------------------------------------------------------------
# scan: no polluter
# --------------------------------------------------------------------------
def test_no_polluter_returns_0_and_runs_every_test(tmp_path):
    _make_tests(tmp_path, ["a.test.ts", "b.test.ts", "c.test.ts"])
    runner = Runner()
    rc = find_polluter.main(["prog", str(tmp_path / "polluted"), _glob(tmp_path, "*.test.ts")],
                            run_test=runner)
    assert rc == 0
    assert runner.names() == ["a.test.ts", "b.test.ts", "c.test.ts"]


def test_some_failing_tests_do_not_stop_a_clean_scan(tmp_path):
    """A failing test is normal; only EVERY run failing says the runner never ran them."""
    _make_tests(tmp_path, ["a.test.ts", "b.test.ts"])

    def runner(test_file):
        return (1, "1 failing") if test_file.endswith("a.test.ts") else (0, "ok")

    rc = find_polluter.main(["prog", str(tmp_path / "polluted"), _glob(tmp_path, "*.test.ts")],
                            run_test=runner)
    assert rc == 0


# --------------------------------------------------------------------------
# scan: a real polluter is detected
# --------------------------------------------------------------------------
def test_finds_polluter_and_returns_1(tmp_path, capsys):
    _make_tests(tmp_path, ["a.test.ts", "b.test.ts", "c.test.ts"])
    pollution = tmp_path / "polluted"
    runner = Runner(pollution, polluter="b.test.ts")
    rc = find_polluter.main(["prog", str(pollution), _glob(tmp_path, "*.test.ts")], run_test=runner)
    assert rc == 1
    assert runner.names() == ["a.test.ts", "b.test.ts"]   # stopped after the polluter
    out = capsys.readouterr().out
    assert "FOUND POLLUTER" in out and "b.test.ts" in out


def test_first_test_is_polluter(tmp_path):
    _make_tests(tmp_path, ["a.test.ts", "b.test.ts"])
    pollution = tmp_path / "polluted"
    runner = Runner(pollution, polluter="a.test.ts")
    assert find_polluter.main(["prog", str(pollution), _glob(tmp_path, "*.test.ts")],
                              run_test=runner) == 1
    assert runner.names() == ["a.test.ts"]


def test_a_polluter_that_also_fails_is_still_found(tmp_path):
    _make_tests(tmp_path, ["a.test.ts"])
    pollution = tmp_path / "polluted"
    runner = Runner(pollution, polluter="a.test.ts", rc=1, output="1 failing")
    assert find_polluter.main(["prog", str(pollution), _glob(tmp_path, "*.test.ts")],
                              run_test=runner) == 1


# --------------------------------------------------------------------------
# pollution already present: nothing can be learned, so refuse
# --------------------------------------------------------------------------
def test_preexisting_pollution_is_refused_not_reported_clean(tmp_path, capsys):
    """Skipping every test and then saying "all tests clean" is a false negative."""
    _make_tests(tmp_path, ["a.test.ts", "b.test.ts"])
    pollution = tmp_path / "polluted"
    pollution.mkdir()
    runner = Runner()
    rc = find_polluter.main(["prog", str(pollution), _glob(tmp_path, "*.test.ts")], run_test=runner)
    assert rc == 3
    assert runner.ran == []
    captured = capsys.readouterr()
    assert "remove it first" in captured.err
    assert "all tests clean" not in captured.out


# --------------------------------------------------------------------------
# glob behaviour
# --------------------------------------------------------------------------
def test_a_glob_that_matches_nothing_is_an_error(tmp_path, capsys):
    runner = Runner()
    rc = find_polluter.main(["prog", str(tmp_path / "polluted"), _glob(tmp_path, "*.nomatch")],
                            run_test=runner)
    assert rc == 2
    assert runner.ran == []
    captured = capsys.readouterr()
    assert "Found 0 test files" in captured.out
    assert "all tests clean" not in captured.out


def test_recursive_glob_and_sorted_order(tmp_path):
    _make_tests(tmp_path, ["src/z.test.ts", "src/nested/a.test.ts", "src/m.test.ts"])
    runner = Runner()
    rc = find_polluter.main(["prog", str(tmp_path / "polluted"), _glob(tmp_path, "src/**/*.test.ts")],
                            run_test=runner)
    assert rc == 0
    assert runner.ran == sorted(runner.ran)
    assert len(runner.ran) == 3


# --------------------------------------------------------------------------
# a runner that never ran the tests is an error, not a clean scan
# --------------------------------------------------------------------------
@pytest.mark.parametrize("rc, output", [
    (1, 'npm ERR! Missing script: "test"\n'),
    (1, 'npm error Missing script: "test"\n'),
    (254, "npm ERR! code ENOENT\nnpm ERR! syscall open\n"),
    (254, ""),
])
def test_npm_own_failure_aborts_the_scan(tmp_path, capsys, rc, output):
    _make_tests(tmp_path, ["a.test.ts", "b.test.ts"])
    runner = Runner(rc=rc, output=output)
    result = find_polluter.main(["prog", str(tmp_path / "polluted"), _glob(tmp_path, "*.test.ts")],
                                run_test=runner)
    assert result == 2
    assert len(runner.ran) == 1      # it stops at the first sign the runner is broken
    assert "all tests clean" not in capsys.readouterr().out


def test_every_run_failing_is_an_error_not_clean(tmp_path, capsys):
    _make_tests(tmp_path, ["a.test.ts", "b.test.ts"])
    runner = Runner(rc=1, output="Error: Cannot find module 'jest'\n")
    rc = find_polluter.main(["prog", str(tmp_path / "polluted"), _glob(tmp_path, "*.test.ts")],
                            run_test=runner)
    assert rc == 2
    assert "Cannot find module" in capsys.readouterr().err


def test_a_runner_that_cannot_start_is_exit_2_not_a_traceback(tmp_path, monkeypatch, capsys):
    """No npm on PATH: FileNotFoundError used to escape as a traceback with exit 1 (= found)."""
    _make_tests(tmp_path, ["a.test.ts"])
    monkeypatch.setattr(find_polluter.shutil, "which", lambda name: None)

    def no_such_binary(cmd, **kwargs):
        raise FileNotFoundError(2, "No such file or directory", cmd[0])

    monkeypatch.setattr(find_polluter.subprocess, "run", no_such_binary)
    rc = find_polluter.main(["prog", str(tmp_path / "polluted"), _glob(tmp_path, "*.test.ts")])
    assert rc == 2
    assert "cannot start the test runner" in capsys.readouterr().err


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
        return subprocess.CompletedProcess(cmd, 0, stdout="out\n", stderr="err\n")

    monkeypatch.setattr(find_polluter.shutil, "which", fake_which)
    monkeypatch.setattr(find_polluter.subprocess, "run", fake_run)

    rc, output = find_polluter._run_test("some/file.test.ts")

    assert captured["which_arg"] == "npm"
    assert captured["cmd"] == ["/fake/path/to/npm", "test", "some/file.test.ts"]
    assert captured["kwargs"].get("shell", False) is False
    assert captured["kwargs"].get("check", None) is False
    assert captured["kwargs"].get("encoding") == "utf-8"
    assert (rc, output) == (0, "out\nerr\n")


def test_run_test_falls_back_to_npm_when_not_on_path(monkeypatch):
    captured = {}
    monkeypatch.setattr(find_polluter.shutil, "which", lambda name: None)

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(find_polluter.subprocess, "run", fake_run)
    find_polluter._run_test("f.test.ts")
    assert captured["cmd"][0] == "npm"


def test_run_test_captures_a_real_child_process(monkeypatch):
    """One run through the real subprocess seam, with the interpreter standing in for npm."""
    monkeypatch.setattr(find_polluter.shutil, "which", lambda name: sys.executable)
    rc, output = find_polluter._run_test("x.test.ts")  # `python test x.test.ts`: no file 'test'
    assert rc != 0
    assert "test" in output


# --------------------------------------------------------------------------
# non-ASCII path handling (embedded via chr, never pasted literally)
# --------------------------------------------------------------------------
def test_non_ascii_pollution_path(tmp_path):
    weird_name = "poll" + chr(0x00E9) + chr(0x1F600)
    _make_tests(tmp_path, ["a.test.ts"])
    pollution = tmp_path / weird_name
    runner = Runner(pollution, polluter="a.test.ts")
    rc = find_polluter.main(["prog", str(pollution), _glob(tmp_path, "*.test.ts")], run_test=runner)
    assert rc == 1
    assert pollution.exists()


def test_a_non_cp1252_test_name_does_not_crash_the_report(tmp_path):
    """A Windows pipe is cp1252; a test file name outside it crashed the progress line."""
    _make_tests(tmp_path, ["a" + chr(0x0141) + ".test.ts"])
    script = os.path.join(os.path.dirname(find_polluter.__file__), "find_polluter.py")
    # PATH points at an empty dir so no real npm can run: the progress line prints before the
    # runner starts, and the run then ends as a runner error (exit 2), never a traceback.
    env = dict(os.environ, PYTHONIOENCODING="cp1252", PATH=str(tmp_path / "no-bin"))
    env.pop("PYTHONUTF8", None)
    proc = subprocess.run([sys.executable, script, str(tmp_path / "polluted"),
                           _glob(tmp_path, "*.test.ts")], capture_output=True, env=env,
                          cwd=str(tmp_path), timeout=60)
    assert b"Traceback" not in proc.stderr, proc.stderr.decode("utf-8", "replace")
    assert b"Testing:" in proc.stdout
    assert proc.returncode == 2
