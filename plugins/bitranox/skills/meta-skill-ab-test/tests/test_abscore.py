"""abscore: the floor runs the profile's argv lists; the score reads result.json and the peers."""
import dataclasses
import json
import sys
from pathlib import Path

import abprofile as P
import abscore as S
import abstream

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
                      "bundle_commits", "void", "wall_s"}
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
