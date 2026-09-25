"""The CI waiter: it must refuse a short sha, and an empty match must be an ERROR, never a not-yet.

Both are the same bug wearing two hats. A sha shorter than 40 characters matches nothing - in
`gh run list --commit` and equally in a client-side `select(.headSha==...)` - and a "are they all
terminal yet?" test over an empty list is vacuous, so the loop spins to its deadline looking busy.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

import ci_wait


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

        def fake_wait(fetch, **kw):
            seen.update(kw)
            return ci_wait.Verdict("success", "CI=success")

        monkeypatch.setattr(ci_wait, "sha_is_known_locally", lambda sha, **kw: True)
        monkeypatch.setattr(ci_wait, "wait_for", fake_wait)

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
            lambda: [], deadline_polls=100, sleep=slept.append, interval_s=120.0, appear_grace_s=120.0
        )
        assert result.state == "no-runs"
        assert sum(slept) >= 120.0

    def test_a_grace_that_is_not_a_multiple_of_the_interval_is_honoured(self):
        slept: list[float] = []
        ci_wait.wait_for(
            lambda: [], deadline_polls=100, sleep=slept.append, interval_s=2.0, appear_grace_s=3.0
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
             "--interval", "1"],
            capture_output=True, text=True, env=env, timeout=45,
        )
        assert proc.returncode == 2, proc.stderr
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
        assert payload["ok"] is False and payload["state"] == "error"
        assert "40-character" in payload["summary"]

    def test_repo_is_passed_to_gh_and_skips_the_local_sha_check(self, monkeypatch, capsys):
        calls: list[list[str]] = []
        monkeypatch.setattr(
            ci_wait.subprocess, "run", emulated_gh([run("CI", "completed", "success")], calls)
        )
        rc = ci_wait.main(["--sha", SHA, "--repo", "o/r", "--settle", "0", "--json"])
        assert rc == 0
        assert all(argv[0] == "gh" for argv in calls), "no git call when --repo names another repo"
        assert calls[0][calls[0].index("--repo") + 1] == "o/r"
        assert json.loads(capsys.readouterr().out)["state"] == "success"

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
        assert json.loads(capsys.readouterr().out)["state"] == "error"


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
            [sys.executable, str(driver)], capture_output=True, env=env, timeout=60
        )
        assert proc.returncode == 0, proc.stderr.decode("cp1252", "replace")
        assert b"CI " in proc.stdout
