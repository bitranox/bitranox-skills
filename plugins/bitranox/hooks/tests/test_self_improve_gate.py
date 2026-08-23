"""Tests for self-improve-gate.py (gated Stop hook).

Contract: reads a Stop event JSON on stdin (transcript_path, cwd, stop_hook_active).
When the last USER message carries a learning signal (correction / "remember") OR the
last ASSISTANT message self-admits a miss, it prints a {"decision":"block",...} JSON on
stdout. main() always returns 0. It blocks at most once per user message (state file)
and honors stop_hook_active.

The state file lives under tempfile.gettempdir(); tests redirect that to an isolated
dir so runs do not collide with the real gate or each other.

All content is ASCII.
"""

import io
import json
import sys
from pathlib import Path

import pytest

import self_improve_gate as G


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    """Send the gate's per-project state file AND its HOME-relative writes into a temp dir.

    Two different roots need redirecting, and isolating one hides that the other is still live:

    * `tempfile.gettempdir()` - the per-project "already blocked for this message" state file.
    * `Path.home()` - `record_session_meta()` writes `~/.claude/self-improve-audit/<key>.session.json`
      on every gate run. Left unpatched, that lands in the DEVELOPER's real home: 24 files per
      full-suite run, and 23,583 had accumulated there, each naming a `/tmp/pytest-of-*` transcript
      that no longer exists. `Path.home()` reads `HOME` on POSIX and `USERPROFILE` on Windows, so
      both are set - patching only HOME would leave this suite leaking on the Windows CI cell.
    """
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    monkeypatch.setattr("tempfile.gettempdir", lambda: str(state_dir))
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    return state_dir


def make_transcript(tmp_path, user="", asst=""):
    p = tmp_path / "transcript.jsonl"
    lines = []
    if user:
        lines.append(json.dumps({"type": "user", "message": {"content": user}}))
    if asst:
        lines.append(json.dumps({"type": "assistant", "message": {"content": asst}}))
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(p)


def run_gate(monkeypatch, tmp_path, event):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(event)))
    rc = G.main()
    return rc


def decision_of(capsys):
    out = capsys.readouterr().out.strip()
    return json.loads(out)["decision"] if out else None


def test_user_correction_blocks(tmp_path, monkeypatch, capsys):
    tp = make_transcript(tmp_path, user="No, that's wrong, the path is /etc not /opt")
    rc = run_gate(monkeypatch, tmp_path, {"transcript_path": tp, "cwd": str(tmp_path)})
    assert rc == 0
    assert decision_of(capsys) == "block"


def test_user_remember_blocks(tmp_path, monkeypatch, capsys):
    tp = make_transcript(tmp_path, user="from now on always run the tests first")
    run_gate(monkeypatch, tmp_path, {"transcript_path": tp, "cwd": str(tmp_path)})
    assert decision_of(capsys) == "block"


def test_assistant_endorses_user_idea_blocks(tmp_path, monkeypatch, capsys):
    # The high-signal case: the LLM judges the USER's suggestion good -> adopt it.
    tp = make_transcript(tmp_path, user="we could cache the sitemap",
                         asst="Good idea - caching the sitemap would cut the calls.")
    run_gate(monkeypatch, tmp_path, {"transcript_path": tp, "cwd": str(tmp_path)})
    assert decision_of(capsys) == "block"


def test_user_endorsement_good_idea_blocks(tmp_path, monkeypatch, capsys):
    tp = make_transcript(tmp_path, user="Good idea, let's do that.")
    run_gate(monkeypatch, tmp_path, {"transcript_path": tp, "cwd": str(tmp_path)})
    assert decision_of(capsys) == "block"


def test_endorsement_nice_catch_blocks(tmp_path, monkeypatch, capsys):
    tp = make_transcript(tmp_path, user="q", asst="Nice catch on the license gate.")
    run_gate(monkeypatch, tmp_path, {"transcript_path": tp, "cwd": str(tmp_path)})
    assert decision_of(capsys) == "block"


def _reason_of(capsys):
    out = capsys.readouterr().out.strip()
    return json.loads(out)["reason"] if out else ""


def _two_trees(tmp_path):
    """cwd's tree (treeA/projA1) + a sibling project and a SECOND tree."""
    for tree in ("treeA", "treeB"):
        (tmp_path / tree / ".claude-memory").mkdir(parents=True)
        (tmp_path / tree / "CLAUDE.md").write_text("top\n", encoding="utf-8")
    for lvl in ("treeA/projA1", "treeA/projA2", "treeB/projB1"):
        (tmp_path / lvl).mkdir(parents=True)
        (tmp_path / lvl / "CLAUDE.md").write_text("proj\n", encoding="utf-8")
    return tmp_path


def test_block_reason_names_other_repos_the_turn_edited(tmp_path, monkeypatch, capsys):
    # The wrong-dir bug: cwd=projA1 but the turn edited a SIBLING project and ANOTHER tree.
    # The nudge must surface those levels so capture can route --proj by SUBJECT, not cwd.
    import self_improve_signals as S
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    root = _two_trees(tmp_path)
    cwd = str(root / "treeA" / "projA1")
    S.record_touched_path("sX", str(root / "treeA" / "projA2" / "sib.py"))
    S.record_touched_path("sX", str(root / "treeB" / "projB1" / "other.py"))
    tp = make_transcript(tmp_path, user="No, that's wrong, the flag is --tree")
    run_gate(monkeypatch, tmp_path, {"transcript_path": tp, "cwd": cwd, "session_id": "sX"})
    reason = _reason_of(capsys)
    assert str(root / "treeA" / "projA2") in reason        # sibling project surfaced
    assert str(root / "treeB" / "projB1") in reason        # other tree surfaced
    assert "different tree" in reason.lower()              # the unrecoverable case is called out
    assert "--proj" in reason                              # tells it HOW to route


def test_block_reason_has_no_routing_hint_when_only_cwd_touched(tmp_path, monkeypatch, capsys):
    import self_improve_signals as S
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    root = _two_trees(tmp_path)
    cwd = str(root / "treeA" / "projA1")
    S.record_touched_path("sY", str(root / "treeA" / "projA1" / "own.py"))
    tp = make_transcript(tmp_path, user="No, that's wrong")
    run_gate(monkeypatch, tmp_path, {"transcript_path": tp, "cwd": cwd, "session_id": "sY"})
    reason = _reason_of(capsys)
    assert "This turn also edited" not in reason           # no noise when the subject IS cwd


def _iso_home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))


def test_buffered_subagent_learning_blocks_even_when_main_turn_is_quiet(tmp_path, monkeypatch, capsys):
    # The P1 case: the SUBAGENT found the learning; the main turn says nothing signal-worthy.
    # Without this the learning dies in the subagent's transcript.
    import self_improve_signals as S
    _iso_home(tmp_path, monkeypatch)
    S.buffer_subagent_learning("sub1", {"agent_type": "Explore", "agent_id": "a1",
                                        "matched": ["realization"],
                                        "snippet": "it turns out check-tree misses sideways refs"})
    tp = make_transcript(tmp_path, user="ok thanks", asst="Done.")   # no main-turn signal
    run_gate(monkeypatch, tmp_path, {"transcript_path": tp, "cwd": str(tmp_path), "session_id": "sub1"})
    assert decision_of(capsys) == "block"


def test_buffered_subagent_learning_is_named_in_the_reason(tmp_path, monkeypatch, capsys):
    import self_improve_signals as S
    _iso_home(tmp_path, monkeypatch)
    S.buffer_subagent_learning("sub2", {"agent_type": "Explore", "agent_id": "a9",
                                        "matched": ["realization"],
                                        "snippet": "the rehome verb over-promotes to the anchor"})
    tp = make_transcript(tmp_path, user="ok", asst="Done.")
    run_gate(monkeypatch, tmp_path, {"transcript_path": tp, "cwd": str(tmp_path), "session_id": "sub2"})
    reason = _reason_of(capsys)
    assert "SUBAGENT" in reason.upper()
    assert "rehome verb over-promotes" in reason           # the actual finding is surfaced
    assert "Explore" in reason                             # which agent found it


def test_no_subagent_buffer_no_extra_noise(tmp_path, monkeypatch, capsys):
    _iso_home(tmp_path, monkeypatch)
    tp = make_transcript(tmp_path, user="No, that's wrong")
    run_gate(monkeypatch, tmp_path, {"transcript_path": tp, "cwd": str(tmp_path), "session_id": "none"})
    assert "SUBAGENT" not in _reason_of(capsys).upper()


def test_owed_post_compaction_nap_blocks_even_with_a_quiet_turn(tmp_path, monkeypatch, capsys):
    # A hook cannot RUN the nap (no model in a hook), so PostCompact records an obligation and the
    # Stop gate refuses to stop while it is owed - that is what makes the nap non-optional.
    import self_improve_signals as S
    _iso_home(tmp_path, monkeypatch)
    S.mark_nap_owed(str(tmp_path))
    tp = make_transcript(tmp_path, user="ok thanks", asst="Done.")      # no signal at all
    run_gate(monkeypatch, tmp_path, {"transcript_path": tp, "cwd": str(tmp_path), "session_id": "s"})
    assert decision_of(capsys) == "block"


def test_owed_nap_reason_directs_to_the_nap_and_says_read_from_disk(tmp_path, monkeypatch, capsys):
    import self_improve_signals as S
    _iso_home(tmp_path, monkeypatch)
    S.mark_nap_owed(str(tmp_path))
    tp = make_transcript(tmp_path, user="ok", asst="Done.")
    run_gate(monkeypatch, tmp_path, {"transcript_path": tp, "cwd": str(tmp_path), "session_id": "s"})
    reason = _reason_of(capsys)
    assert "meta-dream-nap" in reason
    assert "compact" in reason.lower()


def test_owed_nap_from_another_session_names_that_transcript_and_does_not_claim_this_one(
        tmp_path, monkeypatch, capsys):
    # Measured 2026-08-10: a flag three days old blocked a session that had never compacted, while
    # asserting "compaction cleared your context". The premise was false and sent the reader looking
    # for a compaction in the wrong transcript. Name the file that actually compacted instead.
    import self_improve_signals as S
    _iso_home(tmp_path, monkeypatch)
    old = tmp_path / "older-session.jsonl"
    old.write_text("{}\n", encoding="utf-8")
    S.mark_nap_owed(str(tmp_path), session_id="sid-old", transcript_path=str(old))
    tp = make_transcript(tmp_path, user="ok", asst="Done.")
    run_gate(monkeypatch, tmp_path, {"transcript_path": tp, "cwd": str(tmp_path),
                                     "session_id": "sid-current"})
    reason = _reason_of(capsys)
    assert str(old) in reason                       # review THAT file, not this session's
    assert "EARLIER session" in reason              # and say the compaction was not this one


def test_owed_nap_from_this_session_still_reads_as_this_session(tmp_path, monkeypatch, capsys):
    import self_improve_signals as S
    _iso_home(tmp_path, monkeypatch)
    tp = make_transcript(tmp_path, user="ok", asst="Done.")
    S.mark_nap_owed(str(tmp_path), session_id="sid-current", transcript_path=tp)
    run_gate(monkeypatch, tmp_path, {"transcript_path": tp, "cwd": str(tmp_path),
                                     "session_id": "sid-current"})
    reason = _reason_of(capsys)
    assert "EARLIER session" not in reason
    assert "meta-dream-nap" in reason


def test_no_owed_nap_no_block_on_a_quiet_turn(tmp_path, monkeypatch, capsys):
    _iso_home(tmp_path, monkeypatch)
    tp = make_transcript(tmp_path, user="ok thanks", asst="Done.")
    run_gate(monkeypatch, tmp_path, {"transcript_path": tp, "cwd": str(tmp_path), "session_id": "s"})
    assert decision_of(capsys) is None


def test_gate_records_session_meta_so_the_dream_can_find_the_transcript(tmp_path, monkeypatch, capsys):
    # The dream is a model pass and never gets transcript_path; the gate has it every turn.
    import self_improve_signals as S
    _iso_home(tmp_path, monkeypatch)
    tp = make_transcript(tmp_path, user="hello")
    run_gate(monkeypatch, tmp_path, {"transcript_path": tp, "cwd": str(tmp_path), "session_id": "sid9"})
    meta = S.read_session_meta(str(tmp_path))
    assert meta.get("transcript_path") == tp and meta.get("session_id") == "sid9"


def test_bare_ok_does_not_block(tmp_path, monkeypatch, capsys):
    tp = make_transcript(tmp_path, user="ok thanks, looks good", asst="Great, nice. Done.")
    rc = run_gate(monkeypatch, tmp_path, {"transcript_path": tp, "cwd": str(tmp_path)})
    assert rc == 0
    assert decision_of(capsys) is None


def test_assistant_self_admitted_miss_blocks(tmp_path, monkeypatch, capsys):
    tp = make_transcript(tmp_path, user="ok", asst="You're right, my mistake - I'll fix it")
    run_gate(monkeypatch, tmp_path, {"transcript_path": tp, "cwd": str(tmp_path)})
    assert decision_of(capsys) == "block"


def test_assistant_hook_block_self_admission_blocks(tmp_path, monkeypatch, capsys):
    tp = make_transcript(
        tmp_path, user="check the processes", asst="The hook caught my self-matching echo labels. Let me redo it."
    )
    run_gate(monkeypatch, tmp_path, {"transcript_path": tp, "cwd": str(tmp_path)})
    assert decision_of(capsys) == "block"


def test_assistant_blocked_by_guard_blocks(tmp_path, monkeypatch, capsys):
    tp = make_transcript(tmp_path, user="ok", asst="My command was blocked by the guard, so I will use ps instead.")
    run_gate(monkeypatch, tmp_path, {"transcript_path": tp, "cwd": str(tmp_path)})
    assert decision_of(capsys) == "block"


def test_assistant_explaining_a_hook_does_not_block(tmp_path, monkeypatch, capsys):
    tp = make_transcript(
        tmp_path, user="how does it work", asst="The tell-sweep hook blocks em dashes on every write to keep prose clean."
    )
    rc = run_gate(monkeypatch, tmp_path, {"transcript_path": tp, "cwd": str(tmp_path)})
    assert rc == 0
    assert decision_of(capsys) is None


def test_assistant_generic_redo_does_not_block(tmp_path, monkeypatch, capsys):
    tp = make_transcript(tmp_path, user="run it again", asst="Let me redo the query without the join and rerun it.")
    rc = run_gate(monkeypatch, tmp_path, {"transcript_path": tp, "cwd": str(tmp_path)})
    assert rc == 0
    assert decision_of(capsys) is None


def test_assistant_realization_topology_blocks(tmp_path, monkeypatch, capsys):
    tp = make_transcript(
        tmp_path, user="where does the generator run",
        asst="Now I understand the real topology: the generator runs on the internal host.")
    run_gate(monkeypatch, tmp_path, {"transcript_path": tp, "cwd": str(tmp_path)})
    assert decision_of(capsys) == "block"


def test_assistant_figured_out_blocks(tmp_path, monkeypatch, capsys):
    tp = make_transcript(tmp_path, user="why is it slow",
                         asst="I figured out that the worker actually runs on the media host.")
    run_gate(monkeypatch, tmp_path, {"transcript_path": tp, "cwd": str(tmp_path)})
    assert decision_of(capsys) == "block"


def test_assistant_turns_out_blocks(tmp_path, monkeypatch, capsys):
    tp = make_transcript(tmp_path, user="trace it",
                         asst="It turns out the data flows through the cache first.")
    run_gate(monkeypatch, tmp_path, {"transcript_path": tp, "cwd": str(tmp_path)})
    assert decision_of(capsys) == "block"


def test_assistant_clear_now_blocks(tmp_path, monkeypatch, capsys):
    tp = make_transcript(tmp_path, user="trace the path",
                         asst="Now it's clear: the cache sits in front of the database.")
    run_gate(monkeypatch, tmp_path, {"transcript_path": tp, "cwd": str(tmp_path)})
    assert decision_of(capsys) == "block"


def test_assistant_clearer_picture_blocks(tmp_path, monkeypatch, capsys):
    tp = make_transcript(tmp_path, user="how do the pieces connect",
                         asst="I have a clearer picture now of how the services connect.")
    run_gate(monkeypatch, tmp_path, {"transcript_path": tp, "cwd": str(tmp_path)})
    assert decision_of(capsys) == "block"


def test_question_is_that_clear_does_not_block(tmp_path, monkeypatch, capsys):
    tp = make_transcript(tmp_path, user="ok",
                         asst="The requirements are clear and well scoped. Is that clear enough?")
    rc = run_gate(monkeypatch, tmp_path, {"transcript_path": tp, "cwd": str(tmp_path)})
    assert rc == 0
    assert decision_of(capsys) is None


def test_assistant_plain_acknowledgement_does_not_block(tmp_path, monkeypatch, capsys):
    tp = make_transcript(tmp_path, user="please adjust the layout",
                         asst="I understand the requirement and will adjust the layout now.")
    rc = run_gate(monkeypatch, tmp_path, {"transcript_path": tp, "cwd": str(tmp_path)})
    assert rc == 0
    assert decision_of(capsys) is None


def test_normal_turn_does_not_block(tmp_path, monkeypatch, capsys):
    tp = make_transcript(tmp_path, user="add a function to sum a list", asst="Done, added sum_list().")
    rc = run_gate(monkeypatch, tmp_path, {"transcript_path": tp, "cwd": str(tmp_path)})
    assert rc == 0
    assert decision_of(capsys) is None


def test_blocks_only_once_per_user_message(tmp_path, monkeypatch, capsys):
    tp = make_transcript(tmp_path, user="no, that is wrong")
    event = {"transcript_path": tp, "cwd": str(tmp_path)}
    run_gate(monkeypatch, tmp_path, event)
    assert decision_of(capsys) == "block"  # first stop blocks
    run_gate(monkeypatch, tmp_path, event)
    assert decision_of(capsys) is None  # same message -> state file suppresses repeat


def test_stop_hook_active_passes(tmp_path, monkeypatch, capsys):
    tp = make_transcript(tmp_path, user="no, that is wrong")
    rc = run_gate(monkeypatch, tmp_path, {"transcript_path": tp, "cwd": str(tmp_path), "stop_hook_active": True})
    assert rc == 0
    assert decision_of(capsys) is None


def test_missing_transcript_passes(tmp_path, monkeypatch, capsys):
    rc = run_gate(monkeypatch, tmp_path, {"cwd": str(tmp_path)})
    assert rc == 0
    assert decision_of(capsys) is None


def test_malformed_stdin_passes(monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO("not json"))
    assert G.main() == 0
    assert decision_of(capsys) is None


def test_german_signal_blocks(tmp_path, monkeypatch, capsys):
    tp = make_transcript(tmp_path, user="nein, das ist falsch")
    run_gate(monkeypatch, tmp_path, {"transcript_path": tp, "cwd": str(tmp_path)})
    assert decision_of(capsys) == "block"


def test_gate_does_not_block_on_an_invoked_skills_own_body(tmp_path, monkeypatch, capsys):
    """Invoking a skill injects its SKILL.md as a type=user message; its prose is not a directive."""
    body = ("Base directory for this skill: /home/u/.claude/plugins/cache/m/p/1/skills/demo\n"
            "\n# demo\n\nFrom now on always run the full gate. Never skip it.\n")
    tp = make_transcript(tmp_path, user=body)
    run_gate(monkeypatch, tmp_path, {"transcript_path": tp, "cwd": str(tmp_path)})
    assert decision_of(capsys) is None


def test_gate_still_blocks_on_a_real_user_directive(tmp_path, monkeypatch, capsys):
    """The must-not-break half: an ordinary directive must still block."""
    tp = make_transcript(tmp_path, user="from now on always run the full gate before pushing")
    run_gate(monkeypatch, tmp_path, {"transcript_path": tp, "cwd": str(tmp_path)})
    assert decision_of(capsys) == "block"


def test_gate_still_blocks_when_the_ASSISTANT_admits_a_miss_under_a_skill_body(tmp_path, monkeypatch, capsys):
    """Suppressing the user half must not disable the assistant half of the same turn."""
    body = "Base directory for this skill: /x/skills/demo\n\n# demo\n\nsome documentation.\n"
    tp = make_transcript(tmp_path, user=body, asst="you're right, my mistake - I read the stale log")
    run_gate(monkeypatch, tmp_path, {"transcript_path": tp, "cwd": str(tmp_path)})
    assert decision_of(capsys) == "block"


def test_the_gate_writes_its_session_file_under_the_isolated_home(tmp_path, monkeypatch, capsys):
    """The gate records session meta under `Path.home()`; the fixture must redirect that.

    Isolating `tempfile.gettempdir()` alone is not isolation: `record_session_meta` resolves its
    path from the HOME directory, so an unpatched HOME sends one file per run into the real
    `~/.claude/self-improve-audit/`. Measured before this was wired: 24 files per full-suite run,
    and 23,583 accumulated on the developer's machine, every one naming a `/tmp/pytest-of-*`
    transcript that no longer exists.
    """
    tp = make_transcript(tmp_path, user="no, that is wrong")
    run_gate(monkeypatch, tmp_path, {"transcript_path": tp, "cwd": str(tmp_path), "session_id": "s1"})

    written = list((tmp_path / "home" / ".claude" / "self-improve-audit").glob("*.session.json"))
    assert written, "the gate wrote no session file inside the isolated HOME - HOME is not redirected"
