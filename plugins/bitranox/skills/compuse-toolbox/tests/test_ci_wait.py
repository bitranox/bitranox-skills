"""The CI waiter: it must refuse a short sha, and an empty match must be an ERROR, never a not-yet.

Both are the same bug wearing two hats. A sha shorter than 40 characters matches nothing - in
`gh run list --commit` and equally in a client-side `select(.headSha==...)` - and a "are they all
terminal yet?" test over an empty list is vacuous, so the loop spins to its deadline looking busy.
"""
from __future__ import annotations

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
        ]
        calls: list[int] = []

        def fetch() -> list[dict[str, object]]:
            calls.append(1)
            return polls[len(calls) - 1]

        result = ci_wait.wait_for(fetch, deadline_polls=10, sleep=lambda _s: None)

        assert result.state == "success"
        assert len(calls) == 3

    def test_it_stops_at_the_deadline_and_says_it_timed_out(self):
        result = ci_wait.wait_for(
            lambda: [run("CI", "in_progress", None)], deadline_polls=3, sleep=lambda _s: None
        )
        assert result.state == "timeout"
        assert "CI" in result.summary

    def test_runs_that_have_not_been_created_yet_are_waited_for_briefly(self):
        """A push does not create its runs instantly - measured, they take seconds to appear. An
        empty list on the first poll is that race, not a verdict."""
        polls = [[], [], [run("CI", "completed", "success")]]
        calls: list[int] = []

        def fetch() -> list[dict[str, object]]:
            calls.append(1)
            return polls[len(calls) - 1]

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
        assert len(calls) == 3

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

        assert len(calls) == 18  # 90s of grace at 5s per poll, NOT 3 polls


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
        self._fake_gh(monkeypatch, stdout="", returncode=4)

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

        rc = ci_wait.main(["--sha", "a" * 40])
        out, err = capsys.readouterr()

        assert rc == 0, "an unfetched sha whose runs are green must not be refused"
        assert "warning:" in err and "not a commit in this repository" in err
        assert "warning:" not in out, "the warning must not pollute the parsed stream"

    def test_a_green_run_is_still_reported_green(self, monkeypatch, capsys):
        monkeypatch.setattr(ci_wait, "sha_is_known_locally", lambda sha, **kw: False)
        monkeypatch.setattr(ci_wait, "gh_runs", lambda sha, **kw: [run("CI", "completed", "success")])

        ci_wait.main(["--sha", "a" * 40])

        assert "success" in capsys.readouterr().out

    def test_a_sha_git_does_know_produces_no_warning(self, monkeypatch, capsys):
        """The control: the warning must be absent when there is nothing to warn about."""
        monkeypatch.setattr(ci_wait, "sha_is_known_locally", lambda sha, **kw: True)
        monkeypatch.setattr(ci_wait, "gh_runs", lambda sha, **kw: [run("CI", "completed", "success")])

        ci_wait.main(["--sha", "a" * 40])

        assert "warning:" not in capsys.readouterr().err
