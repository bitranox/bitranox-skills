"""Tests for skill_receipt.py + the receipt-aware skill-edit-guard. ASCII."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

import skill_receipt as SR
import skill_edit_guard as G

SCRIPT = Path(SR.__file__).resolve()


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    (h / ".claude").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    # A run inside a Claude Code session inherits that session's id, which would silently key
    # every id-less `start` here to it; the tests name their sessions explicitly instead.
    monkeypatch.delenv("CLAUDE_CODE_SESSION_ID", raising=False)
    return h


def _edit_event():
    return {"tool_name": "Edit",
            "tool_input": {"file_path": "/x/plugins/bitranox/skills/foo/SKILL.md"}}


def test_start_then_fresh_then_ttl_expiry(monkeypatch):
    SR.start("meta-skill-writer")
    assert SR.is_fresh("meta-skill-writer") is True
    assert SR.is_fresh("meta-skill-writer", ttl=0) is False     # expired at zero TTL
    assert SR.is_fresh("never-started") is False


def test_cli_check_exit_codes(capsys):
    assert SR.main(["check", "meta-skill-writer"]) == 1
    assert SR.main(["start", "meta-skill-writer"]) == 0
    assert SR.main(["check", "meta-skill-writer"]) == 0


def test_guard_denies_without_receipt_allows_with(monkeypatch):
    assert G.decide(_edit_event(), {}) is not None              # no receipt -> deny
    SR.start("meta-skill-writer")
    assert G.decide(_edit_event(), {}) is None                  # fresh receipt -> allow
    assert "receipt" in (G.decide(_edit_event(), {}) or "receipt")  # message mentions the mechanism


def test_guard_env_bypass_still_works():
    assert G.decide(_edit_event(), {"BITRANOX_SKILL_WRITER": "1"}) is None


# ---- the receipt must prove WHICH session entered the procedure -------------------------------

THIS = "11111111-2222-3333-4444-555555555555"
OTHER = "99999999-8888-7777-6666-555555555555"


def test_a_receipt_from_another_session_is_not_fresh_for_this_one():
    """The hole this closes: the receipt carried a timestamp and no session id, so is_fresh
    answered "somebody on this machine started the procedure in the last 8 hours" - not "this
    session did". Measured with 4-5 concurrent sessions routinely running on one machine, which
    is the condition that decouples the two; a single-session test box can never reproduce it.
    """
    SR.start("meta-skill-writer", session_id=OTHER)
    assert not SR.is_fresh("meta-skill-writer", session_id=THIS)


def test_a_receipt_from_this_session_is_fresh():
    """Control for the test above: the tightening must not deny the session that did the work."""
    SR.start("meta-skill-writer", session_id=THIS)
    assert SR.is_fresh("meta-skill-writer", session_id=THIS)


def test_a_receipt_with_no_session_id_fails_closed_when_one_is_demanded():
    """A receipt that cannot say which session wrote it is exactly the hole, so it does not get
    grandfathered. Re-running `start` costs one command and re-arms it correctly."""
    p = SR.receipt_path("meta-skill-writer")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text('{"skill": "meta-skill-writer", "ts": %f}' % time.time(), encoding="utf-8")
    assert not SR.is_fresh("meta-skill-writer", session_id=THIS)
    # ... but with no session id demanded, the old TTL-only contract still holds.
    assert SR.is_fresh("meta-skill-writer")


def test_the_session_id_is_taken_from_the_environment_when_not_passed(monkeypatch):
    """The writer is a Bash call, and CLAUDE_CODE_SESSION_ID is set there - verified to equal the
    session's own transcript name, which is the id the hook event carries."""
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", THIS)
    SR.start("meta-skill-writer")
    assert SR.is_fresh("meta-skill-writer", session_id=THIS)
    assert not SR.is_fresh("meta-skill-writer", session_id=OTHER)


def test_the_ttl_still_bounds_a_matching_session(monkeypatch):
    """Session identity is the primary bound; the TTL stays as the secondary one, so a session
    running for days does not keep an ancient receipt armed."""
    SR.start("meta-skill-writer", session_id=THIS)
    # Capture the real clock FIRST: SR.time is the shared time module, so a lambda calling
    # time.time() after the patch calls itself.
    later = time.time() + SR.TTL_SECONDS + 1
    monkeypatch.setattr(SR.time, "time", lambda: later)
    assert not SR.is_fresh("meta-skill-writer", session_id=THIS)


def test_the_guard_denies_an_edit_when_the_receipt_belongs_to_another_session():
    SR.start("meta-skill-writer", session_id=OTHER)
    event = dict(_edit_event(), session_id=THIS)
    assert G.decide(event, {}) is not None


def test_the_guard_allows_an_edit_when_the_receipt_belongs_to_this_session():
    SR.start("meta-skill-writer", session_id=THIS)
    event = dict(_edit_event(), session_id=THIS)
    assert G.decide(event, {}) is None


def test_the_guard_denies_a_session_less_event_when_only_another_session_holds_a_receipt():
    """With no id to offer, the reader answers from the id-less receipt only. Counting any
    session's receipt here is the same hole the session id closed, entered through the side door."""
    SR.start("meta-skill-writer", session_id=OTHER)
    assert G.decide(_edit_event(), {}) is not None


def test_the_guard_allows_a_session_less_event_with_a_session_less_receipt():
    """Control for the test above: a surface that supplies no id to the writer or the reader still
    works end to end, so the procedure stays usable there."""
    SR.start("meta-skill-writer", session_id="")
    assert G.decide(_edit_event(), {}) is None


# ---- receipts are keyed per skill AND session: one session never touches another's ------------

def test_a_second_sessions_start_does_not_unarm_the_first():
    """Keyed by skill alone, B's `start` overwrote A's receipt, so A - which had entered the
    procedure - was denied its next SKILL.md edit. Several sessions share this machine routinely."""
    SR.start("meta-skill-writer", session_id=THIS)
    SR.start("meta-skill-writer", session_id=OTHER)
    assert SR.is_fresh("meta-skill-writer", session_id=THIS)
    assert SR.is_fresh("meta-skill-writer", session_id=OTHER)
    assert G.decide(dict(_edit_event(), session_id=THIS), {}) is None


def test_end_removes_only_this_sessions_receipt():
    SR.start("plan-execution", session_id=THIS)
    SR.start("plan-execution", session_id=OTHER)
    assert SR.end("plan-execution", session_id=OTHER) is True
    assert SR.is_fresh("plan-execution", session_id=THIS)
    assert not SR.is_fresh("plan-execution", session_id=OTHER)


def test_end_takes_the_session_from_the_environment(monkeypatch):
    SR.start("plan-execution", session_id=THIS)
    SR.start("plan-execution", session_id=OTHER)
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", OTHER)
    assert SR.end("plan-execution") is True
    assert SR.is_fresh("plan-execution", session_id=THIS)
    assert SR.end("plan-execution") is False              # idempotent: already gone


def test_a_session_less_reader_is_not_armed_by_a_session_keyed_receipt():
    """Counting any session's receipt is what let one session's plan-execution arm the deny gate
    in every other session on the machine."""
    SR.start("plan-execution", session_id=OTHER)
    assert not SR.is_fresh("plan-execution")
    SR.start("plan-execution", session_id="")
    assert SR.is_fresh("plan-execution")                   # the id-less writer and reader agree


# ---- a receipt written before the per-session key (one file per skill) ------------------------

def _legacy(skill, session_id, ts=None):
    p = SR.receipt_path(skill)
    p.parent.mkdir(parents=True, exist_ok=True)
    body = {"skill": skill, "ts": time.time() if ts is None else ts}
    if session_id is not None:
        body["session_id"] = session_id
    p.write_text(json.dumps(body), encoding="utf-8")
    return p


def test_a_legacy_receipt_still_arms_the_session_that_wrote_it():
    """A session that ran `start` before the key change keeps its receipt: the file names the
    session, so it proves entry exactly as a new-format one does."""
    _legacy("meta-skill-writer", THIS)
    assert SR.is_fresh("meta-skill-writer", session_id=THIS)


def test_a_legacy_receipt_arms_no_other_session():
    """A fresh session must not inherit another session's leftover receipt - neither as an allow
    for the skill-edit guard nor as a DENY for the plan gate."""
    _legacy("plan-execution", THIS)
    assert not SR.is_fresh("plan-execution", session_id=OTHER)
    assert not SR.is_fresh("plan-execution")


def test_a_fresh_session_is_not_stuck_behind_a_legacy_receipt():
    _legacy("meta-skill-writer", OTHER)
    SR.start("meta-skill-writer", session_id=THIS)
    assert SR.is_fresh("meta-skill-writer", session_id=THIS)


def test_end_removes_a_legacy_receipt_only_for_the_session_that_wrote_it():
    p = _legacy("plan-execution", THIS)
    assert SR.end("plan-execution", session_id=OTHER) is False
    assert p.exists()
    assert SR.end("plan-execution", session_id=THIS) is True
    assert not p.exists()


def test_start_prunes_expired_receipts_of_the_same_skill():
    """One file per session would otherwise accumulate for as long as the machine runs."""
    past = time.time() - SR.TTL_SECONDS - 60
    old = _legacy("plan-execution", OTHER, ts=past)
    stale = SR.start("plan-execution", session_id=OTHER)
    keep = SR.start("meta-skill-writer", session_id=OTHER)  # another skill: not this start's to prune
    for p in (old, stale, keep):
        os.utime(p, (past, past))
    SR.start("plan-execution", session_id=THIS)
    assert not old.exists() and not stale.exists()
    assert keep.exists()


# ---- the CLI ----------------------------------------------------------------------------------

def test_cli_check_answers_for_the_calling_session(monkeypatch):
    """`check` ignored the session, so it said "fresh" in a session the guard denies."""
    SR.start("meta-skill-writer", session_id=THIS)
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", OTHER)
    assert SR.main(["check", "meta-skill-writer"]) == 1
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", THIS)
    assert SR.main(["check", "meta-skill-writer"]) == 0


def test_cli_check_prints_the_age_and_the_owning_session(monkeypatch, capsys):
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", THIS)
    SR.main(["start", "meta-skill-writer"])
    capsys.readouterr()
    assert SR.main(["check", "meta-skill-writer"]) == 0
    out = capsys.readouterr().out
    assert "fresh" in out and "age 0.0h" in out and THIS in out


@pytest.mark.parametrize("body", ['{"ts": null}', "[]", '"text"', '{"ts": "soon"}', "not json"])
def test_a_receipt_of_the_wrong_shape_is_stale_not_a_crash(monkeypatch, capsys, body):
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", THIS)
    SR.start("meta-skill-writer", session_id=THIS).write_text(body, encoding="utf-8")
    assert SR.is_fresh("meta-skill-writer", session_id=THIS) is False
    assert SR.main(["check", "meta-skill-writer"]) == 1
    assert "stale-or-missing" in capsys.readouterr().out


@pytest.mark.parametrize("ts_json", ["1e400", "-1e400", "NaN"])
def test_a_non_finite_timestamp_is_stale_not_fresh(monkeypatch, capsys, ts_json):
    """A receipt is written with time.time(), which is always finite - inf/-inf/NaN can only come
    from tampering or a corrupt write, and `age = now - inf` is a huge NEGATIVE number, which used
    to read as "fresh" (age < ttl is trivially true for -inf)."""
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", THIS)
    p = SR.start("meta-skill-writer", session_id=THIS)
    p.write_text('{"skill": "meta-skill-writer", "session_id": "%s", "ts": %s}' % (THIS, ts_json),
                 encoding="utf-8")
    assert SR.is_fresh("meta-skill-writer", session_id=THIS) is False
    assert SR.main(["check", "meta-skill-writer"]) == 1
    assert "stale-or-missing" in capsys.readouterr().out


def test_a_future_timestamp_is_stale_not_fresh(monkeypatch, capsys):
    """A receipt cannot have been written in the future; a future `ts` makes `now - ts` negative,
    which read as "fresh" under a bare `age < ttl` check."""
    monkeypatch.setenv("CLAUDE_CODE_SESSION_ID", THIS)
    p = SR.start("meta-skill-writer", session_id=THIS)
    future = time.time() + 10_000
    p.write_text('{"skill": "meta-skill-writer", "session_id": "%s", "ts": %r}' % (THIS, future),
                 encoding="utf-8")
    assert SR.is_fresh("meta-skill-writer", session_id=THIS) is False
    assert SR.main(["check", "meta-skill-writer"]) == 1
    assert "stale-or-missing" in capsys.readouterr().out


@pytest.mark.parametrize("ts, ok", [(float("inf"), False), (float("-inf"), False),
                                    (float("nan"), False), (1.0, False), (0.0, True), (-1.0, True)])
def test_age_rejects_non_finite_and_future_timestamps(ts, ok):
    # `now` is pinned to 0.0: ts=1.0 is one second in the FUTURE (age would be -1, rejected);
    # ts=-1.0 is one second in the past (age = 1, a perfectly ordinary receipt).
    age = SR._age({"ts": ts}, now=0.0)                     # noqa: SLF001 - the unit under test
    assert (age is not None) == ok


def _cli(home, sid, *args):
    env = dict(os.environ, HOME=str(home), USERPROFILE=str(home), CLAUDE_CODE_SESSION_ID=sid)
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=env, timeout=60)


def test_cli_start_end_check_and_usage_as_a_process(home):
    """The plan-execution skills disarm the gate through `end` from a Bash call, so drive the real
    entry point, not main()."""
    r = _cli(home, THIS, "start", "plan-execution")
    assert r.returncode == 0 and "receipt:" in r.stdout
    assert _cli(home, THIS, "check", "plan-execution").returncode == 0
    assert _cli(home, OTHER, "end", "plan-execution").stdout.strip().endswith("absent")
    assert _cli(home, THIS, "check", "plan-execution").returncode == 0
    r = _cli(home, THIS, "end", "plan-execution")
    assert r.returncode == 0 and r.stdout.strip().endswith("removed")
    assert _cli(home, THIS, "check", "plan-execution").returncode == 1
    r = _cli(home, THIS, "bogus", "plan-execution")
    assert r.returncode == 2 and "usage:" in r.stdout
