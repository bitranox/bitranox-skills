"""session-review --prose: the readable view of a large unreviewed stretch. ASCII only.

A raw part is up to 2 MB of JSONL, mostly thinking signatures, usage blocks, tool output and
system reminders; the learnings sit in the user and assistant text. The prose view keeps that text
(plus failed tool results), and reads a much larger window per part, so a multi-MB stretch is one
review instead of a loop of raw parts. session-reviewed --prose marks the same window it showed.
"""
import json

import pytest

import dream_state as D


@pytest.fixture
def home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    (h / ".claude").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


def _rec(obj):
    return json.dumps(obj) + "\n"


USER = _rec({"type": "user", "message": {"role": "user", "content": "please fix the --check flag"}})
META = _rec({"type": "user", "isMeta": True,
             "message": {"content": [{"type": "text", "text": "SKILL-BODY-TEXT"}]}})
SKILL_BODY = _rec({"type": "user", "message": {"content": [
    {"type": "text", "text": "Base directory for this skill: /x\n\nSKILL-BODY-2"}]}})
ASSISTANT = _rec({"type": "assistant", "message": {"content": [
    {"type": "thinking", "thinking": "THINKING-TEXT", "signature": "SIG" * 50},
    {"type": "text", "text": "The flag was misnamed; renaming it."},
    {"type": "tool_use", "name": "Bash", "input": {"command": "TOOL-INPUT"}}],
    "usage": {"input_tokens": 12345}}})
TOOL_OK = _rec({"type": "user", "message": {"content": [
    {"type": "tool_result", "content": "TOOL-OUTPUT-OK", "is_error": False}]}})
TOOL_ERR = _rec({"type": "user", "message": {"content": [
    {"type": "tool_result", "content": [{"type": "text", "text": "Exit code 2 boom"}],
     "is_error": True}]}})
REMINDER = _rec({"type": "user", "message": {"content":
    "real prompt words<system-reminder>REMINDER-TEXT</system-reminder>"}})
ATTACH = _rec({"type": "attachment", "attachment": {"type": "skill_listing", "content": "LISTING"}})


def test_prose_view_keeps_user_and_assistant_text_and_failed_tool_results():
    out = D.prose_view(USER + META + SKILL_BODY + ASSISTANT + TOOL_OK + TOOL_ERR + ATTACH)
    assert "please fix the --check flag" in out
    assert "The flag was misnamed; renaming it." in out
    assert "Exit code 2 boom" in out
    for dropped in ("SKILL-BODY-TEXT", "SKILL-BODY-2", "THINKING-TEXT", "SIGSIG", "TOOL-INPUT",
                    "TOOL-OUTPUT-OK", "12345", "LISTING"):
        assert dropped not in out, dropped


def test_prose_view_strips_system_reminders_but_keeps_the_prompt_around_them():
    out = D.prose_view(REMINDER)
    assert "real prompt words" in out and "REMINDER-TEXT" not in out


def test_prose_view_truncates_one_long_record_and_says_so():
    long_rec = _rec({"type": "assistant", "message": {"content": [
        {"type": "text", "text": "A" * (D.PROSE_RECORD_CHARS + 500)}]}})
    out = D.prose_view(long_rec)
    assert "A" * D.PROSE_RECORD_CHARS in out and "A" * (D.PROSE_RECORD_CHARS + 1) not in out
    assert "500 more chars" in out


def test_prose_view_skips_a_line_that_is_not_json():
    assert "half" not in D.prose_view('{"type": "user", "half\n' + USER)


def _session(home, proj, tmp_path, text):
    tp = tmp_path / "sess.jsonl"
    tp.write_bytes(text.encode("utf-8"))
    D.sig.record_session_meta(proj, "sid1", str(tp))
    return tp


def test_session_review_prose_prints_the_prose_not_the_raw_records(home, tmp_path, capsys):
    _session(home, "/p/x", tmp_path, USER + ASSISTANT + TOOL_OK)
    assert D.main(["session-review", "--prose", "/p/x"]) == 0
    out = capsys.readouterr().out
    assert "The flag was misnamed" in out and "PROSE VIEW" in out
    assert "SIGSIG" not in out and '"type": "assistant"' not in out


def test_a_prose_part_spans_many_raw_parts_and_reviewed_marks_exactly_it(home, tmp_path, capsys,
                                                                        monkeypatch):
    filler = _rec({"type": "user", "message": {"content": [
        {"type": "tool_result", "content": "f" * 900, "is_error": False}]}})
    late = _rec({"type": "user", "message": {"content": "LATE-MARKER"}})
    tp = _session(home, "/p/x", tmp_path, USER + filler * 40 + late)
    monkeypatch.setattr(D, "REVIEW_CHUNK_BYTES", 2_000)       # raw: ~20 parts
    assert D.main(["session-review", "--prose", "/p/x"]) == 0
    out = capsys.readouterr().out
    assert "LATE-MARKER" in out and "TRUNCATED" not in out
    assert D.main(["session-reviewed", "--prose", "/p/x"]) == 0
    assert D.sig.get_watermark("/p/x", str(tp), "dream") == tp.stat().st_size
    assert D.main(["session-review", "--prose", "/p/x"]) == 1


def test_a_prose_window_over_its_bound_is_truncated_and_marked_only_that_far(home, tmp_path,
                                                                           capsys, monkeypatch):
    tp = _session(home, "/p/x", tmp_path, USER * 10)
    monkeypatch.setattr(D, "PROSE_CHUNK_BYTES", len(USER) * 3)
    assert D.main(["session-review", "--prose", "/p/x"]) == 0
    assert "TRUNCATED" in capsys.readouterr().out
    assert D.main(["session-reviewed", "--prose", "/p/x"]) == 0
    assert D.sig.get_watermark("/p/x", str(tp), "dream") == len(USER) * 3


def test_control_reviewed_without_prose_advances_only_one_raw_part(home, tmp_path, monkeypatch):
    tp = _session(home, "/p/x", tmp_path, USER * 10)
    monkeypatch.setattr(D, "REVIEW_CHUNK_BYTES", len(USER) * 2)
    assert D.main(["session-reviewed", "/p/x"]) == 0
    assert D.sig.get_watermark("/p/x", str(tp), "dream") == len(USER) * 2


@pytest.mark.parametrize("argv", [["due", "--prose"], ["session-review", "--prose",
                                                       "--structured-only", "/p/x"]])
def test_prose_is_refused_where_it_means_nothing(home, argv, capsys):
    assert D.main(argv) == 2
    assert "usage" in capsys.readouterr().err


def test_a_prose_mark_after_a_plain_review_stops_where_the_plain_review_stopped(home, tmp_path,
                                                                               capsys, monkeypatch):
    # The mark must not discharge text the review never showed: a raw review that showed one part
    # followed by a --prose mark (a far wider window) once advanced past everything unread.
    tp = _session(home, "/p/x", tmp_path, USER * 10)
    monkeypatch.setattr(D, "REVIEW_CHUNK_BYTES", len(USER) * 2)
    assert D.main(["session-review", "/p/x"]) == 0
    assert "TRUNCATED" in capsys.readouterr().out
    assert D.main(["session-reviewed", "--prose", "/p/x"]) == 0
    assert D.sig.get_watermark("/p/x", str(tp), "dream") == len(USER) * 2


def test_a_plain_mark_after_a_prose_review_still_marks_only_one_raw_part(home, tmp_path, capsys,
                                                                        monkeypatch):
    tp = _session(home, "/p/x", tmp_path, USER * 10)
    monkeypatch.setattr(D, "REVIEW_CHUNK_BYTES", len(USER) * 2)
    assert D.main(["session-review", "--prose", "/p/x"]) == 0
    capsys.readouterr()
    assert D.main(["session-reviewed", "/p/x"]) == 0
    assert D.sig.get_watermark("/p/x", str(tp), "dream") == len(USER) * 2


def test_the_cap_holds_after_a_replaced_transcript_reset_the_watermark(home, tmp_path, capsys,
                                                                      monkeypatch):
    # A watermark past the end of a replaced file reads as 0, so the cap must be judged against
    # the part the review showed, not against the stored mark.
    tp = _session(home, "/p/x", tmp_path, USER * 10)
    D.sig.set_watermark("/p/x", str(tp), "dream", 50_000_000)
    monkeypatch.setattr(D, "REVIEW_CHUNK_BYTES", len(USER) * 2)
    assert D.main(["session-review", "/p/x"]) == 0
    capsys.readouterr()
    assert D.main(["session-reviewed", "--prose", "/p/x"]) == 0
    assert D.sig.get_watermark("/p/x", str(tp), "dream") == len(USER) * 2
