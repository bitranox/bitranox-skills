"""abscore: the floor runs the profile's argv lists; the score reads result.json and the peers."""
import dataclasses
import json
import os
import sys
import time
from pathlib import Path

import _ablib as L
import abprofile as P
import abscore as S
import abstream
import pytest
from abproc_testkit import gone_within, kill_if_alive

FIXTURES = Path(__file__).resolve().parent / "fixtures"
SHA = "0" * 40


def _profile(tmp_path, scratch_repo, skills_repo, suite=False):
    extra = '\nsuite = "check.sh"\nsuite_cmd = ["sh", "{suite}"]' if suite else ""
    text = f'''
[workpiece]
repo = "{scratch_repo}"
base = "{(scratch_repo / '.base').read_text()}"
task_file = "task.md"
[control]
skills_ref = "{(skills_repo / '.ref').read_text()}"
skill = "demo-skill"
[[variant]]
name = "V1"
dir = "variants/V1"
changes = ["x"]
[floor]
gate = ["./gate.sh"]{extra}
cache_paths = []
timeout_s = 30
[run]
model = "opus"
n = 2
deadline_s = 100
max_tokens = 5000
'''
    p = tmp_path / "abtest.toml"
    p.write_text(text, encoding="utf-8")
    return P.load_profile(p)


def _pure_profile(tmp_path, gate=("true",), timeout_s=30, warmth_tolerance=0.25):
    """A Profile built from its dataclasses: no git repo, no shell script, so it runs on every OS."""
    return P.Profile(
        path=tmp_path / "abtest.toml",
        workpiece=P.Workpiece(repo=tmp_path, base=SHA, task_file="task.md"),
        control=P.Control(skills_ref=SHA, skill="demo-skill"),
        variants=(P.Variant(name="V1", dir="variants/V1", changes=("x",), markers=()),),
        floor=P.Floor(gate=tuple(gate), suite=None, suite_cmd=(), cache_paths=(), timeout_s=timeout_s),
        run=P.Run(model="opus", n=2, deadline_s=100, max_tokens=5000, warmth_tolerance=warmth_tolerance,
                  env_keep=P.DEFAULT_ENV_KEEP, home_links=P.DEFAULT_HOME_LINKS))


def test_floor_runs_gate_then_suite_and_logs(tmp_path, scratch_repo, skills_repo):
    prof = _profile(tmp_path, scratch_repo, skills_repo, suite=True)
    (scratch_repo / "check.sh").write_text("echo suite ok\n", encoding="utf-8")
    res = S.run_floor(scratch_repo, prof, tmp_path / "logs")
    assert res["passed"] is True and [s["name"] for s in res["steps"]] == ["gate", "suite"]
    assert "suite ok" in Path(res["steps"][1]["log"]).read_text(encoding="utf-8")


def test_floor_fails_on_the_gate_and_skips_the_suite(tmp_path, scratch_repo, skills_repo):
    prof = _profile(tmp_path, scratch_repo, skills_repo, suite=True)
    (scratch_repo / "BROKEN").write_text("", encoding="utf-8")
    res = S.run_floor(scratch_repo, prof, tmp_path / "logs")
    assert res["passed"] is False and [s["name"] for s in res["steps"]] == ["gate"] and res["steps"][0]["rc"] == 1


def test_floor_records_a_gate_that_cannot_start_as_a_failed_step(tmp_path):
    prof = _pure_profile(tmp_path, gate=[str(tmp_path / "no-such-gate")])
    res = S.run_floor(tmp_path, prof, tmp_path / "logs")
    assert res["passed"] is False and res["steps"][0]["rc"] == S.RC_NOT_STARTED
    assert "could not start" in Path(res["steps"][0]["log"]).read_text(encoding="utf-8")


def test_floor_records_a_timed_out_gate_as_a_failed_step(tmp_path):
    prof = _pure_profile(tmp_path, gate=[sys.executable, "-c", "import time; time.sleep(10)"], timeout_s=1)
    res = S.run_floor(tmp_path, prof, tmp_path / "logs")
    assert res["passed"] is False and res["steps"][0]["rc"] == S.RC_TIMEOUT
    assert "timed out after 1 s" in Path(res["steps"][0]["log"]).read_text(encoding="utf-8")


def test_floor_suite_does_not_run_after_a_gate_that_cannot_start(tmp_path):
    prof = _pure_profile(tmp_path, gate=[str(tmp_path / "no-such-gate")])
    prof = dataclasses.replace(prof, floor=dataclasses.replace(prof.floor, suite="s.py", suite_cmd=("x", "{suite}")))
    res = S.run_floor(tmp_path, prof, tmp_path / "logs")
    assert [s["name"] for s in res["steps"]] == ["gate"]


def _result(**over):
    base = {"arm": "r1-C", "model": "claude-opus-5-5", "has_result": True, "stop_reason": "finished",
            "void_reasons": [], "total_cost_usd": 0.25, "main_new_tokens": 20010, "first_cache_read": 11000,
            "per_model": {"claude-opus-5-5": {"new_tokens": 20010, "cache_read": 11000, "output_tokens": 50, "cost_usd": 0.25}},
            "wall_s": 1.2, "guard_changes": [], "floor": {"passed": True, "steps": []}, "bundle_commits": 1,
            "skipped_lines": 0}
    base.update(over)
    return base


def _score(tmp_path, res, peers, name="r1-C", **profile_over):
    arm = tmp_path / "arms" / name
    arm.mkdir(parents=True)
    (arm / "result.json").write_text(json.dumps(res), encoding="utf-8")
    return S.score_arm(arm, _pure_profile(tmp_path, **profile_over), peers=peers)


TWO_PEERS = [_result(first_cache_read=11000), _result(first_cache_read=11200)]


def test_score_of_a_clean_arm(tmp_path):
    arm = tmp_path / "arms" / "r1-C"
    arm.mkdir(parents=True)
    (arm / "result.json").write_text(json.dumps(_result()), encoding="utf-8")
    s = S.score_arm(arm, _pure_profile(tmp_path), peers=[_result(first_cache_read=11500)])
    assert s["void"] == [] and s["cost_usd"] == 0.25 and s["floor_passed"] is True
    assert json.loads((arm / "scores.json").read_text(encoding="utf-8")) == s


def test_score_carries_the_listed_fields(tmp_path):
    s = _score(tmp_path, _result(), TWO_PEERS)
    assert set(s) == {"arm", "cost_usd", "per_model", "main_new_tokens", "first_cache_read", "floor_passed",
                      "bundle_commits", "void", "wall_s", "floor_error", "floor_steps", "warmth_checked",
                      "result_subtype", "store_changes", "store_guard", "sandbox", "task_file", "task_sha256",
                      "subagents", "idea_markers", "floor_suite"}
    assert (s["arm"], s["main_new_tokens"], s["bundle_commits"], s["wall_s"]) == ("r1-C", 20010, 1, 1.2)


def test_score_reads_subagents_ideas_and_the_suite_from_the_arm_dir(tmp_path):
    """The three readings come from the arm's own kept files, never from result.json."""
    arm = tmp_path / "arms" / "r1-C"
    sub = arm / "transcripts" / "-ws" / "s1" / "subagents"
    sub.mkdir(parents=True)
    for name, start, end in (("a", "10:00", "10:09"), ("b", "10:01", "10:02"), ("c", "10:01", "10:05")):
        lines = [json.dumps({"timestamp": f"2026-11-08T{t}:00Z"}) for t in (start, end)]
        (sub / f"agent-{name}.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    write = {"type": "tool_use", "id": "t1", "name": "Write",
             "input": {"file_path": ".bitranox/sdd/progress.md", "content": "[abx] idea=2 split the plan\n"}}
    (arm / "stream.jsonl").write_text(json.dumps({"type": "assistant", "message": {"id": "m", "content": [write]}})
                                      + "\n", encoding="utf-8")
    (arm / S.SUITE_LOG).write_text((FIXTURES / "cargo-compile-error.log").read_text(encoding="utf-8"), encoding="utf-8")
    floor = {"passed": False, "steps": [{"name": "gate", "rc": 0, "error": None},
                                        {"name": "suite", "rc": 101, "error": None}]}
    (arm / "result.json").write_text(json.dumps(_result(floor=floor)), encoding="utf-8")
    s = S.score_arm(arm, _pure_profile(tmp_path), peers=TWO_PEERS)
    assert s["subagents"] == {"transcripts": 3, "max_concurrent": 3, "untimed": 0}
    assert s["idea_markers"] == {"writes": 1, "ideas": {"2": {"count": 1, "first": "[abx] idea=2 split the plan"}}}
    assert s["floor_suite"]["outcome"] == "does_not_compile" and "run_sandboxed" in s["floor_suite"]["missing"]
    assert s["floor_steps"] == [{"name": "gate", "rc": 0}, {"name": "suite", "rc": 101}], "existing keys unchanged"


def test_an_arm_with_no_kept_files_scores_none_for_all_three(tmp_path):
    s = _score(tmp_path, _result(), TWO_PEERS)
    assert (s["subagents"], s["idea_markers"], s["floor_suite"]) == (None, None, None)


def test_the_suite_log_run_floor_writes_is_the_one_the_score_reads(tmp_path):
    prof = _pure_profile(tmp_path, gate=[sys.executable, "-c", "pass"])
    suite = [sys.executable, "-c", "print('test result: FAILED. 1 passed; 3 failed; 0 ignored'); raise SystemExit(101)"]
    prof = dataclasses.replace(prof, floor=dataclasses.replace(prof.floor, suite="s.py", suite_cmd=tuple(suite)))
    arm = tmp_path / "arms" / "r1-C"
    floor = S.run_floor(tmp_path, prof, arm)
    (arm / "result.json").write_text(json.dumps(_result(floor=floor)), encoding="utf-8")
    out = S.score_arm(arm, prof, peers=TWO_PEERS)["floor_suite"]
    assert (out["outcome"], out["rc"], out["tests_failed"], out["tests_total"]) == ("tests_failed", 101, 3, 4)


def test_the_real_stream_summary_of_the_fixture_scores_clean(tmp_path):
    """The key names score_arm reads are the ones abstream's summary actually writes."""
    res = abstream.account_stream_file(FIXTURES / "stream-control.jsonl").summary()
    res.update({"arm": "r1-C", "stop_reason": "finished", "wall_s": 1.0, "guard_changes": [],
                "floor": {"passed": True, "steps": []}, "bundle_commits": 1})
    s = _score(tmp_path, res, TWO_PEERS)
    assert s["void"] == [] and s["cost_usd"] == 0.25 and s["first_cache_read"] == 11000


def test_every_void_rule_fires_by_itself(tmp_path):
    cases = {
        "model": _result(void_reasons=["session model is 'x', not an opus id"]),
        "no result": _result(has_result=False, total_cost_usd=None),
        "deadline": _result(stop_reason="deadline"),
        "token_cap": _result(stop_reason="token_cap"),
        "warmth": _result(first_cache_read=20000),
    }
    for name, res in cases.items():
        s = _score(tmp_path, res, TWO_PEERS, name=f"r1-{name}")
        assert len(s["void"]) == 1, (name, s["void"])


TAKEN = {"taken": True, "entries": 3, "skipped": None}


def test_a_store_change_is_recorded_and_never_voids(tmp_path):
    """User decision 2026-11-04: concurrent sessions share the store, so a change is adjudicated."""
    changes = ["changed: slug x", "added: slug y"]
    s = _score(tmp_path, _result(guard=TAKEN, guard_changes=list(changes)), TWO_PEERS)
    assert s["void"] == []
    assert s["store_changes"] == changes and s["store_guard"] == S.STORE_GUARD_CHANGED == "changed"


def test_a_taken_and_verified_snapshot_with_no_change_is_clean(tmp_path):
    s = _score(tmp_path, _result(guard=TAKEN, guard_changes=[]), TWO_PEERS)
    assert (s["store_guard"], s["store_changes"], s["void"]) == (S.STORE_GUARD_CLEAN, [], [])


def test_a_snapshot_not_taken_is_skipped_not_clean(tmp_path):
    skipped = _result(guard={"taken": False, "entries": 0, "skipped": "no .claude-memory store"}, guard_changes=[],
                      guard_skipped="no .claude-memory store")
    s = _score(tmp_path, skipped, TWO_PEERS, name="r1-a")
    assert (s["store_guard"], s["store_changes"], s["void"]) == (S.STORE_GUARD_SKIPPED, [], [])
    assert _score(tmp_path, _result(), TWO_PEERS, name="r1-b")["store_guard"] == "skipped", "no guard record at all"


def test_a_taken_snapshot_whose_after_check_never_ran_is_skipped(tmp_path):
    res = _result(guard=TAKEN)
    del res["guard_changes"]  # the arm ended before _guard_after: nothing was compared
    assert _score(tmp_path, res, TWO_PEERS)["store_guard"] == S.STORE_GUARD_SKIPPED


def test_every_stream_void_reason_is_carried_unchanged(tmp_path):
    stream_reasons = [abstream.NO_INIT_REASON,
                      "model claude-x-1 appears in modelUsage, not an opus or haiku id",
                      "model claude-x-1 appears in an assistant message, not an opus or haiku id",
                      abstream.SYNTHETIC_REASON_PREFIX + "You've hit your usage limit"]
    s = _score(tmp_path, _result(void_reasons=list(stream_reasons), stop_reason="void"), TWO_PEERS)
    assert s["void"] == stream_reasons


def test_skipped_lines_alone_do_not_void_an_arm_with_a_result(tmp_path):
    assert _score(tmp_path, _result(skipped_lines=3), TWO_PEERS)["void"] == []


def test_skipped_lines_are_named_in_the_no_result_reason(tmp_path):
    s = _score(tmp_path, _result(has_result=False, total_cost_usd=None, skipped_lines=1), TWO_PEERS)
    assert len(s["void"]) == 1 and "1 unparsable stream line" in s["void"][0]


def test_a_void_stop_with_its_reasons_lost_is_still_void(tmp_path):
    assert _score(tmp_path, _result(stop_reason="void"), TWO_PEERS)["void"] != []


def test_an_unknown_or_missing_stop_reason_is_void(tmp_path):
    assert _score(tmp_path, _result(stop_reason="interrupted"), TWO_PEERS, name="a")["void"] != []
    res = _result()
    del res["stop_reason"]
    assert _score(tmp_path, res, TWO_PEERS, name="b")["void"] != []


def test_warmth_needs_two_peers_and_uses_the_tolerance(tmp_path):
    arm = tmp_path / "arms" / "r1-C"
    arm.mkdir(parents=True)
    (arm / "result.json").write_text(json.dumps(_result(first_cache_read=20000)), encoding="utf-8")
    prof = _pure_profile(tmp_path)
    assert S.score_arm(arm, prof, peers=[_result(first_cache_read=11000)])["void"] == [], "one peer: no median yet"
    assert S.score_arm(arm, prof, peers=[_result(first_cache_read=16100), _result(first_cache_read=16100)])["void"] == []
    assert S.score_arm(arm, prof, peers=[_result(first_cache_read=15000), _result(first_cache_read=15000)])["void"] != []


def test_warmth_reads_the_profile_tolerance(tmp_path):
    peers = [_result(first_cache_read=15000), _result(first_cache_read=15000)]
    assert _score(tmp_path, _result(first_cache_read=20000), peers, name="a", warmth_tolerance=0.5)["void"] == []
    assert _score(tmp_path, _result(first_cache_read=20000), peers, name="b", warmth_tolerance=0.25)["void"] != []


def test_warmth_ignores_peers_without_a_reading(tmp_path):
    peers = [_result(first_cache_read=11000), _result(first_cache_read=None), _result(first_cache_read=True)]
    assert _score(tmp_path, _result(first_cache_read=20000), peers)["void"] == [], "one usable peer: no median"


def test_warmth_against_a_zero_median(tmp_path):
    peers = [_result(first_cache_read=0), _result(first_cache_read=0)]
    assert _score(tmp_path, _result(first_cache_read=0), peers, name="a")["void"] == []
    assert _score(tmp_path, _result(first_cache_read=5000), peers, name="b")["void"] != []


def test_warmth_skips_an_arm_without_a_reading(tmp_path):
    assert _score(tmp_path, _result(first_cache_read=None), TWO_PEERS)["void"] == []


# --- a timed-out floor step takes its whole process tree with it ---------------------------------

POSIX_ONLY = pytest.mark.skipif(sys.platform == "win32",
                                reason="the A/B harness is Linux only (POSIX process groups); Windows is unsupported")

GRACE_S = 0.3


def _grace_bound(timeout_s):
    """The most a timed-out step may cost: its timeout plus two graces (the stop, then the sweep).

    The 1.5 s slack covers interpreter start-up and polling; it is far below KILL_GRACE_S, so a
    path that waits the default grace instead of the kill_grace_s passed in exceeds it.
    """
    return timeout_s + 2 * GRACE_S + 1.5

# A grandchild that records its pid (atomically, so a reader never sees a half-written file) and
# sleeps. argv: pidfile, mode; a mode starting "ignore" ignores SIGTERM.
_GRANDCHILD = (
    "import os, signal, sys, time\n"
    "if sys.argv[2].startswith('ignore'): signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
    "tmp = sys.argv[1] + '.tmp'\n"
    "open(tmp, 'w').write(str(os.getpid()))\n"
    "os.replace(tmp, sys.argv[1])\n"
    "time.sleep(30)\n")

# The gate starts the grandchild, waits for its pid, then sleeps itself: a timeout that kills only
# the direct child leaves the grandchild running. With "ignore" the grandchild ignores SIGTERM and
# holds the pipes past the gate's death; the stop's SIGKILL removes it (and the sweep of the group
# after the step would). With "ignore_devnull" it ignores SIGTERM and holds no pipe, so the step's
# output closes once the gate dies and only that sweep removes it. With "leader_ignore" the GATE
# ignores SIGTERM (set after the grandchild started, which inherits no SIG_IGN and dies on the
# SIGTERM): the leader then holds the pipes and is never reaped unless the stop escalates to
# SIGKILL. A mode ending "devnull" puts the grandchild's stdio on /dev/null.
_TREE_GATE = """
import signal, subprocess, sys, time
from pathlib import Path
pidfile, mode, child = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
devnull = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
subprocess.Popen([sys.executable, "-c", child, str(pidfile), mode], **(devnull if mode.endswith("devnull") else {}))
if mode == "leader_ignore":
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
while not pidfile.exists():
    time.sleep(0.01)
time.sleep(float(sys.argv[4]))
"""


def _pid_in(pidfile):
    return int(pidfile.read_text(encoding="utf-8")) if pidfile.exists() else None


def _tree_gate(pidfile, mode, gate_sleep_s):
    return [sys.executable, "-c", _TREE_GATE, str(pidfile), mode, _GRANDCHILD, str(gate_sleep_s)]


def _timed_floor(tmp_path, prof):
    """(run_floor's result, its wall time) with the short test grace."""
    t0 = time.monotonic()
    res = S.run_floor(tmp_path, prof, tmp_path / "logs", kill_grace_s=GRACE_S)
    return res, time.monotonic() - t0


@POSIX_ONLY
@pytest.mark.parametrize("on_term", ["exit", "ignore", "ignore_devnull", "leader_ignore"])
def test_a_timed_out_floor_step_leaves_no_process_behind(tmp_path, on_term):
    pidfile = tmp_path / "grandchild.pid"
    prof = _pure_profile(tmp_path, gate=_tree_gate(pidfile, on_term, 30), timeout_s=1)
    res, elapsed = _timed_floor(tmp_path, prof)
    pid = _pid_in(pidfile)
    try:
        assert res["steps"][0]["rc"] == S.RC_TIMEOUT
        assert pid is not None and gone_within(pid), f"grandchild {pid} survived the floor's timeout"
        assert elapsed < _grace_bound(1), elapsed
    finally:
        kill_if_alive(pid)


@POSIX_ONLY
def test_a_clean_step_leaves_no_background_process_behind(tmp_path):
    """A gate that starts a daemon with its stdio on /dev/null and exits 0 passes, and the daemon is gone."""
    pidfile = tmp_path / "daemon.pid"
    prof = _pure_profile(tmp_path, gate=_tree_gate(pidfile, "devnull", 0), timeout_s=30)
    res = S.run_floor(tmp_path, prof, tmp_path / "logs", kill_grace_s=GRACE_S)
    pid = _pid_in(pidfile)
    try:
        assert res["passed"] is True and res["steps"][0]["error"] is None
        assert pid is not None and gone_within(pid, 2.0), f"daemon {pid} outlived its floor step"
    finally:
        kill_if_alive(pid)


# The gate starts a grandchild that inherits its stdout and stderr, then exits 0 at once: the
# leader is done long before the timeout, but the step's output stays open until the grandchild dies.
_HELD_OPEN_GATE = """
import subprocess, sys, time
from pathlib import Path
pidfile = Path(sys.argv[1])
subprocess.Popen([sys.executable, "-c", sys.argv[2], str(pidfile), "exit"])
while not pidfile.exists():
    time.sleep(0.01)
print("gate ok")
"""


@POSIX_ONLY
def test_a_step_whose_output_is_held_open_past_the_timeout_keeps_its_rc_and_fails(tmp_path):
    pidfile = tmp_path / "holder.pid"
    gate = [sys.executable, "-c", _HELD_OPEN_GATE, str(pidfile), _GRANDCHILD]
    prof = _pure_profile(tmp_path, gate=gate, timeout_s=1)
    prof = dataclasses.replace(prof, floor=dataclasses.replace(prof.floor, suite="s.py", suite_cmd=("x", "{suite}")))
    res, elapsed = _timed_floor(tmp_path, prof)
    pid = _pid_in(pidfile)
    try:
        (step,) = res["steps"]
        assert (step["rc"], step["error"]) == (0, S.ERROR_HELD_OPEN)
        assert elapsed < _grace_bound(1), elapsed
        assert res["passed"] is False, "a step that hits the timeout is not a pass"
        assert "gate ok" in Path(step["log"]).read_text(encoding="utf-8")
        assert _score(tmp_path, _result(floor=res), TWO_PEERS)["floor_error"] == (
            "gate: output held open past the timeout by a process the step started (rc 0)")
        assert pid is not None and gone_within(pid), f"holder {pid} survived the floor step"
    finally:
        kill_if_alive(pid)


# --- the floor's environment ---------------------------------------------------------------------

# PYTHONHOME pointing at a missing dir would stop the gate's interpreter from starting at all, so
# a leak of it shows as a failed gate as well as in the names it prints.
_LEAKS = ("VIRTUAL_ENV", "UV_PROJECT_ENVIRONMENT", "PYTHONPATH", "PYTHONHOME", "GIT_CONFIG_PARAMETERS",
          "GIT_CONFIG_COUNT", "GIT_CONFIG_KEY_0", "GIT_CONFIG_VALUE_0", "GIT_CONFIG_KEY_1", "GIT_CONFIG_VALUE_1",
          "GIT_CONFIG_GLOBAL", "GIT_CONFIG_SYSTEM", "GIT_DIR", "GIT_WORK_TREE",
          "GIT_INDEX_FILE", "GIT_COMMON_DIR", "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES",
          "GIT_NAMESPACE", "GIT_CEILING_DIRECTORIES", "GIT_LITERAL_PATHSPECS", "GIT_GLOB_PATHSPECS",
          "GIT_NOGLOB_PATHSPECS", "GIT_ICASE_PATHSPECS")
_KEPT = ("PYTHONUTF8", "ABSCORE_TEST_KEEP", "GIT_SSH_COMMAND", "GIT_CONFIG_NOSYSTEM")


def test_the_floor_runs_without_the_launcher_venv_and_the_git_redirects(tmp_path, monkeypatch):
    for name in _LEAKS:
        monkeypatch.setenv(name, str(tmp_path / "leak"))
    for name in _KEPT:
        monkeypatch.setenv(name, "1")
    venv = tmp_path / "launcher-venv"
    monkeypatch.setenv("VIRTUAL_ENV", str(venv))
    bin_dir = venv / ("Scripts" if sys.platform == "win32" else "bin")
    # The venv's bin dir first and again later with a trailing separator; the gate is an absolute
    # path, so the synthetic PATH does not have to find anything.
    others = [str(tmp_path / "a"), str(tmp_path / "b"), str(tmp_path / "c")]
    path = [str(bin_dir), others[0], str(bin_dir) + os.sep, others[1], "", others[2]]
    monkeypatch.setenv("PATH", os.pathsep.join(path))
    # The gate prints the variable NAMES and PATH only, never another value.
    gate = [sys.executable, "-c", "import json, os; print(json.dumps([sorted(os.environ), os.environ['PATH']]))"]
    res = S.run_floor(tmp_path, _pure_profile(tmp_path, gate=gate), tmp_path / "logs")
    log = Path(res["steps"][0]["log"]).read_text(encoding="utf-8")
    assert res["passed"] is True, log
    names, seen_path = json.loads(log)
    assert set(names).isdisjoint(_LEAKS), sorted(set(names) & set(_LEAKS))
    assert set(_KEPT) <= set(names)
    assert seen_path.split(os.pathsep) == [others[0], others[1], "", others[2]]


# --- floor_error and floor_steps -----------------------------------------------------------------

def _scored_floor(tmp_path, gate, timeout_s=30):
    floor = S.run_floor(tmp_path, _pure_profile(tmp_path, gate=gate, timeout_s=timeout_s), tmp_path / "logs",
                        kill_grace_s=GRACE_S)
    return _score(tmp_path, _result(floor=floor), TWO_PEERS)


def test_floor_error_names_a_step_that_could_not_start(tmp_path):
    s = _scored_floor(tmp_path, [str(tmp_path / "no-such-gate")])
    assert s["floor_error"] == "gate: could not start (rc 127)"
    assert s["floor_steps"] == [{"name": "gate", "rc": 127}] and s["floor_passed"] is False


def test_floor_error_names_a_step_that_timed_out(tmp_path):
    t0 = time.monotonic()
    s = _scored_floor(tmp_path, [sys.executable, "-c", "import time; time.sleep(10)"], timeout_s=1)
    assert time.monotonic() - t0 < _grace_bound(1)
    assert s["floor_error"] == "gate: timed out after 1 s (rc 124)"
    assert s["floor_steps"] == [{"name": "gate", "rc": 124}]


def test_a_gate_that_exits_124_itself_ran_and_has_no_floor_error(tmp_path):
    s = _scored_floor(tmp_path, [sys.executable, "-c", "raise SystemExit(124)"])
    assert s["floor_error"] is None and s["floor_steps"] == [{"name": "gate", "rc": 124}]


def test_a_clean_floor_has_no_error_and_lists_its_steps(tmp_path):
    s = _scored_floor(tmp_path, [sys.executable, "-c", "pass"])
    assert s["floor_error"] is None and s["floor_steps"] == [{"name": "gate", "rc": 0}]
    assert s["floor_passed"] is True


# --- a missing stop reason -----------------------------------------------------------------------

MISSING_STOP = "no stop reason recorded (the arm did not end normally: interrupted or crashed)"


def test_a_missing_stop_reason_says_the_arm_did_not_end_normally(tmp_path):
    res = _result()
    del res["stop_reason"]
    assert _score(tmp_path, res, TWO_PEERS, name="a")["void"] == [MISSING_STOP]
    assert _score(tmp_path, _result(stop_reason=None), TWO_PEERS, name="b")["void"] == [MISSING_STOP]


def test_an_unknown_stop_reason_keeps_its_own_text(tmp_path):
    (reason,) = _score(tmp_path, _result(stop_reason="interrupted"), TWO_PEERS)["void"]
    assert "'interrupted'" in reason and reason != MISSING_STOP


# --- first_cache_read as an integral float --------------------------------------------------------

def test_warmth_accepts_an_integral_float_reading_for_the_arm_and_its_peers(tmp_path):
    float_peers = [_result(first_cache_read=11000.0), _result(first_cache_read=11200.0)]
    assert _score(tmp_path, _result(first_cache_read=20000.0), TWO_PEERS, name="a")["void"] != []
    assert _score(tmp_path, _result(first_cache_read=20000), float_peers, name="b")["void"] != []
    assert _score(tmp_path, _result(first_cache_read=11000.0), float_peers, name="c")["void"] == []


def test_warmth_refuses_a_fractional_float_and_a_bool(tmp_path):
    s = _score(tmp_path, _result(first_cache_read=20000.5), TWO_PEERS, name="a")
    assert s["void"] == [] and s["warmth_checked"] is False
    s = _score(tmp_path, _result(first_cache_read=True), TWO_PEERS, name="b")
    assert s["void"] == [] and s["warmth_checked"] is False


# --- warmth_checked and result_subtype -----------------------------------------------------------

def test_warmth_checked_says_whether_the_check_ran(tmp_path):
    assert _score(tmp_path, _result(), TWO_PEERS, name="a")["warmth_checked"] is True
    assert _score(tmp_path, _result(), TWO_PEERS[:1], name="b")["warmth_checked"] is False
    assert _score(tmp_path, _result(first_cache_read=None), TWO_PEERS, name="c")["warmth_checked"] is False


def test_result_subtype_is_copied_and_does_not_void(tmp_path):
    s = _score(tmp_path, _result(result_subtype="error_max_turns"), TWO_PEERS, name="a")
    assert s["result_subtype"] == "error_max_turns" and s["void"] == []
    assert _score(tmp_path, _result(), TWO_PEERS, name="b")["result_subtype"] is None


# --- whole-branch review: the floor runs the SEALED suite -----------------------------------------

def _sealed(tmp_path, text):
    path = tmp_path / "sealed" / "check.sh"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return S.SealedSuite(path=path, sha256=L.sha256_file(path))


def test_the_floor_runs_the_sealed_suite_over_the_arms_own(tmp_path, scratch_repo, skills_repo):
    prof = _profile(tmp_path, scratch_repo, skills_repo, suite=True)
    (scratch_repo / "check.sh").write_text("echo the arm's suite\nexit 0\n", encoding="utf-8")
    res = S.run_floor(scratch_repo, prof, tmp_path / "logs", sealed_suite=_sealed(tmp_path, "echo sealed\nexit 3\n"))
    assert res["passed"] is False and res["steps"][1]["rc"] == 3 and res["steps"][1]["error"] is None
    assert "sealed" in Path(res["steps"][1]["log"]).read_text(encoding="utf-8")


def test_the_floor_places_a_suite_the_tree_does_not_have(tmp_path, scratch_repo, skills_repo):
    prof = _profile(tmp_path, scratch_repo, skills_repo, suite=True)
    assert not (scratch_repo / "check.sh").exists()
    res = S.run_floor(scratch_repo, prof, tmp_path / "logs", sealed_suite=_sealed(tmp_path, "exit 0\n"))
    assert res["passed"] is True and [s["rc"] for s in res["steps"]] == [0, 0]


def _symlinked_parent(tmp_path, scratch_repo):
    outside = tmp_path / "outside"
    outside.mkdir()
    (scratch_repo / "acceptance").symlink_to(outside, target_is_directory=True)
    return outside


@pytest.mark.parametrize(("setup", "error"), [
    ("tampered", S.ERROR_SUITE_HASH),
    ("directory", S.ERROR_SUITE_NOT_PLACED),
    ("parent-outside", S.ERROR_SUITE_NOT_PLACED),
])
def test_a_suite_that_cannot_be_placed_as_sealed_fails_without_running(tmp_path, scratch_repo, skills_repo, setup, error):
    prof = _profile(tmp_path, scratch_repo, skills_repo, suite=True)
    rel = "acceptance/check.sh" if setup == "parent-outside" else "check.sh"
    prof = dataclasses.replace(prof, floor=dataclasses.replace(prof.floor, suite=rel))
    sealed = _sealed(tmp_path, "exit 0\n")
    outside = None
    if setup == "tampered":
        sealed.path.write_text("exit 0 # edited after the seal\n", encoding="utf-8")
    elif setup == "directory":
        (scratch_repo / "check.sh").mkdir()
    else:
        outside = _symlinked_parent(tmp_path, scratch_repo)
    res = S.run_floor(scratch_repo, prof, tmp_path / "logs", sealed_suite=sealed)
    suite = res["steps"][1]
    assert res["passed"] is False and suite["rc"] == S.RC_NOT_STARTED and suite["error"].startswith(error)
    assert outside is None or list(outside.iterdir()) == [], "nothing was written outside the tree"
