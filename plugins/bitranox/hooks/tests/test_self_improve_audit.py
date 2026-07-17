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
