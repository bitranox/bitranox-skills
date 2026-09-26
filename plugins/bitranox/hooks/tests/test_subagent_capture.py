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


# ---- snippet windowing and dedup (a learning stated late in a long message) ------------------

# ~260 chars of narration that matches no signal pattern, so the learning that follows sits well
# past the snippet cap.
_PREAMBLE = ("Ran the suite on the branch and read every file the task listed, then compared the "
             "output with the recorded run. ") * 3


def test_a_learning_stated_after_the_snippet_cap_is_kept_in_the_snippet(tmp_path, monkeypatch):
    text = _PREAMBLE + "I was wrong earlier: the flag is --check-tree, not --check."
    assert len(_PREAMBLE) > C._SNIPPET
    _run(monkeypatch, _event(tmp_path, agent_msgs=[("assistant", text)]))
    got = S.read_subagent_learnings("s1")
    assert len(got) == 1
    assert "I was wrong earlier" in got[0]["snippet"], got[0]["snippet"]
    assert len(got[0]["snippet"]) <= C._SNIPPET


def test_a_learning_at_the_start_still_opens_the_snippet(tmp_path, monkeypatch):
    # Control: the window must not push an early learning out of its own snippet.
    text = "I was wrong earlier: the flag is --check-tree. " + _PREAMBLE
    _run(monkeypatch, _event(tmp_path, agent_msgs=[("assistant", text)]))
    got = S.read_subagent_learnings("s1")
    assert len(got) == 1 and got[0]["snippet"].startswith("I was wrong earlier")


def test_two_findings_sharing_a_long_opening_are_both_buffered(tmp_path, monkeypatch):
    # Dedup compared the capped snippets, so two different discoveries behind the same long
    # preamble collapsed into one record and the second was lost.
    first = _PREAMBLE + "I was wrong - the real cause is the stale venv."
    second = _PREAMBLE + "I was wrong - the lock file was never regenerated."
    _run(monkeypatch, _event(tmp_path, agent_msgs=[("assistant", first), ("assistant", second)]))
    snippets = [g["snippet"] for g in S.read_subagent_learnings("s1")]
    assert len(snippets) == 2, snippets
    assert any("stale venv" in s for s in snippets) and any("lock file" in s for s in snippets)


# ---- transcript reading: the shapes a real subagent transcript carries ------------------------

def _raw_transcript(tmp_path, lines, name="agent.jsonl"):
    p = tmp_path / name
    p.write_bytes(b"".join(ln.encode("utf-8") + b"\n" for ln in lines))
    return p


def _raw_event(path, final=None):
    ev = {"hook_event_name": "SubagentStop", "session_id": "s1", "agent_id": "a1",
          "agent_type": "general-purpose", "agent_transcript_path": str(path)}
    if final is not None:
        ev["last_assistant_message"] = final
    return ev


def test_a_real_assistant_record_with_a_list_of_blocks_is_scanned(tmp_path, monkeypatch):
    # A real assistant record carries content as a LIST of blocks, not a string. Only the text
    # blocks are the subagent's prose; thinking and tool_use blocks carry no "text" key.
    rec = {"type": "assistant", "message": {"role": "assistant", "content": [
        {"type": "thinking", "thinking": "checking the flags"},
        {"type": "text", "text": "I was wrong - the real cause is the stale venv"},
        {"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": "ls"}}]}}
    path = _raw_transcript(tmp_path, [json.dumps(rec)])
    _run(monkeypatch, _raw_event(path))
    got = S.read_subagent_learnings("s1")
    assert len(got) == 1 and "stale venv" in got[0]["snippet"]


def test_malformed_lines_and_other_record_types_are_skipped_not_fatal(tmp_path, monkeypatch):
    lines = [
        "{not json",
        json.dumps({"type": "system", "message": {"content": "I was wrong about the system prompt"}}),
        json.dumps(["a", "list", "not", "a", "record"]),
        json.dumps({"type": "assistant", "message": {"content": "I was wrong - the real cause is the stale venv"}}),
    ]
    _run(monkeypatch, _raw_event(_raw_transcript(tmp_path, lines)))
    got = S.read_subagent_learnings("s1")
    assert [("stale venv" in g["snippet"]) for g in got] == [True]


def test_a_record_whose_message_is_not_a_dict_does_not_lose_the_scan(tmp_path, monkeypatch):
    # One odd record used to raise AttributeError out of the whole scan, dropping every hit in the
    # transcript AND last_assistant_message along with it.
    lines = [json.dumps({"type": "assistant", "message": "oops-a-string"}),
             json.dumps({"type": "assistant",
                         "message": {"content": "I was wrong - the real cause is the stale venv"}})]
    _run(monkeypatch, _raw_event(_raw_transcript(tmp_path, lines),
                                 final="it turns out the flag is --check-tree"))
    snippets = [g["snippet"] for g in S.read_subagent_learnings("s1")]
    assert len(snippets) == 2, snippets


_FILLER = json.dumps({"type": "user", "message": {"content": "x" * 300}})
_LEARNING = json.dumps({"type": "assistant", "message": {"content": "I was wrong - the real cause is the stale venv"}})


def _tail_capped(tmp_path, monkeypatch, cut_from_learning):
    """Transcript of filler + learning, with the tail cap set so the seek lands
    `cut_from_learning` bytes from the start of the learning record (0 = exactly on it)."""
    path = _raw_transcript(tmp_path, [_FILLER, _LEARNING])
    start = len(_FILLER.encode("utf-8")) + 1
    monkeypatch.setattr(C, "_MAX_BYTES", path.stat().st_size - start - cut_from_learning)
    return [t for _r, t in C._messages(str(path))]


def test_a_tail_cap_landing_exactly_on_a_record_boundary_keeps_that_record(tmp_path, monkeypatch):
    # The seek landed on the first byte of a whole record and readline() threw it away as if it
    # were the partial tail of the line before.
    assert _tail_capped(tmp_path, monkeypatch, 0) == ["I was wrong - the real cause is the stale venv"]


def test_a_tail_cap_landing_before_a_record_drops_only_the_partial_line(tmp_path, monkeypatch):
    # Control: one byte earlier the seek is inside the previous line's newline position - the
    # partial filler tail is dropped, the learning is kept.
    assert _tail_capped(tmp_path, monkeypatch, -1) == ["I was wrong - the real cause is the stale venv"]
    # Landing inside the filler drops the filler's partial tail and keeps the learning.
    assert _tail_capped(tmp_path, monkeypatch, -50) == ["I was wrong - the real cause is the stale venv"]


def test_a_tail_cap_landing_inside_a_record_drops_that_partial_record(tmp_path, monkeypatch):
    # Control for the other direction: a seek one byte INTO the learning record must not parse
    # its truncated remainder.
    assert _tail_capped(tmp_path, monkeypatch, 1) == []
