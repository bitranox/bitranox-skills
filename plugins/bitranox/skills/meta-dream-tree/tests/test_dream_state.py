"""Tests for dream_state.py (meta-dream cadence-marker CLI). ASCII only."""
import sys
from pathlib import Path

import pytest

import dream_state as D


@pytest.fixture
def home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    (h / ".claude").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


def _mem(proj="/p/x"):
    d = D.sig.memory_dir(proj)
    d.mkdir(parents=True, exist_ok=True)
    (d / "a.md").write_text("x", encoding="utf-8")


def test_due_reports_not_due_without_memory(home, capsys):
    assert D.main(["due", "/p/x"]) == 0
    assert capsys.readouterr().out.strip() == "not-due"


def test_due_reports_due_with_fresh_memory(home, capsys):
    _mem()
    assert D.main(["due", "/p/x"]) == 0
    assert capsys.readouterr().out.strip() == "due"


def test_done_marks_and_silences(home, capsys):
    _mem()
    assert D.main(["done", "/p/x"]) == 0
    capsys.readouterr()
    D.main(["due", "/p/x"])
    assert capsys.readouterr().out.strip() == "not-due"  # just dreamed -> not due


def test_mode_default_and_off(home, capsys):
    assert D.main(["mode", "/p/x"]) == 0
    assert capsys.readouterr().out.strip() == "propose"
    D.sig.save_config({"dream_mode": "off"})
    D.main(["mode", "/p/x"])
    assert capsys.readouterr().out.strip() == "off"


def test_unknown_command_errors(home):
    assert D.main(["frobnicate", "/p/x"]) == 2


# ---- corroboration gate (defect F): saw-promotable / should-promote / promoted --------------

def test_should_promote_holds_then_promotes_across_two_dreams(home, capsys):
    # A model-inferred fact routed to the tree top needs >= 2 dream sightings before it may promote.
    assert D.main(["saw-promotable", "some-slug", "/p/x"]) == 0
    assert capsys.readouterr().out.strip() == "1"                  # dwell after first sighting
    assert D.main(["should-promote", "some-slug", "/p/x"]) == 0
    assert capsys.readouterr().out.strip() == "hold"              # one sighting: not yet
    assert D.main(["saw-promotable", "some-slug", "/p/x"]) == 0
    assert capsys.readouterr().out.strip() == "2"
    assert D.main(["should-promote", "some-slug", "/p/x"]) == 0
    assert capsys.readouterr().out.strip() == "promote"          # corroborated across 2 dreams


def test_should_promote_is_read_only(home, capsys):
    # querying should-promote must NOT count as a sighting (else one query would corroborate it)
    D.main(["saw-promotable", "s", "/p/x"]); capsys.readouterr()
    for _ in range(3):
        D.main(["should-promote", "s", "/p/x"])
        assert capsys.readouterr().out.strip() == "hold"          # still 1 sighting after repeated reads


def test_promoted_clears_the_counter(home, capsys):
    D.main(["saw-promotable", "s", "/p/x"])
    D.main(["saw-promotable", "s", "/p/x"]); capsys.readouterr()
    assert D.main(["promoted", "s", "/p/x"]) == 0
    capsys.readouterr()
    D.main(["should-promote", "s", "/p/x"])
    assert capsys.readouterr().out.strip() == "hold"              # counter forgotten after promotion
