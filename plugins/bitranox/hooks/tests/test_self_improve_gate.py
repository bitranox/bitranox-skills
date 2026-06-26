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
    """Send the gate's per-project state file into an isolated temp dir."""
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    monkeypatch.setattr("tempfile.gettempdir", lambda: str(state_dir))
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
