"""Tests for session-review --structured-only (F3): suppress the raw transcript dump. ASCII only."""
import dream_state as D


def test_render_structured_only_suppresses_raw_transcript():
    text = "HUGE RAW TRANSCRIPT LINE\n" * 50
    out = D._render_review([{"agent_type": "gp", "snippet": "learned X"}], [], {"toolbox": 1},
                           text, 500, "/p", structured_only=True)
    assert "SUBAGENT LEARNINGS" in out and "learned X" in out      # structured blocks kept
    assert "SKILLS INVOKED" in out and "toolbox x1" in out
    assert "HUGE RAW TRANSCRIPT LINE" not in out                   # raw body suppressed
    assert "suppressed by --structured-only" in out
    assert "bytes up to offset 500" in out                         # the byte-count header stays


def test_render_default_includes_raw_transcript():
    out = D._render_review([], [], {}, "RAWLINE\n", 10, "/p", structured_only=False)
    assert "RAWLINE" in out
    assert "suppressed" not in out
