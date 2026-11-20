"""Tests for compact-resume.py (SessionStart, source "compact"). ASCII only.

The hook puts the checkpoint this session saved before an auto-compaction back in front of the
model, so the work continues from the saved state instead of from the compaction summary alone.

Two failures matter, and both are silent. Re-injecting a checkpoint that is NOT this session's
latest (written before the save nudge, or already marked STALE) hands the model an older moment
as current. Injecting nothing when no checkpoint was saved leaves the model believing the summary
is complete, so that case must say so and point at the transcript on disk.
"""
import datetime
import io
import json
import os
import random
import re
import subprocess
import sys
import time
from pathlib import Path

import pytest

import compact_resume as H
import self_improve_signals as SIG
import shell_text

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
    """Write handover.md before or after this session's save nudge was recorded.

    The write is recorded in the session's touched paths, as the PostToolUse recorder does for a
    Write: with no readable transcript (these events name a path that does not exist), that record
    is what attributes the file to this session.
    """
    path = repo / "handover.md"
    if after_ask:
        SIG.mark_checkpoint_asked(session, now=time.time() - 60)
        path.write_text(text, encoding="utf-8")
    else:
        path.write_text(text, encoding="utf-8")
        old = time.time() - 600
        os.utime(path, (old, old))
        SIG.mark_checkpoint_asked(session, now=time.time() - 60)
    SIG.record_touched_path(session, str(path))
    return path


def test_a_checkpoint_saved_after_the_nudge_is_reinjected(tmp_path, monkeypatch, capsys):
    repo = _repo(tmp_path)
    _checkpoint(repo, "# Handover\n\n## In flight\n- MARKER-IN-FLIGHT-7\n")
    ctx = _context(_run(monkeypatch, capsys, _event(repo / "sub")))
    assert "MARKER-IN-FLIGHT-7" in ctx
    assert str(repo / "handover.md") in ctx
    assert "STALE" in ctx, "the reader must be told to mark it read, or the next compaction re-feeds it"


def test_the_next_action_is_checked_before_it_is_taken(tmp_path, monkeypatch, capsys):
    # Work can continue past a checkpoint before the compaction lands, and a tracked repo-root
    # handover.md can be another session's: the block must say to check the next action against
    # the summary and git first, and to leave a checkpoint the summary never mentions alone.
    repo = _repo(tmp_path)
    _checkpoint(repo, "# Handover\n- MARKER-8\n")
    ctx = _context(_run(monkeypatch, capsys, _event(repo)))
    assert "compaction summary" in ctx
    assert "git log" in ctx and "git status" in ctx
    assert "another session's" in ctx
    assert "starting with its exact next action" not in ctx


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


def test_another_sessions_touched_handover_is_not_this_sessions_checkpoint(tmp_path, monkeypatch,
                                                                            capsys):
    repo = _repo(tmp_path)
    SIG.mark_checkpoint_asked("s-1", now=time.time() - 60)
    _write_fresh(tmp_path / "other" / "handover.md", "# Handover\n- OTHER-SESSION-18\n",
                 session="someone-else")
    ctx = _context(_run(monkeypatch, capsys, _event(repo, session="s-1")))
    assert "OTHER-SESSION-18" not in ctx


# ---- whose checkpoint is it: attribution from this session's own records ------------------------
# Several sessions share one main checkout and its linked worktrees, and each writes its own
# handover.md. A file's mtime says it changed after this session's save request, never that THIS
# session changed it: a peer's checkpoint, or a tracked copy refreshed by a checkout, is just as
# new. Measured 2026-11-16: compaction hit while the cwd sat in a linked worktree, and the block
# handed back that worktree's tracked handover.md (another moment, another session) as this
# session's own and told the model to mark it STALE, while the session's real checkpoint was the
# main checkout's uncommitted handover.md. Attribution therefore comes from the session's own
# transcript: a successful Write/Edit of the path after the request, with no change since.

def _iso(epoch):
    return datetime.datetime.fromtimestamp(epoch, tz=datetime.UTC).strftime(
        "%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _transcript(tmp_path, writes, name="s-1.jsonl"):
    """A session transcript with one Write tool_use plus its tool_result per (path, at, ok)."""
    lines = []
    for i, (path, at, ok) in enumerate(writes):
        tid = f"toolu_{i:02d}"
        lines.append({"type": "assistant", "timestamp": _iso(at - 0.5), "message": {
            "role": "assistant", "content": [{"type": "tool_use", "id": tid, "name": "Write",
                                              "input": {"file_path": str(path), "content": "x"}}]}})
        result = {"type": "tool_result", "tool_use_id": tid, "content": "ok"}
        if not ok:
            result["is_error"] = True
        lines.append({"type": "user", "timestamp": _iso(at), "message": {
            "role": "user", "content": [result]}})
    out = tmp_path / name
    out.write_text("".join(json.dumps(r) + "\n" for r in lines), encoding="utf-8")
    return out


def _set_mtime(path, epoch):
    os.utime(path, (epoch, epoch))


def _git_init(path):
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    subprocess.run(["git", "init", "-q", str(path)], check=True, env=env)


def test_worktree_cwd_hands_back_the_main_checkout_checkpoint_this_session_wrote(
        tmp_path, monkeypatch, capsys):
    """(1) The cwd is a linked worktree whose tracked handover.md is NEWER (a checkout rewrote it),
    but this session wrote the main checkout's handover.md: that one is the session's."""
    repo = _repo(tmp_path)
    now = time.time()
    SIG.mark_checkpoint_asked("s-1", now=now - 300)
    main_cp = _write_fresh(repo / "handover.md", "# Handover\n- MAIN-OWN-31\n")
    _set_mtime(main_cp, now - 200)
    wt = repo / ".claude" / "worktrees" / "wt"
    wt.mkdir(parents=True)
    _git_init(wt)
    wt_cp = wt / "handover.md"
    wt_cp.write_text("# Handover\n- WORKTREE-TRACKED-32\n", encoding="utf-8")
    _set_mtime(wt_cp, now - 60)
    tr = _transcript(tmp_path, [(main_cp, now - 200, True)])
    ctx = _context(_run(monkeypatch, capsys, _event(wt, transcript=str(tr))))
    assert "MAIN-OWN-31" in ctx
    assert str(main_cp) in ctx
    assert "WORKTREE-TRACKED-32" not in ctx
    assert str(wt_cp) not in ctx, "a file this session never wrote must not be named for editing"


def test_a_peers_newer_checkpoint_in_the_same_checkout_is_not_handed_back_as_ours(
        tmp_path, monkeypatch, capsys):
    """(2) A peer session wrote the shared checkout's handover.md after this session's request;
    this session wrote none. It must not come back as this session's checkpoint."""
    repo = _repo(tmp_path)
    now = time.time()
    SIG.mark_checkpoint_asked("s-1", now=now - 300)
    peer = repo / "handover.md"
    peer.write_text("# Handover\n- PEER-NEXT-ACTION-33\n", encoding="utf-8")
    _set_mtime(peer, now - 120)
    tr = _transcript(tmp_path, [])
    ctx = _context(_run(monkeypatch, capsys, _event(repo, transcript=str(tr))))
    assert "PEER-NEXT-ACTION-33" not in ctx
    assert "replace its first line" not in ctx, "nothing may be told to edit a file it did not write"
    assert str(peer) in ctx, "the candidate is still named, with its path"
    assert "2 min ago" in ctx, "and its age"
    assert "none is handed back as this session's" in ctx


def test_a_peer_overwriting_a_file_this_session_wrote_earlier_is_not_ours(tmp_path, monkeypatch,
                                                                           capsys):
    """(2b) This session wrote the shared handover.md, then a peer rewrote it later: the content
    on disk is the peer's, even though the path is in this session's records."""
    repo = _repo(tmp_path)
    now = time.time()
    SIG.mark_checkpoint_asked("s-1", now=now - 600)
    shared = _write_fresh(repo / "handover.md", "# Handover\n- PEER-OVERWROTE-34\n")
    _set_mtime(shared, now - 60)
    tr = _transcript(tmp_path, [(shared, now - 500, True)])
    ctx = _context(_run(monkeypatch, capsys, _event(repo, transcript=str(tr))))
    assert "PEER-OVERWROTE-34" not in ctx
    assert "replace its first line" not in ctx


def test_worktree_cwd_hands_back_the_worktree_copy_this_session_wrote(tmp_path, monkeypatch,
                                                                       capsys):
    """(3) The session wrote its worktree's handover.md; a peer's newer one sits in the main
    checkout, the cwd. The worktree copy is handed back, and only it is named for the edit."""
    repo = _repo(tmp_path)
    now = time.time()
    SIG.mark_checkpoint_asked("s-1", now=now - 300)
    wt = repo / ".claude" / "worktrees" / "wt"
    own = _write_fresh(wt / "handover.md", "# Handover\n- WT-OWN-35\n")
    _set_mtime(own, now - 200)
    peer = repo / "handover.md"
    peer.write_text("# Handover\n- MAIN-PEER-36\n", encoding="utf-8")
    _set_mtime(peer, now - 30)
    tr = _transcript(tmp_path, [(own, now - 200, True)])
    ctx = _context(_run(monkeypatch, capsys, _event(repo, transcript=str(tr))))
    assert "WT-OWN-35" in ctx and str(own) in ctx
    assert "MAIN-PEER-36" not in ctx
    assert str(peer) not in ctx


def test_a_failed_or_earlier_write_does_not_attribute(tmp_path, monkeypatch, capsys):
    repo = _repo(tmp_path)
    now = time.time()
    SIG.mark_checkpoint_asked("s-1", now=now - 300)
    cp = _write_fresh(repo / "handover.md", "# Handover\n- NOT-OURS-37\n")
    _set_mtime(cp, now - 100)
    tr = _transcript(tmp_path, [(cp, now - 400, True), (cp, now - 100, False)])
    ctx = _context(_run(monkeypatch, capsys, _event(repo, transcript=str(tr))))
    assert "NOT-OURS-37" not in ctx


def test_without_a_readable_transcript_an_unrecorded_cwd_file_is_only_listed(tmp_path,
                                                                             monkeypatch, capsys):
    """No transcript to read: the touched-paths record is the evidence, and a cwd file absent
    from it (a peer's, or one written through Bash) is named, never handed back as ours."""
    repo = _repo(tmp_path)
    SIG.mark_checkpoint_asked("s-1", now=time.time() - 60)
    (repo / "handover.md").write_text("# Handover\n- UNRECORDED-38\n", encoding="utf-8")
    ctx = _context(_run(monkeypatch, capsys, _event(repo)))
    assert "UNRECORDED-38" not in ctx
    assert str(repo / "handover.md") in ctx
    assert "replace its first line" not in ctx


def test_a_transcript_write_alone_finds_and_attributes_the_checkpoint(tmp_path, monkeypatch,
                                                                      capsys):
    """The touched-paths record can miss a write (evicted, or cleared); the transcript names it."""
    repo = _repo(tmp_path)
    now = time.time()
    SIG.mark_checkpoint_asked("s-1", now=now - 300)
    cp = tmp_path / "scratch" / "handover.md"
    cp.parent.mkdir()
    cp.write_text("# Handover\n- TRANSCRIPT-ONLY-39\n", encoding="utf-8")
    _set_mtime(cp, now - 100)
    tr = _transcript(tmp_path, [(cp, now - 100, True)])
    ctx = _context(_run(monkeypatch, capsys, _event(repo, transcript=str(tr))))
    assert "TRANSCRIPT-ONLY-39" in ctx and str(cp) in ctx


@pytest.mark.parametrize("seconds, expected", [
    (0, "0 min ago"), (119, "1 min ago"), (7199, "119 min ago"), (7200, "2 h 0 min ago"),
    (3 * 86400, "3 d ago"), (-5, "0 min ago"),
])
def test_age(seconds, expected):
    assert H._age(seconds) == expected


def test_own_checkpoint_writes_reads_successful_writes_after_the_request(tmp_path):
    now = time.time()
    a, b = tmp_path / "a" / "handover.md", tmp_path / "b" / "handover.md"
    other = tmp_path / "notes.md"
    tr = _transcript(tmp_path, [(a, now - 10, True), (b, now - 20, False), (other, now - 5, True),
                                (a, now - 500, True)])
    writes = H.own_checkpoint_writes(str(tr), now - 100)
    assert set(writes) == {os.path.normpath(str(a))}
    assert abs(writes[os.path.normpath(str(a))] - (now - 10)) < 0.01
    assert H.own_checkpoint_writes(str(tmp_path / "missing.jsonl"), now) is None


# ---- a session's own shell edit of the checkpoint it wrote --------------------------------------
# Measured over real transcripts: after the save request, sessions wrote handover.md with Write and
# then changed it through Bash a few seconds later - mostly a `sed -i` re-stamping the time after
# the PreToolUse CLOCK CHECK nudge (23 of 25), once a python heredoc. That moved the mtime past the
# Write's result, so the session's own checkpoint resumed as "unattributed" (25 misses). The fix
# extends the attribution record, not the slack: a write-shaped Bash command of THIS session that
# names the path, run after its own Write, keeps the file the session's. A change by anything else
# still breaks attribution.

def _tool_use(tid, at, name, tool_input, cwd):
    return {"type": "assistant", "timestamp": _iso(at - 0.5), "cwd": str(cwd), "message": {
        "role": "assistant", "content": [{"type": "tool_use", "id": tid, "name": name,
                                          "input": tool_input}]}}


def _tool_result(tid, at, cwd, ok=True):
    result = {"type": "tool_result", "tool_use_id": tid, "content": "ok"}
    if not ok:
        result["is_error"] = True
    return {"type": "user", "timestamp": _iso(at), "cwd": str(cwd), "message": {
        "role": "user", "content": [result]}}


def _session_transcript(tmp_path, events, cwd, name="s-1.jsonl"):
    """A transcript in the shape the harness writes, from (kind, ...) events in order.

    ("write", path, at, ok) and ("edit", path, at, ok) are Write/Edit tool calls with their result;
    ("bash", command, at, ok[, cwd]) a Bash call run in `cwd`; ("plan", plan_path, at) the plan_mode
    attachment the harness adds while plan mode is on.
    """
    lines = []
    for i, ev in enumerate(events):
        tid = f"toolu_{i:02d}"
        kind = ev[0]
        if kind in ("write", "edit"):
            _k, path, at, ok = ev
            tool_input = ({"file_path": str(path), "content": "x"} if kind == "write" else
                          {"file_path": str(path), "old_string": "a", "new_string": "b"})
            lines += [_tool_use(tid, at, kind.capitalize(), tool_input, cwd),
                      _tool_result(tid, at, cwd, ok)]
        elif kind == "bash":
            command, at, ok = ev[1], ev[2], ev[3]
            run_in = ev[4] if len(ev) > 4 else cwd
            lines += [_tool_use(tid, at, "Bash", {"command": command}, run_in),
                      _tool_result(tid, at, run_in, ok)]
        elif kind == "plan":
            lines.append({"type": "attachment", "timestamp": _iso(ev[2]), "cwd": str(cwd),
                          "attachment": {"type": "plan_mode", "reminderType": "full",
                                         "isSubAgent": False, "planFilePath": str(ev[1]),
                                         "planExists": True}})
    out = tmp_path / name
    out.write_text("".join(json.dumps(r) + "\n" for r in lines), encoding="utf-8")
    return out


def _own_then_bash(tmp_path, repo, command, *, bash_cwd=None, peer_after=False):
    """Own Write at now-200, then a Bash call at now-190; the file's mtime is the Bash moment, or a
    later peer change at now-60 when `peer_after`."""
    now = time.time()
    SIG.mark_checkpoint_asked("s-1", now=now - 300)
    cp = _write_fresh(repo / "handover.md", "# Checkpoint 12:03\n- OWN-RESTAMPED-41\n")
    _set_mtime(cp, now - 60 if peer_after else now - 190)
    tr = _session_transcript(tmp_path, [("write", cp, now - 200, True),
                                        ("bash", command, now - 190, True, bash_cwd or repo)], repo)
    return cp, tr


@pytest.mark.parametrize("command, run_in", [
    ('sed -i "1s/12:00/$(date +%H:%M)/" handover.md && head -1 handover.md', ""),
    ("T=$(date +%H:%M) && sed -i \"1s/12:00/$T/\" handover.md", ""),
    ("sed -i 1s/12:00/$(date +%H:%M)/ handover.md | head -1", ""),
    ("sed -i '1s/12:00/12:03/' ../handover.md && grep -n x src/mod.py", "sub"),
    ("sed -i '1s/12:00/12:03/' {abs} && head -1 {abs}", "sub"),
    (("python3 - <<'PY'\nfrom pathlib import Path\np = Path(\"handover.md\")\n"
      "p.write_text(p.read_text().replace(\"12:00\", \"12:03\"))\nPY"), ""),
    ("cd {repo} && sed -i '1s/12:00/12:03/' handover.md", "sub"),
])
def test_an_own_bash_edit_after_the_own_write_keeps_the_checkpoint_ours(tmp_path, monkeypatch,
                                                                        capsys, command, run_in):
    repo = _repo(tmp_path)
    cp = repo / "handover.md"
    # Spelled the way Git Bash reads a Windows path: unquoted, a backslash is an escape, so
    # `cd C:\temp\x\repo` lands in `C:tempxrepo` - bash itself never reaches the checkpoint.
    command = command.replace("{abs}", cp.as_posix()).replace("{repo}", repo.as_posix())
    _cp, tr = _own_then_bash(tmp_path, repo, command, bash_cwd=repo / run_in if run_in else repo)
    ctx = _context(_run(monkeypatch, capsys, _event(repo, transcript=str(tr))))
    assert "OWN-RESTAMPED-41" in ctx, "the session's own re-stamped checkpoint must come back"
    assert "replace its first line" in ctx


@pytest.mark.parametrize("command", [
    "head -1 handover.md && cat OPEN-WORK.md",                 # names it, changes nothing
    "cp handover.md handover.prev.md",                         # a copy reads its source
    "sed -i '1s/12:00/12:03/' notes/handover.md",              # changes ANOTHER handover.md
    "sed -i '1s/12:00/12:03/' OPEN-WORK.md",                   # changes another file
])
def test_an_own_bash_call_that_does_not_change_the_file_does_not_vouch_for_a_later_change(
        tmp_path, monkeypatch, capsys, command):
    """A peer changed the file after this session's Write; this session's own Bash call reads it
    or edits something else. The content on disk is still not known to be this session's."""
    repo = _repo(tmp_path)
    now = time.time()
    SIG.mark_checkpoint_asked("s-1", now=now - 300)
    cp = _write_fresh(repo / "handover.md", "# Checkpoint\n- PEER-CHANGED-42\n")
    _set_mtime(cp, now - 60)
    tr = _session_transcript(tmp_path, [("write", cp, now - 200, True),
                                        ("bash", command, now - 50, True)], repo)
    ctx = _context(_run(monkeypatch, capsys, _event(repo, transcript=str(tr))))
    assert "PEER-CHANGED-42" not in ctx
    assert "replace its first line" not in ctx


def test_a_change_after_the_own_bash_edit_still_breaks_attribution(tmp_path, monkeypatch, capsys):
    """Own Write, own sed, then a change by another process with no own call naming the path."""
    repo = _repo(tmp_path)
    _cp, tr = _own_then_bash(tmp_path, repo, "sed -i '1s/12:00/12:03/' handover.md",
                             peer_after=True)
    ctx = _context(_run(monkeypatch, capsys, _event(repo, transcript=str(tr))))
    assert "OWN-RESTAMPED-41" not in ctx
    assert "replace its first line" not in ctx


def test_a_bash_edit_before_the_own_write_does_not_attribute(tmp_path, monkeypatch, capsys):
    """Only a Bash edit that FOLLOWS the session's own Write continues its record: a shell edit on
    its own is not this session's checkpoint (it could have touched a peer's file)."""
    repo = _repo(tmp_path)
    now = time.time()
    SIG.mark_checkpoint_asked("s-1", now=now - 300)
    cp = _write_fresh(repo / "handover.md", "# Checkpoint\n- BASH-ONLY-43\n")
    _set_mtime(cp, now - 100)
    tr = _session_transcript(tmp_path, [("bash", "sed -i '1s/a/b/' handover.md", now - 100, True)],
                             repo)
    ctx = _context(_run(monkeypatch, capsys, _event(repo, transcript=str(tr))))
    assert "BASH-ONLY-43" not in ctx


# ---- the paths Git Bash really reaches -----------------------------------------------------------
# Measured on a Windows box: Git Bash spells a drive as `/c/...` (its `pwd` prints it, cygpath -u
# gives it), and `cd /c/temp/x && sed -i ... handover.md` edits C:\temp\x\handover.md. The hook read
# that cd as C:\c\temp\x (os.path roots `/c` at the current drive), so the session's own re-stamp of
# the checkpoint it had just written never matched the Write and the checkpoint resumed as
# unattributed. The other direction: unquoted, a backslash is an escape, so bash edits
# `C:tempxhandover.md` for `sed -i ... C:\temp\x\handover.md`, while the hook read the real file and
# let a call that changed nothing vouch for whatever is on disk now.

_DRIVE_PATH = "C:/temp/x/handover.md" if os.name == "nt" else "/c/temp/x/handover.md"


@pytest.mark.parametrize("command", [
    "cd /c/temp/x && sed -i '1s/12:00/12:03/' handover.md",
    "sed -i '1s/12:00/12:03/' /c/temp/x/handover.md",
    "cd /c/temp && sed -i '1s/12:00/12:03/' x/handover.md",
])
def test_a_git_bash_drive_path_names_the_file_bash_edits(tmp_path, command):
    assert H.bash_targets(command, str(tmp_path)) == {H._norm(_DRIVE_PATH): False}


def test_a_script_body_keeps_its_own_reading_of_a_drive_path(tmp_path):
    """A heredoc feeds a native interpreter: Windows Python opens `/c/temp/...` under the current
    drive root, so only the shell's own words get Git Bash's reading."""
    command = "python3 - <<'PY'\nopen('/c/temp/x/handover.md', 'w').write('x')\nPY"
    assert H.bash_targets(command, str(tmp_path)) == {H._norm("/c/temp/x/handover.md"): False}


@pytest.mark.parametrize("command, reached", [
    (r"sed -i '1s/a/b/' C:\temp\x\handover.md", False),       # bash reads C:tempxhandover.md
    (r"cd /c/temp && sed -i '1s/a/b/' x\handover.md", False),  # bash reads xhandover.md
    (r"sed -i '1s/a/b/' 'C:\temp\x\handover.md'", True),
    (r'sed -i "1s/a/b/" "C:\temp\x\handover.md"', True),
])
def test_an_unquoted_backslash_path_is_not_the_file_bash_edits(tmp_path, command, reached):
    """Only a Windows host reads a backslash as a separator; on POSIX no spelling here names a
    checkpoint at all, so the quoted controls are expected to reach it only there."""
    expected = {H._norm(r"C:\temp\x\handover.md"): False} if reached and os.name == "nt" else {}
    assert H.bash_targets(command, str(tmp_path)) == expected


def _host_checked_reading(token, escaped):
    """`_as_bash_reads` as it read a word with its own host check (`os.name == "nt"`): the
    reference the shared reading must equal. On Windows a rooted word that is neither a drive
    (`/c/...`) nor UNC (`//server/x`) is a Git Bash mount, which no reader places (None)."""
    if escaped:
        token = H._BASH_ESCAPE.sub(r"\1", token)
    windows = os.name == "nt"
    if (windows and token[:1] == "/" and not re.match(r"/[A-Za-z](?:/|$)", token)
            and not re.match(r"//[^/]", token)):
        return None
    return shell_text.msys_drive_path(token, windows)


def _random_words(count, seed=250):
    rng = random.Random(seed)
    alphabet = "/cCdDx:.~\\ '\"-_"
    return ["".join(rng.choice(alphabet) for _ in range(rng.randint(0, 12))) for _ in range(count)]


_BASH_WORDS = ["/c/temp/x/handover.md", "/C/temp", "/d", "/c/", "/c", "/tmp/handover.md",
               "/usr/bin", "/cygdrive/c/x", "//c/x", "/cc/x", "x/handover.md", r"C:\temp\x",
               r"x\handover.md", r"\/c/temp", "~/handover.md", ""]


@pytest.mark.parametrize("escaped", [True, False])
def test_a_bash_word_s_drive_reading_equals_the_host_checked_one(escaped):
    """The word reader takes the drive decision from shell_text (`reads_msys_drives` for the Bash
    tool), which must answer exactly as the host check it replaces, on this host's arm; the
    Windows cell runs the other one."""
    for token in _BASH_WORDS + _random_words(2000):
        assert H._as_bash_reads(token, escaped=escaped) == _host_checked_reading(token, escaped), token


@pytest.mark.parametrize("command", [
    "sed -i '1s/12:00/12:03/' /tmp/x/handover.md",
    "cd /tmp/x && sed -i '1s/12:00/12:03/' handover.md",
])
def test_a_git_bash_mount_names_no_file_bash_edits_on_windows(tmp_path, command):
    """Git Bash maps `/tmp` through its mount table (the user's %TEMP%), so on Windows the file it
    edits is not C:\\tmp\\x\\handover.md and the call vouches for nothing; elsewhere `/tmp` is
    just a rooted directory."""
    expected = {} if os.name == "nt" else {H._norm("/tmp/x/handover.md"): False}
    assert H.bash_targets(command, str(tmp_path)) == expected


def test_a_script_body_keeps_its_own_reading_of_a_mount_path(tmp_path):
    """A heredoc feeds a native interpreter, which opens `/tmp/...` at the current drive's root."""
    command = "python3 - <<'PY'\nopen('/tmp/x/handover.md', 'w').write('x')\nPY"
    assert H.bash_targets(command, str(tmp_path)) == {H._norm("/tmp/x/handover.md"): False}


def _git_bash_spelling(path):
    """`path` as Git Bash's `pwd` prints it: C:\\a\\b -> /c/a/b."""
    drive, rest = os.path.splitdrive(str(path))
    return "/" + drive[0].lower() + rest.replace("\\", "/")


@pytest.mark.skipif(os.name != "nt", reason="a drive letter exists only on Windows")
def test_an_own_edit_after_a_git_bash_drive_cd_keeps_the_checkpoint_ours(tmp_path, monkeypatch,
                                                                       capsys):
    repo = _repo(tmp_path)
    command = f"cd {_git_bash_spelling(repo)} && sed -i '1s/12:00/12:03/' handover.md"
    _cp, tr = _own_then_bash(tmp_path, repo, command, bash_cwd=tmp_path)
    ctx = _context(_run(monkeypatch, capsys, _event(repo, transcript=str(tr))))
    assert "OWN-RESTAMPED-41" in ctx, "the session's own re-stamped checkpoint must come back"
    assert "replace its first line" in ctx


# ---- a prefix name: handover-<topic>.md with the checkpoint heading ------------------------------
# Measured: a session kept its checkpoint in the scratchpad as handover-<topic>.md (heading
# included) across five compactions, and none was handed back; the suffix rule above did not cover
# the prefix form.

def test_a_prefix_name_with_the_lessons_heading_is_handed_back(tmp_path, monkeypatch, capsys):
    repo = _repo(tmp_path)
    now = time.time()
    SIG.mark_checkpoint_asked("s-1", now=now - 300)
    cp = tmp_path / "scratchpad" / "handover-crud-design.md"
    cp.parent.mkdir()
    cp.write_text("# Handover - crud design\n- PREFIX-44\n\n" + _LESSONS, encoding="utf-8")
    _set_mtime(cp, now - 100)
    tr = _session_transcript(tmp_path, [("write", cp, now - 100, True)], repo)
    ctx = _context(_run(monkeypatch, capsys, _event(repo, transcript=str(tr))))
    assert "PREFIX-44" in ctx and str(cp) in ctx


def test_a_prefix_name_without_the_heading_is_not_a_checkpoint(tmp_path, monkeypatch, capsys):
    repo = _repo(tmp_path)
    now = time.time()
    SIG.mark_checkpoint_asked("s-1", now=now - 300)
    cp = tmp_path / "scratchpad" / "handover-notes.md"
    cp.parent.mkdir()
    cp.write_text("# Notes\n- PREFIX-NOTES-45\n", encoding="utf-8")
    _set_mtime(cp, now - 100)
    tr = _session_transcript(tmp_path, [("write", cp, now - 100, True)], repo)
    ctx = _context(_run(monkeypatch, capsys, _event(repo, transcript=str(tr))))
    assert "PREFIX-NOTES-45" not in ctx


# ---- a checkpoint the session retired itself before the compaction ------------------------------
# Measured: 10 of the 47 compactions with a save request and nothing handed back were sessions that
# finished the work after the checkpoint and marked their own file `# STALE ...` (by Edit or by a
# `sed -i`) or removed it, before the compaction landed. The block then said "no checkpoint was
# saved", which is false and sends the reader to the transcript looking for a lost save.

_REMOVE_COMMAND = "g" + "it rm -q handover.md && g" + "it commit -qF msg.txt"


def _retired_by(tmp_path, repo, how):
    now = time.time()
    SIG.mark_checkpoint_asked("s-1", now=now - 300)
    cp = _write_fresh(repo / "handover.md", "# STALE - read 2026-11-14, work continued\n- R-46\n")
    _set_mtime(cp, now - 100)
    events = [("write", cp, now - 200, True)]
    if how == "edit":
        events.append(("edit", cp, now - 100, True))
    elif how == "sed":
        events.append(("bash", "sed -i '1s/^/# STALE - done\\n\\n/' handover.md", now - 100, True))
    elif how == "rm":
        cp.unlink()
        events.append(("bash", _REMOVE_COMMAND, now - 100, True))
    return cp, _session_transcript(tmp_path, events, repo)


@pytest.mark.parametrize("how", ["edit", "sed", "rm"])
def test_a_checkpoint_the_session_retired_itself_is_reported_as_retired(tmp_path, monkeypatch,
                                                                         capsys, how):
    repo = _repo(tmp_path)
    cp, tr = _retired_by(tmp_path, repo, how)
    ctx = _context(_run(monkeypatch, capsys, _event(repo, transcript=str(tr))))
    assert "no checkpoint was saved" not in ctx
    assert "retired" in ctx and str(cp) in ctx
    assert "summary" in ctx
    assert "R-46" not in ctx, "a retired checkpoint is not handed back"


def test_a_stale_line_written_by_another_process_is_not_called_our_retirement(tmp_path,
                                                                               monkeypatch,
                                                                               capsys):
    repo = _repo(tmp_path)
    now = time.time()
    SIG.mark_checkpoint_asked("s-1", now=now - 300)
    cp = _write_fresh(repo / "handover.md", "# STALE - read by a peer\n- R-47\n")
    _set_mtime(cp, now - 60)
    tr = _session_transcript(tmp_path, [("write", cp, now - 200, True)], repo)
    ctx = _context(_run(monkeypatch, capsys, _event(repo, transcript=str(tr))))
    assert "retired" not in ctx


def test_a_checkpoint_removed_by_something_else_is_not_called_our_retirement(tmp_path,
                                                                              monkeypatch, capsys):
    repo = _repo(tmp_path)
    now = time.time()
    SIG.mark_checkpoint_asked("s-1", now=now - 300)
    cp = _write_fresh(repo / "handover.md", "# Checkpoint\n- R-48\n")
    tr = _session_transcript(tmp_path, [("write", cp, now - 200, True)], repo)
    cp.unlink()
    ctx = _context(_run(monkeypatch, capsys, _event(repo, transcript=str(tr))))
    assert "retired" not in ctx


# ---- plan mode: the plan file is the only writable file ----------------------------------------
# Measured: three sessions in plan mode, asked for a checkpoint, wrote it into the plan file (the
# only file plan mode lets them write) and got "no checkpoint was saved" back. The harness itself
# re-attaches the plan file after a compaction, so the block must point there instead.

def test_a_plan_file_written_after_the_request_is_named_instead_of_no_checkpoint(tmp_path,
                                                                                  monkeypatch,
                                                                                  capsys):
    repo = _repo(tmp_path)
    now = time.time()
    SIG.mark_checkpoint_asked("s-1", now=now - 300)
    plan = tmp_path / "home" / ".claude" / "plans" / "some-plan.md"
    plan.parent.mkdir(parents=True)
    plan.write_text("# Plan\n\n## Checkpoint\n- PLAN-49\n", encoding="utf-8")
    tr = _session_transcript(tmp_path, [("plan", plan, now - 400),
                                        ("edit", plan, now - 100, True)], repo)
    ctx = _context(_run(monkeypatch, capsys, _event(repo, transcript=str(tr))))
    assert "no checkpoint was saved" not in ctx
    assert str(plan) in ctx and "plan file" in ctx
    assert "replace its first line" not in ctx, "the plan file is never marked STALE"


def test_a_plan_file_written_before_the_request_is_not_named(tmp_path, monkeypatch, capsys):
    repo = _repo(tmp_path)
    now = time.time()
    SIG.mark_checkpoint_asked("s-1", now=now - 300)
    plan = tmp_path / "home" / ".claude" / "plans" / "some-plan.md"
    plan.parent.mkdir(parents=True)
    plan.write_text("# Plan\n", encoding="utf-8")
    tr = _session_transcript(tmp_path, [("plan", plan, now - 500),
                                        ("edit", plan, now - 400, True)], repo)
    ctx = _context(_run(monkeypatch, capsys, _event(repo, transcript=str(tr))))
    assert str(plan) not in ctx
    assert "no checkpoint was saved" in ctx
