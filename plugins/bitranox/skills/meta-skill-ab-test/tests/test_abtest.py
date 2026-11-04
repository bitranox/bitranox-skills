"""abtest CLI: init, seal, run (dry and fake-live), score, prune-run, resume; through the fake claude."""
import json
import os
import signal
import sys
import threading
from pathlib import Path

import _ablib as L
import abtest as T
import pytest

FIXTURES = Path(__file__).resolve().parent / "fixtures"
SECRET = "fake-arm-token-UNIQUE-7f3c91-abtest"  # unique, so a hit in any file is the copy leaking
LOGIN_TEXT = "Not logged in - Please run /login"


def _init_and_fill(tmp_path, scratch_repo, skills_repo, n=1, gate='["./gate.sh"]'):
    run_dir = tmp_path / "run1"
    assert T.main(["init", str(run_dir), "--repo", str(scratch_repo), "--base", (scratch_repo / ".base").read_text(),
                   "--skills-ref", (skills_repo / ".ref").read_text(), "--skill", "demo-skill"]) == 0
    toml = (run_dir / "abtest.toml").read_text(encoding="utf-8")
    toml = toml.replace('gate = ["make", "test"]', f"gate = {gate}").replace("n = 3", f"n = {n}")
    toml = toml.replace('changes = ["<one change per entry>"]', 'changes = ["louder"]')
    # FAKE_CLAUDE_STREAM must reach the arm: the arm env is built from env_keep only.
    toml = toml.replace("warmth_tolerance = 0.25", 'warmth_tolerance = 0.25\nenv_keep = ["PATH", "LANG", "FAKE_CLAUDE_STREAM"]')
    (run_dir / "abtest.toml").write_text(toml, encoding="utf-8")
    (run_dir / "task.md").write_text("Do the task.\n", encoding="utf-8")
    # seal refuses a PREREG that still holds a <placeholder>, so the skeleton is replaced, not appended to.
    (run_dir / "PREREG.md").write_text("# Pre-registration\n\nQuestion: is V1 cheaper?\nH1: V1 is cheaper.\n", encoding="utf-8")
    (run_dir / "variants" / "V1" / "SKILL.md").write_text("---\nname: demo-skill\n---\nLOUDER.\n", encoding="utf-8")
    return run_dir


def _env(fake_claude_path, tmp_path, stream=None):
    creds = tmp_path / "creds.json"
    creds.write_text(json.dumps({"claudeAiOauth": {"accessToken": SECRET}}), encoding="utf-8")
    creds.chmod(0o600)
    return {"PATH": f"{fake_claude_path}{os.pathsep}{os.environ['PATH']}",
            "FAKE_CLAUDE_STREAM": str(stream or FIXTURES / "stream-control.jsonl")}, creds


def _use_env(monkeypatch, env):
    monkeypatch.setattr(os, "environ", dict(os.environ, **env))


def _run_args(run_dir, creds, skills_repo, *extra):
    return ["run", str(run_dir), "--credentials", str(creds), "--skills-repo", str(skills_repo), *extra]


def _login_failure_stream(tmp_path):
    """What the CLI writes when it calls a failed request a login failure (401 or 429 alike)."""
    rows = [{"type": "system", "subtype": "init", "model": "claude-opus-5-5", "claude_code_version": "9.9.9",
             "session_id": "fake-login", "permissionMode": "bypassPermissions", "plugins": [], "skills": []},
            {"type": "assistant", "error": "authentication_failed",
             "message": {"id": "s1", "model": "<synthetic>", "content": [{"type": "text", "text": LOGIN_TEXT}]}},
            {"type": "result", "subtype": "success", "is_error": True, "result": LOGIN_TEXT, "total_cost_usd": 0,
             "num_turns": 1, "duration_ms": 10, "modelUsage": {}}]
    path = tmp_path / "stream-login.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    return path


class _Probe:
    """The injected out-of-band login check; records every call, answers a fixed word."""

    def __init__(self, word):
        self.word = word
        self.calls = []

    def __call__(self, credentials):
        self.calls.append(credentials)
        return self.word


def _arm_rows(run_dir):
    return [(r["round"], r["arm"], r["status"]) for r in L.read_jsonl(run_dir / "journal.jsonl") if r["step"] == "arm"]


# --- pure: the journal reader (every platform) --------------------------------------------------

def test_a_torn_last_journal_line_is_moved_aside_and_reported(tmp_path, capsys):
    path = tmp_path / "journal.jsonl"
    path.write_text('{"step": "seal", "round": 0}\n{"step": "arm", "rou', encoding="utf-8")
    rows = T.load_journal(tmp_path)
    assert rows == [{"step": "seal", "round": 0}]
    assert "torn" in capsys.readouterr().err
    assert path.read_text(encoding="utf-8") == '{"step": "seal", "round": 0}\n'
    assert (tmp_path / "journal.torn").read_text(encoding="utf-8") == '{"step": "arm", "rou\n'
    T.record(tmp_path, step="arm", round=1, arm="C", status="ran")
    assert [r["step"] for r in L.read_jsonl(path)] == ["seal", "arm"]


def test_a_torn_journal_line_before_the_last_is_an_error(tmp_path):
    (tmp_path / "journal.jsonl").write_text('{"step": "seal"}\nnot json\n{"step": "arm"}\n', encoding="utf-8")
    with pytest.raises(T.JournalError, match="line 2"):
        T.load_journal(tmp_path)


def test_record_starts_a_new_line_after_a_final_line_without_newline(tmp_path):
    (tmp_path / "journal.jsonl").write_text('{"step": "seal"}', encoding="utf-8")
    T.record(tmp_path, step="arm", round=1, arm="C", status="ran")
    assert [r["step"] for r in L.read_jsonl(tmp_path / "journal.jsonl")] == ["seal", "arm"]


def test_a_failing_command_prints_a_json_envelope_and_one_stderr_line(tmp_path, capsys):
    assert T.main(["score", str(tmp_path / "missing"), "--json"]) == 2
    captured = capsys.readouterr()
    assert json.loads(captured.out)["ok"] is False
    assert captured.err.count("\n") == 1 and "Traceback" not in captured.err


def test_a_usage_error_under_json_is_still_an_envelope(capsys):
    assert T.main(["run", "--json"]) == 2
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is False and out["command"] == "run"


def test_the_parser_carries_no_m3_verbs():
    choices = T.build_parser()._subparsers._group_actions[0].choices
    assert sorted(choices) == ["init", "prune-run", "run", "score", "seal"]


# --- through the fake claude and a scratch workpiece (POSIX) ------------------------------------

def test_init_writes_skeletons_and_a_git_repo(tmp_path, scratch_repo, skills_repo):
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo)
    assert (run_dir / ".git").is_dir() and (run_dir / "variants" / "V1").is_dir()
    assert "frozen/" in (run_dir / ".gitignore").read_text(encoding="utf-8")
    assert T.main(["init", str(run_dir)]) == 1, "refuses to overwrite"


def test_init_refuses_a_run_id_that_cannot_name_a_branch(tmp_path):
    assert T.main(["init", str(tmp_path / "bad name")]) == 2
    assert not (tmp_path / "bad name").exists()


def test_seal_validates_commits_and_is_once(tmp_path, scratch_repo, skills_repo, capsys):
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo)
    capsys.readouterr()  # init's own line
    assert T.main(["seal", str(run_dir), "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] and out["data"]["weights"]["correctness"] == 0.30
    assert L.git(run_dir, "status", "--porcelain").stdout == "" and "weights" in (run_dir / "PREREG.md").read_text(encoding="utf-8")
    assert T.main(["seal", str(run_dir)]) == 1, "already sealed"


def test_seal_refuses_a_bad_profile(tmp_path, scratch_repo, skills_repo, capsys):
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo)
    (run_dir / "abtest.toml").write_text("[workpiece]\nrepo = 1\n", encoding="utf-8")
    capsys.readouterr()  # init's own line
    assert T.main(["seal", str(run_dir), "--json"]) == 2
    assert json.loads(capsys.readouterr().out)["ok"] is False
    assert not (run_dir / "journal.jsonl").exists()


def test_run_refuses_before_seal(tmp_path, scratch_repo, skills_repo):
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo)
    assert T.main(["run", str(run_dir), "--dry-run"]) == 2


def test_run_refuses_an_unknown_only(tmp_path, scratch_repo, skills_repo):
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo)
    assert T.main(["seal", str(run_dir)]) == 0
    assert T.main(["run", str(run_dir), "--dry-run", "--only", "V9"]) == 2


def test_dry_run_exercises_everything_but_claude_p(tmp_path, scratch_repo, skills_repo, fake_claude_path, monkeypatch):
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo)
    env, creds = _env(fake_claude_path, tmp_path)
    _use_env(monkeypatch, env)
    assert T.main(["seal", str(run_dir)]) == 0
    assert T.main(_run_args(run_dir, creds, skills_repo, "--dry-run")) == 0
    assert [s for _, _, s in _arm_rows(run_dir)] == ["dry", "dry"]
    for name in ("r1-C", "r1-V1"):
        arm = run_dir / "arms" / name
        assert (arm / "result.json").is_file() and not (arm / "cfg").exists() and not (arm / "stream.jsonl").exists()
        res = json.loads((arm / "result.json").read_text(encoding="utf-8"))
        assert res["floor"]["passed"] is True
        # No memory store in the scratch chain: the snapshot is skipped, so nothing is verified.
        assert res["guard"]["taken"] is False and res["guard_changes"] == [] and "no .claude-memory" in res["guard_skipped"]
        assert res["cleanup"]["errors"] == [] and res["cleanup"]["prune"]["worktree_removed"] is True
    assert not (scratch_repo / ".claude" / "worktrees" / f"abx-{run_dir.name}-r1-C").exists()
    assert L.git(scratch_repo, "rev-parse", "--verify", "-q", f"abx/{run_dir.name}/r1-C").returncode == 0
    # Every frozen checkout is released: no directory left, no registration left in the skills repo.
    assert not any((run_dir / "frozen").glob("*"))
    assert L.git(skills_repo, "worktree", "list", "--porcelain").stdout.count("worktree ") == 1
    assert T.main(_run_args(run_dir, creds, skills_repo, "--dry-run")) == 0
    assert len(_arm_rows(run_dir)) == 2, "a second dry run skips what the first did"


def test_live_run_then_score_then_resume_skips_paid_steps(tmp_path, scratch_repo, skills_repo, fake_claude_path, monkeypatch, capsys):
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo, n=2)
    env, creds = _env(fake_claude_path, tmp_path)
    _use_env(monkeypatch, env)
    assert T.main(["seal", str(run_dir)]) == 0
    probe = _Probe("ok")
    assert T.main(_run_args(run_dir, creds, skills_repo, "--only", "C"), login_check=probe) == 0
    assert _arm_rows(run_dir) == [(1, "C", "ran"), (2, "C", "ran")]
    assert probe.calls == [], "the probe is asked only after a login-looking failure"
    arm = run_dir / "arms" / "r1-C"
    res = json.loads((arm / "result.json").read_text(encoding="utf-8"))
    assert res["total_cost_usd"] == 0.25 and res["bundle_commits"] == 1 and not (arm / "cfg").exists()
    assert (arm / "bundle.git").is_file() and (arm / "stream.jsonl").is_file()
    capsys.readouterr()
    assert T.main(["score", str(run_dir), "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["data"]["arms"]["r1-C"]["void"] == [] and (arm / "scores.json").is_file()
    before = (arm / "result.json").stat().st_mtime_ns
    assert T.main(_run_args(run_dir, creds, skills_repo, "--only", "C"), login_check=probe) == 0
    assert (arm / "result.json").stat().st_mtime_ns == before, "resume never repeats a paid arm"


def test_a_live_run_after_a_dry_run_sets_the_dry_attempt_aside(tmp_path, scratch_repo, skills_repo, fake_claude_path, monkeypatch):
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo)
    env, creds = _env(fake_claude_path, tmp_path)
    _use_env(monkeypatch, env)
    assert T.main(["seal", str(run_dir)]) == 0
    assert T.main(_run_args(run_dir, creds, skills_repo, "--dry-run", "--only", "C")) == 0
    assert T.main(_run_args(run_dir, creds, skills_repo, "--only", "C"), login_check=_Probe("ok")) == 0
    assert _arm_rows(run_dir) == [(1, "C", "dry"), (1, "C", "ran")]
    aside = run_dir / "arms" / "r1-C.attempt-1"
    assert json.loads((aside / "result.json").read_text(encoding="utf-8"))["dry_run"] is True
    assert (run_dir / "arms" / "r1-C" / "stream.jsonl").is_file()
    assert L.git(scratch_repo, "rev-parse", "--verify", "-q", f"abx/{run_dir.name}/r1-C.attempt-1").returncode == 0


def test_a_login_looking_failure_asks_the_probe_and_pauses(tmp_path, scratch_repo, skills_repo, fake_claude_path, monkeypatch, capsys):
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo)
    env, creds = _env(fake_claude_path, tmp_path, stream=_login_failure_stream(tmp_path))
    _use_env(monkeypatch, env)
    assert T.main(["seal", str(run_dir)]) == 0
    probe = _Probe("quota")
    capsys.readouterr()  # init's and seal's own lines
    assert T.main(_run_args(run_dir, creds, skills_repo, "--json"), login_check=probe) == 1
    out = json.loads(capsys.readouterr().out)
    assert probe.calls == [creds]
    rows = L.read_jsonl(run_dir / "journal.jsonl")
    assert rows[-1]["step"] == "pause" and rows[-1]["status"] == "quota"
    assert _arm_rows(run_dir) == [(1, "C", "paused")]
    res = json.loads((run_dir / "arms" / "r1-C" / "result.json").read_text(encoding="utf-8"))
    assert res["login_probe"] == "quota"
    assert not (run_dir / "arms" / "r1-V1").exists(), "nothing runs after the pause"
    # The probe's word is reported, never a cause: a 429 came back while the account was serving.
    assert "the out-of-band probe answered quota" in out["data"]["message"]
    assert "exhausted" not in json.dumps(out).lower()
    # Resume: the paused attempt is set aside and the arm runs again, not voided.
    env["FAKE_CLAUDE_STREAM"] = str(FIXTURES / "stream-control.jsonl")
    _use_env(monkeypatch, env)
    assert T.main(_run_args(run_dir, creds, skills_repo), login_check=_Probe("ok")) == 0
    assert _arm_rows(run_dir) == [(1, "C", "paused"), (1, "C", "ran"), (1, "V1", "ran")]
    assert (run_dir / "arms" / "r1-C.attempt-1" / "result.json").is_file()


def test_no_file_under_the_run_dir_carries_the_credentials(tmp_path, scratch_repo, skills_repo, fake_claude_path, monkeypatch):
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo)
    env, creds = _env(fake_claude_path, tmp_path)
    _use_env(monkeypatch, env)
    assert T.main(["seal", str(run_dir)]) == 0
    assert T.main(_run_args(run_dir, creds, skills_repo), login_check=_Probe("ok")) == 0
    assert T.main(["score", str(run_dir)]) == 0
    scanned = 0
    for root in (run_dir, scratch_repo):
        for p in root.rglob("*"):
            if p.is_file() and not p.is_symlink() and "home" not in p.relative_to(root).parts:
                scanned += 1
                assert SECRET.encode() not in p.read_bytes(), p
    assert scanned > 20, "the scan must have read the arm's files"


def test_a_failing_arm_exits_2_records_an_error_row_and_cleans_up(tmp_path, scratch_repo, skills_repo, fake_claude_path, monkeypatch, capsys):
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo)
    env, creds = _env(fake_claude_path, tmp_path)
    _use_env(monkeypatch, env)
    assert T.main(["seal", str(run_dir)]) == 0
    capsys.readouterr()
    not_a_repo = tmp_path / "not-a-repo"
    not_a_repo.mkdir()
    assert T.main(_run_args(run_dir, creds, not_a_repo, "--json")) == 2
    captured = capsys.readouterr()
    assert json.loads(captured.out)["ok"] is False
    assert captured.err.count("\n") == 1 and "Traceback" not in captured.err
    assert _arm_rows(run_dir) == [(1, "C", "error")]
    res = json.loads((run_dir / "arms" / "r1-C" / "result.json").read_text(encoding="utf-8"))
    assert "ArmError" in res["error"] and not (run_dir / "arms" / "r1-C" / "cfg").exists()


@pytest.mark.skipif(sys.platform == "win32", reason="SIGINT delivery to the process is POSIX here")
def test_ctrl_c_still_writes_result_and_journal_then_reraises(tmp_path, scratch_repo, skills_repo, fake_claude_path, monkeypatch):
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo, gate='["sleep", "6"]')
    env, creds = _env(fake_claude_path, tmp_path)
    _use_env(monkeypatch, env)
    assert T.main(["seal", str(run_dir)]) == 0
    timer = threading.Timer(1.5, os.kill, (os.getpid(), signal.SIGINT))
    timer.start()
    try:
        with pytest.raises(KeyboardInterrupt):
            T.main(_run_args(run_dir, creds, skills_repo, "--only", "C"), login_check=_Probe("ok"))
    finally:
        timer.cancel()
    assert _arm_rows(run_dir) == [(1, "C", "interrupted")]
    arm = run_dir / "arms" / "r1-C"
    res = json.loads((arm / "result.json").read_text(encoding="utf-8"))
    assert res["stop_reason"] == "interrupted" and not (arm / "cfg").exists()
    assert not (scratch_repo / ".claude" / "worktrees" / f"abx-{run_dir.name}-r1-C").exists()


def _fabricate_arm(run_dir, round_no, *, cache_read, stop_reason="finished"):
    arm = run_dir / "arms" / f"r{round_no}-C"
    arm.mkdir(parents=True)
    res = {"arm": f"r{round_no}-C", "round": round_no, "name": "C", "dry_run": False, "has_result": True,
           "stop_reason": stop_reason, "first_cache_read": cache_read, "void_reasons": [], "guard_changes": [],
           "floor": {"passed": True, "steps": []}, "bundle_commits": 1, "total_cost_usd": 0.25}
    (arm / "result.json").write_text(json.dumps(res), encoding="utf-8")
    T.record(run_dir, step="arm", round=round_no, arm="C", status="ran")


def test_score_never_lets_a_void_arm_set_the_warmth_median(tmp_path, scratch_repo, skills_repo, capsys):
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo, n=5)
    assert T.main(["seal", str(run_dir)]) == 0
    for r in (1, 2, 3):
        _fabricate_arm(run_dir, r, cache_read=11000)
    for r in (4, 5):  # void by their stop reason, and far off in warmth
        _fabricate_arm(run_dir, r, cache_read=900000, stop_reason="deadline")
    capsys.readouterr()
    assert T.main(["score", str(run_dir), "--json"]) == 0
    arms = json.loads(capsys.readouterr().out)["data"]["arms"]
    # With the void arms as peers the median would be 455500 and r1-r3 would read as out of line.
    for label in ("r1-C", "r2-C", "r3-C"):
        assert arms[label]["warmth_checked"] is True and arms[label]["void"] == [], label
    assert arms["r4-C"]["void"] and arms["r5-C"]["void"]


def test_prune_run_deletes_the_branches(tmp_path, scratch_repo, skills_repo, fake_claude_path, monkeypatch):
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo)
    env, creds = _env(fake_claude_path, tmp_path)
    _use_env(monkeypatch, env)
    assert T.main(["seal", str(run_dir)]) == 0
    assert T.main(_run_args(run_dir, creds, skills_repo, "--dry-run")) == 0
    assert T.main(["prune-run", str(run_dir)]) == 0
    assert L.git(scratch_repo, "branch", "--list", f"abx/{run_dir.name}/*").stdout.strip() == ""
