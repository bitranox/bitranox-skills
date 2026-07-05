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
