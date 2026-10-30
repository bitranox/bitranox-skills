# /// script
# requires-python = ">=3.14"
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
once, even while other runs on the sha are still going, since a later run cannot rescue it.

Waits up to `--timeout` seconds (default 3600; a 25-minute default was seconds short of a real
CI run) polling every `--interval` (30; below 5 is refused, since each poll is one API request and
a tiny one polls back to back). The timeout is wall-clock time, and each poll's run listing is
itself bounded (60 seconds, or what is left of the timeout, but never under 10 seconds: a final
call bounded by the one second left failed on a run still in progress and read as an API outage).
Every other call - job reads, a dropped run's re-read, the billing check, a timeout's history
lookups - shares one window that ends that same floor past the deadline, and none is made once it
is spent, so a stalled API connection cannot hold the wait more than that floor past it. A timeout
names how long each unfinished workflow usually takes (the median of its recent successful runs),
and a gh failure on the calls the deadline cut short is reported as the timeout, not as `error`.
The runs are asked for by sha (`gh run list --commit`), so newer runs of other commits cannot
push them out of the `--limit` window. That sha-filtered listing can DROP a run it already
returned - measured: a ci run listed in_progress for 27 polls vanished as it completed, and the
listing answered [] for minutes - so every run once listed is remembered, and one missing from a
later listing is re-read by id (`gh run view`), with a stderr line naming it. An empty listing then means "no runs" only
for a sha never seen with any, and a failing run cannot drop out beside a listed success.

A run concluding `skipped` (a workflow whose jobs were all `if:`-gated off) does not fail the push;
a push on which every run was skipped tested nothing and is reported `failed`, never green.

By default every run on the sha counts EXCEPT a scheduled one: a nightly run that GitHub queues on
the same head sha would otherwise hold a push's verdict open until the deadline, or fail it for a
reason the push did not cause. The exclusion is client-side and covers only `schedule`, so a fork
pull request's head - whose only runs are `pull_request` - is seen by a bare wait. `--event NAME`
counts only runs of that event (asked for server-side); `--event any` counts every run, scheduled
ones included. When the default leaves a run out, the verdict says how many, so a green
beside a still-queued nightly run does not read as the tool missing it. A run
concluding `action_required` (a fork pull request awaiting a maintainer's approval) is reported at
once as `pending-approval`, exit 2: no wait resolves it, and it is not a failure.

A run that stays `queued` for `--queued-grace` seconds (900; 0 disables) while nothing else on the
sha is still going is reported as `stuck-queued`, exit 2, naming the run id - not waited out to the
deadline. Measured: a duplicate `workflow_run` trigger of a release workflow sat queued with no
runner for 35 minutes after its twin on the same sha had already published, and the wait polled it
73 times. When a run of the same workflow on that sha already succeeded, the summary says the stuck
one is likely a duplicate trigger; it never cancels anything itself. Before that verdict the run's
own jobs are read (`gh run view <id> --json jobs`), because a run stays `queued` while ONE job
waits for a runner: measured, a run read `queued` for 15 minutes with three of five jobs done and
one running. A run with a started job, or jobs that could not be read, is waited for instead.

Every unfinished run's JOBS are read on each poll (`gh run view <id> --json jobs`), because the
run status hides them both ways: a run stays `queued` while one job waits for a runner (measured,
35+ polls of `CI=queued` with 15 of 16 jobs green), and a run can read `completed` / `success`
while its jobs endpoint still shows jobs queued or running (measured, 9 of 18). So each poll line
names the job counts, every queued job with how long it has waited, and any job already failed,
and a green run with an unfinished job is waited for. `--fail-on-failed-job` ends the wait as
`failed` as soon as such a job failed; it is off by default because a `continue-on-error` job
fails without failing its run and the API does not say which jobs carry it.

`--workflow NAME` counts only that workflow's runs (asked for server-side), for waiting on a
release workflow without also waiting on CI. A `no-runs` verdict names its two live causes: a
push to a branch the workflows' `on: push` filters exclude, and - when the local repository
holds the sha on no remote-tracking branch - a sha that was never pushed or that a rebase
republished under a new sha.

The repository is resolved ONCE, before the first poll (`--repo`, else `gh repo view` from the
cwd; a `--repo` that is a local directory is resolved the same way from there, and one that is
neither OWNER/NAME nor a directory is refused, exit 2), and named on every poll: a cwd removed mid-wait - a worktree deleted while CI runs - would
otherwise turn every later poll into a gh failure.

`--ref REF` (HEAD, origin/master, a tag) asks this tool to resolve the sha itself, with
`git rev-parse --verify` in the cwd's repository, and prints what it resolved to. Prefer it to
`--sha`: a sha the caller types is one it can pad from a short display or splice onto a guessed
prefix, and both are 40 hex characters that pass every format check here. It also works where the
caller's own `$(git rev-parse ...)` is refused, as in a worktree-isolated Claude Code session.
Exactly one of `--sha` and `--ref` is required.

Run: `uv run scripts/ci_wait.py --ref HEAD`
     `uv run scripts/ci_wait.py --ref origin/master --repo OWNER/REPO --json`
     `uv run scripts/ci_wait.py --sha <full sha from a CI URL> --timeout 1800 --interval 30`
Exit 0 = every counted run for that sha succeeded (or was skipped; scheduled runs are not counted
unless `--event any`), 1 = at least one did not, 2 = could
not tell (bad sha, a ref that does not resolve, a bad flag value, no runs for it, a run awaiting
approval, a run stuck in the queue, every failed run refused by GitHub for account billing, timed out, `gh` failed, or the tool itself crashed). `--json` prints the envelope
`{ok, command, data: {state, summary, runs, sha, not_counted}, skipped}` on every exit, a usage
error included (`sha` is absent when the sha itself was refused; `not_counted`, the scheduled runs
the default filter left out of the last answered poll, is present only under the default filter
once a poll answered); `ok` is false exactly on exit 2, with `error` repeating the summary.
"""

import argparse
import itertools
import json
import math
import os
import re
import statistics
import subprocess
import sys
import time
import traceback
from datetime import datetime
from dataclasses import dataclass, replace
from collections.abc import Callable, Iterable, Sequence

from _cli_envelope import EnvelopeArgumentParser, emit

FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")

_FIELDS = "headSha,workflowName,status,conclusion,databaseId,event"
_TERMINAL = "completed"
#: Conclusions that do not fail a push. `skipped` is a workflow whose jobs were all if:-gated off.
_PASSING = frozenset({"success", "skipped"})
#: Longest a single `gh run list` may take. A half-open API connection otherwise blocks the whole
#: wait forever, and `--timeout` - checked only between polls - never gets its turn.
GH_CALL_TIMEOUT_S = 60.0
#: Shortest bound a single gh call is given, even when less of the wait is left. Bounding the last
#: call by the second left made it fail (`gh did not answer within 1s`) on a run still in
#: progress, and the wait ended reading as an API outage. The final call may overrun the deadline
#: by up to this much, which is the cheaper error.
GH_CALL_FLOOR_S = 10.0
#: Shortest `--interval` accepted. Every poll is one API request, and the wall-clock deadline keeps
#: polling for the whole wait, so `--interval 0.01` would call gh back to back for 25 minutes and
#: spend the hourly rate limit every other gh call on the machine shares. Refused, never raised
#: silently: a caller who typed 1 should learn it was not honoured.
MIN_INTERVAL_S = 5.0
#: gh's documented exit code for "authentication required" (measured on 2.92.0: no token and no
#: config gives 4 and tells you to run `gh auth login`). Local configuration, so it is fatal here
#: rather than retried. A REJECTED credential is exit 1, not this - see GhUnavailable.
_GH_EXIT_AUTH_REQUIRED = 4
#: A fork pull request's run waiting for a maintainer to approve it. Terminal for a waiter: no
#: amount of polling changes it, and it is not a failure of the code.
_AWAITING_APPROVAL = "action_required"
#: `--event` value meaning "do not filter on the event", scheduled runs included.
ANY_EVENT = "any"
#: Events left out when no `--event` is given. A scheduled run is not caused by the commit it runs
#: on, yet GitHub queues it on the default branch's head sha, so counting it would make a push's
#: verdict wait for (or fail on) a nightly job. Excluded client-side, because gh's `--event` takes
#: one event to KEEP and has no way to drop one.
_EXCLUDED_BY_DEFAULT = frozenset({"schedule"})
#: The run-level status of a run that MAY not have started. It is not proof: measured 2026-10-23,
#: run 39932914131 stayed `queued` for 15 minutes while three of its five jobs had completed and
#: one was in_progress, because one job was still waiting for a hosted runner. Only the run's own
#: jobs (:func:`gh_run_started`) say whether anything picked it up.
_QUEUED = "queued"
#: Job statuses that mean a runner took the job. `queued`, `waiting`, `pending` and `requested`
#: all mean it has not run yet.
_JOB_STARTED = frozenset({"in_progress", "completed"})
#: Job conclusions that mean the job failed. `cancelled` is left out: a fail-fast matrix cancels
#: the cells beside the one that failed, and that one already carries `failure`.
_JOB_FAILED = frozenset({"failure", "timed_out"})
#: `--repo` as gh takes it: OWNER/NAME, or HOST/OWNER/NAME for an enterprise host.
_REPO_NAME_RE = re.compile(r"(?:[A-Za-z0-9.-]+/)?[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")
_EXIT_CODES = {"success": 0, "failed": 1, "timeout": 2, "no-runs": 2, "error": 2,
               "pending-approval": 2, "stuck-queued": 2, "billing-blocked": 2}
#: GitHub's annotation on a job it refused to start for billing. Matched on the text because
#: nothing else separates it: the run concludes `failure` exactly like a real one, and the only
#: structural sign, zero steps, is shared with jobs cancelled before a runner took them.
_BILLING_RE = re.compile(r"recent account payments have failed|spending limit needs to be increased",
                         re.IGNORECASE)


class BadSha(ValueError):
    """The sha is not a full 40-character hex commit id - the trap this tool exists to close."""


class BadRef(ValueError):
    """`--ref` did not resolve to a commit here: unknown, not a commit, option-shaped, or no git."""


class BadRepo(ValueError):
    """`--repo` is neither OWNER/NAME nor a directory whose repository gh can name."""


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
        state: ``success``, ``failed``, ``billing-blocked``, ``pending``, ``pending-approval``,
            ``stuck-queued``, ``no-runs``, ``timeout`` or ``error``.
        summary: One human line naming the runs that decided it.
        runs: The rows the verdict was computed from.
    """

    state: str
    summary: str
    runs: tuple[dict[str, object], ...] = ()


@dataclass(frozen=True)
class JobTally:
    """What one run's jobs are doing, counted from `gh run view <id> --json jobs`.

    Attributes:
        done: Jobs that completed, whatever their conclusion.
        running: Jobs a runner is executing.
        queued: Jobs no runner has taken yet (``queued``, ``waiting``, ``pending``, ...).
        queued_names: The queued jobs by name, the matrix label included.
        running_names: The running jobs by name.
        failed_names: Completed jobs that concluded ``failure`` or ``timed_out``.
    """

    done: int
    running: int
    queued: int
    queued_names: tuple[str, ...] = ()
    running_names: tuple[str, ...] = ()
    failed_names: tuple[str, ...] = ()

    @property
    def total(self) -> int:
        return self.done + self.running + self.queued


def tally_jobs(jobs: Iterable[object]) -> JobTally:
    """Count a run's jobs by state. PURE.

    A run's own status cannot say this: it stays ``queued`` while one job waits for a runner and
    reads ``completed`` before every job has (both measured), so the jobs are the only place a
    waiter can see a runner backlog, an early failure, or a run that is not really finished.
    """
    done = running = 0
    queued: list[str] = []
    running_names: list[str] = []
    failed: list[str] = []
    for item in jobs:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or item.get("databaseId") or "?")
        status = item.get("status")
        if status == _TERMINAL:
            done += 1
            if item.get("conclusion") in _JOB_FAILED:
                failed.append(name)
        elif status == "in_progress":
            running += 1
            running_names.append(name)
        else:
            queued.append(name)
    return JobTally(done, running, len(queued), tuple(queued), tuple(running_names), tuple(failed))


def format_duration(seconds: float) -> str:
    """``45s``, ``24m51s``, ``1h02m``. PURE."""
    whole = int(round(seconds))
    if whole < 60:
        return f"{whole}s"
    minutes, secs = divmod(whole, 60)
    if minutes < 60:
        return f"{minutes}m{secs:02d}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h{minutes:02d}m"


def no_runs_hint(on_remote: bool | None) -> str:
    """The two live causes of a ``no-runs`` verdict, for the summary. PURE.

    Measured: a bare "no runs found" read as broken CI and invited a retry loop, when the push had
    gone to a branch the workflows' triggers exclude, or the sha was not on origin at all (a
    peer's rebase republished it under a new sha). ``on_remote`` is whether the local repository
    holds the sha on a remote-tracking branch; ``None`` when that could not be asked.
    """
    hint = ""
    if on_remote is False:
        hint += (" This sha is on no remote-tracking branch here (as of the last fetch): it may "
                 "never have been pushed, or a rebase republished it under a new sha - fetch and "
                 "compare.")
    return hint + (" If it was pushed, read the workflows' on: push: branches / paths filters: a "
                   "push to a branch no trigger names starts no run.")


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
            f"would spin to its deadline. Pass --ref HEAD and let the tool resolve it, or use "
            f"`git rev-parse HEAD`, never `--short`."
        )
    return candidate


def resolve_ref(ref: str, *, run: Callable[..., object] = subprocess.run) -> str:
    """The full sha the cwd's repository holds for ``ref``, or a refusal.

    The point of ``--ref``: a caller that names a ref never types a sha, so it cannot pad a short
    one or splice a guessed prefix onto a derived tail - the invented-identifier mistake that
    recurred nine times by hand. It also works where the caller's own `$(git rev-parse ...)`
    cannot: a worktree-isolated Claude Code session refuses that substitution, not this process.

    Args:
        ref: Anything ``git rev-parse`` accepts that names a commit (``HEAD``, ``origin/master``,
            a tag, ``HEAD~1``).
        run: Injected process runner, so the no-git path is testable.

    Returns:
        The lowercased 40-character sha.

    Raises:
        BadRef: empty or option-shaped (``--all`` would be read as a FLAG by rev-parse, so it is
            refused before git runs), not a commit in this repository (an unknown name, a tree,
            outside a repository), or git could not be run. Never falls back to the text itself.
    """
    if not ref or ref.startswith("-"):
        raise BadRef(f"{ref!r} is not a ref: it is empty or starts with '-', which git reads as an option")
    try:
        proc = run(["git", "rev-parse", "--verify", "-q", f"{ref}^{{commit}}"], capture_output=True,
                   text=True, encoding="utf-8", errors="replace", check=False)
    except OSError as exc:
        raise BadRef(f"could not run git to resolve {ref!r}: {exc}") from exc
    out = (getattr(proc, "stdout", "") or "").strip().lower()
    if getattr(proc, "returncode", 1) != 0 or not FULL_SHA_RE.match(out):
        raise BadRef(f"{ref!r} does not name a commit in this repository "
                     f"(git rev-parse --verify {ref}^{{commit}} gave no full sha)")
    return out


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


def sha_on_a_remote(sha: str, *, cwd: str | None = None,
                    run: Callable[..., object] = subprocess.run) -> bool | None:
    """Does a remote-tracking branch of the local repository contain ``sha``? ``None``: cannot tell.

    Answers from the last fetch, never the network, so it is evidence for a hint and never a
    verdict. ``None`` outside a work tree, without git, or for a sha git does not hold.
    """
    try:
        proc = run(["git", "for-each-ref", "--contains", sha, "--format=%(refname)", "refs/remotes"],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", check=False,
                   cwd=cwd)
    except OSError:
        return None
    if getattr(proc, "returncode", 1) != 0:
        return None
    return bool((getattr(proc, "stdout", "") or "").strip())


def verdict(runs: Sequence[dict[str, object]], *, event: str | None = None,
            workflow: str | None = None) -> Verdict:
    """Classify one poll's run list. PURE.

    Args:
        runs: The rows for ONE sha, as `gh run list --json` returns them.
        event: The event the runs were filtered to, named in a ``no-runs`` summary so the reader
            sees the filter that may have emptied the list. ``None`` is the default filter
            (every event except ``schedule``), ``any`` is no filter at all.

    Returns:
        ``no-runs`` when the list is empty - never ``success``, because "nothing matched" and
        "everything passed" are the same shape and only one of them is good news. ``failed``
        when any completed run's conclusion is anything but ``success`` or ``skipped``, a null
        conclusion included (a run cancelled at source completes with none, and that is not
        green) - even while other runs are still going, since a later run cannot rescue it; the
        summary then names those too. Otherwise ``pending`` while any run is not ``completed``.
        ``skipped`` is a workflow whose
        jobs were all ``if:``-gated off: nothing ran and nothing failed, so it does not fail the
        push. ``success`` only when every run completed successfully or was skipped AND at
        least one actually succeeded - a push where everything was skipped tested nothing, so
        it is reported ``failed`` rather than green. ``pending-approval`` when the only runs that
        did not pass are ``action_required`` (awaiting a maintainer's approval): a real failure
        beside one still reads ``failed``.
    """
    if not runs and workflow is not None:
        return Verdict("no-runs", f"no runs of workflow {workflow!r} found for that sha (only that "
                                  f"workflow is counted)")
    if not runs:
        if event is None:
            excluded = ", ".join(sorted(_EXCLUDED_BY_DEFAULT))
            return Verdict("no-runs", f"no runs found for that sha ({excluded} runs are not "
                                      f"counted by default: pass --event any to see every run)")
        if event != ANY_EVENT:
            return Verdict("no-runs", f"no {event} runs found for that sha (runs of another event "
                                      f"are not counted: pass --event any to see every run)")
        return Verdict("no-runs", "no runs found for that sha")
    unfinished = [r for r in runs if r.get("status") != _TERMINAL]
    bad = [r for r in runs if r.get("status") == _TERMINAL and r.get("conclusion") not in _PASSING]
    failed = [r for r in bad if r.get("conclusion") != _AWAITING_APPROVAL]
    if failed:
        # Before the pending check: a completed run's failure is final, so waiting for the runs
        # still going only turned a certain red into a timeout (exit 2) at the deadline.
        still = f" (still going: {_named(unfinished, 'status')})" if unfinished else ""
        return Verdict("failed", _named(failed, "conclusion") + still, tuple(runs))
    if unfinished:
        return Verdict("pending", _named(unfinished, "status"), tuple(runs))
    if bad:
        return Verdict("pending-approval", _named(bad, "conclusion")
                       + " (awaiting a maintainer's approval; no wait resolves it)", tuple(runs))
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
    event: str | None = None,
    deadline_polls: int | None = None,
    sleep: Callable[[float], None],
    interval_s: float = 30.0,
    appear_grace_s: float = 120.0,
    error_grace_s: float = 300.0,
    settle_s: float = 20.0,
    queued_grace_s: float = 900.0,
    report: Callable[[str], None] = lambda _m: None,
    deadline_s: float | None = None,
    clock: Callable[[], float] | None = None,
    run_started: Callable[[object], bool | None] | None = None,
    run_jobs: Callable[[object], list[dict[str, object]] | None] | None = None,
    fail_on_failed_job: bool = False,
    workflow: str | None = None,
    run_billing_blocked: Callable[[object], bool | None] | None = None,
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
    and running out of deadline mid-confirmation reports the green, never a timeout - with the
    summary saying it was not confirmed, or that the deadline cut the settle short.

    A run that sits ``queued`` for ``queued_grace_s`` while every other run is terminal ends the
    wait as ``stuck-queued`` (:func:`_stuck_queued`): no deadline helps a run no runner will take,
    and waiting it out reads as "CI is slow" for the whole timeout. Each run's queued time is its
    current streak, restarted whenever it leaves ``queued``, and the check waits while any run is
    still working, so a failure there still ends the wait as ``failed`` (any completed run that
    failed does, before this check is reached). A run's
    ``queued`` status alone is not that verdict: once the grace is spent, ``run_started`` is asked
    about each queued run, and a run with a started job - or one whose jobs could not be read -
    is waited for like any running one.

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
        queued_grace_s: How long a run may stay ``queued``, with nothing else still going, before
            the wait reports ``stuck-queued``. ``0`` disables the check.
        report: Where a per-poll progress line goes.
        event: The event ``fetch`` filters to, so a ``no-runs`` verdict can name the filter.
        deadline_s: A wall-clock bound on the whole wait, checked after every poll. A sleep is
            cut to the time left, so the last poll lands on the deadline instead of an interval
            past it. ``None`` leaves only ``deadline_polls``.
        clock: Returns the current time in seconds; see above for the default.
        run_started: Given a run id, whether any of its jobs has started (``True``), none has
            (``False``), or it could not be told (``None``). Asked only for a run already queued
            past the grace. ``None`` here keeps the run-status-only check.
        run_jobs: Given a run id, its jobs (``None`` when they could not be read). With it,
            every pending poll names each unfinished run's job counts, its queued jobs with how
            long each has been queued, and any job already failed; and a run that reads
            ``completed`` / ``success`` while a job is still queued or running is waited for,
            never reported green. A job list that cannot be read keeps the run-level answer.
        fail_on_failed_job: End the wait as ``failed`` as soon as a completed job of a run still
            going concluded ``failure`` or ``timed_out``. Off by default: a job marked
            ``continue-on-error`` fails without failing its run, and the jobs API does not say
            which jobs carry it.
        workflow: The workflow ``fetch`` filters to, named in a ``no-runs`` summary.
        run_billing_blocked: Given a run id, whether GitHub refused to start its jobs for
            billing (``True``), did not (``False``), or it could not be told (``None``). Asked
            for every failed run once the verdict is ``failed``; only when EVERY one answers
            ``True`` is the verdict ``billing-blocked`` instead. ``None`` here skips the check.

    Returns:
        The terminal verdict: ``success``, ``failed``, ``billing-blocked``, ``pending-approval``,
        ``stuck-queued``, ``no-runs``, ``timeout`` or ``error``.

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
    green_since = 0.0
    last_success: Verdict | None = None
    queued_since: dict[tuple[object, object], float] = {}
    job_queued_since: dict[tuple[object, str], float] = {}
    answered = False
    last_rows: Sequence[dict[str, object]] = ()

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
        answered = True
        last_rows = rows
        _track_queued(queued_since, rows, timer.now())
        current = verdict(rows, event=event, workflow=workflow)
        last_summary = current.summary
        if current.state == "no-runs":
            empty_since = timer.now() if empty_since is None else empty_since
            if timer.now() - empty_since >= appear_grace_s:
                return current
            report(f"{label(poll)}: no runs yet for that sha")
        elif current.state == "success" and run_jobs is not None and (
                unfinished_jobs := _jobs_not_finished(rows, run_jobs)):
            # GitHub can report a run completed/success while its jobs endpoint still shows jobs
            # queued or running (measured, 9 of 18). That is not a green to confirm yet.
            empty_since = None
            settled = None
            last_success = None
            last_summary = f"{current.summary}; {unfinished_jobs}"
            report(f"{label(poll)}: {last_summary}")
        elif current.state == "success":
            empty_since = None
            last_success = current
            seen = frozenset(_run_key(r) for r in rows)
            if settle_s <= 0:
                return current
            if settled == seen:
                return _cut_settle_said(current, timer.now() - green_since, settle_s)
            report(f"{label(poll)}: {current.summary}; confirming no run for "
                   f"this sha is still being created")
            settled = seen
            green_since = timer.now()
            if not may_poll_again(poll):
                break
            pause(settle_s)
            continue
        elif current.state == "failed":
            return _billing_blocked(current, run_billing_blocked)
        elif current.state != "pending":
            return current
        else:
            empty_since = None
            settled = None
            last_success = None
            stuck = _stuck_queued(rows, queued_since, timer.now(), queued_grace_s, run_started)
            if stuck is not None:
                return stuck
            note, failed_jobs = ("", ()) if run_jobs is None else _job_progress(
                rows, run_jobs, job_queued_since, timer.now())
            if fail_on_failed_job and failed_jobs:
                return Verdict("failed", f"{current.summary}; job(s) already failed while the run "
                                         f"is still going: {', '.join(failed_jobs)}", tuple(rows))
            last_summary = current.summary + note
            report(f"{label(poll)}: {last_summary}")
        if not may_poll_again(poll):
            break
        pause(interval_s)
    # The deadline, reported from what the last ANSWERED poll saw. Re-fetching here to describe
    # the timeout cost an extra request that could itself fail, turning a plain timeout into an
    # error about the API - a report naming the wrong system entirely.
    # Confirming must never turn a green into a timeout. If every run was terminal and successful
    # and only the confirming poll ran out of deadline, report what was actually seen - which is
    # exactly what this function returned before the confirmation existed.
    # It still says so: a green nobody re-polled must not read like a confirmed one.
    if last_success is not None:
        return replace(last_success, summary=last_success.summary
                       + " (not confirmed: the deadline ended before the --settle re-poll)")
    if errors_seen and answered:
        # The deadline, not the error budget, ended this wait: the calls failing at the end were
        # often bounded by the seconds left, so the verdict is the timeout the last answer shows.
        return Verdict("timeout", f"{last_summary} (deadline reached while gh was failing: "
                                  f"{errors_seen} call(s), last: {last_error})", tuple(last_rows))
    if errors_seen:
        return _gh_gave_up(errors_seen, last_error)
    return Verdict("timeout", last_summary, tuple(last_rows))


def _job_progress(rows: Sequence[dict[str, object]],
                  run_jobs: Callable[[object], list[dict[str, object]] | None],
                  queued_since: dict[tuple[object, str], float],
                  now: float) -> tuple[str, tuple[str, ...]]:
    """`` [CI: 15/16 jobs done, 0 running, 1 queued (test (macos-latest) queued 12m00s)]``.

    Returns the note and the names of jobs already failed. Read for every unfinished run, because
    the run status alone made a single job waiting for a macOS runner read as a whole run stuck
    (measured: 35+ polls of `CI=queued` with 15 of 16 jobs green). Each job's queued time is
    counted from the first poll that saw it queued, keyed by run and job name.
    """
    parts: list[str] = []
    failed: list[str] = []
    seen: set[tuple[object, str]] = set()
    for row in rows:
        if row.get("status") == _TERMINAL:
            continue
        run_id = row.get("databaseId")
        jobs = run_jobs(run_id)
        if jobs is None:
            parts.append(f"{row.get('workflowName')}: jobs not read")
            continue
        tally = tally_jobs(jobs)
        waits = []
        for name in tally.queued_names:
            key = (run_id, name)
            seen.add(key)
            since = queued_since.setdefault(key, now)
            waits.append(f"{name} queued {format_duration(now - since)}")
        part = (f"{row.get('workflowName')}: {tally.done}/{tally.total} jobs done, "
                f"{tally.running} running, {tally.queued} queued")
        if waits:
            part += f" ({', '.join(waits)})"
        if tally.failed_names:
            part += f", failed: {', '.join(tally.failed_names)}"
            failed.extend(tally.failed_names)
        parts.append(part)
    for key in [k for k in queued_since if k not in seen]:
        del queued_since[key]
    return (f" [{'; '.join(parts)}]" if parts else ""), tuple(failed)


def _jobs_not_finished(rows: Sequence[dict[str, object]],
                       run_jobs: Callable[[object], list[dict[str, object]] | None]) -> str:
    """Name each run that reads finished while a job of it is still queued or running, else ``""``.

    A job list that cannot be read is not evidence either way, so it leaves the run-level answer.
    """
    parts = []
    for row in rows:
        jobs = run_jobs(row.get("databaseId"))
        if jobs is None:
            continue
        tally = tally_jobs(jobs)
        if tally.running or tally.queued:
            names = ", ".join((*tally.running_names, *tally.queued_names))
            parts.append(f"{row.get('workflowName')} reads {row.get('conclusion')} but "
                         f"{tally.running + tally.queued} of {tally.total} jobs not finished: {names}")
    return "; ".join(parts)


def _billing_blocked(failed: Verdict,
                     ask: Callable[[object], bool | None] | None) -> Verdict:
    """``failed`` as it is, or ``billing-blocked`` when GitHub refused to start every failed run.

    A billing block reads as an ordinary failure in the run list, so without this the reader opens
    each job log looking for a code defect in jobs that never ran, and a watcher demanding a green
    can never be satisfied. Every failed run must answer ``True``: one real failure beside a
    blocked run is still a failure the push owns, and an unknown answer never upgrades a verdict.
    """
    if ask is None:
        return failed
    bad = [r for r in failed.runs if r.get("status") == _TERMINAL
           and r.get("conclusion") not in _PASSING and r.get("conclusion") != _AWAITING_APPROVAL]
    if not bad or not all(ask(r.get("databaseId")) is True for r in bad):
        return failed
    ids = ", ".join(str(r.get("databaseId")) for r in bad)
    return Verdict("billing-blocked",
                   f"no job ran: GitHub refused to start run(s) {ids} for account billing "
                   f"(recent account payments have failed or the spending limit is reached). No "
                   f"wait or retry fixes it; once billing is fixed, re-run with `gh run rerun <id>`",
                   failed.runs)


def _track_queued(since: dict[tuple[object, object], float], rows: Sequence[dict[str, object]],
                  now: float) -> None:
    """Record when each run's current ``queued`` streak began; forget a run that left ``queued``.

    Keyed like :func:`_run_key`. A run that went ``in_progress`` and back to ``queued`` starts a new
    streak, so two short waits for a runner never add up to one long one.
    """
    queued = {_run_key(r) for r in rows if r.get("status") == _QUEUED}
    for key in list(since):
        if key not in queued:
            del since[key]
    for key in queued:
        since.setdefault(key, now)


def _stuck_queued(rows: Sequence[dict[str, object]], since: dict[tuple[object, object], float],
                  now: float, grace_s: float,
                  run_started: Callable[[object], bool | None] | None = None) -> Verdict | None:
    """``stuck-queued`` when every unfinished run has been queued for ``grace_s``, else None.

    Only when NOTHING else is still going: a run in progress beside the stuck one is an outcome
    still to come, and reporting before it lands would hide a failure. The summary names each stuck
    run by id, so the caller can look at it or cancel it, and the terminal runs by conclusion; a
    run of the same workflow on the sha that already SUCCEEDED is named as the likely original,
    because a duplicate trigger is the measured cause. Without one, no cause is claimed.

    ``run_started`` is asked last, and only once the grace is spent, because the run status lies:
    a run stays ``queued`` while any ONE job waits for a runner, even with its other jobs done.
    Anything but a definite ``False`` keeps the wait open - a run whose jobs could not be read
    is not proven stuck, and the deadline still bounds it.
    """
    if grace_s <= 0:
        return None
    unfinished = [r for r in rows if r.get("status") != _TERMINAL]
    if not unfinished or any(r.get("status") != _QUEUED for r in unfinished):
        return None
    if any(now - since.get(_run_key(r), now) < grace_s for r in unfinished):
        return None
    if run_started is not None and any(run_started(r.get("databaseId")) is not False
                                       for r in unfinished):
        return None
    parts = []
    for row in unfinished:
        line = (f"run {row.get('databaseId')} ({row.get('workflowName')}) has been queued for "
                f"{now - since[_run_key(row)]:.0f}s with no runner starting it")
        twin = next((r for r in rows if r.get("workflowName") == row.get("workflowName")
                     and r.get("status") == _TERMINAL and r.get("conclusion") == "success"), None)
        if twin is not None:
            line += (f"; run {twin.get('databaseId')} of the same workflow on this sha already "
                     f"succeeded, so this is likely a duplicate trigger")
        parts.append(line)
    finished = [r for r in rows if r.get("status") == _TERMINAL]
    if finished:
        parts.append("the other runs: " + _named(finished, "conclusion"))
    return Verdict("stuck-queued", "; ".join(parts), tuple(rows))


def _cut_settle_said(confirmed: Verdict, waited: float, settle_s: float) -> Verdict:
    """The confirmed green, saying so when the deadline cut the settle short.

    Every sleep is cut to the time left, the settle included, so a green first seen near the
    deadline is re-polled sooner than ``--settle`` asked. That is still reported as success - a
    confirmation is never another way to fail - but a run created in the part of the settle that
    never happened is exactly what the settle exists to catch, so the summary names the shortfall.
    """
    if waited >= settle_s:
        return confirmed
    return replace(confirmed, summary=f"{confirmed.summary} (confirmed after {waited:.0f}s, not the "
                                      f"full {settle_s:g}s --settle: the deadline cut it short)")


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
    event: str | None = None,
    on_not_counted: Callable[[int], None] | None = None,
    workflow: str | None = None,
) -> list[dict[str, object]]:
    """Fetch the runs whose ``headSha`` is ``sha``: asked for SERVER-side, checked client-side.

    `--commit` is passed so the API returns this sha's runs only. Without it, `--limit` bounds a
    window over EVERY recent run, and on a busy repo 30 newer runs of other shas push this sha's
    older runs out of it - a failing CI run vanished that way while a green CodeQL run remained,
    and the push read as green. `--commit` needs the full sha and fails silently without it; this
    tool has already refused a short one. The client-side filter stays as a second check.

    ``event`` (anything but ``None`` or ``any``) is passed as `--event` and checked client-side on
    the rows that carry the field. ``None`` - the default - asks for every event and drops the
    rows whose event is in :data:`_EXCLUDED_BY_DEFAULT` (``schedule``) client-side; ``any`` keeps
    every row.

    ``on_not_counted`` is handed, once per answered call, how many of this sha's rows the event
    filter dropped. A callback rather than a second return value keeps the fetch shape that
    :func:`wait_for` and every injected fake share; the caller needs the number only to SAY a run
    was left out, never to decide the verdict.

    Raises:
        GhFailed: `gh` exited non-zero, did not answer within ``timeout_s``, or returned
            something that is not a JSON list. The caller may retry this; a bad minute at the
            API arrives here.
        GhUnavailable: `gh` could not be spawned at all - not installed, or not executable.
    """
    argv = ["gh", "run", "list", "--commit", sha, "--json", _FIELDS, "--limit", str(limit)]
    if repo:
        argv += ["--repo", repo]
    filtered = event not in (None, ANY_EVENT)
    if filtered:
        argv += ["--event", str(event)]
    if workflow:
        # Server-side only: gh takes a workflow NAME or its FILE name, and the rows carry only the
        # name, so a client-side check would drop every row asked for by file name.
        argv += ["--workflow", workflow]
    rows = _gh_json(argv, timeout_s)
    if not isinstance(rows, list):
        raise GhFailed(f"gh returned {type(rows).__name__}, not a list")
    same_sha = [r for r in rows if isinstance(r, dict) and r.get("headSha") == sha]
    kept = [r for r in same_sha if _event_counts(r, event)]
    if on_not_counted is not None:
        on_not_counted(len(same_sha) - len(kept))
    return kept


def gh_run(run_id: object, *, repo: str | None = None,
           timeout_s: float = GH_CALL_TIMEOUT_S) -> dict[str, object]:
    """Re-read ONE run by its id with `gh run view`, in the same row shape `gh_runs` returns.

    The by-id read is what :func:`keep_seen_runs` falls back on when the sha-filtered listing
    drops a run it already returned: a run's own endpoint answers from the run itself, not from
    the index the filtered listing is served from.

    Raises:
        GhFailed: as :func:`gh_runs`, and also for a run gh cannot read - a deleted run answers
            HTTP 404 with exit 1. Raised rather than dropped, because dropping a run the wait has
            already seen is the defect the caller exists to close.
        GhUnavailable: as :func:`gh_runs`.
    """
    argv = ["gh", "run", "view", str(run_id), "--json", _FIELDS]
    if repo:
        argv += ["--repo", repo]
    row = _gh_json(argv, timeout_s)
    if not isinstance(row, dict):
        raise GhFailed(f"gh run view {run_id} returned {type(row).__name__}, not one run")
    return row


def gh_run_started(run_id: object, *, repo: str | None = None,
                   timeout_s: float = GH_CALL_TIMEOUT_S) -> bool | None:
    """Whether any job of run ``run_id`` has started, read from the run's own jobs.

    The run-level status cannot answer this: a run stays ``queued`` while one job waits for a
    runner, however many of its other jobs already ran. ``None`` when gh could not be asked or
    answered something that is not a job list - an unknown, which the stuck check reads as
    "keep waiting", never as "nothing started".
    """
    argv = ["gh", "run", "view", str(run_id), "--json", "jobs"]
    if repo:
        argv += ["--repo", repo]
    try:
        answer = _gh_json(argv, timeout_s)
    except (GhFailed, GhUnavailable):
        return None
    jobs = answer.get("jobs") if isinstance(answer, dict) else None
    if not isinstance(jobs, list):
        return None
    return any(isinstance(j, dict) and j.get("status") in _JOB_STARTED for j in jobs)


def gh_run_jobs(run_id: object, *, repo: str | None = None,
                timeout_s: float = GH_CALL_TIMEOUT_S) -> list[dict[str, object]] | None:
    """The jobs of run ``run_id`` (`gh run view <id> --json jobs`); ``None`` when not readable."""
    argv = ["gh", "run", "view", str(run_id), "--json", "jobs"]
    if repo:
        argv += ["--repo", repo]
    try:
        answer = _gh_json(argv, timeout_s)
    except (GhFailed, GhUnavailable):
        return None
    jobs = answer.get("jobs") if isinstance(answer, dict) else None
    if not isinstance(jobs, list):
        return None
    return [j for j in jobs if isinstance(j, dict)]


def gh_typical_duration(workflow: str, *, repo: str | None = None,
                        timeout_s: float = GH_CALL_FLOOR_S, sample: int = 5) -> float | None:
    """Median wall time of ``workflow``'s last ``sample`` successful runs, in seconds; else None.

    Asked only once a wait has timed out, to say how long the unfinished workflow normally takes:
    measured, a default deadline of 25 minutes was seconds short of a 24m51s CI run, and a
    timeout that names the usual duration says what --timeout to pass next. `updatedAt` minus
    `createdAt` includes queueing, which is what a waiter sits through too.
    """
    argv = ["gh", "run", "list", "--workflow", workflow, "--status", "success",
            "--limit", str(sample), "--json", "createdAt,updatedAt"]
    if repo:
        argv += ["--repo", repo]
    try:
        rows = _gh_json(argv, timeout_s)
    except (GhFailed, GhUnavailable):
        return None
    spans = []
    for row in rows if isinstance(rows, list) else []:
        try:
            start = datetime.fromisoformat(str(row["createdAt"]))
            end = datetime.fromisoformat(str(row["updatedAt"]))
        except (KeyError, TypeError, ValueError):
            continue
        spans.append((end - start).total_seconds())
    return statistics.median(spans) if spans else None


def gh_run_billing_blocked(run_id: object, *, repo: str | None = None,
                           timeout_s: float = GH_CALL_TIMEOUT_S,
                           bound: Callable[[], float | None] | None = None) -> bool | None:
    """Whether GitHub refused to start run ``run_id`` for billing, read from its jobs.

    Blocked means every job ran ZERO steps and at least one carries the billing annotation
    (:data:`_BILLING_RE`). A job with steps answers ``False`` at once, without the annotation
    read; zero steps for another reason (a cancellation) answers ``False`` too. ``None`` when gh
    could not be asked or answered something unexpected - an unknown, which never turns a failure
    into a billing block.

    This makes one call per job, so ``bound``, when given, is asked before EACH call for its
    timeout (``None``: no time left, and the answer is unknown); a single ``timeout_s`` for all of
    them would let a stalled API hold the wait that many times past its deadline.
    """
    def ask(argv: list[str]) -> object:
        limit = timeout_s if bound is None else bound()
        if limit is None:
            raise GhFailed("no time left before the deadline")
        return _gh_json(argv, limit)

    argv = ["gh", "run", "view", str(run_id), "--json", "jobs"]
    if repo:
        argv += ["--repo", repo]
    try:
        answer = ask(argv)
    except (GhFailed, GhUnavailable):
        return None
    jobs = answer.get("jobs") if isinstance(answer, dict) else None
    if not isinstance(jobs, list) or not jobs:
        return None
    if any(not isinstance(j, dict) or j.get("steps") for j in jobs):
        return False
    gh_api, base = _gh_api_target(repo)
    for job in jobs:
        try:
            notes = ask([*gh_api, f"{base}/check-runs/{job.get('databaseId')}/annotations"])
        except (GhFailed, GhUnavailable):
            return None
        if isinstance(notes, list) and any(isinstance(n, dict) and _BILLING_RE.search(
                str(n.get("message") or "")) for n in notes):
            return True
    return False


def _gh_api_target(repo: str | None) -> tuple[list[str], str]:
    """(the `gh api` argv prefix, the ``repos/OWNER/NAME`` path) for ``repo``. PURE.

    `gh api` takes the host as `--hostname`, never inside the path, so the HOST of an enterprise
    ``HOST/OWNER/NAME`` (which `--repo` accepts) is split off: left in, the request went to
    github.com as ``repos/HOST/OWNER/NAME/...`` and every billing check answered unknown.
    ``{owner}/{repo}`` is gh's own placeholder for the cwd's repository.
    """
    if not repo:
        return ["gh", "api"], "repos/{owner}/{repo}"
    parts = repo.split("/")
    if len(parts) == 3:
        return ["gh", "api", "--hostname", parts[0]], f"repos/{parts[1]}/{parts[2]}"
    return ["gh", "api"], f"repos/{repo}"


def keep_seen_runs(
    fetch: Callable[[], list[dict[str, object]]],
    fetch_one: Callable[[object], dict[str, object]],
    *,
    report: Callable[[str], None] = lambda _m: None,
) -> Callable[[], list[dict[str, object]]]:
    """Wrap ``fetch`` so a run it returned once is never lost when a later listing omits it.

    Measured 2026-10-22: `gh run list --commit <sha>` listed a ci run as in_progress for 27
    polls, then answered [] around the moment it completed, and kept answering [] for minutes,
    while `gh run view <id>` and the unfiltered runs API both had it as completed success. The
    wait read the empty listing as "this sha has no runs" and exited 2. Worse is a PARTIAL drop:
    the verdict is computed over whatever is still listed, so a failing run that drops out beside
    a listed success reads as a green push. A run that was listed is a fact; its absence from a
    later listing is the index lagging, so each such run is re-read by id with ``fetch_one`` and
    put back. A run the listing still carries is never re-read, so a normal poll costs no extra
    call, and a sha never seen with runs keeps the appear-grace path untouched.

    Keyed on ``databaseId``: a row without one cannot be re-read, so it is not remembered.
    """
    seen: dict[object, dict[str, object]] = {}

    def fetch_with_seen() -> list[dict[str, object]]:
        rows = list(fetch())
        listed = {row.get("databaseId") for row in rows}
        missing = [run_id for run_id in seen if run_id not in listed]
        if missing:
            report(f"{len(missing)} run(s) dropped from the listing, re-read by id: "
                   f"{', '.join(str(run_id) for run_id in missing)}")
            rows += [fetch_one(run_id) for run_id in missing]
        for row in rows:
            if row.get("databaseId") is not None:
                seen[row["databaseId"]] = row
        return rows

    return fetch_with_seen


def _gh_json(argv: list[str], timeout_s: float) -> object:
    """Run one gh command and parse its JSON, mapping every failure onto the retry contract."""
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
        return json.loads(proc.stdout)
    except ValueError as exc:
        raise GhFailed(f"gh returned unparseable output: {exc}") from exc


def _event_counts(row: dict[str, object], event: str | None) -> bool:
    """Does this row's event pass the filter? A row without the field passes every filter."""
    if event == ANY_EVENT:
        return True
    if event is None:
        return row.get("event") not in _EXCLUDED_BY_DEFAULT
    return row.get("event", event) == event


def resolve_repo(*, timeout_s: float = GH_CALL_TIMEOUT_S, cwd: str | None = None) -> str:
    """OWNER/NAME of the repository at ``cwd`` (default: the cwd), as gh resolves it, asked ONCE.

    Raises:
        GhFailed: gh answered without a repository (a non-zero exit, or an empty answer).
        GhUnavailable: gh could not be spawned, or is not logged in.
    """
    argv = ["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"]
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", check=False, timeout=timeout_s, cwd=cwd)
    except subprocess.TimeoutExpired as exc:
        raise GhFailed(f"gh repo view did not answer within {timeout_s:g}s") from exc
    except OSError as exc:
        raise GhUnavailable(f"could not run gh: {exc}") from exc
    if proc.returncode == _GH_EXIT_AUTH_REQUIRED:
        raise GhUnavailable(f"gh is not authenticated: {(proc.stderr or '').strip()}")
    name = (proc.stdout or "").strip()
    if proc.returncode != 0 or not name:
        raise GhFailed(f"gh repo view exited {proc.returncode}: {(proc.stderr or '').strip()}")
    return name


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


def _interval(text: str) -> float:
    """A positive duration of at least :data:`MIN_INTERVAL_S` - see there for why."""
    value = _seconds(allow_zero=False)(text)
    if value < MIN_INTERVAL_S:
        raise argparse.ArgumentTypeError(
            f"{text!r} is below the {MIN_INTERVAL_S:g}-second floor: every poll is one gh API "
            f"request, so a shorter interval polls back to back until the deadline")
    return value


def _positive_int(text: str) -> int:
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a whole number: {text!r}") from None
    if value < 1:
        raise argparse.ArgumentTypeError(f"{text!r} must be at least 1")
    return value


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = EnvelopeArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
                                    envelope_command="ci_wait")
    positive, non_negative = _seconds(allow_zero=False), _seconds(allow_zero=True)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--sha", help="the FULL 40-character commit sha (git rev-parse HEAD)")
    target.add_argument("--ref", help="a ref this tool resolves to its sha in the cwd's repository "
                                      "(HEAD, origin/master, a tag), so no sha is typed")
    parser.add_argument("--repo", default=None,
                        help="OWNER/NAME (or HOST/OWNER/NAME), or a local checkout directory whose "
                             "repository gh resolves; default is the cwd's repo. Anything else is "
                             "refused before the first poll")
    parser.add_argument("--timeout", type=positive, default=3600.0,
                        help="seconds to wait (default 3600); a timeout names how long each "
                             "unfinished workflow usually takes")
    parser.add_argument("--workflow", default=None,
                        help="count only runs of this workflow (its name or file name, asked for "
                             "server-side), e.g. the release workflow after a tag push")
    parser.add_argument("--fail-on-failed-job", action="store_true",
                        help="end the wait as failed (exit 1) once a completed job of a run still "
                             "going concluded failure or timed_out. Off by default: a job marked "
                             "continue-on-error fails without failing its run")
    parser.add_argument("--interval", type=_interval, default=30.0,
                        help=f"seconds between polls (default 30, at least {MIN_INTERVAL_S:g}: each "
                             "poll is one API request)")
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
    parser.add_argument(
        "--queued-grace", type=non_negative, default=900.0,
        help="seconds a run may stay queued, with none of its jobs started and nothing else on the "
             "sha still going, before the wait reports stuck-queued (exit 2) naming it (default "
             "900; 0 disables). Counted from the first poll that saw the run queued, restarting "
             "when it leaves queued. No deadline helps a run no runner will take, such as a "
             "duplicate workflow_run trigger",
    )
    parser.add_argument(
        "--event", default=None,
        help="count only runs of this event, e.g. push or pull_request ('any' counts every run). "
             "Default: every event except schedule - a nightly run GitHub queues on the same "
             "head sha otherwise holds a push's verdict open or fails it",
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


def _target_sha(args: argparse.Namespace) -> str:
    """The sha to watch: ``--ref`` resolved here, or ``--sha`` through the format guard.

    Raises:
        BadRef: ``--ref`` did not resolve.
        BadSha: ``--sha`` is not a full sha.
    """
    if args.ref is not None:
        sha = resolve_ref(args.ref)
        print(f"resolved {args.ref} to {sha}", file=sys.stderr, flush=True)
        return sha
    sha = require_full_sha(args.sha)
    # WARN, never refuse. git not holding the sha is strong evidence of a caller bug, but it is not
    # proof: watching a sha you have not fetched (someone else's push, a sha from a notification, a
    # shallow clone) is legitimate, and `gh` is the authority on whether runs exist - not this
    # checkout. Refusing here would turn those into a hard error that reads as "no such commit".
    # Only asked when the sha is meant to be THIS repo's: with --repo the runs belong elsewhere.
    if args.repo is None and sha_is_known_locally(sha) is False:
        print(
            f"warning: {sha} is not a commit in this repository. If you did not fetch it, that is "
            f"expected; if you completed it from a short one, it will match no run and this wait "
            f"will end in 'no-runs'. Let the tool derive it: --ref HEAD.",
            file=sys.stderr,
        )
    return sha


def _run(args: argparse.Namespace) -> int:
    try:
        sha = _target_sha(args)
    except (BadRef, BadSha) as exc:
        return _emit(Verdict("error", str(exc)), as_json=args.json)
    deadline = _Deadline(args.timeout)
    try:
        repo, local_dir = _repo_target(args.repo, args.timeout)
    except (BadRepo, GhFailed, GhUnavailable) as exc:
        return _emit(Verdict("error", str(exc)), as_json=args.json, sha=sha)
    # One entry per ANSWERED poll, so the last one belongs to the rows the verdict was computed
    # from. Collected only under the default filter: that is the filter that drops runs silently.
    not_counted: list[int] = []

    def fetch_listing() -> list[dict[str, object]]:
        return gh_runs(
            sha, repo=repo, limit=args.limit, timeout_s=deadline.listing_bound(),
            event=args.event, on_not_counted=not_counted.append if args.event is None else None,
            workflow=args.workflow,
        )

    def fetch_one(run_id: object) -> dict[str, object]:
        bound = deadline.side_bound()
        if bound is None:
            raise GhFailed(f"no time left before the deadline to re-read run {run_id}")
        return gh_run(run_id, repo=repo, timeout_s=bound)

    def side_call[T](lookup: Callable[..., T]) -> Callable[[object], T | None]:
        """``lookup`` for one run id, bounded by what is left of the deadline's floor window."""
        def ask(run_id: object) -> T | None:
            bound = deadline.side_bound()
            return None if bound is None else lookup(run_id, repo=repo, timeout_s=bound)
        return ask

    fetch = keep_seen_runs(
        fetch_listing, fetch_one, report=lambda line: print(line, file=sys.stderr, flush=True))
    try:
        result = wait_for(
            fetch,
            sleep=time.sleep,
            interval_s=args.interval,
            appear_grace_s=args.appear_grace,
            error_grace_s=args.error_grace,
            settle_s=args.settle,
            queued_grace_s=args.queued_grace,
            report=lambda line: print(line, file=sys.stderr, flush=True),
            # What is left, not args.timeout: the repo lookup above already spent some of it, and
            # the side calls are bounded by the same end.
            deadline_s=max(0.0, deadline.left()),
            clock=time.monotonic,
            event=args.event,
            run_started=side_call(gh_run_started),
            run_jobs=side_call(gh_run_jobs),
            fail_on_failed_job=args.fail_on_failed_job,
            workflow=args.workflow,
            run_billing_blocked=lambda run_id: gh_run_billing_blocked(
                run_id, repo=repo, bound=deadline.side_bound),
        )
    except (GhFailed, GhUnavailable) as exc:
        return _emit(Verdict("error", str(exc)), as_json=args.json, sha=sha)
    if result.state == "no-runs":
        on_remote = sha_on_a_remote(sha, cwd=local_dir) if args.repo is None or local_dir else None
        result = replace(result, summary=result.summary + no_runs_hint(on_remote))
    elif result.state == "timeout":
        result = replace(result, summary=result.summary
                         + _usual_durations(result.runs, repo, deadline.side_bound))
    return _emit(result, as_json=args.json, sha=sha,
                 not_counted=not_counted[-1] if not_counted else None)


class _Deadline:
    """The wall-clock end of the wait, and the bound each gh call gets from it.

    The poll listing gets at least :data:`GH_CALL_FLOOR_S` (see there). Every OTHER call - each
    unfinished run's jobs, a queued run's start, a dropped run's re-read, each billing annotation,
    a timeout's history lookup - shares one window ending that floor past the deadline, and is not
    made once the window is spent. Bounding each of them by the floor separately let N stalled
    calls hold the wait N floors past the deadline (measured: three job reads, 20s over).
    ``time.monotonic`` is read at each call, never captured, so a test's clock reaches it.
    """

    def __init__(self, timeout_s: float) -> None:
        self._end = time.monotonic() + timeout_s

    def left(self) -> float:
        return self._end - time.monotonic()

    def listing_bound(self) -> float:
        return max(GH_CALL_FLOOR_S, min(GH_CALL_TIMEOUT_S, self.left()))

    def side_bound(self) -> float | None:
        window = self.left() + GH_CALL_FLOOR_S
        return min(GH_CALL_TIMEOUT_S, window) if window > 0 else None


def _repo_target(value: str | None, timeout_s: float) -> tuple[str | None, str | None]:
    """(the OWNER/NAME every poll names, the local directory it came from or None).

    A checkout PATH given as --repo made every gh poll fail and the wait ran to its deadline with
    no verdict (measured), so a directory is resolved to its repository here and anything that is
    neither OWNER/NAME nor a directory is refused before the first poll.

    Raises:
        BadRepo: the value is neither.
        GhFailed: gh could not name the repository of that directory.
        GhUnavailable: gh could not be run.
    """
    if value is None:
        return _resolve_repo_once(timeout_s), None
    expanded = os.path.expanduser(value)
    if os.path.isdir(expanded):
        bound = max(GH_CALL_FLOOR_S, min(GH_CALL_TIMEOUT_S, timeout_s))
        name = resolve_repo(timeout_s=bound, cwd=expanded)
        print(f"resolved --repo {value} to {name}", file=sys.stderr, flush=True)
        return name, expanded
    parts = value.split("/")
    if _REPO_NAME_RE.fullmatch(value) and not {".", ".."} & set(parts):
        return value, None
    raise BadRepo(f"--repo {value!r} is neither OWNER/NAME (HOST/OWNER/NAME) nor an existing "
                  f"directory; pass OWNER/NAME, or a checkout path, or run from inside the checkout")


def _usual_durations(runs: Sequence[dict[str, object]], repo: str | None,
                     bound: Callable[[], float | None]) -> str:
    """`` (ci usually takes 24m51s: the median of its recent successful runs)``, per unfinished
    workflow, or ``""`` when no history could be read. Each lookup is bounded by ``bound`` (the
    deadline's window, see :class:`_Deadline`); once it is spent the rest are not asked."""
    notes = []
    for name in dict.fromkeys(str(r.get("workflowName")) for r in runs
                              if r.get("status") != _TERMINAL and r.get("workflowName")):
        limit = bound()
        if limit is None:
            break
        typical = gh_typical_duration(name, repo=repo, timeout_s=min(GH_CALL_FLOOR_S, limit))
        if typical is not None:
            notes.append(f"{name} usually takes {format_duration(typical)}")
    if not notes:
        return ""
    return f" ({'; '.join(notes)}: the median of recent successful runs; raise --timeout above it)"


def _resolve_repo_once(timeout_s: float) -> str | None:
    """The cwd's repo, so every poll names it; None (polling from the cwd) when gh answered badly.

    A failed lookup falls back rather than ending the wait: it may be the same 502 weather the
    poll loop sits through, and polling from the cwd is what this tool did before the lookup.
    GhUnavailable propagates - no poll can succeed without gh either.
    """
    try:
        return resolve_repo(timeout_s=max(GH_CALL_FLOOR_S, min(GH_CALL_TIMEOUT_S, timeout_s)))
    except GhFailed as exc:
        print(f"warning: could not resolve the repository once ({exc}); polling from the "
              f"current directory, so removing it mid-wait fails the polls. Pass --repo OWNER/NAME.",
              file=sys.stderr)
        return None


def _emit(result: Verdict, *, as_json: bool, sha: str | None = None,
          not_counted: int | None = None) -> int:
    """Print the verdict and return its exit code; diagnostics to stderr, never into the data.

    ``sha`` is the commit that was watched, once known, so a ``--ref`` caller learns what it
    resolved to; it is absent when the sha itself was refused. ``not_counted`` is how many runs
    the default event filter left out of the last answered poll (``None``: not measured). JSON
    carries it as its own field and leaves ``summary`` as it was, so a consumer matching the
    summary is unaffected; the text line gets :func:`_not_counted_note` appended.
    """
    code = exit_code_for(result.state)
    if as_json:
        data: dict[str, object] = {"state": result.state, "summary": result.summary,
                                   "runs": list(result.runs)}
        if sha is not None:
            data["sha"] = sha
        if not_counted is not None:
            data["not_counted"] = not_counted
        emit(code, "ci_wait", data, error=result.summary if code == 2 else None, indent=None)
        return code
    summary = result.summary + _not_counted_note(not_counted, result.state)
    if code == 0:
        print(summary)
    else:
        print(f"{result.state}: {summary}", file=sys.stderr)
    return code


def _not_counted_note(not_counted: int | None, state: str) -> str:
    """`` (N scheduled run(s) not counted; --event any counts it/them)``, or ``""``. PURE.

    Measured: "CodeQL=success CI=success" and exit 0, while a scheduled CI run on the same sha was
    still queued, read as the tool missing a run, because nothing said one was left out on purpose.
    Skipped for ``no-runs``, whose summary already says scheduled runs are not counted, and for
    ``error``, whose summary is about gh or a crash rather than about the runs.
    """
    if not not_counted or state in ("no-runs", "error"):
        return ""
    if not_counted == 1:
        return " (1 scheduled run not counted; --event any counts it)"
    return f" ({not_counted} scheduled runs not counted; --event any counts them)"


if __name__ == "__main__":
    sys.exit(main())
