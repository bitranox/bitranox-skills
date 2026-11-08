"""abtest CLI: init, seal, run (dry and fake-live), score, prune-run, resume; through the fake claude."""
import importlib.util
import json
import os
import shutil
import signal
import subprocess
import sys
import tarfile
import time
from pathlib import Path

import _ablib as L
import abarm as A
import abtest as T
import pytest
from abproc_testkit import SigintOnMarker, alive, kill_if_alive, pids_in

FIXTURES = Path(__file__).resolve().parent / "fixtures"
SECRET = "fake-arm-token-UNIQUE-7f3c91-abtest"  # unique, so a hit in any file is the copy leaking
LOGIN_TEXT = "Not logged in - Please run /login"


def _init_and_fill(tmp_path, scratch_repo, skills_repo, n=1, gate='["./gate.sh"]', sandbox="none"):
    run_dir = tmp_path / "run1"
    assert T.main(["init", str(run_dir), "--repo", str(scratch_repo), "--base", (scratch_repo / ".base").read_text(),
                   "--skills-ref", (skills_repo / ".ref").read_text(), "--skill", "demo-skill"]) == 0
    toml = (run_dir / "abtest.toml").read_text(encoding="utf-8")
    toml = toml.replace('gate = ["make", "test"]', f"gate = {gate}").replace("n = 3", f"n = {n}")
    toml = toml.replace('changes = ["<one change per entry>"]', 'changes = ["louder"]')
    # The fake claude and its stream live under tmp_path, which a real sandbox's /tmp tmpfs hides;
    # the bwrap path has its own tests (a fake bwrap here, the real one in test_abarm).
    assert toml.count('sandbox = "bwrap"') == 1
    toml = toml.replace('sandbox = "bwrap"', f'sandbox = "{sandbox}"')
    # FAKE_CLAUDE_STREAM and _SCRIPT must reach the arm: the arm env is built from env_keep only.
    toml = toml.replace("warmth_tolerance = 0.25", 'warmth_tolerance = 0.25\nenv_keep = ["PATH", "LANG", "FAKE_CLAUDE_STREAM", "FAKE_CLAUDE_SCRIPT"]')
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
    """Set each variable through monkeypatch, so os.environ stays the real mapping (putenv included)."""
    for key, value in env.items():
        monkeypatch.setenv(key, value)


def _run_args(run_dir, creds, skills_repo, *extra):
    return ["run", str(run_dir), "--credentials", str(creds), "--skills-repo", str(skills_repo), *extra]


def _synthetic_stream(tmp_path, text, *, error=None, real_work_first=False, name="stream-synthetic.jsonl"):
    """A session whose last assistant message is a CLI synthetic notice carrying `text`.

    real_work_first puts one real opus message (the control fixture's) before the notice.
    """
    control = (FIXTURES / "stream-control.jsonl").read_text(encoding="utf-8").splitlines()
    rows = [{"type": "system", "subtype": "init", "model": "claude-opus-5-5", "claude_code_version": "9.9.9",
             "session_id": "fake-synthetic", "permissionMode": "bypassPermissions", "plugins": [], "skills": []}]
    rows += [json.loads(control[1])] if real_work_first else []
    notice = {"type": "assistant", "message": {"id": "s1", "model": "<synthetic>", "content": [{"type": "text", "text": text}]}}
    rows.append(dict(notice, error=error) if error else notice)
    rows.append({"type": "result", "subtype": "success", "is_error": True, "result": text, "total_cost_usd": 0,
                 "num_turns": 1, "duration_ms": 10, "modelUsage": {}})
    path = tmp_path / name
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    return path


def _login_failure_stream(tmp_path):
    """What the CLI writes when it calls a failed request a login failure (401 or 429 alike)."""
    return _synthetic_stream(tmp_path, LOGIN_TEXT, error="authentication_failed", name="stream-login.jsonl")


def _files_carrying(root, *tokens):
    """Every regular file under root (symlinks and the linked-in home skipped) holding any token; and the count read."""
    hits, scanned = [], 0
    for p in root.rglob("*"):
        if p.is_file() and not p.is_symlink() and "home" not in p.relative_to(root).parts:
            scanned += 1
            data = p.read_bytes()
            hits += [str(p) for t in tokens if t.encode() in data]
    return hits, scanned


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
        hits, count = _files_carrying(root, SECRET)
        assert hits == []
        scanned += count
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
    marker = tmp_path / "gate-started"
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo, gate=f'["sh", "-c", "touch {marker} && sleep 30"]')
    env, creds = _env(fake_claude_path, tmp_path)
    _use_env(monkeypatch, env)
    assert T.main(["seal", str(run_dir)]) == 0
    with SigintOnMarker(marker) as sigint, pytest.raises(KeyboardInterrupt):
        T.main(_run_args(run_dir, creds, skills_repo, "--only", "C"), login_check=_Probe("ok"))
    assert sigint.sent, "the interrupt must land inside the gate"
    assert _arm_rows(run_dir) == [(1, "C", "interrupted")]
    arm = run_dir / "arms" / "r1-C"
    res = json.loads((arm / "result.json").read_text(encoding="utf-8"))
    assert res["stop_reason"] == "interrupted" and not (arm / "cfg").exists()
    assert not (scratch_repo / ".claude" / "worktrees" / f"abx-{run_dir.name}-r1-C").exists()
    assert _lock_is_free(run_dir), "a Ctrl-C left the run dir locked"


def _fabricate_arm(run_dir, round_no, *, cache_read, stop_reason="finished", guard_changes=()):
    arm = run_dir / "arms" / f"r{round_no}-C"
    arm.mkdir(parents=True)
    res = {"arm": f"r{round_no}-C", "round": round_no, "name": "C", "dry_run": False, "has_result": True,
           "stop_reason": stop_reason, "first_cache_read": cache_read, "void_reasons": [],
           "guard": {"taken": True, "entries": 3, "skipped": None}, "guard_changes": list(guard_changes),
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


def test_score_flags_an_arm_whose_store_changed_without_voiding_it(tmp_path, scratch_repo, skills_repo, capsys):
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo)
    assert T.main(["seal", str(run_dir)]) == 0
    _fabricate_arm(run_dir, 1, cache_read=11000, guard_changes=["changed: slug x", "added: slug y"])
    _fabricate_arm(run_dir, 2, cache_read=11000)
    flag = "store changed: 2 entries, adjudicate against arms/r1-C/transcripts/"
    capsys.readouterr()
    assert T.main(["score", str(run_dir)]) == 0
    lines = capsys.readouterr().out.splitlines()
    r1 = [ln for ln in lines if ln.startswith("r1-C:")]
    r2 = [ln for ln in lines if ln.startswith("r2-C:")]
    assert len(r1) == 1 and flag in r1[0] and "void=-" in r1[0], lines
    assert len(r2) == 1 and "store changed" not in r2[0], lines
    assert T.main(["score", str(run_dir), "--json"]) == 0
    data = json.loads(capsys.readouterr().out)["data"]
    assert data["flags"] == {"r1-C": flag}
    assert data["arms"]["r1-C"]["void"] == [] and data["arms"]["r1-C"]["store_guard"] == "changed"
    assert data["arms"]["r2-C"]["store_guard"] == "clean" and data["arms"]["r2-C"]["store_changes"] == []


def test_score_text_names_subagents_ideas_and_the_suite_outcome(tmp_path, scratch_repo, skills_repo, capsys):
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo, n=2)
    assert T.main(["seal", str(run_dir)]) == 0
    _fabricate_arm(run_dir, 1, cache_read=11000)
    _fabricate_arm(run_dir, 2, cache_read=11000)
    arm = run_dir / "arms" / "r1-C"
    sub = arm / "transcripts" / "-ws" / "s1" / "subagents"
    sub.mkdir(parents=True)
    for name in ("a", "b"):
        stamps = [json.dumps({"timestamp": f"2026-11-08T10:0{m}:00Z"}) for m in (0, 5)]
        (sub / f"agent-{name}.jsonl").write_text("\n".join(stamps) + "\n", encoding="utf-8")
    bash = {"type": "tool_use", "id": "t1", "name": "Bash",
            "input": {"command": 'echo "[abx] idea=3 reviewed twice" >> .bitranox/sdd/progress.md'}}
    (arm / "stream.jsonl").write_text(json.dumps({"type": "assistant", "message": {"id": "m", "content": [bash]}})
                                      + "\n", encoding="utf-8")
    (arm / "floor-suite.log").write_text((FIXTURES / "cargo-test-failed.log").read_text(encoding="utf-8"),
                                         encoding="utf-8")
    res = json.loads((arm / "result.json").read_text(encoding="utf-8"))
    res["floor"] = {"passed": False, "steps": [{"name": "gate", "rc": 0, "error": None},
                                               {"name": "suite", "rc": 101, "error": None}]}
    (arm / "result.json").write_text(json.dumps(res), encoding="utf-8")
    capsys.readouterr()
    assert T.main(["score", str(run_dir)]) == 0
    lines = capsys.readouterr().out.splitlines()
    r1 = next(ln for ln in lines if ln.startswith("r1-C:"))
    r2 = next(ln for ln in lines if ln.startswith("r2-C:"))
    assert "subagents=2(max 2 at once)" in r1 and "ideas=3x1" in r1 and "suite=tests_failed(2 of 10)" in r1, r1
    assert "gate=passed" in r1, r1
    assert "  r1-C idea 3: [abx] idea=3 reviewed twice" in lines, lines
    assert "subagents=- ideas=- suite=- gate=-" in r2, r2


def test_prune_run_deletes_the_branches(tmp_path, scratch_repo, skills_repo, fake_claude_path, monkeypatch):
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo)
    env, creds = _env(fake_claude_path, tmp_path)
    _use_env(monkeypatch, env)
    assert T.main(["seal", str(run_dir)]) == 0
    assert T.main(_run_args(run_dir, creds, skills_repo, "--dry-run")) == 0
    assert T.main(["prune-run", str(run_dir)]) == 0
    assert L.git(scratch_repo, "branch", "--list", f"abx/{run_dir.name}/*").stdout.strip() == ""


def test_prune_run_bundles_every_branch_before_deleting_them(tmp_path, scratch_repo, skills_repo, fake_claude_path, monkeypatch):
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo)
    env, creds = _env(fake_claude_path, tmp_path)
    _use_env(monkeypatch, env)
    assert T.main(["seal", str(run_dir)]) == 0
    assert T.main(_run_args(run_dir, creds, skills_repo, "--dry-run")) == 0
    # a set-aside attempt branch: no arm's own bundle.git covers it, the run-wide bundle must
    L.git(scratch_repo, "branch", f"abx/{run_dir.name}/r1-C.attempt-1", "HEAD")
    before = sorted(L.git(scratch_repo, "branch", "--list", f"abx/{run_dir.name}/*", "--format=%(refname)").stdout.split())
    assert len(before) >= 2
    assert T.main(["prune-run", str(run_dir)]) == 0
    bundle = run_dir / "branches.bundle"
    assert bundle.is_file()
    heads = subprocess.run(["git", "bundle", "list-heads", str(bundle)], capture_output=True, text=True, check=True).stdout
    assert sorted(line.split()[1] for line in heads.splitlines()) == before
    # a second prune finds no branch and must not replace the bundle with an empty one
    assert T.main(["prune-run", str(run_dir)]) == 0
    assert bundle.is_file() and len(heads.splitlines()) == len(before)


def test_prune_run_deletes_no_branch_when_the_bundle_cannot_be_written(tmp_path, scratch_repo, skills_repo, fake_claude_path,
                                                                      monkeypatch):
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo)
    env, creds = _env(fake_claude_path, tmp_path)
    _use_env(monkeypatch, env)
    assert T.main(["seal", str(run_dir)]) == 0
    assert T.main(_run_args(run_dir, creds, skills_repo, "--dry-run")) == 0
    before = L.git(scratch_repo, "branch", "--list", f"abx/{run_dir.name}/*").stdout
    assert before.strip()
    run_dir.chmod(0o555)  # the bundle cannot be created in a read-only run dir
    try:
        if os.access(run_dir, os.W_OK):
            pytest.skip("the run dir stays writable here (running as root)")
        assert T.main(["prune-run", str(run_dir)]) == 2
    finally:
        run_dir.chmod(0o755)
    assert L.git(scratch_repo, "branch", "--list", f"abx/{run_dir.name}/*").stdout == before


# --- review round: pause on a refused request, leftovers of a killed attempt, refusals ------------

PLANTED = "fake-planted-token-UNIQUE-0d41e2-abtest"  # a credentials copy a hard kill left behind
REFUSED_INSTALL = """#!/usr/bin/env python3
import os, runpy, sys
from pathlib import Path
if sys.argv[1:4] == ["plugin", "marketplace", "add"]:
    cfg = Path(os.environ["CLAUDE_CONFIG_DIR"])
    if (cfg / ".credentials.json").is_file():
        (cfg.parent / "saw-credentials").write_text("yes", encoding="utf-8")
    print("marketplace add refused", file=sys.stderr)
    sys.exit(3)
sys.argv[0] = str(Path(__file__).with_name("claude_real"))
runpy.run_path(sys.argv[0], run_name="__main__")
"""


def _ws(scratch_repo, run_dir, label):
    return scratch_repo / ".claude" / "worktrees" / f"abx-{run_dir.name}-{label}"


def _extension_set(repo):
    return L.git(repo, "config", "--local", "--get", "extensions.worktreeConfig").returncode == 0


@pytest.mark.parametrize(("text", "real_work_first", "trigger"), [
    ("You've hit your weekly limit - resets Monday", False, "a usage-limit notice"),
    ("You've hit your usage limit", True, "a usage-limit notice"),
    ("Something the CLI said instead of the model", False, "only CLI synthetic messages"),
], ids=["weekly-limit-only", "usage-limit-after-real-work", "synthetic-only"])
def test_a_refused_session_pauses_the_run_instead_of_voiding_the_rest(tmp_path, scratch_repo, skills_repo, fake_claude_path,
                                                                       monkeypatch, capsys, text, real_work_first, trigger):
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo)
    env, creds = _env(fake_claude_path, tmp_path, stream=_synthetic_stream(tmp_path, text, real_work_first=real_work_first))
    _use_env(monkeypatch, env)
    assert T.main(["seal", str(run_dir)]) == 0
    probe = _Probe("quota")
    capsys.readouterr()
    assert T.main(_run_args(run_dir, creds, skills_repo, "--json"), login_check=probe) == 1
    out = json.loads(capsys.readouterr().out)
    assert probe.calls == [creds] and out["data"]["pause_trigger"] == trigger
    assert _arm_rows(run_dir) == [(1, "C", "paused")] and not (run_dir / "arms" / "r1-V1").exists()
    last = L.read_jsonl(run_dir / "journal.jsonl")[-1]
    assert (last["step"], last["status"], last["pause_trigger"]) == ("pause", "quota", trigger)
    assert "exhausted" not in json.dumps(out).lower(), "the probe's word is reported, never a cause"
    env["FAKE_CLAUDE_STREAM"] = str(FIXTURES / "stream-control.jsonl")
    _use_env(monkeypatch, env)
    assert T.main(_run_args(run_dir, creds, skills_repo), login_check=_Probe("ok")) == 0
    assert _arm_rows(run_dir) == [(1, "C", "paused"), (1, "C", "ran"), (1, "V1", "ran")]


def test_a_synthetic_notice_after_real_work_that_is_no_limit_does_not_pause(tmp_path, scratch_repo, skills_repo,
                                                                            fake_claude_path, monkeypatch):
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo)
    stream = _synthetic_stream(tmp_path, "Something the CLI said", real_work_first=True)
    env, creds = _env(fake_claude_path, tmp_path, stream=stream)
    _use_env(monkeypatch, env)
    assert T.main(["seal", str(run_dir)]) == 0
    probe = _Probe("ok")
    assert T.main(_run_args(run_dir, creds, skills_repo, "--only", "C"), login_check=probe) == 0
    assert probe.calls == [] and _arm_rows(run_dir) == [(1, "C", "ran")], "the scorer voids it; the run goes on"


def test_the_arm_row_is_journaled_before_the_probe_is_asked(tmp_path, scratch_repo, skills_repo, fake_claude_path, monkeypatch):
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo)
    env, creds = _env(fake_claude_path, tmp_path, stream=_login_failure_stream(tmp_path))
    _use_env(monkeypatch, env)
    assert T.main(["seal", str(run_dir)]) == 0
    seen = []

    def probe(credentials):
        seen.append(_arm_rows(run_dir))
        return "ok"

    assert T.main(_run_args(run_dir, creds, skills_repo, "--only", "C"), login_check=probe) == 1
    assert seen == [[(1, "C", "paused")]], "a kill inside the probe must not lose the paid arm's row"


def test_a_hard_killed_attempt_is_cleaned_up_before_the_rerun(tmp_path, scratch_repo, skills_repo, fake_claude_path, monkeypatch):
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo)
    env, creds = _env(fake_claude_path, tmp_path)
    _use_env(monkeypatch, env)
    assert T.main(["seal", str(run_dir)]) == 0
    # What a SIGKILL mid-dispatch leaves: the credentials copy, the harness's worktree and its hooks dir.
    ws = _ws(scratch_repo, run_dir, "r1-C")
    A.make_worktree(scratch_repo, (scratch_repo / ".base").read_text(), f"abx/{run_dir.name}/r1-C", ws,
                    copy_untracked_claude_md=True)
    cfg = run_dir / "arms" / "r1-C" / "cfg"
    cfg.mkdir(parents=True)
    (cfg / ".credentials.json").write_text(json.dumps({"claudeAiOauth": {"accessToken": PLANTED}}), encoding="utf-8")
    hooks = ws.parent / f"{ws.name}.githooks"
    assert hooks.is_dir() and _extension_set(scratch_repo)
    assert T.main(_run_args(run_dir, creds, skills_repo, "--only", "C"), login_check=_Probe("ok")) == 0
    assert _arm_rows(run_dir) == [(1, "C", "ran")] and (run_dir / "arms" / "r1-C.attempt-1").is_dir()
    hits, scanned = _files_carrying(run_dir, PLANTED, SECRET)
    assert hits == [] and scanned > 10
    assert not ws.exists() and not hooks.exists() and not _extension_set(scratch_repo)


@pytest.mark.skipif(sys.platform == "win32", reason="SIGINT delivery to the process is POSIX here")
def test_ctrl_c_right_after_worktree_add_still_prunes_the_worktree(tmp_path, scratch_repo, skills_repo, fake_claude_path,
                                                                   monkeypatch):
    marker, release = tmp_path / "worktree-added", tmp_path / "release-hook"
    # post-checkout runs once `worktree add` has registered the worktree, before make_worktree returns.
    hook = scratch_repo / ".git" / "hooks" / "post-checkout"
    hook.write_text(f"#!/bin/sh\ntouch {marker}\ni=0\nwhile [ ! -e {release} ] && [ $i -lt 300 ]; do sleep 0.1; i=$((i+1)); done\n",
                    encoding="utf-8")
    hook.chmod(0o755)
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo)
    env, creds = _env(fake_claude_path, tmp_path)
    _use_env(monkeypatch, env)
    assert T.main(["seal", str(run_dir)]) == 0
    try:
        with SigintOnMarker(marker) as sigint, pytest.raises(KeyboardInterrupt):
            T.main(_run_args(run_dir, creds, skills_repo, "--only", "C"), login_check=_Probe("ok"))
    finally:
        release.write_text("", encoding="utf-8")
    assert sigint.sent
    ws = _ws(scratch_repo, run_dir, "r1-C")
    res = json.loads((run_dir / "arms" / "r1-C" / "result.json").read_text(encoding="utf-8"))
    assert "worktree" not in res, "the interrupt landed inside make_worktree"
    assert not ws.exists() and str(ws) not in L.git(scratch_repo, "worktree", "list", "--porcelain").stdout
    assert _arm_rows(run_dir) == [(1, "C", "interrupted")]


def test_prune_run_finishes_a_locked_arm_the_user_removed_by_hand(tmp_path, scratch_repo, skills_repo, capsys):
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo)
    ws = _ws(scratch_repo, run_dir, "r1-C")
    hooks = ws.parent / f"{ws.name}.githooks"
    A.make_worktree(scratch_repo, (scratch_repo / ".base").read_text(), f"abx/{run_dir.name}/r1-C", ws,
                    copy_untracked_claude_md=False)
    assert L.git(scratch_repo, "worktree", "lock", str(ws)).returncode == 0
    with pytest.raises(A.ArmError):
        A.prune(ws, scratch_repo, ())
    capsys.readouterr()
    # While it is locked, prune-run fails and says so on exactly one stderr line, in both modes.
    assert T.main(["prune-run", str(run_dir)]) == 2
    assert capsys.readouterr().err.count("\n") == 1
    assert T.main(["prune-run", str(run_dir), "--json"]) == 2
    captured = capsys.readouterr()
    assert json.loads(captured.out)["ok"] is False and captured.err.count("\n") == 1
    assert L.git(scratch_repo, "worktree", "remove", "-f", "-f", str(ws)).returncode == 0
    assert hooks.is_dir() and _extension_set(scratch_repo), "what the hand removal leaves"
    assert T.main(["prune-run", str(run_dir)]) == 0
    assert not hooks.exists() and not _extension_set(scratch_repo)


def test_a_task_file_that_is_not_utf8_is_refused_not_a_traceback(tmp_path, scratch_repo, skills_repo, capsys):
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo)
    (run_dir / "task.md").write_bytes(b"\xff\xfe bad")
    capsys.readouterr()
    assert T.main(["seal", str(run_dir), "--json"]) == 2
    captured = capsys.readouterr()
    assert "task.md is not UTF-8" in json.loads(captured.out)["data"]["error"] and captured.err.count("\n") == 1
    (run_dir / "task.md").write_text("Do the task.\n", encoding="utf-8")
    assert T.main(["seal", str(run_dir)]) == 0
    # After the seal the task file is frozen: a rewrite is refused as a change, before it is read.
    (run_dir / "task.md").write_bytes(b"\xff\xfe bad")
    capsys.readouterr()
    assert T.main(["run", str(run_dir), "--dry-run", "--json"]) == 2
    assert "M task.md" in json.loads(capsys.readouterr().out)["data"]["error"]


@pytest.mark.parametrize("change", ["modified", "untracked"])
def test_run_refuses_a_prereg_changed_after_the_seal(tmp_path, scratch_repo, skills_repo, fake_claude_path, monkeypatch,
                                                     capsys, change):
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo)
    env, creds = _env(fake_claude_path, tmp_path)
    _use_env(monkeypatch, env)
    assert T.main(["seal", str(run_dir)]) == 0
    prereg = run_dir / "PREREG.md"
    if change == "modified":
        prereg.write_text(prereg.read_text(encoding="utf-8") + "\n## Amendment\n\nH2 added.\n", encoding="utf-8")
    else:
        assert L.git(run_dir, "rm", "-q", "--cached", "PREREG.md").returncode == 0
    capsys.readouterr()
    assert T.main(_run_args(run_dir, creds, skills_repo, "--dry-run", "--only", "C", "--json")) == 2
    error = json.loads(capsys.readouterr().out)["data"]["error"]
    assert "PREREG.md" in error and "commit" in error and _arm_rows(run_dir) == []
    assert L.git(run_dir, "add", "PREREG.md").returncode == 0
    if change == "modified":  # re-adding an untracked PREREG.md already restores the committed state
        assert L.git(run_dir, *T.SEAL_GIT, "commit", "-q", "-m", "amend").returncode == 0
    assert T.main(_run_args(run_dir, creds, skills_repo, "--dry-run", "--only", "C")) == 0, "a committed amendment runs"


@pytest.mark.parametrize(("question", "sealed"), [("Is V1 cheaper when cost < 0.10?", True),
                                                  ("<what the variants are expected to change>", False)])
def test_seal_refuses_only_placeholder_shaped_angle_brackets(tmp_path, scratch_repo, skills_repo, question, sealed):
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo)
    (run_dir / "PREREG.md").write_text(f"# Pre-registration\n\nQuestion: {question}\n", encoding="utf-8")
    assert T.main(["seal", str(run_dir)]) == (0 if sealed else 2)


def test_set_aside_skips_an_attempt_number_whose_branch_survives(tmp_path, scratch_repo, skills_repo, fake_claude_path,
                                                                 monkeypatch):
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo)
    env, creds = _env(fake_claude_path, tmp_path)
    _use_env(monkeypatch, env)
    assert T.main(["seal", str(run_dir)]) == 0
    branch = f"abx/{run_dir.name}/r1-C"
    # An unfinished attempt's branch, and an older set-aside branch whose directory was deleted.
    for name in (branch, branch + ".attempt-1"):
        assert L.git(scratch_repo, "branch", name, (scratch_repo / ".base").read_text()).returncode == 0
    assert T.main(_run_args(run_dir, creds, skills_repo, "--dry-run", "--only", "C")) == 0
    assert L.read_jsonl(run_dir / "journal.jsonl")[-1]["set_aside"] == "r1-C.attempt-2"
    for name in (branch + ".attempt-1", branch + ".attempt-2"):
        assert L.git(scratch_repo, "rev-parse", "--verify", "-q", name).returncode == 0, name


def test_a_failing_install_step_deletes_the_credentials_copy_and_journals_an_error(tmp_path, scratch_repo, skills_repo,
                                                                                   fake_claude_path, monkeypatch, capsys):
    (fake_claude_path / "claude").rename(fake_claude_path / "claude_real")
    (fake_claude_path / "claude").write_text(REFUSED_INSTALL, encoding="utf-8")
    (fake_claude_path / "claude").chmod(0o755)
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo)
    env, creds = _env(fake_claude_path, tmp_path)
    _use_env(monkeypatch, env)
    assert T.main(["seal", str(run_dir)]) == 0
    capsys.readouterr()
    assert T.main(_run_args(run_dir, creds, skills_repo, "--only", "C")) == 2
    arm = run_dir / "arms" / "r1-C"
    assert (arm / "saw-credentials").is_file(), "the step failed while the copy existed"
    assert not (arm / "cfg").exists() and _arm_rows(run_dir) == [(1, "C", "error")]
    assert "marketplace add" in json.loads((arm / "result.json").read_text(encoding="utf-8"))["error"]


# --- whole-branch review: the user's repo is touched only at the harness's own paths ------------


def test_prune_run_keeps_a_stale_registration_that_is_not_the_runs(tmp_path, scratch_repo, skills_repo, fake_claude_path,
                                                                    monkeypatch):
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo)
    env, creds = _env(fake_claude_path, tmp_path)
    _use_env(monkeypatch, env)
    foreign = tmp_path / "users-offline-worktree"
    assert L.git(scratch_repo, "worktree", "add", "-q", "--detach", str(foreign)).returncode == 0
    foreign.rename(tmp_path / "moved-away")
    assert T.main(["seal", str(run_dir)]) == 0
    assert T.main(_run_args(run_dir, creds, skills_repo, "--dry-run")) == 0
    assert T.main(["prune-run", str(run_dir)]) == 0
    assert str(foreign) in L.git(scratch_repo, "worktree", "list", "--porcelain").stdout


def test_prune_run_removes_a_worktree_the_arm_registered_under_its_own_home(tmp_path, scratch_repo, skills_repo,
                                                                          fake_claude_path, monkeypatch):
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo)
    env, creds = _env(fake_claude_path, tmp_path)
    _use_env(monkeypatch, env)
    assert T.main(["seal", str(run_dir)]) == 0
    assert T.main(_run_args(run_dir, creds, skills_repo, "--dry-run")) == 0
    own = run_dir / "arms" / "r1-C" / "home" / "wt" / "node-8"
    assert L.git(scratch_repo, "worktree", "add", "-q", "-b", "node-8", str(own)).returncode == 0
    foreign = tmp_path / "users-worktree"
    assert L.git(scratch_repo, "worktree", "add", "-q", "-b", "users-topic", str(foreign)).returncode == 0
    assert T.main(["prune-run", str(run_dir)]) == 0
    listed = L.git(scratch_repo, "worktree", "list", "--porcelain").stdout
    assert str(own) not in listed and not own.exists(), "the arm's own worktree stays registered"
    assert L.git(scratch_repo, "branch", "--list", "node-8").stdout.strip() == ""
    assert str(foreign) in listed, "a worktree outside the run's arms dir was touched"
    assert L.git(scratch_repo, "branch", "--list", "users-topic").stdout.strip() != ""


def _exclude_text(repo):
    path = repo / ".git" / "info" / "exclude"
    return path.read_text(encoding="utf-8") if path.is_file() else None


def test_prune_run_removes_only_the_exclude_line_the_harness_added(tmp_path, scratch_repo, skills_repo, fake_claude_path,
                                                                     monkeypatch, capsys):
    exclude = scratch_repo / ".git" / "info" / "exclude"
    exclude.parent.mkdir(parents=True, exist_ok=True)
    exclude.write_text("# the user's own excludes\n*.swp\n", encoding="utf-8")
    original = _exclude_text(scratch_repo)
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo)
    env, creds = _env(fake_claude_path, tmp_path)
    _use_env(monkeypatch, env)
    assert T.main(["seal", str(run_dir)]) == 0
    assert T.main(_run_args(run_dir, creds, skills_repo, "--dry-run")) == 0
    assert ".claude/worktrees/" in _exclude_text(scratch_repo), "precondition: the harness added the line"
    capsys.readouterr()
    assert T.main(["prune-run", str(run_dir), "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert _exclude_text(scratch_repo) == original
    assert out["data"]["exclude"] == "removed"


def test_prune_run_keeps_an_exclude_line_the_user_wrote(tmp_path, scratch_repo, skills_repo, fake_claude_path, monkeypatch,
                                                        capsys):
    exclude = scratch_repo / ".git" / "info" / "exclude"
    exclude.parent.mkdir(parents=True, exist_ok=True)
    exclude.write_text(".claude/worktrees/\n", encoding="utf-8")
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo)
    env, creds = _env(fake_claude_path, tmp_path)
    _use_env(monkeypatch, env)
    assert T.main(["seal", str(run_dir)]) == 0
    assert T.main(_run_args(run_dir, creds, skills_repo, "--dry-run")) == 0
    capsys.readouterr()
    assert T.main(["prune-run", str(run_dir), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["data"]["exclude"] == "not_added"
    assert _exclude_text(scratch_repo) == ".claude/worktrees/\n"


def test_init_and_seal_refuse_a_run_id_whose_branches_exist(tmp_path, scratch_repo, skills_repo, capsys):
    base = (scratch_repo / ".base").read_text()
    assert L.git(scratch_repo, "branch", "abx/run1/r1-C", base).returncode == 0
    capsys.readouterr()
    assert T.main(["init", str(tmp_path / "run1"), "--repo", str(scratch_repo), "--json"]) == 2
    assert "abx/run1/" in json.loads(capsys.readouterr().out)["data"]["error"]
    assert not (tmp_path / "run1").exists()
    assert L.git(scratch_repo, "branch", "-D", "abx/run1/r1-C").returncode == 0
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo)
    assert L.git(scratch_repo, "branch", "abx/run1/r2-V1", base).returncode == 0  # made after init
    assert T.main(["seal", str(run_dir)]) == 2
    assert not (run_dir / "journal.jsonl").exists()


# --- whole-branch review: an interrupted session is over before the arm's cleanup runs -----------

# Run by the fake claude after its commit, stdout still open: ignores SIGTERM, then keeps
# recreating a file in its config dir, as a real session would keep writing its transcript.
_STUCK_SESSION = """
import os, signal, time
from pathlib import Path
signal.signal(signal.SIGTERM, signal.SIG_IGN)
cfg = Path(os.environ["CLAUDE_CONFIG_DIR"])
Path(MARKER).write_text(str(os.getpid()), encoding="utf-8")
for _ in range(1200):
    cfg.mkdir(parents=True, exist_ok=True)
    (cfg / "still-writing").write_text("x", encoding="utf-8")
    time.sleep(0.05)
"""


@pytest.mark.skipif(sys.platform == "win32", reason="SIGINT delivery to the process is POSIX here")
def test_ctrl_c_ends_a_session_that_ignores_sigterm_before_its_config_dir_is_deleted(tmp_path, scratch_repo, skills_repo,
                                                                                     fake_claude_path, monkeypatch):
    marker, script = tmp_path / "session.pid", tmp_path / "stuck.py"
    script.write_text(_STUCK_SESSION.replace("MARKER", repr(str(marker))), encoding="utf-8")
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo)
    env, creds = _env(fake_claude_path, tmp_path)
    _use_env(monkeypatch, dict(env, FAKE_CLAUDE_SCRIPT=str(script)))
    assert T.main(["seal", str(run_dir)]) == 0
    try:
        with SigintOnMarker(marker) as sigint, pytest.raises(KeyboardInterrupt):
            T.main(_run_args(run_dir, creds, skills_repo, "--only", "C", "--stop-grace-s", "1"), login_check=_Probe("ok"))
        assert sigint.sent
        (pid,) = pids_in(marker)
        assert not alive(pid), "the session outlived the arm"
        time.sleep(0.3)
        assert not (run_dir / "arms" / "r1-C" / "cfg").exists(), "the session recreated the deleted config dir"
        assert [t.rsplit("/", 1)[1] for t in _transcripts(run_dir / "arms" / "r1-C")] == ["fake-session-1.jsonl"]
        assert _arm_rows(run_dir) == [(1, "C", "interrupted")]
    finally:
        for pid in pids_in(marker):
            kill_if_alive(pid)


# --- whole-branch review: what cleanup would destroy is copied out first -------------------------

# Run by the fake claude after its commit: leaves a tracked edit, an untracked file and a build
# cache file uncommitted; with BREAK_BUNDLE it also blocks the bundle step, so run_arm raises
# after the session (the error path).
_LEAVES_WORK = """
import os
from pathlib import Path
Path("CLAUDE.md").write_text(Path("CLAUDE.md").read_text(encoding="utf-8") + "edited by the arm\\n", encoding="utf-8")
Path("notes").mkdir()
Path("notes/draft.txt").write_text("an uncommitted draft\\n", encoding="utf-8")
Path("target").mkdir()
Path("target/cache.bin").write_bytes(b"build output")
if BREAK_BUNDLE:
    (Path(os.environ["CLAUDE_CONFIG_DIR"]).parent / "bundle.git").mkdir()
"""


def _transcripts(arm):
    return sorted(p.relative_to(arm / "transcripts").as_posix() for p in (arm / "transcripts").rglob("*") if p.is_file())


def test_an_arm_keeps_its_transcript_and_says_it_left_no_uncommitted_work(tmp_path, scratch_repo, skills_repo,
                                                                           fake_claude_path, monkeypatch):
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo)
    env, creds = _env(fake_claude_path, tmp_path)
    _use_env(monkeypatch, env)
    assert T.main(["seal", str(run_dir)]) == 0
    assert T.main(_run_args(run_dir, creds, skills_repo, "--only", "C"), login_check=_Probe("ok")) == 0
    arm = run_dir / "arms" / "r1-C"
    res = json.loads((arm / "result.json").read_text(encoding="utf-8"))
    (transcript,) = _transcripts(arm)
    assert transcript.endswith("/fake-session-1.jsonl") and res["transcripts"] == [transcript]
    assert "fake transcript of fake-session-1" in (arm / "transcripts" / transcript).read_text(encoding="utf-8")
    assert res["uncommitted"]["left_work"] is False and not (arm / A.UNCOMMITTED_PATCH).exists()
    assert not (arm / A.UNTRACKED_TAR).exists() and not (arm / "cfg").exists()


@pytest.mark.parametrize("path", ["normal", "error"])
def test_uncommitted_work_and_the_transcript_survive_the_cleanup(tmp_path, scratch_repo, skills_repo, fake_claude_path,
                                                                  monkeypatch, path):
    script = tmp_path / "leaves_work.py"
    script.write_text(_LEAVES_WORK.replace("BREAK_BUNDLE", str(path == "error")), encoding="utf-8")
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo)
    env, creds = _env(fake_claude_path, tmp_path)
    _use_env(monkeypatch, dict(env, FAKE_CLAUDE_SCRIPT=str(script)))
    assert T.main(["seal", str(run_dir)]) == 0
    rc = T.main(_run_args(run_dir, creds, skills_repo, "--only", "C"), login_check=_Probe("ok"))
    assert rc == (0 if path == "normal" else 2)
    assert _arm_rows(run_dir) == [(1, "C", "ran" if path == "normal" else "error")]
    arm = run_dir / "arms" / "r1-C"
    res = json.loads((arm / "result.json").read_text(encoding="utf-8"))
    assert ("bundle failed" in res.get("error", "")) == (path == "error")
    assert (arm / A.UNCOMMITTED_PATCH).is_file(), "the arm's uncommitted edit was destroyed with its worktree"
    assert "+edited by the arm" in (arm / A.UNCOMMITTED_PATCH).read_text(encoding="utf-8")
    assert res["uncommitted"]["left_work"] is True and res["uncommitted"]["untracked"] == ["notes/draft.txt"]
    with tarfile.open(arm / A.UNTRACKED_TAR) as tar:
        assert tar.getnames() == ["notes/draft.txt"]
        assert tar.extractfile("notes/draft.txt").read() == b"an uncommitted draft\n"
    assert [t.rsplit("/", 1)[1] for t in _transcripts(arm)] == ["fake-session-1.jsonl"]
    assert not _ws(scratch_repo, run_dir, "r1-C").exists() and not (arm / "cfg").exists()
    hits, scanned = _files_carrying(arm, SECRET)
    assert hits == [] and scanned > 5


def _plant_cfg(arm, token):
    cfg = arm / "cfg"
    (cfg / "projects" / "-some-project").mkdir(parents=True)
    (cfg / "projects" / "-some-project" / "killed-session.jsonl").write_text('{"type": "user"}\n', encoding="utf-8")
    (cfg / ".credentials.json").write_text(json.dumps({"claudeAiOauth": {"accessToken": token}}), encoding="utf-8")
    return cfg


def test_run_and_prune_run_delete_a_config_dir_a_killed_arm_left(tmp_path, scratch_repo, skills_repo, fake_claude_path,
                                                                 monkeypatch, capsys):
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo)
    env, creds = _env(fake_claude_path, tmp_path)
    _use_env(monkeypatch, env)
    assert T.main(["seal", str(run_dir)]) == 0
    killed = _plant_cfg(run_dir / "arms" / "r1-C", PLANTED)
    # --only V1 never visits r1-C, so only a sweep of every arm dir reaches its credentials copy.
    assert T.main(_run_args(run_dir, creds, skills_repo, "--dry-run", "--only", "V1")) == 0
    assert not killed.exists()
    assert (run_dir / "arms" / "r1-C" / "transcripts" / "-some-project" / "killed-session.jsonl").is_file()
    aside = _plant_cfg(run_dir / "arms" / "r1-V1.attempt-1", PLANTED)
    capsys.readouterr()
    assert T.main(["prune-run", str(run_dir), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["data"]["cfg_removed"] == [str(aside)]
    assert not aside.exists()
    hits, scanned = _files_carrying(run_dir, PLANTED, SECRET)
    assert hits == [] and scanned > 5


# --- whole-branch review: an arm is not started on a login that lapses before its deadline -------

def _creds_expiring(tmp_path, expires_at):
    creds = tmp_path / "expiring-creds.json"
    oauth = {"accessToken": SECRET} if expires_at is None else {"accessToken": SECRET, "expiresAt": expires_at}
    creds.write_text(json.dumps({"claudeAiOauth": oauth}), encoding="utf-8")
    return creds


@pytest.mark.parametrize(("expires_in_s", "starts"), [(-60, False), (14400 - 600, False), (14400 + 3600, True),
                                                      (None, True), ("soon", True)],
                         ids=["expired", "lapses-before-the-deadline", "outlives-the-deadline", "no-expiresAt", "malformed"])
def test_an_arm_is_not_started_on_a_login_that_lapses_before_its_deadline(tmp_path, scratch_repo, skills_repo,
                                                                          fake_claude_path, monkeypatch, capsys,
                                                                          expires_in_s, starts):
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo)  # deadline_s = 14400, the skeleton's
    env, _ = _env(fake_claude_path, tmp_path)
    _use_env(monkeypatch, env)
    at = expires_in_s if not isinstance(expires_in_s, int) else int((time.time() + expires_in_s) * 1000)
    creds = _creds_expiring(tmp_path, at)
    assert T.main(["seal", str(run_dir)]) == 0
    probe = _Probe("ok")
    capsys.readouterr()
    rc = T.main(_run_args(run_dir, creds, skills_repo, "--only", "C", "--json"), login_check=probe)
    out = json.loads(capsys.readouterr().out)
    assert probe.calls == []
    if starts:
        assert rc == 0 and _arm_rows(run_dir) == [(1, "C", "ran")]
        return
    assert rc == 1 and _arm_rows(run_dir) == [(1, "C", "paused")]
    assert not (run_dir / "arms" / "r1-C").exists(), "the arm was never started, nothing was copied"
    assert "refreshed first" in out["data"]["message"] and out["data"]["paused_at"] == "r1-C"
    assert str(at) not in json.dumps(out), "no value of the credentials file is reported"


# --- whole-branch review: run refuses inputs that differ from the seal ----------------------------

def _commit_all(run_dir, message):
    assert L.git(run_dir, "add", "-A").returncode == 0
    assert L.git(run_dir, *T.SEAL_GIT, "commit", "-q", "-m", message).returncode == 0


def _tweak_variant(run_dir):
    path = run_dir / "variants" / "V1" / "SKILL.md"
    path.write_text(path.read_text(encoding="utf-8") + "One more line.\n", encoding="utf-8")


def _new_variant_file(run_dir):
    (run_dir / "variants" / "V1" / "extra").mkdir()
    (run_dir / "variants" / "V1" / "extra" / "notes.md").write_text("added after the seal\n", encoding="utf-8")


def _edit_task(run_dir):
    (run_dir / "task.md").write_text("Do a different task.\n", encoding="utf-8")


def _edit_gitignore(run_dir):
    with (run_dir / ".gitignore").open("a", encoding="utf-8") as fh:
        fh.write("variants/\n")


def _commit_max_tokens(run_dir):
    toml = run_dir / "abtest.toml"
    text = toml.read_text(encoding="utf-8")
    assert text.count("max_tokens = 6000000") == 1
    toml.write_text(text.replace("max_tokens = 6000000", "max_tokens = 9000000"), encoding="utf-8")
    _commit_all(run_dir, "raise the cap")


def _commit_variant(run_dir):
    _tweak_variant(run_dir)
    _commit_all(run_dir, "tweak V1")


def _rewrite_prereg(run_dir):
    (run_dir / "PREREG.md").write_text("# Pre-registration\n\nH1: V1 is better (rewritten).\n", encoding="utf-8")
    _commit_all(run_dir, "rewrite")


@pytest.mark.parametrize(("change", "named"), [
    (_tweak_variant, "variants/V1/SKILL.md"),
    (_new_variant_file, "variants/V1/extra/notes.md"),
    (_edit_task, "task.md"),
    (_edit_gitignore, ".gitignore"),
    (_commit_max_tokens, "abtest.toml"),
    (_commit_variant, "variants/V1/SKILL.md"),
    (_rewrite_prereg, "PREREG.md"),
], ids=["tweaked-variant", "untracked-variant-file", "edited-task", "edited-gitignore", "committed-max-tokens",
        "committed-variant", "rewritten-prereg"])
def test_run_refuses_inputs_that_changed_since_the_seal(tmp_path, scratch_repo, skills_repo, fake_claude_path, monkeypatch,
                                                        capsys, change, named):
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo)
    env, creds = _env(fake_claude_path, tmp_path)
    _use_env(monkeypatch, env)
    assert T.main(["seal", str(run_dir)]) == 0
    change(run_dir)
    capsys.readouterr()
    assert T.main(_run_args(run_dir, creds, skills_repo, "--dry-run", "--only", "C", "--json")) == 2
    error = json.loads(capsys.readouterr().out)["data"]["error"]
    assert named in error and _arm_rows(run_dir) == []


def test_a_committed_prereg_amendment_runs_and_the_seal_row_names_the_commit(tmp_path, scratch_repo, skills_repo,
                                                                             fake_claude_path, monkeypatch):
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo)
    env, creds = _env(fake_claude_path, tmp_path)
    _use_env(monkeypatch, env)
    assert T.main(["seal", str(run_dir)]) == 0
    (seal,) = [r for r in L.read_jsonl(run_dir / "journal.jsonl") if r["step"] == "seal"]
    assert seal["commit"] == L.git(run_dir, "rev-parse", "--verify", "-q", "HEAD").stdout.strip()
    assert L.git(run_dir, "status", "--porcelain").stdout == "", "the journal is the run's output, not an input"
    with (run_dir / "PREREG.md").open("a", encoding="utf-8") as fh:
        fh.write("\n## Amendment 1\n\nH2: V1 also writes fewer tests.\n")
    _commit_all(run_dir, "amend")
    assert T.main(_run_args(run_dir, creds, skills_repo, "--dry-run", "--only", "C")) == 0


# --- whole-branch review: every arm's floor runs the suite as sealed ------------------------------

def _with_suite(tmp_path, scratch_repo, skills_repo, suite_text):
    """A run whose floor has an acceptance suite that is UNTRACKED in the workpiece (so no worktree has it)."""
    (scratch_repo / "acceptance").mkdir()
    (scratch_repo / "acceptance" / "check.sh").write_text(suite_text, encoding="utf-8")
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo)
    toml = run_dir / "abtest.toml"
    text = toml.read_text(encoding="utf-8")
    old = '# suite = "acceptance/test_task.py"\n# suite_cmd = ["pytest", "{suite}", "-q"]\n'
    assert text.count(old) == 1
    toml.write_text(text.replace(old, 'suite = "acceptance/check.sh"\nsuite_cmd = ["sh", "{suite}"]\n'), encoding="utf-8")
    return run_dir


def _suite_step(run_dir):
    res = json.loads((run_dir / "arms" / "r1-C" / "result.json").read_text(encoding="utf-8"))
    return res["floor"]["passed"], res["floor"]["steps"][-1]


def test_an_untracked_acceptance_suite_still_reaches_every_arms_floor(tmp_path, scratch_repo, skills_repo,
                                                                     fake_claude_path, monkeypatch):
    run_dir = _with_suite(tmp_path, scratch_repo, skills_repo, "echo acceptance ok\n")
    env, creds = _env(fake_claude_path, tmp_path)
    _use_env(monkeypatch, env)
    assert T.main(["seal", str(run_dir)]) == 0
    assert L.git(run_dir, "ls-files", "--error-unmatch", "sealed/acceptance/check.sh").returncode == 0, "committed"
    assert T.main(_run_args(run_dir, creds, skills_repo, "--dry-run", "--only", "C")) == 0
    passed, step = _suite_step(run_dir)
    assert passed is True and (step["name"], step["rc"], step["error"]) == ("suite", 0, None)


_REWRITES_SUITE = """
import subprocess
from pathlib import Path
Path("acceptance").mkdir(exist_ok=True)
Path("acceptance/check.sh").write_text("exit 0\\n", encoding="utf-8")
subprocess.run(["git", "add", "acceptance/check.sh"], check=True)
subprocess.run(["git", "-c", "user.name=arm", "-c", "user.email=arm@x", "commit", "-q", "-m", "make it pass"], check=True)
"""


def test_an_arm_that_rewrites_the_suite_still_runs_the_sealed_one(tmp_path, scratch_repo, skills_repo, fake_claude_path,
                                                                  monkeypatch):
    run_dir = _with_suite(tmp_path, scratch_repo, skills_repo, "echo the sealed suite fails\nexit 3\n")
    script = tmp_path / "rewrites_suite.py"
    script.write_text(_REWRITES_SUITE, encoding="utf-8")
    env, creds = _env(fake_claude_path, tmp_path)
    _use_env(monkeypatch, dict(env, FAKE_CLAUDE_SCRIPT=str(script)))
    assert T.main(["seal", str(run_dir)]) == 0
    assert T.main(_run_args(run_dir, creds, skills_repo, "--only", "C"), login_check=_Probe("ok")) == 0
    passed, step = _suite_step(run_dir)
    assert passed is False and (step["name"], step["rc"]) == ("suite", 3), "the arm's `exit 0` suite ran instead"


def test_run_refuses_a_sealed_suite_whose_hash_differs_from_the_seal_record(tmp_path, scratch_repo, skills_repo,
                                                                           fake_claude_path, monkeypatch, capsys):
    run_dir = _with_suite(tmp_path, scratch_repo, skills_repo, "exit 0\n")
    env, creds = _env(fake_claude_path, tmp_path)
    _use_env(monkeypatch, env)
    assert T.main(["seal", str(run_dir)]) == 0
    journal = run_dir / "journal.jsonl"
    rows = L.read_jsonl(journal)
    rows[-1]["suite_sha256"] = "0" * 64
    journal.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    capsys.readouterr()
    assert T.main(_run_args(run_dir, creds, skills_repo, "--dry-run", "--only", "C", "--json")) == 2
    assert "sealed/acceptance/check.sh" in json.loads(capsys.readouterr().out)["data"]["error"]
    assert _arm_rows(run_dir) == []


def test_run_refuses_an_edited_sealed_suite_copy(tmp_path, scratch_repo, skills_repo, fake_claude_path, monkeypatch, capsys):
    run_dir = _with_suite(tmp_path, scratch_repo, skills_repo, "exit 3\n")
    env, creds = _env(fake_claude_path, tmp_path)
    _use_env(monkeypatch, env)
    assert T.main(["seal", str(run_dir)]) == 0
    (run_dir / "sealed" / "acceptance" / "check.sh").write_text("exit 0\n", encoding="utf-8")
    capsys.readouterr()
    assert T.main(_run_args(run_dir, creds, skills_repo, "--dry-run", "--only", "C", "--json")) == 2
    assert "sealed/acceptance/check.sh" in json.loads(capsys.readouterr().out)["data"]["error"]
    _commit_all(run_dir, "loosen the suite")
    assert T.main(_run_args(run_dir, creds, skills_repo, "--dry-run", "--only", "C", "--json")) == 2
    assert "sealed/acceptance/check.sh" in json.loads(capsys.readouterr().out)["data"]["error"]
    assert _arm_rows(run_dir) == []


def _with_suite_from(tmp_path, scratch_repo, skills_repo, suite_text):
    """A run whose suite lives OUTSIDE the workpiece (floor.suite_from); the workpiece has no copy."""
    source = tmp_path / "other-repo" / "acceptance.sh"
    source.parent.mkdir()
    source.write_text(suite_text, encoding="utf-8")
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo)
    toml = run_dir / "abtest.toml"
    text = toml.read_text(encoding="utf-8")
    old = '# suite = "acceptance/test_task.py"\n# suite_cmd = ["pytest", "{suite}", "-q"]\n'
    assert text.count(old) == 1
    toml.write_text(text.replace(old, f'suite = "acceptance/check.sh"\nsuite_cmd = ["sh", "{{suite}}"]\n'
                                      f'suite_from = "{source.as_posix()}"\n'), encoding="utf-8")
    return run_dir, source


def test_seal_copies_the_suite_from_suite_from_and_every_floor_runs_it(tmp_path, scratch_repo, skills_repo,
                                                                     fake_claude_path, monkeypatch, capsys):
    run_dir, source = _with_suite_from(tmp_path, scratch_repo, skills_repo, "echo outside ok\n")
    assert not (scratch_repo / "acceptance").exists(), "the workpiece holds no suite"
    before = L.git(scratch_repo, "status", "--porcelain").stdout
    env, creds = _env(fake_claude_path, tmp_path)
    _use_env(monkeypatch, env)
    capsys.readouterr()
    assert T.main(["seal", str(run_dir), "--json"]) == 0
    stamp = json.loads(capsys.readouterr().out)["data"]
    sealed = run_dir / "sealed" / "acceptance" / "check.sh"
    assert sealed.read_bytes() == source.read_bytes()
    assert stamp["suite_sha256"] == L.sha256_file(source) and stamp["suite_from"] == source.as_posix()
    (seal,) = [r for r in L.read_jsonl(run_dir / "journal.jsonl") if r["step"] == "seal"]
    assert (seal["suite_from"], seal["suite_sha256"]) == (source.as_posix(), L.sha256_file(source))
    assert L.git(scratch_repo, "status", "--porcelain").stdout == before, "the workpiece is not dirtied"
    assert T.main(_run_args(run_dir, creds, skills_repo, "--only", "C"), login_check=_Probe("ok")) == 0
    passed, step = _suite_step(run_dir)
    assert passed is True and (step["name"], step["rc"], step["error"]) == ("suite", 0, None)


def test_seal_refuses_a_suite_from_that_does_not_exist(tmp_path, scratch_repo, skills_repo, capsys):
    run_dir, source = _with_suite_from(tmp_path, scratch_repo, skills_repo, "exit 0\n")
    source.unlink()
    capsys.readouterr()
    assert T.main(["seal", str(run_dir), "--json"]) == 2
    error = json.loads(capsys.readouterr().out)["data"]["error"]
    assert f"floor.suite_from {source} does not exist or is not a file" in error
    assert not (run_dir / "journal.jsonl").exists() and not (run_dir / "sealed").exists()


def test_without_suite_from_seal_still_reads_the_workpiece_and_records_none(tmp_path, scratch_repo, skills_repo, capsys):
    run_dir = _with_suite(tmp_path, scratch_repo, skills_repo, "exit 0\n")
    capsys.readouterr()
    assert T.main(["seal", str(run_dir), "--json"]) == 0
    stamp = json.loads(capsys.readouterr().out)["data"]
    assert stamp["suite_from"] is None
    assert stamp["suite_sha256"] == L.sha256_file(scratch_repo / "acceptance" / "check.sh")


def test_run_refuses_a_suite_from_copy_whose_hash_differs_from_the_seal(tmp_path, scratch_repo, skills_repo,
                                                                         fake_claude_path, monkeypatch, capsys):
    run_dir, source = _with_suite_from(tmp_path, scratch_repo, skills_repo, "exit 3\n")
    env, creds = _env(fake_claude_path, tmp_path)
    _use_env(monkeypatch, env)
    assert T.main(["seal", str(run_dir)]) == 0
    source.write_text("exit 0\n", encoding="utf-8")  # the source moving on changes nothing sealed
    assert T.main(_run_args(run_dir, creds, skills_repo, "--dry-run", "--only", "C")) == 0
    (run_dir / "sealed" / "acceptance" / "check.sh").write_text("exit 0\n", encoding="utf-8")
    _commit_all(run_dir, "loosen the sealed copy")
    capsys.readouterr()
    assert T.main(_run_args(run_dir, creds, skills_repo, "--dry-run", "--only", "V1", "--json")) == 2
    assert "sealed/acceptance/check.sh" in json.loads(capsys.readouterr().out)["data"]["error"]


_LEAVES_AN_UNREADABLE_FILE = """
import os
from pathlib import Path
Path("secret-draft.txt").write_text("cannot be read back\\n", encoding="utf-8")
os.chmod("secret-draft.txt", 0)
"""


@pytest.mark.skipif(sys.platform == "win32" or (hasattr(os, "geteuid") and os.geteuid() == 0),
                    reason="POSIX mode bits; root reads a mode-0 file anyway")
def test_a_failed_save_of_uncommitted_work_never_fails_the_paid_arm(tmp_path, scratch_repo, skills_repo, fake_claude_path,
                                                                     monkeypatch, capsys):
    script = tmp_path / "unreadable.py"
    script.write_text(_LEAVES_AN_UNREADABLE_FILE, encoding="utf-8")
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo)
    env, creds = _env(fake_claude_path, tmp_path)
    _use_env(monkeypatch, dict(env, FAKE_CLAUDE_SCRIPT=str(script)))
    assert T.main(["seal", str(run_dir)]) == 0
    capsys.readouterr()
    assert T.main(_run_args(run_dir, creds, skills_repo, "--only", "C"), login_check=_Probe("ok")) == 0
    assert _arm_rows(run_dir) == [(1, "C", "ran")], "the session is not paid for twice"
    res = json.loads((run_dir / "arms" / "r1-C" / "result.json").read_text(encoding="utf-8"))
    assert res["uncommitted"]["left_work"] is None and "untracked.tar" in res["uncommitted"]["error"]
    assert "save_uncommitted" in capsys.readouterr().err


# --- the sandbox a live arm runs in ([run] sandbox) -------------------------------------------------

@pytest.fixture
def fake_bwrap(fake_claude_path):
    """tests/fakes/bwrap beside the fake claude (so first on PATH); its calls land in bwrap-calls.jsonl."""
    target = fake_claude_path / "bwrap"
    shutil.copyfile(Path(__file__).resolve().parent / "fakes" / "bwrap", target)
    target.chmod(0o755)
    return fake_claude_path / "bwrap-calls.jsonl"


def _seal_as_an_older_harness_did(run_dir):
    """Drop the sandbox key after the seal and move the seal record onto that commit.

    A run sealed before the key existed looks exactly like this: a sealed, intact profile with no
    [run] sandbox. (seal itself now refuses such a profile.)
    """
    toml = run_dir / "abtest.toml"
    text = toml.read_text(encoding="utf-8")
    assert text.count('sandbox = "none"\n') == 1
    toml.write_text(text.replace('sandbox = "none"\n', ""), encoding="utf-8")
    for args in (("add", "abtest.toml"), (*T.SEAL_GIT, "commit", "-q", "-m", "older seal")):
        assert L.git(run_dir, *args).returncode == 0
    head = L.git(run_dir, "rev-parse", "HEAD").stdout.strip()
    rows = [dict(r, commit=head) if r.get("step") == "seal" else r for r in L.read_jsonl(run_dir / "journal.jsonl")]
    (run_dir / "journal.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def test_seal_refuses_a_profile_that_names_no_sandbox(tmp_path, scratch_repo, skills_repo, capsys):
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo)
    toml = run_dir / "abtest.toml"
    toml.write_text(toml.read_text(encoding="utf-8").replace('sandbox = "none"\n', ""), encoding="utf-8")
    capsys.readouterr()
    assert T.main(["seal", str(run_dir)]) == 2
    assert 'set sandbox = "bwrap"' in capsys.readouterr().err
    assert not (run_dir / "journal.jsonl").exists()


def test_seal_refuses_a_sandbox_value_it_does_not_know(tmp_path, scratch_repo, skills_repo, capsys):
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo, sandbox="docker")
    capsys.readouterr()
    assert T.main(["seal", str(run_dir)]) == 2
    assert 'run.sandbox: must be "bwrap", "bwrap-host-proc" or "none"' in capsys.readouterr().err


def test_a_run_sealed_without_the_key_dry_runs_but_refuses_a_live_arm(tmp_path, scratch_repo, skills_repo,
                                                                     fake_claude_path, monkeypatch, capsys):
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo)
    env, creds = _env(fake_claude_path, tmp_path)
    _use_env(monkeypatch, env)
    assert T.main(["seal", str(run_dir)]) == 0
    _seal_as_an_older_harness_did(run_dir)
    assert T.main(_run_args(run_dir, creds, skills_repo, "--dry-run", "--only", "C")) == 0
    capsys.readouterr()
    assert T.main(_run_args(run_dir, creds, skills_repo, "--only", "C"), login_check=_Probe("ok")) == 2
    assert 'set sandbox = "bwrap"' in capsys.readouterr().err
    assert _arm_rows(run_dir) == [(1, "C", "dry")], "the live arm never started"


def test_sandbox_none_is_recorded_in_the_journal_the_result_the_score_and_prune_run(
        tmp_path, scratch_repo, skills_repo, fake_claude_path, monkeypatch, capsys):
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo)
    env, creds = _env(fake_claude_path, tmp_path)
    _use_env(monkeypatch, env)
    assert T.main(["seal", str(run_dir)]) == 0
    assert T.main(_run_args(run_dir, creds, skills_repo, "--only", "C"), login_check=_Probe("ok")) == 0
    rows = [r for r in L.read_jsonl(run_dir / "journal.jsonl") if r["step"] == "arm"]
    assert [(r["status"], r["sandbox"]) for r in rows] == [("ran", "none")]
    assert json.loads((run_dir / "arms" / "r1-C" / "result.json").read_text(encoding="utf-8"))["sandbox"] == "none"
    capsys.readouterr()
    assert T.main(["score", str(run_dir), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["data"]["arms"]["r1-C"]["sandbox"] == "none"
    assert T.main(["score", str(run_dir)]) == 0
    assert "sandbox=none" in capsys.readouterr().out
    assert T.main(["prune-run", str(run_dir), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["data"]["sandbox"] == {"r1-C": "none"}


@pytest.mark.parametrize("sandbox", ["bwrap", "bwrap-host-proc"])
def test_a_bwrap_run_starts_the_session_inside_the_sandbox_argv(tmp_path, scratch_repo, skills_repo,
                                                               fake_claude_path, fake_bwrap, monkeypatch, sandbox):
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo, sandbox=sandbox)
    env, creds = _env(fake_claude_path, tmp_path)
    _use_env(monkeypatch, env)
    assert T.main(["seal", str(run_dir)]) == 0
    assert T.main(_run_args(run_dir, creds, skills_repo, "--only", "C"), login_check=_Probe("ok")) == 0
    probe, session = [json.loads(line) for line in fake_bwrap.read_text(encoding="utf-8").splitlines()]
    assert probe == [*A.BWRAP_BASES[sandbox][1:], "true"], "the probe runs the value's own shape, once"
    assert session[:len(A.BWRAP_BASES[sandbox]) - 1] == list(A.BWRAP_BASES[sandbox][1:])
    ws = scratch_repo / ".claude" / "worktrees" / f"abx-{run_dir.name}-r1-C"
    arm = run_dir / "arms" / "r1-C"
    pairs = list(zip(session, session[1:], session[2:], strict=False))
    rw = [(s, d) for flag, s, d in pairs if flag == "--bind"]
    common = (scratch_repo / ".git").resolve()
    own_entry = common / "worktrees" / ws.name
    assert rw == [(str(p), str(p)) for p in (ws, arm / "home", arm / "cfg", common, own_entry)]
    registry = str(common / "worktrees")
    assert session.index(registry) < session.index(str(own_entry)), "the arm's own entry is re-bound last"
    assert ("--tmpfs", str(Path.home())) in list(zip(session, session[1:], strict=False))
    ro = [s for flag, s, _ in pairs if flag == "--ro-bind"]
    assert str(scratch_repo) in ro and any(Path(s).parent == run_dir / "frozen" for s in ro), ro
    assert registry in ro, "the repo's worktree registry is read-only in the sandbox"
    chdir = session.index("--chdir")
    assert session[chdir + 1] == str(ws) and session[chdir + 2:chdir + 4] == ["claude", "-p"]
    rows = [r for r in L.read_jsonl(run_dir / "journal.jsonl") if r["step"] == "arm"]
    assert [(r["status"], r["sandbox"]) for r in rows] == [("ran", sandbox)]
    assert json.loads((arm / "result.json").read_text(encoding="utf-8"))["bundle_commits"] == 1


def test_a_bwrap_that_cannot_build_its_sandbox_refuses_the_live_run(tmp_path, scratch_repo, skills_repo,
                                                                   fake_claude_path, fake_bwrap, monkeypatch, capsys):
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo, sandbox="bwrap")
    env, creds = _env(fake_claude_path, tmp_path)
    _use_env(monkeypatch, dict(env, FAKE_BWRAP_REFUSE="1"))
    assert T.main(["seal", str(run_dir)]) == 0
    assert T.main(_run_args(run_dir, creds, skills_repo, "--dry-run", "--only", "C")) == 0, "a dry run needs no bwrap"
    assert not fake_bwrap.exists(), "a dry run never probes bwrap"
    capsys.readouterr()
    assert T.main(_run_args(run_dir, creds, skills_repo, "--only", "C"), login_check=_Probe("ok")) == 2
    err = capsys.readouterr().err
    assert 'cannot create its sandbox = "bwrap" here' in err and "No permissions to create new namespace" in err, err
    assert _arm_rows(run_dir) == [(1, "C", "dry")], "no live arm started"


def test_a_bwrap_refused_a_private_proc_names_bwrap_host_proc_as_the_remedy(
        tmp_path, scratch_repo, skills_repo, fake_claude_path, fake_bwrap, monkeypatch, capsys):
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo, sandbox="bwrap")
    env, creds = _env(fake_claude_path, tmp_path)
    _use_env(monkeypatch, dict(env, FAKE_BWRAP_REFUSE="proc"))
    assert T.main(["seal", str(run_dir)]) == 0
    capsys.readouterr()
    assert T.main(_run_args(run_dir, creds, skills_repo, "--only", "C"), login_check=_Probe("ok")) == 2
    err = capsys.readouterr().err
    assert 'set sandbox = "bwrap-host-proc"' in err and "Can't mount proc" in err, err
    assert _arm_rows(run_dir) == [], "no live arm started"


# --- a bare arm (remove_skill) with its own prompt (variant task_file) ---------------------------

BARE_TASK = "Do the task. Plan it yourself.\n"


def _add_bare(run_dir, *, write_task=BARE_TASK):
    """Add a remove_skill variant Vbare whose prompt is task-bare.md; write that file unless None."""
    toml = run_dir / "abtest.toml"
    text = toml.read_text(encoding="utf-8")
    assert text.count("\n[floor]\n") == 1
    toml.write_text(text.replace("\n[floor]\n", '\n[[variant]]\nname = "Vbare"\nremove_skill = true\n'
                                 'task_file = "task-bare.md"\nchanges = ["the plugin without the skill"]\n\n[floor]\n'),
                    encoding="utf-8")
    if write_task is not None:
        (run_dir / "task-bare.md").write_text(write_task, encoding="utf-8")


def _session_line(run_dir, label):
    (transcript,) = _transcripts(run_dir / "arms" / label)
    return json.loads((run_dir / "arms" / label / "transcripts" / transcript).read_text(encoding="utf-8"))


def test_a_bare_arm_gets_its_own_prompt_runs_without_the_skill_and_every_record_names_its_prompt(
        tmp_path, scratch_repo, skills_repo, fake_claude_path, monkeypatch, capsys):
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo)
    _add_bare(run_dir)
    env, creds = _env(fake_claude_path, tmp_path)
    _use_env(monkeypatch, env)
    capsys.readouterr()
    assert T.main(["seal", str(run_dir), "--json"]) == 0
    sha = {"task.md": L.sha256_file(run_dir / "task.md"), "task-bare.md": L.sha256_file(run_dir / "task-bare.md")}
    want = {"C": {"file": "task.md", "sha256": sha["task.md"]}, "V1": {"file": "task.md", "sha256": sha["task.md"]},
            "Vbare": {"file": "task-bare.md", "sha256": sha["task-bare.md"]}}
    assert json.loads(capsys.readouterr().out)["data"]["task_files"] == want
    (seal,) = [r for r in L.read_jsonl(run_dir / "journal.jsonl") if r["step"] == "seal"]
    assert seal["task_files"] == want and "task-bare.md" in (run_dir / "PREREG.md").read_text(encoding="utf-8")
    for arm in ("Vbare", "C"):
        assert T.main(_run_args(run_dir, creds, skills_repo, "--only", arm), login_check=_Probe("ok")) == 0
    bare, control = _session_line(run_dir, "r1-Vbare"), _session_line(run_dir, "r1-C")
    assert bare["prompt"] == BARE_TASK and control["prompt"] == "Do the task.\n", "each arm's prompt reached claude"
    assert "demo-skill" not in bare["installed_skills"] and "demo-skill" in control["installed_skills"]
    res = json.loads((run_dir / "arms" / "r1-Vbare" / "result.json").read_text(encoding="utf-8"))
    assert (res["task_file"], res["task_sha256"]) == ("task-bare.md", sha["task-bare.md"])
    assert res["frozen"]["skill_removed"] is True and res["install"]["drift"] == []
    rows = [(r["arm"], r["task_file"], r["task_sha256"]) for r in L.read_jsonl(run_dir / "journal.jsonl") if r["step"] == "arm"]
    assert rows == [("Vbare", "task-bare.md", sha["task-bare.md"]), ("C", "task.md", sha["task.md"])]
    capsys.readouterr()
    assert T.main(["score", str(run_dir), "--json"]) == 0
    arms = json.loads(capsys.readouterr().out)["data"]["arms"]
    assert {k: (v["task_file"], v["task_sha256"]) for k, v in arms.items()} == {
        "r1-Vbare": ("task-bare.md", sha["task-bare.md"]), "r1-C": ("task.md", sha["task.md"])}
    assert T.main(["score", str(run_dir)]) == 0
    assert f"task=task-bare.md@{sha['task-bare.md'][:12]}" in capsys.readouterr().out


@pytest.mark.parametrize("content", [None, "", "  \n"], ids=["missing", "empty", "blank"])
def test_seal_refuses_a_variant_task_file_that_is_missing_or_empty(tmp_path, scratch_repo, skills_repo, capsys, content):
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo)
    _add_bare(run_dir, write_task=content)
    capsys.readouterr()
    assert T.main(["seal", str(run_dir), "--json"]) == 2
    assert "task-bare.md is missing or empty" in json.loads(capsys.readouterr().out)["data"]["error"]
    assert not (run_dir / "journal.jsonl").exists()


def _edit_bare_task(run_dir):
    (run_dir / "task-bare.md").write_text(BARE_TASK + "Use bitranox:demo-skill.\n", encoding="utf-8")


def _commit_bare_task(run_dir):
    _edit_bare_task(run_dir)
    _commit_all(run_dir, "edit the bare prompt")


@pytest.mark.parametrize("change", [_edit_bare_task, _commit_bare_task], ids=["uncommitted", "committed"])
def test_run_refuses_an_edited_variant_task_file(tmp_path, scratch_repo, skills_repo, fake_claude_path, monkeypatch,
                                                 capsys, change):
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo)
    _add_bare(run_dir)
    env, creds = _env(fake_claude_path, tmp_path)
    _use_env(monkeypatch, env)
    assert T.main(["seal", str(run_dir)]) == 0
    change(run_dir)
    capsys.readouterr()
    assert T.main(_run_args(run_dir, creds, skills_repo, "--dry-run", "--only", "C", "--json")) == 2
    assert "task-bare.md" in json.loads(capsys.readouterr().out)["data"]["error"] and _arm_rows(run_dir) == []


def test_run_refuses_a_prompt_whose_sha_differs_from_the_seal_row(tmp_path, scratch_repo, skills_repo, fake_claude_path,
                                                                  monkeypatch, capsys):
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo)
    _add_bare(run_dir)
    env, creds = _env(fake_claude_path, tmp_path)
    _use_env(monkeypatch, env)
    assert T.main(["seal", str(run_dir)]) == 0
    journal = run_dir / "journal.jsonl"
    rows = L.read_jsonl(journal)
    rows[0]["task_files"]["Vbare"]["sha256"] = "0" * 64
    journal.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    capsys.readouterr()
    assert T.main(_run_args(run_dir, creds, skills_repo, "--dry-run", "--only", "C", "--json")) == 2
    assert "the prompt of arm Vbare (task-bare.md) differs from the seal" in json.loads(capsys.readouterr().out)["data"]["error"]


def _moved_config(tmp_path, monkeypatch):
    """HOME at tmp/home, CLAUDE_CONFIG_DIR at tmp/arm: (home, arm)."""
    home, arm = tmp_path / "home", tmp_path / "arm"
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(arm))
    return home, arm


def test_the_default_login_and_skills_clone_follow_claude_config_dir(tmp_path, monkeypatch):
    _, arm = _moved_config(tmp_path, monkeypatch)
    assert T.default_credentials() == arm / ".credentials.json"
    assert T.default_skills_repo() == arm / "plugins" / "marketplaces" / "bitranox-skills"
    args = T.build_parser().parse_args(["run", str(tmp_path / "run")])
    assert (args.credentials, args.skills_repo) == (None, None)    # resolved per run, not at build


def test_user_config_dir_answers_like_the_plugin_rule(tmp_path, monkeypatch):
    # abarm keeps a copy of hooks/claude_paths.config_dir(); pin the two to the same answers.
    hooks = Path(__file__).resolve().parents[3] / "hooks" / "claude_paths.py"
    spec = importlib.util.spec_from_file_location("_claude_paths_for_parity", hooks)
    rule = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rule)
    home, arm = _moved_config(tmp_path, monkeypatch)
    for value in (str(arm), "", "   ", None):
        if value is None:
            monkeypatch.delenv("CLAUDE_CONFIG_DIR")
        else:
            monkeypatch.setenv("CLAUDE_CONFIG_DIR", value)
        assert A.user_config_dir() == rule.config_dir(), value
    assert A.user_config_dir() == home / ".claude"


# --- one `run` per run dir: the lock, and SIGTERM taking the Ctrl-C path -------------------------

ABTEST = Path(T.__file__).resolve()
LOCK_FILE = "run.lock"  # spelt out, so the test reads RED (not AttributeError) on a harness without it
# Run by the fake claude after its commit: says the session started, then holds it until the
# test writes RELEASE (bounded, so a run that is never released still ends).
_HOLDS_THE_SESSION = """
import time
from pathlib import Path
Path(MARKER).write_text("held", encoding="utf-8")
for _ in range(400):
    if Path(RELEASE).exists():
        break
    time.sleep(0.05)
"""


def _lock_is_free(run_dir):
    """Whether run.lock exists and nobody holds it (a fresh flock on it succeeds at once)."""
    fcntl = pytest.importorskip("fcntl")
    path = run_dir / LOCK_FILE
    if not path.is_file():
        return False
    with path.open("r+", encoding="utf-8") as fh:
        try:
            fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return False
        fcntl.flock(fh, fcntl.LOCK_UN)
    return True


def _wait_for(path, seconds=90.0):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if path.exists():
            return True
        time.sleep(0.05)
    return False


def _held_child(tmp_path, run_dir, creds, skills_repo, env):
    """`abtest.py run` in a child process whose one arm's session is held open; (child, marker, release, script)."""
    marker, release, script = tmp_path / "session-held", tmp_path / "release", tmp_path / "hold.py"
    script.write_text(_HOLDS_THE_SESSION.replace("MARKER", repr(str(marker))).replace("RELEASE", repr(str(release))),
                      encoding="utf-8")
    child_env = dict(os.environ, **env, FAKE_CLAUDE_SCRIPT=str(script))
    argv = [sys.executable, str(ABTEST), *_run_args(run_dir, creds, skills_repo, "--only", "C", "--stop-grace-s", "1")]
    child = subprocess.Popen(argv, env=child_env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,  # nosec B603
                             text=True, encoding="utf-8", start_new_session=True)
    return child, marker, release, script


@pytest.mark.skipif(sys.platform == "win32", reason="flock and SIGTERM delivery are POSIX here")
def test_a_second_run_on_a_held_run_dir_is_refused_and_sigterm_ends_the_first_like_ctrl_c(
        tmp_path, scratch_repo, skills_repo, fake_claude_path, monkeypatch, capsys):
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo)
    env, creds = _env(fake_claude_path, tmp_path)
    assert T.main(["seal", str(run_dir)]) == 0
    child, marker, release, script = _held_child(tmp_path, run_dir, creds, skills_repo, env)
    cfg = run_dir / "arms" / "r1-C" / "cfg"
    try:
        assert _wait_for(marker), "the first run's session never started"
        assert cfg.is_dir() and not _lock_is_free(run_dir)
        # The first run's own environment: a harness without the lock would sweep the held arm's
        # config dir and set its arm aside before running it again.
        _use_env(monkeypatch, dict(env, FAKE_CLAUDE_SCRIPT=str(script)))
        capsys.readouterr()
        rc = T.main(_run_args(run_dir, creds, skills_repo, "--only", "C", "--json"), login_check=_Probe("ok"))
        out = json.loads(capsys.readouterr().out)
        assert rc == 2 and out["ok"] is False, out
        assert LOCK_FILE in out["data"]["error"] and f"pid {child.pid}" in out["data"]["error"], out
        assert cfg.is_dir(), "the refused run swept the held arm's config dir"
        assert not (run_dir / "arms" / "r1-C.attempt-1").exists(), "the refused run set the held arm aside"
        os.kill(child.pid, signal.SIGTERM)
        _, err = child.communicate(timeout=120)
    finally:
        release.write_text("go", encoding="utf-8")
        if child.poll() is None:
            os.killpg(child.pid, signal.SIGKILL)
            child.wait()
    assert child.returncode == 130, err
    assert "interrupted" in err
    assert _arm_rows(run_dir) == [(1, "C", "interrupted")]
    res = json.loads((run_dir / "arms" / "r1-C" / "result.json").read_text(encoding="utf-8"))
    assert res["stop_reason"] == "interrupted" and not cfg.exists()
    assert _lock_is_free(run_dir), "SIGTERM left the run dir locked"


def test_a_run_takes_the_lock_and_frees_it_and_the_sigterm_handler_at_its_end(
        tmp_path, scratch_repo, skills_repo, fake_claude_path, monkeypatch):
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo)
    env, creds = _env(fake_claude_path, tmp_path)
    _use_env(monkeypatch, env)
    assert T.main(["seal", str(run_dir)]) == 0
    before = signal.getsignal(signal.SIGTERM)
    assert T.main(_run_args(run_dir, creds, skills_repo, "--only", "C"), login_check=_Probe("ok")) == 0
    assert signal.getsignal(signal.SIGTERM) is before, "run left its SIGTERM handler installed"
    assert _lock_is_free(run_dir), "a finished run left the run dir locked"
    assert (run_dir / LOCK_FILE).read_text(encoding="utf-8").strip() == str(os.getpid()), "the lock names its holder"
    assert LOCK_FILE not in L.git(run_dir, "status", "--porcelain").stdout, "the lock file is gitignored"


# --- [workpiece] link: a gitignored build prerequisite linked into every arm's worktree ----------

PROTOC = Path(".packages") / "protoc" / "bin" / "protoc"
NEEDS_PROTOC = '["sh", "-c", "test -x .packages/protoc/bin/protoc"]'


def _plant_packages(repo, *, exclude_line="/.packages"):
    """A gitignored .packages dir holding an executable protoc, as a build script would leave it."""
    tool = repo / PROTOC
    tool.parent.mkdir(parents=True)
    tool.write_text("#!/bin/sh\necho protoc\n", encoding="utf-8")
    tool.chmod(0o755)
    if exclude_line is not None:
        with (repo / ".git" / "info" / "exclude").open("a", encoding="utf-8") as fh:
            fh.write(f"\n{exclude_line}\n")


def _with_link(run_dir, entries='[".packages"]'):
    toml = run_dir / "abtest.toml"
    text = toml.read_text(encoding="utf-8")
    assert text.count('task_file = "task.md"\n') == 1
    toml.write_text(text.replace('task_file = "task.md"\n', f'task_file = "task.md"\nlink = {entries}\n'), encoding="utf-8")


def test_a_linked_prerequisite_reaches_the_arms_floor_and_survives_prune_run(
        tmp_path, scratch_repo, skills_repo, fake_claude_path, monkeypatch, capsys):
    _plant_packages(scratch_repo)
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo, gate=NEEDS_PROTOC)
    _with_link(run_dir)
    env, creds = _env(fake_claude_path, tmp_path)
    _use_env(monkeypatch, env)
    assert T.main(["seal", str(run_dir)]) == 0
    assert T.main(_run_args(run_dir, creds, skills_repo, "--only", "C"), login_check=_Probe("ok")) == 0
    arm = run_dir / "arms" / "r1-C"
    res = json.loads((arm / "result.json").read_text(encoding="utf-8"))
    assert res["floor"]["passed"] is True, res["floor"]
    assert res["linked"] == [".packages"]
    assert not (arm / A.UNTRACKED_TAR).exists(), "the link was saved as the arm's own untracked work"
    assert T.main(["prune-run", str(run_dir)]) == 0
    assert (scratch_repo / PROTOC).is_file(), "removing the arm's worktree deleted the workpiece's real dir"
    assert not _ws(scratch_repo, run_dir, "r1-C").exists()


def test_without_the_link_the_same_gate_fails(tmp_path, scratch_repo, skills_repo, fake_claude_path, monkeypatch):
    _plant_packages(scratch_repo)
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo, gate=NEEDS_PROTOC)
    env, creds = _env(fake_claude_path, tmp_path)
    _use_env(monkeypatch, env)
    assert T.main(["seal", str(run_dir)]) == 0
    assert T.main(_run_args(run_dir, creds, skills_repo, "--only", "C"), login_check=_Probe("ok")) == 0
    res = json.loads((run_dir / "arms" / "r1-C" / "result.json").read_text(encoding="utf-8"))
    assert res["floor"]["passed"] is False and res["linked"] == []


def _track_packages(repo):
    for args in (("add", "-f", str(PROTOC)), ("commit", "-q", "-m", "vendor protoc")):
        assert L.git(repo, *args).returncode == 0


@pytest.mark.parametrize(("setup", "named"), [
    ("missing", "workpiece.link: .packages does not exist in the workpiece"),
    ("tracked", "workpiece.link: .packages is tracked by git"),
    ("not_ignored", "workpiece.link: .packages is not ignored by git"),
    ("negated", "workpiece.link: .packages is not ignored by git"),
    ("dir_only", "workpiece.link: .packages is ignored only as a directory (.packages/)"),
])
def test_seal_refuses_a_link_that_is_not_ignored_build_output(tmp_path, scratch_repo, skills_repo, capsys, setup, named):
    if setup != "missing":
        _plant_packages(scratch_repo, exclude_line={"tracked": "/.packages", "not_ignored": None,
                                                    "negated": "/.packages\n!/.packages",
                                                    "dir_only": ".packages/"}[setup])
    if setup == "tracked":
        _track_packages(scratch_repo)
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo)
    _with_link(run_dir)
    capsys.readouterr()
    assert T.main(["seal", str(run_dir)]) == 2
    err = capsys.readouterr().err
    assert named in err, err
    assert not (run_dir / "journal.jsonl").exists(), "a refused seal recorded nothing"


def _commit_file(repo, rel, text):
    (repo / rel).parent.mkdir(parents=True, exist_ok=True)
    (repo / rel).write_text(text, encoding="utf-8")
    for args in (("add", rel), ("commit", "-q", "-m", f"add {rel}")):
        assert L.git(repo, *args).returncode == 0


@pytest.mark.parametrize("layout", ["dir_only_beside_a_symlink_pattern", "nested_gitignore"])
def test_seal_accepts_a_link_git_ignores_as_a_symlink_and_the_arm_gets_it(
        tmp_path, scratch_repo, skills_repo, fake_claude_path, monkeypatch, layout):
    """The .gitignore files that decide are the ones a worktree has, so the seal check reads those."""
    if layout == "dir_only_beside_a_symlink_pattern":
        # The tracked .gitignore wins over info/exclude for the directory, but not for the symlink.
        _commit_file(scratch_repo, ".gitignore", "CLAUDE.local.md\n.packages/\n")
        _plant_packages(scratch_repo)
        entry, gate = ".packages", NEEDS_PROTOC
    else:
        _commit_file(scratch_repo, "third_party/.gitignore", "/protoc\n")
        (scratch_repo / "third_party" / "protoc").mkdir()
        (scratch_repo / "third_party" / "protoc" / "README").write_text("vendored\n", encoding="utf-8")
        entry, gate = "third_party/protoc", '["test", "-f", "third_party/protoc/README"]'
    (scratch_repo / ".base").write_text(L.git(scratch_repo, "rev-parse", "HEAD").stdout.strip(), encoding="utf-8")
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo, gate=gate)
    _with_link(run_dir, f'["{entry}"]')
    env, creds = _env(fake_claude_path, tmp_path)
    _use_env(monkeypatch, env)
    assert T.main(["seal", str(run_dir)]) == 0
    assert T.main(_run_args(run_dir, creds, skills_repo, "--only", "C"), login_check=_Probe("ok")) == 0
    res = json.loads((run_dir / "arms" / "r1-C" / "result.json").read_text(encoding="utf-8"))
    assert res["floor"]["passed"] is True and res["linked"] == [entry]


def test_a_link_adds_no_bind_to_the_sandbox(tmp_path, scratch_repo, skills_repo, fake_claude_path, fake_bwrap, monkeypatch):
    _plant_packages(scratch_repo)
    run_dir = _init_and_fill(tmp_path, scratch_repo, skills_repo, gate=NEEDS_PROTOC, sandbox="bwrap")
    _with_link(run_dir)
    env, creds = _env(fake_claude_path, tmp_path)
    _use_env(monkeypatch, env)
    assert T.main(["seal", str(run_dir)]) == 0
    assert T.main(_run_args(run_dir, creds, skills_repo, "--only", "C"), login_check=_Probe("ok")) == 0
    session = [json.loads(line) for line in fake_bwrap.read_text(encoding="utf-8").splitlines()][-1]
    assert not any(".packages" in a for a in session), "the link reaches the arm through the workpiece's read-only bind"
    assert str(scratch_repo) in session
    res = json.loads((run_dir / "arms" / "r1-C" / "result.json").read_text(encoding="utf-8"))
    assert res["floor"]["passed"] is True and res["linked"] == [".packages"]
