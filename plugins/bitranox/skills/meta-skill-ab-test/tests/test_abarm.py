"""abarm: freeze, install, worktree, dispatch, bundle, prune; through the fake claude and a scratch repo."""
import dataclasses
import json
import os
import shutil
import sys
import time
from pathlib import Path

import _ablib as L
import abarm as A
import abprofile as P
import abstream as S
import pytest
from abproc_testkit import SigintOnMarker, alive, gone_within, kill_if_alive, pids_in

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


# --- review fixes: reversible repo writes, the deadline, the workpiece's hooks, leftovers -----------


def _ext(repo):
    """The repo's extensions.worktreeConfig as git reads it: (rc, value)."""
    proc = L.git(repo, "config", "--local", "--get", "extensions.worktreeConfig")
    return proc.returncode, proc.stdout.strip()


def _arm_ws(repo, name="abx-t-r1-C"):
    return repo / ".claude" / "worktrees" / name


def _registered(repo):
    return L.git(repo, "worktree", "list", "--porcelain").stdout


def test_make_worktree_sets_worktree_config_only_when_unset_and_prune_restores_it(scratch_repo):
    base = (scratch_repo / ".base").read_text()
    assert _ext(scratch_repo)[0] == 1, "precondition: the scratch repo has no extensions.worktreeConfig"
    ws = _arm_ws(scratch_repo)
    info = A.make_worktree(scratch_repo, base, "abx/t/r1-C", ws, copy_untracked_claude_md=False)
    assert _ext(scratch_repo) == (0, "true")
    assert info["worktree_config_set_by_harness"] is True
    pruned = A.prune(ws, scratch_repo, ())
    assert _ext(scratch_repo)[0] == 1, "the harness's own write is undone"
    assert pruned["worktree_config"] == "unset"


def test_make_worktree_leaves_a_preset_worktree_config_alone(scratch_repo):
    L.git(scratch_repo, "config", "--local", "extensions.worktreeConfig", "true")
    base = (scratch_repo / ".base").read_text()
    ws = _arm_ws(scratch_repo)
    info = A.make_worktree(scratch_repo, base, "abx/t/r1-C", ws, copy_untracked_claude_md=False)
    assert info["worktree_config_set_by_harness"] is False
    pruned = A.prune(ws, scratch_repo, ())
    assert _ext(scratch_repo) == (0, "true"), "the user's own setting survives the prune"
    assert pruned["worktree_config"] == "untouched"


def test_make_worktree_refuses_an_explicitly_disabled_worktree_config(scratch_repo):
    L.git(scratch_repo, "config", "--local", "extensions.worktreeConfig", "false")
    base = (scratch_repo / ".base").read_text()
    ws = _arm_ws(scratch_repo)
    with pytest.raises(A.ArmError, match="extensions.worktreeConfig"):
        A.make_worktree(scratch_repo, base, "abx/t/r1-C", ws, copy_untracked_claude_md=False)
    assert not ws.exists() and _ext(scratch_repo) == (0, "false")


def test_prune_keeps_worktree_config_while_another_worktree_uses_it(scratch_repo, tmp_path):
    base = (scratch_repo / ".base").read_text()
    ws = _arm_ws(scratch_repo)
    A.make_worktree(scratch_repo, base, "abx/t/r1-C", ws, copy_untracked_claude_md=False)
    other = tmp_path / "users-own-worktree"
    L.git(scratch_repo, "worktree", "add", "-q", "--detach", str(other), base)
    L.git(other, "config", "--worktree", "user.name", "someone")
    pruned = A.prune(ws, scratch_repo, ())
    assert _ext(scratch_repo) == (0, "true"), "another worktree's config.worktree still needs it"
    assert pruned["worktree_config"] == "kept"
    assert [Path(p).name for p in pruned["worktree_config_kept_for"]] == ["config.worktree"]


# The state file's key is persisted data a later prune reads back, so its spelling is pinned here.
STATE_KEY = "worktree_config_set_by_harness"


def _hooks_of(ws):
    return ws.parent / f"{ws.name}.githooks"


def _state(ws):
    return json.loads((_hooks_of(ws) / A.STATE_FILE).read_text(encoding="utf-8"))


# The workpiece's post-checkout hook is the seam that makes a step after `worktree add` fail: git
# runs it inside `worktree add`, before make_worktree's own steps, so a lock it plants makes a later
# git write refuse. Nothing of abarm is patched.
LOCK_THE_WORKTREE = 'git worktree lock --reason test "$PWD"'
BLOCK_ITS_CONFIG_WORKTREE = 'touch "$(git rev-parse --git-dir)/config.worktree.lock"'
BLOCK_THE_SHARED_CONFIG = 'touch "$(git rev-parse --git-common-dir)/config.lock"'


def _post_checkout(repo, *lines):
    _hook(repo / ".git" / "hooks" / "post-checkout", "\n".join(lines))


@POSIX_ONLY
def test_make_worktree_rolls_back_when_the_hook_setup_fails(scratch_repo):
    _post_checkout(scratch_repo, BLOCK_ITS_CONFIG_WORKTREE)  # core.hooksPath, after the extension
    base = (scratch_repo / ".base").read_text()
    ws = _arm_ws(scratch_repo)
    with pytest.raises(A.ArmError, match="removed again"):
        A.make_worktree(scratch_repo, base, "abx/t/r1-C", ws, copy_untracked_claude_md=False)
    assert not ws.exists() and str(ws) not in _registered(scratch_repo), "the worktree is removed again"
    assert not _hooks_of(ws).exists(), "and with it the arm's hooks dir"
    assert _ext(scratch_repo)[0] == 1, "the extension the harness set is unset again"


@POSIX_ONLY
def test_make_worktree_keeps_the_hooks_and_the_extension_when_the_rollback_cannot_remove(scratch_repo):
    _post_checkout(scratch_repo, LOCK_THE_WORKTREE, BLOCK_ITS_CONFIG_WORKTREE)
    base = (scratch_repo / ".base").read_text()
    ws = _arm_ws(scratch_repo)
    with pytest.raises(A.ArmError) as err:
        A.make_worktree(scratch_repo, base, "abx/t/r1-C", ws, copy_untracked_claude_md=False)
    assert ws.is_dir() and _state(ws) == {STATE_KEY: True}, "the hooks dir lives as long as the worktree"
    assert _ext(scratch_repo) == (0, "true"), "and so does the extension"
    msg = str(err.value)
    assert f"{_hooks_of(ws)} and its {A.STATE_FILE} are kept" in msg
    assert "extensions.worktreeConfig, which the harness set, stays set" in msg
    assert f"worktree unlock {ws}" in msg and "run prune again" in msg
    L.git(scratch_repo, "worktree", "remove", "-f", "-f", str(ws))  # the cleanup the message names
    pruned = A.prune(ws, scratch_repo, ())
    assert not _hooks_of(ws).exists() and _ext(scratch_repo)[0] == 1 and pruned["worktree_config"] == "unset"
    assert pruned["worktree_removed"] is False, "it was already gone"


@POSIX_ONLY
def test_make_worktree_writes_the_state_before_it_sets_the_extension(scratch_repo):
    _post_checkout(scratch_repo, LOCK_THE_WORKTREE, BLOCK_THE_SHARED_CONFIG)
    base = (scratch_repo / ".base").read_text()
    ws = _arm_ws(scratch_repo)
    with pytest.raises(A.ArmError, match="git config failed"):
        A.make_worktree(scratch_repo, base, "abx/t/r1-C", ws, copy_untracked_claude_md=False)
    assert _state(ws) == {STATE_KEY: True}, "the state was written before the config call that failed"
    assert _ext(scratch_repo)[0] == 1, "the config call itself was refused"
    (scratch_repo / ".git" / "config.lock").unlink()
    L.git(scratch_repo, "worktree", "remove", "-f", "-f", str(ws))
    pruned = A.prune(ws, scratch_repo, ())
    assert pruned["worktree_config"] == "unset", "unsetting the never-set key is harmless"
    assert _ext(scratch_repo)[0] == 1 and not _hooks_of(ws).exists()


@pytest.mark.parametrize("kind", ["earlier_arm", "plain_file"])
def test_make_worktree_refuses_a_stray_hooks_path_before_adding_the_worktree(scratch_repo, kind):
    base = (scratch_repo / ".base").read_text()
    ws = _arm_ws(scratch_repo)
    hooks = _hooks_of(ws)
    hooks.parent.mkdir(parents=True)
    if kind == "earlier_arm":
        hooks.mkdir()
        (hooks / A.STATE_FILE).write_text(json.dumps({STATE_KEY: True}), encoding="utf-8")
        L.git(scratch_repo, "config", "--local", "extensions.worktreeConfig", "true")
    else:
        hooks.write_text("not a dir\n", encoding="utf-8")
    with pytest.raises(A.ArmError, match="leftover") as err:
        A.make_worktree(scratch_repo, base, "abx/t/r1-C", ws, copy_untracked_claude_md=False)
    assert not ws.exists() and str(ws) not in _registered(scratch_repo), "refused before worktree add"
    assert L.git(scratch_repo, "rev-parse", "--verify", "-q", "refs/heads/abx/t/r1-C").returncode == 1, \
        "worktree add -b never ran, so no branch was made"
    msg = str(err.value)
    assert f"prune of {ws} cleans it up, or rm -r {hooks}" in msg
    assert ("config --local --unset extensions.worktreeConfig" in msg) == (kind == "earlier_arm")
    pruned = A.prune(ws, scratch_repo, ())  # the route the message names
    assert not hooks.exists() and not hooks.is_symlink()
    assert pruned["worktree_config"] == ("unset" if kind == "earlier_arm" else "no_state")
    assert _ext(scratch_repo)[0] == 1


@POSIX_ONLY
def test_dispatch_deadline_fires_while_a_grandchild_holds_the_stream(tmp_path):
    """The leader exits at once; its child keeps stdout open. The deadline must still end it."""
    arm_dir = tmp_path / "arm"
    arm_dir.mkdir()
    code = ("import subprocess, sys; subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)']); "
            "sys.exit(0)")
    res = A.dispatch(arm_dir, tmp_path, {"PATH": os.environ["PATH"]}, [sys.executable, "-c", code],
                     max_tokens=10**7, deadline_s=1)
    assert res["stop_reason"] == "deadline" and res["wall_s"] < 15 and res["process_rc"] == 0


@POSIX_ONLY
def test_dispatch_kills_a_group_that_ignores_sigterm_after_the_grace(tmp_path):
    arm_dir = tmp_path / "arm"
    arm_dir.mkdir()
    # SIG_IGN survives exec, so the grandchild ignores SIGTERM too; only SIGKILL ends it.
    code = ("import signal, subprocess, sys; signal.signal(signal.SIGTERM, signal.SIG_IGN); "
            "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)']); sys.exit(0)")
    res = A.dispatch(arm_dir, tmp_path, {"PATH": os.environ["PATH"]}, [sys.executable, "-c", code],
                     max_tokens=10**7, deadline_s=1, stop_grace_s=1)
    assert res["stop_reason"] == "deadline"
    assert 1.5 <= res["wall_s"] < 15, "deadline plus the lowered grace, then SIGKILL"


def _hook(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\n" + body + "\n", encoding="utf-8", newline="\n")
    path.chmod(0o755)


@pytest.mark.parametrize("where", ["hookspath", "default"])
def test_make_worktree_keeps_the_workpiece_hooks(scratch_repo, tmp_path, where):
    _with_origin(scratch_repo, tmp_path)
    marker = tmp_path / "pre-commit-ran"
    if where == "hookspath":
        _hook(scratch_repo / "githooks" / "pre-commit", f"touch '{marker}'")
        _hook(scratch_repo / "githooks" / "pre-push", "exit 0")
        L.git(scratch_repo, "add", "githooks")
        L.git(scratch_repo, "-c", "user.name=t", "-c", "user.email=t@x", "commit", "-q", "-m", "hooks")
        L.git(scratch_repo, "config", "core.hooksPath", "githooks")
    else:
        _hook(scratch_repo / ".git" / "hooks" / "pre-commit", f"touch '{marker}'")
        _hook(scratch_repo / ".git" / "hooks" / "pre-push", "exit 0")
    base = L.git(scratch_repo, "rev-parse", "HEAD").stdout.strip()
    ws = _arm_ws(scratch_repo)
    info = A.make_worktree(scratch_repo, base, "abx/t/r1-C", ws, copy_untracked_claude_md=False)
    assert not marker.exists()
    L.git(ws, "-c", "user.name=t", "-c", "user.email=t@x", "commit", "-q", "--allow-empty", "-m", "arm work")
    assert marker.exists(), "the workpiece's pre-commit ran in the arm"
    refused = L.git(ws, "push", "origin", "HEAD")
    assert refused.returncode != 0 and "pushing is refused" in refused.stderr, "its own pre-push is not linked"
    assert info["hooks_linked"] == ["pre-commit"]


@POSIX_ONLY
def test_install_plugin_replaces_a_planted_credentials_link_and_tightens_cfg(tmp_path, user_home):
    cfg = tmp_path / "cfg"
    cfg.mkdir()
    cfg.chmod(0o755)
    victim = tmp_path / "victim.txt"
    victim.write_text("keep me\n", encoding="utf-8")
    (cfg / ".credentials.json").symlink_to(victim)
    creds = tmp_path / "creds.json"
    creds.write_text('{"fake": true}', encoding="utf-8")
    plugin = tmp_path / "frozen"
    frozen = A.Frozen(path=plugin, skills_ref="0" * 40, skill_dir=plugin / "skills" / "x", overlay_written=(), hashes={})
    empty_bin = tmp_path / "emptybin"
    empty_bin.mkdir()
    with pytest.raises(A.ArmError, match="could not start"):
        A.install_plugin(cfg, frozen, creds, {"PATH": str(empty_bin)})
    assert victim.read_text(encoding="utf-8") == "keep me\n", "the copy never writes through a planted link"
    target = cfg / ".credentials.json"
    assert not target.is_symlink() and target.read_text(encoding="utf-8") == '{"fake": true}'
    assert target.stat().st_mode & 0o777 == 0o600
    assert cfg.stat().st_mode & 0o777 == 0o700, "an existing cfg dir is tightened too"


@POSIX_ONLY
def test_prune_keeps_the_hooks_and_the_extension_while_the_worktree_survives(scratch_repo, tmp_path):
    _with_origin(scratch_repo, tmp_path)
    base = (scratch_repo / ".base").read_text()
    ws = _arm_ws(scratch_repo)
    A.make_worktree(scratch_repo, base, "abx/t/r1-C", ws, copy_untracked_claude_md=False)
    L.git(scratch_repo, "worktree", "lock", str(ws))  # a single --force does not remove a locked worktree
    with pytest.raises(A.ArmError, match="worktree remove") as err:
        A.prune(ws, scratch_repo, ())
    refused = L.git(ws, "push", "origin", "HEAD")
    assert refused.returncode != 0 and "pushing is refused" in refused.stderr, "the survivor still cannot push"
    assert _state(ws) == {STATE_KEY: True} and _ext(scratch_repo) == (0, "true")
    msg = str(err.value)
    assert f"{_hooks_of(ws)} and its {A.STATE_FILE} are kept" in msg
    assert "says the harness set extensions.worktreeConfig" in msg
    assert f"git -C {scratch_repo} worktree unlock {ws}" in msg and "run prune again" in msg
    L.git(scratch_repo, "worktree", "unlock", str(ws))
    pruned = A.prune(ws, scratch_repo, ())
    assert not ws.exists() and str(ws) not in _registered(scratch_repo) and not _hooks_of(ws).exists()
    assert _ext(scratch_repo)[0] == 1 and pruned["worktree_config"] == "unset"
    assert pruned["worktree_removed"] is True


@POSIX_ONLY
def test_prune_after_a_manual_remove_restores_the_extension_from_the_kept_state(scratch_repo):
    base = (scratch_repo / ".base").read_text()
    ws = _arm_ws(scratch_repo)
    A.make_worktree(scratch_repo, base, "abx/t/r1-C", ws, copy_untracked_claude_md=False)
    L.git(scratch_repo, "worktree", "lock", str(ws))
    with pytest.raises(A.ArmError, match="worktree remove") as err:
        A.prune(ws, scratch_repo, ())
    assert _state(ws) == {STATE_KEY: True}, "the failed prune kept the state the next one needs"
    assert f"git -C {scratch_repo} worktree remove -f -f {ws}" in str(err.value)
    L.git(scratch_repo, "worktree", "remove", "-f", "-f", str(ws))
    assert not ws.exists() and str(ws) not in _registered(scratch_repo), "precondition: the worktree is gone"
    pruned = A.prune(ws, scratch_repo, ())
    assert pruned["worktree_removed"] is False and pruned["worktree_config"] == "unset"
    assert not _hooks_of(ws).exists() and _ext(scratch_repo)[0] == 1


def test_make_worktree_refuses_an_existing_worktree_and_names_the_cleanup(scratch_repo):
    base = (scratch_repo / ".base").read_text()
    ws = _arm_ws(scratch_repo)
    A.make_worktree(scratch_repo, base, "abx/t/r1-C", ws, copy_untracked_claude_md=False)
    with pytest.raises(A.ArmError, match="worktree remove --force") as err:
        A.make_worktree(scratch_repo, base, "abx/t/r2-C", ws, copy_untracked_claude_md=False)
    assert str(ws) in str(err.value)
    assert L.git(scratch_repo, "rev-parse", "--verify", "-q", "refs/heads/abx/t/r2-C").returncode == 1


def test_make_worktree_refuses_a_plain_directory_in_the_way(scratch_repo):
    base = (scratch_repo / ".base").read_text()
    ws = _arm_ws(scratch_repo)
    ws.mkdir(parents=True)
    with pytest.raises(A.ArmError, match="not a worktree") as err:
        A.make_worktree(scratch_repo, base, "abx/t/r1-C", ws, copy_untracked_claude_md=False)
    assert str(ws) in str(err.value) and ws.is_dir(), "named, never deleted"


def test_make_worktree_refuses_an_existing_branch_and_never_deletes_it(scratch_repo):
    base = (scratch_repo / ".base").read_text()
    L.git(scratch_repo, "branch", "abx/t/r1-C", base)
    with pytest.raises(A.ArmError, match="branch -D abx/t/r1-C"):
        A.make_worktree(scratch_repo, base, "abx/t/r1-C", _arm_ws(scratch_repo), copy_untracked_claude_md=False)
    assert L.git(scratch_repo, "rev-parse", "--verify", "-q", "refs/heads/abx/t/r1-C").returncode == 0


def test_make_worktree_prunes_a_registration_whose_path_is_gone_then_refuses(scratch_repo):
    base = (scratch_repo / ".base").read_text()
    ws = _arm_ws(scratch_repo)
    A.make_worktree(scratch_repo, base, "abx/t/r1-C", ws, copy_untracked_claude_md=False)
    shutil.rmtree(ws)
    assert str(ws) in _registered(scratch_repo), "precondition: a stale registration"
    with pytest.raises(A.ArmError, match="abx/t/r1-C"):
        A.make_worktree(scratch_repo, base, "abx/t/r1-C", ws, copy_untracked_claude_md=False)
    assert str(ws) not in _registered(scratch_repo), "the stale registration of this path was removed"
    assert L.git(scratch_repo, "rev-parse", "--verify", "-q", "refs/heads/abx/t/r1-C").returncode == 0


def test_release_frozen_removes_the_checkout_and_its_registration(tmp_path, scratch_repo, skills_repo):
    run_dir, prof = _profile(tmp_path, scratch_repo, skills_repo)
    frozen = A.freeze_variant(run_dir, prof, "V1", skills_repo)
    assert str(frozen.path) in _registered(skills_repo)
    A.release_frozen(frozen, skills_repo)
    assert not frozen.path.exists() and str(frozen.path) not in _registered(skills_repo)


def test_release_frozen_of_a_vanished_checkout_prunes_the_registration(tmp_path, scratch_repo, skills_repo):
    run_dir, prof = _profile(tmp_path, scratch_repo, skills_repo)
    frozen = A.freeze_variant(run_dir, prof, "C", skills_repo)
    shutil.rmtree(frozen.path)
    A.release_frozen(frozen, skills_repo)
    assert str(frozen.path) not in _registered(skills_repo)


# --- whole-branch review: the harness never prunes the user's other stale registrations ----------


def _foreign_stale_worktree(repo, tmp_path, name):
    """A worktree of repo outside the harness's paths whose directory is gone (a disk not mounted)."""
    foreign = tmp_path / name
    assert L.git(repo, "worktree", "add", "-q", "--detach", str(foreign)).returncode == 0
    shutil.rmtree(foreign)
    assert str(foreign) in _registered(repo), "precondition: a stale foreign registration"
    return foreign


def test_a_leftover_refusal_drops_only_its_own_stale_registration(scratch_repo, tmp_path):
    base = (scratch_repo / ".base").read_text()
    foreign = _foreign_stale_worktree(scratch_repo, tmp_path, "users-offline-worktree")
    ws = _arm_ws(scratch_repo)
    A.make_worktree(scratch_repo, base, "abx/t/r1-C", ws, copy_untracked_claude_md=False)
    shutil.rmtree(ws)
    with pytest.raises(A.ArmError):
        A.make_worktree(scratch_repo, base, "abx/t/r1-C", ws, copy_untracked_claude_md=False)
    assert str(ws) not in _registered(scratch_repo)
    assert str(foreign) in _registered(scratch_repo), "a repo-wide prune dropped the user's registration"


def test_release_frozen_keeps_the_skills_repos_other_stale_registrations(tmp_path, scratch_repo, skills_repo):
    run_dir, prof = _profile(tmp_path, scratch_repo, skills_repo)
    foreign = _foreign_stale_worktree(skills_repo, tmp_path, "users-skills-worktree")
    for vanish in (False, True):
        frozen = A.freeze_variant(run_dir, prof, "C", skills_repo)
        if vanish:
            shutil.rmtree(frozen.path)
        A.release_frozen(frozen, skills_repo)
        assert str(frozen.path) not in _registered(skills_repo)
    assert str(foreign) in _registered(skills_repo), "a repo-wide prune dropped the user's registration"


# --- whole-branch review: nothing of the session's process group outlives dispatch -------------

# Ignores SIGTERM (its child inherits SIG_IGN), writes the child's pid and then its own (the
# marker), and keeps recreating out_dir while holding stdout open.
_IGNORES_TERM_SESSION = """
import os, signal, subprocess, sys, time
from pathlib import Path
signal.signal(signal.SIGTERM, signal.SIG_IGN)
pidfile, child_pidfile, out_dir = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
child_pidfile.write_text(str(child.pid), encoding="utf-8")
pidfile.write_text(str(os.getpid()), encoding="utf-8")
for _ in range(1200):
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "still-writing").write_text("x", encoding="utf-8")
    time.sleep(0.05)
"""

# Starts a daemon with its stdio on /dev/null (invisible to the pipes), waits for its pid, exits 0.
_DAEMON_SESSION = """
import subprocess, sys, time
from pathlib import Path
pidfile, mode = Path(sys.argv[1]), sys.argv[2]
code = ("import os, signal, sys, time; "
        + ("signal.signal(signal.SIGTERM, signal.SIG_IGN); " if mode == "ignore" else "")
        + "open(sys.argv[1], 'w').write(str(os.getpid())); time.sleep(60)")
subprocess.Popen([sys.executable, "-c", code, str(pidfile)], stdin=subprocess.DEVNULL,
                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
while not pidfile.exists() or not pidfile.read_text():
    time.sleep(0.01)
"""


@POSIX_ONLY
def test_an_interrupt_ends_the_whole_session_group_before_dispatch_returns(tmp_path):
    arm_dir = tmp_path / "arm"
    arm_dir.mkdir()
    pidfile, child_pidfile, cfg = tmp_path / "leader.pid", tmp_path / "child.pid", tmp_path / "cfg"
    argv = [sys.executable, "-c", _IGNORES_TERM_SESSION, str(pidfile), str(child_pidfile), str(cfg)]
    try:
        with SigintOnMarker(pidfile) as sigint, pytest.raises(KeyboardInterrupt):
            A.dispatch(arm_dir, tmp_path, {"PATH": os.environ["PATH"]}, argv, max_tokens=10**7, deadline_s=60,
                       stop_grace_s=1)
        assert sigint.sent
        leader, child = pids_in(pidfile, child_pidfile)
        assert not alive(leader), "the leader is reaped before dispatch re-raises"
        # A SIGKILLed process can take a moment to be scheduled out; the old daemon-timer kill
        # came only after the whole grace, by which time the session had rewritten cfg.
        assert gone_within(child, 0.5), "the session's child outlived dispatch"
        shutil.rmtree(cfg)
        time.sleep(0.3)
        assert not cfg.exists(), "a session still running recreated the deleted dir"
    finally:
        for pid in pids_in(pidfile, child_pidfile):
            kill_if_alive(pid)


@POSIX_ONLY
@pytest.mark.parametrize("mode", ["exit", "ignore"])
def test_a_daemon_the_session_left_is_gone_when_dispatch_returns(tmp_path, mode):
    arm_dir = tmp_path / "arm"
    arm_dir.mkdir()
    pidfile = tmp_path / "daemon.pid"
    argv = [sys.executable, "-c", _DAEMON_SESSION, str(pidfile), mode]
    try:
        res = A.dispatch(arm_dir, tmp_path, {"PATH": os.environ["PATH"]}, argv, max_tokens=10**7, deadline_s=60,
                         stop_grace_s=1)
        assert res["stop_reason"] == "finished" and res["process_rc"] == 0
        (pid,) = pids_in(pidfile)
        assert gone_within(pid, 0.5), f"daemon {pid} outlived the arm's session"
    finally:
        for pid in pids_in(pidfile):
            kill_if_alive(pid)


@POSIX_ONLY
def test_save_transcripts_copies_regular_files_under_projects_only(tmp_path):
    cfg = tmp_path / "cfg"
    (cfg / "projects" / "-p").mkdir(parents=True)
    (cfg / ".credentials.json").write_text('{"claudeAiOauth": {"accessToken": "tok-UNIQUE-55a1"}}', encoding="utf-8")
    (cfg / "settings.json").write_text("{}", encoding="utf-8")
    (cfg / "projects" / "-p" / "s1.jsonl").write_text('{"type": "user"}\n', encoding="utf-8")
    (cfg / "projects" / "-p" / "creds-link").symlink_to(cfg / ".credentials.json")
    (cfg / "projects" / "cfg-link").symlink_to(cfg, target_is_directory=True)
    dest = tmp_path / "arm" / "transcripts"
    assert A.save_transcripts(cfg, dest) == ["-p/s1.jsonl"]
    copied = [p for p in dest.rglob("*") if p.is_file() or p.is_symlink()]
    assert copied == [dest / "-p" / "s1.jsonl"]
    assert A.save_transcripts(tmp_path / "no-cfg", dest) == []


# --- the bubblewrap sandbox a live arm runs in ------------------------------------------------------

def _mounts(root, **over):
    """SandboxMounts laid out as a real arm is: the arm dir under the real home, the worktree under the repo."""
    real_home = root / "home" / "user"
    run = real_home / "runs" / "run1" / "arms" / "r1-C"
    repo = root / "wp"
    fields = {"ws": repo / ".claude" / "worktrees" / "abx-run1-r1-C", "home": run / "home", "cfg": run / "cfg",
              "git_common_dir": repo / ".git", "real_home": real_home,
              "read_only": (real_home / ".cargo", real_home / ".local", repo)}
    fields.update(over)
    return A.SandboxMounts(**fields)


def _binds(argv, flag):
    """Every (src, dest) of one bind flag, in argv order, with the index of the flag."""
    return [(i, argv[i + 1], argv[i + 2]) for i, a in enumerate(argv) if a == flag]


def test_sandbox_argv_is_the_exact_documented_prefix(tmp_path):
    m = _mounts(tmp_path)
    s = str
    assert A.sandbox_argv(m) == [
        "bwrap", "--die-with-parent", "--unshare-pid", "--unshare-ipc", "--unshare-uts",
        "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc", "--tmpfs", s(m.tmp),
        "--tmpfs", s(m.real_home),
        "--ro-bind", s(m.read_only[0]), s(m.read_only[0]), "--ro-bind", s(m.read_only[1]), s(m.read_only[1]),
        "--ro-bind", s(m.read_only[2]), s(m.read_only[2]),
        "--bind", s(m.ws), s(m.ws), "--bind", s(m.home), s(m.home), "--bind", s(m.cfg), s(m.cfg),
        "--bind", s(m.git_common_dir), s(m.git_common_dir),
        "--chdir", s(m.ws)]


def test_sandbox_argv_binds_exactly_the_four_writable_paths(tmp_path):
    m = _mounts(tmp_path)
    rw = [(src, dest) for _, src, dest in _binds(A.sandbox_argv(m), "--bind")]
    assert rw == [(str(p), str(p)) for p in (m.ws, m.home, m.cfg, m.git_common_dir)]
    assert "--bind-try" not in A.sandbox_argv(m) and "--dev-bind" not in A.sandbox_argv(m)


def test_sandbox_argv_mounts_the_home_tmpfs_before_every_bind_under_it(tmp_path):
    m = _mounts(tmp_path)
    argv = A.sandbox_argv(m)
    tmpfs_at = argv.index("--tmpfs", argv.index("--tmpfs") + 1)
    assert argv[tmpfs_at + 1] == str(m.real_home)
    under = [i for flag in ("--bind", "--ro-bind") for i, _, dest in _binds(argv, flag)
             if Path(dest).is_relative_to(m.real_home)]
    assert len(under) == 4, "the arm home, the arm cfg and the two link targets live under the real home"
    assert all(i > tmpfs_at for i in under)


def test_sandbox_argv_rebinds_the_link_targets_read_only_and_writable_binds_last(tmp_path):
    m = _mounts(tmp_path)
    argv = A.sandbox_argv(m)
    ro = _binds(argv, "--ro-bind")
    assert [(s, d) for _, s, d in ro[1:]] == [(str(p), str(p)) for p in m.read_only]
    first_rw = min(i for i, _, _ in _binds(argv, "--bind"))
    assert all(i < first_rw for i, _, _ in ro), "a read-only bind after a writable one under it would cover it"


def test_sandbox_argv_starts_the_session_in_the_worktree(tmp_path):
    m = _mounts(tmp_path)
    assert A.sandbox_argv(m)[-2:] == ["--chdir", str(m.ws)]
    assert "--unshare-net" not in A.sandbox_argv(m), "the session must reach the API"


def test_home_link_targets_names_the_existing_targets_only(tmp_path):
    real = tmp_path / "real"
    (real / ".cargo").mkdir(parents=True)
    home = tmp_path / "armhome"
    home.mkdir()
    (home / ".cargo").symlink_to(real / ".cargo")
    (home / ".rustup").symlink_to(real / ".rustup")  # dangling: its target is gone
    (home / ".local").mkdir()  # a plain dir is no link
    # samefile, not ==: os.readlink returns a \\?\-prefixed path on Windows, which realpath keeps (measured on 3.14).
    found = A.home_link_targets(home, (".cargo", ".rustup", ".local", ".cache"))
    assert len(found) == 1 and os.path.samefile(found[0], real / ".cargo"), found


def test_git_common_dir_of_a_worktree_is_the_main_repos_git_dir(scratch_repo, tmp_path):
    ws = tmp_path / "ws"
    _git_ok(scratch_repo, "worktree", "add", "-q", "-b", "sbx", str(ws))
    assert A.git_common_dir(ws) == (scratch_repo / ".git").resolve()


def test_bwrap_problem_names_a_missing_bwrap(tmp_path):
    empty = tmp_path / "emptybin"
    empty.mkdir()
    problem = A.bwrap_problem(str(empty))
    assert problem is not None and "bwrap is not on PATH" in problem and 'sandbox = "none"' in problem


@POSIX_ONLY
def test_bwrap_problem_names_a_refused_namespace(tmp_path):
    fake = tmp_path / "bin" / "bwrap"
    fake.parent.mkdir()
    fake.write_text("#!/bin/sh\necho 'bwrap: No permissions to create new namespace' >&2\nexit 1\n", encoding="utf-8")
    fake.chmod(0o755)
    problem = A.bwrap_problem(str(fake.parent))
    assert problem is not None and "rc 1" in problem and "No permissions to create new namespace" in problem


def _git_ok(repo, *args):
    proc = L.git(repo, *args)
    assert proc.returncode == 0, f"git {' '.join(args)}: {proc.stderr}"


@POSIX_ONLY
@pytest.mark.parametrize("sandbox", ["bwrap", "bwrap-host-proc"])
def test_bwrap_problem_probes_the_values_own_namespaces_and_proc(tmp_path, sandbox):
    """`bwrap --ro-bind / / true` alone passed on a host where the arm's argv then failed."""
    log = tmp_path / "argv.txt"
    fake = tmp_path / "bin" / "bwrap"
    fake.parent.mkdir()
    fake.write_text(f'#!/bin/sh\nprintf "%s\\n" "$@" > "{log}"\n', encoding="utf-8")
    fake.chmod(0o755)
    assert A.bwrap_problem(str(fake.parent), sandbox) is None
    base = A.BWRAP_BASES[sandbox]
    assert log.read_text(encoding="utf-8").splitlines() == [*base[1:], "true"]
    assert A.sandbox_argv(_mounts(tmp_path), sandbox=sandbox)[:len(base)] == list(base)


@POSIX_ONLY
def test_a_bwrap_refused_only_its_private_proc_names_bwrap_host_proc(tmp_path):
    fake = tmp_path / "bin" / "bwrap"
    fake.parent.mkdir()
    fake.write_text('#!/bin/sh\nfor a in "$@"; do\n  if [ "$a" = --proc ]; then\n'
                    "    echo \"bwrap: Can't mount proc on /newroot/proc: Operation not permitted\" >&2; exit 1\n"
                    "  fi\ndone\nexit 0\n", encoding="utf-8")
    fake.chmod(0o755)
    problem = A.bwrap_problem(str(fake.parent), "bwrap")
    assert problem is not None and 'set sandbox = "bwrap-host-proc"' in problem and "Can't mount proc" in problem
    assert A.bwrap_problem(str(fake.parent), "bwrap-host-proc") is None


def test_bwrap_host_proc_differs_from_bwrap_only_in_its_proc(tmp_path):
    m = _mounts(tmp_path)
    plain, host = A.sandbox_argv(m), A.sandbox_argv(m, sandbox="bwrap-host-proc")
    i = plain.index("--proc")
    assert plain[i:i + 2] == ["--proc", "/proc"]
    assert host == [*plain[:i], "--ro-bind", "/proc", "/proc", *plain[i + 2:]]
    assert "--proc" not in host
    assert all(flag in host for flag in ("--unshare-pid", "--unshare-ipc", "--unshare-uts"))


@POSIX_ONLY
@pytest.mark.parametrize("sandbox", ["bwrap", "bwrap-host-proc"])
def test_a_real_bwrap_sandbox_confines_writes_and_hides_the_real_home(tmp_path, sandbox):
    """sandbox_argv run for real, each value's full argv: the writable paths take writes, the real home is hidden.

    Each value is skipped only when its own probe fails (on the LXC dev box "bwrap" is refused a
    private /proc, while "bwrap-host-proc" runs). The fake real home sits under tmp_path; `tmp`
    points the private tmpfs away from /tmp, which holds tmp_path: a tmpfs over /tmp would hide the
    fake home whatever the home tmpfs does, and the test could not see that element go missing. A
    second, read-only check runs the production layout against the user's actual home and only
    asks whether ~/.ssh is visible.

    /proc: for every value the test process (same uid, outside the sandbox) has no readable
    environ and no usable root, and a write through that root leaves no file; for
    "bwrap-host-proc" also host PID 1's, and its cmdline stays readable (the known residual,
    and the proof that the /proc paths probed are real).
    """
    reason = A.bwrap_problem(os.environ.get("PATH"), sandbox)
    if reason:
        pytest.skip(f'sandbox = "{sandbox}" cannot run on this machine: {reason}')
    repo = tmp_path / "wp"
    repo.mkdir()
    _git_ok(repo, "init", "-q", "-b", "main")
    _git_ok(repo, "-c", "user.name=t", "-c", "user.email=t@x", "commit", "-q", "--allow-empty", "-m", "base")
    ws = repo / ".claude" / "worktrees" / "ws"
    _git_ok(repo, "worktree", "add", "-q", "-b", "arm", str(ws))
    real_home = tmp_path / "realhome"
    (real_home / ".ssh").mkdir(parents=True)
    (real_home / ".ssh" / "id_test").write_text("PRIVATE-KEY-7d1e\n", encoding="utf-8")
    secret = real_home / "notes.txt"
    secret.write_text("REAL-HOME-CONTENT-3b9a\n", encoding="utf-8")
    (real_home / ".cargo").mkdir()
    (real_home / ".cargo" / "tool.txt").write_text("CARGO-TOOL-5c2f\n", encoding="utf-8")
    home, cfg, priv_tmp = tmp_path / "armhome", tmp_path / "cfg", tmp_path / "privtmp"
    for d in (home, cfg, priv_tmp):
        d.mkdir()
    (home / ".cargo").symlink_to(real_home / ".cargo")
    common = A.git_common_dir(ws)
    m = A.SandboxMounts(ws=ws, home=home, cfg=cfg, git_common_dir=common, real_home=real_home,
                        read_only=(*A.home_link_targets(home, (".cargo",)), repo), tmp=priv_tmp)
    script = ('echo inside > "$1/inside.txt" && echo A_WS_WRITABLE\n'
              'cat "$2/notes.txt" 2>/dev/null\n'
              'echo tampered >> "$2/notes.txt" 2>/dev/null\n'
              'echo probe > "$3/sbx-probe" && echo C_COMMON_WRITABLE\n'
              'test -e "$2/.ssh" && echo D_SSH_VISIBLE\n'
              'cat "$2/.cargo/tool.txt"\n'
              'echo w > "$2/.cargo/w" 2>/dev/null && echo LINK_TARGET_WRITABLE\n'
              'echo "PWD=$(pwd)"\n'
              'cat /proc/1/environ >/dev/null 2>&1 && echo P1_ENVIRON_READABLE\n'
              'ls /proc/1/root/ >/dev/null 2>&1 && echo P1_ROOT_READABLE\n'
              'cat "/proc/$4/environ" >/dev/null 2>&1 && echo HOST_ENVIRON_READABLE\n'
              'ls "/proc/$4/root/" >/dev/null 2>&1 && echo HOST_ROOT_READABLE\n'
              'echo x > "/proc/$4/root$5" 2>/dev/null && echo HOST_ROOT_WRITABLE\n'
              'cat "/proc/$4/cmdline" >/dev/null 2>&1 && echo HOST_CMDLINE_READABLE\n')
    escape = tmp_path / "escape-through-proc-root.txt"
    proc = L.run([*A.sandbox_argv(m, sandbox=sandbox), "sh", "-c", script, "sh", str(ws), str(real_home), str(common),
                  str(os.getpid()), str(escape)], timeout=60)
    out = proc.stdout
    assert "A_WS_WRITABLE" in out and (ws / "inside.txt").is_file(), proc.stderr  # (a)
    assert "REAL-HOME-CONTENT" not in out, "(b) the real home's file is readable inside the sandbox"
    assert secret.read_text(encoding="utf-8") == "REAL-HOME-CONTENT-3b9a\n", "(b) a write reached the real home"
    assert "C_COMMON_WRITABLE" in out and (common / "sbx-probe").is_file(), proc.stderr  # (c)
    assert "D_SSH_VISIBLE" not in out, "(d) the real ~/.ssh is visible inside the sandbox"
    assert "CARGO-TOOL-5c2f" in out and "LINK_TARGET_WRITABLE" not in out, "a link target is re-bound read-only"
    assert f"PWD={ws}" in out
    for leak in ("HOST_ENVIRON_READABLE", "HOST_ROOT_READABLE", "HOST_ROOT_WRITABLE"):
        assert leak not in out, f"{leak}: a same-uid host process is reachable through /proc"
    assert not escape.exists(), "a write through /proc/<pid>/root reached the host filesystem"
    if sandbox == "bwrap-host-proc":
        assert "P1_ENVIRON_READABLE" not in out and "P1_ROOT_READABLE" not in out, out
        assert "HOST_CMDLINE_READABLE" in out, "the host /proc is not bound: the checks above prove nothing"
    real_ssh = Path.home() / ".ssh"
    if real_ssh.exists():
        live = dataclasses.replace(m, real_home=Path.home(), read_only=(repo,), tmp=Path("/tmp"))
        seen = L.run([*A.sandbox_argv(live, sandbox=sandbox), "sh", "-c", 'test -e "$1" && echo VISIBLE; echo done', "sh",
                      str(real_ssh)], timeout=60)
        assert "done" in seen.stdout and "VISIBLE" not in seen.stdout, seen.stderr


@POSIX_ONLY
def test_the_fake_claude_starts_inside_the_real_bwrap_host_proc_sandbox(tmp_path, scratch_repo, fake_claude_path):
    """A process that needs /proc starts inside the real sandbox, sees its cwd and writes in ws.

    The gap the earlier empty-/proc value fell through: every argv test passed while a real
    `claude -p` could not resolve its working directory. FAKE_CLAUDE_CWD_FROM_PROC makes the fake
    resolve its cwd through /proc/self/cwd the way that failure needs.
    """
    reason = A.bwrap_problem(os.environ.get("PATH"), "bwrap-host-proc")
    if reason:
        pytest.skip(f'sandbox = "bwrap-host-proc" cannot run on this machine: {reason}')
    ws = scratch_repo / ".claude" / "worktrees" / "abx-sbx-r1-C"
    _git_ok(scratch_repo, "worktree", "add", "-q", "-b", "abx/sbx/r1-C", str(ws))
    home, cfg, priv_tmp = tmp_path / "armhome", tmp_path / "cfg", tmp_path / "privtmp"
    for d in (home, cfg, priv_tmp):
        d.mkdir()
    # The fixtures sit in the checkout, which may live under the real home the sandbox hides.
    stream = tmp_path / "stream.jsonl"
    shutil.copyfile(FIXTURES / "stream-control.jsonl", stream)
    m = A.SandboxMounts(ws=ws, home=home, cfg=cfg, git_common_dir=A.git_common_dir(ws), real_home=Path.home(),
                        read_only=(scratch_repo,), tmp=priv_tmp)
    env = dict(L.git_env(), PATH=f"{fake_claude_path}{os.pathsep}{os.environ['PATH']}", HOME=str(home),
               CLAUDE_CONFIG_DIR=str(cfg), FAKE_CLAUDE_STREAM=str(stream), FAKE_CLAUDE_CWD_FROM_PROC="1")
    proc = L.run([*A.sandbox_argv(m, sandbox="bwrap-host-proc"), *A.claude_argv("Do the task.", 3)], env=env, timeout=120)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == stream.read_text(encoding="utf-8")
    assert (ws / "arm-work.txt").read_text(encoding="utf-8") == "done by the fake arm\n"
    assert L.git(ws, "log", "-1", "--format=%s").stdout.strip() == "Task 1: arm work"
    assert list((cfg / "projects").glob("*/*.jsonl")), "no transcript was written into the config dir"
