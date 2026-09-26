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

`gh` itself FAILING gets the same treatment (`--error-grace`, 300 seconds). One HTTP 502 from
api.github.com used to end the wait outright, three times in one session, each time with twenty
minutes still on the deadline and each time reading as an infrastructure problem rather than as
one bad response. A waiter is the tool that must sit through its fetch failing, so a failure is
retried on its own budget; the streak resets on any answered poll, and only a sustained outage
ends the wait - reported as `error` with gh's own last message, never as a `timeout` that would
blame CI for the API.

An all-green answer is CONFIRMED before it is returned (`--settle`, 20 seconds), for the same
reason one level up: the runs for a push are not all created at the same instant, so the first
poll can see a SUBSET of them, and a subset that is entirely terminal is indistinguishable from
the whole set being done. Measured: a push whose `ci` workflow went green while a second workflow
for the same sha was still being created was reported as success. A failure is still reported at
once, since a later run cannot rescue it.

Waits up to `--timeout` seconds (default 1500, so 25 minutes) polling every `--interval` (30).
The timeout is wall-clock time, and each `gh` call is itself bounded (60 seconds, or what is left
of the timeout), so a stalled API connection cannot hold the wait past it. The runs are asked for
by sha (`gh run list --commit`), so newer runs of other commits cannot push them out of the
`--limit` window.

A run concluding `skipped` (a workflow whose jobs were all `if:`-gated off) does not fail the push;
a push on which every run was skipped tested nothing and is reported `failed`, never green.

Run: `uv run scripts/ci_wait.py --sha $(git rev-parse HEAD)`
     `uv run scripts/ci_wait.py --sha $(git rev-parse HEAD) --repo OWNER/REPO --json`
     `uv run scripts/ci_wait.py --sha $(git rev-parse HEAD) --timeout 1800 --interval 30`
Exit 0 = every run for that sha succeeded (or was skipped), 1 = at least one did not, 2 = could
not tell (bad sha, a bad flag value, no runs for it, timed out, `gh` failed, or the tool itself
crashed).
"""
from __future__ import annotations

import argparse
import itertools
import json
import math
import re
import subprocess
import sys
import time
import traceback
from dataclasses import dataclass
from typing import Callable, Iterable, Sequence

FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")

_FIELDS = "headSha,workflowName,status,conclusion,databaseId"
_TERMINAL = "completed"
#: Conclusions that do not fail a push. `skipped` is a workflow whose jobs were all if:-gated off.
_PASSING = frozenset({"success", "skipped"})
#: Longest a single `gh run list` may take. A half-open API connection otherwise blocks the whole
#: wait forever, and `--timeout` - checked only between polls - never gets its turn.
GH_CALL_TIMEOUT_S = 60.0
#: gh's documented exit code for "authentication required" (measured on 2.92.0: no token and no
#: config gives 4 and tells you to run `gh auth login`). Local configuration, so it is fatal here
#: rather than retried. A REJECTED credential is exit 1, not this - see GhUnavailable.
_GH_EXIT_AUTH_REQUIRED = 4
_EXIT_CODES = {"success": 0, "failed": 1, "timeout": 2, "no-runs": 2, "error": 2}


class BadSha(ValueError):
    """The sha is not a full 40-character hex commit id - the trap this tool exists to close."""


class GhFailed(RuntimeError):
    """`gh` answered, badly - a non-zero exit or output that is not a JSON list.

    Retryable. Most of what lands here is the remote end having a bad minute (a 502 from
    api.github.com), which is exactly what a WAITER should sit through rather than report.
    """


class GhUnavailable(RuntimeError):
    """`gh` cannot give an answer in this process - not installed, or not logged in.

    Not retryable: both are local configuration, and they will answer the same way for the whole
    run. Kept apart from :class:`GhFailed` so the retry budget is not spent on them, and so a
    missing `gh` reports as "could not tell" rather than as a traceback.

    The split is drawn on the exit code and nowhere else. Note its measured limit: a REJECTED
    credential does not land here. Against gh 2.92.0, no credentials at all exits 4 ("please run
    gh auth login") while a revoked or mistyped token exits 1 with `HTTP 401: Bad credentials` -
    the same code as a 502. So a dead token is retried and costs the grace before it is reported.
    Telling those apart needs gh's MESSAGE, and reading a remote system's wording for its meaning
    is the guess that produced the abandoned-wait defect in the first place.
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
        anything but ``success`` or ``skipped``, a null conclusion included (a run cancelled at
        source completes with none, and that is not green). ``skipped`` is a workflow whose
        jobs were all ``if:``-gated off: nothing ran and nothing failed, so it does not fail the
        push. ``success`` only when every run completed successfully or was skipped AND at
        least one actually succeeded - a push where everything was skipped tested nothing, so
        it is reported ``failed`` rather than green.
    """
    if not runs:
        return Verdict("no-runs", "no runs found for that sha")
    unfinished = [r for r in runs if r.get("status") != _TERMINAL]
    if unfinished:
        return Verdict("pending", _named(unfinished, "status"), tuple(runs))
    bad = [r for r in runs if r.get("conclusion") not in _PASSING]
    if bad:
        return Verdict("failed", _named(bad, "conclusion"), tuple(runs))
    if not any(r.get("conclusion") == "success" for r in runs):
        return Verdict("failed", _named(runs, "conclusion") + " (nothing ran)", tuple(runs))
    return Verdict("success", _named(runs, "conclusion"), tuple(runs))


def _run_key(row: dict[str, object]) -> tuple[object, object]:
    """Identity for one run, for asking whether the SET of runs changed between two polls.

    Pairs the id with the workflow name rather than trusting either alone: a re-run gets a fresh
    ``databaseId`` under the same name, and a row missing the field would otherwise collapse
    every run to one key and make a growing set look stable.
    """
    return (row.get("databaseId"), row.get("workflowName"))


def _named(runs: Iterable[dict[str, object]], field: str) -> str:
    """Render `workflow=value` for each run, so a report names WHICH run decided it."""
    return " ".join(f"{r.get('workflowName')}={r.get(field)}" for r in runs)


def wait_for(
    fetch: Callable[[], list[dict[str, object]]],
    *,
    deadline_polls: int | None = None,
    sleep: Callable[[float], None],
    interval_s: float = 30.0,
    appear_grace_s: float = 120.0,
    error_grace_s: float = 300.0,
    settle_s: float = 20.0,
    report: Callable[[str], None] = lambda _m: None,
    deadline_s: float | None = None,
    clock: Callable[[], float] | None = None,
) -> Verdict:
    """Poll ``fetch`` until every run is terminal, or a budget runs out.

    ``fetch``, ``sleep`` and ``clock`` are injected so the loop is testable without a network or
    a clock. With no ``clock``, elapsed time is the sum of what was handed to ``sleep``, which is
    what a test with an instant ``sleep`` means; the command line passes ``time.monotonic``, so
    the time a slow ``gh`` call took counts too.

    Each grace is measured as elapsed time since the FIRST empty (or failed) poll of the current
    streak and compared against the budget, never converted into a poll count: floor-dividing a
    grace by the interval gave ``--interval 120 --appear-grace 120`` no grace at all.

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

    An all-green result is CONFIRMED rather than returned at once, because a run that has not
    been CREATED yet is indistinguishable from one that does not exist - the same confusion the
    appear-grace closes for an EMPTY match, one level up, where the match is non-empty but
    INCOMPLETE. Measured 2026-09-02 on a real push: the first poll saw one workflow, it went
    green, and the wait reported success while a second workflow for that sha was still being
    created. So a success re-polls after ``settle_s`` and must see the same SET of runs (by
    :func:`_run_key`) before it is returned; a set that grew starts the confirmation again. Only
    a success is confirmed - a failure is returned at once, because a later run cannot rescue it -
    and running out of deadline mid-confirmation reports the green, never a timeout.

    Only :class:`GhFailed` is retried. :class:`GhUnavailable` - the OS refusing to spawn `gh` -
    propagates at once, because it is a local fact that will not change during this process, and
    spending the grace on it only delays the report. The line is drawn there, where it is
    certain, rather than by reading gh's message for words like "transient": that would be a
    guess about a remote system, and the first wrong guess puts this bug straight back.

    Args:
        fetch: Returns the run rows for the sha under test.
        deadline_polls: How many polls before giving up on runs that are still going. ``None``
            sets no count, leaving ``deadline_s`` to end the wait - what the command line does,
            since a count derived as timeout / interval ends early whenever an iteration is
            shorter than the interval (a settle, or a timeout under two intervals).
        sleep: What to wait with between polls.
        interval_s: Seconds handed to ``sleep``.
        appear_grace_s: How long to keep tolerating an EMPTY match before reporting ``no-runs``.
        error_grace_s: How long to keep tolerating CONSECUTIVE ``GhFailed`` before reporting
            ``error``.
        settle_s: How long to wait before CONFIRMING an all-green result, so a run created after
            the first all-terminal poll is still counted. ``0`` returns on the first one.
        report: Where a per-poll progress line goes.
        deadline_s: A wall-clock bound on the whole wait, checked after every poll. A sleep is
            cut to the time left, so the last poll lands on the deadline instead of an interval
            past it. ``None`` leaves only ``deadline_polls``.
        clock: Returns the current time in seconds; see above for the default.

    Returns:
        The terminal verdict: ``success``, ``failed``, ``no-runs``, ``timeout`` or ``error``.

    Raises:
        GhUnavailable: `gh` cannot be run here; no budget can fix that.
        ValueError: neither ``deadline_polls`` nor ``deadline_s`` is given, so nothing would end
            a wait on runs that never finish.
    """
    if deadline_polls is None and deadline_s is None:
        raise ValueError("wait_for needs deadline_polls or deadline_s, or it can never end")
    timer = _Timer(sleep, clock)
    started = timer.now()
    empty_since: float | None = None
    error_since: float | None = None
    errors_seen = 0
    last_error = ""
    last_summary = ""
    settled: frozenset[tuple[object, object]] | None = None
    last_success: Verdict | None = None

    def may_poll_again(poll: int) -> bool:
        if deadline_polls is not None and poll + 1 >= deadline_polls:
            return False
        return deadline_s is None or timer.now() - started < deadline_s

    def pause(seconds: float) -> None:
        if deadline_s is not None:
            seconds = min(seconds, max(0.0, deadline_s - (timer.now() - started)))
        timer.sleep(seconds)

    def label(poll: int) -> str:
        return f"poll {poll + 1}" + ("" if deadline_polls is None else f"/{deadline_polls}")

    for poll in itertools.count() if deadline_polls is None else range(deadline_polls):
        try:
            rows = fetch()
        except GhFailed as exc:
            errors_seen += 1
            last_error = str(exc)
            error_since = timer.now() if error_since is None else error_since
            if timer.now() - error_since >= error_grace_s:
                return _gh_gave_up(errors_seen, last_error)
            report(f"{label(poll)}: gh failed, retrying: {last_error}")
            if not may_poll_again(poll):
                break
            pause(interval_s)
            continue
        errors_seen = 0
        error_since = None
        current = verdict(rows)
        last_summary = current.summary
        if current.state == "no-runs":
            empty_since = timer.now() if empty_since is None else empty_since
            if timer.now() - empty_since >= appear_grace_s:
                return current
            report(f"{label(poll)}: no runs yet for that sha")
        elif current.state == "success":
            empty_since = None
            last_success = current
            seen = frozenset(_run_key(r) for r in rows)
            if settle_s <= 0 or settled == seen:
                return current
            report(f"{label(poll)}: {current.summary}; confirming no run for "
                   f"this sha is still being created")
            settled = seen
            if not may_poll_again(poll):
                break
            pause(settle_s)
            continue
        elif current.state != "pending":
            return current
        else:
            empty_since = None
            settled = None
            last_success = None
            report(f"{label(poll)}: {current.summary}")
        if not may_poll_again(poll):
            break
        pause(interval_s)
    # The deadline, reported from what the last ANSWERED poll saw. Re-fetching here to describe
    # the timeout cost an extra request that could itself fail, turning a plain timeout into an
    # error about the API - a report naming the wrong system entirely.
    # Confirming must never turn a green into a timeout. If every run was terminal and successful
    # and only the confirming poll ran out of deadline, report what was actually seen - which is
    # exactly what this function returned before the confirmation existed.
    if last_success is not None:
        return last_success
    if errors_seen:
        return _gh_gave_up(errors_seen, last_error)
    return Verdict("timeout", last_summary)


class _Timer:
    """Sleeps, and tells the time: from ``clock`` when given, else from the sleeps it was asked for.

    The fallback keeps the loop's arithmetic identical in a test whose ``sleep`` returns at once.
    """

    def __init__(self, sleep: Callable[[float], None], clock: Callable[[], float] | None) -> None:
        self._sleep = sleep
        self._clock = clock
        self._slept = 0.0

    def now(self) -> float:
        return self._clock() if self._clock is not None else self._slept

    def sleep(self, seconds: float) -> None:
        self._slept += seconds
        self._sleep(seconds)


def _gh_gave_up(polls: int, message: str) -> Verdict:
    """The verdict for gh failing on every poll of its budget, naming gh's own last words."""
    return Verdict("error", f"gh failed {polls} polls running: {message}")


def exit_code_for(state: str) -> int:
    """Map a verdict state to a POSIX exit code: 0 yes, 1 no, 2 could not tell."""
    return _EXIT_CODES.get(state, 2)


def gh_runs(
    sha: str,
    *,
    repo: str | None = None,
    limit: int = 30,
    timeout_s: float = GH_CALL_TIMEOUT_S,
) -> list[dict[str, object]]:
    """Fetch the runs whose ``headSha`` is ``sha``: asked for SERVER-side, checked client-side.

    `--commit` is passed so the API returns this sha's runs only. Without it, `--limit` bounds a
    window over EVERY recent run, and on a busy repo 30 newer runs of other shas push this sha's
    older runs out of it - a failing CI run vanished that way while a green CodeQL run remained,
    and the push read as green. `--commit` needs the full sha and fails silently without it; this
    tool has already refused a short one. The client-side filter stays as a second check.

    Raises:
        GhFailed: `gh` exited non-zero, did not answer within ``timeout_s``, or returned
            something that is not a JSON list. The caller may retry this; a bad minute at the
            API arrives here.
        GhUnavailable: `gh` could not be spawned at all - not installed, or not executable.
    """
    argv = ["gh", "run", "list", "--commit", sha, "--json", _FIELDS, "--limit", str(limit)]
    if repo:
        argv += ["--repo", repo]
    try:
        proc = subprocess.run(
            argv, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired as exc:
        raise GhFailed(f"gh did not answer within {timeout_s:g}s") from exc
    except OSError as exc:
        raise GhUnavailable(f"could not run gh: {exc}") from exc
    if proc.returncode == _GH_EXIT_AUTH_REQUIRED:
        raise GhUnavailable(f"gh is not authenticated: {(proc.stderr or '').strip()}")
    if proc.returncode != 0:
        raise GhFailed(f"gh exited {proc.returncode}: {(proc.stderr or '').strip()}")
    try:
        rows = json.loads(proc.stdout)
    except ValueError as exc:
        raise GhFailed(f"gh returned unparseable output: {exc}") from exc
    if not isinstance(rows, list):
        raise GhFailed(f"gh returned {type(rows).__name__}, not a list")
    return [r for r in rows if isinstance(r, dict) and r.get("headSha") == sha]


def _seconds(*, allow_zero: bool) -> Callable[[str], float]:
    """An argparse type for a duration: finite, and positive (or zero when ``allow_zero``).

    `float()` alone accepted `-5`, `inf` and `nan`, which then crashed deep in the loop with a
    traceback and exit 1 - the code this tool reserves for "a run failed".
    """

    def parse(text: str) -> float:
        try:
            value = float(text)
        except ValueError:
            raise argparse.ArgumentTypeError(f"not a number: {text!r}") from None
        if not math.isfinite(value) or value < 0 or (value == 0 and not allow_zero):
            bound = "zero or more" if allow_zero else "more than zero"
            raise argparse.ArgumentTypeError(f"{text!r} must be a finite number of seconds, {bound}")
        return value

    return parse


def _positive_int(text: str) -> int:
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a whole number: {text!r}") from None
    if value < 1:
        raise argparse.ArgumentTypeError(f"{text!r} must be at least 1")
    return value


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    positive, non_negative = _seconds(allow_zero=False), _seconds(allow_zero=True)
    parser.add_argument("--sha", required=True, help="the FULL 40-character commit sha (git rev-parse HEAD)")
    parser.add_argument("--repo", default=None, help="OWNER/NAME; default is the cwd's repo")
    parser.add_argument("--timeout", type=positive, default=1500.0, help="seconds to wait (default 1500)")
    parser.add_argument("--interval", type=positive, default=30.0, help="seconds between polls (default 30)")
    parser.add_argument(
        "--limit", type=_positive_int, default=30,
        help="how many of this sha's runs to fetch (default 30)",
    )
    parser.add_argument(
        "--appear-grace", type=non_negative, default=120.0,
        help="seconds to keep tolerating an EMPTY match before reporting no-runs (default 120); "
             "a just-pushed commit takes seconds to have runs at all. A DURATION, so changing "
             "--interval does not move it",
    )
    parser.add_argument(
        "--error-grace", type=non_negative, default=300.0,
        help="seconds to keep tolerating CONSECUTIVE gh failures before giving up (default 300); "
             "a 502 from the API is weather, not a verdict. The streak resets on any answered "
             "poll. Also a DURATION. Longer than --appear-grace because the costs are asymmetric: "
             "too short abandons a wait that had its whole deadline left, too long only delays "
             "reporting a setup that was broken anyway",
    )
    parser.add_argument(
        "--settle", type=non_negative, default=20.0,
        help="seconds to wait before CONFIRMING an all-green result (default 20; 0 disables). A "
             "run that has not been created yet looks exactly like one that does not exist, so a "
             "verdict from the first all-terminal poll can be computed over a partial set. Only "
             "a success is confirmed: a failure is reported at once, since a later run cannot "
             "rescue it",
    )
    parser.add_argument("--json", action="store_true", help="emit a JSON envelope instead of text")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Wait for one sha's runs and report. Returns the process exit code.

    An unexpected exception is reported as ``error`` (exit 2, "could not tell") with its
    traceback on stderr: left to the interpreter it would exit 1, the code that means "a run
    failed", and a crashed waiter would read as a red CI.
    """
    _tolerant_streams()
    args = _parse_args(argv)
    try:
        return _run(args)
    except Exception as exc:  # noqa: BLE001 - the boundary that keeps a crash off exit code 1
        traceback.print_exc(file=sys.stderr)
        return _emit(Verdict("error", f"unexpected {type(exc).__name__}: {exc}"), as_json=args.json)


def _tolerant_streams() -> None:
    """Print a workflow name the console cannot encode (cp1252) as an escape, never crash on it."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(errors="backslashreplace")
        except (ValueError, OSError):
            continue


def _run(args: argparse.Namespace) -> int:
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
    started = time.monotonic()

    def fetch() -> list[dict[str, object]]:
        # A single gh call may not outlive the whole wait: bound it by what is left, too.
        left = args.timeout - (time.monotonic() - started)
        return gh_runs(
            sha, repo=args.repo, limit=args.limit, timeout_s=max(1.0, min(GH_CALL_TIMEOUT_S, left))
        )

    try:
        result = wait_for(
            fetch,
            sleep=time.sleep,
            interval_s=args.interval,
            appear_grace_s=args.appear_grace,
            error_grace_s=args.error_grace,
            settle_s=args.settle,
            report=lambda line: print(line, file=sys.stderr, flush=True),
            deadline_s=args.timeout,
            clock=time.monotonic,
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
