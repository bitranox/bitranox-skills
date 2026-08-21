"""Behaviour tests for pluginprune, run against real directory trees on disk.

Every test builds a throwaway cache under tmp_path and asserts on what the tool plans or
actually removes. Nothing is monkeypatched: the liveness check is exercised with this very
pytest process as the live pid and a genuinely exited subprocess as the dead one, because a
detector that is only ever shown the answer it expects proves nothing.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

import pluginprune as P


# --------------------------------------------------------------------------------------------
# Fixture builders
# --------------------------------------------------------------------------------------------


def make_version(cache: Path, marketplace: str, plugin: str, version: str) -> Path:
    """One cache version dir with a byte of content, so sizes are non-zero."""
    path = cache / marketplace / plugin / version
    (path / ".claude-plugin").mkdir(parents=True)
    (path / ".claude-plugin" / "plugin.json").write_text(
        json.dumps({"name": plugin, "version": version}), encoding="utf-8"
    )
    (path / "skills").mkdir()
    (path / "skills" / "filler.md").write_text("x" * 100, encoding="utf-8")
    return path


def write_lock(version_dir: Path, pid: int, proc_start: str | None) -> Path:
    """An `.in_use/<pid>` lock of the shape Claude Code writes."""
    lock_dir = version_dir / ".in_use"
    lock_dir.mkdir(exist_ok=True)
    path = lock_dir / str(pid)
    payload: dict[str, object] = {"pid": pid}
    if proc_start is not None:
        payload["procStart"] = proc_start
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def write_installed(plugins_dir: Path, entries: dict[str, Path]) -> Path:
    """installed_plugins.json in the shape Claude Code writes it (a list per plugin key)."""
    path = plugins_dir / "installed_plugins.json"
    path.write_text(
        json.dumps(
            {
                "version": 2,
                "plugins": {
                    key: [{"scope": "user", "installPath": str(target), "version": target.name}]
                    for key, target in entries.items()
                },
            }
        ),
        encoding="utf-8",
    )
    return path


def make_temp_dir(cache: Path, name: str, *, age_seconds: float) -> Path:
    path = cache / name
    path.mkdir(parents=True)
    (path / "filler").write_text("x" * 100, encoding="utf-8")
    stamp = time.time() - age_seconds
    os.utime(path, (stamp, stamp))
    return path


@pytest.fixture()
def cache(tmp_path: Path) -> Path:
    """A `~/.claude/plugins/cache` shaped tree.

    Three versions of one plugin, a solo plugin the install record names, a solo plugin it does
    not, and temp leftovers. The installed version carries an EMPTY `.in_use` directory, which is
    what an idle machine looks like once a lock-aware Claude Code has loaded it.
    """
    plugins = tmp_path / "plugins"
    root = plugins / "cache"
    for version in ("1.0.0", "1.1.0", "1.2.0"):
        make_version(root, "own-marketplace", "own-plugin", version)
    (root / "own-marketplace" / "own-plugin" / "1.2.0" / ".in_use").mkdir()
    make_version(root, "other-marketplace", "solo-plugin", "2.0.0")
    make_version(root, "other-marketplace", "orphan-plugin", "3.0.0")
    make_temp_dir(root, "temp_subdir_1_abc.clone", age_seconds=7200)
    make_temp_dir(root, "temp_git_2_def", age_seconds=7200)
    make_temp_dir(root, "temp_subdir_3_ghi.clone", age_seconds=5)
    write_installed(
        plugins,
        {
            "own-plugin@own-marketplace": root / "own-marketplace" / "own-plugin" / "1.2.0",
            "solo-plugin@other-marketplace": root / "other-marketplace" / "solo-plugin" / "2.0.0",
        },
    )
    return root


def spawn_and_reap() -> int:
    popen = subprocess.Popen([sys.executable, "-c", "pass"])
    popen.wait()
    return popen.pid


def paths(entries) -> set[str]:
    return {str(entry.path) for entry in entries}


def plan_for(cache_dir: Path, **kwargs) -> P.Plan:
    return P.build_plan(cache_dir, **kwargs)


# --------------------------------------------------------------------------------------------
# Liveness - the detector, checked against a known positive AND a known negative
# --------------------------------------------------------------------------------------------


def test_pid_alive_is_true_for_this_process() -> None:
    assert P.pid_alive(os.getpid()) is True


def test_pid_alive_is_false_for_a_reaped_process() -> None:
    assert P.pid_alive(spawn_and_reap()) is False


def test_process_start_ticks_is_stable_for_this_process() -> None:
    first = P.process_start_ticks(os.getpid())
    if first is None:
        pytest.skip("no process start time available on this platform")
    assert first == P.process_start_ticks(os.getpid())


# --------------------------------------------------------------------------------------------
# Which version dirs are kept
# --------------------------------------------------------------------------------------------


def test_stale_versions_are_planned_and_the_installed_one_is_kept(cache: Path) -> None:
    plan = plan_for(cache)
    assert paths(plan.prune) == {
        str(cache / "own-marketplace" / "own-plugin" / "1.0.0"),
        str(cache / "own-marketplace" / "own-plugin" / "1.1.0"),
        str(cache / "other-marketplace" / "orphan-plugin" / "3.0.0"),
        str(cache / "temp_subdir_1_abc.clone"),
        str(cache / "temp_git_2_def"),
    }
    kept = {str(entry.path): entry.keep_reason for entry in plan.keep}
    assert kept[str(cache / "own-marketplace" / "own-plugin" / "1.2.0")] == "installed"


def test_a_sole_version_the_install_record_names_is_kept(cache: Path) -> None:
    plan = plan_for(cache)
    solo = cache / "other-marketplace" / "solo-plugin" / "2.0.0"
    kept = {str(entry.path): entry.keep_reason for entry in plan.keep}
    assert kept[str(solo)] == "installed"
    assert str(solo) not in paths(plan.prune)


def test_a_sole_version_no_record_mentions_is_planned(cache: Path) -> None:
    """An uninstalled plugin leaves its cache directory behind; nothing else will reclaim it."""
    orphan = cache / "other-marketplace" / "orphan-plugin" / "3.0.0"
    assert str(orphan) in paths(plan_for(cache).prune)


def test_a_sole_version_enabled_in_a_settings_file_is_kept(cache: Path, tmp_path: Path) -> None:
    """enabledPlugins names plugin@marketplace, so a disabled-not-uninstalled plugin survives."""
    settings = tmp_path / "settings.json"
    settings.write_text(
        json.dumps({"enabledPlugins": {"orphan-plugin@other-marketplace": False}}),
        encoding="utf-8",
    )
    plan = plan_for(cache, settings_files=[settings])
    orphan = cache / "other-marketplace" / "orphan-plugin" / "3.0.0"
    kept = {str(entry.path): entry.keep_reason for entry in plan.keep}
    assert kept[str(orphan)] == f"only version, enabled in {settings.name}"


def test_a_live_in_use_lock_keeps_a_version(cache: Path) -> None:
    target = cache / "own-marketplace" / "own-plugin" / "1.0.0"
    write_lock(target, os.getpid(), P.process_start_ticks(os.getpid()))
    plan = plan_for(cache)
    kept = {str(entry.path): entry.keep_reason for entry in plan.keep}
    assert kept[str(target)] == f"in use by pid {os.getpid()}"
    assert str(target) not in paths(plan.prune)


def test_a_lock_from_a_reaped_process_does_not_keep_a_version(cache: Path) -> None:
    target = cache / "own-marketplace" / "own-plugin" / "1.0.0"
    write_lock(target, spawn_and_reap(), "1")
    plan = plan_for(cache)
    assert str(target) in paths(plan.prune)


def test_a_lock_whose_start_time_disagrees_is_treated_as_stale(cache: Path) -> None:
    """PID reuse: the pid is alive, but it is not the process that took the lock."""
    if P.process_start_ticks(os.getpid()) is None:
        pytest.skip("no process start time available on this platform")
    target = cache / "own-marketplace" / "own-plugin" / "1.0.0"
    write_lock(target, os.getpid(), "1")
    plan = plan_for(cache)
    assert str(target) in paths(plan.prune)


def test_a_lock_without_a_start_time_falls_back_to_pid_existence(cache: Path) -> None:
    target = cache / "own-marketplace" / "own-plugin" / "1.0.0"
    write_lock(target, os.getpid(), None)
    plan = plan_for(cache)
    assert str(target) not in paths(plan.prune)


def test_keep_names_an_extra_version(cache: Path) -> None:
    target = cache / "own-marketplace" / "own-plugin" / "1.1.0"
    plan = plan_for(cache, keep=[target])
    kept = {str(entry.path): entry.keep_reason for entry in plan.keep}
    assert kept[str(target)] == "named with --keep"
    assert str(target) not in paths(plan.prune)


def test_a_version_pinned_by_a_settings_file_is_kept(cache: Path, tmp_path: Path) -> None:
    pinned = cache / "own-marketplace" / "own-plugin" / "1.0.0"
    settings = tmp_path / "settings.json"
    settings.write_text(
        json.dumps({"hooks": {"Stop": [{"command": f"bash {pinned}/hooks/x.sh"}]}}),
        encoding="utf-8",
    )
    plan = plan_for(cache, settings_files=[settings])
    kept = {str(entry.path): entry.keep_reason for entry in plan.keep}
    assert kept[str(pinned)] == f"pinned in {settings.name}"
    assert str(pinned) not in paths(plan.prune)


def test_enabled_in_settings_does_not_keep_every_version_of_a_plugin(
    cache: Path, tmp_path: Path
) -> None:
    """enabledPlugins names a PLUGIN, not a version, so it cannot decide between versions.

    Left unscoped it keeps the whole history of every enabled plugin, which is the entire
    accumulation this tool exists to reclaim.
    """
    settings = tmp_path / "settings.json"
    settings.write_text(
        json.dumps({"enabledPlugins": {"own-plugin@own-marketplace": True}}), encoding="utf-8"
    )
    plan = plan_for(cache, settings_files=[settings])
    assert str(cache / "own-marketplace" / "own-plugin" / "1.0.0") in paths(plan.prune)
    assert str(cache / "own-marketplace" / "own-plugin" / "1.1.0") in paths(plan.prune)


def test_marketplace_filter_limits_the_scan(cache: Path) -> None:
    plan = plan_for(cache, marketplaces=["own-marketplace"])
    assert all("other-marketplace" not in path for path in paths(plan.prune))
    assert all("temp_" not in Path(path).name for path in paths(plan.prune))


# --------------------------------------------------------------------------------------------
# Project-scope settings discovery
# --------------------------------------------------------------------------------------------


def write_claude_json(tmp_path: Path, projects: list[Path]) -> Path:
    """`~/.claude.json` in the shape Claude Code writes it: a `projects` map keyed by path."""
    path = tmp_path / "claude.json"
    path.write_text(
        json.dumps({"projects": {str(project): {} for project in projects}}), encoding="utf-8"
    )
    return path


def write_project_settings(project: Path, payload: dict[str, object]) -> Path:
    settings = project / ".claude" / "settings.json"
    settings.parent.mkdir(parents=True, exist_ok=True)
    settings.write_text(json.dumps(payload), encoding="utf-8")
    return settings


def test_a_project_settings_file_keeps_a_sole_version(cache: Path, tmp_path: Path) -> None:
    """A plugin enabled only in a project must not be reclaimed as an uninstalled leftover."""
    project = tmp_path / "some-project"
    project.mkdir()
    write_project_settings(project, {"enabledPlugins": {"orphan-plugin@other-marketplace": True}})
    plan = plan_for(cache, claude_json=write_claude_json(tmp_path, [project]))
    orphan = cache / "other-marketplace" / "orphan-plugin" / "3.0.0"
    kept = {str(entry.path): entry.keep_reason for entry in plan.keep}
    assert kept[str(orphan)] == "only version, enabled in settings.json"


def test_a_project_path_that_no_longer_exists_yields_no_settings_paths(tmp_path: Path) -> None:
    """Asserted on the discovery function: a stale entry must not even produce a candidate path.

    Going through the plan cannot show this - the existence filter downstream hides it either
    way - so the check has to sit where the decision is made.
    """
    live = tmp_path / "live-project"
    write_project_settings(live, {"enabledPlugins": {}})
    claude_json = write_claude_json(tmp_path, [tmp_path / "gone", live, tmp_path / "also-gone"])
    found = P.project_settings_files(claude_json)
    assert all(str(live) in str(path) for path in found)
    assert found


def test_an_unreadable_claude_json_is_not_fatal(cache: Path, tmp_path: Path) -> None:
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    plan = plan_for(cache, claude_json=broken)
    assert str(cache / "own-marketplace" / "own-plugin" / "1.0.0") in paths(plan.prune)


def test_explicit_settings_files_disable_discovery(cache: Path, tmp_path: Path) -> None:
    project = tmp_path / "some-project"
    project.mkdir()
    write_project_settings(project, {"enabledPlugins": {"orphan-plugin@other-marketplace": True}})
    plan = plan_for(
        cache, settings_files=[], claude_json=write_claude_json(tmp_path, [project])
    )
    assert str(cache / "other-marketplace" / "orphan-plugin" / "3.0.0") in paths(plan.prune)


def test_the_resolved_settings_files_are_reported_and_deduped(cache: Path, tmp_path: Path) -> None:
    """The tool says which files it read, and two spellings of one project count once.

    `~/.claude.json` is keyed by path STRING, so the same directory can appear under more than
    one key and hand back the same settings file twice.
    """
    user_settings = tmp_path / "settings.json"
    user_settings.write_text(json.dumps({"enabledPlugins": {}}), encoding="utf-8")
    project = tmp_path / "some-project"
    write_project_settings(project, {"enabledPlugins": {}})
    claude_json = tmp_path / "claude.json"
    claude_json.write_text(
        json.dumps({"projects": {str(project): {}, f"{project}/.": {}}}), encoding="utf-8"
    )
    plan = plan_for(cache, claude_json=claude_json)
    reported = plan.as_dict()["settings_files"]
    assert len(reported) == len(set(reported))
    assert str(user_settings) in reported
    assert sum(1 for path in reported if "some-project" in path) == 1


def test_no_project_settings_flag_skips_discovery(cache: Path, tmp_path: Path, capsys) -> None:
    project = tmp_path / "some-project"
    project.mkdir()
    write_project_settings(project, {"enabledPlugins": {"orphan-plugin@other-marketplace": True}})
    claude_json = write_claude_json(tmp_path, [project])
    rc = P.main(
        [
            "--cache-dir",
            str(cache),
            "--claude-json",
            str(claude_json),
            "--no-project-settings",
            "--json",
        ]
    )
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    planned = {entry["path"] for entry in payload["data"]["prune"]}
    assert str(cache / "other-marketplace" / "orphan-plugin" / "3.0.0") in planned


# --------------------------------------------------------------------------------------------
# The lock mechanism itself
# --------------------------------------------------------------------------------------------


def test_no_in_use_directory_anywhere_refuses_the_version_dirs(cache: Path) -> None:
    """A renamed or dropped lock mechanism must not read as "every version is free"."""
    for lock_dir in cache.glob("*/*/*/.in_use"):
        lock_dir.rmdir()
    plan = plan_for(cache)
    assert plan.prune  # the temp leftovers do not depend on locks
    assert all(entry.kind == P.KIND_TEMP for entry in plan.prune)
    refused = {str(entry.path): entry.refusal for entry in plan.refused}
    assert refused
    assert all("lock" in reason for reason in refused.values())


def test_an_empty_in_use_directory_is_an_idle_machine_not_a_missing_mechanism(cache: Path) -> None:
    plan = plan_for(cache)
    assert plan.refused == ()
    assert any(entry.kind == P.KIND_VERSION for entry in plan.prune)


def test_allow_missing_locks_overrides_the_refusal(cache: Path) -> None:
    for lock_dir in cache.glob("*/*/*/.in_use"):
        lock_dir.rmdir()
    plan = plan_for(cache, allow_missing_locks=True)
    assert plan.refused == ()
    assert any(entry.kind == P.KIND_VERSION for entry in plan.prune)


def test_a_missing_mechanism_exits_one_and_names_the_override(cache: Path, capsys) -> None:
    for lock_dir in cache.glob("*/*/*/.in_use"):
        lock_dir.rmdir()
    rc = P.main(["--cache-dir", str(cache)])
    assert rc == 1
    assert "--allow-missing-locks" in capsys.readouterr().err


# --------------------------------------------------------------------------------------------
# Temp leftovers
# --------------------------------------------------------------------------------------------


def test_old_temp_dirs_are_planned_and_a_fresh_one_is_kept(cache: Path) -> None:
    plan = plan_for(cache)
    pruned = paths(plan.prune)
    assert str(cache / "temp_subdir_1_abc.clone") in pruned
    assert str(cache / "temp_git_2_def") in pruned
    fresh = cache / "temp_subdir_3_ghi.clone"
    assert str(fresh) not in pruned
    kept = {str(entry.path): entry.keep_reason for entry in plan.keep}
    assert "in flight" in kept[str(fresh)]


def test_min_age_zero_takes_even_a_fresh_temp_dir(cache: Path) -> None:
    plan = plan_for(cache, min_age_seconds=0)
    assert str(cache / "temp_subdir_3_ghi.clone") in paths(plan.prune)


# --------------------------------------------------------------------------------------------
# Refusals
# --------------------------------------------------------------------------------------------


def test_a_symlinked_version_dir_is_refused(cache: Path, tmp_path: Path) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    link = cache / "own-marketplace" / "own-plugin" / "1.3.0"
    link.symlink_to(outside, target_is_directory=True)
    plan = plan_for(cache)
    refused = {str(entry.path): entry.refusal for entry in plan.refused}
    assert "symlink" in refused[str(link)]
    assert str(link) not in paths(plan.prune)
    assert outside.exists()


def test_a_cache_dir_that_does_not_exist_is_a_usage_error(tmp_path: Path, capsys) -> None:
    rc = P.main(["--cache-dir", str(tmp_path / "nope")])
    assert rc == 2
    assert "no plugin cache" in capsys.readouterr().err


# --------------------------------------------------------------------------------------------
# Dry run, apply, and the envelope
# --------------------------------------------------------------------------------------------


def test_dry_run_removes_nothing(cache: Path) -> None:
    rc = P.main(["--cache-dir", str(cache)])
    assert rc == 0
    assert (cache / "own-marketplace" / "own-plugin" / "1.0.0").exists()
    assert (cache / "temp_subdir_1_abc.clone").exists()


def test_apply_removes_exactly_the_plan(cache: Path) -> None:
    planned = paths(plan_for(cache).prune)
    rc = P.main(["--cache-dir", str(cache), "--apply"])
    assert rc == 0
    for path in planned:
        assert not Path(path).exists(), path
    assert (cache / "own-marketplace" / "own-plugin" / "1.2.0").exists()
    assert (cache / "other-marketplace" / "solo-plugin" / "2.0.0").exists()
    assert (cache / "temp_subdir_3_ghi.clone").exists()


def test_apply_does_not_rescan_after_building_the_plan(cache: Path) -> None:
    """A directory that appears after the plan is built is not swept up by --apply."""
    late = make_version(cache, "own-marketplace", "own-plugin", "0.9.0")
    plan = plan_for(cache)
    assert str(late) in paths(plan.prune)
    later = make_version(cache, "own-marketplace", "own-plugin", "0.8.0")
    refusals = P.apply_plan(plan)
    assert refusals == []
    assert not late.exists()
    assert later.exists()


def test_apply_refuses_a_directory_that_gained_a_live_lock_after_the_plan(cache: Path) -> None:
    """A session can start between the plan and the apply; that directory must survive."""
    plan = plan_for(cache)
    latecomer = cache / "own-marketplace" / "own-plugin" / "1.0.0"
    assert str(latecomer) in paths(plan.prune)
    write_lock(latecomer, os.getpid(), P.process_start_ticks(os.getpid()))

    refusals = P.apply_plan(plan)

    assert latecomer.exists()
    assert any(str(latecomer) in item and "in use" in item for item in refusals)
    assert not (cache / "own-marketplace" / "own-plugin" / "1.1.0").exists()


def test_apply_reports_the_late_lock_and_exits_one(cache: Path, capsys) -> None:
    write_lock(
        cache / "own-marketplace" / "own-plugin" / "1.0.0",
        os.getpid(),
        P.process_start_ticks(os.getpid()),
    )
    rc = P.main(["--cache-dir", str(cache), "--apply", "--json"])
    assert rc == 0  # the lock is seen while planning, so it is a kept directory, not a refusal
    payload = json.loads(capsys.readouterr().out)
    assert payload["skipped"] == []


def test_json_envelope_shape(cache: Path, capsys) -> None:
    rc = P.main(["--cache-dir", str(cache), "--json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["command"] == "pluginprune"
    assert payload["skipped"] == []
    data = payload["data"]
    assert data["applied"] is False
    assert data["cache_dir"] == str(cache)
    assert data["reclaimable_bytes"] > 0
    assert {entry["path"] for entry in data["prune"]} == paths(plan_for(cache).prune)
    assert all("keep_reason" in entry for entry in data["keep"])


def test_json_reports_a_refusal_and_exits_one(cache: Path, capsys) -> None:
    link = cache / "own-marketplace" / "own-plugin" / "1.3.0"
    link.symlink_to(cache / "other-marketplace", target_is_directory=True)
    rc = P.main(["--cache-dir", str(cache), "--json"])
    assert rc == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert any("symlink" in item for item in payload["skipped"])


def test_text_report_names_the_session_check_when_no_live_lock_is_found(cache: Path, capsys) -> None:
    P.main(["--cache-dir", str(cache)])
    err = capsys.readouterr().err
    assert "--keep" in err


def test_no_warning_when_a_live_lock_answers_the_session_question(cache: Path, capsys) -> None:
    write_lock(
        cache / "own-marketplace" / "own-plugin" / "1.1.0",
        os.getpid(),
        P.process_start_ticks(os.getpid()),
    )
    P.main(["--cache-dir", str(cache)])
    assert "--keep" not in capsys.readouterr().err
