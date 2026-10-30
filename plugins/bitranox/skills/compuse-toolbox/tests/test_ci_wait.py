"""The CI waiter: it must refuse a short sha, and an empty match must be an ERROR, never a not-yet.

Both are the same bug wearing two hats. A sha shorter than 40 characters matches nothing - in
`gh run list --commit` and equally in a client-side `select(.headSha==...)` - and a "are they all
terminal yet?" test over an empty list is vacuous, so the loop spins to its deadline looking busy.
"""

import inspect
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

import ci_wait

#: The real lookups, kept before the autouse stub below replaces them, for the tests that exercise
#: them.
REAL_RESOLVE_REPO = getattr(ci_wait, "resolve_repo", None)
REAL_GH_RUN_JOBS = getattr(ci_wait, "gh_run_jobs", None)
REAL_GH_TYPICAL_DURATION = getattr(ci_wait, "gh_typical_duration", None)
REAL_SHA_ON_A_REMOTE = getattr(ci_wait, "sha_on_a_remote", None)
REAL_BILLING_BLOCKED = getattr(ci_wait, "gh_run_billing_blocked", None)
#: The real loop, kept so a fake standing in for it can check each call against its signature.
REAL_WAIT_FOR = ci_wait.wait_for


@pytest.fixture(autouse=True)
def _no_real_repo_lookup(monkeypatch):
    """Never ask the real `gh repo view`: main resolves the repo once when --repo is absent, and a
    test that stubs only gh_runs would otherwise reach the network. gh is a true external edge."""
    if REAL_RESOLVE_REPO is not None:
        monkeypatch.setattr(ci_wait, "resolve_repo", lambda **kw: "o/r")
    # The same for every other gh or git lookup main makes beside the run listing: a test that
    # fakes only the listing must not reach the network, and a subprocess-level fake written for
    # `gh run list` must not be handed a `gh run view` it cannot parse.
    for name in ("gh_run_jobs", "gh_typical_duration", "sha_on_a_remote"):
        if hasattr(ci_wait, name):
            monkeypatch.setattr(ci_wait, name, lambda *a, **kw: None)
    # A failed verdict asks each failed run's jobs whether GitHub refused them for billing; a
    # test that stubs only the listing would otherwise send that question to the real gh.
    if REAL_BILLING_BLOCKED is not None:
        monkeypatch.setattr(ci_wait, "gh_run_billing_blocked", lambda rid, **kw: None)


def recording_wait_for(seen: dict[str, object]):
    """A stand-in for `wait_for` that records the keywords main passed and returns success.

    It binds each call against the REAL signature first: a bare `**kw` fake accepts any keyword,
    so main passing a misspelt or removed one would pass here and raise TypeError in production.
    """

    def fake_wait(*args, **kw):
        inspect.signature(REAL_WAIT_FOR).bind(*args, **kw)
        seen.update(kw)
        return ci_wait.Verdict("success", "CI=success")

    return fake_wait


def run(workflow: str, status: str, conclusion: str | None, sha: str = "a" * 40) -> dict[str, object]:
    """One `gh run list --json` row."""
    return {"headSha": sha, "workflowName": workflow, "status": status, "conclusion": conclusion, "databaseId": 1}


class TestRequireFullSha:
    def test_a_short_sha_is_refused(self):
        with pytest.raises(ci_wait.BadSha):
            ci_wait.require_full_sha("24da3ec")

    def test_the_full_sha_passes_through_lowercased(self):
        assert ci_wait.require_full_sha("A" * 40) == "a" * 40

    def test_a_forty_character_non_hex_string_is_refused(self):
        with pytest.raises(ci_wait.BadSha):
            ci_wait.require_full_sha("z" * 40)


class TestVerdict:
    def test_no_runs_for_the_sha_is_an_error_not_a_not_yet(self):
        """The whole point: an empty match must never read as 'nothing left to wait for'."""
        assert ci_wait.verdict([]).state == "no-runs"

    def test_any_run_still_going_is_pending(self):
        rows = [run("CI", "in_progress", None), run("CodeQL", "completed", "success")]
        assert ci_wait.verdict(rows).state == "pending"

    def test_a_queued_run_is_pending(self):
        assert ci_wait.verdict([run("CI", "queued", None)]).state == "pending"

    def test_every_run_completed_and_successful_passes(self):
        rows = [run("CI", "completed", "success"), run("CodeQL", "completed", "success")]
        assert ci_wait.verdict(rows).state == "success"

    def test_one_failed_run_fails_the_whole_sha(self):
        rows = [run("CI", "completed", "failure"), run("CodeQL", "completed", "success")]
        result = ci_wait.verdict(rows)
        assert result.state == "failed"
        assert "CI" in result.summary

    def test_a_completed_run_with_no_conclusion_is_not_a_success(self):
        """A cancelled-at-source run can complete with a null conclusion; that is not green."""
        assert ci_wait.verdict([run("CI", "completed", None)]).state == "failed"


class TestWaitLoop:
    def test_it_polls_until_every_run_is_terminal(self):
        polls = [
            [run("CI", "in_progress", None)],
            [run("CI", "in_progress", None)],
            [run("CI", "completed", "success")],
            [run("CI", "completed", "success")],
        ]
        calls: list[int] = []

        def fetch() -> list[dict[str, object]]:
            calls.append(1)
            return polls[min(len(calls) - 1, len(polls) - 1)]

        result = ci_wait.wait_for(fetch, deadline_polls=10, sleep=lambda _s: None)

        assert result.state == "success"
        assert len(calls) == 4  # three to go green, a fourth confirming no run is still appearing

    def test_it_stops_at_the_deadline_and_says_it_timed_out(self):
        result = ci_wait.wait_for(
            lambda: [run("CI", "in_progress", None)], deadline_polls=3, sleep=lambda _s: None
        )
        assert result.state == "timeout"
        assert "CI" in result.summary

    def test_runs_that_have_not_been_created_yet_are_waited_for_briefly(self):
        """A push does not create its runs instantly - measured, they take seconds to appear. An
        empty list on the first poll is that race, not a verdict."""
        polls = [[], [], [run("CI", "completed", "success")], [run("CI", "completed", "success")]]
        calls: list[int] = []

        def fetch() -> list[dict[str, object]]:
            calls.append(1)
            return polls[min(len(calls) - 1, len(polls) - 1)]

        result = ci_wait.wait_for(
            fetch, deadline_polls=10, sleep=lambda _s: None, interval_s=30.0, appear_grace_s=120.0
        )

        assert result.state == "success"

    def test_an_empty_match_gives_up_on_its_own_grace_budget_not_the_whole_deadline(self):
        """The short-sha trap stays closed: a sha that will never match must not spin to the
        deadline. It cannot BE a short sha here - require_full_sha refuses those before any poll -
        so this is the full-sha-that-matches-nothing case, and it ends in seconds, not minutes."""
        calls: list[int] = []

        def fetch() -> list[dict[str, object]]:
            calls.append(1)
            return []

        result = ci_wait.wait_for(
            fetch, deadline_polls=100, sleep=lambda _s: None, interval_s=30.0, appear_grace_s=90.0
        )

        assert result.state == "no-runs"
        assert len(calls) == 4  # empty at 0, 30, 60 and 90s: the full 90s of grace was waited

    def test_the_appear_grace_is_a_DURATION_so_a_short_interval_cannot_shrink_it(self):
        """The defect this replaced: expressed as a poll COUNT, --interval 5 silently cut the
        grace to a sixth, and the tool then errored on a push whose runs took 20s to appear."""
        calls: list[int] = []

        def fetch() -> list[dict[str, object]]:
            calls.append(1)
            return []

        ci_wait.wait_for(
            fetch, deadline_polls=100, sleep=lambda _s: None, interval_s=5.0, appear_grace_s=90.0
        )

        assert len(calls) == 19  # empty at 0, 5, ... 90s: 90s of grace at 5s per poll, NOT 3 polls


class TestSettleBeforeCallingItGreen:
    """A run that has not been CREATED yet is indistinguishable from one that does not exist.

    Measured 2026-09-02 on a real push: the first poll saw only `ci`, which went green, and the
    waiter reported success while a second workflow for the same sha was still being created. The
    verdict was computed over a partial set and read as the whole set - the same not-yet-versus-
    absent confusion the appear-grace closes for an EMPTY match, one level up.
    """

    def test_a_run_created_after_the_first_green_poll_is_still_waited_for(self):
        polls = [
            [run("ci", "completed", "success")],
            [run("ci", "completed", "success"), run("workflow", "in_progress", None)],
            [run("ci", "completed", "success"), run("workflow", "completed", "success")],
            [run("ci", "completed", "success"), run("workflow", "completed", "success")],
        ]
        calls: list[int] = []

        def fetch() -> list[dict[str, object]]:
            calls.append(1)
            return polls[min(len(calls) - 1, len(polls) - 1)]

        result = ci_wait.wait_for(fetch, deadline_polls=10, sleep=lambda _s: None)

        assert result.state == "success"
        assert "workflow=success" in result.summary   # the late run is IN the verdict
        assert len(calls) >= 3                        # it did not answer from the first poll

    def test_settle_zero_keeps_the_old_answer_on_the_first_poll(self):
        calls: list[int] = []

        def fetch() -> list[dict[str, object]]:
            calls.append(1)
            return [run("ci", "completed", "success")]

        result = ci_wait.wait_for(fetch, deadline_polls=10, sleep=lambda _s: None, settle_s=0.0)

        assert result.state == "success"
        assert len(calls) == 1

    def test_confirming_can_never_turn_a_green_into_a_timeout(self):
        """The settle is a confirmation, not another way to fail: with one poll left it reports
        what it saw rather than spending the last poll and calling it a timeout."""
        result = ci_wait.wait_for(
            lambda: [run("ci", "completed", "success")], deadline_polls=1, sleep=lambda _s: None
        )
        assert result.state == "success"

    def test_a_failure_is_reported_at_once_because_a_later_run_cannot_rescue_it(self):
        calls: list[int] = []

        def fetch() -> list[dict[str, object]]:
            calls.append(1)
            return [run("ci", "completed", "failure")]

        result = ci_wait.wait_for(fetch, deadline_polls=10, sleep=lambda _s: None)

        assert result.state == "failed"
        assert len(calls) == 1


class TestExitCodes:
    def test_the_states_map_to_posix_exit_codes(self):
        assert ci_wait.exit_code_for("success") == 0
        assert ci_wait.exit_code_for("failed") == 1
        assert ci_wait.exit_code_for("timeout") == 2
        assert ci_wait.exit_code_for("no-runs") == 2


class TestGhRuns:
    """The client-side filter and the gh edge. `subprocess` is a true external edge, so it is
    patched here rather than injected - the rest of the tool takes `fetch` as a parameter."""

    def _fake_gh(self, monkeypatch, *, stdout: str, returncode: int = 0):
        import subprocess as sp

        def fake_run(argv, **kwargs):
            return sp.CompletedProcess(argv, returncode, stdout=stdout, stderr="boom")

        monkeypatch.setattr(ci_wait.subprocess, "run", fake_run)

    def test_it_keeps_only_the_rows_for_the_asked_sha(self, monkeypatch):
        import json

        wanted, other = "a" * 40, "b" * 40
        rows = [run("CI", "completed", "success", wanted), run("CI", "completed", "failure", other)]
        self._fake_gh(monkeypatch, stdout=json.dumps(rows))

        kept = ci_wait.gh_runs(wanted)

        assert [r["headSha"] for r in kept] == [wanted]

    def test_a_nonzero_gh_exit_is_raised_not_read_as_no_runs(self, monkeypatch):
        """Otherwise a broken `gh` reads as 'this sha has no runs', which exits 2 for the wrong
        reason and points at the sha instead of at the tool that failed."""
        self._fake_gh(monkeypatch, stdout="", returncode=1)

        with pytest.raises(ci_wait.GhFailed):
            ci_wait.gh_runs("a" * 40)

    def test_unparseable_output_is_raised_not_read_as_no_runs(self, monkeypatch):
        self._fake_gh(monkeypatch, stdout="not json at all")

        with pytest.raises(ci_wait.GhFailed):
            ci_wait.gh_runs("a" * 40)


class TestShaIsKnownLocally:
    """A 40-hex sha can still be one nobody ever committed.

    The format guard closes the SHORT-sha trap; it says nothing about a sha that was completed,
    transcribed or invented. Such a sha reaches `gh`, matches no run, and the wait reports
    `no-runs` - the same words a just-pushed commit produces before its runs appear. The caller
    then cannot tell "wait a moment longer" from "you asked about a commit that does not exist".
    """

    @staticmethod
    def _git(inside=True, known=True):
        """A fake `git` runner. Keyed on the ARGV, and answering by EXIT CODE only."""
        def run(argv, **kwargs):
            class P:
                pass
            p = P()
            if "rev-parse" in argv:
                p.returncode, p.stdout, p.stderr = (0, "true\n", "") if inside else (128, "", "fatal\n")
            else:
                p.returncode, p.stdout, p.stderr = (0, "", "") if known else (1, "", "")
            return p
        return run

    def test_a_sha_the_repo_holds_is_known(self):
        assert ci_wait.sha_is_known_locally("a" * 40, run=self._git(known=True)) is True

    def test_a_sha_the_repo_does_not_hold_is_not_known(self):
        assert ci_wait.sha_is_known_locally("a" * 40, run=self._git(known=False)) is False

    def test_outside_a_git_repo_it_declines_to_answer(self):
        """None, never False: 'I cannot tell' must not read as 'that commit does not exist'."""
        assert ci_wait.sha_is_known_locally("a" * 40, run=self._git(inside=False)) is None

    def test_no_git_on_path_declines_to_answer(self):
        def boom(argv, **kwargs):
            raise OSError("no git")
        assert ci_wait.sha_is_known_locally("a" * 40, run=boom) is None

    def test_the_verdict_is_keyed_on_exit_code_not_on_git_s_message(self):
        """git localises its messages, so matching English text fails on a German machine."""
        def german(argv, **kwargs):
            class P:
                pass
            p = P()
            if "rev-parse" in argv:
                p.returncode, p.stdout, p.stderr = 0, "true\n", ""
            else:
                p.returncode, p.stdout, p.stderr = 1, "", "fatal: Kein gueltiges Objekt\n"
            return p
        assert ci_wait.sha_is_known_locally("a" * 40, run=german) is False


class TestAnUnknownShaWarnsButStillPolls:
    """git not holding the sha is evidence, not proof - `gh` decides whether runs exist.

    Refusing here would break a legitimate wait: a sha you never fetched (a colleague's push, a sha
    read off a notification, a shallow clone) is not in this checkout and its runs are real. The
    warning has to reach stderr, never stdout, so a --json consumer's stream stays parseable.
    """

    def test_it_does_not_refuse_and_the_warning_goes_to_stderr(self, monkeypatch, capsys):
        monkeypatch.setattr(ci_wait, "sha_is_known_locally", lambda sha, **kw: False)
        monkeypatch.setattr(ci_wait, "gh_runs", lambda sha, **kw: [run("CI", "completed", "success")])

        rc = ci_wait.main(["--sha", "a" * 40, "--settle", "0"])
        out, err = capsys.readouterr()

        assert rc == 0, "an unfetched sha whose runs are green must not be refused"
        assert "warning:" in err and "not a commit in this repository" in err
        assert "warning:" not in out, "the warning must not pollute the parsed stream"

    def test_a_green_run_is_still_reported_green(self, monkeypatch, capsys):
        monkeypatch.setattr(ci_wait, "sha_is_known_locally", lambda sha, **kw: False)
        monkeypatch.setattr(ci_wait, "gh_runs", lambda sha, **kw: [run("CI", "completed", "success")])

        ci_wait.main(["--sha", "a" * 40, "--settle", "0"])

        assert "success" in capsys.readouterr().out

    def test_a_sha_git_does_know_produces_no_warning(self, monkeypatch, capsys):
        """The control: the warning must be absent when there is nothing to warn about."""
        monkeypatch.setattr(ci_wait, "sha_is_known_locally", lambda sha, **kw: True)
        monkeypatch.setattr(ci_wait, "gh_runs", lambda sha, **kw: [run("CI", "completed", "success")])

        ci_wait.main(["--sha", "a" * 40, "--settle", "0"])

        assert "warning:" not in capsys.readouterr().err


class TestATransientGhFailureIsRetried:
    """A 5xx from the API is weather, not a verdict.

    Measured 2026-08-31: `gh run list` answered HTTP 502 intermittently while the API was
    otherwise healthy, and this tool exited 2 three times running - each time abandoning a wait
    with twenty minutes left on its deadline, and each time reading as an infrastructure problem
    rather than as one bad response. A WAITER is the one tool that must survive its fetch failing,
    because the alternative is the caller re-running the whole wait by hand.
    """

    @staticmethod
    def _fails_then(times: int, rows: list[dict[str, object]]):
        """A fetch raising GhFailed ``times`` times, then answering ``rows``."""
        seen: list[int] = []

        def fetch() -> list[dict[str, object]]:
            seen.append(1)
            if len(seen) <= times:
                raise ci_wait.GhFailed("gh exited 1: HTTP 502 (api.github.com)")
            return rows

        return fetch, seen

    def test_one_502_does_not_end_the_wait(self):
        fetch, seen = self._fails_then(1, [run("CI", "completed", "success")])

        result = ci_wait.wait_for(fetch, deadline_polls=10, sleep=lambda _s: None)

        assert result.state == "success"
        assert len(seen) == 3  # the 502, the green poll, and the one confirming it

    def test_an_intermittent_failure_never_exhausts_the_budget(self):
        """The streak resets on any answered poll, so 'every other poll 502s' waits it out.

        Counted cumulatively rather than consecutively, the second failure here would end the
        wait at `error` while CI was still running perfectly well.
        """
        script: list[object] = [
            "fail", [run("CI", "in_progress", None)],
            "fail", [run("CI", "in_progress", None)],
            "fail", [run("CI", "completed", "success")],
            [run("CI", "completed", "success")],   # the poll confirming no run is still appearing
        ]
        seen: list[int] = []

        def fetch() -> list[dict[str, object]]:
            step = script[len(seen)]
            seen.append(1)
            if step == "fail":
                raise ci_wait.GhFailed("gh exited 1: HTTP 502")
            return step  # type: ignore[return-value]

        result = ci_wait.wait_for(
            fetch, deadline_polls=20, sleep=lambda _s: None, interval_s=30.0, error_grace_s=60.0
        )

        assert result.state == "success"
        assert len(seen) == 7  # six scripted, then the poll confirming no run is still appearing

    def test_a_sustained_outage_ends_in_error_naming_the_last_gh_message(self):
        """Bounded, and it still says WHAT failed - `error: gh exited 1: HTTP 502`, not `timeout`."""
        seen: list[int] = []

        def fetch() -> list[dict[str, object]]:
            seen.append(1)
            raise ci_wait.GhFailed("gh exited 1: HTTP 502 (api.github.com)")

        result = ci_wait.wait_for(
            fetch, deadline_polls=100, sleep=lambda _s: None, interval_s=30.0, error_grace_s=90.0
        )

        assert result.state == "error"
        assert "502" in result.summary
        assert len(seen) == 4, "failing at 0, 30, 60, 90s: 90s of grace, not the 100-poll deadline"

    def test_the_error_grace_is_a_DURATION_so_a_short_interval_cannot_shrink_it(self):
        """The same defect the appear-grace carries a test for: as a poll COUNT, `--interval 5`
        would cut a 90-second tolerance to 18 seconds and a blip would end the wait."""
        seen: list[int] = []

        def fetch() -> list[dict[str, object]]:
            seen.append(1)
            raise ci_wait.GhFailed("gh exited 1: HTTP 502")

        ci_wait.wait_for(
            fetch, deadline_polls=100, sleep=lambda _s: None, interval_s=5.0, error_grace_s=90.0
        )

        assert len(seen) == 19

    def test_it_sleeps_between_retries_rather_than_hammering_the_api(self):
        """A retry loop with no wait turns one 502 into a burst against an API already struggling."""
        slept: list[float] = []

        def fetch() -> list[dict[str, object]]:
            raise ci_wait.GhFailed("gh exited 1: HTTP 502")

        ci_wait.wait_for(
            fetch, deadline_polls=100, sleep=slept.append, interval_s=30.0, error_grace_s=90.0
        )

        assert slept == [30.0, 30.0, 30.0], "between the four attempts, none after the verdict"

    def test_a_deadline_reached_while_gh_is_failing_reports_the_failure_not_a_timeout(self):
        """Whichever budget runs out first, the report must name the cause it actually saw."""

        def fetch() -> list[dict[str, object]]:
            raise ci_wait.GhFailed("gh exited 1: HTTP 502")

        result = ci_wait.wait_for(
            fetch, deadline_polls=2, sleep=lambda _s: None, interval_s=30.0, error_grace_s=300.0
        )

        assert result.state == "error"
        assert "502" in result.summary

    def test_a_timeout_reports_the_last_seen_state_without_a_further_fetch(self):
        """The extra fetch the timeout used to make could itself 502, turning a plain timeout
        into an error about the API."""
        seen: list[int] = []

        def fetch() -> list[dict[str, object]]:
            seen.append(1)
            return [run("CI", "in_progress", None)]

        result = ci_wait.wait_for(fetch, deadline_polls=3, sleep=lambda _s: None)

        assert result.state == "timeout"
        assert "CI=in_progress" in result.summary
        assert len(seen) == 3


class TestGhBeingUnrunnableIsNotRetried:
    """`gh` missing is permanent for this process; 502 is not. Retrying the first wastes the grace.

    The distinction is drawn where it is CERTAIN - the OS refusing to spawn the binary - not by
    reading gh's message for words like 'transient', which would be a guess about a remote system
    and would put the 502 bug back the first time a guess was wrong.
    """

    def test_gh_not_on_path_is_a_typed_error_not_a_traceback(self, monkeypatch):
        def boom(argv, **kwargs):
            raise FileNotFoundError(2, "No such file or directory", "gh")

        monkeypatch.setattr(ci_wait.subprocess, "run", boom)

        with pytest.raises(ci_wait.GhUnavailable):
            ci_wait.gh_runs("a" * 40)

    def test_the_wait_gives_up_on_it_at_once(self):
        seen: list[int] = []

        def fetch() -> list[dict[str, object]]:
            seen.append(1)
            raise ci_wait.GhUnavailable("gh is not installed or not on PATH")

        with pytest.raises(ci_wait.GhUnavailable):
            ci_wait.wait_for(fetch, deadline_polls=100, sleep=lambda _s: None)

        assert len(seen) == 1

    def test_gh_with_no_credentials_is_fatal_rather_than_retried(self, monkeypatch):
        """Measured against gh 2.92.0: with no token and no config, `gh run list` exits 4 and says
        to run `gh auth login`. That is a local configuration fact, so no amount of waiting fixes
        it and the grace must not be spent on it."""
        import subprocess as sp

        def fake_run(argv, **kwargs):
            return sp.CompletedProcess(
                argv, 4, stdout="",
                stderr="To get started with GitHub CLI, please run:  gh auth login",
            )

        monkeypatch.setattr(ci_wait.subprocess, "run", fake_run)

        with pytest.raises(ci_wait.GhUnavailable):
            ci_wait.gh_runs("a" * 40)

    def test_a_rejected_credential_is_still_retried_because_gh_exits_1_for_it(self, monkeypatch):
        """The MEASURED LIMIT of the exit-code split, kept as an executable fact.

        A revoked or mistyped token is not exit 4. gh 2.92.0 exits 1 with `HTTP 401: Bad
        credentials`, which no exit code distinguishes from the 502 this tool retries, so it stays
        retryable and costs the grace before it is reported. Separating it would mean reading gh's
        message for its meaning, which is the guess this design refuses - the same guess that would
        put the 502 defect back. If this test ever fails because gh started exiting 4 for a
        rejected credential, that is the moment to widen the split, not before.
        """
        import subprocess as sp

        def fake_run(argv, **kwargs):
            return sp.CompletedProcess(
                argv, 1, stdout="",
                stderr="failed to get runs: HTTP 401: Bad credentials (https://api.github.com/...)",
            )

        monkeypatch.setattr(ci_wait.subprocess, "run", fake_run)

        with pytest.raises(ci_wait.GhFailed):
            ci_wait.gh_runs("a" * 40)

    def test_main_reports_it_as_could_not_tell_rather_than_crashing(self, monkeypatch, capsys):
        monkeypatch.setattr(ci_wait, "sha_is_known_locally", lambda sha, **kw: True)

        def boom(sha, **kw):
            raise ci_wait.GhUnavailable("gh is not installed or not on PATH")

        monkeypatch.setattr(ci_wait, "gh_runs", boom)

        rc = ci_wait.main(["--sha", "a" * 40])

        assert rc == 2
        assert "gh is not installed" in capsys.readouterr().err


class TestTheRetryReachesTheRealCommandLine:
    """The loop tolerating a failure is worth nothing if `main` does not wire it that way."""

    def test_a_502_on_the_first_poll_still_ends_green(self, monkeypatch, capsys):
        monkeypatch.setattr(ci_wait, "sha_is_known_locally", lambda sha, **kw: True)
        monkeypatch.setattr(ci_wait.time, "sleep", lambda _s: None)
        calls: list[int] = []

        def flaky(sha, **kw):
            calls.append(1)
            if len(calls) == 1:
                raise ci_wait.GhFailed("gh exited 1: HTTP 502 (api.github.com)")
            return [run("CI", "completed", "success")]

        monkeypatch.setattr(ci_wait, "gh_runs", flaky)

        rc = ci_wait.main(["--sha", "a" * 40])

        assert rc == 0, "a single 502 must not end a wait that had its whole deadline left"
        assert len(calls) == 3  # the 502, the green poll, and the one confirming it

    def test_the_error_grace_defaults_to_300_seconds(self):
        """Longer than --appear-grace on purpose. The costs are asymmetric: too short reproduces
        the abandoned-wait defect on any API wobble outlasting it, while too long only delays
        reporting a setup that was broken anyway."""
        assert ci_wait._parse_args(["--sha", "a" * 40]).error_grace == 300.0

    def test_the_cli_value_reaches_the_wait_loop(self, monkeypatch):
        """Parsed and then dropped is the shape a green suite cannot see: the flag exists, the
        help text is right, and the loop keeps its default."""
        seen: dict[str, object] = {}
        monkeypatch.setattr(ci_wait, "sha_is_known_locally", lambda sha, **kw: True)
        monkeypatch.setattr(ci_wait, "wait_for", recording_wait_for(seen))

        ci_wait.main(["--sha", "a" * 40, "--error-grace", "300"])

        assert seen["error_grace_s"] == 300.0


# --------------------------------------------------------------------------------------------
# Review findings (rank 10, group R): each class pins one confirmed defect
# --------------------------------------------------------------------------------------------

SHA = "a" * 40
SCRIPT = Path(ci_wait.__file__).resolve()


def emulated_gh(rows_newest_first: list[dict[str, object]], calls: list[list[str]]):
    """A stand-in for `gh run list` with gh's own semantics: `--commit` filters server-side,
    then `--limit` keeps the newest N. `subprocess` is the true external edge here."""

    def fake_run(argv, **kwargs):
        calls.append(list(argv))
        rows = rows_newest_first
        if "--commit" in argv:
            wanted = argv[argv.index("--commit") + 1]
            rows = [r for r in rows if r["headSha"] == wanted]
        limit = int(argv[argv.index("--limit") + 1])
        return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(rows[:limit]), stderr="")

    return fake_run


class TestTheShaIsAskedForServerSide:
    def test_older_runs_of_the_sha_beyond_the_limit_window_are_still_seen(self, monkeypatch):
        """29 newer runs of other shas pushed the failing CI run out of a 30-row window, and the
        tool reported the remaining CodeQL success as a green push."""
        others = [run("CI", "completed", "success", "b" * 40) for _ in range(29)]
        rows = others + [run("CodeQL", "completed", "success"), run("CI", "completed", "failure")]
        calls: list[list[str]] = []
        monkeypatch.setattr(ci_wait.subprocess, "run", emulated_gh(rows, calls))

        result = ci_wait.verdict(ci_wait.gh_runs(SHA, limit=30))

        assert result.state == "failed"
        assert "--commit" in calls[0] and SHA in calls[0]


class TestGracesAreMeasuredInTime:
    def test_an_interval_as_long_as_the_grace_still_waits_the_grace_once(self):
        slept: list[float] = []
        result = ci_wait.wait_for(
            list, deadline_polls=100, sleep=slept.append, interval_s=120.0, appear_grace_s=120.0
        )
        assert result.state == "no-runs"
        assert sum(slept) >= 120.0

    def test_a_grace_that_is_not_a_multiple_of_the_interval_is_honoured(self):
        slept: list[float] = []
        ci_wait.wait_for(
            list, deadline_polls=100, sleep=slept.append, interval_s=2.0, appear_grace_s=3.0
        )
        assert sum(slept) >= 3.0

    def test_the_error_grace_is_honoured_when_the_interval_equals_it(self):
        slept: list[float] = []

        def fetch() -> list[dict[str, object]]:
            raise ci_wait.GhFailed("gh exited 1: HTTP 502")

        result = ci_wait.wait_for(
            fetch, deadline_polls=100, sleep=slept.append, interval_s=5.0, error_grace_s=5.0
        )
        assert result.state == "error"
        assert sum(slept) >= 5.0

    def test_an_injected_clock_counts_the_time_a_slow_fetch_took(self):
        """In real use elapsed time includes the gh calls themselves, not only the sleeps."""
        now = [0.0]
        calls: list[int] = []

        def slow_empty() -> list[dict[str, object]]:
            calls.append(1)
            now[0] += 50.0
            return []

        ci_wait.wait_for(
            slow_empty, deadline_polls=100, sleep=lambda s: now.__setitem__(0, now[0] + s),
            interval_s=10.0, appear_grace_s=100.0, clock=lambda: now[0],
        )
        assert len(calls) == 3  # empty at 50, 110, 170: 120s since the first empty >= 100


class TestAStalledGhCannotOutliveTheTimeout:
    def test_gh_runs_bounds_the_call_and_maps_a_timeout_to_a_retryable_failure(self, monkeypatch):
        seen: dict[str, object] = {}

        def fake_run(argv, **kwargs):
            seen.update(kwargs)
            raise subprocess.TimeoutExpired(argv, kwargs.get("timeout"))

        monkeypatch.setattr(ci_wait.subprocess, "run", fake_run)
        with pytest.raises(ci_wait.GhFailed, match="did not answer"):
            ci_wait.gh_runs(SHA, timeout_s=7.0)
        assert seen["timeout"] == 7.0

    def test_the_wall_clock_deadline_ends_the_wait(self):
        now = [0.0]
        calls: list[int] = []

        def hung() -> list[dict[str, object]]:
            calls.append(1)
            now[0] += 100.0
            raise ci_wait.GhFailed("gh did not answer within 100s")

        result = ci_wait.wait_for(
            hung, deadline_polls=1000, sleep=lambda s: None, interval_s=1.0,
            error_grace_s=10_000.0, deadline_s=150.0, clock=lambda: now[0],
        )
        assert result.state == "error"
        assert len(calls) == 2

    @staticmethod
    def _cli_on_a_fake_clock(monkeypatch, argv, gh_seconds=1.0):
        """Run main() with the CLOCK faked - the one external edge here that cannot be injected
        through the command line - and gh answering 'still running' after `gh_seconds`."""
        now = [1000.0]
        calls: list[float] = []

        def pending(sha, **kw):
            calls.append(now[0])
            now[0] += gh_seconds
            return [run("CI", "in_progress", None)]

        monkeypatch.setattr(ci_wait, "sha_is_known_locally", lambda sha, **kw: True)
        monkeypatch.setattr(ci_wait, "gh_runs", pending)
        monkeypatch.setattr(ci_wait.time, "monotonic", lambda: now[0])
        monkeypatch.setattr(ci_wait.time, "sleep", lambda s: now.__setitem__(0, now[0] + s))
        rc = ci_wait.main(argv)
        return rc, [t - 1000.0 for t in calls], now[0] - 1000.0

    def test_a_timeout_shorter_than_two_intervals_still_polls_until_the_deadline(self, monkeypatch):
        """A poll COUNT of timeout // interval gave --timeout 50 --interval 30 one poll, so the
        wait ended after a second while the documented wall-clock deadline had 49 left."""
        rc, polled_at, ended = self._cli_on_a_fake_clock(
            monkeypatch, ["--sha", SHA, "--timeout", "50", "--interval", "30"])
        assert rc == 2
        assert len(polled_at) >= 2, polled_at
        assert ended >= 50.0, ended

    def test_the_last_sleep_is_cut_to_the_deadline_rather_than_overshooting_it(self, monkeypatch):
        rc, polled_at, ended = self._cli_on_a_fake_clock(
            monkeypatch, ["--sha", SHA, "--timeout", "50", "--interval", "30"])
        assert rc == 2
        assert polled_at == [0.0, 31.0, 50.0], polled_at
        assert ended <= 51.0, ended

    def test_slow_polls_do_not_stretch_the_wait_past_the_timeout(self, monkeypatch):
        rc, _polled_at, ended = self._cli_on_a_fake_clock(
            monkeypatch, ["--sha", SHA, "--timeout", "100", "--interval", "10"], gh_seconds=15.0)
        assert rc == 2
        assert ended <= 115.0, ended

    def test_stalled_job_reads_cannot_hold_the_wait_past_the_floor(self, monkeypatch):
        """Review finding: every pending poll reads each unfinished run's jobs, each read with its
        own floor-bounded timeout, so three stalled reads held the wait 20s past a 50s deadline
        while the docstring promised at most GH_CALL_FLOOR_S."""
        now = [1000.0]
        rows = [{**run(name, "in_progress", None), "databaseId": rid}
                for rid, name in enumerate(("ci", "docs", "lint"), start=1)]

        def fake_gh(argv, **kw):
            if argv[:3] == ["gh", "run", "list"]:
                return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(rows), stderr="")
            now[0] += kw["timeout"]               # a stalled job read takes its whole bound
            raise subprocess.TimeoutExpired(argv, kw["timeout"])

        monkeypatch.setattr(ci_wait, "sha_is_known_locally", lambda sha, **kw: True)
        monkeypatch.setattr(ci_wait, "gh_run_jobs", REAL_GH_RUN_JOBS)
        monkeypatch.setattr(ci_wait.subprocess, "run", fake_gh)
        monkeypatch.setattr(ci_wait.time, "monotonic", lambda: now[0])
        monkeypatch.setattr(ci_wait.time, "sleep", lambda s: now.__setitem__(0, now[0] + s))

        rc = ci_wait.main(["--sha", SHA, "--repo", "o/r", "--timeout", "50", "--interval", "30"])

        assert rc == 2
        assert now[0] - 1000.0 <= 50.0 + ci_wait.GH_CALL_FLOOR_S, now[0] - 1000.0

    @pytest.mark.skipif(os.name == "nt", reason="a fake gh on PATH needs a POSIX shebang")
    def test_a_hanging_gh_is_ended_by_timeout_end_to_end(self, tmp_path):
        fake = tmp_path / "bin" / "gh"
        fake.parent.mkdir()
        fake.write_text(f"#!{sys.executable}\nimport time\ntime.sleep(60)\n", encoding="utf-8")
        fake.chmod(0o755)
        env = {**os.environ, "PATH": f"{fake.parent}{os.pathsep}{os.environ.get('PATH', '')}"}
        started = time.monotonic()
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--sha", SHA, "--repo", "o/r", "--timeout", "2",
             "--interval", str(ci_wait.MIN_INTERVAL_S)],
            capture_output=True, text=True, env=env, timeout=45, check=False,
        )
        assert proc.returncode == 2, proc.stderr
        # Exit 2 is also a usage error: require that the wait actually RAN and timed out on gh.
        assert "usage:" not in proc.stderr, proc.stderr
        assert time.monotonic() - started < 30


class TestBadNumbersAreUsageErrors:
    @pytest.mark.parametrize(
        "flag,value",
        [("--interval", "-5"), ("--interval", "0"), ("--timeout", "inf"), ("--timeout", "nan"),
         ("--timeout", "-1"), ("--appear-grace", "-1"), ("--error-grace", "nan"),
         ("--settle", "-2"), ("--limit", "0")],
    )
    def test_a_bad_value_exits_2_without_a_traceback(self, flag, value, monkeypatch, capsys):
        # Never the real gh: a value that slips through must end fast, not poll the API.
        calls: list[list[str]] = []
        monkeypatch.setattr(
            ci_wait.subprocess, "run", emulated_gh([run("CI", "completed", "success")], calls)
        )
        monkeypatch.setattr(ci_wait.time, "sleep", lambda _s: None)
        with pytest.raises(SystemExit) as info:
            ci_wait.main(["--sha", SHA, "--repo", "o/r", "--settle", "0", flag, value])
        assert info.value.code == 2
        assert "Traceback" not in capsys.readouterr().err

    def test_zero_settle_and_zero_grace_stay_allowed(self):
        args = ci_wait._parse_args(["--sha", SHA, "--settle", "0", "--appear-grace", "0"])
        assert args.settle == 0.0 and args.appear_grace == 0.0


class TestMainEnvelopeAndRepo:
    def test_a_short_sha_with_json_is_an_error_envelope(self, capsys):
        rc = ci_wait.main(["--sha", "abc1234", "--json"])
        payload = json.loads(capsys.readouterr().out)
        assert rc == 2
        assert payload["ok"] is False and payload["command"] == "ci_wait"
        assert payload["data"]["state"] == "error"
        assert "40-character" in payload["data"]["summary"]
        assert "40-character" in payload["error"]

    def test_repo_is_passed_to_gh_and_skips_the_local_sha_check(self, monkeypatch, capsys):
        calls: list[list[str]] = []
        monkeypatch.setattr(
            ci_wait.subprocess, "run", emulated_gh([run("CI", "completed", "success")], calls)
        )
        rc = ci_wait.main(["--sha", SHA, "--repo", "o/r", "--settle", "0", "--json"])
        assert rc == 0
        assert all(argv[0] == "gh" for argv in calls), "no git call when --repo names another repo"
        assert calls[0][calls[0].index("--repo") + 1] == "o/r"
        assert json.loads(capsys.readouterr().out)["data"]["state"] == "success"

    def test_a_json_object_from_gh_is_a_retryable_failure(self, monkeypatch):
        monkeypatch.setattr(
            ci_wait.subprocess, "run",
            lambda argv, **kw: subprocess.CompletedProcess(argv, 0, stdout='{"a": 1}', stderr=""),
        )
        with pytest.raises(ci_wait.GhFailed, match="dict, not a list"):
            ci_wait.gh_runs(SHA)

    def test_an_unexpected_crash_is_could_not_tell_not_a_failed_run(self, monkeypatch, capsys):
        def boom(argv, **kw):
            raise RuntimeError("something nobody planned for")

        monkeypatch.setattr(ci_wait.subprocess, "run", boom)
        rc = ci_wait.main(["--sha", SHA, "--repo", "o/r", "--json"])
        assert rc == 2
        assert json.loads(capsys.readouterr().out)["data"]["state"] == "error"


class TestASkippedRunIsNotAFailure:
    def test_a_skipped_workflow_beside_a_green_one_is_green(self):
        rows = [run("ci", "completed", "success"), run("deploy", "completed", "skipped")]
        assert ci_wait.verdict(rows).state == "success"

    def test_nothing_but_skipped_runs_is_not_green(self):
        assert ci_wait.verdict([run("deploy", "completed", "skipped")]).state == "failed"

    def test_a_failure_beside_a_skipped_run_still_fails(self):
        rows = [run("ci", "completed", "failure"), run("deploy", "completed", "skipped")]
        assert ci_wait.verdict(rows).state == "failed"


class TestAConsoleThatCannotEncodeAWorkflowName:
    def test_the_report_does_not_crash_on_cp1252(self, tmp_path):
        driver = tmp_path / "drive.py"
        driver.write_text(
            "import json, subprocess, sys\n"
            f"sys.path.insert(0, {str(SCRIPT.parent)!r})\n"
            "import ci_wait\n"
            "row = {'headSha': 'a' * 40, 'workflowName': 'CI \\u2713', 'status': 'completed',"
            " 'conclusion': 'success', 'databaseId': 1}\n"
            "ci_wait.subprocess.run = lambda argv, **kw: subprocess.CompletedProcess("
            "argv, 0, stdout=json.dumps([row]), stderr='')\n"
            "sys.exit(ci_wait.main(['--sha', 'a' * 40, '--repo', 'o/r', '--settle', '0']))\n",
            encoding="utf-8",
        )
        env = {**os.environ, "PYTHONIOENCODING": "cp1252"}
        env.pop("PYTHONUTF8", None)
        proc = subprocess.run(
            [sys.executable, str(driver)], capture_output=True, env=env, timeout=60, check=False
        )
        assert proc.returncode == 0, proc.stderr.decode("cp1252", "replace")
        assert b"CI " in proc.stdout


class TestAnIntervalHasAFloor:
    """With the wall-clock deadline, a tiny --interval polls gh back to back for the whole wait:
    one API request per call, ~1,500 a minute at 0.04 s, which spends the hourly rate limit the
    rest of the machine shares. Refused as a usage error rather than silently raised."""

    @pytest.mark.parametrize("value", ["0.001", "1", "4.9"])
    def test_an_interval_below_the_floor_is_a_usage_error(self, value, monkeypatch, capsys):
        calls: list[list[str]] = []
        monkeypatch.setattr(
            ci_wait.subprocess, "run", emulated_gh([run("CI", "completed", "success")], calls)
        )
        monkeypatch.setattr(ci_wait.time, "sleep", lambda _s: None)
        with pytest.raises(SystemExit) as info:
            ci_wait.main(["--sha", SHA, "--repo", "o/r", "--settle", "0", "--interval", value])
        assert info.value.code == 2
        err = capsys.readouterr().err
        assert "--interval" in err and "Traceback" not in err
        assert not calls

    def test_the_floor_itself_is_allowed(self):
        assert ci_wait._parse_args(["--sha", SHA, "--interval", str(ci_wait.MIN_INTERVAL_S)]).interval \
            == ci_wait.MIN_INTERVAL_S


class TestASettleCutByTheDeadlineIsSaid:
    """The deadline cuts every sleep to the time left, the settle included. The green is still
    reported (a confirmation is never another way to fail), but a confirmation that waited less
    than --settle, or never ran, must not read like a full one."""

    @staticmethod
    def _green_at(poll_index: int):
        polls: list[int] = []

        def fetch() -> list[dict[str, object]]:
            polls.append(1)
            status = "completed" if len(polls) > poll_index else "in_progress"
            return [run("ci", status, "success" if status == "completed" else None)]
        return fetch

    def test_a_settle_shortened_by_the_deadline_says_so(self):
        # polls at 0, 30, 60 pending; green at 90; the 20 s settle is cut to 10 by deadline 100.
        result = ci_wait.wait_for(self._green_at(3), sleep=lambda _s: None, interval_s=30.0,
                                  settle_s=20.0, deadline_s=100.0)
        assert result.state == "success"
        assert "not the full 20s --settle" in result.summary, result.summary

    def test_a_green_the_deadline_never_let_be_confirmed_says_so(self):
        result = ci_wait.wait_for(self._green_at(0), deadline_polls=1, sleep=lambda _s: None)
        assert result.state == "success"
        assert "not confirmed" in result.summary, result.summary

    def test_control_a_settle_that_fits_adds_nothing(self):
        result = ci_wait.wait_for(self._green_at(3), sleep=lambda _s: None, interval_s=30.0,
                                  settle_s=20.0, deadline_s=1000.0)
        assert result.state == "success"
        assert result.summary == "ci=success"


# --------------------------------------------------------------------------------------------
# Wave D: the shared envelope, --event (#41), action_required (#92), the repo resolved once (#109)
# --------------------------------------------------------------------------------------------

def evrun(workflow: str, status: str, conclusion: str | None, event: str) -> dict[str, object]:
    return {**run(workflow, status, conclusion), "event": event}


class TestTheEnvelope:
    def test_a_failed_run_is_exit_1_with_ok_true(self, monkeypatch, capsys):
        """ok means "ran without error": a red CI is an answer, exit 1."""
        monkeypatch.setattr(ci_wait, "sha_is_known_locally", lambda sha, **kw: True)
        monkeypatch.setattr(ci_wait, "gh_runs", lambda sha, **kw: [run("CI", "completed", "failure")])
        rc = ci_wait.main(["--sha", SHA, "--settle", "0", "--json"])
        payload = json.loads(capsys.readouterr().out)
        assert rc == 1
        assert list(payload)[:4] == ["ok", "command", "data", "skipped"]
        assert payload["ok"] is True and payload["data"]["state"] == "failed"
        assert payload["data"]["runs"][0]["conclusion"] == "failure"

    def test_an_argparse_error_under_json_prints_the_envelope(self, capsys):
        with pytest.raises(SystemExit) as info:
            ci_wait.main(["--json", "--sha", SHA, "--interval", "1"])
        assert info.value.code == 2
        payload = json.loads(capsys.readouterr().out)
        assert payload["ok"] is False and payload["command"] == "ci_wait"

    def test_a_missing_sha_under_json_prints_the_envelope(self, capsys):
        with pytest.raises(SystemExit):
            ci_wait.main(["--json"])
        assert json.loads(capsys.readouterr().out)["ok"] is False


class TestAnEventFilter:
    """#41: a SCHEDULED run queued on the same head sha held a push's verdict open until timeout."""

    def test_the_default_asks_gh_for_every_event(self, monkeypatch):
        """The default excludes schedule CLIENT-side, so gh is not asked for one event."""
        calls: list[list[str]] = []
        monkeypatch.setattr(ci_wait.subprocess, "run", emulated_gh([run("CI", "completed", "success")],
                                                                    calls))
        ci_wait.main(["--sha", SHA, "--repo", "o/r", "--settle", "0"])
        assert "--event" not in calls[0]

    def test_a_scheduled_run_on_the_same_sha_cannot_hold_the_verdict(self, monkeypatch):
        rows = [evrun("CI", "completed", "success", "push"),
                evrun("nightly", "in_progress", None, "schedule")]
        monkeypatch.setattr(ci_wait.subprocess, "run",
                            lambda argv, **kw: subprocess.CompletedProcess(
                                argv, 0, stdout=json.dumps(rows), stderr=""))
        kept = ci_wait.gh_runs(SHA, event="push")
        assert [r["workflowName"] for r in kept] == ["CI"]
        assert ci_wait.verdict(kept).state == "success"

    def test_event_any_asks_for_every_run(self, monkeypatch):
        calls: list[list[str]] = []
        monkeypatch.setattr(ci_wait.subprocess, "run", emulated_gh([run("CI", "completed", "success")],
                                                                    calls))
        ci_wait.main(["--sha", SHA, "--repo", "o/r", "--settle", "0", "--event", "any"])
        assert "--event" not in calls[0]

    def test_the_cli_value_reaches_gh(self, monkeypatch):
        seen: list[object] = []

        def fake(sha, **kw):
            seen.append(kw.get("event"))
            return [run("CI", "completed", "success")]

        monkeypatch.setattr(ci_wait, "sha_is_known_locally", lambda sha, **kw: True)
        monkeypatch.setattr(ci_wait, "gh_runs", fake)
        ci_wait.main(["--sha", SHA, "--settle", "0", "--event", "pull_request"])
        assert seen == ["pull_request"]

    def test_no_runs_under_a_filter_names_the_way_out(self):
        assert "--event any" in ci_wait.verdict([], event="push").summary


def event_gh(rows: list[dict[str, object]], calls: list[list[str]]):
    """`gh run list` with gh's server-side `--commit` AND `--event` filters, `--limit` last."""

    def fake_run(argv, **kwargs):
        calls.append(list(argv))
        if argv[:3] == ["gh", "run", "view"]:
            # A failed run's own jobs, as the billing check reads them: one that ran steps, so a
            # failure here stays an ordinary failure.
            jobs = {"jobs": [{"databaseId": 1, "steps": [{"name": "Set up job"}]}]}
            return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(jobs), stderr="")
        kept = [r for r in rows if r["headSha"] == argv[argv.index("--commit") + 1]]
        if "--event" in argv:
            kept = [r for r in kept if r.get("event") == argv[argv.index("--event") + 1]]
        limit = int(argv[argv.index("--limit") + 1])
        return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(kept[:limit]), stderr="")

    return fake_run


class TestTheDefaultEventIsAnyButSchedule:
    """W-D8: with no --event every run on the sha counts EXCEPT a scheduled one.

    A `push` default read a fork pull request's head - whose only runs are `pull_request` - as
    `no-runs`, exit 2, on a bare wait. Excluding only `schedule` keeps the reason the filter was
    added (a nightly run queued on the same sha held a push's verdict open) without that cost.
    """

    def _main(self, monkeypatch, rows, *extra):
        calls: list[list[str]] = []
        monkeypatch.setattr(ci_wait.subprocess, "run", event_gh(rows, calls))
        monkeypatch.setattr(ci_wait.time, "sleep", lambda _s: None)
        rc = ci_wait.main(["--sha", SHA, "--repo", "o/r", "--settle", "0", "--appear-grace", "0",
                           "--timeout", "60", *extra])
        return rc, calls

    def test_a_fork_pr_head_with_only_pull_request_runs_is_seen_by_a_bare_wait(self, monkeypatch):
        rc, _ = self._main(monkeypatch, [evrun("CI", "completed", "success", "pull_request")])
        assert rc == 0

    def test_control_event_push_still_filters_them_out(self, monkeypatch, capsys):
        rc, calls = self._main(monkeypatch, [evrun("CI", "completed", "success", "pull_request")],
                               "--event", "push")
        assert rc == 2 and "no push runs" in capsys.readouterr().err
        assert calls[0][calls[0].index("--event") + 1] == "push"

    def test_a_scheduled_run_does_not_hold_a_bare_wait_open(self, monkeypatch):
        rows = [evrun("CI", "completed", "success", "push"),
                evrun("nightly", "in_progress", None, "schedule")]
        rc, _ = self._main(monkeypatch, rows)
        assert rc == 0

    def test_a_scheduled_failure_does_not_fail_a_bare_wait(self, monkeypatch):
        rows = [evrun("CI", "completed", "success", "push"),
                evrun("nightly", "completed", "failure", "schedule")]
        rc, _ = self._main(monkeypatch, rows)
        assert rc == 0

    def test_event_any_counts_the_scheduled_run_too(self, monkeypatch):
        rows = [evrun("CI", "completed", "success", "push"),
                evrun("nightly", "completed", "failure", "schedule")]
        rc, _ = self._main(monkeypatch, rows, "--event", "any")
        assert rc == 1

    def test_gh_runs_with_no_event_drops_only_schedule_rows(self, monkeypatch):
        rows = [evrun("CI", "completed", "success", "push"),
                evrun("PR", "completed", "success", "pull_request"),
                evrun("nightly", "in_progress", None, "schedule"),
                run("legacy", "completed", "success")]
        monkeypatch.setattr(ci_wait.subprocess, "run", event_gh(rows, []))
        kept = ci_wait.gh_runs(SHA)
        assert [r["workflowName"] for r in kept] == ["CI", "PR", "legacy"]

    def test_only_scheduled_runs_read_no_runs_naming_the_way_out(self, monkeypatch, capsys):
        rc, _ = self._main(monkeypatch, [evrun("nightly", "completed", "success", "schedule")])
        err = capsys.readouterr().err
        assert rc == 2 and "schedule" in err and "--event any" in err

    def test_the_help_states_the_default(self, capsys):
        with pytest.raises(SystemExit):
            ci_wait.main(["--help"])
        assert "except schedule" in " ".join(capsys.readouterr().out.split())


class TestARunLeftOutByTheDefaultIsNamed:
    """A green "CodeQL=success CI=success" while a scheduled CI run for the same sha was still
    queued read as a bug: the default filter dropped that run and the output never said so."""

    def _main(self, monkeypatch, rows, *extra):
        monkeypatch.setattr(ci_wait.subprocess, "run", event_gh(rows, []))
        monkeypatch.setattr(ci_wait.time, "sleep", lambda _s: None)
        return ci_wait.main(["--sha", SHA, "--repo", "o/r", "--settle", "0", "--appear-grace", "0",
                             "--timeout", "60", *extra])

    def test_a_dropped_scheduled_run_is_named_in_the_green_summary(self, monkeypatch, capsys):
        rows = [evrun("CI", "completed", "success", "push"),
                evrun("CI", "queued", None, "schedule")]
        rc = self._main(monkeypatch, rows)
        out = capsys.readouterr().out
        assert rc == 0
        assert "(1 scheduled run not counted; --event any counts it)" in out

    def test_several_dropped_runs_are_counted_in_the_plural(self, monkeypatch, capsys):
        rows = [evrun("CI", "completed", "success", "push"),
                evrun("CI", "queued", None, "schedule"),
                evrun("nightly", "completed", "failure", "schedule")]
        assert self._main(monkeypatch, rows) == 0
        assert "(2 scheduled runs not counted; --event any counts them)" in capsys.readouterr().out

    def test_a_failed_verdict_names_it_too(self, monkeypatch, capsys):
        rows = [evrun("CI", "completed", "failure", "push"),
                evrun("CI", "queued", None, "schedule")]
        assert self._main(monkeypatch, rows) == 1
        assert "1 scheduled run not counted" in capsys.readouterr().err

    def test_control_no_scheduled_row_leaves_the_summary_unchanged(self, monkeypatch, capsys):
        rc = self._main(monkeypatch, [evrun("CI", "completed", "success", "push")])
        assert rc == 0
        assert capsys.readouterr().out == "CI=success\n"

    def test_control_event_any_reports_nothing_as_not_counted(self, monkeypatch, capsys):
        rows = [evrun("CI", "completed", "success", "push"),
                evrun("nightly", "completed", "success", "schedule")]
        assert self._main(monkeypatch, rows, "--event", "any") == 0
        assert "not counted" not in capsys.readouterr().out

    def test_json_adds_the_count_and_keeps_every_existing_key(self, monkeypatch, capsys):
        rows = [evrun("CI", "completed", "success", "push"),
                evrun("CI", "queued", None, "schedule")]
        assert self._main(monkeypatch, rows, "--json") == 0
        data = json.loads(capsys.readouterr().out)["data"]
        assert data["not_counted"] == 1
        assert {"state", "summary", "runs", "sha"} <= set(data)
        assert data["summary"] == "CI=success"

    def test_control_json_with_event_any_carries_no_count(self, monkeypatch, capsys):
        rows = [evrun("CI", "completed", "success", "push")]
        assert self._main(monkeypatch, rows, "--event", "any", "--json") == 0
        assert "not_counted" not in json.loads(capsys.readouterr().out)["data"]


class TestAwaitingApproval:
    """#92: a fork PR's run waiting for approval is not a failure, and no wait resolves it."""

    def test_action_required_is_its_own_state_and_exit_2(self):
        result = ci_wait.verdict([run("CI", "completed", "action_required")])
        assert result.state == "pending-approval"
        assert ci_wait.exit_code_for(result.state) == 2

    def test_a_real_failure_beside_it_still_reads_failed(self):
        rows = [run("CI", "completed", "action_required"), run("lint", "completed", "failure")]
        assert ci_wait.verdict(rows).state == "failed"

    def test_the_wait_returns_at_once_rather_than_spinning(self):
        polls: list[int] = []

        def fetch():
            polls.append(1)
            return [run("CI", "completed", "action_required")]

        result = ci_wait.wait_for(fetch, deadline_polls=50, sleep=lambda _s: None)
        assert result.state == "pending-approval" and len(polls) == 1

    def test_the_cli_says_so_in_the_envelope(self, monkeypatch, capsys):
        monkeypatch.setattr(ci_wait, "sha_is_known_locally", lambda sha, **kw: True)
        monkeypatch.setattr(ci_wait, "gh_runs",
                            lambda sha, **kw: [run("CI", "completed", "action_required")])
        rc = ci_wait.main(["--sha", SHA, "--json"])
        payload = json.loads(capsys.readouterr().out)
        assert rc == 2 and payload["ok"] is False
        assert payload["data"]["state"] == "pending-approval"


class TestTheRepoIsResolvedOnce:
    """#109: a worktree deleted mid-wait turned every later poll into a gh failure, because each
    poll re-resolved the repo from the cwd."""

    def test_every_poll_gets_the_repo_resolved_at_start(self, monkeypatch):
        seen: list[object] = []
        rows = iter([[run("CI", "in_progress", None)], [run("CI", "completed", "success")]])

        def fake(sha, **kw):
            seen.append(kw.get("repo"))
            return next(rows)

        monkeypatch.setattr(ci_wait, "sha_is_known_locally", lambda sha, **kw: True)
        monkeypatch.setattr(ci_wait, "gh_runs", fake)
        monkeypatch.setattr(ci_wait.time, "sleep", lambda _s: None)
        rc = ci_wait.main(["--sha", SHA, "--settle", "0"])
        assert rc == 0 and seen == ["o/r", "o/r"]

    def test_the_local_sha_check_still_runs_without_an_explicit_repo(self, monkeypatch):
        asked: list[str] = []
        monkeypatch.setattr(ci_wait, "sha_is_known_locally", lambda sha, **kw: asked.append(sha))
        monkeypatch.setattr(ci_wait, "gh_runs", lambda sha, **kw: [run("CI", "completed", "success")])
        ci_wait.main(["--sha", SHA, "--settle", "0"])
        assert asked == [SHA]

    def test_a_failed_lookup_falls_back_to_the_cwd_with_a_warning(self, monkeypatch, capsys):
        def lookup(**kw):
            raise ci_wait.GhFailed("gh exited 1: HTTP 502")

        seen: list[object] = []
        monkeypatch.setattr(ci_wait, "resolve_repo", lookup)
        monkeypatch.setattr(ci_wait, "sha_is_known_locally", lambda sha, **kw: True)
        monkeypatch.setattr(ci_wait, "gh_runs",
                            lambda sha, **kw: seen.append(kw.get("repo")) or [
                                run("CI", "completed", "success")])
        rc = ci_wait.main(["--sha", SHA, "--settle", "0"])
        assert rc == 0 and seen == [None]
        assert "warning:" in capsys.readouterr().err

    def test_gh_missing_at_lookup_is_could_not_tell(self, monkeypatch, capsys):
        def lookup(**kw):
            raise ci_wait.GhUnavailable("could not run gh: not found")

        monkeypatch.setattr(ci_wait, "resolve_repo", lookup)
        monkeypatch.setattr(ci_wait, "sha_is_known_locally", lambda sha, **kw: True)
        assert ci_wait.main(["--sha", SHA, "--json"]) == 2
        assert json.loads(capsys.readouterr().out)["data"]["state"] == "error"

    def test_resolve_repo_asks_gh_repo_view(self, monkeypatch):
        calls: list[list[str]] = []

        def fake(argv, **kw):
            calls.append(list(argv))
            return subprocess.CompletedProcess(argv, 0, stdout="owner/name\n", stderr="")

        monkeypatch.setattr(ci_wait.subprocess, "run", fake)
        assert REAL_RESOLVE_REPO() == "owner/name"
        assert calls[0][:3] == ["gh", "repo", "view"]

    @pytest.mark.parametrize("rc,stdout,exc", [(1, "", "GhFailed"), (0, "\n", "GhFailed"),
                                               (4, "", "GhUnavailable")])
    def test_resolve_repo_failures_are_typed(self, monkeypatch, rc, stdout, exc):
        monkeypatch.setattr(ci_wait.subprocess, "run",
                            lambda argv, **kw: subprocess.CompletedProcess(argv, rc, stdout=stdout,
                                                                           stderr="x"))
        with pytest.raises(getattr(ci_wait, exc)):
            REAL_RESOLVE_REPO()


# --- --ref: the jig derives the sha itself, so no caller types or pads one -------------------------
# Recurrence 9 of the invented-identifier rule (2026-10-15): a sha completed from a short one went
# into a backgrounded ci_wait, and in a worktree-isolated session the inline `$(git rev-parse ...)`
# remedy is refused by Claude Code's isolation guard. A ref the jig resolves leaves nothing to type.


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True,
                          encoding="utf-8", check=True).stdout.strip()


@pytest.fixture()
def repo(tmp_path, monkeypatch):
    """A real repository with one commit on `main`, as the cwd. git is the thing under test here."""
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    (root / "f.txt").write_text("x\n", encoding="utf-8")
    _git(root, "add", "f.txt")
    _git(root, "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "-m", "c1")
    monkeypatch.chdir(root)
    return root


class TestResolveRef:
    def test_head_resolves_to_the_full_sha_git_reports(self, repo):
        assert ci_wait.resolve_ref("HEAD") == _git(repo, "rev-parse", "HEAD")

    @pytest.mark.parametrize("ref", ["main", "HEAD~0", "refs/heads/main"])
    def test_a_branch_or_revision_expression_resolves(self, repo, ref):
        assert ci_wait.resolve_ref(ref) == _git(repo, "rev-parse", "HEAD")

    def test_an_unknown_ref_is_refused(self, repo):
        with pytest.raises(ci_wait.BadRef, match="nope"):
            ci_wait.resolve_ref("nope")

    def test_a_ref_naming_a_tree_not_a_commit_is_refused(self, repo):
        """`HEAD^{tree}` is a real object, but no CI run is keyed on a tree."""
        with pytest.raises(ci_wait.BadRef):
            ci_wait.resolve_ref("HEAD^{tree}")

    @pytest.mark.parametrize("ref", ["--all", "-q", ""])
    def test_an_option_shaped_or_empty_ref_never_reaches_git(self, ref):
        """`--all` would be read as an OPTION by rev-parse, not as a ref to resolve."""
        def must_not_run(argv, **kw):
            raise AssertionError(f"git was run: {argv}")

        with pytest.raises(ci_wait.BadRef):
            ci_wait.resolve_ref(ref, run=must_not_run)

    def test_outside_a_repository_it_is_refused(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        with pytest.raises(ci_wait.BadRef):
            ci_wait.resolve_ref("HEAD")

    def test_no_git_on_path_is_a_typed_refusal_not_a_traceback(self):
        def no_git(argv, **kw):
            raise FileNotFoundError("git")

        with pytest.raises(ci_wait.BadRef, match="git"):
            ci_wait.resolve_ref("HEAD", run=no_git)

    def test_output_that_is_not_a_full_sha_is_refused(self):
        """Never pass on whatever git printed: the format guard still decides."""
        def short(argv, **kw):
            return subprocess.CompletedProcess(argv, 0, stdout="abc1234\n", stderr="")

        with pytest.raises(ci_wait.BadRef):
            ci_wait.resolve_ref("HEAD", run=short)


class TestRefOnTheCommandLine:
    def test_main_polls_the_resolved_sha_and_names_it(self, repo, monkeypatch, capsys):
        asked: list[str] = []

        def fake_runs(sha, **kw):
            asked.append(sha)
            return [run("CI", "completed", "success", sha=sha)]

        monkeypatch.setattr(ci_wait, "gh_runs", fake_runs)
        head = _git(repo, "rev-parse", "HEAD")
        assert ci_wait.main(["--ref", "HEAD", "--settle", "0"]) == 0
        assert asked and set(asked) == {head}
        assert f"resolved HEAD to {head}" in capsys.readouterr().err

    def test_the_json_envelope_carries_the_resolved_sha(self, repo, monkeypatch, capsys):
        monkeypatch.setattr(ci_wait, "gh_runs", lambda sha, **kw: [run("CI", "completed", "success", sha=sha)])
        assert ci_wait.main(["--ref", "main", "--settle", "0", "--json"]) == 0
        data = json.loads(capsys.readouterr().out)["data"]
        assert data["sha"] == _git(repo, "rev-parse", "HEAD")

    def test_an_unresolvable_ref_is_could_not_tell_and_never_polls(self, repo, monkeypatch, capsys):
        def must_not_poll(sha, **kw):
            raise AssertionError("polled")

        monkeypatch.setattr(ci_wait, "gh_runs", must_not_poll)
        assert ci_wait.main(["--ref", "nope", "--json"]) == 2
        envelope = json.loads(capsys.readouterr().out)
        assert envelope["ok"] is False and envelope["data"]["state"] == "error"
        assert "nope" in envelope["error"]

    @pytest.mark.parametrize("argv,message", [
        (["--sha", "a" * 40, "--ref", "HEAD"], "not allowed with argument"),
        ([], "one of the arguments --sha --ref is required"),
    ])
    def test_exactly_one_of_sha_and_ref_is_required(self, argv, message, capsys):
        """A usage error, through the envelope parser like every other one: SystemExit(2).

        The MESSAGE is asserted, not only the exit: before --ref existed the first case also exited
        2, because argparse refused `--ref` as an unknown flag.
        """
        with pytest.raises(SystemExit) as info:
            ci_wait.main([*argv, "--json"])
        assert info.value.code == 2
        envelope = json.loads(capsys.readouterr().out)
        assert envelope["ok"] is False
        assert message in envelope["error"]



def queued_row(workflow: str, run_id: int, status: str = "queued", conclusion: str | None = None,
               event: str = "workflow_run") -> dict[str, object]:
    """A run row with its own id, so the stuck-queued verdict can name WHICH run is stuck."""
    return {"headSha": SHA, "workflowName": workflow, "status": status, "conclusion": conclusion,
            "databaseId": run_id, "event": event}


class TestARunNoRunnerPicksUpIsReportedNotWaitedOut:
    """Measured 2026-10-19: a second workflow_run trigger of a release workflow sat `queued` for 35
    minutes with no runner while its twin on the same sha had already published the release, and
    the wait polled it 73 times to the deadline. A run queued past --queued-grace with nothing else
    still going is a verdict of its own, naming the run."""

    def test_a_run_queued_past_the_grace_ends_the_wait_naming_its_id(self):
        polls: list[int] = []

        def fetch():
            polls.append(1)
            return [queued_row("release", 777)]

        result = ci_wait.wait_for(fetch, deadline_polls=200, sleep=lambda _s: None,
                                  interval_s=30.0, queued_grace_s=600.0)

        assert result.state == "stuck-queued"
        assert "777" in result.summary
        assert len(polls) == 21  # queued at 0, 30, ... 600s: the whole grace was waited, no more
        assert ci_wait.exit_code_for(result.state) == 2

    def test_a_sibling_success_of_the_same_workflow_is_named_as_a_likely_duplicate(self):
        rows = [queued_row("release", 777),
                queued_row("release", 555, status="completed", conclusion="success"),
                queued_row("ci", 111, status="completed", conclusion="success", event="push")]

        result = ci_wait.wait_for(lambda: rows, deadline_polls=200, sleep=lambda _s: None,
                                  interval_s=30.0, queued_grace_s=60.0)

        assert result.state == "stuck-queued"
        assert "555" in result.summary and "duplicate" in result.summary

    def test_without_a_sibling_success_it_does_not_claim_a_duplicate(self):
        rows = [queued_row("release", 777),
                queued_row("ci", 111, status="completed", conclusion="success", event="push")]

        result = ci_wait.wait_for(lambda: rows, deadline_polls=200, sleep=lambda _s: None,
                                  interval_s=30.0, queued_grace_s=60.0)

        assert result.state == "stuck-queued"
        assert "duplicate" not in result.summary

    def test_a_run_that_starts_inside_the_grace_is_waited_for_as_before(self):
        """Control: queued for a while and then picked up is the ordinary case, never stuck."""
        polls = [[queued_row("ci", 1)]] * 2 + [[queued_row("ci", 1, status="in_progress")]] * 3 \
            + [[queued_row("ci", 1, status="completed", conclusion="success")]] * 2

        calls: list[int] = []

        def fetch():
            calls.append(1)
            return polls[min(len(calls) - 1, len(polls) - 1)]

        result = ci_wait.wait_for(fetch, deadline_polls=200, sleep=lambda _s: None,
                                  interval_s=30.0, queued_grace_s=60.0)

        assert result.state == "success"

    def test_the_queued_clock_restarts_when_a_run_leaves_queued(self):
        """A run that went in_progress and back to queued (a re-run of a job) starts a new streak,
        so two short queued spells never add up to one long one."""
        spell = [[queued_row("ci", 1)]] * 2 + [[queued_row("ci", 1, status="in_progress")]]
        polls = spell * 4 + [[queued_row("ci", 1, status="completed", conclusion="success")]] * 2
        calls: list[int] = []

        def fetch():
            calls.append(1)
            return polls[min(len(calls) - 1, len(polls) - 1)]

        result = ci_wait.wait_for(fetch, deadline_polls=200, sleep=lambda _s: None,
                                  interval_s=30.0, queued_grace_s=60.0)

        assert result.state == "success"

    def test_a_queued_run_beside_one_still_running_keeps_the_wait_open(self):
        """Only a run with NOTHING else going is stuck: while another run works, its outcome is
        still coming, and a failure there must be reported as a failure."""
        polls = [[queued_row("release", 777), queued_row("ci", 1, status="in_progress", event="push")]] * 5 \
            + [[queued_row("release", 777), queued_row("ci", 1, status="completed", conclusion="failure",
                                                       event="push")]]
        calls: list[int] = []

        def fetch():
            calls.append(1)
            return polls[min(len(calls) - 1, len(polls) - 1)]

        result = ci_wait.wait_for(fetch, deadline_polls=200, sleep=lambda _s: None,
                                  interval_s=30.0, queued_grace_s=60.0)

        assert len(calls) >= 6, "the wait must not end while the ci run is still in progress"
        assert result.state == "failed"
        assert "ci=failure" in result.summary and "release=queued" in result.summary

    def test_a_grace_of_zero_disables_the_check(self):
        result = ci_wait.wait_for(lambda: [queued_row("release", 777)], deadline_polls=5,
                                  sleep=lambda _s: None, interval_s=30.0, queued_grace_s=0.0)
        assert result.state == "timeout"

    def test_the_cli_takes_the_flag_and_reports_the_state_in_the_envelope(self, monkeypatch, capsys):
        monkeypatch.setattr(ci_wait, "sha_is_known_locally", lambda sha, **kw: True)
        monkeypatch.setattr(ci_wait, "gh_runs", lambda sha, **kw: [queued_row("release", 777)])
        monkeypatch.setattr(ci_wait, "gh_run_started", lambda rid, **kw: False)
        monkeypatch.setattr(ci_wait.time, "sleep", lambda _s: None)
        clock = iter(range(0, 100000, 30))
        monkeypatch.setattr(ci_wait.time, "monotonic", lambda: next(clock))

        rc = ci_wait.main(["--sha", SHA, "--json", "--queued-grace", "300"])

        payload = json.loads(capsys.readouterr().out)
        assert rc == 2 and payload["ok"] is False
        assert payload["data"]["state"] == "stuck-queued"
        assert "777" in payload["error"]


class TestARunWhoseJobsStartedIsNotStuck:
    """Measured 2026-10-23, run 39932914131: the run's own status stayed `queued` for 15 minutes
    while three of its five jobs had completed success and windows was in_progress - only the
    macos-latest job was waiting for a hosted runner. The wait read the RUN status, reported
    'queued ... with no runner starting it' and exited 2. A run with any job started is running."""

    @staticmethod
    def _queued_then_green(calls: list[int]):
        polls = [[queued_row("ci", 1, event="push")]] * 40 \
            + [[queued_row("ci", 1, status="completed", conclusion="success", event="push")]] * 2

        def fetch():
            calls.append(1)
            return polls[min(len(calls) - 1, len(polls) - 1)]

        return fetch

    def test_a_queued_run_with_a_started_job_is_waited_out_to_its_verdict(self):
        calls: list[int] = []
        asked: list[object] = []

        def started(run_id):
            asked.append(run_id)
            return True

        result = ci_wait.wait_for(self._queued_then_green(calls), deadline_polls=200,
                                  sleep=lambda _s: None, interval_s=30.0, queued_grace_s=60.0,
                                  run_started=started)

        assert result.state == "success"
        assert asked and set(asked) == {1}

    def test_a_queued_run_whose_jobs_are_all_queued_is_still_stuck(self):
        """Control: the duplicate-trigger case the check exists for keeps its verdict."""
        result = ci_wait.wait_for(lambda: [queued_row("release", 777)], deadline_polls=200,
                                  sleep=lambda _s: None, interval_s=30.0, queued_grace_s=60.0,
                                  run_started=lambda _rid: False)

        assert result.state == "stuck-queued"
        assert "777" in result.summary

    def test_an_unreadable_job_list_never_proves_a_run_stuck(self):
        """Unknown is not 'no job started': the wait goes on, and the deadline still bounds it."""
        calls: list[int] = []

        result = ci_wait.wait_for(self._queued_then_green(calls), deadline_polls=200,
                                  sleep=lambda _s: None, interval_s=30.0, queued_grace_s=60.0,
                                  run_started=lambda _rid: None)

        assert result.state == "success"

    def test_the_job_list_is_not_read_before_the_grace_runs_out(self):
        asked: list[object] = []

        def started(run_id):
            asked.append(run_id)
            return True

        polls = [[queued_row("ci", 1, event="push")]] * 2 \
            + [[queued_row("ci", 1, status="completed", conclusion="success", event="push")]] * 2
        calls: list[int] = []

        def fetch():
            calls.append(1)
            return polls[min(len(calls) - 1, len(polls) - 1)]

        result = ci_wait.wait_for(fetch, deadline_polls=200, sleep=lambda _s: None,
                                  interval_s=30.0, queued_grace_s=600.0, run_started=started)

        assert result.state == "success"
        assert asked == []


def jobs_gh(jobs: object, calls: list[list[str]], rc: int = 0):
    """`gh run view <id> --json jobs` answering ``{"jobs": jobs}`` (or failing with ``rc``)."""

    def fake_run(argv, **kwargs):
        calls.append(list(argv))
        if rc:
            return subprocess.CompletedProcess(argv, rc, stdout="", stderr="HTTP 502")
        return subprocess.CompletedProcess(argv, 0, stdout=json.dumps({"jobs": jobs}), stderr="")

    return fake_run


class TestGhRunStarted:
    """`gh_run_started` asks the run's own jobs, the only place a started job shows."""

    def test_a_completed_or_running_job_means_started(self, monkeypatch):
        calls: list[list[str]] = []
        monkeypatch.setattr(ci_wait.subprocess, "run", jobs_gh(
            [{"status": "completed"}, {"status": "queued"}], calls))

        assert ci_wait.gh_run_started(39932914131, repo="o/r") is True
        assert calls[0][:5] == ["gh", "run", "view", "39932914131", "--json"]
        assert "jobs" in calls[0] and calls[0][-2:] == ["--repo", "o/r"]

    def test_in_progress_alone_means_started(self, monkeypatch):
        monkeypatch.setattr(ci_wait.subprocess, "run", jobs_gh([{"status": "in_progress"}], []))
        assert ci_wait.gh_run_started(5) is True

    def test_only_queued_or_waiting_jobs_mean_not_started(self, monkeypatch):
        monkeypatch.setattr(ci_wait.subprocess, "run", jobs_gh(
            [{"status": "queued"}, {"status": "waiting"}], []))
        assert ci_wait.gh_run_started(5) is False

    def test_no_jobs_yet_means_not_started(self, monkeypatch):
        monkeypatch.setattr(ci_wait.subprocess, "run", jobs_gh([], []))
        assert ci_wait.gh_run_started(5) is False

    def test_a_failed_read_answers_unknown(self, monkeypatch):
        monkeypatch.setattr(ci_wait.subprocess, "run", jobs_gh(None, [], rc=1))
        assert ci_wait.gh_run_started(5) is None

    def test_a_malformed_answer_is_unknown(self, monkeypatch):
        monkeypatch.setattr(ci_wait.subprocess, "run", jobs_gh("not a list", []))
        assert ci_wait.gh_run_started(5) is None

    def test_the_incident_through_the_command_line_is_not_stuck(self, monkeypatch, capsys):
        """Run 39932914131's shape end to end: the listing says queued, the jobs say running."""
        monkeypatch.setattr(ci_wait, "sha_is_known_locally", lambda sha, **kw: True)
        listing = [queued_row("ci", 39932914131, event="push")]
        monkeypatch.setattr(ci_wait, "gh_runs", lambda sha, **kw: listing)
        monkeypatch.setattr(ci_wait, "gh_run", lambda rid, **kw: listing[0])
        monkeypatch.setattr(ci_wait, "gh_run_started", lambda rid, **kw: True)
        monkeypatch.setattr(ci_wait.time, "sleep", lambda _s: None)
        clock = iter(range(0, 100000, 30))
        monkeypatch.setattr(ci_wait.time, "monotonic", lambda: next(clock))

        rc = ci_wait.main(["--sha", SHA, "--repo", "o/r", "--json", "--queued-grace", "300",
                           "--timeout", "1200"])

        payload = json.loads(capsys.readouterr().out)
        assert rc == 2
        assert payload["data"]["state"] == "timeout"


def vanishing_gh(listings: list[list[dict[str, object]]], by_id: dict[int, dict[str, object]],
                 calls: list[list[str]]):
    """`gh run list` answering ``listings`` in turn (the last repeats), `gh run view <id>` answering
    from ``by_id`` - the shape GitHub served on 2026-10-22, where the head_sha-filtered listing
    dropped runs it had already returned while each run stayed readable by its id."""

    def fake_run(argv, **kwargs):
        calls.append(list(argv))
        if argv[1:3] == ["run", "view"]:
            row = by_id.get(int(argv[3]))
            if row is None:
                return subprocess.CompletedProcess(argv, 1, stdout="", stderr="HTTP 404: Not Found")
            return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(row), stderr="")
        listed = sum(1 for c in calls if c[1:3] == ["run", "list"])
        rows = listings[min(listed - 1, len(listings) - 1)]
        return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(rows), stderr="")

    return fake_run


def row_id(workflow: str, run_id: int, status: str, conclusion: str | None) -> dict[str, object]:
    return {**run(workflow, status, conclusion), "databaseId": run_id, "event": "push"}


class TestARunThatVanishesFromTheListingIsReReadById:
    """Measured 2026-10-22 on a real push: `gh run list --commit <sha>` returned the ci run as
    in_progress for 27 polls, then [] while that run completed green, and `gh run list --commit`
    kept answering [] minutes later while `gh run view <id>` and the unfiltered runs API both
    showed it completed success. The wait spent its appear-grace on the empty listing and exited 2
    'no runs found for that sha' - for a sha it had watched running. A run once seen is a fact; the
    listing losing it is the index lagging, not the run ceasing to exist."""

    def test_the_incident_through_the_command_line_ends_green(self, monkeypatch, capsys):
        monkeypatch.setattr(ci_wait, "sha_is_known_locally", lambda sha, **kw: True)
        monkeypatch.setattr(ci_wait.time, "sleep", lambda _s: None)
        calls: list[list[str]] = []
        listings = [[row_id("ci", 7, "in_progress", None)], []]
        by_id = {7: row_id("ci", 7, "completed", "success")}
        monkeypatch.setattr(ci_wait.subprocess, "run", vanishing_gh(listings, by_id, calls))

        rc = ci_wait.main(["--sha", SHA, "--appear-grace", "0", "--settle", "0"])

        assert rc == 0, "a run seen in_progress and then dropped by the listing must be re-read"
        assert any(c[1:4] == ["run", "view", "7"] for c in calls)
        assert "re-read" in capsys.readouterr().err

    def test_a_vanished_failure_beside_a_listed_success_is_still_a_failure(self):
        """The worse half: a PARTIAL drop. Judged on what the listing still shows, the failing run
        is gone and the remaining success reads as a green push."""
        listings = iter([
            [row_id("ci", 1, "in_progress", None), row_id("codeql", 2, "completed", "success")],
            [row_id("codeql", 2, "completed", "success")],
        ])
        reread: list[object] = []

        def fetch_one(run_id):
            reread.append(run_id)
            return row_id("ci", 1, "completed", "failure")

        fetch = ci_wait.keep_seen_runs(lambda: next(listings), fetch_one)
        fetch()
        result = ci_wait.verdict(fetch())

        assert reread == [1]
        assert result.state == "failed"

    def test_a_sha_never_seen_with_runs_reads_no_runs_without_any_re_read(self):
        fetch_one_calls: list[object] = []
        fetch = ci_wait.keep_seen_runs(list, lambda rid: fetch_one_calls.append(rid) or {})

        assert ci_wait.verdict(fetch()).state == "no-runs"
        assert fetch_one_calls == []

    def test_a_run_still_listed_is_not_re_read(self):
        """The re-read costs one gh call per vanished run; a run the listing still carries must
        never cost one, or every poll doubles its API spend."""
        fetch_one_calls: list[object] = []
        rows = [row_id("ci", 3, "in_progress", None)]
        fetch = ci_wait.keep_seen_runs(lambda: rows, lambda rid: fetch_one_calls.append(rid) or {})

        fetch()
        fetch()

        assert fetch_one_calls == []

    def test_the_listing_answer_wins_once_the_run_is_listed_again(self):
        listings = iter([[row_id("ci", 4, "in_progress", None)], [],
                         [row_id("ci", 4, "completed", "success")]])
        fetch = ci_wait.keep_seen_runs(lambda: next(listings),
                                       lambda rid: row_id("ci", 4, "in_progress", None))
        fetch()
        fetch()

        assert ci_wait.verdict(fetch()).state == "success"


class TestGhRun:
    """`gh run view <id>`: the by-id read the vanished-run fallback relies on."""

    def test_it_asks_for_the_same_fields_and_the_repo(self, monkeypatch):
        calls: list[list[str]] = []
        monkeypatch.setattr(ci_wait.subprocess, "run",
                            vanishing_gh([[]], {9: row_id("ci", 9, "completed", "success")}, calls))

        row = ci_wait.gh_run(9, repo="o/r")

        assert row["conclusion"] == "success"
        assert calls[0][:4] == ["gh", "run", "view", "9"]
        assert calls[0][calls[0].index("--json") + 1] == ci_wait._FIELDS
        assert calls[0][calls[0].index("--repo") + 1] == "o/r"

    def test_a_run_gh_cannot_read_is_raised_for_the_retry_budget(self, monkeypatch):
        """A deleted run answers HTTP 404 with exit 1. Raised as GhFailed, never dropped: dropping
        it is the vanished-run defect again, one call later."""
        monkeypatch.setattr(ci_wait.subprocess, "run", vanishing_gh([[]], {}, []))

        with pytest.raises(ci_wait.GhFailed):
            ci_wait.gh_run(5)

    def test_an_answer_that_is_not_one_row_is_raised(self, monkeypatch):
        monkeypatch.setattr(ci_wait.subprocess, "run",
                            lambda argv, **kw: subprocess.CompletedProcess(argv, 0, stdout="[]", stderr=""))

        with pytest.raises(ci_wait.GhFailed):
            ci_wait.gh_run(5)



# --- job-level reading: a run's own status hides what its jobs are doing ----------------------


def job(name: str, status: str, conclusion: str | None = None) -> dict[str, object]:
    """One `gh run view --json jobs` entry."""
    return {"name": name, "status": status, "conclusion": conclusion}


def _cells(done: int, *rest: dict[str, object]) -> list[dict[str, object]]:
    return [job(f"test ({i})", "completed", "success") for i in range(done)] + list(rest)


class TestTallyJobs:
    def test_counts_done_running_queued_and_names_the_queued_and_failed(self):
        tally = ci_wait.tally_jobs(_cells(14, job("lint", "completed", "failure"),
                                          job("win", "in_progress"),
                                          job("test (macos-latest)", "queued")))
        assert (tally.done, tally.running, tally.queued, tally.total) == (15, 1, 1, 17)
        assert tally.queued_names == ("test (macos-latest)",)
        assert tally.failed_names == ("lint",)

    @pytest.mark.parametrize("conclusion", ["failure", "timed_out"])
    def test_a_failure_or_timeout_is_a_failed_job(self, conclusion):
        assert ci_wait.tally_jobs([job("a", "completed", conclusion)]).failed_names == ("a",)

    @pytest.mark.parametrize("conclusion", ["success", "skipped", "cancelled", "neutral"])
    def test_other_conclusions_are_not_failed_jobs(self, conclusion):
        assert ci_wait.tally_jobs([job("a", "completed", conclusion)]).failed_names == ()

    def test_waiting_and_pending_count_as_queued(self):
        tally = ci_wait.tally_jobs([job("a", "waiting"), job("b", "pending")])
        assert tally.queued == 2


class TestPerJobProgress:
    """1775aa1c / 713ff207: 35+ polls of `CI=queued` while 15 of 16 jobs were green and one
    macos-latest job waited for a runner. The poll line must say what the jobs are doing."""

    def test_each_pending_poll_names_the_job_counts_and_the_queued_job(self):
        lines: list[str] = []
        now = [0.0]
        jobs = _cells(15, job("test (macos-latest)", "queued"))

        def sleep(s):
            now[0] += s

        result = ci_wait.wait_for(lambda: [run("CI", "queued", None)], deadline_s=200.0,
                                  sleep=sleep, clock=lambda: now[0], interval_s=60.0,
                                  report=lines.append, run_jobs=lambda _rid: jobs,
                                  queued_grace_s=0)
        assert result.state == "timeout"
        assert "15/16 jobs done" in lines[0] and "test (macos-latest)" in lines[0], lines
        assert "queued 2m" in lines[2] or "queued 120s" in lines[2], lines
        assert "15/16 jobs done" in result.summary, result.summary

    def test_no_job_reader_keeps_the_old_line(self):
        lines: list[str] = []
        ci_wait.wait_for(lambda: [run("CI", "in_progress", None)], deadline_polls=1,
                         sleep=lambda _s: None, report=lines.append)
        assert lines == ["poll 1/1: CI=in_progress"]

    def test_an_unreadable_job_list_says_so_rather_than_inventing_counts(self):
        lines: list[str] = []
        ci_wait.wait_for(lambda: [run("CI", "in_progress", None)], deadline_polls=1,
                         sleep=lambda _s: None, report=lines.append, run_jobs=lambda _rid: None)
        assert "jobs" not in lines[0] or "not read" in lines[0], lines


class TestAFailedJobInAnUnfinishedRun:
    """99e2eca2: six Windows jobs failed within 3 minutes, one macOS job stayed queued, and the
    wait polled `CI=queued` for 25 minutes and exited 2 for a run that had certainly failed."""

    @staticmethod
    def _rows():
        return [run("CI", "queued", None)]

    @staticmethod
    def _jobs(_rid):
        return _cells(3, job("test (windows-latest)", "completed", "failure"),
                      job("test (macos-latest)", "queued"))

    def test_it_is_named_on_every_poll_and_in_the_timeout(self):
        lines: list[str] = []
        result = ci_wait.wait_for(self._rows, deadline_polls=2, sleep=lambda _s: None,
                                  report=lines.append, run_jobs=self._jobs, queued_grace_s=0)
        assert "failed: test (windows-latest)" in lines[0], lines
        assert result.state == "timeout"
        assert "test (windows-latest)" in result.summary

    def test_with_fail_on_failed_job_it_ends_the_wait_as_failed_at_once(self):
        polls: list[int] = []

        def fetch():
            polls.append(1)
            return self._rows()

        result = ci_wait.wait_for(fetch, deadline_polls=50, sleep=lambda _s: None,
                                  run_jobs=self._jobs, fail_on_failed_job=True)
        assert result.state == "failed" and len(polls) == 1
        assert "test (windows-latest)" in result.summary

    def test_control_without_a_failed_job_the_flag_changes_nothing(self):
        result = ci_wait.wait_for(self._rows, deadline_polls=2, sleep=lambda _s: None,
                                  run_jobs=lambda _rid: _cells(2, job("m", "queued")),
                                  fail_on_failed_job=True, queued_grace_s=0)
        assert result.state == "timeout"


class TestARunThatAlreadyFailedBesideOneStillGoing:
    """Review finding: a run that had CONCLUDED failure beside one still in progress was never
    reported. The verdict read `pending` while any run was unfinished, and the per-job check skips
    terminal runs, so the wait timed out (exit 2) on a push that had certainly failed."""

    @staticmethod
    def _rows():
        return [{**run("CI", "completed", "failure"), "databaseId": 1},
                {**run("Docs", "in_progress", None), "databaseId": 2}]

    @staticmethod
    def _jobs(rid):
        return [job("test", "completed", "failure")] if rid == 1 else [job("build", "in_progress")]

    def _wait(self, **kw):
        polls: list[int] = []

        def fetch():
            polls.append(1)
            return self._rows()

        now = [0.0]
        result = ci_wait.wait_for(fetch, deadline_s=100.0, interval_s=30.0, clock=lambda: now[0],
                                  sleep=lambda s: now.__setitem__(0, now[0] + s),
                                  run_jobs=self._jobs, **kw)
        return result, len(polls)

    def test_with_fail_on_failed_job_it_ends_as_failed_at_once(self):
        result, polls = self._wait(fail_on_failed_job=True)
        assert (result.state, polls) == ("failed", 1), result
        assert ci_wait.exit_code_for(result.state) == 1

    def test_without_the_flag_it_also_ends_as_failed_at_once(self):
        """A completed run's failure is final - no later run rescues it - so the module's
        'a failure is reported at once' holds whatever else is still going."""
        result, polls = self._wait()
        assert (result.state, polls) == ("failed", 1), result
        assert "CI=failure" in result.summary and "Docs=in_progress" in result.summary

    def test_the_verdict_alone_names_the_failure_and_what_is_still_going(self):
        verdict = ci_wait.verdict(self._rows())
        assert verdict.state == "failed"
        assert "CI=failure" in verdict.summary and "Docs=in_progress" in verdict.summary

    def test_control_a_success_beside_a_run_still_going_is_still_pending(self):
        rows = [run("CI", "completed", "success"), run("Docs", "in_progress", None)]
        assert ci_wait.verdict(rows).state == "pending"


class TestSuccessNeedsEveryJobFinished:
    """a389f515: run 39794411508 read completed/success and the wait exited 0 while its jobs
    endpoint still showed 9 of 18 jobs in_progress or queued."""

    def test_a_green_run_with_unfinished_jobs_is_waited_for(self):
        answers = iter([_cells(9, job("mac", "in_progress"))] * 2 + [_cells(10)] * 10)
        lines: list[str] = []
        result = ci_wait.wait_for(lambda: [run("CI", "completed", "success")], deadline_polls=20,
                                  sleep=lambda _s: None, settle_s=5.0, report=lines.append,
                                  run_jobs=lambda _rid: next(answers))
        assert result.state == "success"
        assert any("mac" in line and "not finished" in line for line in lines), lines

    def test_it_never_reports_success_while_a_job_is_running(self):
        result = ci_wait.wait_for(lambda: [run("CI", "completed", "success")], deadline_polls=4,
                                  sleep=lambda _s: None, settle_s=0,
                                  run_jobs=lambda _rid: _cells(3, job("mac", "queued")))
        assert result.state == "timeout"
        assert "mac" in result.summary

    def test_an_unreadable_job_list_keeps_the_run_level_answer(self):
        result = ci_wait.wait_for(lambda: [run("CI", "completed", "success")], deadline_polls=4,
                                  sleep=lambda _s: None, settle_s=0, run_jobs=lambda _rid: None)
        assert result.state == "success"


class TestGhRunJobs:
    def test_it_reads_the_jobs_of_one_run(self, monkeypatch):
        calls: list[list[str]] = []
        monkeypatch.setattr(ci_wait.subprocess, "run", jobs_gh([job("a", "queued")], calls))
        assert REAL_GH_RUN_JOBS(7, repo="o/r") == [job("a", "queued")]
        assert calls[0][:4] == ["gh", "run", "view", "7"] and calls[0][-2:] == ["--repo", "o/r"]

    def test_a_failed_read_is_unknown(self, monkeypatch):
        monkeypatch.setattr(ci_wait.subprocess, "run", jobs_gh(None, [], rc=1))
        assert REAL_GH_RUN_JOBS(7) is None


class TestTheDeadlineCuttingTheLastGhCall:
    """b76cc15a / 32998619: --timeout 580 ended rc 2 with 'gh did not answer within 1s' on a run
    still in_progress: the final call was bounded by the second left, failed, and read as an
    API outage."""

    def test_a_failure_of_the_call_the_deadline_cut_reports_a_timeout(self):
        answers = iter([[run("CI", "in_progress", None)]])
        now = [0.0]

        def fetch():
            try:
                return next(answers)
            except StopIteration:
                raise ci_wait.GhFailed("gh did not answer within 1s") from None

        def sleep(s):
            now[0] += s

        result = ci_wait.wait_for(fetch, deadline_s=60.0, sleep=sleep, clock=lambda: now[0],
                                  interval_s=30.0, error_grace_s=300.0)
        assert result.state == "timeout", result
        assert "CI=in_progress" in result.summary and "deadline" in result.summary

    def test_the_cli_never_bounds_a_gh_call_below_its_floor(self, monkeypatch):
        bounds: list[float] = []
        now = [0.0]

        def pending(sha, **kw):
            bounds.append(kw["timeout_s"])
            return [run("CI", "in_progress", None)]

        monkeypatch.setattr(ci_wait, "sha_is_known_locally", lambda sha, **kw: True)
        monkeypatch.setattr(ci_wait, "gh_runs", pending)
        monkeypatch.setattr(ci_wait.time, "monotonic", lambda: now[0])
        monkeypatch.setattr(ci_wait.time, "sleep", lambda s: now.__setitem__(0, now[0] + s))
        ci_wait.main(["--sha", SHA, "--timeout", "61", "--interval", "30"])
        assert min(bounds) >= ci_wait.GH_CALL_FLOOR_S >= 10.0, bounds


class TestTimeoutDefaultAndExpectedDuration:
    """b76cc15a: the default --timeout 1500 was shorter than this repo's own ci run (24 m 51 s),
    and the timeout said nothing about how long the run normally takes."""

    def test_the_default_timeout_outlasts_a_25_minute_run(self):
        assert ci_wait._parse_args(["--sha", SHA]).timeout >= 3600.0

    def test_a_timeout_names_how_long_the_unfinished_workflow_usually_takes(self, monkeypatch,
                                                                         capsys):
        monkeypatch.setattr(ci_wait, "sha_is_known_locally", lambda sha, **kw: True)
        monkeypatch.setattr(ci_wait, "gh_runs", lambda sha, **kw: [run("ci", "in_progress", None)])
        monkeypatch.setattr(ci_wait, "gh_typical_duration", lambda wf, **kw: 1491.0)
        now = [0.0]
        monkeypatch.setattr(ci_wait.time, "monotonic", lambda: now[0])
        monkeypatch.setattr(ci_wait.time, "sleep", lambda s: now.__setitem__(0, now[0] + s))
        rc = ci_wait.main(["--sha", SHA, "--timeout", "10", "--interval", "5"])
        err = capsys.readouterr().err
        assert rc == 2
        assert "ci usually takes 24m51s" in err, err

    def test_gh_typical_duration_is_the_median_of_recent_successful_runs(self, monkeypatch):
        rows = [{"createdAt": "2026-10-22T10:00:00Z", "updatedAt": f"2026-10-22T10:{m:02d}:00Z"}
                for m in (20, 25, 30)]
        calls: list[list[str]] = []

        def fake(argv, **kw):
            calls.append(list(argv))
            return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(rows), stderr="")

        monkeypatch.setattr(ci_wait.subprocess, "run", fake)
        assert REAL_GH_TYPICAL_DURATION("ci", repo="o/r") == 25 * 60.0
        assert "--workflow" in calls[0] and "ci" in calls[0] and "success" in calls[0]

    def test_gh_typical_duration_with_no_history_is_unknown(self, monkeypatch):
        monkeypatch.setattr(ci_wait.subprocess, "run",
                            lambda argv, **kw: subprocess.CompletedProcess(argv, 0, stdout="[]",
                                                                           stderr=""))
        assert REAL_GH_TYPICAL_DURATION("ci") is None


class TestAWorkflowFilter:
    """a389f515: waiting on only the Release workflow after `make release` needed a hand-picked
    run id and `gh run watch`; --sha alone also waits on CI and CodeQL."""

    def test_the_cli_value_reaches_gh_server_side(self, monkeypatch):
        calls: list[list[str]] = []
        monkeypatch.setattr(ci_wait.subprocess, "run", event_gh(
            [evrun("Release", "completed", "success", "push")], calls))
        monkeypatch.setattr(ci_wait.time, "sleep", lambda _s: None)
        rc = ci_wait.main(["--sha", SHA, "--repo", "o/r", "--settle", "0", "--timeout", "60",
                           "--workflow", "Release"])
        assert rc == 0
        listing = [c for c in calls if c[:3] == ["gh", "run", "list"]]
        assert listing and listing[0][listing[0].index("--workflow") + 1] == "Release"

    def test_no_runs_under_a_workflow_filter_names_it(self):
        assert "Release" in ci_wait.verdict([], workflow="Release").summary


class TestARepoGivenAsALocalPath:
    """32998619: --repo given a checkout path made every gh poll fail and the wait ended rc 2 with
    no verdict, after polling nothing until its deadline."""

    def test_an_existing_directory_is_resolved_to_its_owner_and_name(self, monkeypatch, tmp_path):
        asked: list[object] = []
        seen: list[object] = []
        monkeypatch.setattr(ci_wait, "resolve_repo", lambda **kw: asked.append(kw.get("cwd"))
                            or "owner/name")
        monkeypatch.setattr(ci_wait, "gh_runs", lambda sha, **kw: seen.append(kw.get("repo"))
                            or [run("CI", "completed", "success")])
        rc = ci_wait.main(["--sha", SHA, "--repo", str(tmp_path), "--settle", "0"])
        assert rc == 0
        assert asked == [str(tmp_path)] and seen == ["owner/name"]

    @pytest.mark.parametrize("value", ["./no/such/dir", "a b/c", "o/r/x/y", "/abs/missing"])
    def test_a_value_that_is_neither_a_directory_nor_owner_name_is_refused(self, value, capsys,
                                                                          monkeypatch):
        polled: list[int] = []
        monkeypatch.setattr(ci_wait, "gh_runs", lambda sha, **kw: polled.append(1) or [])
        rc = ci_wait.main(["--sha", SHA, "--repo", value, "--json"])
        assert rc == 2 and polled == []
        assert "OWNER/NAME" in json.loads(capsys.readouterr().out)["error"]

    @pytest.mark.parametrize("value", ["o/r", "bitranox/bitranox-skills", "ghe.example.com/o/r"])
    def test_owner_name_forms_pass_untouched(self, value, monkeypatch):
        seen: list[object] = []
        monkeypatch.setattr(ci_wait, "gh_runs", lambda sha, **kw: seen.append(kw.get("repo"))
                            or [run("CI", "completed", "success")])
        assert ci_wait.main(["--sha", SHA, "--repo", value, "--settle", "0"]) == 0
        assert seen == [value]


class TestANoRunsVerdictNamesTheLiveCauses:
    """b76cc15a: 'no runs found for that sha' read as broken CI and invited a retry loop, when
    the push went to a branch the workflows' on: push: branches exclude, or the sha is not on
    origin (a peer's rebase republished it under a new sha)."""

    def _main(self, monkeypatch, on_remote):
        monkeypatch.setattr(ci_wait, "sha_is_known_locally", lambda sha, **kw: True)
        monkeypatch.setattr(ci_wait, "gh_runs", lambda sha, **kw: [])
        monkeypatch.setattr(ci_wait, "sha_on_a_remote", lambda sha, **kw: on_remote)
        monkeypatch.setattr(ci_wait.time, "sleep", lambda _s: None)
        return ci_wait.main(["--sha", SHA, "--appear-grace", "0", "--json"])

    def test_it_names_the_branch_filter_cause(self, monkeypatch, capsys):
        assert self._main(monkeypatch, True) == 2
        summary = json.loads(capsys.readouterr().out)["data"]["summary"]
        assert "on: push" in summary and "branches" in summary, summary

    def test_a_sha_on_no_remote_branch_says_so(self, monkeypatch, capsys):
        self._main(monkeypatch, False)
        summary = json.loads(capsys.readouterr().out)["data"]["summary"]
        assert "no remote-tracking branch" in summary and "rebase" in summary, summary

    def test_control_a_sha_on_a_remote_does_not_claim_otherwise(self, monkeypatch, capsys):
        self._main(monkeypatch, True)
        assert "no remote-tracking branch" not in json.loads(capsys.readouterr().out)["data"][
            "summary"]

    def test_sha_on_a_remote_reads_git(self, repo):
        sha = _git(repo, "rev-parse", "HEAD")
        assert REAL_SHA_ON_A_REMOTE(sha) is False
        _git(repo, "update-ref", "refs/remotes/origin/main", sha)
        assert REAL_SHA_ON_A_REMOTE(sha) is True

    def test_sha_on_a_remote_outside_a_repository_is_unknown(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        assert REAL_SHA_ON_A_REMOTE(SHA) is None


class TestTheNewFlagsReachTheLoop:
    def test_fail_on_failed_job_and_the_job_reader_are_wired(self, monkeypatch):
        seen: dict[str, object] = {}
        monkeypatch.setattr(ci_wait, "sha_is_known_locally", lambda sha, **kw: True)
        monkeypatch.setattr(ci_wait, "wait_for", recording_wait_for(seen))
        ci_wait.main(["--sha", SHA, "--fail-on-failed-job"])
        assert seen["fail_on_failed_job"] is True and callable(seen["run_jobs"])


# --- a run GitHub refused to start for billing ------------------------------------------------
# A billing block fails every job before a runner takes it: conclusion `failure`, ZERO steps, and
# a check-run annotation saying recent account payments have failed. No wait or retry fixes it,
# so reporting it as an ordinary failure sends the reader into the job log for a code defect.

_BILLING_MSG = ("The job was not started because recent account payments have failed or your "
                "spending limit needs to be increased. Please check the 'Billing & plans' section "
                "in your settings")


def failed_row(workflow: str, run_id: int) -> dict[str, object]:
    return {"headSha": "a" * 40, "workflowName": workflow, "status": "completed",
            "conclusion": "failure", "databaseId": run_id, "event": "push"}


class TestBillingBlocked:
    def test_every_failed_run_billing_blocked_is_its_own_verdict(self):
        asked: list[object] = []

        def blocked(run_id):
            asked.append(run_id)
            return True

        result = ci_wait.wait_for(lambda: [failed_row("ci", 11), failed_row("codeql", 12)],
                                  deadline_polls=5, sleep=lambda _s: None,
                                  run_billing_blocked=blocked)

        assert result.state == "billing-blocked"
        assert sorted(asked) == [11, 12]
        assert "11" in result.summary and "billing" in result.summary.lower()
        assert ci_wait.exit_code_for(result.state) == 2

    def test_a_real_failure_beside_a_billing_block_stays_failed(self):
        result = ci_wait.wait_for(lambda: [failed_row("ci", 11), failed_row("lint", 12)],
                                  deadline_polls=5, sleep=lambda _s: None,
                                  run_billing_blocked=lambda rid: rid == 11)
        assert result.state == "failed"

    def test_an_unknown_answer_never_turns_a_failure_into_billing(self):
        result = ci_wait.wait_for(lambda: [failed_row("ci", 11)], deadline_polls=5,
                                  sleep=lambda _s: None, run_billing_blocked=lambda _rid: None)
        assert result.state == "failed"

    def test_without_the_check_a_failure_is_reported_as_before(self):
        result = ci_wait.wait_for(lambda: [failed_row("ci", 11)], deadline_polls=5,
                                  sleep=lambda _s: None)
        assert result.state == "failed"


def billing_gh(jobs: object, annotations: object, calls: list[list[str]]):
    """`gh run view --json jobs` answers ``jobs``; `gh api .../annotations` answers ``annotations``."""

    def fake_run(argv, **kwargs):
        calls.append(list(argv))
        payload = {"jobs": jobs} if argv[:3] == ["gh", "run", "view"] else annotations
        return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(payload), stderr="")

    return fake_run


class TestGhRunBillingBlocked:
    def test_zero_step_jobs_with_the_billing_annotation_are_blocked(self, monkeypatch):
        calls: list[list[str]] = []
        monkeypatch.setattr(ci_wait.subprocess, "run", billing_gh(
            [{"databaseId": 901, "steps": [], "conclusion": "failure"}],
            [{"message": _BILLING_MSG, "annotation_level": "failure"}], calls))

        assert REAL_BILLING_BLOCKED(11, repo="o/r") is True
        assert calls[1][:3] == ["gh", "api", "repos/o/r/check-runs/901/annotations"]

    def test_a_job_that_ran_steps_is_not_a_billing_block(self, monkeypatch):
        calls: list[list[str]] = []
        monkeypatch.setattr(ci_wait.subprocess, "run", billing_gh(
            [{"databaseId": 901, "steps": [{"name": "Set up job"}]}], [], calls))

        assert REAL_BILLING_BLOCKED(11, repo="o/r") is False
        assert len(calls) == 1                # no annotation read for a job that ran

    def test_zero_steps_for_another_reason_is_not_billing(self, monkeypatch):
        monkeypatch.setattr(ci_wait.subprocess, "run", billing_gh(
            [{"databaseId": 901, "steps": []}],
            [{"message": "The runner has received a shutdown signal."}], []))
        assert REAL_BILLING_BLOCKED(11, repo="o/r") is False

    def test_an_unreadable_job_list_is_unknown(self, monkeypatch):
        monkeypatch.setattr(ci_wait.subprocess, "run", jobs_gh(None, [], rc=1))
        assert REAL_BILLING_BLOCKED(11, repo="o/r") is None

    def test_an_enterprise_repo_sends_the_annotation_read_to_its_own_host(self, monkeypatch):
        """`--repo HOST/OWNER/NAME` is accepted, and `gh api` takes no host inside the path: the
        annotation read went to github.com as `repos/HOST/OWNER/NAME/...` and always failed."""
        calls: list[list[str]] = []
        monkeypatch.setattr(ci_wait.subprocess, "run", billing_gh(
            [{"databaseId": 901, "steps": []}], [{"message": _BILLING_MSG}], calls))

        assert REAL_BILLING_BLOCKED(11, repo="ghe.example.com/o/r") is True
        assert calls[1] == ["gh", "api", "--hostname", "ghe.example.com",
                            "repos/o/r/check-runs/901/annotations"], calls[1]

    def test_the_billing_block_through_the_command_line(self, monkeypatch, capsys):
        monkeypatch.setattr(ci_wait, "sha_is_known_locally", lambda sha, **kw: True)
        listing = [failed_row("ci", 41)]
        monkeypatch.setattr(ci_wait, "gh_runs", lambda sha, **kw: listing)
        monkeypatch.setattr(ci_wait, "gh_run_billing_blocked", lambda rid, **kw: True)
        monkeypatch.setattr(ci_wait.time, "sleep", lambda _s: None)

        rc = ci_wait.main(["--sha", SHA, "--repo", "o/r", "--json"])

        payload = json.loads(capsys.readouterr().out)
        assert rc == 2
        assert payload["data"]["state"] == "billing-blocked"
