"""Tests for tmp_prune.py (the dead temp-dir pruner) and tmp-prune-hook.py (its throttled trigger).

Every test builds a real temp tree under tmp_path and hands the pruner its paths through
PruneConfig, so nothing here touches the machine's own temp dir, session registry or transcripts.
"""

import json
import mmap
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

import pytest

import process_liveness
import tmp_prune
import tmp_prune_hook

DAY = 86400.0
NOW = time.time()
ON_LINUX = sys.platform.startswith("linux")


# ---- fixtures -------------------------------------------------------------------------------


def age_tree(path: Path, days: float) -> None:
    """Set the mtime of `path` and everything under it to `days` ago (children first)."""
    stamp = NOW - days * DAY
    # Windows has no utime(follow_symlinks=False); the fixtures there hold no symlinks to protect.
    no_follow = {"follow_symlinks": False} if os.utime in os.supports_follow_symlinks else {}
    for root, dirs, files in os.walk(path, topdown=False):
        for name in files + dirs:
            os.utime(os.path.join(root, name), (stamp, stamp), **no_follow)
    os.utime(path, (stamp, stamp))


def make_dir(path: Path, *, days: float, files: int = 2) -> Path:
    path.mkdir(parents=True)
    for i in range(files):
        (path / f"f{i}.txt").write_text("x", encoding="utf-8")
    age_tree(path, days)
    return path


class Machine:
    """A fake temp dir, session registry and transcript store, wired into one PruneConfig."""

    def __init__(self, root: Path) -> None:
        self.base = root / "tmp"
        self.base.mkdir()
        self.projects = root / "projects"
        self.projects.mkdir()
        self.sessions = root / "sessions"
        self.sessions.mkdir()
        self.state = root / "state"
        self.uid = os.getuid() if hasattr(os, "getuid") else None
        self.scratch_name = tmp_prune.scratch_dir_names(self.uid)[0]

    def config(self, **overrides: object) -> tmp_prune.PruneConfig:
        values: dict[str, object] = {
            "scratch_bases": (self.base,),
            "oneoff_base": self.base,
            "projects_dir": self.projects,
            "sessions_dir": self.sessions,
            "uid": self.uid,
            "now": NOW,
        }
        values.update(overrides)
        return tmp_prune.PruneConfig(**values)  # type: ignore[arg-type]

    def scratch(self, *, days: float, session: str | None = None, project: str = "-proj") -> Path:
        sid = session or str(uuid.uuid4())
        return make_dir(self.base / self.scratch_name / project / sid, days=days)

    def transcript(self, scratch: Path, *, days: float) -> Path:
        path = self.projects / scratch.parent.name / (scratch.name + ".jsonl")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}\n", encoding="utf-8")
        stamp = NOW - days * DAY
        os.utime(path, (stamp, stamp))
        return path

    def register(self, session_id: str, *, pid: int, proc_start: str | None) -> None:
        record = {"pid": pid, "sessionId": session_id, "procStart": proc_start}
        (self.sessions / f"{pid}.json").write_text(json.dumps(record), encoding="utf-8")


@pytest.fixture
def machine(tmp_path: Path) -> Machine:
    return Machine(tmp_path)


def reaped_pid() -> int:
    proc = subprocess.Popen([sys.executable, "-c", "pass"])
    proc.wait()
    return proc.pid


def decisions(cfg: tmp_prune.PruneConfig) -> dict[Path, tmp_prune.Decision]:
    return {d.path: d for d in tmp_prune.plan(cfg)}


# ---- process_liveness -----------------------------------------------------------------------


def test_a_registered_live_session_is_live(machine: Machine) -> None:
    sid = str(uuid.uuid4())
    machine.register(sid, pid=os.getpid(), proc_start=process_liveness.process_start_ticks(os.getpid()))
    live = process_liveness.live_session_ids(machine.sessions)
    assert sid in live.ids
    assert live.uncertain is False


def test_a_registered_session_whose_process_is_gone_is_not_live(machine: Machine) -> None:
    sid = str(uuid.uuid4())
    machine.register(sid, pid=reaped_pid(), proc_start=None)
    assert sid not in process_liveness.live_session_ids(machine.sessions).ids


@pytest.mark.skipif(not ON_LINUX, reason="process start ticks are read from /proc")
def test_a_reused_pid_with_a_different_start_time_is_not_that_session(machine: Machine) -> None:
    sid = str(uuid.uuid4())
    machine.register(sid, pid=os.getpid(), proc_start="1")
    assert sid not in process_liveness.live_session_ids(machine.sessions).ids


def test_an_unparseable_registry_entry_makes_the_answer_uncertain(machine: Machine) -> None:
    (machine.sessions / "4242.json").write_text("{not json", encoding="utf-8")
    assert process_liveness.live_session_ids(machine.sessions).uncertain is True


def test_a_missing_registry_dir_is_certain_and_empty(tmp_path: Path) -> None:
    live = process_liveness.live_session_ids(tmp_path / "absent")
    assert live.ids == frozenset()
    assert live.uncertain is False


def test_registry_key_files_beside_the_json_are_ignored(machine: Machine) -> None:
    (machine.sessions / "4242.abcdef.key").write_text("secret", encoding="utf-8")
    assert process_liveness.live_session_ids(machine.sessions).uncertain is False


# ---- where the scratch lives ----------------------------------------------------------------


def test_the_override_names_the_scratch_base() -> None:
    bases = tmp_prune.scratch_bases({"CLAUDE_CODE_TMPDIR": "/x/override"}, "linux", "/sys-tmp")
    assert bases[0] == Path("/x/override")


def test_an_override_still_scans_the_system_default_for_long_path_fallbacks() -> None:
    bases = tmp_prune.scratch_bases({"CLAUDE_CODE_TMPDIR": "/x/override"}, "linux", "/sys-tmp")
    assert Path("/sys-tmp") in bases


def test_macos_scratch_defaults_to_slash_tmp_not_the_per_user_tmpdir() -> None:
    assert tmp_prune.scratch_bases({}, "darwin", "/var/folders/ab/T") == (Path("/tmp"),)


def test_linux_scratch_defaults_to_the_system_temp_dir() -> None:
    assert tmp_prune.scratch_bases({}, "linux", "/sys-tmp") == (Path("/sys-tmp"),)


def test_posix_scratch_dir_is_named_after_the_uid() -> None:
    assert tmp_prune.scratch_dir_names(1000) == ("claude-1000",)


def test_windows_accepts_both_the_binary_and_the_documented_name() -> None:
    assert set(tmp_prune.scratch_dir_names(None)) == {"claude-0", "claude"}


# ---- scratch: what is dead ------------------------------------------------------------------


def test_a_day_old_scratch_dir_with_no_owner_is_pruned(machine: Machine) -> None:
    dead = machine.scratch(days=2)
    assert decisions(machine.config())[dead].prune is True


def test_a_scratch_dir_touched_within_a_day_is_kept(machine: Machine) -> None:
    fresh = machine.scratch(days=0.5)
    decision = decisions(machine.config())[fresh]
    assert decision.prune is False
    assert "changed" in decision.reason


def test_a_live_sessions_scratch_dir_is_kept_however_old(machine: Machine) -> None:
    sid = str(uuid.uuid4())
    old = machine.scratch(days=30, session=sid)
    machine.register(sid, pid=os.getpid(), proc_start=process_liveness.process_start_ticks(os.getpid()))
    decision = decisions(machine.config())[old]
    assert decision.prune is False
    assert "live session" in decision.reason


def test_the_calling_sessions_own_dir_is_kept(machine: Machine) -> None:
    sid = str(uuid.uuid4())
    old = machine.scratch(days=30, session=sid)
    assert decisions(machine.config(keep_sessions=frozenset({sid})))[old].prune is False


def test_a_scratch_dir_whose_transcript_moved_recently_is_kept(machine: Machine) -> None:
    old = machine.scratch(days=5)
    machine.transcript(old, days=0.2)
    assert decisions(machine.config())[old].prune is False


def test_an_unreadable_registry_keeps_every_scratch_dir(machine: Machine) -> None:
    old = machine.scratch(days=30)
    (machine.sessions / "4242.json").write_text("{not json", encoding="utf-8")
    decision = decisions(machine.config())[old]
    assert decision.prune is False
    assert "registry" in decision.reason


def test_a_dir_not_named_like_a_session_is_never_a_scratch_candidate(machine: Machine) -> None:
    odd = make_dir(machine.base / machine.scratch_name / "-proj" / "plugin-tool-staging", days=30)
    assert odd not in decisions(machine.config())


@pytest.mark.skipif(not hasattr(__import__("socket"), "AF_UNIX"), reason="needs unix sockets")
def test_a_dir_holding_a_socket_is_kept(machine: Machine, monkeypatch: pytest.MonkeyPatch) -> None:
    import socket

    old = machine.scratch(days=5)
    # A relative bind: the absolute tmp_path is longer than a unix socket path may be.
    monkeypatch.chdir(old)
    with socket.socket(socket.AF_UNIX) as sock:
        sock.bind("s")
        age_tree(old, 5)
        decision = decisions(machine.config())[old]
    assert decision.prune is False
    assert "socket" in decision.reason


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="needs named pipes")
def test_a_dir_holding_a_fifo_is_kept(machine: Machine) -> None:
    old = machine.scratch(days=5)
    os.mkfifo(old / "pipe")
    age_tree(old, 5)
    assert decisions(machine.config())[old].prune is False


# ---- one-offs -------------------------------------------------------------------------------


def test_a_week_old_unheld_oneoff_is_pruned_where_holders_are_checkable(machine: Machine) -> None:
    if tmp_prune.HolderIndex.build(machine.config()).method == "none":
        pytest.skip("no holder check on this platform")
    old = make_dir(machine.base / "mktemp.abc", days=8)
    assert decisions(machine.config())[old].prune is True


def test_a_oneoff_younger_than_a_week_is_kept(machine: Machine) -> None:
    young = make_dir(machine.base / "mktemp.abc", days=3)
    assert decisions(machine.config())[young].prune is False


def test_pytest_basetemp_is_left_to_pytest(machine: Machine) -> None:
    owned = make_dir(machine.base / "pytest-of-someone", days=30)
    assert owned not in decisions(machine.config())


def test_the_scratch_root_is_not_itself_a_oneoff(machine: Machine) -> None:
    machine.scratch(days=30)
    assert (machine.base / machine.scratch_name) not in decisions(machine.config())


def test_a_symlinked_dir_is_never_followed(machine: Machine, tmp_path: Path) -> None:
    target = make_dir(tmp_path / "elsewhere", days=30)
    link = machine.base / "link"
    link.symlink_to(target, target_is_directory=True)
    assert link not in decisions(machine.config())


@pytest.mark.skipif(not ON_LINUX, reason="the /proc holder index is Linux-only")
def test_a_oneoff_with_a_file_held_open_is_kept(machine: Machine) -> None:
    old = make_dir(machine.base / "held", days=8)
    with open(old / "f0.txt", encoding="utf-8"):
        age_tree(old, 8)
        decision = decisions(machine.config())[old]
    assert decision.prune is False
    assert "held" in decision.reason


@pytest.mark.skipif(not ON_LINUX, reason="the /proc holder index is Linux-only")
@pytest.mark.skipif(sys.version_info < (3, 13), reason="mmap(trackfd=False) arrived in 3.13")
def test_a_oneoff_with_a_file_only_mmapped_is_kept(machine: Machine) -> None:
    old = make_dir(machine.base / "mapped", days=8)
    # trackfd=False keeps no file descriptor behind the mapping, so only /proc/<pid>/maps shows it.
    with open(old / "f0.txt", "r+b") as handle:
        mapping = mmap.mmap(handle.fileno(), 0, trackfd=False)
    try:
        age_tree(old, 8)
        assert decisions(machine.config())[old].prune is False
    finally:
        mapping.close()


# ---- applying -------------------------------------------------------------------------------


def test_apply_deletes_what_the_plan_prunes_and_keeps_the_rest(machine: Machine) -> None:
    dead = machine.scratch(days=2)
    fresh = machine.scratch(days=0.1)
    result = tmp_prune.apply(machine.config(), tmp_prune.plan(machine.config()))
    assert not dead.exists()
    assert fresh.exists()
    assert result.removed_inodes >= 3


def test_apply_rechecks_a_dir_written_after_the_plan(machine: Machine) -> None:
    dead = machine.scratch(days=2)
    decided = tmp_prune.plan(machine.config())
    (dead / "late.txt").write_text("written after planning", encoding="utf-8")
    tmp_prune.apply(machine.config(), decided)
    assert dead.exists()


@pytest.mark.skipif(os.name == "nt", reason="POSIX permission bits")
def test_apply_removes_a_dir_holding_an_unreadable_subdir(machine: Machine) -> None:
    dead = machine.scratch(days=2)
    locked = dead / "locked"
    locked.mkdir()
    (locked / "x").write_text("x", encoding="utf-8")
    age_tree(dead, 2)
    locked.chmod(0)
    try:
        tmp_prune.apply(machine.config(), tmp_prune.plan(machine.config()))
    finally:
        if locked.exists():
            locked.chmod(0o700)
    assert not dead.exists()


def test_apply_removes_a_project_dir_left_empty_and_old(machine: Machine) -> None:
    dead = machine.scratch(days=2, project="-gone")
    project = dead.parent
    age_tree(project, 2)
    tmp_prune.apply(machine.config(), tmp_prune.plan(machine.config()))
    assert not project.exists()


def test_a_failed_non_removal_call_is_recorded_not_raised(tmp_path: Path) -> None:
    # rmtree reports failures of os.open(path, flags, dir_fd=...) too; re-calling that with one
    # argument raised TypeError, which escaped rmtree and aborted the whole run.
    errors: list[str] = []
    tmp_prune._retry_writable(os.open, str(tmp_path), errors)
    assert errors


@pytest.mark.skipif(os.name != "nt", reason="the rename probe is how Windows sees a held file")
def test_windows_leaves_a_oneoff_whose_file_is_open(machine: Machine) -> None:
    old = make_dir(machine.base / "held", days=8)
    with open(old / "f0.txt", encoding="utf-8"):
        age_tree(old, 8)
        result = tmp_prune.apply(machine.config(), tmp_prune.plan(machine.config()))
    assert old.exists()
    assert result.removed_dirs == 0


def test_a_dry_run_deletes_nothing(machine: Machine) -> None:
    dead = machine.scratch(days=2)
    result = tmp_prune.apply(machine.config(), tmp_prune.plan(machine.config()), dry_run=True)
    assert dead.exists()
    assert result.removed_dirs == 1


# ---- the throttle ---------------------------------------------------------------------------


def test_the_first_claim_wins(tmp_path: Path) -> None:
    assert tmp_prune.claim_slot(tmp_path, now=NOW, interval=3600) is True


def test_a_second_claim_within_the_interval_loses(tmp_path: Path) -> None:
    tmp_prune.claim_slot(tmp_path, now=NOW, interval=3600)
    tmp_prune.release_slot(tmp_path)
    assert tmp_prune.claim_slot(tmp_path, now=NOW + 60, interval=3600) is False


def test_a_claim_after_the_interval_wins(tmp_path: Path) -> None:
    tmp_prune.claim_slot(tmp_path, now=NOW, interval=3600)
    tmp_prune.release_slot(tmp_path)
    assert tmp_prune.claim_slot(tmp_path, now=NOW + 3601, interval=3600) is True


def test_a_running_prune_blocks_a_claim_even_past_the_interval(tmp_path: Path) -> None:
    tmp_prune.claim_slot(tmp_path, now=NOW, interval=3600)
    assert tmp_prune.claim_slot(tmp_path, now=NOW + 3601, interval=3600) is False


def test_a_lock_left_by_a_crashed_prune_expires(tmp_path: Path) -> None:
    tmp_prune.claim_slot(tmp_path, now=NOW, interval=3600)
    assert tmp_prune.claim_slot(tmp_path, now=NOW + 3 * 3600, interval=3600) is True


# ---- the CLI, end to end --------------------------------------------------------------------


def run_cli(machine: Machine, *extra: str) -> tuple[int, dict[str, object]]:
    script = Path(tmp_prune.__file__)
    argv = [
        sys.executable, str(script), "--json",
        "--scratch-base", str(machine.base), "--oneoff-base", str(machine.base),
        "--projects-dir", str(machine.projects), "--sessions-dir", str(machine.sessions),
        "--state-dir", str(machine.state), *extra,
    ]
    proc = subprocess.run(argv, capture_output=True, encoding="utf-8", errors="replace", check=False)
    return proc.returncode, json.loads(proc.stdout)


def test_the_cli_dry_runs_by_default(machine: Machine) -> None:
    dead = machine.scratch(days=2)
    rc, envelope = run_cli(machine)
    assert rc == 0
    assert envelope["ok"] is True
    assert dead.exists()
    assert envelope["data"]["removed_dirs"] == 1  # type: ignore[index]


def test_the_cli_names_each_dir_it_would_remove(machine: Machine) -> None:
    dead = machine.scratch(days=2)
    _rc, envelope = run_cli(machine)
    listed = envelope["data"]["removed"]  # type: ignore[index]
    assert [entry["path"] for entry in listed] == [str(dead)]  # type: ignore[index]


def test_the_run_log_carries_counts_not_paths(machine: Machine) -> None:
    machine.scratch(days=2)
    run_cli(machine)
    record = json.loads((machine.state / tmp_prune.LOG_NAME).read_text(encoding="utf-8").splitlines()[-1])
    assert "removed" not in record


def test_the_cli_reports_how_much_it_examined(machine: Machine) -> None:
    machine.scratch(days=2)
    machine.scratch(days=0.1)
    _rc, envelope = run_cli(machine)
    assert envelope["data"]["examined_dirs"] == 2  # type: ignore[index]


def test_the_cli_applies_and_logs_the_run(machine: Machine) -> None:
    dead = machine.scratch(days=2)
    rc, _envelope = run_cli(machine, "--apply")
    assert rc == 0
    assert not dead.exists()
    log = (machine.state / tmp_prune.LOG_NAME).read_text(encoding="utf-8").splitlines()
    assert json.loads(log[-1])["removed_dirs"] == 1


def test_the_cli_releases_the_slot_it_was_handed(machine: Machine) -> None:
    tmp_prune.claim_slot(machine.state, now=NOW, interval=3600)
    run_cli(machine, "--release-slot")
    assert not (machine.state / tmp_prune.LOCK_NAME).exists()


# ---- the hook -------------------------------------------------------------------------------


class Spawned:
    def __init__(self) -> None:
        self.argv: list[str] | None = None

    def __call__(self, argv: list[str]) -> None:
        self.argv = argv


def run_hook(tmp_path: Path, *, mode: str, event: str = "Stop") -> Spawned:
    spawned = Spawned()
    payload = json.dumps({"hook_event_name": event, "session_id": "abc-123"})
    tmp_prune_hook.run(payload, mode=mode, state_dir=tmp_path, now=NOW, spawn=spawned)
    return spawned


def test_the_hook_starts_a_detached_prune_when_the_slot_is_free(tmp_path: Path) -> None:
    spawned = run_hook(tmp_path, mode="on")
    assert spawned.argv is not None
    assert "--apply" in spawned.argv
    assert "--release-slot" in spawned.argv
    assert spawned.argv[spawned.argv.index("--keep-session") + 1] == "abc-123"


def test_the_hook_dry_run_mode_never_passes_apply(tmp_path: Path) -> None:
    spawned = run_hook(tmp_path, mode="dry-run")
    assert spawned.argv is not None
    assert "--apply" not in spawned.argv


def test_the_hook_does_nothing_when_off(tmp_path: Path) -> None:
    assert run_hook(tmp_path, mode="off").argv is None


def test_the_hook_starts_nothing_within_the_interval(tmp_path: Path) -> None:
    run_hook(tmp_path, mode="on")
    tmp_prune.release_slot(tmp_path)
    assert run_hook(tmp_path, mode="on", event="SessionStart").argv is None


def test_the_hook_survives_garbage_on_stdin(tmp_path: Path) -> None:
    spawned = Spawned()
    tmp_prune_hook.run("not json", mode="on", state_dir=tmp_path, now=NOW, spawn=spawned)
    assert spawned.argv is not None
    assert "--keep-session" not in spawned.argv
