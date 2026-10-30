"""Tests for winpytest.py - ship a repo's committed tree to a Windows host and run pytest there.

ssh and scp are the true external edge, so they go through the injected runner; git runs for
real against a throwaway repo.
"""

import json
import subprocess
from pathlib import Path

import pytest

import winpytest as W


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=str(repo), check=True, capture_output=True, timeout=30)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@example.test")
    _git(root, "config", "user.name", "t")
    (root / "test_a.py").write_text("def test_a():\n    assert True\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "seed")
    return root


class FakeRemote:
    """Records every ssh/scp argv; answers each with the scripted (rc, out) for its step name."""

    def __init__(self, answers=None):
        self.calls: list[list[str]] = []
        self.answers = answers or {}

    def __call__(self, argv):
        if argv[0] == "git":
            done = subprocess.run(argv, capture_output=True, text=True, timeout=30, check=False)
            return done.returncode, done.stdout, done.stderr
        self.calls.append(argv)
        remote = argv[-1]
        for key, answer in self.answers.items():
            if key in remote:
                return answer
        return 0, "", ""


def _args(repo, *extra):
    return ["--host", "winbox", "--user", "tester", "--key", "/keys/k", "--repo", str(repo),
            "--dest", "C:/work/proj", *extra]


# ---- the destination ---------------------------------------------------------------------------

@pytest.mark.parametrize("dest", ["C:\\", "C:/", "D:\\work", "work\\proj", "/c/work/proj",
                                  "C:\\work\\..\\Windows", "C:\\work\\a\"b"])
def test_a_destination_a_recursive_delete_must_never_reach_is_refused(dest):
    assert W.dest_problem(W.windows_path(dest)) is not None


def test_a_forward_slash_destination_is_written_with_backslashes():
    assert W.windows_path("C:/work/proj") == "C:\\work\\proj"
    assert W.dest_problem("C:\\work\\proj") is None


# ---- the steps ---------------------------------------------------------------------------------

def test_the_steps_keep_mkdir_out_of_the_rmdir_call_and_scp_to_a_backslash_path(repo):
    fake = FakeRemote({"pytest": (0, "==== 1 passed in 0.01s ====\n", "")})
    assert W.execute(_args(repo), runner=fake) == 0
    remotes = [c[-1] for c in fake.calls if c[0] == "ssh"]
    assert remotes[0] == 'if exist "C:\\work\\proj" rmdir /s /q "C:\\work\\proj"'
    assert remotes[1] == 'mkdir "C:\\work\\proj"'
    scp = next(c for c in fake.calls if c[0] == "scp")
    assert scp[-1] == "tester@winbox:C:\\work\\proj\\src.tar"
    assert remotes[2].startswith('cd /d "C:\\work\\proj" && tar -xf src.tar && uv run ')
    for call in fake.calls:
        assert "BatchMode=yes" in call and "/keys/k" in call


def test_env_extras_and_pytest_args_reach_the_remote_command(repo):
    fake = FakeRemote({"pytest": (0, "1 passed in 0.01s\n", "")})
    code = W.execute(_args(repo, "--env", "MODE=fast", "--extra", "dev", "--",
                           "-k", "a and not b", "-q"), runner=fake)
    assert code == 0
    remote = [c[-1] for c in fake.calls if c[0] == "ssh"][-1]
    assert 'set "MODE=fast" && ' in remote
    assert "--extra dev" in remote
    assert remote.endswith('pytest -k "a and not b" -q')


def test_a_tracked_uv_lock_runs_frozen(repo):
    (repo / "uv.lock").write_text("version = 1\n", encoding="utf-8")
    _git(repo, "add", "uv.lock")
    _git(repo, "commit", "-qm", "lock")
    fake = FakeRemote({"pytest": (0, "1 passed in 0.01s\n", "")})
    W.execute(_args(repo), runner=fake)
    assert "uv run --frozen " in [c[-1] for c in fake.calls if c[0] == "ssh"][-1]


# ---- verdicts ----------------------------------------------------------------------------------

def test_failing_tests_exit_1_and_report_the_summary(repo, capsys):
    out = "test_a.py F\n=========== 1 failed, 2 passed in 0.31s ===========\n"
    assert W.execute(_args(repo, "--json"), runner=FakeRemote({"pytest": (1, out, "")})) == 1
    data = json.loads(capsys.readouterr().out)["data"]
    assert data["pytest_rc"] == 1 and data["summary"] == "1 failed, 2 passed in 0.31s"


@pytest.mark.parametrize("rc", [2, 3, 4, 5, 255])
def test_a_run_that_did_not_produce_a_verdict_exits_2(repo, rc):
    assert W.execute(_args(repo), runner=FakeRemote({"pytest": (rc, "", "boom")})) == 2


def test_a_failed_mkdir_stops_before_anything_is_shipped(repo, capsys):
    fake = FakeRemote({"mkdir": (1, "", "Access is denied.")})
    assert W.execute(_args(repo, "--json"), runner=fake) == 2
    assert not any(c[0] == "scp" for c in fake.calls)
    env = json.loads(capsys.readouterr().out)
    assert env["ok"] is False and "mkdir" in env["error"]


def test_uncommitted_changes_are_named_as_not_shipped(repo, capsys):
    (repo / "test_a.py").write_text("def test_a():\n    assert False\n", encoding="utf-8")
    W.execute(_args(repo), runner=FakeRemote({"pytest": (0, "1 passed in 0.01s\n", "")}))
    assert "uncommitted" in capsys.readouterr().err


@pytest.mark.parametrize(("text", "summary"), [
    ("x\n===== 3 passed, 1 skipped in 2.10s =====\n", "3 passed, 1 skipped in 2.10s"),
    ("..\n2 passed in 0.05s\n", "2 passed in 0.05s"),
    ("=== no tests ran in 0.01s ===\n", "no tests ran in 0.01s"),
    ("no summary here\n", None),
])
def test_the_summary_line_is_the_last_pytest_tally(text, summary):
    assert W.pytest_summary(text) == summary


def test_a_bad_destination_is_refused_before_any_remote_call(repo):
    fake = FakeRemote()
    args = ["--host", "winbox", "--repo", str(repo), "--dest", "C:\\"]
    assert W.execute(args, runner=fake) == 2
    assert fake.calls == []


def test_rc_1_without_a_tally_line_is_no_verdict_not_failed_tests(repo, capsys):
    # cmd's `cd /d X && tar -xf ... && uv run pytest` gives errorlevel 1 when cd, tar or uv's sync
    # fails, so rc 1 alone does not prove pytest ran.
    fake = FakeRemote({"pytest": (1, "", "tar: Error opening archive: Failed to open 'src.tar'")})
    assert W.execute(_args(repo, "--json"), runner=fake) == 2
    env = json.loads(capsys.readouterr().out)
    assert env["ok"] is False and env["data"]["summary"] is None
    assert "no pytest tally" in env["error"]


def test_rc_1_under_qq_still_counts_as_failed_tests_by_its_short_summary(repo):
    # `pytest -qq` prints no tally line, only the short test summary; that still proves it ran.
    out = ("F\n=========================== short test summary info ============================\n"
           "FAILED test_a.py::test_a - assert False\n")
    assert W.execute(_args(repo, "--", "-qq"), runner=FakeRemote({"pytest": (1, out, "")})) == 1


# Real pytest 9.2.0 output for one failing and one passing test, captured with `--color=yes` (and
# with `-qq --color=yes`): with colour on, every rule line starts with an SGR escape, so a parser
# anchored on `^=` sees neither the tally nor the short summary header.
_COLOURED_FAILED = (
    '\x1b[1m============================= test session starts ==============================\x1b[0m\n'
    'platform linux -- Python 3.15.0, pytest-9.2.0, pluggy-1.7.0\n'
    'rootdir: /tmp/claude-1000/winpy-5pPcKQ/t\n'
    'collected 2 items\n'
    '\n'
    'test_x.py \x1b[31mF\x1b[0m\x1b[32m.\x1b[0m\x1b[31m                                                             [100%]\x1b[0m\n'
    '\n'
    '=================================== FAILURES ===================================\n'
    '\x1b[31m\x1b[1m____________________________________ test_a ____________________________________\x1b[0m\n'
    '\n'
    '    \x1b[0m\x1b[94mdef\x1b[39;49;00m\x1b[90m \x1b[39;49;00m\x1b[92mtest_a\x1b[39;49;00m():\x1b[90m\x1b[39;49;00m\n'
    '>       \x1b[94massert\x1b[39;49;00m \x1b[94m1\x1b[39;49;00m == \x1b[94m2\x1b[39;49;00m\x1b[90m\x1b[39;49;00m\n'
    '\x1b[1m\x1b[31mE       assert 1 == 2\x1b[0m\n'
    '\n'
    '\x1b[1m\x1b[31mtest_x.py\x1b[0m:2: AssertionError\n'
    '\x1b[36m\x1b[1m=========================== short test summary info ============================\x1b[0m\n'
    '\x1b[31mFAILED\x1b[0m test_x.py::\x1b[1mtest_a\x1b[0m - assert 1 == 2\n'
    '\x1b[31m========================= \x1b[31m\x1b[1m1 failed\x1b[0m, \x1b[32m1 passed\x1b[0m\x1b[31m in 0.04s\x1b[0m\x1b[31m ==========================\x1b[0m\n'
)
_COLOURED_FAILED_QQ = (
    '\x1b[31mF\x1b[0m\x1b[32m.\x1b[0m\x1b[31m                                                                       [100%]\x1b[0m\n'
    '=================================== FAILURES ===================================\n'
    '\x1b[31m\x1b[1m____________________________________ test_a ____________________________________\x1b[0m\n'
    '\n'
    '    \x1b[0m\x1b[94mdef\x1b[39;49;00m\x1b[90m \x1b[39;49;00m\x1b[92mtest_a\x1b[39;49;00m():\x1b[90m\x1b[39;49;00m\n'
    '>       \x1b[94massert\x1b[39;49;00m \x1b[94m1\x1b[39;49;00m == \x1b[94m2\x1b[39;49;00m\x1b[90m\x1b[39;49;00m\n'
    '\x1b[1m\x1b[31mE       assert 1 == 2\x1b[0m\n'
    '\n'
    '\x1b[1m\x1b[31mtest_x.py\x1b[0m:2: AssertionError\n'
    '\x1b[36m\x1b[1m=========================== short test summary info ============================\x1b[0m\n'
    '\x1b[31mFAILED\x1b[0m test_x.py::\x1b[1mtest_a\x1b[0m - assert 1 == 2\n'
)


def test_coloured_output_still_yields_its_tally():
    assert W.pytest_summary(_COLOURED_FAILED) == "1 failed, 1 passed in 0.04s"


@pytest.mark.parametrize("out", [_COLOURED_FAILED, _COLOURED_FAILED_QQ])
def test_rc_1_with_coloured_output_counts_as_failed_tests(repo, out):
    fake = FakeRemote({"pytest": (1, out, "")})
    assert W.execute(_args(repo, "--", "--color=yes"), runner=fake) == 1
