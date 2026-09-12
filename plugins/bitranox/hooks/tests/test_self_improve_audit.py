"""Tests for self-improve-audit.py (SessionEnd miss-audit hook).

Builds synthetic transcripts and an isolated HOME so the audit file lands in tmp_path.

All content is ASCII.
"""

import io
import json
import sys
from pathlib import Path

import pytest

import self_improve_audit as A
import self_improve_signals as S


@pytest.fixture(autouse=True)
def isolate_home(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    return home


def make_transcript(tmp_path, turns):
    """turns: list of (role, text). Writes a JSONL transcript and returns its path."""
    p = tmp_path / "transcript.jsonl"
    lines = [json.dumps({"type": role, "message": {"content": text}}) for role, text in turns]
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(p)


def run_audit(monkeypatch, transcript, cwd):
    event = {"transcript_path": transcript, "cwd": cwd, "hook_event_name": "SessionEnd"}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(event)))
    return A.main()


def test_writes_audit_for_candidate_misses(tmp_path, monkeypatch):
    tp = make_transcript(tmp_path, [
        ("user", "no, that's wrong"),                          # strict hit -> not a candidate
        ("assistant", "let me reconsider the parser approach"), # candidate (broad, not strict)
        ("user", "why did you skip the tests again?"),          # candidate (broad, not strict)
        ("assistant", "Done, added it."),                       # neutral
    ])
    rc = run_audit(monkeypatch, tp, "/proj/alpha")
    assert rc == 0
    out = S.audit_file("/proj/alpha")
    assert out.is_file()
    body = out.read_text(encoding="utf-8")
    assert "<SELF-IMPROVE-AUDIT>" in body
    assert "2 message(s)" in body              # exactly the two candidates
    assert "reconsider" in body.lower()
    assert "why did you" in body.lower()
    assert "that's wrong" not in body.lower()  # the strict hit is not listed as a miss


def test_no_file_when_no_candidates(tmp_path, monkeypatch):
    tp = make_transcript(tmp_path, [
        ("user", "no, that's wrong"),            # strict
        ("assistant", "You're right, fixing."),  # strict
        ("assistant", "Done, added the test."),  # neutral
    ])
    rc = run_audit(monkeypatch, tp, "/proj/beta")
    assert rc == 0
    assert not S.audit_file("/proj/beta").is_file()


def test_stale_audit_removed_when_clean(tmp_path, monkeypatch):
    out = S.audit_file("/proj/gamma")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("old report", encoding="utf-8")
    tp = make_transcript(tmp_path, [("assistant", "Done, nothing notable.")])
    run_audit(monkeypatch, tp, "/proj/gamma")
    assert not out.is_file()  # cleared


def test_missing_transcript_is_noop(tmp_path, monkeypatch):
    event = {"transcript_path": str(tmp_path / "nope.jsonl"), "cwd": "/proj/x"}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(event)))
    assert A.main() == 0
    assert not S.audit_file("/proj/x").is_file()


def test_candidates_are_capped(tmp_path, monkeypatch):
    turns = [("assistant", "let me reconsider item %d" % i) for i in range(30)]
    tp = make_transcript(tmp_path, turns)
    run_audit(monkeypatch, tp, "/proj/cap")
    body = S.audit_file("/proj/cap").read_text(encoding="utf-8")
    listed = body.count("- [assistant]")
    assert listed <= A._MAX_CANDIDATES
    assert "30 message(s)" in body  # the total count is still reported honestly


# ---- the report names the moment it describes: PreCompact is not SessionEnd ---------------

def run_audit_for(monkeypatch, transcript, cwd, event_name):
    event = {"transcript_path": transcript, "cwd": cwd, "hook_event_name": event_name}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(event)))
    return A.main()


def test_a_precompact_report_does_not_call_the_session_previous(tmp_path, monkeypatch):
    """The hook is registered on PreCompact as well as SessionEnd, and SessionStart surfaces the file
    after a compaction - into the SAME session, where 'the previous session' is false."""
    tp = make_transcript(tmp_path, [("assistant", "let me reconsider the parser approach")])
    run_audit_for(monkeypatch, tp, "/proj/compact", "PreCompact")
    body = S.audit_file("/proj/compact").read_text(encoding="utf-8").lower()
    assert "previous session" not in body and "last session" not in body
    assert "compact" in body


def test_a_precompact_report_does_not_call_the_skill_roster_last_session():
    cand = {"role": "assistant", "matched": ["reconsider"], "snippet": "let me reconsider",
            "escaped": False}
    body = A.render_report([cand], {"bitranox:meta-self-improve": 1}, event="PreCompact").lower()
    assert "last session" not in body and "previous session" not in body
    assert "bitranox:meta-self-improve" in body


def test_a_sessionend_report_still_names_the_previous_session(tmp_path, monkeypatch):
    """Control: the SessionEnd wording was right for SessionEnd and must stay."""
    tp = make_transcript(tmp_path, [("assistant", "let me reconsider the parser approach")])
    run_audit_for(monkeypatch, tp, "/proj/ended", "SessionEnd")
    assert "previous session" in S.audit_file("/proj/ended").read_text(encoding="utf-8").lower()


# ---- fixture suppression is per tool block, and a test-file name hides only its own line ----

def _tool_results(tmp_path, *contents):
    return write_raw(tmp_path, [{"type": "user", "message": {"content": [
        {"type": "tool_result", "content": c} for c in contents]}}])


def test_a_test_file_name_elsewhere_in_the_block_does_not_hide_a_real_gap(tmp_path):
    """The suppression was all-or-nothing over the message: one test_*.py token anywhere switched
    off every tool signal in it. A line naming a test file is data; the line after it is not."""
    t = _tool_results(tmp_path, "tests/test_alpha.py\ntests/test_beta.py\nbash: pct: command not found")
    cands = A.find_candidates(str(t))
    assert any("command not found" in m for c in cands for m in c["matched"]), cands


def test_pytest_output_in_one_result_does_not_hide_a_gap_in_another(tmp_path):
    """Blocks are judged independently. Current transcripts write one tool_result per record, so
    this pins the block boundary rather than a shape seen in practice."""
    t = _tool_results(tmp_path, "1 failed, 41 passed in 2.10s", "bash: pct: command not found")
    cands = A.find_candidates(str(t))
    assert any("command not found" in m for c in cands for m in c["matched"]), cands


def test_a_signal_on_the_same_line_as_a_test_file_name_is_still_data(tmp_path):
    """grep output over test files puts the phrase and the file name on one line: that stays quiet."""
    t = _tool_results(tmp_path, 'tests/test_x.py:12:    assert "command not found" in err')
    assert A.find_candidates(str(t)) == []


def test_a_candidate_snippet_shows_the_block_that_matched(tmp_path):
    """With several blocks in one message, the snippet must quote the signal, not the fixture."""
    t = _tool_results(tmp_path, "1 failed, 41 passed in 2.10s " + "x" * 200, "bash: pct: command not found")
    cands = [c for c in A.find_candidates(str(t)) if c["role"] == "tool"]
    assert cands and "command not found" in cands[0]["snippet"], cands


# ---- P2: tool-block scanning + skill tally ---------------------------------------------

def write_raw(tmp_path, objs):
    p = tmp_path / "raw.jsonl"
    p.write_text("\n".join(json.dumps(o) for o in objs) + "\n", encoding="utf-8")
    return p


def test_finds_a_learning_expressed_only_in_a_tool_call(tmp_path):
    """The whole point of P2: the discovery never reaches prose. Here the model runs a flag that
    does not exist and the tool_result says so - nothing in any text block hints at it."""
    t = write_raw(tmp_path, [
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Bash",
             "input": {"command": "reconcile_memory_index.py --rehome-to root"}}]}},
        {"type": "user", "message": {"content": [
            {"type": "tool_result",
             "content": "error: unrecognized arguments: --rehome-to"}]}},
    ])
    cands = A.find_candidates(str(t))
    assert any(c["role"] == "tool" for c in cands), cands
    assert any("unrecognized arguments" in m for c in cands for m in c["matched"]), cands


def test_ordinary_tool_output_is_not_a_candidate(tmp_path):
    t = write_raw(tmp_path, [
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Bash", "input": {"command": "pytest -q"}}]}},
        {"type": "user", "message": {"content": [
            {"type": "tool_result", "content": "1170 passed, 7 skipped in 14.18s"}]}},
    ])
    assert A.find_candidates(str(t)) == []


def test_pytest_fixture_output_is_not_a_candidate(tmp_path):
    """Regression: when the session's own work is signal-detection code, reading test_*.py or a RED
    pytest tail injects TOOL_SIGNAL_PATTERN phrases as literal DATA. Those must NOT become misses."""
    t = write_raw(tmp_path, [
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Read",
             "input": {"file_path": "plugins/bitranox/hooks/tests/test_self_improve_signals.py"}}]}},
        {"type": "user", "message": {"content": [
            {"type": "tool_result",
             "content": "--- RED --- E error: unrecognized arguments: --rehome-to\n"
                        "test_self_improve_signals.py::test_x FAILED\n1 failed, 41 passed"}]}},
    ])
    assert A.find_candidates(str(t)) == []


def test_a_real_tool_gap_still_surfaces_outside_a_test_run(tmp_path):
    """The suppression must be narrow: a genuine gap in ordinary tool output still surfaces."""
    t = write_raw(tmp_path, [
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Bash", "input": {"command": "pct list"}}]}},
        {"type": "user", "message": {"content": [
            {"type": "tool_result", "content": "bash: pct: command not found"}]}},
    ])
    cands = A.find_candidates(str(t))
    assert any(c["role"] == "tool" for c in cands), cands


def test_text_blocks_still_scanned_alongside_tool_blocks(tmp_path):
    """Adding tool scanning must not regress the prose path."""
    t = write_raw(tmp_path, [
        {"type": "user", "message": {"content": [
            {"type": "text", "text": "that is not working, it fails again"}]}},
    ])
    assert any(c["role"] == "user" for c in A.find_candidates(str(t)))


def test_report_names_the_skills_that_ran(tmp_path, monkeypatch):
    """flag-a-skill-when-a-real-bug-slips-past-it needs the roster of what actually ran."""
    t = write_raw(tmp_path, [
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Skill", "input": {"skill": "compuse-git"}}]}},
        {"type": "user", "message": {"content": [
            {"type": "tool_result", "content": "fatal: not a git repository"}]}},
    ])
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(
        {"transcript_path": str(t), "cwd": str(tmp_path)})))
    assert A.main() == 0
    report = S.audit_file(str(tmp_path)).read_text(encoding="utf-8")
    assert "compuse-git" in report, report


# ---- an invoked skill's own body is not a user learning signal --------------------------------

# Matches the BROAD user patterns only (no strict directive), which is the real leak: a strict hit
# is already excluded as "the gate caught it", so only broad-only text reaches the candidate list.
_INJECTED_SKILL_BODY = (
    "Base directory for this skill: /home/u/.claude/plugins/cache/mkt/plug/9.9.9/skills/demo\n"
    "\n# demo\n\nDo not always run the subset; a wrong verdict here is worse than none.\n"
)


def test_the_injected_body_would_otherwise_be_a_candidate(tmp_path):
    """Premise guard: without suppression this text IS a broad-only candidate, so the next test can fail."""
    assert not S.strict_user_hit(_INJECTED_SKILL_BODY)
    assert S.broad_matches("user", _INJECTED_SKILL_BODY)


def test_an_invoked_skills_body_is_not_a_candidate_miss(tmp_path):
    t = make_transcript(tmp_path, [("user", _INJECTED_SKILL_BODY)])
    assert A.find_candidates(t) == []


def test_a_real_broad_only_user_miss_still_surfaces(tmp_path):
    """The must-not-break half: suppression must not swallow an ordinary broad-recall miss."""
    t = make_transcript(tmp_path, [("user", "the deploy path is wrong, it is under /srv not /opt")])
    assert A.find_candidates(t)


def test_a_message_that_QUOTES_the_marker_mid_sentence_still_surfaces(tmp_path):
    """Anchored at the start: quoting the marker must not hide a real signal."""
    t = make_transcript(tmp_path, [
        ("user", "the header reads 'Base directory for this skill: /x' but the deploy path is wrong")])
    assert A.find_candidates(t)
