"""abarm: freeze, install, worktree, dispatch, bundle, prune; through the fake claude and a scratch repo."""
import dataclasses
import json
import os
import shutil
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
def test_dispatch_kills_a_group_that_ignores_sigterm_after_the_grace(tmp_path, monkeypatch):
    monkeypatch.setattr(A, "STOP_GRACE_S", 1)
    arm_dir = tmp_path / "arm"
    arm_dir.mkdir()
    # SIG_IGN survives exec, so the grandchild ignores SIGTERM too; only SIGKILL ends it.
    code = ("import signal, subprocess, sys; signal.signal(signal.SIGTERM, signal.SIG_IGN); "
            "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)']); sys.exit(0)")
    res = A.dispatch(arm_dir, tmp_path, {"PATH": os.environ["PATH"]}, [sys.executable, "-c", code],
                     max_tokens=10**7, deadline_s=1)
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
    assert str(ws) not in _registered(scratch_repo), "git worktree prune ran"
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
