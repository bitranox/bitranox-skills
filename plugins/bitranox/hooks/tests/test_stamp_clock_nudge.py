"""Tests for stamp-clock-nudge.py: a new HH:MM in a durable record is checked against the clock."""

import datetime
import json

import pytest

import stamp_clock_nudge as N

NOW = datetime.datetime(2026, 11, 9, 17, 44)
UTC = datetime.datetime(2026, 11, 9, 16, 44, tzinfo=datetime.timezone.utc)


def _edit(path, new, old="x"):
    return {"tool_name": "Edit", "tool_input": {"file_path": path, "new_string": new, "old_string": old}}


def _assess(event):
    return N.assess(event, now_local=NOW, now_utc=UTC)


def test_a_stamp_far_from_the_clock_is_named_with_the_clock():
    text = _assess(_edit("/r/OPEN-WORK.md", "ran at 17:55 today"))
    assert "17:55" in text and "17:44" in text


@pytest.mark.parametrize("new", [
    "ran at 17:43",                             # within the tolerance
    "ran at 17:44",
])
def test_a_stamp_near_the_clock_passes(new):
    assert _assess(_edit("/r/OPEN-WORK.md", new)) is None


def test_a_future_stamp_fires_even_inside_the_tolerance():
    assert "17:48" in _assess(_edit("/r/handover.md", "done 17:48"))


def test_a_stamp_already_in_the_replaced_text_is_not_new():
    assert _assess(_edit("/r/OPEN-WORK.md", "still 09:00", old="was 09:00")) is None


def test_a_zulu_stamp_is_compared_to_utc():
    assert _assess(_edit("/r/OPEN-WORK.md", "at 16:44Z")) is None
    assert "17:44Z" in _assess(_edit("/r/OPEN-WORK.md", "at 17:44Z"))


def test_a_line_dated_another_day_is_skipped_and_today_is_judged():
    assert _assess(_edit("/r/OPEN-WORK.md", "(2026-11-03 17:55) ran")) is None
    assert "17:55" in _assess(_edit("/r/OPEN-WORK.md", "(2026-11-09 17:55) ran"))


def test_a_time_far_from_the_clock_is_read_as_a_quoted_time_and_skipped():
    assert _assess(_edit("/r/OPEN-WORK.md", "at 01:35 the run ended")) is None


def test_a_file_that_is_no_durable_record_is_ignored():
    assert _assess(_edit("/r/notes.md", "at 03:00")) is None


def test_a_write_subtracts_what_is_on_disk(tmp_path):
    path = tmp_path / "EXECUTION-USER-REVIEW.md"
    path.write_text("old 03:00\n", encoding="utf-8")
    event = {"tool_name": "Write", "tool_input": {"file_path": str(path), "content": "old 03:00\nnew 17:00\n"}}
    assert "17:00" in _assess(event) and "03:00" not in _assess(event).split("clock")[0]


def test_a_heredoc_append_is_read_and_a_clock_read_silences_it():
    cmd = "cat >> OPEN-WORK.md <<'EOF'\n- [ ] (2026-11-09) 17:55 note\nEOF\n"
    assert "17:55" in _assess({"tool_name": "Bash", "cwd": "/r", "tool_input": {"command": cmd}})
    derived = 'T=$(date +%H:%M); ' + cmd
    assert _assess({"tool_name": "Bash", "cwd": "/r", "tool_input": {"command": derived}}) is None


def test_a_python_heredoc_writing_a_record_is_read():
    cmd = "python3 - <<'PY'\nopen('OPEN-WORK.md','a').write('(at 17:55) x')\nPY\n"
    assert "17:55" in _assess({"tool_name": "Bash", "cwd": "/r", "tool_input": {"command": cmd}})


def test_a_bash_command_naming_no_record_is_silent():
    assert _assess({"tool_name": "Bash", "tool_input": {"command": "echo 21:20 > f.txt"}}) is None


def test_main_is_silent_on_junk_and_quiet_events():
    assert N.main("not json") == 0
    assert N.main(json.dumps({"tool_name": "Read"})) == 0
