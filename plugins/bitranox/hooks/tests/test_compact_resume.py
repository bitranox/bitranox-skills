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
