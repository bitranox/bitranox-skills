"""Tests for post-compact-nudge.py (PostCompact hook). ASCII only.

PostCompact has no decision control and no context channel: Claude Code discards a PostCompact
hook's JSON fields, writes its stdout to the debug log, and shows exit-0 stderr to nobody
(code.claude.com/docs/en/hooks.md: "PostCompact - None - No decision control. Used for side
effects"). So this hook is a side effect only - it records that a nap is owed - and the tests below
pin both halves of that: it writes the obligation, and it no longer consumes the salvaged audit that
SessionStart (source "compact"), a channel that DOES deliver context, is there to surface.
"""
import io
import json
import os
import runpy
import sys
from pathlib import Path

import pytest

import post_compact_nudge as H
import self_improve_gate as GATE
import session_start as START
import self_improve_signals as SIG

SCRIPT = Path(__file__).resolve().parent.parent / "post-compact-nudge.py"


@pytest.fixture(autouse=True)
def isolate_home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    (h / ".claude").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    return h


def run(monkeypatch, cwd="/proj/x", **extra):
    event = {"cwd": cwd}
    event.update(extra)
    return run_raw(monkeypatch, json.dumps(event))


def run_raw(monkeypatch, stdin_text):
    monkeypatch.setattr(sys, "stdin", io.StringIO(stdin_text))
    return H.main()


def seed_audit(proj="/proj/x", text="salvaged thing"):
    af = SIG.audit_file(proj)
    af.parent.mkdir(parents=True, exist_ok=True)
    af.write_text("<SELF-IMPROVE-AUDIT>\n%s\n</SELF-IMPROVE-AUDIT>\n" % text, encoding="utf-8")
    return af


def test_writes_nothing_a_postcompact_hook_cannot_deliver(monkeypatch, capsys):
    """additionalContext on PostCompact is discarded, so printing it only ever reached the debug
    log while reading as a working nudge."""
    assert run(monkeypatch) == 0
    captured = capsys.readouterr()
    assert (captured.out, captured.err) == ("", "")


def test_records_which_session_and_transcript_compacted(monkeypatch, isolate_home):
    # The flag alone cannot say WHICH transcript holds the pre-compaction stretch, so a nap in a
    # later session clears an obligation it never read. PostCompact has both in its event.
    run(monkeypatch, "/proj/x", session_id="sid-old", transcript_path="/t/old.jsonl")
    info = SIG.nap_owed_info("/proj/x")
    assert info.get("session_id") == "sid-old"
    assert info.get("transcript_path") == "/t/old.jsonl"


def test_records_that_a_nap_is_owed(monkeypatch, isolate_home):
    # A hook cannot RUN the nap (no model in a hook). It records the obligation; the Stop gate
    # enforces it. Without this the nudge is skippable and the compaction stretch is lost.
    assert SIG.is_nap_owed("/proj/x") is False
    run(monkeypatch, "/proj/x")
    assert SIG.is_nap_owed("/proj/x") is True


def test_the_obligation_reaches_the_model_through_the_stop_gate(monkeypatch):
    """Where the nudge text actually lands: the Stop gate's block, which a Stop hook CAN deliver.
    It is the text this hook used to print, so nothing was lost by not printing it here."""
    run(monkeypatch, "/proj/x", session_id="sid-1", transcript_path="/t/1.jsonl")
    hint = GATE._nap_owed_hint("/proj/x", "sid-1")
    assert "meta-dream-nap" in hint
    assert "DISK" in hint and "not from what you still remember" in hint


def test_leaves_the_salvaged_audit_for_session_start(monkeypatch):
    """The unlink deleted the file SessionStart(compact) would have delivered, after folding it into
    a string PostCompact discards - so the salvage was lost on every compaction."""
    af = seed_audit()
    run(monkeypatch, "/proj/x")
    assert af.is_file(), "PostCompact must not consume what it cannot deliver"
    delivered = START.audit_context("/proj/x")
    assert delivered and "salvaged thing" in delivered
    assert not af.is_file(), "the working consumer still consumes it once"


@pytest.mark.parametrize("stdin_text", ["[]", "null", "7", '"text"', "not json at all", ""])
def test_any_unusable_stdin_still_records_the_nap(monkeypatch, tmp_path, stdin_text):
    """A JSON value that is not an object defeated the fallback: `.get` raised, the catch-all
    swallowed it, and the nap was never recorded. Every unusable stdin now falls back the same way."""
    proj = str(tmp_path / "proj-fallback")
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", proj)
    assert run_raw(monkeypatch, stdin_text) == 0
    assert SIG.is_nap_owed(proj) is True


def test_an_unwritable_audit_dir_exits_zero(monkeypatch, isolate_home):
    """A real failure to record: a FILE where the audit dir should be."""
    audit_dir = SIG.nap_owed_file("/proj/x").parent
    audit_dir.write_text("not a directory\n", encoding="utf-8")
    assert run(monkeypatch, "/proj/x") == 0
    assert SIG.is_nap_owed("/proj/x") is False


def test_a_recorder_that_raises_does_not_wedge_the_turn(monkeypatch):
    """The catch-all around the recorder, for anything it does not already swallow itself."""
    def boom(*_a, **_k):
        raise RuntimeError("recorder broke")
    monkeypatch.setattr(H, "mark_nap_owed", boom)
    assert run(monkeypatch, "/proj/x") == 0


def test_the_script_exits_zero_when_main_itself_raises(monkeypatch):
    """The __main__ guard: with no cwd in the event and no CLAUDE_PROJECT_DIR, main() falls back to
    os.getcwd(), which is made to fail here (a deleted working directory fails the same way)."""
    def gone():
        raise FileNotFoundError("cwd was deleted")
    monkeypatch.setattr(sys, "stdin", io.StringIO("{}"))
    monkeypatch.setattr(os, "getcwd", gone)
    with pytest.raises(SystemExit) as exc:
        runpy.run_path(str(SCRIPT), run_name="__main__")
    assert exc.value.code == 0
