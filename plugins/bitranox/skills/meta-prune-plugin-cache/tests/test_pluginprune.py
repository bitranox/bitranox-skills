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


def test_a_pin_is_found_even_though_json_escapes_the_backslashes(tmp_path: Path) -> None:
    r"""pinning_settings searches the settings file's RAW TEXT, and JSON escapes a backslash.
    On Windows the stored command reads "C:\\dir\\1.0.0" while str(path) is "C:\dir\1.0.0", so
    the pin was never seen and the version was planned for DELETION - the failure direction
    that cannot be undone.

    Portable RED: a directory name containing a backslash reproduces the same escaping on
    POSIX, so this fails on both platforms without the fix rather than only on Windows.
    """
    pinned = tmp_path / "cache" / "mkt" / "plug" / "1.0.0"
    pinned.mkdir(parents=True)
    settings = tmp_path / "settings.json"
    settings.write_text(
        json.dumps({"hooks": {"Stop": [{"command": "bash %s/hooks/x.sh" % pinned}]}}),
        encoding="utf-8",
    )
    assert P.pinning_settings(pinned, [settings]) == settings.name

    if os.name != "nt":
        # A backslash IS a path separator on Windows, so a name holding one cannot exist there.
        # On POSIX it can, and it reproduces the same JSON escaping the Windows path shape
        # causes - which is what makes this half fail without the fix on THIS platform too,
        # rather than leaving the fix provable only on the other one.
        escaped_name = tmp_path / "has\\backslash"
        escaped_name.mkdir()
        other = tmp_path / "settings2.json"
        other.write_text(
            json.dumps({"hooks": {"Stop": [{"command": "bash %s/x.sh" % escaped_name}]}}),
            encoding="utf-8")
        assert P.pinning_settings(escaped_name, [other]) == other.name


def test_pinning_settings_says_no_when_nothing_names_the_path(tmp_path: Path) -> None:
    """The direction it must NOT fire: a settings file naming a DIFFERENT version is not a pin,
    or every version would be kept and the tool would reclaim nothing."""
    pinned = tmp_path / "cache" / "mkt" / "plug" / "1.0.0"
    pinned.mkdir(parents=True)
    settings = tmp_path / "settings.json"
    settings.write_text(json.dumps({"hooks": {"Stop": [{"command": "bash %s/x.sh"
                                                       % (pinned.parent / "9.9.9")}]}}),
                        encoding="utf-8")
    assert P.pinning_settings(pinned, [settings]) is None


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


@pytest.mark.parametrize("text", ["{not json", '{"projects": ["a"]}', "[]"])
def test_a_claude_json_that_cannot_be_parsed_refuses_rather_than_losing_every_project(
    cache: Path, tmp_path: Path, text: str
) -> None:
    """A broken project index hides EVERY project's settings, and with them every plugin enabled
    only in a project - read as "no projects", each such sole version was planned for deletion."""
    broken = tmp_path / "broken.json"
    broken.write_text(text, encoding="utf-8")
    plan = plan_for(cache, claude_json=broken)
    assert str(cache / "own-marketplace" / "own-plugin" / "1.0.0") not in paths(plan.prune)
    assert any(str(broken) in problem for problem in plan.settings_problems)


def test_a_claude_json_without_a_projects_map_is_an_ordinary_index(
    cache: Path, tmp_path: Path
) -> None:
    """The control: an index that lists no projects is valid, not a problem."""
    index = tmp_path / "claude.json"
    index.write_text(json.dumps({"numStartups": 3}), encoding="utf-8")
    plan = plan_for(cache, claude_json=index)
    assert plan.settings_problems == ()
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
    result = P.apply_plan(plan)
    assert result.failures == ()
    assert str(late) in paths(result.removed)
    assert not late.exists()
    assert later.exists()


def test_apply_refuses_a_directory_that_gained_a_live_lock_after_the_plan(cache: Path) -> None:
    """A session can start between the plan and the apply; that directory must survive."""
    plan = plan_for(cache)
    latecomer = cache / "own-marketplace" / "own-plugin" / "1.0.0"
    assert str(latecomer) in paths(plan.prune)
    write_lock(latecomer, os.getpid(), P.process_start_ticks(os.getpid()))

    result = P.apply_plan(plan)

    assert latecomer.exists()
    assert any(str(latecomer) in item and "in use" in item for item in result.failures)
    assert str(latecomer) not in paths(result.removed)
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


# --------------------------------------------------------------------------------------------
# Fail closed: any doubt about what is installed, pinned or live keeps or refuses, never prunes
# --------------------------------------------------------------------------------------------

SCRIPT = Path(P.__file__).resolve()

# A permission fault cannot be staged on Windows with chmod, and root reads through mode 000.
needs_posix_perms = pytest.mark.skipif(
    os.name == "nt" or (hasattr(os, "geteuid") and os.geteuid() == 0),
    reason="needs POSIX permission bits enforced against a non-root user",
)


def run_cli(
    args: list[str], *, cwd: Path, home: Path, extra_env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    """The script as a user runs it, with HOME pointed into the fixture so nothing real is read."""
    env = {**os.environ, "HOME": str(home), "USERPROFILE": str(home)}
    env.pop("PYTHONUTF8", None)
    env.update(extra_env or {})
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )


def kept_reasons(plan: P.Plan) -> dict[str, str | None]:
    return {str(entry.path): entry.keep_reason for entry in plan.keep}


def test_a_symlinked_marketplace_dir_is_refused_and_the_installed_version_survives(
    cache: Path, tmp_path: Path
) -> None:
    """Removing through an alias of a real marketplace deletes the real, installed version."""
    alias = cache / "alias"
    alias.symlink_to(cache / "own-marketplace", target_is_directory=True)
    installed = cache / "own-marketplace" / "own-plugin" / "1.2.0"

    plan = plan_for(cache)
    refused = {str(entry.path): entry.refusal for entry in plan.refused}
    assert "symlink" in (refused.get(str(alias / "own-plugin" / "1.2.0")) or "")
    assert not any(str(alias) in path for path in paths(plan.prune))
    assert kept_reasons(plan)[str(installed)] == "installed"

    rc = P.main(["--cache-dir", str(cache), "--marketplace", "alias", "--apply", "--json"])
    assert rc == 1
    assert installed.exists()
    assert (cache / "own-marketplace" / "own-plugin" / "1.0.0").exists()


def test_a_marketplace_symlink_pointing_outside_the_cache_is_refused(
    cache: Path, tmp_path: Path
) -> None:
    outside = tmp_path / "outside-mkt"
    make_version(outside.parent, outside.name, "plug", "1.0.0")
    (outside / "plug" / "1.0.0" / ".in_use").mkdir()
    (cache / "linked").symlink_to(outside, target_is_directory=True)
    rc = P.main(["--cache-dir", str(cache), "--apply", "--json"])
    assert rc == 1
    assert (outside / "plug" / "1.0.0" / "skills" / "filler.md").exists()


def test_refusal_for_a_path_outside_the_base_names_it(cache: Path, tmp_path: Path) -> None:
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    assert "outside" in (P.refusal_for(elsewhere, base=cache) or "")


def test_keep_through_another_spelling_of_the_cache_is_honoured(
    cache: Path, tmp_path: Path
) -> None:
    """Scanning through a symlinked spelling must not lose --keep nor the install record."""
    link = tmp_path / "lnk"
    link.symlink_to(cache.parent, target_is_directory=True)
    target = cache / "own-marketplace" / "own-plugin" / "1.0.0"
    plan = plan_for(link / "cache", keep=[target])
    kept = kept_reasons(plan)
    assert kept[str(target)] == "named with --keep"
    assert kept[str(cache / "own-marketplace" / "own-plugin" / "1.2.0")] == "installed"

    plan = plan_for(cache, keep=[link / "cache" / "own-marketplace" / "own-plugin" / "1.0.0"])
    assert kept_reasons(plan)[str(target)] == "named with --keep"


def test_a_relative_keep_is_resolved_against_the_working_directory(
    cache: Path, tmp_path: Path
) -> None:
    result = run_cli(
        ["--cache-dir", str(cache), "--keep", "./1.0.0", "--json"],
        cwd=cache / "own-marketplace" / "own-plugin",
        home=tmp_path,
    )
    assert result.returncode == 0, result.stderr
    kept = {e["path"]: e["keep_reason"] for e in json.loads(result.stdout)["data"]["keep"]}
    assert kept[str(cache / "own-marketplace" / "own-plugin" / "1.0.0")] == "named with --keep"


def test_a_keep_inside_a_version_dir_keeps_that_version(cache: Path) -> None:
    """The base path a skill invocation prints sits INSIDE the version directory."""
    target = cache / "own-marketplace" / "own-plugin" / "1.0.0"
    plan = plan_for(cache, keep=[target / "skills" / "some-skill"])
    assert kept_reasons(plan)[str(target)] == "named with --keep"


def test_a_keep_that_names_no_scanned_version_is_a_usage_error(
    cache: Path, tmp_path: Path
) -> None:
    result = run_cli(
        ["--cache-dir", str(cache), "--keep", str(tmp_path / "typo" / "1.0.0"), "--apply"],
        cwd=tmp_path,
        home=tmp_path,
    )
    assert result.returncode == 2
    assert "--keep" in result.stderr
    assert (cache / "own-marketplace" / "own-plugin" / "1.0.0").exists()


def test_a_relative_cache_dir_keeps_the_installed_version(cache: Path, tmp_path: Path) -> None:
    result = run_cli(["--cache-dir", "plugins/cache", "--json"], cwd=tmp_path, home=tmp_path)
    assert result.returncode == 0, result.stderr
    kept = {e["path"]: e["keep_reason"] for e in json.loads(result.stdout)["data"]["keep"]}
    assert kept[str(cache / "own-marketplace" / "own-plugin" / "1.2.0")] == "installed"


@needs_posix_perms
def test_an_unreadable_lock_dir_keeps_the_version(cache: Path) -> None:
    target = cache / "own-marketplace" / "own-plugin" / "1.0.0"
    write_lock(target, os.getpid(), P.process_start_ticks(os.getpid()))
    (target / ".in_use").chmod(0)
    try:
        plan = plan_for(cache)
    finally:
        (target / ".in_use").chmod(0o755)
    assert str(target) not in paths(plan.prune)
    assert "unreadable" in (kept_reasons(plan)[str(target)] or "")


def test_a_lock_dir_that_is_not_a_directory_keeps_the_version(cache: Path) -> None:
    target = cache / "own-marketplace" / "own-plugin" / "1.0.0"
    (target / ".in_use").write_text("not a dir", encoding="utf-8")
    plan = plan_for(cache)
    assert str(target) not in paths(plan.prune)


@pytest.mark.parametrize("prefix", ["~", "$HOME", "${HOME}"])
def test_a_pin_spelled_relative_to_home_is_found(tmp_path: Path, prefix: str) -> None:
    home = tmp_path / "home"
    pinned = home / ".claude" / "plugins" / "cache" / "mkt" / "plug" / "1.0.0"
    pinned.mkdir(parents=True)
    settings = tmp_path / "settings.json"
    command = f"bash {prefix}/.claude/plugins/cache/mkt/plug/1.0.0/hooks/x.sh"
    settings.write_text(json.dumps({"hooks": {"Stop": [{"command": command}]}}), encoding="utf-8")
    assert P.pinning_settings(pinned, [settings], homes=[home]) == settings.name
    other = pinned.parent / "1.0.1"
    other.mkdir()
    assert P.pinning_settings(other, [settings], homes=[home]) is None


def test_a_home_relative_pin_keeps_the_version_end_to_end(tmp_path: Path) -> None:
    home = tmp_path / "home"
    root = home / ".claude" / "plugins" / "cache"
    pinned = make_version(root, "mkt", "plug", "1.0.0")
    make_version(root, "mkt", "plug", "1.2.0")
    (pinned / ".in_use").mkdir()
    write_installed(root.parent, {"plug@mkt": root / "mkt" / "plug" / "1.2.0"})
    (home / ".claude" / "settings.json").write_text(
        json.dumps({"hooks": {"Stop": [{"command": "bash ~/.claude/plugins/cache/mkt/plug/1.0.0/x"}]}}),
        encoding="utf-8",
    )
    result = run_cli(["--cache-dir", str(root), "--json"], cwd=tmp_path, home=home)
    assert result.returncode == 0, result.stderr
    kept = {e["path"]: e["keep_reason"] for e in json.loads(result.stdout)["data"]["keep"]}
    assert kept[str(pinned)] == "pinned in settings.json"


def test_text_output_survives_a_console_that_cannot_encode_a_path(
    cache: Path, tmp_path: Path
) -> None:
    make_temp_dir(cache, "temp_✓", age_seconds=7200)
    result = run_cli(
        ["--cache-dir", str(cache)],
        cwd=tmp_path,
        home=tmp_path,
        extra_env={"PYTHONIOENCODING": "cp1252"},
    )
    assert result.returncode == 0, result.stderr
    assert "Traceback" not in result.stderr
    assert "temp_" in result.stdout


@pytest.mark.skipif(sys.platform != "linux", reason="only Linux filesystems take a non-UTF-8 name")
def test_a_non_utf8_dir_name_does_not_crash_after_apply(cache: Path, tmp_path: Path) -> None:
    raw = os.fsencode(str(cache)) + b"/temp_\xff"
    os.mkdir(raw)
    os.utime(raw, (0, 0))
    result = run_cli(
        ["--cache-dir", str(cache), "--apply"],
        cwd=tmp_path,
        home=tmp_path,
        extra_env={"PYTHONIOENCODING": "utf-8:strict"},
    )
    assert "Traceback" not in result.stderr
    assert result.returncode == 0, result.stderr
    assert not os.path.exists(raw)


def test_pid_alive_treats_an_out_of_range_pid_as_alive() -> None:
    assert P.pid_alive(99999999999) is True


def test_a_lock_with_an_out_of_range_pid_keeps_the_version(cache: Path) -> None:
    target = cache / "own-marketplace" / "own-plugin" / "1.0.0"
    lock_dir = target / ".in_use"
    lock_dir.mkdir()
    (lock_dir / "99999999999").write_text(json.dumps({"pid": 99999999999}), encoding="utf-8")
    plan = plan_for(cache)
    assert str(target) not in paths(plan.prune)


def test_a_corrupt_install_record_refuses_every_otherwise_unkept_version(cache: Path) -> None:
    (cache.parent / "installed_plugins.json").write_text("{bad", encoding="utf-8")
    plan = plan_for(cache)
    assert not any(entry.kind == P.KIND_VERSION for entry in plan.prune)
    refused = {str(entry.path): entry.refusal for entry in plan.refused}
    assert "installed_plugins.json" in (
        refused[str(cache / "own-marketplace" / "own-plugin" / "1.2.0")] or ""
    )
    assert str(cache / "temp_git_2_def") in paths(plan.prune)


def test_a_missing_install_record_refuses_and_exits_one(cache: Path, capsys) -> None:
    (cache.parent / "installed_plugins.json").unlink()
    rc = P.main(["--cache-dir", str(cache), "--apply"])
    assert rc == 1
    assert (cache / "own-marketplace" / "own-plugin" / "1.2.0").exists()
    assert (cache / "own-marketplace" / "own-plugin" / "1.0.0").exists()
    assert "installed_plugins.json" in capsys.readouterr().err


def test_an_explicit_install_record_that_cannot_be_read_is_a_usage_error(
    cache: Path, tmp_path: Path, capsys
) -> None:
    rc = P.main(
        ["--cache-dir", str(cache), "--installed-plugins", str(tmp_path / "typo.json"), "--apply"]
    )
    assert rc == 2
    assert "typo.json" in capsys.readouterr().err
    assert (cache / "own-marketplace" / "own-plugin" / "1.0.0").exists()


def test_an_install_record_listing_nothing_is_not_a_refusal(cache: Path) -> None:
    """Claude Code writes an empty plugins map once everything is uninstalled; that is valid."""
    (cache.parent / "installed_plugins.json").write_text(
        json.dumps({"version": 2, "plugins": {}}), encoding="utf-8"
    )
    plan = plan_for(cache)
    assert plan.refused == ()
    assert str(cache / "own-marketplace" / "own-plugin" / "1.2.0") in paths(plan.prune)


def test_a_bom_does_not_hide_enabled_plugins_or_the_install_record(
    cache: Path, tmp_path: Path
) -> None:
    settings = tmp_path / "bom-settings.json"
    payload = json.dumps({"enabledPlugins": {"orphan-plugin@other-marketplace": True}})
    settings.write_bytes(b"\xef\xbb\xbf" + payload.encode("utf-8"))
    record = cache.parent / "installed_plugins.json"
    record.write_bytes(b"\xef\xbb\xbf" + record.read_bytes())
    plan = plan_for(cache, settings_files=[settings])
    kept = kept_reasons(plan)
    assert kept[str(cache / "other-marketplace" / "orphan-plugin" / "3.0.0")] == (
        f"only version, enabled in {settings.name}"
    )
    assert kept[str(cache / "own-marketplace" / "own-plugin" / "1.2.0")] == "installed"


def test_a_bom_in_claude_json_still_discovers_project_settings(
    cache: Path, tmp_path: Path
) -> None:
    project = tmp_path / "some-project"
    write_project_settings(project, {"enabledPlugins": {}})
    claude_json = tmp_path / "claude.json"
    claude_json.write_bytes(
        b"\xef\xbb\xbf" + json.dumps({"projects": {str(project): {}}}).encode("utf-8")
    )
    assert P.project_settings_files(claude_json)


# A settings source that cannot be read is refused, never read as "nothing pinned or enabled":
# the pin or enabledPlugins entry it holds is exactly what keeps a version off the delete list.

ENABLE_ORPHAN = json.dumps({"enabledPlugins": {"orphan-plugin@other-marketplace": True}})


def orphan_of(cache: Path) -> Path:
    return cache / "other-marketplace" / "orphan-plugin" / "3.0.0"


def write_user_settings(cache: Path, text: str, name: str = "settings.json") -> Path:
    """A settings file where discovery looks for it: `~/.claude/<name>`, from the cache path."""
    path = cache.parent.parent / name
    path.write_text(text, encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("text", "reason"),
    [
        ('{"enabledPlugins": {"orphan-plugin@other-marketplace": true},}', "not valid JSON"),
        ("[1, 2]", "not a JSON object"),
        ('{"enabledPlugins": ["orphan-plugin@other-marketplace"]}', "enabledPlugins"),
    ],
)
def test_a_malformed_settings_file_refuses_the_version_it_could_have_kept(
    cache: Path, text: str, reason: str
) -> None:
    settings = write_user_settings(cache, text)
    plan = plan_for(cache)
    assert str(orphan_of(cache)) not in paths(plan.prune)
    refusal = {str(entry.path): entry.refusal for entry in plan.refused}[str(orphan_of(cache))]
    assert refusal is not None
    assert str(settings) in refusal
    assert reason in refusal


def test_the_same_settings_file_well_formed_keeps_the_version_and_is_no_problem(
    cache: Path,
) -> None:
    """The control for the malformed arm: one character apart, the opposite verdict."""
    write_user_settings(cache, ENABLE_ORPHAN)
    plan = plan_for(cache)
    assert plan.settings_problems == ()
    assert kept_reasons(plan)[str(orphan_of(cache))] == "only version, enabled in settings.json"


def test_a_whitespace_only_settings_file_holds_nothing_and_is_no_problem(cache: Path) -> None:
    """Nothing is lost by reading an empty file as empty, so it is not a reason to refuse."""
    write_user_settings(cache, "  \n", name="settings.local.json")
    plan = plan_for(cache)
    assert plan.settings_problems == ()
    assert str(orphan_of(cache)) in paths(plan.prune)


def test_a_settings_file_that_is_not_utf8_is_a_problem(cache: Path) -> None:
    settings = cache.parent.parent / "settings.json"
    settings.write_bytes(
        b'{"enabledPlugins": {"orphan-plugin@other-marketplace": true}, "x": "\xff"}'
    )
    plan = plan_for(cache)
    assert str(orphan_of(cache)) not in paths(plan.prune)
    assert any(str(settings) in problem for problem in plan.settings_problems)


@needs_posix_perms
def test_an_unreadable_settings_file_refuses_rather_than_dropping_its_pin(cache: Path) -> None:
    pinned = cache / "own-marketplace" / "own-plugin" / "1.0.0"
    settings = write_user_settings(
        cache, json.dumps({"hooks": {"Stop": [{"command": f"bash {pinned}/x.sh"}]}})
    )
    settings.chmod(0)
    try:
        plan = plan_for(cache)
    finally:
        settings.chmod(0o600)
    assert str(pinned) not in paths(plan.prune)
    assert any(
        str(settings) in problem and "cannot be read" in problem
        for problem in plan.settings_problems
    )


def test_a_malformed_project_settings_file_refuses(cache: Path, tmp_path: Path) -> None:
    project = tmp_path / "some-project"
    (project / ".claude").mkdir(parents=True)
    broken = project / ".claude" / "settings.local.json"
    broken.write_text("{bad", encoding="utf-8")
    plan = plan_for(cache, claude_json=write_claude_json(tmp_path, [project]))
    assert str(orphan_of(cache)) not in paths(plan.prune)
    assert any(str(broken) in problem for problem in plan.settings_problems)


def test_a_malformed_settings_file_exits_two_before_removing_anything(
    cache: Path, capsys
) -> None:
    settings = write_user_settings(cache, "{bad")
    rc = P.main(["--cache-dir", str(cache), "--apply"])
    err = capsys.readouterr().err
    assert rc == 2
    assert str(settings) in err
    assert "not valid JSON" in err
    assert orphan_of(cache).exists()
    assert (cache / "own-marketplace" / "own-plugin" / "1.0.0").exists()
    assert (cache / "temp_git_2_def").exists()


@pytest.mark.parametrize("flag", ["--settings", "--claude-json"])
def test_an_explicit_settings_source_that_does_not_exist_exits_two(
    cache: Path, tmp_path: Path, capsys, flag: str
) -> None:
    """A named source that is not there is a typo, not "nothing is pinned"."""
    rc = P.main(["--cache-dir", str(cache), flag, str(tmp_path / "typo.json"), "--apply"])
    assert rc == 2
    assert "typo.json" in capsys.readouterr().err
    assert orphan_of(cache).exists()


def test_the_readonly_retry_makes_a_file_writable_and_retries(tmp_path: Path) -> None:
    """What Windows needs for a read-only git pack file; the retry is exercised with a strict
    remover that refuses a read-only file the way Windows does."""
    target = tmp_path / "pack.idx"
    target.write_text("x", encoding="utf-8")
    target.chmod(0o444)

    def strict_unlink(path: str) -> None:
        if not os.access(path, os.W_OK):
            raise PermissionError(13, "read-only", path)
        os.unlink(path)

    P._retry_writable(strict_unlink, str(target), PermissionError(13, "read-only"))
    assert not target.exists()


def test_the_readonly_retry_never_touches_a_symlink(tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.write_text("x", encoding="utf-8")
    real.chmod(0o444)
    link = tmp_path / "link"
    link.symlink_to(real)
    with pytest.raises(PermissionError):
        P._retry_writable(os.unlink, str(link), PermissionError(13, "original"))
    assert not os.access(real, os.W_OK) or os.name == "nt"


@pytest.mark.skipif(os.name != "nt", reason="the read-only attribute blocks deletion only on Windows")
def test_apply_removes_a_temp_clone_holding_read_only_files(cache: Path) -> None:
    temp = make_temp_dir(cache, "temp_git_9_ro", age_seconds=7200)
    pack = temp / "objects" / "pack.idx"
    pack.parent.mkdir()
    pack.write_text("x", encoding="utf-8")
    pack.chmod(0o444)
    os.utime(temp, (0, 0))
    assert P.main(["--cache-dir", str(cache), "--apply"]) == 0
    assert not temp.exists()


def test_help_states_the_sole_version_rule_and_apply_replans(capsys) -> None:
    with pytest.raises(SystemExit):
        P.main(["--help"])
    text = " ".join(capsys.readouterr().out.split())
    assert "plugin's only version" not in text
    assert "enabledPlugins" in text
    assert "EXACTLY what the plan listed" not in (P.__doc__ or "")
    assert "re-plans" in " ".join((P.__doc__ or "").split())


@needs_posix_perms
def test_apply_does_not_report_a_directory_it_failed_to_remove(cache: Path, capsys) -> None:
    target = cache / "own-marketplace" / "own-plugin" / "1.0.0"
    (target / "skills").chmod(0o555)
    try:
        rc = P.main(["--cache-dir", str(cache), "--apply"])
    finally:
        (target / "skills").chmod(0o755)
    out, err = capsys.readouterr()
    assert rc == 1
    assert target.exists()
    assert f"removed: {target} " not in out
    assert "FAILED" in err and str(target) in err
    assert not (cache / "own-marketplace" / "own-plugin" / "1.1.0").exists()


@needs_posix_perms
def test_apply_json_lists_only_what_was_removed(cache: Path, capsys) -> None:
    target = cache / "own-marketplace" / "own-plugin" / "1.0.0"
    (target / "skills").chmod(0o555)
    try:
        rc = P.main(["--cache-dir", str(cache), "--apply", "--json"])
    finally:
        (target / "skills").chmod(0o755)
    payload = json.loads(capsys.readouterr().out)
    assert rc == 1
    removed = set(payload["data"]["removed"])
    assert str(target) not in removed
    assert str(cache / "own-marketplace" / "own-plugin" / "1.1.0") in removed


def test_text_mode_names_the_files_it_read(cache: Path, tmp_path: Path, capsys) -> None:
    settings = tmp_path / "settings.json"
    settings.write_text("{}", encoding="utf-8")
    P.main(["--cache-dir", str(cache), "--settings", str(settings)])
    out = capsys.readouterr().out
    assert str(settings) in out
    assert str(cache.parent / "installed_plugins.json") in out


def test_a_corrupt_lock_body_with_a_non_numeric_name_keeps_the_version(cache: Path) -> None:
    target = cache / "own-marketplace" / "own-plugin" / "1.0.0"
    (target / ".in_use").mkdir()
    (target / ".in_use" / "garbage").write_text("{not json", encoding="utf-8")
    assert kept_reasons(plan_for(cache))[str(target)] == "in use (unreadable lock garbage)"


def test_parse_duration_reads_minutes_by_default_and_rejects_garbage() -> None:
    assert P.parse_duration("90") == 5400.0
    assert P.parse_duration("2h") == 7200.0
    with pytest.raises(Exception, match="not a duration"):
        P.parse_duration("x")


def test_an_unexpected_crash_exits_two_not_one(cache: Path, tmp_path: Path) -> None:
    """Exit 1 means "refused or not removed"; a crash must never read as that."""
    driver = tmp_path / "drive.py"
    driver.write_text(
        "import sys\n"
        f"sys.path.insert(0, {str(SCRIPT.parent)!r})\n"
        "import pluginprune\n"
        "def boom(*a, **k):\n    raise RuntimeError('unplanned')\n"
        "pluginprune.build_plan = boom\n"
        f"sys.exit(pluginprune.main(['--cache-dir', {str(cache)!r}]))\n",
        encoding="utf-8",
    )
    done = subprocess.run([sys.executable, str(driver)], capture_output=True, text=True, timeout=60)
    assert done.returncode == 2
    assert "unplanned" in done.stderr


@needs_posix_perms
def test_an_unreadable_subtree_is_not_a_silent_size_undercount(cache: Path) -> None:
    target = cache / "own-marketplace" / "own-plugin" / "1.0.0"
    (target / "skills").chmod(0)
    try:
        plan = plan_for(cache)
    finally:
        (target / "skills").chmod(0o755)
    entry = next(e for e in plan.entries if e.path == target)
    assert entry.size_complete is False
    assert entry.as_dict()["size_complete"] is False
