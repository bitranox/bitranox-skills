"""abscore: the floor runs the profile's argv lists; the score reads result.json and the peers."""
import dataclasses
import json
import os
import signal
import sys
import time
from pathlib import Path

import abprofile as P
import abscore as S
import abstream
import pytest

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
                      "result_subtype"}
    assert (s["arm"], s["main_new_tokens"], s["bundle_commits"], s["wall_s"]) == ("r1-C", 20010, 1, 1.2)


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
        "guard": _result(guard_changes=["changed: slug x"]),
        "warmth": _result(first_cache_read=20000),
    }
    for name, res in cases.items():
        s = _score(tmp_path, res, TWO_PEERS, name=f"r1-{name}")
        assert len(s["void"]) == 1, (name, s["void"])


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

# The gate starts a grandchild that records its pid and sleeps, then sleeps itself: a timeout that
# kills only the direct child leaves the grandchild running. With "ignore" the grandchild ignores
# SIGTERM, so only the SIGKILL escalation removes it.
_TREE_GATE = """
import subprocess, sys, time
from pathlib import Path
pidfile = Path(sys.argv[1])
child = (
    "import os, signal, sys, time\\n"
    "if sys.argv[2] == 'ignore': signal.signal(signal.SIGTERM, signal.SIG_IGN)\\n"
    "tmp = sys.argv[1] + '.tmp'\\n"
    "open(tmp, 'w').write(str(os.getpid()))\\n"
    "os.replace(tmp, sys.argv[1])\\n"
    "time.sleep(30)\\n")
subprocess.Popen([sys.executable, "-c", child, str(pidfile), sys.argv[2]])
while not pidfile.exists():
    time.sleep(0.01)
time.sleep(30)
"""


def _alive(pid):
    """True while pid runs; a zombie (killed, not yet reaped by its new parent) counts as gone."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    if not Path("/proc/self/stat").exists():
        return True  # no procfs (macOS): kill(0) is the only reading there is
    try:
        state = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8").rsplit(")", 1)[1].split()[0]
    except FileNotFoundError:
        return False  # it exited between the two reads
    except (OSError, IndexError):
        return True
    return state != "Z"


def _gone_within(pid, seconds=5.0):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if not _alive(pid):
            return True
        time.sleep(0.05)
    return False


@POSIX_ONLY
@pytest.mark.parametrize("on_term", ["exit", "ignore"])
def test_a_timed_out_floor_step_leaves_no_process_behind(tmp_path, monkeypatch, on_term):
    monkeypatch.setattr(S, "KILL_GRACE_S", 0.3)
    pidfile = tmp_path / "grandchild.pid"
    prof = _pure_profile(tmp_path, gate=[sys.executable, "-c", _TREE_GATE, str(pidfile), on_term], timeout_s=1)
    t0 = time.monotonic()
    res = S.run_floor(tmp_path, prof, tmp_path / "logs")
    elapsed = time.monotonic() - t0
    pid = int(pidfile.read_text(encoding="utf-8"))
    try:
        assert res["steps"][0]["rc"] == S.RC_TIMEOUT
        assert _gone_within(pid), f"grandchild {pid} survived the floor's timeout"
        assert elapsed < 10, elapsed
    finally:
        if _alive(pid):
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass


# --- the floor's environment ---------------------------------------------------------------------

_LEAKS = ("VIRTUAL_ENV", "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR", "GIT_OBJECT_DIRECTORY",
          "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_NAMESPACE", "GIT_CEILING_DIRECTORIES", "GIT_LITERAL_PATHSPECS",
          "GIT_GLOB_PATHSPECS", "GIT_NOGLOB_PATHSPECS", "GIT_ICASE_PATHSPECS")


def test_the_floor_runs_without_the_venv_and_the_repo_scoping_git_variables(tmp_path, monkeypatch):
    for name in _LEAKS:
        monkeypatch.setenv(name, str(tmp_path / "leak"))
    monkeypatch.setenv("PYTHONUTF8", "1")
    monkeypatch.setenv("ABSCORE_TEST_KEEP", "yes")
    monkeypatch.setenv("GIT_SSH_COMMAND", "ssh")
    # The gate prints the variable NAMES only, never a value.
    gate = [sys.executable, "-c", "import json, os; print(json.dumps(sorted(os.environ)))"]
    res = S.run_floor(tmp_path, _pure_profile(tmp_path, gate=gate), tmp_path / "logs")
    seen = set(json.loads(Path(res["steps"][0]["log"]).read_text(encoding="utf-8")))
    assert res["passed"] is True
    assert seen.isdisjoint(_LEAKS), sorted(seen & set(_LEAKS))
    assert {"PYTHONUTF8", "ABSCORE_TEST_KEEP", "GIT_SSH_COMMAND"} <= seen


# --- floor_error and floor_steps -----------------------------------------------------------------

def _scored_floor(tmp_path, gate, timeout_s=30):
    floor = S.run_floor(tmp_path, _pure_profile(tmp_path, gate=gate, timeout_s=timeout_s), tmp_path / "logs")
    return _score(tmp_path, _result(floor=floor), TWO_PEERS)


def test_floor_error_names_a_step_that_could_not_start(tmp_path):
    s = _scored_floor(tmp_path, [str(tmp_path / "no-such-gate")])
    assert s["floor_error"] == "gate: could not start (rc 127)"
    assert s["floor_steps"] == [{"name": "gate", "rc": 127}] and s["floor_passed"] is False


def test_floor_error_names_a_step_that_timed_out(tmp_path, monkeypatch):
    monkeypatch.setattr(S, "KILL_GRACE_S", 0.3)
    s = _scored_floor(tmp_path, [sys.executable, "-c", "import time; time.sleep(10)"], timeout_s=1)
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
