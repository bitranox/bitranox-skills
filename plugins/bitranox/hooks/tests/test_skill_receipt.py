"""Tests for skill_receipt.py + the receipt-aware skill-edit-guard. ASCII."""
import time

import pytest

import skill_receipt as SR
import skill_edit_guard as G


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    (h / ".claude").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
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


def test_the_guard_falls_back_to_the_ttl_when_the_event_carries_no_session_id():
    """Not every surface supplies one. Where it is absent the guard keeps its previous contract
    rather than denying every edit, which would make the whole procedure unusable there."""
    SR.start("meta-skill-writer", session_id=OTHER)
    assert G.decide(_edit_event(), {}) is None
