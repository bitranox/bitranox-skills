"""abarm: freeze, install, worktree, dispatch, bundle, prune; through the fake claude and a scratch repo."""
import dataclasses
import json
import os
import sys
from pathlib import Path

import _ablib as L
import abarm as A
import abprofile as P
import abstream as S
import pytest

FIXTURES = Path(__file__).resolve().parent / "fixtures"
POSIX_ONLY = pytest.mark.skipif(sys.platform == "win32", reason="the A/B harness is Linux only; Windows is unsupported")


def _profile(tmp_path, scratch_repo, skills_repo):
    ref = (skills_repo / ".ref").read_text()
    text = f'''
[workpiece]
repo = "{scratch_repo}"
base = "{(scratch_repo / '.base').read_text()}"
task_file = "task.md"
[control]
skills_ref = "{ref}"
skill = "demo-skill"
[[variant]]
name = "V1"
dir = "variants/V1"
changes = ["louder"]
markers = ["LOUDER"]
[floor]
gate = ["./gate.sh"]
cache_paths = ["target"]
[run]
model = "opus"
n = 1
deadline_s = 100
max_tokens = 5000
'''
    run_dir = tmp_path / "run"
    (run_dir / "variants" / "V1").mkdir(parents=True)
    (run_dir / "variants" / "V1" / "SKILL.md").write_text("---\nname: demo-skill\n---\nLOUDER text.\n", encoding="utf-8")
    (run_dir / "abtest.toml").write_text(text, encoding="utf-8")
    return run_dir, P.load_profile(run_dir / "abtest.toml")


@pytest.fixture
def user_home(tmp_path, monkeypatch):
    """A fake real home whose settings.json holds one seeded key and one that must stay behind."""
    home = tmp_path / "userhome"
    (home / ".claude").mkdir(parents=True)
    (home / ".claude" / "settings.json").write_text(
        json.dumps({"skillListingBudgetFraction": 0.2, "model": "not-copied"}), encoding="utf-8")
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.delenv("CLAUDE_CONFIG_DIR", raising=False)
    return home


def test_freeze_control_and_variant(tmp_path, scratch_repo, skills_repo):
    run_dir, prof = _profile(tmp_path, scratch_repo, skills_repo)
    c = A.freeze_variant(run_dir, prof, "C", skills_repo)
    v = A.freeze_variant(run_dir, prof, "V1", skills_repo)
    assert c.overlay_written == () and v.overlay_written == ("SKILL.md",)
    assert "LOUDER" in (v.skill_dir / "SKILL.md").read_text(encoding="utf-8")
    assert "LOUDER" not in (c.skill_dir / "SKILL.md").read_text(encoding="utf-8")
    assert c.hashes["SKILL.md"] != v.hashes["SKILL.md"]
    assert A.freeze_variant(run_dir, prof, "C", skills_repo).path == c.path, "idempotent: same checkout"


def test_freeze_refuses_an_unknown_variant(tmp_path, scratch_repo, skills_repo):
    run_dir, prof = _profile(tmp_path, scratch_repo, skills_repo)
    with pytest.raises(A.ArmError, match="no variant named 'V9'"):
        A.freeze_variant(run_dir, prof, "V9", skills_repo)


def test_freeze_refuses_a_ref_without_the_switch(tmp_path, scratch_repo, skills_repo):
    run_dir, prof = _profile(tmp_path, scratch_repo, skills_repo)
    (skills_repo / "hooks" / "self_improve_signals.py").write_text("# no switch here\n", encoding="utf-8")
    L.git(skills_repo, "-c", "user.name=t", "-c", "user.email=t@x", "commit", "-q", "-am", "drop the switch")
    ref = L.git(skills_repo, "rev-parse", "HEAD").stdout.strip()
    prof2 = P.Profile(path=prof.path, workpiece=prof.workpiece, control=P.Control(skills_ref=ref, skill="demo-skill"),
                      variants=prof.variants, floor=prof.floor, run=prof.run)
    with pytest.raises(A.ArmError, match="BITRANOX_MEMORY_WRITES"):
        A.freeze_variant(run_dir, prof2, "C", skills_repo)


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_plugin_root_follows_the_marketplace_source(tmp_path):
    checkout = tmp_path / "checkout"
    _write(checkout / ".claude-plugin" / "marketplace.json",
           json.dumps({"plugins": [{"name": "other", "source": "./x"}, {"name": "bitranox", "source": "./plugins/bitranox"}]}))
    assert A.plugin_root(checkout) == checkout / "plugins" / "bitranox"


def test_plugin_root_is_the_checkout_for_a_bare_plugin(tmp_path):
    _write(tmp_path / ".claude-plugin" / "plugin.json", "{}")
    assert A.plugin_root(tmp_path) == tmp_path


@pytest.mark.parametrize("market", [
    {"plugins": [{"name": "other", "source": "./x"}]},
    {"plugins": [{"name": "bitranox", "source": "../outside"}]},
    {"plugins": [{"name": "bitranox", "source": {"source": "github", "repo": "a/b"}}]},
])
def test_plugin_root_refuses_a_marketplace_without_a_local_bitranox(tmp_path, market):
    _write(tmp_path / ".claude-plugin" / "marketplace.json", json.dumps(market))
    with pytest.raises(A.ArmError, match="bitranox"):
        A.plugin_root(tmp_path)


def test_plugin_root_refuses_a_checkout_with_no_plugin(tmp_path):
    with pytest.raises(A.ArmError, match="neither"):
        A.plugin_root(tmp_path)


def test_install_plugin_verifies_bytes(tmp_path, scratch_repo, skills_repo, arm_env_base, user_home):
    run_dir, prof = _profile(tmp_path, scratch_repo, skills_repo)
    frozen = A.freeze_variant(run_dir, prof, "V1", skills_repo)
    creds = tmp_path / "creds.json"
    creds.write_text('{"fake": true}', encoding="utf-8")
    creds.chmod(0o600)
    cfg = run_dir / "arms" / "r1-V1" / "cfg"
    info = A.install_plugin(cfg, frozen, creds, arm_env_base)
    assert info["drift"] == [] and info["installed_version"] == "0.0.1-fixture"
    seeded = json.loads((cfg / "settings.json").read_text(encoding="utf-8"))
    assert set(seeded) <= {"skillListingBudgetFraction"}, "only the named keys are seeded"
    assert seeded == {"skillListingBudgetFraction": 0.2}, "seeded from the user's own settings.json"
    assert (cfg / ".credentials.json").stat().st_mode & 0o777 == 0o600
    assert '"fake"' not in json.dumps(info), "the credentials never reach the returned record"
    # A re-install overwrites the cache, so drift is planted on the frozen side's recorded hashes.
    bad = dataclasses.replace(frozen, hashes=dict(frozen.hashes, **{"SKILL.md": "0" * 64}))
    with pytest.raises(A.ArmError, match="drift"):
        A.install_plugin(cfg, bad, creds, arm_env_base)


@POSIX_ONLY
def test_install_plugin_turns_a_missing_claude_into_an_arm_error(tmp_path, user_home):
    plugin = tmp_path / "frozen"
    (plugin / "skills" / "demo-skill").mkdir(parents=True)
    frozen = A.Frozen(path=plugin, skills_ref="0" * 40, skill_dir=plugin / "skills" / "demo-skill",
                      overlay_written=(), hashes={})
    creds = tmp_path / "creds.json"
    creds.write_text("{}", encoding="utf-8")
    empty_bin = tmp_path / "emptybin"
    empty_bin.mkdir()
    with pytest.raises(A.ArmError, match="could not start"):
        A.install_plugin(tmp_path / "cfg", frozen, creds, {"PATH": str(empty_bin)})


def test_install_plugin_refuses_a_missing_credentials_file(tmp_path, user_home):
    plugin = tmp_path / "frozen"
    frozen = A.Frozen(path=plugin, skills_ref="0" * 40, skill_dir=plugin / "skills" / "x", overlay_written=(), hashes={})
    with pytest.raises(A.ArmError, match="no credentials file"):
        A.install_plugin(tmp_path / "cfg", frozen, tmp_path / "absent.json", {"PATH": ""})


def _with_origin(repo, tmp_path):
    bare = tmp_path / "origin.git"
    L.git(tmp_path, "init", "-q", "--bare", str(bare))
    L.git(repo, "remote", "add", "origin", str(bare))
    return bare


def test_make_worktree_branch_hook_and_untracked_claude_md(scratch_repo, tmp_path):
    _with_origin(scratch_repo, tmp_path)
    L.git(scratch_repo, "rm", "-q", "--cached", "CLAUDE.md")
    L.git(scratch_repo, "-c", "user.name=t", "-c", "user.email=t@x", "commit", "-q", "-m", "untrack")
    base = L.git(scratch_repo, "rev-parse", "HEAD").stdout.strip()
    (scratch_repo / "CLAUDE.md").write_text("# untracked root rules\n", encoding="utf-8")
    path = scratch_repo / ".claude" / "worktrees" / "abx-t-r1-C"
    info = A.make_worktree(scratch_repo, base, "abx/t/r1-C", path, copy_untracked_claude_md=True)
    assert info["head"] == base and info["claude_md_copied"] is True
    assert (path / "CLAUDE.md").read_text(encoding="utf-8") == "# untracked root rules\n"
    assert not (path / "CLAUDE.local.md").exists(), "CLAUDE.local.md already loads via the ancestor walk"
    assert L.git(path, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip() == "abx/t/r1-C"
    assert L.git(scratch_repo, "check-ignore", "-q", ".claude/worktrees/x").returncode == 0
    refused = L.git(path, "push", "origin", "HEAD")
    assert refused.returncode != 0 and "pushing is refused" in refused.stderr, "the pre-push hook refuses"
    with pytest.raises(A.ArmError):
        A.make_worktree(scratch_repo, base, "abx/t/r1-C", path, copy_untracked_claude_md=False)


def test_make_worktree_leaves_the_real_checkout_able_to_push(scratch_repo, tmp_path):
    _with_origin(scratch_repo, tmp_path)
    base = (scratch_repo / ".base").read_text()
    A.make_worktree(scratch_repo, base, "abx/t/r1-C", scratch_repo / ".claude" / "worktrees" / "abx-t-r1-C",
                    copy_untracked_claude_md=False)
    assert L.git(scratch_repo, "config", "core.hooksPath").stdout.strip() == "", "the hook is the arm's alone"
    assert L.git(scratch_repo, "push", "-q", "origin", "main").returncode == 0


def test_make_worktree_leaves_a_tracked_claude_md_alone(scratch_repo):
    base = (scratch_repo / ".base").read_text()
    path = scratch_repo / ".claude" / "worktrees" / "abx-t-r1-V1"
    info = A.make_worktree(scratch_repo, base, "abx/t/r1-V1", path, copy_untracked_claude_md=True)
    assert info["claude_md_copied"] is False
    assert (path / "CLAUDE.md").read_text(encoding="utf-8") == "# workpiece\n"


def test_make_worktree_refuses_when_a_negation_unignores_the_worktrees(scratch_repo):
    (scratch_repo / ".gitignore").write_text("CLAUDE.local.md\n!.claude/worktrees/\n", encoding="utf-8")
    base = (scratch_repo / ".base").read_text()
    with pytest.raises(A.ArmError, match="not ignored"):
        A.make_worktree(scratch_repo, base, "abx/t/r1-C", scratch_repo / ".claude" / "worktrees" / "w",
                        copy_untracked_claude_md=False)
    assert ".claude/worktrees/" in (scratch_repo / ".git" / "info" / "exclude").read_text(encoding="utf-8")


def test_make_worktree_turns_a_missing_git_into_an_arm_error(scratch_repo, tmp_path, monkeypatch):
    base = (scratch_repo / ".base").read_text()
    monkeypatch.setenv("PATH", str(tmp_path / "no-bin"))
    with pytest.raises(A.ArmError, match="git could not run"):
        A.make_worktree(scratch_repo, base, "abx/t/r1-C", scratch_repo / ".claude" / "worktrees" / "w",
                        copy_untracked_claude_md=False)


def test_arm_env_is_built_from_scratch(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDECODE", "1")
    monkeypatch.setenv("SECRET_THING", "x")
    env = A.arm_env(tmp_path / "cfg", tmp_path / "home", ("PATH", "LANG", "CLAUDECODE"))
    assert "CLAUDECODE" not in env and "SECRET_THING" not in env
    assert env["BITRANOX_MEMORY_WRITES"] == "off" and env["CLAUDE_CONFIG_DIR"] == str(tmp_path / "cfg")
    assert env["HOME"] == str(tmp_path / "home") and env["PATH"] == os.environ["PATH"]


@POSIX_ONLY
def test_arm_home_links_only_what_exists(tmp_path, monkeypatch):
    real = tmp_path / "realhome"
    (real / ".cargo").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(real))
    home = A.arm_home(tmp_path / "arm", (".cargo", ".rustup"))
    assert (home / ".cargo").is_symlink() and not (home / ".rustup").exists()


def test_claude_argv_pins_opus_and_the_stream():
    argv = A.claude_argv("do it", 7)
    assert argv[:3] == ["claude", "-p", "do it"]
    assert argv[argv.index("--model") + 1] == "opus" and argv[argv.index("--max-turns") + 1] == "7"
    assert argv[argv.index("--output-format") + 1] == "stream-json"


def test_dispatch_streams_and_bundles(tmp_path, scratch_repo, arm_env_base, fake_claude_path):
    base = (scratch_repo / ".base").read_text()
    ws = scratch_repo / ".claude" / "worktrees" / "abx-t-r1-C"
    A.make_worktree(scratch_repo, base, "abx/t/r1-C", ws, copy_untracked_claude_md=False)
    arm_dir = tmp_path / "arm"
    arm_dir.mkdir()
    env = dict(A.arm_env(arm_dir / "cfg", arm_dir / "home", ("PATH",)), **arm_env_base,
               FAKE_CLAUDE_STREAM=str(FIXTURES / "stream-control.jsonl"))
    (arm_dir / "cfg").mkdir()
    res = A.dispatch(arm_dir, ws, env, A.claude_argv("do the task", 5), max_tokens=10**7, deadline_s=60)
    assert res["stop_reason"] == "finished" and res["process_rc"] == 0 and res["total_cost_usd"] == 0.25
    assert (arm_dir / "stream.jsonl").stat().st_size > 0
    assert A.bundle(ws, base, arm_dir / "bundle.git") == 1
    assert L.git(scratch_repo, "bundle", "verify", str(arm_dir / "bundle.git")).returncode == 0
    (ws / "target").mkdir()
    (ws / "target" / "big").write_bytes(b"x" * 1000)
    pruned = A.prune(ws, scratch_repo, ("target",))
    assert pruned["cache_bytes"] >= 1000 and not ws.exists()
    assert L.git(scratch_repo, "rev-parse", "--verify", "-q", "abx/t/r1-C").returncode == 0, "the branch stays"


def test_dispatch_token_cap_ends_the_run(tmp_path, scratch_repo, arm_env_base):
    base = (scratch_repo / ".base").read_text()
    ws = scratch_repo / ".claude" / "worktrees" / "abx-t-r1-V1"
    A.make_worktree(scratch_repo, base, "abx/t/r1-V1", ws, copy_untracked_claude_md=False)
    arm_dir = tmp_path / "arm2"
    (arm_dir / "cfg").mkdir(parents=True)
    env = dict(A.arm_env(arm_dir / "cfg", arm_dir / "home", ("PATH",)), **arm_env_base,
               FAKE_CLAUDE_STREAM=str(FIXTURES / "stream-control.jsonl"))
    res = A.dispatch(arm_dir, ws, env, A.claude_argv("x", 5), max_tokens=100, deadline_s=60)
    assert res["stop_reason"] == "token_cap"


def test_dispatch_stops_on_a_void_stream(tmp_path, scratch_repo, arm_env_base):
    base = (scratch_repo / ".base").read_text()
    ws = scratch_repo / ".claude" / "worktrees" / "abx-t-r1-V1"
    A.make_worktree(scratch_repo, base, "abx/t/r1-V1", ws, copy_untracked_claude_md=False)
    stream = tmp_path / "haiku-main.jsonl"
    stream.write_text(json.dumps({"type": "system", "subtype": "init", "model": "claude-haiku-5-5"}) + "\n",
                      encoding="utf-8")
    arm_dir = tmp_path / "arm3"
    (arm_dir / "cfg").mkdir(parents=True)
    env = dict(A.arm_env(arm_dir / "cfg", arm_dir / "home", ("PATH",)), **arm_env_base, FAKE_CLAUDE_STREAM=str(stream))
    res = A.dispatch(arm_dir, ws, env, A.claude_argv("x", 5), max_tokens=10**7, deadline_s=60)
    assert res["stop_reason"] == "void" and "not an opus id" in res["void_reasons"][0]


@POSIX_ONLY
def test_dispatch_deadline_ends_a_silent_session(tmp_path):
    """A session that prints nothing must still end at the deadline, not when it chooses to."""
    arm_dir = tmp_path / "arm"
    arm_dir.mkdir()
    argv = [sys.executable, "-c", "import time; time.sleep(20)"]
    res = A.dispatch(arm_dir, tmp_path, {"PATH": os.environ["PATH"]}, argv, max_tokens=10**7, deadline_s=1)
    assert res["stop_reason"] == "deadline" and res["wall_s"] < 15
    assert S.NO_INIT_REASON in res["void_reasons"]


def test_dispatch_turns_a_missing_binary_into_an_arm_error(tmp_path):
    arm_dir = tmp_path / "arm"
    arm_dir.mkdir()
    with pytest.raises(A.ArmError, match="could not start"):
        A.dispatch(arm_dir, tmp_path, {"PATH": ""}, [str(tmp_path / "no-such-claude")], max_tokens=1, deadline_s=60)


def test_bundle_refuses_a_base_it_cannot_resolve(scratch_repo, tmp_path):
    with pytest.raises(A.ArmError, match="rev-list"):
        A.bundle(scratch_repo, "f" * 40, tmp_path / "b.git")


def test_bundle_of_no_commits_writes_nothing(scratch_repo, tmp_path):
    base = (scratch_repo / ".base").read_text()
    assert A.bundle(scratch_repo, base, tmp_path / "b.git") == 0 and not (tmp_path / "b.git").exists()


def test_delete_cfg_removes_the_credentials_copy(tmp_path):
    cfg = tmp_path / "cfg"
    cfg.mkdir()
    (cfg / ".credentials.json").write_text("{}", encoding="utf-8")
    A.delete_cfg(cfg)
    assert not cfg.exists()
    A.delete_cfg(cfg)
