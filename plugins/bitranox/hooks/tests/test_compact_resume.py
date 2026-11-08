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


# ---- the checkpoint the session WROTE, wherever its cwd has drifted to --------------------------
# Measured over real transcripts: 23 of 106 checkpoints written after the save nudge were reported
# as "no checkpoint" because the hook looked only at the git top level of the cwd at compaction,
# while the session had written handover.md in a linked worktree (cwd the main checkout) or at a
# parent directory (cwd drifted into a nested repo by a `cd`). The touched-paths record names the
# file the session actually wrote.

def _write_fresh(path, text, session="s-1", age=0):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    if age:
        t = time.time() - age
        os.utime(path, (t, t))
    SIG.record_touched_path(session, str(path))
    return path


def test_a_checkpoint_written_in_another_tree_is_found_through_touched_paths(tmp_path,
                                                                              monkeypatch, capsys):
    repo = _repo(tmp_path)
    SIG.mark_checkpoint_asked("s-1", now=time.time() - 60)
    elsewhere = _write_fresh(repo / ".claude" / "worktrees" / "wt" / "handover.md",
                             "# Handover\n- WORKTREE-CHECKPOINT-11\n")
    ctx = _context(_run(monkeypatch, capsys, _event(repo)))
    assert "WORKTREE-CHECKPOINT-11" in ctx
    assert str(elsewhere) in ctx


def test_a_checkpoint_at_a_parent_is_found_when_the_cwd_is_a_nested_repo(tmp_path, monkeypatch,
                                                                          capsys):
    parent = tmp_path / "umbrella"
    nested = parent / "child"
    nested.mkdir(parents=True)
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    subprocess.run(["git", "init", "-q", str(nested)], check=True, env=env)
    SIG.mark_checkpoint_asked("s-1", now=time.time() - 60)
    _write_fresh(parent / "handover.md", "# Handover\n- PARENT-CHECKPOINT-12\n")
    ctx = _context(_run(monkeypatch, capsys, _event(nested)))
    assert "PARENT-CHECKPOINT-12" in ctx


def test_the_newest_fresh_checkpoint_wins(tmp_path, monkeypatch, capsys):
    repo = _repo(tmp_path)
    SIG.mark_checkpoint_asked("s-1", now=time.time() - 120)
    _write_fresh(repo / "handover.md", "# Handover\n- OLDER-FRESH-13\n", age=30)
    _write_fresh(tmp_path / "other" / "handover.md", "# Handover\n- NEWER-FRESH-14\n")
    ctx = _context(_run(monkeypatch, capsys, _event(repo)))
    assert "NEWER-FRESH-14" in ctx
    assert "OLDER-FRESH-13" not in ctx


def test_a_touched_handover_from_before_the_nudge_does_not_displace_a_fresh_one(tmp_path,
                                                                                 monkeypatch,
                                                                                 capsys):
    repo = _repo(tmp_path)
    _write_fresh(tmp_path / "other" / "handover.md", "# Handover\n- EARLIER-MOMENT-15\n", age=600)
    _checkpoint(repo, "# Handover\n- CURRENT-16\n")
    ctx = _context(_run(monkeypatch, capsys, _event(repo)))
    assert "CURRENT-16" in ctx
    assert "EARLIER-MOMENT-15" not in ctx


@pytest.mark.parametrize("name", ["handover.prev.md", "my-handover.md", "HANDOVER.md.bak"])
def test_another_name_without_the_lessons_heading_does_not_count(tmp_path, monkeypatch, capsys,
                                                                  name):
    repo = _repo(tmp_path)
    SIG.mark_checkpoint_asked("s-1", now=time.time() - 60)
    _write_fresh(tmp_path / "other" / name, "# Handover\n- NOT-A-CHECKPOINT-17\n")
    ctx = _context(_run(monkeypatch, capsys, _event(repo)))
    assert "NOT-A-CHECKPOINT-17" not in ctx
    assert "no checkpoint" in ctx.lower()


# ---- an improvised name: <anything>-handover.md with the checkpoint heading ---------------------
# Measured 2026-11-08 over 5497 transcripts: sessions with a worktree outside any repo wrote their
# checkpoints to ~/wt-<topic>-handover.md (43 writes, three names), and none was ever handed back.

_LESSONS = "## Lessons for the next nap\n- none\n"


def test_an_improvised_name_with_the_lessons_heading_is_handed_back(tmp_path, monkeypatch,
                                                                     capsys):
    repo = _repo(tmp_path)
    SIG.mark_checkpoint_asked("s-1", now=time.time() - 60)
    written = _write_fresh(tmp_path / "home" / "wt-vmxnet3-handover.md",
                           "# vmxnet3 checkpoint\n- IMPROVISED-19\n\n" + _LESSONS)
    ctx = _context(_run(monkeypatch, capsys, _event(repo)))
    assert "IMPROVISED-19" in ctx
    assert str(written) in ctx


def test_an_improvised_name_without_the_heading_is_not_a_checkpoint(tmp_path, monkeypatch,
                                                                     capsys):
    """The corpus's one other `-handover.md` file was a skill checklist, which has no such line."""
    repo = _repo(tmp_path)
    SIG.mark_checkpoint_asked("s-1", now=time.time() - 60)
    _write_fresh(tmp_path / "skill" / ".skillwriter" / "checklist-20261029-goal-and-handover.md",
                 "# Checklist\n- [x] CHECKLIST-20\n## RED\n- nothing\n")
    ctx = _context(_run(monkeypatch, capsys, _event(repo)))
    assert "CHECKLIST-20" not in ctx
    assert "no checkpoint" in ctx.lower()


def test_the_heading_counts_only_as_a_line_of_its_own(tmp_path, monkeypatch, capsys):
    repo = _repo(tmp_path)
    SIG.mark_checkpoint_asked("s-1", now=time.time() - 60)
    _write_fresh(tmp_path / "notes" / "design-handover.md",
                 "# Notes\n- MENTION-21: a checkpoint has a ## Lessons for the next nap heading\n")
    ctx = _context(_run(monkeypatch, capsys, _event(repo)))
    assert "MENTION-21" not in ctx


def test_the_backup_copy_never_counts_even_with_the_heading(tmp_path, monkeypatch, capsys):
    """handover.prev.md holds an EARLIER checkpoint, heading included; handing it back as current
    would resume from the wrong moment."""
    repo = _repo(tmp_path)
    SIG.mark_checkpoint_asked("s-1", now=time.time() - 60)
    _write_fresh(tmp_path / "other" / "handover.prev.md", "# Checkpoint\n- BACKUP-22\n\n" + _LESSONS)
    ctx = _context(_run(monkeypatch, capsys, _event(repo)))
    assert "BACKUP-22" not in ctx


def test_handover_md_itself_needs_no_heading(tmp_path, monkeypatch, capsys):
    repo = _repo(tmp_path)
    SIG.mark_checkpoint_asked("s-1", now=time.time() - 60)
    _write_fresh(tmp_path / "other" / "handover.md", "# Handover\n- PLAIN-23\n")
    ctx = _context(_run(monkeypatch, capsys, _event(repo)))
    assert "PLAIN-23" in ctx


@pytest.mark.parametrize("name, expected", [
    ("handover.md", True), ("wt-x-handover.md", True), ("-handover.md", False),
    ("handover.prev.md", False), ("x-handover.md.bak", False), ("xhandover.md", False),
    ("myhandover.md", False),
])
def test_is_checkpoint_name(name, expected):
    assert H.is_checkpoint_name(name) is expected


def test_another_sessions_touched_handover_is_not_this_sessions_checkpoint(tmp_path, monkeypatch,
                                                                            capsys):
    repo = _repo(tmp_path)
    SIG.mark_checkpoint_asked("s-1", now=time.time() - 60)
    _write_fresh(tmp_path / "other" / "handover.md", "# Handover\n- OTHER-SESSION-18\n",
                 session="someone-else")
    ctx = _context(_run(monkeypatch, capsys, _event(repo, session="s-1")))
    assert "OTHER-SESSION-18" not in ctx
