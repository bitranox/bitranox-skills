"""Tests for compact-resume.py (SessionStart, source "compact"). ASCII only.

The hook puts the checkpoint this session saved before an auto-compaction back in front of the
model, so the work continues from the saved state instead of from the compaction summary alone.

Two failures matter, and both are silent. Re-injecting a checkpoint that is NOT this session's
latest (written before the save nudge, or already marked STALE) hands the model an older moment
as current. Injecting nothing when no checkpoint was saved leaves the model believing the summary
is complete, so that case must say so and point at the transcript on disk.
"""
import io
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

import compact_resume as H
import self_improve_signals as SIG

HOOKS_DIR = Path(__file__).resolve().parent.parent
SCRIPT = HOOKS_DIR / "compact-resume.py"
SHIM = HOOKS_DIR / "run-python.sh"


@pytest.fixture(autouse=True)
def isolate_home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    (h / ".claude").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    return h


def _repo(tmp_path):
    repo = tmp_path / "repo"
    (repo / "sub").mkdir(parents=True)
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    subprocess.run(["git", "init", "-q", str(repo)], check=True, env=env)
    return repo


def _run(monkeypatch, capsys, event):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(event)))
    assert H.main() == 0
    out = capsys.readouterr().out
    return json.loads(out) if out.strip() else None


def _context(payload):
    assert payload is not None, "the hook printed nothing"
    hso = payload["hookSpecificOutput"]
    assert hso["hookEventName"] == "SessionStart"
    return hso["additionalContext"]


def _event(cwd, session="s-1", source="compact", transcript="/t/s-1.jsonl"):
    return {"hook_event_name": "SessionStart", "source": source, "session_id": session,
            "cwd": str(cwd), "transcript_path": transcript}


def _checkpoint(repo, text, *, after_ask=True, session="s-1"):
    """Write handover.md before or after this session's save nudge was recorded."""
    path = repo / "handover.md"
    if after_ask:
        SIG.mark_checkpoint_asked(session, now=time.time() - 60)
        path.write_text(text, encoding="utf-8")
    else:
        path.write_text(text, encoding="utf-8")
        old = time.time() - 600
        os.utime(path, (old, old))
        SIG.mark_checkpoint_asked(session, now=time.time() - 60)
    return path


def test_a_checkpoint_saved_after_the_nudge_is_reinjected(tmp_path, monkeypatch, capsys):
    repo = _repo(tmp_path)
    _checkpoint(repo, "# Handover\n\n## In flight\n- MARKER-IN-FLIGHT-7\n")
    ctx = _context(_run(monkeypatch, capsys, _event(repo / "sub")))
    assert "MARKER-IN-FLIGHT-7" in ctx
    assert str(repo / "handover.md") in ctx
    assert "STALE" in ctx, "the reader must be told to mark it read, or the next compaction re-feeds it"


def test_a_checkpoint_older_than_the_nudge_is_not_presented_as_current(tmp_path, monkeypatch,
                                                                         capsys):
    repo = _repo(tmp_path)
    _checkpoint(repo, "# Handover\n- OLD-MOMENT-3\n", after_ask=False)
    ctx = _context(_run(monkeypatch, capsys, _event(repo)))
    assert "OLD-MOMENT-3" not in ctx
    assert "no checkpoint" in ctx.lower()


def test_a_stale_checkpoint_is_not_reinjected(tmp_path, monkeypatch, capsys):
    repo = _repo(tmp_path)
    _checkpoint(repo, "# STALE - read 2026-10-26, work continued\n- GONE-4\n")
    ctx = _context(_run(monkeypatch, capsys, _event(repo)))
    assert "GONE-4" not in ctx
    assert "no checkpoint" in ctx.lower()


def test_another_sessions_nudge_does_not_vouch_for_this_one(tmp_path, monkeypatch, capsys):
    repo = _repo(tmp_path)
    _checkpoint(repo, "# Handover\n- FOREIGN-5\n", session="someone-else")
    ctx = _context(_run(monkeypatch, capsys, _event(repo, session="s-1")))
    assert "FOREIGN-5" not in ctx


def test_without_a_checkpoint_it_points_at_the_transcript(tmp_path, monkeypatch, capsys):
    repo = _repo(tmp_path)
    ctx = _context(_run(monkeypatch, capsys, _event(repo, transcript="/t/abc.jsonl")))
    assert "/t/abc.jsonl" in ctx
    assert "session-review" in ctx


@pytest.mark.parametrize("source", ["startup", "resume", "clear", "", None])
def test_it_speaks_only_after_a_compaction(tmp_path, monkeypatch, capsys, source):
    repo = _repo(tmp_path)
    _checkpoint(repo, "# Handover\n- X\n")
    assert _run(monkeypatch, capsys, _event(repo, source=source)) is None


def test_an_oversized_checkpoint_is_cut_and_names_the_file(tmp_path, monkeypatch, capsys):
    repo = _repo(tmp_path)
    body = "# Handover\n" + "".join("- line %05d padding padding padding\n" % i
                                    for i in range(2000))
    _checkpoint(repo, body + "TAIL-MARKER-9\n")
    ctx = _context(_run(monkeypatch, capsys, _event(repo)))
    assert len(ctx) <= H.MAX_CONTEXT_CHARS
    assert "TAIL-MARKER-9" not in ctx
    assert "line 00000" in ctx
    assert str(repo / "handover.md") in ctx


def test_outside_a_repository_it_looks_in_the_cwd(tmp_path, monkeypatch, capsys):
    plain = tmp_path / "plain"
    plain.mkdir()
    _checkpoint(plain, "# Handover\n- PLAIN-6\n")
    ctx = _context(_run(monkeypatch, capsys, _event(plain)))
    assert "PLAIN-6" in ctx


@pytest.mark.skipif(sys.platform == "win32", reason="drives the bash shim directly")
@pytest.mark.parametrize("payload", ["", "not json", "[]", "null"])
def test_malformed_input_fails_open(payload):
    proc = subprocess.run(["bash", str(SHIM), str(SCRIPT)], input=payload, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")
    assert (proc.returncode, proc.stdout.strip()) == (0, "")


@pytest.mark.skipif(sys.platform == "win32", reason="drives the bash shim directly")
def test_end_to_end_through_the_shim(tmp_path):
    repo = _repo(tmp_path)
    env = dict(os.environ, HOME=str(tmp_path / "home"), USERPROFILE=str(tmp_path / "home"))
    proc = subprocess.run(["bash", str(SHIM), str(SCRIPT)], input=json.dumps(_event(repo)),
                          capture_output=True, text=True, encoding="utf-8", errors="replace",
                          env=env)
    assert proc.returncode == 0
    assert "session-review" in _context(json.loads(proc.stdout))
