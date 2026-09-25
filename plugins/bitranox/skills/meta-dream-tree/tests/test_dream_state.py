"""Tests for dream_state.py (meta-dream cadence-marker CLI). ASCII only."""
import os
import subprocess
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


# ---- session-review: the dream reads the session from DISK, incrementally --------------------

def _session(home, proj, tmp_path, text):
    tp = tmp_path / "sess.jsonl"
    tp.write_text(text, encoding="utf-8")
    D.sig.record_session_meta(proj, "sid1", str(tp))
    return tp


def test_session_review_prints_unreviewed_transcript_then_reviewed_advances(home, tmp_path, capsys):
    # This is the compaction fix: the dream reads the FILE (which survives compaction), not its
    # context - and never re-reads what it already consumed.
    proj = "/p/x"
    _session(home, proj, tmp_path, '{"type":"user","message":{"content":"the flag is --check-tree"}}\n')
    assert D.main(["session-review", proj]) == 0
    out = capsys.readouterr().out
    assert "--check-tree" in out                      # the on-disk content came back

    assert D.main(["session-reviewed", proj]) == 0    # advance the mark
    capsys.readouterr()
    D.main(["session-review", proj])
    out2 = capsys.readouterr().out
    assert "--check-tree" not in out2                 # already consumed -> not re-fed to the model


def test_session_review_surfaces_buffered_subagent_learnings_and_touched_paths(home, tmp_path, capsys):
    # routing evidence is about LEVELS, so the touched path must live under a real CLAUDE.md-bearing
    # dir (a path under no level is not routable and is correctly not surfaced)
    tree = tmp_path / "tree"
    (tree / ".claude-memory").mkdir(parents=True)
    (tree / "CLAUDE.md").write_text("top\n", encoding="utf-8")
    for p in ("cwdproj", "otherproj"):
        (tree / p).mkdir()
        (tree / p / "CLAUDE.md").write_text("proj\n", encoding="utf-8")
    proj = str(tree / "cwdproj")
    _session(home, proj, tmp_path, '{"type":"user","message":{"content":"hi"}}\n')
    D.sig.record_session_meta(proj, "sidZ", str(tmp_path / "sess.jsonl"))
    D.sig.buffer_subagent_learning("sidZ", {"agent_type": "Explore", "snippet": "rehome over-promotes"})
    D.sig.record_touched_path("sidZ", str(tree / "otherproj" / "x.py"))
    D.main(["session-review", proj])
    out = capsys.readouterr().out
    assert "rehome over-promotes" in out              # subagent findings are a dream input
    assert str(tree / "otherproj") in out             # so is the routing evidence


def test_session_review_targets_the_transcript_that_actually_compacted(home, tmp_path, capsys):
    # The obligation is per-PROJECT, the material per-SESSION. Reviewing only the CURRENT session
    # while clearing the flag discharges the compacted session's stretch unread - measured
    # 2026-08-10, where 5.6 MB of an earlier session sat unreviewed behind a 3-day-old flag.
    proj = "/p/x"
    old = tmp_path / "compacted.jsonl"
    old.write_text('{"type":"user","message":{"content":"the OLD lesson"}}\n', encoding="utf-8")
    _session(home, proj, tmp_path, '{"type":"user","message":{"content":"the NEW turn"}}\n')
    D.sig.mark_nap_owed(proj, session_id="sid-old", transcript_path=str(old))

    assert D.main(["session-review", proj]) == 0
    out = capsys.readouterr().out
    assert "the OLD lesson" in out                    # the owed transcript is what comes back
    assert str(old) in out                            # and it says which file it is showing


def test_an_owed_transcript_whose_tail_is_one_huge_line_is_still_the_target(home, tmp_path, capsys):
    # The "does the owed transcript still have unreviewed bytes?" probe read the NEWEST 2 MB and
    # dropped the partial first line - so an unreviewed stretch that was one line over 2 MB read as
    # "nothing new", and the review fell back to the live session with the owed stretch unread.
    proj = "/p/x"
    old = tmp_path / "compacted.jsonl"
    old.write_bytes(b'{"type":"user","message":{"content":"the OLD lesson ' + b"x" * 2_100_000
                    + b'"}}\n')
    _session(home, proj, tmp_path, '{"type":"user","message":{"content":"the NEW turn"}}\n')
    D.sig.mark_nap_owed(proj, session_id="sid-old", transcript_path=str(old))
    assert D._review_target(proj) == str(old)


def test_session_reviewed_marks_the_owed_transcript_it_showed(home, tmp_path, capsys):
    # review and reviewed must agree on the file, or the watermark advances on the wrong one and
    # the owed stretch is skipped forever.
    proj = "/p/x"
    old = tmp_path / "compacted.jsonl"
    old.write_text('{"type":"user","message":{"content":"the OLD lesson"}}\n', encoding="utf-8")
    _session(home, proj, tmp_path, '{"type":"user","message":{"content":"the NEW turn"}}\n')
    D.sig.mark_nap_owed(proj, session_id="sid-old", transcript_path=str(old))

    D.main(["session-review", proj])
    capsys.readouterr()
    assert D.main(["session-reviewed", proj]) == 0
    assert str(old) in capsys.readouterr().out
    assert D.sig.get_watermark(proj, str(old), "dream") == old.stat().st_size

    D.main(["session-review", proj])                  # owed one consumed -> back to this session
    out = capsys.readouterr().out
    assert "the NEW turn" in out


def test_session_review_ignores_an_owed_transcript_that_is_gone(home, tmp_path, capsys):
    # a deleted or rotated transcript must not strand the review on a path that cannot be read
    proj = "/p/x"
    _session(home, proj, tmp_path, '{"type":"user","message":{"content":"the NEW turn"}}\n')
    D.sig.mark_nap_owed(proj, session_id="sid-old", transcript_path=str(tmp_path / "gone.jsonl"))
    assert D.main(["session-review", proj]) == 0
    assert "the NEW turn" in capsys.readouterr().out


def test_session_review_is_quiet_when_nothing_new(home, tmp_path, capsys):
    proj = "/p/x"
    _session(home, proj, tmp_path, '{"type":"user","message":{"content":"x"}}\n')
    D.main(["session-review", proj])
    capsys.readouterr()
    D.main(["session-reviewed", proj])
    capsys.readouterr()
    assert D.main(["session-review", proj]) == 0
    assert "NOTHING NEW" in capsys.readouterr().out.upper()


def test_session_review_without_a_known_transcript_reports_discovery_failure(home, capsys):
    # "couldn't find a transcript" must be DISTINCT from "nothing new" - collapsing them silently
    # reviews zero bytes on a keying/timing miss while reporting success.
    assert D.main(["session-review", "/unknown/proj"]) == 0
    out = capsys.readouterr().out
    assert "NO TRANSCRIPT DISCOVERED" in out
    assert "NOTHING NEW" not in out.upper()


def _place_native_transcript(proj, text):
    """Write a *.jsonl under the project's native dir WITHOUT recording session meta (the
    post-/clear manual-run case: no Stop hook has recorded the transcript path yet)."""
    d = D.sig.memory_dir(proj).parent
    d.mkdir(parents=True, exist_ok=True)
    tp = d / "sessABC.jsonl"
    tp.write_text(text, encoding="utf-8")
    return tp


def test_session_review_self_locates_transcript_when_meta_absent(home, tmp_path, capsys):
    proj = "/p/x"
    _place_native_transcript(proj, '{"type":"user","message":{"content":"the flag is --check-tree"}}\n')
    assert D.main(["session-review", proj]) == 0
    out = capsys.readouterr().out
    assert "--check-tree" in out                       # self-located and reviewed, not a silent miss
    assert "NOTHING NEW" not in out.upper()


def test_session_reviewed_advances_watermark_for_a_self_located_transcript(home, tmp_path, capsys):
    proj = "/p/x"
    _place_native_transcript(proj, '{"type":"user","message":{"content":"--check-tree lives here"}}\n')
    assert D.main(["session-review", proj]) == 0
    capsys.readouterr()
    assert D.main(["session-reviewed", proj]) == 0     # must resolve the self-located path too
    capsys.readouterr()
    D.main(["session-review", proj])
    assert "--check-tree" not in capsys.readouterr().out   # already consumed -> not re-fed


# ---- corroboration gate (defect F): saw-promotable / should-promote / promoted --------------

def test_should_promote_is_read_only(home, capsys):
    # Querying must NOT count as a sighting. Asked from the SAME project that recorded, the answer
    # could only stay "hold" either way, so the read has to come from a SECOND project: if the query
    # recorded, that project would become the corroborator and the verdict would flip to "promote".
    D.main(["saw-promotable", "s", "/p/a"])
    capsys.readouterr()
    for _ in range(3):
        D.main(["should-promote", "s", "/p/b"])
        assert capsys.readouterr().out.strip() == "hold"          # still one corroborator


def test_repeat_sightings_in_one_project_never_corroborate(home, capsys):
    """One act of judgement re-derived is not corroboration. A deep crosstree fan-out re-reads the
    same UNCHANGED fact bodies on every run, so a per-run sighting counter let run 2 corroborate
    run 1 with no new evidence - 84 sightings were recorded in a single measured pass."""
    for _ in range(84):
        assert D.main(["saw-promotable", "s", "/p/x"]) == 0
        assert capsys.readouterr().out.strip() == "1"             # one project, one corroborator
    assert D.main(["should-promote", "s", "/p/x"]) == 0
    assert capsys.readouterr().out.strip() == "hold"


def test_two_sightings_in_one_project_still_hold(home, capsys):
    D.main(["saw-promotable", "s", "/p/x"])
    D.main(["saw-promotable", "s", "/p/x"])
    capsys.readouterr()
    assert D.main(["should-promote", "s", "/p/x"]) == 0
    assert capsys.readouterr().out.strip() == "hold"              # N=2 from one project: not evidence


def test_two_distinct_projects_corroborate(home, capsys):
    # Real corroboration must still work: the fix tightens WHAT counts, not whether anything counts.
    # A model-inferred fact routed to the tree top needs >= 2 distinct projects before it may promote.
    assert D.main(["saw-promotable", "some-slug", "/p/a"]) == 0
    assert capsys.readouterr().out.strip() == "1"                 # dwell after the first project
    assert D.main(["should-promote", "some-slug", "/p/a"]) == 0
    assert capsys.readouterr().out.strip() == "hold"              # one project: not yet
    assert D.main(["saw-promotable", "some-slug", "/p/b"]) == 0
    assert capsys.readouterr().out.strip() == "2"
    assert D.main(["should-promote", "some-slug", "/p/a"]) == 0
    assert capsys.readouterr().out.strip() == "promote"           # readable from either project
    assert D.main(["should-promote", "some-slug", "/p/b"]) == 0
    assert capsys.readouterr().out.strip() == "promote"


def test_promoted_clears_every_project_sighting(home, capsys):
    D.main(["saw-promotable", "s", "/p/a"])
    D.main(["saw-promotable", "s", "/p/b"])
    capsys.readouterr()
    assert D.main(["promoted", "s", "/p/a"]) == 0
    capsys.readouterr()
    # /p/b's sighting went too - a leftover entry would let one later sighting re-trip the gate
    assert D.main(["saw-promotable", "s", "/p/b"]) == 0
    assert capsys.readouterr().out.strip() == "1"
    assert D.main(["should-promote", "s", "/p/b"]) == 0
    assert capsys.readouterr().out.strip() == "hold"


def test_session_review_reports_which_skills_actually_ran(home, tmp_path, capsys):
    """P2: the skill-gap correlation (flag-a-skill-when-a-real-bug-slips-past-it) needs REAL
    invocation data - in a long session the early Skill calls have scrolled out of context, so
    the dream must read them from the transcript rather than recall them."""
    proj = "/p/x"
    _session(home, proj, tmp_path, "\n".join([
        '{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Skill",'
        '"input":{"skill":"compuse-git"}}]}}',
        '{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Skill",'
        '"input":{"skill":"compuse-git"}}]}}',
        '{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Bash",'
        '"input":{"command":"ls"}}]}}',
    ]) + "\n")
    assert D.main(["session-review", proj]) == 0
    out = capsys.readouterr().out
    assert "compuse-git" in out and "x2" in out, out


def test_session_review_omits_the_skill_line_when_none_ran(home, tmp_path, capsys):
    proj = "/p/x"
    _session(home, proj, tmp_path, '{"type":"user","message":{"content":"plain text"}}\n')
    assert D.main(["session-review", proj]) == 0
    assert "SKILLS INVOKED" not in capsys.readouterr().out


# ---- a stretch over the review chunk is reviewed in parts, never silently cut ----------------

def _big_transcript(home, tmp_path, size_bytes):
    """EARLY on the first line, LATE on the last, filler lines between: `size_bytes` in all."""
    filler = '{"type":"user","message":{"content":"' + "f" * 980 + '"}}\n'
    early = '{"type":"user","message":{"content":"EARLY-MARKER"}}\n'
    late = '{"type":"user","message":{"content":"LATE-MARKER"}}\n'
    n = max(0, (size_bytes - len(early) - len(late)) // len(filler))
    return _session(home, "/p/big", tmp_path, early + filler * n + late)


def test_a_stretch_over_the_chunk_is_shown_oldest_first_and_says_it_is_truncated(
        home, tmp_path, capsys):
    tp = _big_transcript(home, tmp_path, 2 * D.REVIEW_CHUNK_BYTES)
    size = tp.stat().st_size
    assert D.main(["session-review", "/p/big"]) == 0
    out = capsys.readouterr().out
    assert "EARLY-MARKER" in out and "LATE-MARKER" not in out
    assert "TRUNCATED" in out

    assert D.main(["session-reviewed", "/p/big"]) == 0
    mark = D.sig.get_watermark("/p/big", str(tp), "dream")
    assert 0 < mark < size, "reviewed may only advance past what was SHOWN"
    assert tp.read_bytes()[mark - 1:mark] == b"\n", "the cut lands on a line end"
    capsys.readouterr()

    # Keep going part by part: every byte is shown exactly once, and the end is reached.
    shown = len(out.encode("utf-8"))
    for _ in range(4):
        assert D.main(["session-review", "/p/big"]) == 0
        part = capsys.readouterr().out
        shown += len(part.encode("utf-8"))
        assert D.main(["session-reviewed", "/p/big"]) == 0
        capsys.readouterr()
        if "LATE-MARKER" in part:
            break
    assert "LATE-MARKER" in part
    assert D.sig.get_watermark("/p/big", str(tp), "dream") == size
    assert shown >= size, "no part was skipped"
    D.main(["session-review", "/p/big"])
    assert "NOTHING NEW" in capsys.readouterr().out.upper()


def test_a_stretch_under_the_chunk_is_shown_whole_and_not_marked_truncated(
        home, tmp_path, capsys):
    """Control: the ordinary case is one pass, as before."""
    _big_transcript(home, tmp_path, 40_000)
    assert D.main(["session-review", "/p/big"]) == 0
    out = capsys.readouterr().out
    assert "EARLY-MARKER" in out and "LATE-MARKER" in out and "TRUNCATED" not in out


# ---- a failed write is reported, never a success line -----------------------------------------

NO_CHMOD = not hasattr(os, "geteuid") or os.geteuid() == 0


@pytest.fixture
def locked_audit(home):
    audit = home / ".claude" / "self-improve-audit"
    audit.mkdir(parents=True, exist_ok=True)
    audit.chmod(0o555)
    yield audit
    audit.chmod(0o755)


@pytest.mark.skipif(NO_CHMOD, reason="needs a non-root POSIX user for a read-only dir")
def test_done_reports_a_marker_it_could_not_write(home, locked_audit, capsys):
    _mem("/p/y")
    assert D.main(["done", "/p/y"]) == 2
    captured = capsys.readouterr()
    assert "marked done" not in captured.out and "error" in captured.err


@pytest.mark.skipif(NO_CHMOD, reason="needs a non-root POSIX user for a read-only dir")
def test_session_reviewed_reports_a_watermark_it_could_not_write(home, tmp_path, capsys):
    # The session meta is recorded BEFORE the dir is locked, so the transcript is found and only
    # the watermark write can fail.
    tp = _session(home, "/p/w", tmp_path, '{"type":"user","message":{"content":"x"}}\n')
    audit = home / ".claude" / "self-improve-audit"
    audit.chmod(0o555)
    try:
        assert D.main(["session-reviewed", "/p/w"]) == 2
    finally:
        audit.chmod(0o755)
    assert "advanced" not in capsys.readouterr().out
    assert D.sig.get_watermark("/p/w", str(tp), "dream") == 0


@pytest.mark.skipif(NO_CHMOD, reason="needs a non-root POSIX user for a read-only dir")
def test_saw_promotable_reports_a_sighting_it_could_not_write(home, locked_audit, capsys):
    assert D.main(["saw-promotable", "s4", "/p/a"]) == 2
    assert D.sig.promotion_dwell("/p/a", "s4") == 0


@pytest.mark.skipif(NO_CHMOD, reason="needs a non-root POSIX user for a read-only file")
def test_promoted_reports_a_clear_it_could_not_write(home, capsys):
    D.main(["saw-promotable", "s3", "/p/a"])
    D.main(["saw-promotable", "s3", "/p/b"])
    store = D.sig.promotion_file()
    store.chmod(0o444)
    try:
        assert D.main(["promoted", "s3"]) == 2
    finally:
        store.chmod(0o644)
    capsys.readouterr()
    D.main(["should-promote", "s3"])
    assert capsys.readouterr().out.strip() == "promote", "the sightings really are still there"


# The state layer now RAISES a failed write (StateWriteError) instead of swallowing it; each verb
# must turn that into its exit 2, never a traceback. A directory where the store file belongs blocks
# the write on every platform, where the chmod variants above need a non-root POSIX user.

def _block_with_a_dir(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.mkdir()
    (path / "keep").write_text("x", encoding="utf-8")


def test_session_reviewed_exits_2_when_the_watermark_store_is_blocked(home, tmp_path, capsys):
    tp = _session(home, "/p/wb", tmp_path, '{"type":"user","message":{"content":"x"}}\n')
    _block_with_a_dir(D.sig.watermark_file("/p/wb"))
    assert D.main(["session-reviewed", "/p/wb"]) == 2
    captured = capsys.readouterr()
    assert "advanced" not in captured.out and "did not land" in captured.err
    assert str(tp) in captured.err


def test_saw_promotable_exits_2_when_the_sighting_store_is_blocked(home, capsys):
    _block_with_a_dir(D.sig.promotion_file())
    assert D.main(["saw-promotable", "s5", "/p/a"]) == 2
    captured = capsys.readouterr()
    assert captured.out.strip() == "" and "did not land" in captured.err


def test_promoted_exits_2_when_the_sighting_store_is_blocked(home, capsys):
    _block_with_a_dir(D.sig.promotion_file())
    assert D.main(["promoted", "s5"]) == 2
    captured = capsys.readouterr()
    assert "cleared" not in captured.out and "did not land" in captured.err


def test_promoted_with_a_writable_store_clears_the_gate(home, capsys):
    """Control for the refusal above."""
    D.main(["saw-promotable", "s3", "/p/a"])
    D.main(["saw-promotable", "s3", "/p/b"])
    assert D.main(["promoted", "s3"]) == 0
    capsys.readouterr()
    D.main(["should-promote", "s3"])
    assert capsys.readouterr().out.strip() == "hold"


def test_session_reviewed_with_no_known_transcript_marks_nothing(home, capsys):
    assert D.main(["session-reviewed", "/unknown/proj"]) == 0
    assert "nothing to mark" in capsys.readouterr().out


# ---- arguments: an unknown flag is refused, never taken as the project path ------------------

@pytest.mark.parametrize("argv", [["done", "--dry-run"], ["session-review", "--structured", "/p/y"],
                                  ["due", "/p/x", "extra"], ["saw-promotable", "s", "/p", "x"],
                                  ["should-promote"]])
def test_a_bad_argument_is_a_usage_error_and_changes_nothing(home, argv, capsys):
    assert D.main(argv) == 2
    captured = capsys.readouterr()
    assert "usage" in captured.err
    assert not list((home / ".claude").rglob("*.dream"))


def test_structured_only_is_still_accepted(home, tmp_path, capsys):
    _session(home, "/p/x", tmp_path, '{"type":"user","message":{"content":"RAWLINE"}}\n')
    assert D.main(["session-review", "--structured-only", "/p/x"]) == 0
    assert "RAWLINE" not in capsys.readouterr().out


@pytest.mark.parametrize("flag", ["-h", "--help"])
def test_help_lists_every_verb_and_exits_0(home, flag, capsys):
    assert D.main([flag]) == 0
    out = capsys.readouterr().out
    for verb in ("due", "done", "mode", "saw-promotable", "should-promote", "promoted",
                 "session-review", "session-reviewed", "--structured-only"):
        assert verb in out


def test_a_cp1252_stdout_does_not_crash_on_a_non_ascii_transcript(home, tmp_path):
    tp = tmp_path / "u.jsonl"
    tp.write_text('{"type":"user","message":{"content":"done ✅ → next"}}\n',
                  encoding="utf-8")
    D.sig.record_session_meta("/p/u", "sid-u", str(tp))
    env = dict(os.environ, PYTHONIOENCODING="cp1252")
    env.pop("PYTHONUTF8", None)
    r = subprocess.run([sys.executable, str(Path(D.__file__).resolve()), "session-review",
                        "/p/u"], capture_output=True, check=False, env=env)
    assert b"Traceback" not in r.stderr, r.stderr.decode("utf-8", "replace")
    assert r.returncode == 0
