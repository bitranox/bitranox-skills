"""Tests for suite_busy.py - is a test suite already running in this checkout or its worktrees?

The load-bearing tests launch REAL child processes with a controlled cwd and argv inside a temp
git repository that has linked worktrees, and ask the jig about them through its CLI. Three
properties are pinned with a planted positive and a planted negative each:

- a suite process in a worktree is found, and one outside every checkout is not;
- matching is by argv TOKEN, so `mypytestish` and a `bash -c '... pytest ...'` string are not
  suites;
- the jig never reports itself or the shell that ran it, even when both argvs carry the token.

Linux only, like the jig: the real-process tests are skipped where there is no /proc.
"""

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

import suite_busy as S

TOOL = Path(__file__).resolve().parents[1] / "scripts" / "suite_busy.py"
HAS_PROC = Path("/proc/self/cmdline").is_file()
needs_proc = pytest.mark.skipif(not HAS_PROC, reason="the jig reads /proc, which only Linux has")

_SLEEP = "import time; time.sleep(60)"
_STARTUP_S = 10.0
_GIT_TIMEOUT = 30
_CLI_TIMEOUT = 60


# ---- the argv rules -----------------------------------------------------------------------------

def _rule(argv: list[str]) -> str | None:
    for name, predicate in S.builtin_matchers():
        if predicate(argv):
            return name
    return None


@pytest.mark.parametrize("argv, expected", [
    (["pytest", "-q"], "pytest"),
    (["/repo/.venv/bin/pytest", "-x"], "pytest"),
    (["/repo/.venv/bin/python", "/repo/.venv/bin/pytest", "-q"], "pytest"),
    (["python3", "-m", "pytest", "tests/"], "pytest"),
    (["python3.12", "-u", "-mpytest"], "pytest"),
    (["python3", "-W", "error", "/x/py.test"], "pytest"),
    (["python", "/x/bin/coverage", "run", "-m", "pytest"], "pytest"),
    (["/home/u/.local/share/uv/tools/bmk/bin/python", "/home/u/.local/bin/bmk", "test"], "bmk"),
    (["bmk", "test-all"], "bmk"),
    (["python3", "-m", "bmk", "push"], "bmk"),
    (["make", "test"], "make"),
    (["make", "-j4", "testintegration"], "make"),
    (["make", "-C", "sub", "-f", "Makefile.ci", "test"], "make"),
    (["gmake", "release"], "make"),
])
def test_a_gate_process_is_recognised_by_its_argv_tokens(argv, expected):
    assert _rule(argv) == expected


@pytest.mark.parametrize("argv", [
    ["mypytestish", "-q"],
    ["python3", "/x/mypytestish"],
    ["bash", "-c", "cd /repo && pytest -q"],
    ["grep", "-rn", "pytest", "src"],
    ["vim", "pytest.ini"],
    ["python3", "-c", "import pytest", "x"],
    ["python3", "/x/pytest_helper.py"],
    ["uv", "run", "pytest"],
    ["bmk", "--version"],
    ["make", "clean"],
    ["make", "-C", "test"],
    ["make", "-f", "release", "all"],
    ["less", "/tmp/make-test.log"],
    [],
])
def test_a_substring_or_a_mention_is_not_a_gate(argv):
    """`uv run pytest` is the parent of the python process that IS pytest - that one is found."""
    assert _rule(argv) is None


def test_a_user_match_needs_its_tokens_consecutive_and_whole():
    name, cargo = S.token_matcher("cargo test")
    assert name == "match:cargo test"
    assert cargo(["/usr/bin/cargo", "test", "--release"])
    assert not cargo(["cargo", "build", "test"])
    assert not cargo(["cargo-test"])
    _, word = S.token_matcher("pytest")
    assert not word(["mypytestish"])


def test_an_empty_user_match_is_refused():
    with pytest.raises(S.SuiteBusyError):
        S.token_matcher("   ")


# ---- checkouts ----------------------------------------------------------------------------------

def test_worktree_porcelain_is_parsed_main_first():
    porcelain = ("worktree /r\nHEAD 1\nbranch refs/heads/main\n\n"
                 "worktree /r/.wt/a\nHEAD 2\nbranch refs/heads/topic\n\n"
                 "worktree /elsewhere/b\nHEAD 3\ndetached\nprunable gitdir file points to "
                 "non-existent location\n\n")
    assert S.parse_worktrees(porcelain) == [
        S.Checkout("/r", "main"), S.Checkout("/r/.wt/a", "topic"),
        S.Checkout("/elsewhere/b", "(detached)")]


@pytest.mark.parametrize("cwd, expected", [
    ("/r", "/r"),
    ("/r/src", "/r"),
    ("/r/.wt/a", "/r/.wt/a"),
    ("/r/.wt/a/tests", "/r/.wt/a"),
    ("/rr", None),
    ("/r2/src", None),
])
def test_a_process_belongs_to_the_deepest_checkout_holding_its_cwd(cwd, expected):
    checkouts = [S.Checkout("/r", "main"), S.Checkout("/r/.wt/a", "topic")]
    found = S.attribute(cwd, checkouts)
    assert (found.path if found else None) == expected


# ---- the scan over a fake /proc: exclusion is applied, and is what hides a match -----------------

def _fake_proc(root: Path, pid: int, cwd: str, argv: list[str], ppid: int) -> None:
    d = root / str(pid)
    d.mkdir(parents=True)
    (d / "cwd").symlink_to(cwd)
    (d / "cmdline").write_bytes(("\0".join(argv) + "\0").encode("utf-8"))
    (d / "stat").write_text(f"{pid} (x) S {ppid} 0 0\n", encoding="utf-8")


@needs_proc                    # the fake tree's cwd links are POSIX paths; the jig is Linux-only
def test_excluded_pids_are_never_reported_and_only_exclusion_hides_them(tmp_path):
    proc = tmp_path / "proc"
    _fake_proc(proc, 10, "/r", ["bash", "-c", "x", "pytest"], 1)
    _fake_proc(proc, 20, "/r", ["python3", "suite_busy.py", "--match", "pytest"], 10)
    _fake_proc(proc, 30, "/r/sub", ["pytest", "-q"], 1)
    checkouts = [S.Checkout("/r", "main")]
    rules = [*S.builtin_matchers(), S.token_matcher("pytest")]
    everything = S.scan(proc, checkouts, rules, exclude=set())
    assert sorted(b.pid for b in everything.busy) == [10, 20, 30]           # the control
    assert S.ancestors(20, proc) == {20, 10, 1}
    assert [b.pid for b in S.scan(proc, checkouts, rules, S.ancestors(20, proc)).busy] == [30]


@needs_proc
def test_an_unreadable_cwd_is_counted_not_examined(tmp_path):
    proc = tmp_path / "proc"
    (proc / "40").mkdir(parents=True)                                         # no cwd link
    _fake_proc(proc, 41, "/elsewhere", ["sleep", "5"], 1)
    result = S.scan(proc, [S.Checkout("/r", "main")], S.builtin_matchers(), set())
    assert (result.processes_examined, result.unreadable_cwd, result.busy) == (1, 1, ())


def _hosted_runner_proc(root: Path, work: str, *, self_cwd: bool = True) -> int:
    """A /proc shaped like a hosted CI runner, with the CALLER as the jig. Returns the jig's pid.

    Every process the test user can read is the jig or one of its ancestors (an agent, its
    worker, the step's shell); everything else belongs to another user, so its cwd link cannot
    be read. The jig's pid is this test process's own, which is how `execute` finds its chain in
    the fake tree through the `proc_root` seam, exactly as it does in the real one.
    """
    me = os.getpid()
    (root / "1").mkdir(parents=True)                                       # init: root's, unreadable
    (root / "1" / "stat").write_text("1 (init) S 0 0 0\n", encoding="utf-8")
    (root / "2").mkdir()                                                   # another user's daemon
    (root / "2" / "stat").write_text("2 (daemon) S 1 0 0\n", encoding="utf-8")
    _fake_proc(root, 50, "/home/ci-user", ["ci-agent", "run"], 1)
    _fake_proc(root, 60, "/home/ci-user", ["ci-worker", "spawnclient"], 50)
    _fake_proc(root, 70, work, ["bash", "-e", "step.sh"], 60)
    if self_cwd:
        _fake_proc(root, me, work, ["python3", "suite_busy.py", "--json"], 70)
    else:                                                                  # listed, cwd unreadable
        (root / str(me)).mkdir()
        (root / str(me) / "stat").write_text(f"{me} (python3) S 70 0 0\n", encoding="utf-8")
    return me


@needs_proc
def test_a_runner_where_only_the_jig_s_own_chain_is_readable_answers_free(repo, tmp_path,
                                                                           capsys):
    """The hosted-runner shape that made CI red: nothing readable is left once the jig's own
    chain is set aside. /proc WAS read - the chain itself was - so the answer is "nothing is
    running" with the unreadable processes in `skipped`, never "no answer is possible"."""
    proc = tmp_path / "runner-proc"
    _hosted_runner_proc(proc, str(repo["linked"]))
    code = S.execute(["--repo", str(repo["main"]), "--json-bare"], proc_root=proc)
    env = json.loads(capsys.readouterr().out)
    assert code == 0, env
    assert env["ok"] is True and env["data"]["busy"] == []
    assert env["data"]["processes_examined"] == 0
    assert env["data"]["processes_excluded"] == 4                 # the jig, bash, worker, agent
    assert env["data"]["processes_unreadable"] == 1               # pid 2; init is an ancestor
    assert env["skipped"] == ["1 process(es) whose cwd could not be read"]


@needs_proc
def test_a_runner_where_nothing_at_all_is_readable_is_still_a_refusal(repo, tmp_path, capsys):
    """The guard the counting change must keep: the jig's chain is LISTED, but not one cwd in the
    whole tree could be read, so the scan read nothing and the answer is a refusal."""
    proc = tmp_path / "blind-proc"
    _hosted_runner_proc(proc, str(repo["linked"]), self_cwd=False)
    for pid in (50, 60, 70):                                       # the whole chain unreadable too
        (proc / str(pid) / "cwd").unlink()
    code = S.execute(["--repo", str(repo["main"]), "--json-bare"], proc_root=proc)
    env = json.loads(capsys.readouterr().out)
    assert code == 2, env
    assert env["ok"] is False and "zero processes" in env["error"]
    assert env["data"]["processes_excluded"] == 0 and env["data"]["processes_examined"] == 0


# ---- real processes in a real repository --------------------------------------------------------

def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=str(cwd), check=True, capture_output=True,
                   timeout=_GIT_TIMEOUT)


@pytest.fixture
def repo(tmp_path: Path) -> dict[str, Path]:
    main = tmp_path / "main"
    main.mkdir()
    _git(main, "init", "-q", "-b", "main")
    _git(main, "config", "user.email", "t@example.test")
    _git(main, "config", "user.name", "t")
    (main / "README").write_text("x\n", encoding="utf-8")
    _git(main, "add", "README")
    _git(main, "commit", "-qm", "seed")
    linked = tmp_path / "linked"
    nested = main / ".wt" / "nested"
    _git(main, "worktree", "add", "-q", "-b", "topic", str(linked))
    _git(main, "worktree", "add", "-q", "-b", "inner", str(nested))
    outside = tmp_path / "outside"
    outside.mkdir()
    return {"main": main, "linked": linked, "nested": nested, "outside": outside}


@pytest.fixture
def spawn(tmp_path: Path):
    """Start a sleeping python whose argv and cwd the test chooses, and return its pid.

    `name` makes argv[0] a symlink of that name to this interpreter, so /proc shows e.g.
    `.../pytest -c <sleep> ...` while the process is an ordinary sleeper; `script` instead runs a
    sleeping script file of that name. The start is confirmed from /proc (bounded) before the
    jig is asked, so a slow fork cannot read as "not found".
    """
    children: list[subprocess.Popen[bytes]] = []
    bindir = tmp_path / "bin"
    bindir.mkdir()

    def start(cwd: Path, *rest: str, name: str | None = None, script: str | None = None,
              code: str = _SLEEP) -> int:
        program = sys.executable
        if name is not None:
            program = str(bindir / name)
            os.symlink(sys.executable, program)
        if script is not None:
            path = bindir / script
            path.write_text(code + "\n", encoding="utf-8")
            cmd = [program, str(path), *rest]
        else:
            cmd = [program, "-c", code, *rest]
        child = subprocess.Popen(cmd, cwd=str(cwd), stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)
        children.append(child)
        want = ("\0".join(cmd) + "\0").encode("utf-8")
        deadline = time.monotonic() + _STARTUP_S
        while time.monotonic() < deadline:
            try:
                if Path(f"/proc/{child.pid}/cmdline").read_bytes() == want:
                    return child.pid
            except OSError:
                pass
            time.sleep(0.02)
        raise AssertionError(f"child never showed argv {cmd!r} within {_STARTUP_S}s")

    yield start
    for child in children:
        if child.poll() is None:
            child.send_signal(signal.SIGKILL)
        child.wait(timeout=10)


def run_cli(*args: str, cwd: Path,
            timeout: float = _CLI_TIMEOUT) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(TOOL), *args], cwd=str(cwd), capture_output=True,
                          text=True, encoding="utf-8", check=False, timeout=timeout)


def _busy(r: subprocess.CompletedProcess[str]) -> list[dict]:
    return json.loads(r.stdout)["data"]["busy"]


@needs_proc
def test_a_suite_in_a_linked_worktree_is_found_and_attributed(repo, spawn):
    pid = spawn(repo["linked"], name="pytest")
    r = run_cli("--repo", str(repo["main"]), "--json", cwd=repo["outside"])
    assert r.returncode == 1, r.stdout + r.stderr
    env = json.loads(r.stdout)
    assert env["ok"] is True
    assert env["data"]["checkouts_examined"] == 3 and env["data"]["processes_examined"] > 0
    assert [(b["pid"], b["rule"], b["checkout"]) for b in env["data"]["busy"]] \
        == [(pid, "pytest", os.path.realpath(repo["linked"]))]


@needs_proc
def test_the_same_suite_outside_every_checkout_is_not_found(repo, spawn):
    spawn(repo["outside"], name="pytest")
    r = run_cli("--repo", str(repo["linked"]), "--json", cwd=repo["outside"])
    assert r.returncode == 0, r.stdout + r.stderr
    assert _busy(r) == []


@needs_proc
def test_a_suite_in_a_nested_worktree_belongs_to_that_worktree(repo, spawn):
    pid = spawn(repo["nested"], "-m", "pytest")
    r = run_cli("--repo", str(repo["main"]), "--json-bare", cwd=repo["outside"])
    assert r.returncode == 1, r.stdout + r.stderr
    assert [(b["pid"], b["checkout"]) for b in _busy(r)] \
        == [(pid, os.path.realpath(repo["nested"]))]


@needs_proc
def test_a_python_running_a_script_named_pytest_is_found(repo, spawn):
    pid = spawn(repo["main"], "-q", script="pytest")
    r = run_cli("--repo", str(repo["main"]), "--json", cwd=repo["outside"])
    assert r.returncode == 1, r.stdout + r.stderr
    assert [b["pid"] for b in _busy(r)] == [pid]


@needs_proc
def test_a_name_merely_containing_pytest_is_not_found(repo, spawn):
    spawn(repo["linked"], name="mypytestish")
    spawn(repo["linked"], "-q", script="mypytestish-run")
    r = run_cli("--repo", str(repo["main"]), "--match", "pytest", "--json", cwd=repo["outside"])
    assert r.returncode == 0, r.stdout + r.stderr
    assert _busy(r) == []


@needs_proc
def test_a_make_gate_target_is_found_and_a_user_rule_is_applied(repo, spawn):
    make = spawn(repo["main"], "-C", "sub", "test", name="make")
    cargo = spawn(repo["linked"], name="cargo")
    r = run_cli("--repo", str(repo["main"]), "--json", cwd=repo["outside"])
    assert [b["pid"] for b in _busy(r)] == [make]
    r = run_cli("--repo", str(repo["main"]), "--match", "cargo", "--no-builtin", "--json",
                cwd=repo["outside"])
    assert [(b["pid"], b["rule"]) for b in _busy(r)] == [(cargo, "match:cargo")]


@needs_proc
def test_the_jig_never_reports_itself_or_the_shell_that_ran_it(repo, spawn):
    """Both argvs carry the `pytest` token (`--match pytest`, and the shell's $0), and both sit
    in the worktree. Only the exclusion keeps them out, which the fake-/proc test above shows."""
    script = (f'"{sys.executable}" "{TOOL}" --repo . --match pytest --json; exit $?')
    shell_argv = ["bash", "-c", script, "pytest"]
    assert S.token_matcher("pytest")[1](shell_argv)                        # it WOULD match
    r = subprocess.run(shell_argv, cwd=str(repo["linked"]), capture_output=True, text=True,
                       encoding="utf-8", check=False, timeout=_CLI_TIMEOUT)
    assert r.returncode == 0, r.stdout + r.stderr
    assert _busy(r) == []
    # The planted positive through the same command: a real suite beside it IS reported.
    pid = spawn(repo["linked"], name="pytest")
    r = subprocess.run(shell_argv, cwd=str(repo["linked"]), capture_output=True, text=True,
                       encoding="utf-8", check=False, timeout=_CLI_TIMEOUT)
    assert r.returncode == 1, r.stdout + r.stderr
    assert [b["pid"] for b in _busy(r)] == [pid]


@needs_proc
def test_wait_returns_free_once_the_suite_ends(repo, spawn):
    short = "import time; time.sleep(1.5)"
    spawn(repo["main"], name="pytest", code=short)
    r = run_cli("--repo", str(repo["main"]), "--wait-s", "20", "--interval", "0.2", "--json",
                cwd=repo["outside"])
    assert r.returncode == 0, r.stdout + r.stderr
    data = json.loads(r.stdout)["data"]
    assert data["polls"] > 1 and data["timed_out"] is False and data["waited_s"] < 20


@needs_proc
def test_wait_reports_the_deadline_when_the_suite_outlives_it(repo, spawn):
    spawn(repo["main"], name="pytest")
    r = run_cli("--repo", str(repo["main"]), "--wait-s", "0.6", "--interval", "0.2", "--json",
                cwd=repo["outside"])
    assert r.returncode == 1, r.stdout + r.stderr
    data = json.loads(r.stdout)["data"]
    assert data["timed_out"] is True and data["polls"] >= 2


# ---- refusals ----------------------------------------------------------------------------------

def test_a_platform_without_proc_is_refused(tmp_path, capsys):
    assert S.execute(["--repo", str(tmp_path)], proc_root=tmp_path / "no-proc-here") == 2
    assert "Linux only" in capsys.readouterr().err


@needs_proc
def test_zero_processes_examined_is_a_refusal_not_free(repo, tmp_path, capsys):
    empty = tmp_path / "empty-proc"
    empty.mkdir()
    assert S.execute(["--repo", str(repo["main"]), "--json-bare"], proc_root=empty) == 2
    env = json.loads(capsys.readouterr().out)
    assert env["ok"] is False and env["data"]["checkouts_examined"] == 3


@needs_proc
def test_a_path_outside_any_repository_is_refused(tmp_path):
    r = run_cli("--repo", str(tmp_path), "--json", cwd=tmp_path)
    assert r.returncode == 2
    assert "Traceback" not in r.stderr
    assert json.loads(r.stdout)["ok"] is False


@pytest.mark.parametrize("args, says", [
    (["--wait-s", "-1"], "--wait-s"), (["--interval", "0"], "--interval"),
    (["--no-builtin"], "nothing to look for"), (["--match", " "], "at least one token"),
])
def test_bad_arguments_are_refused(tmp_path, args, says, capsys):
    # proc_root is any existing directory, so the argument check is reached on every platform.
    assert S.execute(["--repo", str(tmp_path), *args], proc_root=tmp_path) == 2
    assert says in capsys.readouterr().err


def test_a_usage_error_still_prints_the_envelope(tmp_path):
    r = run_cli("--json-bare", "--wait-s", "soon", cwd=tmp_path)
    assert r.returncode == 2
    assert json.loads(r.stdout)["ok"] is False
