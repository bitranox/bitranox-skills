# /// script
# requires-python = ">=3.10"
# ///
"""Arm a time-bounded backstop over async work, and REFUSE to arm one that is already satisfied.

Why: when you dispatch a background subagent (or any long async job), the completion
notification is the happy path - a hung or died-on-error worker may never fire it. So you arm a
waiter. Hand-rolling that waiter goes wrong in two opposite directions, both of which look like
success:

1. **The exit condition is satisfiable while the worker is still going.** "The branch head moved"
   reads like the artifact-only-a-finished-worker-writes test, but an agent that commits and then
   writes its report is still working, so the backstop retires mid-flight and stands down before
   the window it existed to cover. When a dispatch owes TWO deliverables, only the LAST one is a
   completion signal. The same defect hides one level down: a worker that creates its report
   first and appends to it satisfies a bare `exists()` test MID-WRITE, so the controller is told
   the work finished and then reads a truncated artifact. See `DoneFileWatch`.
2. **The deadline has no cancel path.** A 45-minute timer armed over a reviewer that returned in
   7 minutes keeps counting and then announces a timeout for a job that was never late. A stale
   alarm is not harmless: it is a false positive in the one channel built to be believed, and it
   discounts the next real one.

Measured 2026-08-28: five backstops hand-written in a single session, two of them carrying one of
those defects, plus a third where a trailing `&` in a foreground shell orphaned the waiter so it
ran but could never report.

The load-bearing part of this tool is therefore NOT the sleeping - it is `validate_arm`, which
refuses at arm time when the exit condition is ALREADY true. A backstop whose condition holds
before the work starts provides no coverage at all while reporting success on its first poll,
and nothing downstream can detect that.

Exit codes: 0 = the work finished (or the controller cancelled), 1 = TIMEOUT, go and look,
2 = refused to arm / usage error.
"""

from __future__ import annotations

import argparse
import enum
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "ArmRefused",
    "DoneFileWatch",
    "Outcome",
    "Probe",
    "decide",
    "probe_now",
    "validate_arm",
    "wait",
]


class ArmRefused(Exception):
    """The backstop would provide no coverage, so it was not armed."""


class Outcome(enum.Enum):
    WAIT = "wait"
    DONE = "done"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


@dataclass(frozen=True)
class Probe:
    """One sample of the world: has the controller cancelled, and is the work finished."""

    cancelled: bool
    done: bool


def decide(probe: Probe, *, elapsed: float, deadline: float) -> Outcome:
    """Decide what a waiter should do, given one sample and the clock.

    Precedence is deliberate and is where the hand-rolled loops went wrong:

    * CANCELLED outranks everything, including an expired deadline - the controller saying
      "the subject reported" must never still produce a timeout.
    * DONE outranks TIMEOUT, so a worker that finishes in the same tick the deadline expires is
      reported finished rather than hung.
    """
    if probe.cancelled:
        return Outcome.CANCELLED
    if probe.done:
        return Outcome.DONE
    if elapsed >= deadline:
        return Outcome.TIMEOUT
    return Outcome.WAIT


def _head(repo: Path) -> str:
    out = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return out.stdout.strip()


def _head_moved(repo: Path, base: str) -> bool:
    """True when HEAD is no longer the base commit. Compared on the SHORTER of the two strings so
    an abbreviated base (the form a human pastes) matches a full sha."""
    head = _head(repo)
    n = min(len(head), len(base))
    return head[:n] != base[:n]


def validate_arm(
    *,
    done_file: Path | None,
    repo: Path | None,
    base: str | None,
    cancel_file: Path | None = None,
) -> None:
    """Refuse to arm a backstop that cannot provide coverage.

    A cancel file ALONE is a legitimate arming: a text-returning subagent produces no artifact
    at any point, so the documented sound shape there is a deadline plus a sentinel the
    controller touches when the agent reports. What is refused is a bare deadline with no signal
    of any kind, and any signal that is already true before the work starts.

    Raises:
        ArmRefused: there is no signal at all (a bare sleep cannot tell finished from hung), or
            a signal is ALREADY satisfied before the work has begun.
    """
    if done_file is None and repo is None and cancel_file is None:
        raise ArmRefused(
            "no exit condition given - pass --done-file (the LAST artifact the worker writes), "
            "or --repo with --base, or at minimum --cancel-file for a text-returning agent; "
            "a bare deadline cannot tell finished from hung"
        )
    if cancel_file is not None and cancel_file.exists():
        raise ArmRefused(
            f"{cancel_file} already exists, so this backstop would cancel on its first poll and "
            "cover nothing - remove the stale sentinel from the previous run"
        )
    if done_file is not None and done_file.exists():
        raise ArmRefused(
            f"{done_file} already exists, so this backstop would report success on its first "
            "poll and cover nothing - delete the stale artifact, or name the artifact this run "
            "will actually produce"
        )
    if repo is not None:
        if base is None:
            raise ArmRefused("--repo needs --base (the commit the work starts from)")
        if _head_moved(repo, base):
            raise ArmRefused(
                f"{repo} HEAD has already moved past {base}, so the exit condition is satisfied "
                "before the work starts - pass the CURRENT head as --base"
            )


class DoneFileWatch:
    """Decide when a done-file means FINISHED rather than merely PRESENT.

    A worker that creates its report first and writes it incrementally satisfies a bare
    ``exists()`` test mid-write. That is defect 1 from the module docstring arriving in the
    middle of the run instead of at arm time, and it is worse there: the controller is told the
    work finished, reads a half-written artifact, and nothing distinguishes a short report from
    a short answer.

    Two conditions, because they cover different halves. An EMPTY file is never a finished
    report - a bare ``touch`` produces one - and a file whose size is still changing is still
    being written. ``settle`` is how long the size must hold, and defaults to one poll interval.

    It cannot tell a finished file from one whose writer paused longer than ``settle``; that is
    inherent to any stability test, which is why the deadline stays the real backstop. Pass
    ``settle=0`` to accept a non-empty file on sight - sound only when the worker writes the
    artifact atomically, temp file then rename, so it is never observable half-written.
    """

    def __init__(self, path: Path | None, *, settle: float) -> None:
        self.path = path
        self.settle = settle
        self._size: int | None = None
        self._since: float = 0.0

    def finished(self, now: float) -> bool:
        """Sample once: True only when the file is non-empty and its size has held for settle."""
        size = self._current_size()
        if size is None or size == 0:
            self._size, self._since = None, now
            return False
        if size != self._size:
            self._size, self._since = size, now
        return now - self._since >= self.settle

    def _current_size(self) -> int | None:
        """None for absent or unreadable, which both contribute False rather than raising."""
        if self.path is None:
            return None
        try:
            return self.path.stat().st_size
        except OSError:
            return None


def probe_now(
    *,
    done_watch: DoneFileWatch | None,
    cancel_file: Path | None,
    repo: Path | None,
    base: str | None,
    now: float = 0.0,
) -> Probe:
    """Sample the world once. A missing repo or file simply contributes False.

    The done-file half is asked through a ``DoneFileWatch`` rather than a bare path, so no
    caller can reach exists()-only semantics and stand down over a half-written report. ``now``
    is the elapsed time the watch measures its settle window against.
    """
    cancelled = cancel_file is not None and cancel_file.exists()
    done = done_watch is not None and done_watch.finished(now)
    if not done and repo is not None and base is not None:
        done = _head_moved(repo, base)
    return Probe(cancelled=cancelled, done=done)


def wait(
    *,
    deadline: float,
    interval: float,
    done_file: Path | None,
    cancel_file: Path | None,
    repo: Path | None,
    base: str | None,
    label: str,
    settle: float | None = None,
    now: object = time.monotonic,
    sleep: object = time.sleep,
) -> tuple[Outcome, float]:
    """Poll until the work finishes, the controller cancels, or the deadline expires.

    ``settle`` is how long the done-file's size must hold before it counts as finished; None
    means one poll interval, which is the shortest window a poller can actually observe.

    ``now`` and ``sleep`` are injected so the loop is testable without real time.
    """
    clock = now  # type: ignore[assignment]
    napper = sleep  # type: ignore[assignment]
    start = clock()  # type: ignore[operator]
    watch = DoneFileWatch(done_file, settle=interval if settle is None else settle)
    while True:
        elapsed = clock() - start  # type: ignore[operator]
        probe = probe_now(
            done_watch=watch, cancel_file=cancel_file, repo=repo, base=base, now=elapsed
        )
        outcome = decide(probe, elapsed=elapsed, deadline=deadline)
        if outcome is not Outcome.WAIT:
            return outcome, elapsed
        napper(interval)  # type: ignore[operator]


def _report(outcome: Outcome, elapsed: float, label: str) -> int:
    tag = f" [{label}]" if label else ""
    secs = f"{elapsed:.0f}s"
    if outcome is Outcome.DONE:
        print(f"BACKSTOP{tag}: work finished at {secs}")
        return 0
    if outcome is Outcome.CANCELLED:
        print(f"BACKSTOP{tag}: cancelled by the controller at {secs} - nothing wrong")
        return 0
    print(f"BACKSTOP{tag}: TIMEOUT after {secs} - investigate or take over")
    return 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Arm a deadline over async work; refuse to arm one already satisfied."
    )
    p.add_argument("--deadline", type=float, required=True, help="seconds, about 1.5-2x expected")
    p.add_argument("--interval", type=float, default=60.0, help="poll seconds (default 60)")
    p.add_argument(
        "--done-file",
        type=Path,
        help="the LAST artifact the worker writes - not an intermediate one",
    )
    p.add_argument(
        "--cancel-file",
        type=Path,
        help="sentinel the controller touches when the subject reports, so a finished job "
        "cannot produce a timeout later",
    )
    p.add_argument("--repo", type=Path, help="git repo whose HEAD moving means finished")
    p.add_argument("--base", help="the commit --repo starts from")
    p.add_argument("--label", default="", help="name shown in the output line")
    p.add_argument(
        "--settle",
        type=float,
        default=None,
        help="seconds the done-file's size must hold before it counts as finished (default: "
        "one --interval). 0 accepts a non-empty file on sight, which is only safe when the "
        "worker writes it atomically",
    )
    a = p.parse_args(argv)

    try:
        validate_arm(
            done_file=a.done_file, repo=a.repo, base=a.base, cancel_file=a.cancel_file
        )
    except ArmRefused as exc:
        print(f"BACKSTOP REFUSED: {exc}", file=sys.stderr)
        return 2

    outcome, elapsed = wait(
        deadline=a.deadline,
        interval=a.interval,
        done_file=a.done_file,
        cancel_file=a.cancel_file,
        repo=a.repo,
        base=a.base,
        label=a.label,
        settle=a.settle,
    )
    return _report(outcome, elapsed, a.label)


if __name__ == "__main__":
    raise SystemExit(main())
