"""The floor (the profile's gate and suite, as argv lists) and the per-arm score with void rules.

Void rules (design S4) apply to every arm the same way and a void arm counts as nothing: main
model not opus (and every other reason the stream account gives), no result record, deadline or
token cap, store guard fired, first-message cache read out of line with the other finished arms
(design S5.5, warmth_tolerance). The floor's answer is each command's exit code, nothing else.

Each floor step runs in its own process group (POSIX) with an explicit environment: when a step
ends, timed out or not, every process it left in its group is stopped, and a venv, a uv project
environment, a PYTHONPATH or PYTHONHOME, git config overrides or a git repo the harness itself was
launched from cannot redirect what the workpiece's commands see.
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from _ablib import clear_group, median, signal_group
from abprofile import Profile

__all__ = [
    "CAP_STOP_REASONS",
    "CLEAN_STOP_REASON",
    "ERROR_HELD_OPEN",
    "ERROR_NOT_STARTED",
    "KILL_GRACE_S",
    "MISSING_STOP_REASON",
    "RC_NOT_STARTED",
    "RC_TIMEOUT",
    "STREAM_VOID_STOP_REASON",
    "WARMTH_MIN_PEERS",
    "run_floor",
    "score_arm",
]

# A median of one reading is that reading: the check needs two other arms before it means anything.
WARMTH_MIN_PEERS = 2
# The shell's conventions, so a log reader recognises them: timeout(1) exits 124, a command that
# cannot be executed 126 and one that is not found 127. This floor records both of the last as 127.
RC_TIMEOUT = 124
RC_NOT_STARTED = 127
CLEAN_STOP_REASON = "finished"
CAP_STOP_REASONS = ("deadline", "token_cap")
# abarm writes "void" when the stream account voided the arm mid-run; its reasons travel in
# void_reasons, so this stop reason adds a reason of its own only when they were lost.
STREAM_VOID_STOP_REASON = "void"
# Written when result.json carries no stop reason: abarm records one for every way an arm ENDS,
# so its absence means the run never reached that point.
MISSING_STOP_REASON = "no stop reason recorded (the arm did not end normally: interrupted or crashed)"
# How long a step's leftover process group gets between SIGTERM and SIGKILL: long enough for a
# test runner to flush and remove its temp files, short against any floor timeout.
KILL_GRACE_S = 5.0
ERROR_NOT_STARTED = "could not start"
# The leader exited before the timeout, but something it started kept stdout or stderr open past
# it. The leader's own exit code is recorded; the step still fails, since it hit the timeout.
ERROR_HELD_OPEN = "output held open past the timeout by a process the step started"
# The variables that would make a git command in the workpiece act on ANOTHER repository (the one
# the harness was started from), plus the pathspec modes that change what a pathspec matches.
_REPO_SCOPING_GIT_VARS = frozenset({
    "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR", "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_NAMESPACE", "GIT_CEILING_DIRECTORIES"})
# The launcher's Python environment (its venv, uv project environment, PYTHONPATH and PYTHONHOME:
# a PYTHONPATH pointing at the checkout the harness runs from would make every arm's floor import
# THAT code instead of the arm's) and the config git takes from the environment (git -c,
# GIT_CONFIG_COUNT with its numbered KEY/VALUE pairs, and the files named by GIT_CONFIG_GLOBAL and
# GIT_CONFIG_SYSTEM). Everything else, GIT_SSH_COMMAND, GIT_CONFIG_NOSYSTEM and PYTHONUTF8
# included, passes through unchanged.
_LAUNCHER_VARS = frozenset({
    "VIRTUAL_ENV", "UV_PROJECT_ENVIRONMENT", "PYTHONPATH", "PYTHONHOME",
    "GIT_CONFIG_PARAMETERS", "GIT_CONFIG_COUNT", "GIT_CONFIG_GLOBAL", "GIT_CONFIG_SYSTEM"})
_LAUNCHER_VAR_PREFIXES = ("GIT_CONFIG_KEY_", "GIT_CONFIG_VALUE_")


@dataclass(frozen=True)
class _Limits:
    """How long a step may run, and how long its leftover group gets between SIGTERM and SIGKILL."""

    timeout_s: int
    kill_grace_s: float


def _partial_output(exc: subprocess.TimeoutExpired) -> str:
    """Whatever the command printed before it was killed; bytes when the platform gives bytes."""
    parts = []
    for chunk in (exc.stdout, exc.stderr):
        if isinstance(chunk, bytes):
            chunk = chunk.decode("utf-8", errors="replace")
        if chunk:
            parts.append(chunk)
    return "".join(parts)


def _is_leaked(name: str) -> bool:
    if name in _LAUNCHER_VARS or name in _REPO_SCOPING_GIT_VARS or name.startswith(_LAUNCHER_VAR_PREFIXES):
        return True
    return name.startswith("GIT_") and name.endswith("_PATHSPECS")


def _same_dir(entry: str) -> str:
    return os.path.normcase(os.path.normpath(entry))


def _without_venv_bin(path: str, venv: str) -> str:
    """PATH minus the venv's bin dir (Scripts on Windows); every other entry stays, in order."""
    drop = _same_dir(os.path.join(venv, "Scripts" if sys.platform == "win32" else "bin"))
    # An empty entry means the cwd to a shell; it is not the venv's, so it is kept as it is.
    return os.pathsep.join(e for e in path.split(os.pathsep) if not e or _same_dir(e) != drop)


def _floor_env() -> dict[str, str]:
    """os.environ minus the launcher's Python environment (venv variable and PATH entry, PYTHONPATH,
    PYTHONHOME), its git config overrides and the repo-scoping git variables."""
    env = {k: v for k, v in os.environ.items() if not _is_leaked(k)}
    venv = os.environ.get("VIRTUAL_ENV")
    if venv and "PATH" in env:
        env["PATH"] = _without_venv_bin(env["PATH"], venv)
    return env


def _reap(proc: subprocess.Popen[str], grace: float) -> str:
    """Collect everything the stopped step printed; a process that left its group cannot hang us."""
    try:
        out, err = proc.communicate(timeout=grace)
    except subprocess.TimeoutExpired as exc:
        # Something started its own session and kept the pipes: stop reading and reap the step.
        for pipe in (proc.stdout, proc.stderr):
            if pipe is not None:
                pipe.close()
        proc.wait()
        return _partial_output(exc) + "\na process outside the step's group kept its output open\n"
    return (out or "") + (err or "")


def _stop_tree(proc: subprocess.Popen[str], grace: float) -> str:
    """Stop a step that hit its timeout and the members holding its pipes; return what it printed.

    A member that ignores SIGTERM and holds no pipe outlives this; clear_group, which runs after
    every step, is what removes it.
    """
    if sys.platform == "win32":
        proc.kill()  # no process groups to signal; the direct child is what can be stopped
        return _reap(proc, grace)
    signal_group(proc.pid, signal.SIGTERM)
    try:
        out, err = proc.communicate(timeout=grace)
    except subprocess.TimeoutExpired:
        signal_group(proc.pid, signal.SIGKILL)
        return _reap(proc, grace)
    return (out or "") + (err or "")


def _start(argv: list[str], tree: Path) -> subprocess.Popen[str]:
    return subprocess.Popen(argv, cwd=str(tree), env=_floor_env(), stdout=subprocess.PIPE,  # nosec B603
                            stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace",
                            start_new_session=sys.platform != "win32")


def _finish(proc: subprocess.Popen[str], argv: list[str], limits: _Limits) -> tuple[int, str, str | None]:
    try:
        out, err = proc.communicate(timeout=limits.timeout_s)
    except subprocess.TimeoutExpired:
        # Read before the tree is stopped: afterwards every leader has an exit code, the signal's.
        leader_rc = proc.poll()
        error = f"timed out after {limits.timeout_s} s" if leader_rc is None else ERROR_HELD_OPEN
        out = _stop_tree(proc, limits.kill_grace_s) + f"\n{argv[0]} {error}\n"
        return (RC_TIMEOUT if leader_rc is None else leader_rc), out, error
    return proc.returncode, out + err, None


def _execute(argv: list[str], tree: Path, limits: _Limits) -> tuple[int, str, str | None]:
    """(exit code, combined output, error); error names why the command did not run to its end."""
    try:
        proc = _start(argv, tree)
    except OSError as exc:
        # FileNotFoundError and PermissionError: the command never ran, so the floor cannot pass.
        return RC_NOT_STARTED, f"{argv[0]} could not start in {tree}: {exc}\n", ERROR_NOT_STARTED
    try:
        return _finish(proc, argv, limits)
    finally:
        if sys.platform != "win32":
            # A daemon with its stdio on /dev/null never shows in the pipes: only the group finds it.
            clear_group(proc.pid, limits.kill_grace_s)


def _step(name: str, argv: list[str], tree: Path, *, limits: _Limits, log: Path) -> dict[str, Any]:
    t0 = time.monotonic()
    rc, out, error = _execute(argv, tree, limits)
    log.write_text(out, encoding="utf-8")
    return {"name": name, "argv": argv, "rc": rc, "error": error, "wall_s": round(time.monotonic() - t0, 1),
            "log": str(log)}


def _step_passed(step: dict[str, Any]) -> bool:
    return step["rc"] == 0 and step["error"] is None


def run_floor(tree: Path, profile: Profile, log_dir: Path, *, kill_grace_s: float = KILL_GRACE_S) -> dict[str, Any]:
    """Run the gate, then the suite (when set); the suite is skipped once the gate failed.

    Args:
        tree: the checkout the commands run in (their cwd).
        profile: the sealed profile; its floor names the argv lists and the per-step timeout.
        log_dir: where floor-gate.log and floor-suite.log are written (created when missing).
        kill_grace_s: how long a step's leftover process group gets between SIGTERM and SIGKILL.

    Returns:
        {"passed": every step exited 0 and ran to its end, "steps": [{"name", "argv", "rc", "error",
        "wall_s", "log"}]}. A step that could not start exits RC_NOT_STARTED with error "could not
        start"; one that timed out exits RC_TIMEOUT with error "timed out after N s". A step whose
        leader exited before the timeout while a process it started held its output open past it
        keeps the leader's exit code, with error ERROR_HELD_OPEN, and fails. error is None for a
        step that ran to its end, whatever its exit code: a gate that exits 124 itself did not time
        out. After every step its process group is stopped (SIGTERM, kill_grace_s, SIGKILL), so
        nothing a step started outlives it. The limit: a grandchild that leaves the group with
        setsid() is not killed (process groups cannot reach it; only a cgroup could), but the floor
        does not hang on it, since its pipes are closed after the grace and the step is reaped.
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    limits = _Limits(timeout_s=profile.floor.timeout_s, kill_grace_s=kill_grace_s)
    steps = [_step("gate", list(profile.floor.gate), tree, limits=limits, log=log_dir / "floor-gate.log")]
    suite = profile.suite_argv()
    if suite is not None and _step_passed(steps[0]):
        steps.append(_step("suite", suite, tree, limits=limits, log=log_dir / "floor-suite.log"))
    return {"passed": all(_step_passed(s) for s in steps), "steps": steps}


def _result_reason(res: dict[str, Any]) -> list[str]:
    if res.get("has_result"):
        # Unparsable lines beside a result record lost nothing the score reads: not a void.
        return []
    skipped = int(res.get("skipped_lines") or 0)
    torn = f" ({skipped} unparsable stream line(s): the session was likely cut off mid-write)" if skipped else ""
    return ["no result record in the stream" + torn]


def _stop_reason(res: dict[str, Any], stream_reasons: list[str]) -> list[str]:
    stop = res.get("stop_reason")
    if stop == CLEAN_STOP_REASON:
        return []
    if stop is None:
        return [MISSING_STOP_REASON]
    if stop in CAP_STOP_REASONS:
        return [f"ended by {stop}"]
    if stop == STREAM_VOID_STOP_REASON:
        return [] if stream_reasons else ["stopped as void with no reason recorded"]
    return [f"stop reason {stop!r} is not one an arm ends with (finished, void, deadline, token_cap)"]


def _cache_read(record: dict[str, Any]) -> int | None:
    """The token count, from an int or an integral float (a JSON writer may emit 11000.0)."""
    value = record.get("first_cache_read")
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return int(value) if isinstance(value, float) and value.is_integer() else None


def _warmth(res: dict[str, Any], tolerance: float, peers: list[dict[str, Any]]) -> tuple[bool, list[str]]:
    """(whether the check ran, its void reason if any)."""
    mine = _cache_read(res)
    reads = [r for r in (_cache_read(p) for p in peers) if r is not None]
    if mine is None or len(reads) < WARMTH_MIN_PEERS:
        return False, []
    m = median([float(r) for r in reads])
    # Against a zero median a relative difference is undefined; any non-zero read is out of line.
    out_of_line = abs(mine - m) / m > tolerance if m > 0 else mine != 0
    if not out_of_line:
        return True, []
    return True, [f"first-message cache read {mine} is off the peers' median {m:.0f} by more than {tolerance}"]


def _void_reasons(res: dict[str, Any], warmth_reasons: list[str]) -> list[str]:
    stream_reasons = [str(r) for r in res.get("void_reasons") or []]
    guard = [str(g) for g in res.get("guard_changes") or []]
    return (stream_reasons + _result_reason(res) + _stop_reason(res, stream_reasons)
            + (["store guard fired: " + "; ".join(guard)] if guard else []) + warmth_reasons)


def _floor_steps(floor: dict[str, Any]) -> list[dict[str, Any]]:
    return [s for s in floor.get("steps") or [] if isinstance(s, dict)]


def _floor_error(steps: list[dict[str, Any]]) -> str | None:
    """'<step>: <why> (rc N)' for the first step that did not run to its end, else None."""
    for step in steps:
        if step.get("error"):
            return f"{step.get('name')}: {step['error']} (rc {step.get('rc')})"
    return None


def _score_record(res: dict[str, Any], arm_dir: Path, profile: Profile,
                  peers: list[dict[str, Any]]) -> dict[str, Any]:
    floor = res.get("floor") or {}
    steps = _floor_steps(floor)
    checked, warmth_reasons = _warmth(res, profile.run.warmth_tolerance, peers)
    return {"arm": res.get("arm", arm_dir.name), "cost_usd": res.get("total_cost_usd"),
            "per_model": res.get("per_model") or {}, "main_new_tokens": res.get("main_new_tokens"),
            "first_cache_read": res.get("first_cache_read"), "floor_passed": bool(floor.get("passed")),
            "floor_error": _floor_error(steps),
            "floor_steps": [{"name": s.get("name"), "rc": s.get("rc")} for s in steps],
            "bundle_commits": int(res.get("bundle_commits") or 0), "wall_s": res.get("wall_s"),
            "warmth_checked": checked, "result_subtype": res.get("result_subtype"),
            "void": _void_reasons(res, warmth_reasons)}


def score_arm(arm_dir: Path, profile: Profile, peers: list[dict[str, Any]]) -> dict[str, Any]:
    """Read arm_dir/result.json, apply the void rules against peers, write and return scores.json.

    Args:
        arm_dir: the arm's directory holding result.json (dispatch summary, guard_changes, floor,
            bundle_commits).
        profile: the sealed profile (its run.warmth_tolerance).
        peers: the OTHER finished arms' result.json dicts; fewer than WARMTH_MIN_PEERS with a
            first-message cache read skip the warmth check.

    Returns:
        The score: arm, cost_usd, per_model, main_new_tokens (every model's new input),
        first_cache_read, floor_passed, floor_error (None when every floor step ran to its end, else
        "<step>: could not start (rc 127)", "<step>: timed out after N s (rc 124)" or "<step>:
        output held open past the timeout by a process the step started (rc <the leader's>)" for
        the first such step), floor_steps ([{"name", "rc"}] per step attempted, in order), bundle_commits, wall_s,
        warmth_checked (False when the arm or fewer than WARMTH_MIN_PEERS peers had a reading),
        result_subtype (the result record's subtype, informational: it never voids) and void (every
        reason, the stream account's own ones first and unchanged; empty means the arm counts).

    Raises:
        FileNotFoundError: arm_dir has no result.json.
        json.JSONDecodeError: result.json is not JSON.
    """
    res = json.loads((arm_dir / "result.json").read_text(encoding="utf-8"))
    score = _score_record(res, arm_dir, profile, peers)
    (arm_dir / "scores.json").write_text(json.dumps(score, indent=1, sort_keys=True), encoding="utf-8")
    return score
