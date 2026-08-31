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

`gh` itself FAILING gets the same treatment (`--error-grace`, 120 seconds). One HTTP 502 from
api.github.com used to end the wait outright, three times in one session, each time with twenty
minutes still on the deadline and each time reading as an infrastructure problem rather than as
one bad response. A waiter is the tool that must sit through its fetch failing, so a failure is
retried on its own budget; the streak resets on any answered poll, and only a sustained outage
ends the wait - reported as `error` with gh's own last message, never as a `timeout` that would
blame CI for the API.

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
    """`gh` answered, badly - a non-zero exit or output that is not a JSON list.

    Retryable. Most of what lands here is the remote end having a bad minute (a 502 from
    api.github.com), which is exactly what a WAITER should sit through rather than report.
    """


class GhUnavailable(RuntimeError):
    """`gh` could not be run at all - not installed, or not executable.

    Not retryable: this is the local machine, and it will answer the same way for the whole
    process. Kept apart from :class:`GhFailed` so the retry budget is not spent on it, and so
    a missing `gh` reports as "could not tell" rather than as a traceback.
    """


@dataclass(frozen=True)
class Verdict:
    """What one look at the run list means.

    Attributes:
        state: ``success``, ``failed``, ``pending``, ``no-runs``, ``timeout`` or ``error``.
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


def sha_is_known_locally(sha: str, *, run: Callable[..., object] = subprocess.run) -> bool | None:
    """Does the local repository hold ``sha`` as a commit? ``None`` when it cannot tell.

    The format guard above closes the SHORT-sha trap. It cannot close the neighbouring one: a
    sha that is 40 hex characters and simply never existed - completed from an abbreviated
    display, transcribed, or invented. That sha reaches `gh`, matches nothing, and the wait
    reports ``no-runs``, which is the SAME answer a freshly pushed commit gives before its runs
    appear. Asking git first separates the two, locally and instantly.

    Args:
        sha: A full sha, already through `require_full_sha`.
        run: Injected process runner, so the check is testable without a repository.

    Returns:
        ``True`` if this repository holds the commit, ``False`` if it demonstrably does not,
        and ``None`` when the question cannot be answered here - no git on PATH, or not inside
        a work tree. ``None`` is deliberately distinct from ``False``: "I cannot tell" must
        never be reported as "that commit does not exist".
    """
    def _rc(argv: list[str]) -> object | None:
        try:
            return run(argv, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
        except OSError:
            return None

    inside = _rc(["git", "rev-parse", "--is-inside-work-tree"])
    # Keyed on the exit code plus that one stdout token, never on git's message: git localises
    # its errors, so an English-text match silently stops working on a non-English machine.
    if inside is None or getattr(inside, "returncode", 1) != 0:
        return None
    if (getattr(inside, "stdout", "") or "").strip() != "true":
        return None
    proc = _rc(["git", "cat-file", "-e", f"{sha}^{{commit}}"])
    if proc is None:
        return None
    return getattr(proc, "returncode", 1) == 0


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
    error_grace_s: float = 120.0,
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

    ``fetch`` FAILING gets a third budget, on the same duration reasoning. Measured 2026-08-31:
    `gh run list` answered HTTP 502 intermittently while the API was otherwise healthy, and one
    bad response ended a wait that had twenty minutes left - three times running. A waiter is
    the one tool that must sit through its fetch failing, because the alternative is the caller
    re-running the whole wait by hand, which is the spin this tool exists to prevent. The streak
    RESETS on any answered poll, so an intermittent fault is waited out however long it lasts
    while a sustained one still ends inside ``error_grace_s``. Which budget ran out is always
    named: gh failing for the whole deadline reports ``error`` with gh's own last message, never
    ``timeout``, which would blame CI for the API.

    Only :class:`GhFailed` is retried. :class:`GhUnavailable` - the OS refusing to spawn `gh` -
    propagates at once, because it is a local fact that will not change during this process, and
    spending the grace on it only delays the report. The line is drawn there, where it is
    certain, rather than by reading gh's message for words like "transient": that would be a
    guess about a remote system, and the first wrong guess puts this bug straight back.

    Args:
        fetch: Returns the run rows for the sha under test.
        deadline_polls: How many polls before giving up on runs that are still going.
        sleep: What to wait with between polls.
        interval_s: Seconds handed to ``sleep``.
        appear_grace_s: How long to keep tolerating an EMPTY match before reporting ``no-runs``.
        error_grace_s: How long to keep tolerating CONSECUTIVE ``GhFailed`` before reporting
            ``error``.
        report: Where a per-poll progress line goes.

    Returns:
        The terminal verdict: ``success``, ``failed``, ``no-runs``, ``timeout`` or ``error``.

    Raises:
        GhUnavailable: `gh` cannot be run here; no budget can fix that.
    """
    empty_polls_allowed = max(1, int(appear_grace_s // max(interval_s, 0.001)))
    error_polls_allowed = max(1, int(error_grace_s // max(interval_s, 0.001)))
    empty_seen = 0
    errors_seen = 0
    last_error = ""
    last_summary = ""
    for poll in range(deadline_polls):
        try:
            rows = fetch()
        except GhFailed as exc:
            errors_seen += 1
            last_error = str(exc)
            if errors_seen >= error_polls_allowed:
                return _gh_gave_up(errors_seen, last_error)
            report(f"poll {poll + 1}/{deadline_polls}: gh failed, retrying: {last_error}")
            if poll + 1 < deadline_polls:
                sleep(interval_s)
            continue
        errors_seen = 0
        current = verdict(rows)
        last_summary = current.summary
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
    # The deadline, reported from what the last ANSWERED poll saw. Re-fetching here to describe
    # the timeout cost an extra request that could itself fail, turning a plain timeout into an
    # error about the API - a report naming the wrong system entirely.
    if errors_seen:
        return _gh_gave_up(errors_seen, last_error)
    return Verdict("timeout", last_summary)


def _gh_gave_up(polls: int, message: str) -> Verdict:
    """The verdict for gh failing on every poll of its budget, naming gh's own last words."""
    return Verdict("error", f"gh failed {polls} polls running: {message}")


def exit_code_for(state: str) -> int:
    """Map a verdict state to a POSIX exit code: 0 yes, 1 no, 2 could not tell."""
    return _EXIT_CODES.get(state, 2)


def gh_runs(sha: str, *, repo: str | None = None, limit: int = 30) -> list[dict[str, object]]:
    """Fetch the runs whose ``headSha`` is ``sha``, filtering CLIENT-side.

    The filter is client-side because `--commit` needs the full sha too and fails silently
    without it; this tool has already refused a short one, so both routes are safe, and the
    client-side one costs no second request.

    Raises:
        GhFailed: `gh` exited non-zero or returned something that is not a JSON list. The
            caller may retry this; a bad minute at the API arrives here.
        GhUnavailable: `gh` could not be spawned at all - not installed, or not executable.
    """
    argv = ["gh", "run", "list", "--json", _FIELDS, "--limit", str(limit)]
    if repo:
        argv += ["--repo", repo]
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
    except OSError as exc:
        raise GhUnavailable(f"could not run gh: {exc}") from exc
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
    parser.add_argument(
        "--error-grace", type=float, default=120.0,
        help="seconds to keep tolerating CONSECUTIVE gh failures before giving up (default 120); "
             "a 502 from the API is weather, not a verdict. The streak resets on any answered "
             "poll. Also a DURATION",
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
    # WARN, never refuse. git not holding the sha is strong evidence of a caller bug, but it is not
    # proof: watching a sha you have not fetched (someone else's push, a sha from a notification, a
    # shallow clone) is legitimate, and `gh` is the authority on whether runs exist - not this
    # checkout. Refusing here would turn those into a hard error that reads as "no such commit".
    # Only asked when the sha is meant to be THIS repo's: with --repo the runs belong elsewhere.
    if args.repo is None and sha_is_known_locally(sha) is False:
        print(
            f"warning: {sha} is not a commit in this repository. If you did not fetch it, that is "
            f"expected; if you completed it from a short one, it will match no run and this wait "
            f"will end in 'no-runs'. Derive it in the same command: --sha $(git rev-parse HEAD).",
            file=sys.stderr,
        )
    polls = max(1, int(args.timeout // max(args.interval, 1.0)))
    try:
        result = wait_for(
            lambda: gh_runs(sha, repo=args.repo, limit=args.limit),
            deadline_polls=polls,
            sleep=time.sleep,
            interval_s=args.interval,
            appear_grace_s=args.appear_grace,
            error_grace_s=args.error_grace,
            report=lambda line: print(line, file=sys.stderr, flush=True),
        )
    except (GhFailed, GhUnavailable) as exc:
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
