"""Tests for subagent-capture.py (SubagentStop hook).

Contract: reads a SubagentStop event on stdin. Scans the SUBAGENT's own transcript
(`agent_transcript_path` - NOT `transcript_path`, which is the MAIN session's, probe-verified) plus
`last_assistant_message` for learning signals, and buffers hits for the main session's capture to
drain. Always returns 0 and never emits a decision (a subagent must never be blocked).

All content ASCII.
"""
import io
import json

import pytest

import self_improve_signals as S
import subagent_capture as C


@pytest.fixture(autouse=True)
def _home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    (h / ".claude").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


def _transcript(tmp_path, name, msgs):
    p = tmp_path / name
    p.write_text("\n".join(json.dumps({"type": r, "message": {"content": t}}) for r, t in msgs) + "\n",
                 encoding="utf-8")
    return str(p)


def _event(tmp_path, agent_msgs=(), main_msgs=(), final=None, session="s1"):
    ev = {"hook_event_name": "SubagentStop", "session_id": session,
          "agent_id": "a1", "agent_type": "general-purpose",
          "agent_transcript_path": _transcript(tmp_path, "agent.jsonl", agent_msgs or [("user", "go")]),
          "transcript_path": _transcript(tmp_path, "main.jsonl", main_msgs or [("user", "hi")])}
    if final is not None:
        ev["last_assistant_message"] = final
    return ev


def _run(monkeypatch, event):
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(event)))
    return C.main()


def test_buffers_a_signal_found_in_the_subagent_transcript(tmp_path, monkeypatch):
    ev = _event(tmp_path, agent_msgs=[("assistant", "I was wrong - the real cause is the stale venv")])
    assert _run(monkeypatch, ev) == 0
    got = S.read_subagent_learnings("s1")
    assert len(got) == 1
    assert got[0]["agent_type"] == "general-purpose" and "stale venv" in got[0]["snippet"]


def test_ignores_signals_in_the_dispatch_prompt_user_message(tmp_path, monkeypatch):
    # A subagent's USER messages are the PARENT's dispatch prompt (and tool results), not the
    # subagent's own discovery. Instruction phrasing ("always use ...") matches the signal patterns,
    # but it is the main agent's own text - already in its context - so it must NOT be buffered as a
    # subagent learning. (Real defect: 5 dream-scanner dispatch prompts were buffered and re-nudged.)
    ev = _event(tmp_path,
                agent_msgs=[("user", "Always use the SUBJECT repo. Find and return candidates. Do not edit."),
                            ("assistant", "Listed the candidates as requested.")],
                final="Listed the candidates as requested.")
    _run(monkeypatch, ev)
    assert S.read_subagent_learnings("s1") == []


def test_reads_the_AGENT_transcript_not_the_main_one(tmp_path, monkeypatch):
    # The probe-caught bug: transcript_path is the MAIN session's. A signal that exists ONLY in the
    # main transcript must NOT be attributed to the subagent (the main gate already covers it).
    ev = _event(tmp_path,
                agent_msgs=[("assistant", "did the task, nothing notable")],
                main_msgs=[("user", "no, that's wrong, use --tree")])
    _run(monkeypatch, ev)
    assert S.read_subagent_learnings("s1") == []


def test_uses_last_assistant_message_when_present(tmp_path, monkeypatch):
    # The event hands us the subagent's final text for free - a zero-cost signal source.
    ev = _event(tmp_path, agent_msgs=[("user", "go")],
                final="it turns out the flag is --check-tree, not --check")
    _run(monkeypatch, ev)
    got = S.read_subagent_learnings("s1")
    assert len(got) == 1 and "check-tree" in got[0]["snippet"]


def test_final_message_does_not_duplicate_the_same_finding(tmp_path, monkeypatch):
    # last_assistant_message is normally the SAME text as the transcript's last assistant message
    # (often a substring of it). One finding must buffer ONCE, not twice.
    ev = _event(tmp_path,
                agent_msgs=[("assistant", "I was wrong earlier - it turns out the flag is --check-tree")],
                final="it turns out the flag is --check-tree")
    _run(monkeypatch, ev)
    got = S.read_subagent_learnings("s1")
    assert len(got) == 1, "near-duplicate finding buffered twice: %r" % [g["snippet"] for g in got]


def test_no_signal_buffers_nothing(tmp_path, monkeypatch):
    ev = _event(tmp_path, agent_msgs=[("assistant", "Listed the files as requested.")], final="done")
    _run(monkeypatch, ev)
    assert S.read_subagent_learnings("s1") == []


def test_never_blocks_or_wedges(tmp_path, monkeypatch, capsys):
    ev = _event(tmp_path, agent_msgs=[("assistant", "I was wrong about that")])
    assert _run(monkeypatch, ev) == 0
    assert capsys.readouterr().out.strip() == ""          # never emits a decision
    monkeypatch.setattr("sys.stdin", io.StringIO("garbage"))
    assert C.main() == 0
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"session_id": "sX"})))
    assert C.main() == 0                                   # missing agent_transcript_path -> no crash


def test_no_session_id_is_a_noop(tmp_path, monkeypatch):
    ev = _event(tmp_path, agent_msgs=[("assistant", "I was wrong")], session="")
    assert _run(monkeypatch, ev) == 0
