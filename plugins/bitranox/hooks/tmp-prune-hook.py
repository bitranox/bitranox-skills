"""SessionStart + Stop hook: start a detached temp-dir prune at most once an hour, machine-wide.

The pruning itself, and what it counts as dead, is `tmp_prune.py`. This hook only decides whether
one should start now: on SessionStart, and on every Stop so a session that runs for days still
triggers it. One timestamp file shared by every session on the machine throttles it, so ten open
sessions still prune once an hour, not ten times.

The `tmp_prune` config knob (`/memory-settings`) chooses the mode: `on` deletes, `dry-run` only logs
what would go, `off` starts nothing. Each run appends one JSON line to
`~/.claude/self-improve-audit/tmp-prune.log.jsonl`.

It prints nothing: SessionStart stdout would be injected into the session's context. Every failure
exits 0, because a cleanup chore must never wedge a turn.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import tmp_prune  # noqa: E402 - needs the sys.path line above

WORKER = Path(__file__).resolve().with_name("tmp_prune.py")
MODES = ("on", "dry-run", "off")


def worker_argv(*, mode: str, state_dir: Path, session_id: str | None) -> list[str]:
    argv = [sys.executable, str(WORKER), "--release-slot", "--state-dir", str(state_dir)]
    if mode == "on":
        argv.append("--apply")
    if session_id:
        argv += ["--keep-session", session_id]
    return argv


def spawn_detached(argv: list[str]) -> None:
    """Start the worker so it outlives this hook and is never part of the session's process group."""
    kwargs: dict[str, object] = {
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "close_fds": True,
    }
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
    else:
        kwargs["start_new_session"] = True
    subprocess.Popen(argv, **kwargs)  # type: ignore[call-overload]  # noqa: S603 - our own interpreter and script


def _session_id(payload: str) -> str | None:
    try:
        event = json.loads(payload)
    except ValueError:
        return None
    sid = event.get("session_id") if isinstance(event, dict) else None
    return sid if isinstance(sid, str) and sid else None


def run(
    payload: str,
    *,
    mode: str,
    state_dir: Path,
    now: float,
    spawn: Callable[[list[str]], None] = spawn_detached,
) -> None:
    """Start one prune when the mode allows it and the machine-wide slot is free."""
    if mode not in MODES or mode == "off":
        return
    if not tmp_prune.claim_slot(state_dir, now=now):
        return
    try:
        spawn(worker_argv(mode=mode, state_dir=state_dir, session_id=_session_id(payload)))
    except OSError:
        tmp_prune.release_slot(state_dir)  # nothing started, so nothing will release it


def _configured_mode() -> str:
    import self_improve_signals  # noqa: PLC0415 - large module, only needed once a hook actually runs

    return str(self_improve_signals.load_config().get("tmp_prune", "on"))


def main() -> int:
    try:
        payload = sys.stdin.read()
        run(payload, mode=_configured_mode(), state_dir=tmp_prune.default_state_dir(), now=time.time())
    except Exception:  # noqa: BLE001, S110 - a cleanup chore must never fail a turn
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
