"""Tests for recall-memory.py (UserPromptSubmit recall hook). All content ASCII."""

import io
import json
import sys

import pytest

import recall_memory as R
import self_improve_signals as sig


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    (h / ".claude").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


def _mem(proj, name, text):
    d = sig.memory_dir(proj)
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(text, encoding="utf-8")
    return d


def run(monkeypatch, capsys, prompt, cwd="/p/cur", sid="t1"):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(
        {"prompt": prompt, "cwd": cwd, "session_id": sid})))
    rc = R.main()
    return rc, capsys.readouterr().out


def test_surfaces_relevant_note_from_another_project(monkeypatch, capsys):
    _mem("/p/other", "make-test.md", "Run make test with VIRTUAL_ENV=$PWD/.venv before committing")
    rc, out = run(monkeypatch, capsys, "run make test")
    assert rc == 0
    payload = json.loads(out)
    ctx = payload["hookSpecificOutput"]["additionalContext"]
    assert payload["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
    assert "make-test" in ctx and "VIRTUAL_ENV" in ctx      # the other tree's body is drawn in
    assert payload.get("suppressOutput") is True


def test_excludes_current_project(monkeypatch, capsys):
    _mem("/p/cur", "current-make.md", "make test current only secret")
    _mem("/p/other", "make-test.md", "make test elsewhere")
    rc, out = run(monkeypatch, capsys, "run make test", cwd="/p/cur")
    ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
    assert "make-test" in ctx            # other project surfaced
    assert "current-make" not in ctx     # our own memory is NOT redrawn (dedup with current)


def test_per_session_dedup_then_new_session(monkeypatch, capsys):
    _mem("/p/other", "make-test.md", "make test note")
    _, out1 = run(monkeypatch, capsys, "make test", sid="s1")
    assert "make-test" in out1
    _, out2 = run(monkeypatch, capsys, "make test again", sid="s1")
    assert out2 == ""                    # same session -> already surfaced -> silent
    _, out3 = run(monkeypatch, capsys, "make test", sid="s2")
    assert "make-test" in out3           # new session -> surfaces again


def test_no_match_no_output(monkeypatch, capsys):
    _mem("/p/other", "make-test.md", "make test note")
    rc, out = run(monkeypatch, capsys, "completely unrelated zzzqqq topic")
    assert rc == 0 and out == ""


def test_rarity_drops_common_only_matches(monkeypatch, capsys):
    monkeypatch.setattr(R, "SPECIFIC_MAX", 1)        # treat a keyword in >1 candidate as "common"
    _mem("/p/r", "rare.md", "alpha config note")     # matches a rare term (alpha) + the common one
    _mem("/p/b", "b.md", "config only here")         # common-only
    _mem("/p/c", "c.md", "config only there")        # common-only
    rc, out = run(monkeypatch, capsys, "alpha config")
    assert "alpha config note" in out                 # rare / multi-keyword note surfaces (its body)
    assert "config only here" not in out and "config only there" not in out  # common-only dropped


def test_single_rare_keyword_still_surfaces(monkeypatch, capsys):
    # a lone specific keyword (matches few notes) is a STRONG signal - must surface (not dropped)
    _mem("/p/x", "bindsnap-note.md", "bindsnap divert shim details")
    rc, out = run(monkeypatch, capsys, "bindsnap")
    assert "bindsnap-note" in out


def test_no_keywords_no_output(monkeypatch, capsys):
    _mem("/p/other", "make-test.md", "make test note")
    rc, out = run(monkeypatch, capsys, "do it")     # all stopwords/short
    assert rc == 0 and out == ""


def test_malformed_stdin_exits_zero(monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO("not json"))
    assert R.main() == 0
    assert capsys.readouterr().out == ""
