"""Tests for post-compact-nudge.py (PostCompact hook). ASCII only."""
import io
import json
import sys
from pathlib import Path

import pytest

import post_compact_nudge as H
import self_improve_signals as SIG


@pytest.fixture(autouse=True)
def isolate_home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    (h / ".claude").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


def run(monkeypatch, cwd="/proj/x"):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"cwd": cwd})))
    rc = H.main()
    return rc


def test_always_nudges_capture(monkeypatch, capsys):
    rc = run(monkeypatch)
    assert rc == 0
    ctx = json.loads(capsys.readouterr().out)["hookSpecificOutput"]["additionalContext"]
    assert "meta-self-improve" in ctx
    assert json.loads(json.dumps({"x": ctx}))  # valid/escaped


def test_surfaces_and_consumes_salvaged_audit(monkeypatch, capsys, isolate_home):
    af = SIG.audit_file("/proj/x")
    af.parent.mkdir(parents=True, exist_ok=True)
    af.write_text("<SELF-IMPROVE-AUDIT>\nsalvaged thing\n</SELF-IMPROVE-AUDIT>\n", encoding="utf-8")
    run(monkeypatch, "/proj/x")
    ctx = json.loads(capsys.readouterr().out)["hookSpecificOutput"]["additionalContext"]
    assert "salvaged thing" in ctx
    assert not af.is_file()  # consumed


def test_mentions_dream_when_due(monkeypatch, capsys, isolate_home):
    mem = SIG.memory_dir("/proj/x")
    mem.mkdir(parents=True, exist_ok=True)
    (mem / "a.md").write_text("x", encoding="utf-8")  # memory exists, no last-dream -> due
    run(monkeypatch, "/proj/x")
    ctx = json.loads(capsys.readouterr().out)["hookSpecificOutput"]["additionalContext"]
    assert "meta-dream-project" in ctx


def test_no_dream_mention_when_not_due(monkeypatch, capsys):
    run(monkeypatch, "/proj/none")  # no memory dir -> not due
    ctx = json.loads(capsys.readouterr().out)["hookSpecificOutput"]["additionalContext"]
    assert "meta-dream-project" not in ctx
    assert "meta-self-improve" in ctx
