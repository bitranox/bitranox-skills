"""Tests for mcp_search.py (optional basic-memory search, fallback-safe). All content ASCII."""

import json
import subprocess
import types

import pytest

import mcp_search as X
import self_improve_signals as sig


@pytest.fixture
def home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    (h / ".claude").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


def _fake_run(stdout, rc=0):
    def run(*a, **k):
        return types.SimpleNamespace(returncode=rc, stdout=stdout, stderr="")
    return run


def test_available_reflects_which(monkeypatch):
    monkeypatch.setattr(X.shutil, "which", lambda _n: "/usr/bin/basic-memory")
    assert X.available() is True
    monkeypatch.setattr(X.shutil, "which", lambda _n: None)
    assert X.available() is False


def test_enabled_honors_knob(home, monkeypatch):
    monkeypatch.setattr(X, "available", lambda: True)
    assert X.enabled() is True                           # default mcp_search=auto
    sig.save_config({"mcp_search": "off"})
    assert X.enabled() is False
    sig.save_config({"mcp_search": "auto"})
    monkeypatch.setattr(X, "available", lambda: False)
    assert X.enabled() is False                          # auto but CLI absent


def test_search_none_when_unavailable(monkeypatch):
    monkeypatch.setattr(X, "available", lambda: False)
    assert X.search("query") is None


def test_search_none_on_error_output(monkeypatch):
    monkeypatch.setattr(X, "available", lambda: True)
    monkeypatch.setattr(subprocess, "run", _fake_run("Error during search: Project not found: 'main'."))
    assert X.search("q") is None


def test_search_parses_json(monkeypatch):
    monkeypatch.setattr(X, "available", lambda: True)
    payload = json.dumps({"results": [{"permalink": "notes/a"}, {"file_path": "notes/b.md"}]})
    monkeypatch.setattr(subprocess, "run", _fake_run(payload))
    assert X.search("q") == ["notes/a", "notes/b.md"]


def test_search_parses_lines(monkeypatch):
    monkeypatch.setattr(X, "available", lambda: True)
    monkeypatch.setattr(subprocess, "run", _fake_run("notes/a\nnotes/b\n"))
    assert X.search("q") == ["notes/a", "notes/b"]


def test_watched_roots_and_covers(home):
    (home / ".basic-memory").mkdir()
    (home / ".basic-memory" / "config.json").write_text(
        json.dumps({"projects": {"main": {"path": str(home / "kb")}}}), encoding="utf-8")
    (home / "kb" / "sub").mkdir(parents=True)
    assert str(home / "kb") in X.watched_roots()
    assert X.covers(str(home / "kb" / "sub")) is True    # ancestor project covers it
    assert X.covers("/tmp/elsewhere") is False
