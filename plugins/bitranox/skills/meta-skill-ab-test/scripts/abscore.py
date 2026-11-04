"""The floor (the profile's gate and suite, as argv lists) and the per-arm score with void rules.

Void rules (design S4) apply to every arm the same way and a void arm counts as nothing: main
model not opus (and every other reason the stream account gives), no result record, deadline or
token cap, store guard fired, first-message cache read out of line with the other finished arms
(design S5.5, warmth_tolerance). The floor's answer is each command's exit code, nothing else.
"""
from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any

from _ablib import median, run
from abprofile import Profile

__all__ = [
    "CAP_STOP_REASONS",
    "CLEAN_STOP_REASON",
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


def _partial_output(exc: subprocess.TimeoutExpired) -> str:
    """Whatever the command printed before it was killed; bytes when the platform gives bytes."""
    parts = []
    for chunk in (exc.stdout, exc.stderr):
        if isinstance(chunk, bytes):
            chunk = chunk.decode("utf-8", errors="replace")
        if chunk:
            parts.append(chunk)
    return "".join(parts)


def _execute(argv: list[str], tree: Path, timeout: int) -> tuple[int, str]:
    """(exit code, combined output); a command that cannot start or times out is a failed exit."""
    try:
        proc = run(argv, cwd=tree, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        return RC_TIMEOUT, _partial_output(exc) + f"\n{argv[0]} timed out after {timeout} s\n"
    except OSError as exc:
        # FileNotFoundError and PermissionError: the command never ran, so the floor cannot pass.
        return RC_NOT_STARTED, f"{argv[0]} could not start in {tree}: {exc}\n"
    return proc.returncode, proc.stdout + proc.stderr


def _step(name: str, argv: list[str], tree: Path, timeout: int, log: Path) -> dict[str, Any]:
    t0 = time.monotonic()
    rc, out = _execute(argv, tree, timeout)
    log.write_text(out, encoding="utf-8")
    return {"name": name, "argv": argv, "rc": rc, "wall_s": round(time.monotonic() - t0, 1), "log": str(log)}


def run_floor(tree: Path, profile: Profile, log_dir: Path) -> dict[str, Any]:
    """Run the gate, then the suite (when set); the suite is skipped once the gate failed.

    Args:
        tree: the checkout the commands run in (their cwd).
        profile: the sealed profile; its floor names the argv lists and the per-step timeout.
        log_dir: where floor-gate.log and floor-suite.log are written (created when missing).

    Returns:
        {"passed": every step exited 0, "steps": [{"name", "argv", "rc", "wall_s", "log"}]}.
        A step that could not start exits RC_NOT_STARTED, one that timed out RC_TIMEOUT.
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    timeout = profile.floor.timeout_s
    steps = [_step("gate", list(profile.floor.gate), tree, timeout, log_dir / "floor-gate.log")]
    suite = profile.suite_argv()
    if suite is not None and steps[0]["rc"] == 0:
        steps.append(_step("suite", suite, tree, timeout, log_dir / "floor-suite.log"))
    return {"passed": all(s["rc"] == 0 for s in steps), "steps": steps}


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
    if stop in CAP_STOP_REASONS:
        return [f"ended by {stop}"]
    if stop == STREAM_VOID_STOP_REASON:
        return [] if stream_reasons else ["stopped as void with no reason recorded"]
    return [f"stop reason {stop!r} is not one an arm ends with (finished, void, deadline, token_cap)"]


def _cache_read(record: dict[str, Any]) -> int | None:
    value = record.get("first_cache_read")
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _warmth_reason(res: dict[str, Any], tolerance: float, peers: list[dict[str, Any]]) -> list[str]:
    mine = _cache_read(res)
    reads = [r for r in (_cache_read(p) for p in peers) if r is not None]
    if mine is None or len(reads) < WARMTH_MIN_PEERS:
        return []
    m = median([float(r) for r in reads])
    # Against a zero median a relative difference is undefined; any non-zero read is out of line.
    out_of_line = abs(mine - m) / m > tolerance if m > 0 else mine != 0
    if not out_of_line:
        return []
    return [f"first-message cache read {mine} is off the peers' median {m:.0f} by more than {tolerance}"]


def _void_reasons(res: dict[str, Any], profile: Profile, peers: list[dict[str, Any]]) -> list[str]:
    stream_reasons = [str(r) for r in res.get("void_reasons") or []]
    guard = [str(g) for g in res.get("guard_changes") or []]
    return (stream_reasons + _result_reason(res) + _stop_reason(res, stream_reasons)
            + (["store guard fired: " + "; ".join(guard)] if guard else [])
            + _warmth_reason(res, profile.run.warmth_tolerance, peers))


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
        first_cache_read, floor_passed, bundle_commits, wall_s and void (every reason, the stream
        account's own ones first and unchanged; empty means the arm counts).

    Raises:
        FileNotFoundError: arm_dir has no result.json.
        json.JSONDecodeError: result.json is not JSON.
    """
    res = json.loads((arm_dir / "result.json").read_text(encoding="utf-8"))
    score = {"arm": res.get("arm", arm_dir.name), "cost_usd": res.get("total_cost_usd"),
             "per_model": res.get("per_model") or {}, "main_new_tokens": res.get("main_new_tokens"),
             "first_cache_read": res.get("first_cache_read"),
             "floor_passed": bool((res.get("floor") or {}).get("passed")),
             "bundle_commits": int(res.get("bundle_commits") or 0), "wall_s": res.get("wall_s"),
             "void": _void_reasons(res, profile, peers)}
    (arm_dir / "scores.json").write_text(json.dumps(score, indent=1, sort_keys=True), encoding="utf-8")
    return score
