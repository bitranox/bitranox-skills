"""Tests for dream_state.py (meta-dream cadence-marker CLI). ASCII only."""
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


def test_session_review_is_quiet_when_nothing_new(home, tmp_path, capsys):
    proj = "/p/x"
    _session(home, proj, tmp_path, '{"type":"user","message":{"content":"x"}}\n')
    D.main(["session-review", proj])
    capsys.readouterr()
    D.main(["session-reviewed", proj])
    capsys.readouterr()
    assert D.main(["session-review", proj]) == 0
    assert "NOTHING NEW" in capsys.readouterr().out.upper()


def test_session_review_without_a_known_transcript_does_not_crash(home, capsys):
    assert D.main(["session-review", "/unknown/proj"]) == 0


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
    D.main(["saw-promotable", "s", "/p/x"])
    capsys.readouterr()
    for _ in range(3):
        D.main(["should-promote", "s", "/p/x"])
        assert capsys.readouterr().out.strip() == "hold"          # still 1 sighting after repeated reads


def test_promoted_clears_the_counter(home, capsys):
    D.main(["saw-promotable", "s", "/p/x"])
    D.main(["saw-promotable", "s", "/p/x"])
    capsys.readouterr()
    assert D.main(["promoted", "s", "/p/x"]) == 0
    capsys.readouterr()
    D.main(["should-promote", "s", "/p/x"])
    assert capsys.readouterr().out.strip() == "hold"              # counter forgotten after promotion


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
