# /// script
# requires-python = ">=3.10"
# ///
"""Wait until every GitHub Actions run for ONE commit is finished, and say whether they passed.

Why: a hand-rolled CI poll goes wrong the same way every time. `gh run list --limit 1` returns
whichever run sorted first (CodeQL, not CI, on a repo with several push workflows), a run reads
`queued` while any single job of it is, and - the one that costs an hour - a SHORT sha matches
nothing. `--commit 24da3ec` returns `[]` with no error and exit 0, and filtering client-side on
`headSha` does not sidestep that, it relocates it: the filtered list is simply empty, and an
"are they all terminal?" test over an empty list is vacuous, so the loop spins to its deadline
printing progress. So this refuses a sha that is not 40 hex characters BEFORE it polls, and gives
an empty match its own SMALL budget (`--appear-grace`, 120 seconds) rather than the full deadline:
a just-pushed commit takes seconds to have runs at all, so an empty first poll is that race, while
an empty one two minutes later is a sha that will never match. That budget is a DURATION, so
changing `--interval` does not silently move it.

Waits up to `--timeout` seconds (default 1500, so 25 minutes) polling every `--interval` (30).

Run: `uv run scripts/ci_wait.py --sha $(git rev-parse HEAD)`
     `uv run scripts/ci_wait.py --sha $(git rev-parse HEAD) --repo OWNER/REPO --json`
     `uv run scripts/ci_wait.py --sha $(git rev-parse HEAD) --timeout 1800 --interval 30`
Exit 0 = every run for that sha succeeded, 1 = at least one did not, 2 = could not tell
(bad sha, no runs for it, timed out, `gh` failed).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Callable, Iterable, Sequence

FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")

_FIELDS = "headSha,workflowName,status,conclusion,databaseId"
_TERMINAL = "completed"
_EXIT_CODES = {"success": 0, "failed": 1, "timeout": 2, "no-runs": 2, "error": 2}


class BadSha(ValueError):
    """The sha is not a full 40-character hex commit id - the trap this tool exists to close."""


class GhFailed(RuntimeError):
    """`gh` itself could not answer; nothing can be concluded about the runs."""


@dataclass(frozen=True)
class Verdict:
    """What one look at the run list means.

    Attributes:
        state: ``success``, ``failed``, ``pending``, ``no-runs`` or ``timeout``.
        summary: One human line naming the runs that decided it.
        runs: The rows the verdict was computed from.
    """

    state: str
    summary: str
    runs: tuple[dict[str, object], ...] = ()


def require_full_sha(sha: str) -> str:
    """Return ``sha`` lowercased, or refuse it. PURE.

    Args:
        sha: The commit id to check.

    Returns:
        The lowercased 40-character sha.

    Raises:
        BadSha: not 40 hex characters. This is checked BEFORE any polling, because the
            failure it prevents is silent: a short sha matches no run, and a wait loop over
            an empty match never terminates on its own.
    """
    candidate = sha.strip().lower()
    if not FULL_SHA_RE.match(candidate):
        raise BadSha(
            f"{sha!r} is not a full 40-character sha; a short one matches no run and the wait "
            f"would spin to its deadline. Use `git rev-parse HEAD`, never `--short`."
        )
    return candidate


def verdict(runs: Sequence[dict[str, object]]) -> Verdict:
    """Classify one poll's run list. PURE.

    Args:
        runs: The rows for ONE sha, as `gh run list --json` returns them.

    Returns:
        ``no-runs`` when the list is empty - never ``success``, because "nothing matched" and
        "everything passed" are the same shape and only one of them is good news. ``pending``
        while any run is not ``completed``. ``failed`` when any completed run's conclusion is
        anything but ``success``, a null conclusion included (a run cancelled at source
        completes with none, and that is not green). ``success`` only when every run completed
        successfully.
    """
    if not runs:
        return Verdict("no-runs", "no runs found for that sha")
    unfinished = [r for r in runs if r.get("status") != _TERMINAL]
    if unfinished:
        return Verdict("pending", _named(unfinished, "status"), tuple(runs))
    bad = [r for r in runs if r.get("conclusion") != "success"]
    if bad:
        return Verdict("failed", _named(bad, "conclusion"), tuple(runs))
    return Verdict("success", _named(runs, "conclusion"), tuple(runs))


def _named(runs: Iterable[dict[str, object]], field: str) -> str:
    """Render `workflow=value` for each run, so a report names WHICH run decided it."""
    return " ".join(f"{r.get('workflowName')}={r.get(field)}" for r in runs)


def wait_for(
    fetch: Callable[[], list[dict[str, object]]],
    *,
    deadline_polls: int,
    sleep: Callable[[float], None],
    interval_s: float = 30.0,
    appear_grace_s: float = 120.0,
    report: Callable[[str], None] = lambda _m: None,
) -> Verdict:
    """Poll ``fetch`` until every run is terminal, or a budget runs out.

    ``fetch`` and ``sleep`` are injected so the loop is testable without a network or a clock.

    An empty match gets its OWN small budget, separate from the deadline, because it has two
    causes that look identical: the runs for a just-pushed commit have not been created yet
    (seconds), or this sha will never have any. Waiting the FULL deadline out on the second is
    the spin this tool exists to prevent; refusing on the first poll breaks the ordinary case of
    running it straight after `git push`. So it waits ``appear_grace_s`` and then says ``no-runs``.
    The short-sha half of that trap is closed elsewhere and earlier - :func:`require_full_sha`
    refuses before any polling - so nothing here has to guess about it.

    That budget is a DURATION and not a poll count on purpose: as a count it moved with
    ``interval_s``, so ``--interval 5`` silently cut the grace to a sixth and the tool would
    error on a push whose runs took twenty seconds to appear - the commonest path, reported as
    "no runs found for that sha", which points at the sha rather than at the grace.

    Args:
        fetch: Returns the run rows for the sha under test.
        deadline_polls: How many polls before giving up on runs that are still going.
        sleep: What to wait with between polls.
        interval_s: Seconds handed to ``sleep``.
        appear_grace_s: How long to keep tolerating an EMPTY match before reporting ``no-runs``.
        report: Where a per-poll progress line goes.

    Returns:
        The terminal verdict: ``success``, ``failed``, ``no-runs`` or ``timeout``.
    """
    empty_polls_allowed = max(1, int(appear_grace_s // max(interval_s, 0.001)))
    empty_seen = 0
    for poll in range(deadline_polls):
        current = verdict(fetch())
        if current.state == "no-runs":
            empty_seen += 1
            if empty_seen >= empty_polls_allowed:
                return current
            report(f"poll {poll + 1}/{deadline_polls}: no runs yet for that sha")
        elif current.state != "pending":
            return current
        else:
            empty_seen = 0
            report(f"poll {poll + 1}/{deadline_polls}: {current.summary}")
        if poll + 1 < deadline_polls:
            sleep(interval_s)
    return Verdict("timeout", verdict(fetch()).summary)


def exit_code_for(state: str) -> int:
    """Map a verdict state to a POSIX exit code: 0 yes, 1 no, 2 could not tell."""
    return _EXIT_CODES.get(state, 2)


def gh_runs(sha: str, *, repo: str | None = None, limit: int = 30) -> list[dict[str, object]]:
    """Fetch the runs whose ``headSha`` is ``sha``, filtering CLIENT-side.

    The filter is client-side because `--commit` needs the full sha too and fails silently
    without it; this tool has already refused a short one, so both routes are safe, and the
    client-side one costs no second request.

    Raises:
        GhFailed: `gh` exited non-zero or returned something that is not a JSON list.
    """
    argv = ["gh", "run", "list", "--json", _FIELDS, "--limit", str(limit)]
    if repo:
        argv += ["--repo", repo]
    proc = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
    if proc.returncode != 0:
        raise GhFailed(f"gh exited {proc.returncode}: {(proc.stderr or '').strip()}")
    try:
        rows = json.loads(proc.stdout)
    except ValueError as exc:
        raise GhFailed(f"gh returned unparseable output: {exc}") from exc
    if not isinstance(rows, list):
        raise GhFailed(f"gh returned {type(rows).__name__}, not a list")
    return [r for r in rows if isinstance(r, dict) and r.get("headSha") == sha]


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--sha", required=True, help="the FULL 40-character commit sha (git rev-parse HEAD)")
    parser.add_argument("--repo", default=None, help="OWNER/NAME; default is the cwd's repo")
    parser.add_argument("--timeout", type=float, default=1500.0, help="seconds to wait (default 1500)")
    parser.add_argument("--interval", type=float, default=30.0, help="seconds between polls (default 30)")
    parser.add_argument("--limit", type=int, default=30, help="how many recent runs to scan (default 30)")
    parser.add_argument(
        "--appear-grace", type=float, default=120.0,
        help="seconds to keep tolerating an EMPTY match before reporting no-runs (default 120); "
             "a just-pushed commit takes seconds to have runs at all. A DURATION, so changing "
             "--interval does not move it",
    )
    parser.add_argument("--json", action="store_true", help="emit a JSON envelope instead of text")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Wait for one sha's runs and report. Returns the process exit code."""
    args = _parse_args(argv)
    try:
        sha = require_full_sha(args.sha)
    except BadSha as exc:
        return _emit(Verdict("error", str(exc)), as_json=args.json)
    polls = max(1, int(args.timeout // max(args.interval, 1.0)))
    try:
        result = wait_for(
            lambda: gh_runs(sha, repo=args.repo, limit=args.limit),
            deadline_polls=polls,
            sleep=time.sleep,
            interval_s=args.interval,
            appear_grace_s=args.appear_grace,
            report=lambda line: print(line, file=sys.stderr, flush=True),
        )
    except GhFailed as exc:
        return _emit(Verdict("error", str(exc)), as_json=args.json)
    return _emit(result, as_json=args.json)


def _emit(result: Verdict, *, as_json: bool) -> int:
    """Print the verdict and return its exit code; diagnostics to stderr, never into the data."""
    code = exit_code_for(result.state)
    if as_json:
        print(json.dumps({"ok": code == 0, "state": result.state, "summary": result.summary,
                          "runs": list(result.runs)}))
    elif code == 0:
        print(result.summary)
    else:
        print(f"{result.state}: {result.summary}", file=sys.stderr)
    return code


if __name__ == "__main__":
    sys.exit(main())
