"""Tests for stamp-clock-nudge.py: a new HH:MM in a durable record is checked against the clock."""

import datetime
import json
import os

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


@pytest.mark.parametrize("path", ["/r/handover.md", "/s/handover-topic.md", "/h/wt-x-handover.md"])
def test_a_checkpoint_stamp_is_fixed_with_the_edit_tool_after_reading_the_clock(path):
    """Measured: 23 of 25 checkpoints that resumed as "unattributed" had been re-stamped with
    `sed -i` right after this nudge, which told the session to stamp "from `date` in the same
    command". The compaction resume attributes a checkpoint by this session's Write/Edit calls, so
    for a checkpoint the nudge must say: read `date`, then fix the stamp with the Edit tool."""
    text = _assess(_edit(path, "# Checkpoint 2026-11-09 17:55"))
    assert "17:55" in text and "17:44" in text
    assert "`date`" in text and "Edit tool" in text
    assert "same command" not in text
    assert "sed" in text, "the shell edit to avoid is named, so it is not the reflex fix"


def test_a_backlog_stamp_keeps_the_same_command_advice():
    text = _assess(_edit("/r/OPEN-WORK.md", "ran at 17:55 today"))
    assert "same command" in text and "Edit tool" not in text


def test_main_is_silent_on_junk_and_quiet_events():
    assert N.main("not json") == 0
    assert N.main(json.dumps({"tool_name": "Read"})) == 0


# ---- a Bash write is compared with the record it names, not the one in the cwd -----------------

# A Bash command spells a path the way a user types it under Git Bash, C:/temp/...: unquoted, a
# backslash is an escape there, so C:\temp\x reaches the shell as C:tempx, a different file.
# An unquoted path below goes in through as_posix() for that reason.
def _append(target, stamp="17:30"):
    return "cat >> %s <<'EOF'\n- (2026-11-09 %s) note\nEOF\n" % (target, stamp)


def _bash(cmd, cwd, **kw):
    return N.assess({"tool_name": "Bash", "cwd": str(cwd), "tool_input": {"command": cmd}},
                    now_local=NOW, now_utc=UTC, **kw)


@pytest.fixture
def two_records(tmp_path):
    """A cwd whose OPEN-WORK.md already holds 17:30, and another dir whose record does not."""
    here, there = tmp_path / "here", tmp_path / "there"
    here.mkdir()
    there.mkdir()
    (here / "OPEN-WORK.md").write_text("- (2026-11-09 17:30) old\n", encoding="utf-8")
    (there / "OPEN-WORK.md").write_text("- nothing stamped\n", encoding="utf-8")
    return here, there


@pytest.mark.parametrize("form", ["cat >> {p} <<'EOF'", "cat >>{p} <<'EOF'", "tee -a {p} <<'EOF'"])
def test_an_append_to_another_dirs_record_reads_that_record(two_records, form):
    """The stamp is new in the record the command writes; the cwd's record already holding it
    made the nudge stay silent."""
    here, there = two_records
    cmd = form.format(p=(there / "OPEN-WORK.md").as_posix()) + "\n- (2026-11-09 17:30) note\nEOF\n"
    text = _bash(cmd, here)
    assert text is not None and "17:30" in text and "OPEN-WORK.md" in text


def test_a_stamp_already_in_the_named_record_is_not_new_whatever_the_cwd(two_records):
    """The other direction: the named record holds the stamp, the cwd's does not."""
    here, there = two_records
    assert _bash(_append((here / "OPEN-WORK.md").as_posix()), there) is None


def test_a_quoted_record_path_with_a_space_is_read_whole(tmp_path):
    spaced = tmp_path / "a b"
    spaced.mkdir()
    (spaced / "handover.md").write_text("at 17:30\n", encoding="utf-8")
    assert _bash(_append('"%s"' % (spaced / "handover.md")), tmp_path) is None


@pytest.mark.skipif(os.name == "nt", reason="needs a host where C:/... is a relative path")
def test_a_git_bash_drive_path_is_read_as_that_drive_on_a_windows_host(tmp_path, monkeypatch):
    """`/c/...` is drive C under Git Bash: the record read is `C:/w/OPEN-WORK.md`, and off
    Windows `/c/w/OPEN-WORK.md` itself. On a POSIX host `C:/w/...` is a relative path, so a record
    planted at `<cwd>/C:/w/` shows which of the two was read."""
    planted = tmp_path / "C:" / "w"
    planted.mkdir(parents=True)
    (planted / "OPEN-WORK.md").write_text("at 17:30\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    cmd = _append("/c/w/OPEN-WORK.md")
    assert _bash(cmd, tmp_path, os_name="nt") is None             # read C:/w/: holds the stamp
    assert "17:30" in _bash(cmd, tmp_path, os_name="posix")         # /c/w/ does not exist here


def test_a_git_bash_mount_is_read_as_no_record_on_a_windows_host(two_records):
    """`/tmp/...` under Git Bash lands where only its mount table says; it is never read from
    this host's /tmp. The drive is cut off on a Windows host, so the path is rooted but names no
    drive there either: the record exists on this host and must still go unread."""
    here, _there = two_records
    rooted = (here / "OPEN-WORK.md").as_posix()[len(here.drive):]
    assert "17:30" in _bash(_append(rooted), here, os_name="nt")
