"""Tests for newest.py - pick the latest timestamped path by MTIME, never by name sort."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

import newest as N

TOOL = Path(__file__).resolve().parents[1] / "scripts" / "newest.py"


def _touch(path, mtime):
    """Write a file and set its mtime EXPLICITLY - never rely on creation order for timing.

    Filesystem mtime resolution differs by OS (as coarse as 2s on some setups), so two files
    created back to back can land on the SAME mtime; a test that depends on creation order to
    separate them is flaky exactly when it matters most.
    """
    path.write_text("x", encoding="utf-8")
    os.utime(path, (mtime, mtime))


# --- pure comparison logic --------------------------------------------------------------------

def test_the_name_sort_trap_is_the_whole_point(tmp_path):
    """A longer name sharing the prefix sorts AFTER a shorter one, so an extra word beats the date."""
    old_but_longer = tmp_path / "nightly-snapshot-with-extra-notes-20260708"
    new_but_shorter = tmp_path / "nightly-snapshot-20260804"
    _touch(old_but_longer, time.time() - 10_000)
    _touch(new_but_shorter, time.time())

    by_name = sorted(p.name for p in tmp_path.iterdir())[-1]
    assert by_name == "nightly-snapshot-with-extra-notes-20260708", (
        "the trap must be reproduced, or this proves nothing")
    assert N.newest([str(p) for p in tmp_path.iterdir()]).name == "nightly-snapshot-20260804"


def test_newest_of_an_empty_set_is_none():
    assert N.newest([]) is None


def test_ordering_is_newest_first(tmp_path):
    a, b, c = (tmp_path / n for n in ("a", "b", "c"))
    _touch(a, 100.0)
    _touch(b, 300.0)
    _touch(c, 200.0)
    ordered = [p.name for p in N.by_mtime([str(a), str(b), str(c)])]
    assert ordered == ["b", "c", "a"]


def test_a_tie_in_mtime_breaks_by_input_order_not_by_chance(tmp_path):
    """Equal mtimes happen (coarse filesystem resolution) - the tie-break must be deterministic."""
    a = tmp_path / "a"
    b = tmp_path / "b"
    tie = time.time()
    _touch(a, tie)
    _touch(b, tie)
    assert N.newest([str(a), str(b)]).name == "a"
    assert N.newest([str(b), str(a)]).name == "b"


def test_a_missing_path_is_skipped_not_a_crash(tmp_path):
    real = tmp_path / "real"
    _touch(real, 100.0)
    assert N.newest([str(real), str(tmp_path / "gone")]).name == "real"


def test_unreadable_reports_exactly_the_paths_that_could_not_be_stat_d(tmp_path):
    real = tmp_path / "real"
    _touch(real, 100.0)
    gone = str(tmp_path / "gone")
    assert N.unreadable([str(real), gone]) == [gone]
    assert N.unreadable([str(real)]) == []


def test_directories_count_too(tmp_path):
    """Backups and worktrees are DIRS - a file-only tool would miss the whole use case."""
    d = tmp_path / "snap-2"
    d.mkdir()
    os.utime(d, (500.0, 500.0))
    f = tmp_path / "snap-1"
    _touch(f, 100.0)
    assert N.newest([str(d), str(f)]).name == "snap-2"


def test_age_seconds_is_reported_so_a_stale_pick_is_visible(tmp_path):
    """Picking the newest of a stale set still gives a stale answer - print the age."""
    p = tmp_path / "old"
    _touch(p, time.time() - 3600)
    age = N.age_seconds(p)
    assert 3500 < age < 3700


def test_age_seconds_of_an_unreadable_path_is_infinite(tmp_path):
    assert N.age_seconds(tmp_path / "gone") == float("inf")


# --- CLI contract: exit codes, JSON envelope, stderr-only diagnostics --------------------------

def _run(args):
    return subprocess.run([sys.executable, str(TOOL), *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def test_no_paths_is_a_usage_error_not_a_traceback():
    r = _run([])
    assert r.returncode == 2
    assert "no paths" in r.stderr
    assert "Traceback" not in r.stderr


def test_nothing_readable_is_exit_1(tmp_path):
    r = _run([str(tmp_path / "gone-a"), str(tmp_path / "gone-b")])
    assert r.returncode == 1
    assert "nothing readable" in r.stderr


def test_picks_the_mtime_winner_over_the_earlier_name_sort_winner(tmp_path):
    """End to end through the real CLI: the same trap as the pure-logic test, via subprocess."""
    old_but_longer = tmp_path / "nightly-snapshot-with-extra-notes-20260708"
    new_but_shorter = tmp_path / "nightly-snapshot-20260804"
    _touch(old_but_longer, time.time() - 10_000)
    _touch(new_but_shorter, time.time())

    r = _run([str(old_but_longer), str(new_but_shorter)])
    assert r.returncode == 0
    assert "nightly-snapshot-20260804" in r.stdout
    assert "nightly-snapshot-with-extra-notes-20260708" not in r.stdout


def test_all_lists_every_match_newest_first(tmp_path):
    a = tmp_path / "a"
    b = tmp_path / "b"
    _touch(a, 100.0)
    _touch(b, 300.0)
    r = _run(["--all", str(a), str(b)])
    assert r.returncode == 0
    lines = [ln for ln in r.stdout.splitlines() if ln.strip()]
    assert len(lines) == 2
    assert lines[0].startswith(str(b))
    assert lines[1].startswith(str(a))


def test_json_envelope_is_the_documented_shape(tmp_path):
    p = tmp_path / "only"
    _touch(p, 100.0)
    r = _run(["--json", str(p)])
    assert r.returncode == 0
    payload = json.loads(r.stdout)
    assert payload["ok"] is True
    assert payload["command"] == "newest"
    assert payload["skipped"] == []
    assert payload["data"][0]["path"] == str(p)


def test_skipped_paths_are_warned_on_stderr_and_listed_in_json_not_stdout(tmp_path):
    """A diagnostic must not corrupt --json stdout, even when some paths were unreadable."""
    real = tmp_path / "real"
    _touch(real, 100.0)
    gone = str(tmp_path / "gone")
    r = _run(["--json", str(real), gone])
    assert r.returncode == 0
    payload = json.loads(r.stdout)  # must still parse even though a diagnostic was emitted
    assert payload["skipped"] == [gone]
    assert "skipped 1 unreadable" in r.stderr


# --------------------------------------------------------------------------
# --name-timestamp: mtime is the WRONG key when a later pass rewrote the files.
# --------------------------------------------------------------------------


def test_parse_name_stamp_reads_the_common_fixed_width_forms():
    assert N.parse_name_stamp("samples-20260823T173409Z.jsonl.gz") is not None
    assert N.parse_name_stamp("dump-20260823-173409.sql") is not None
    assert N.parse_name_stamp("dump_20260823_173409.sql") is not None
    assert N.parse_name_stamp("backup-20260823.tar") is not None


def test_parse_name_stamp_orders_correctly():
    earlier = N.parse_name_stamp("s-20260823T090000Z.gz")
    later = N.parse_name_stamp("s-20260823T173409Z.gz")
    assert earlier < later


def test_parse_name_stamp_rejects_a_non_date():
    """13 is not a month. A number of the right WIDTH is not a timestamp."""
    assert N.parse_name_stamp("build-20261345.log") is None
    assert N.parse_name_stamp("v1.2.3-release.tar") is None


def test_by_name_stamp_ignores_mtime_entirely(tmp_path):
    """The whole point: the file rewritten LAST is not the one produced last."""
    old_content = tmp_path / "samples-20260823T173409Z.jsonl.gz"
    new_content = tmp_path / "samples-20260824T090000Z.jsonl.gz"
    new_content.write_text("newer content", encoding="utf-8")
    old_content.write_text("older content", encoding="utf-8")
    # gzipped afterwards: the OLDER content carries the LATER mtime
    import os
    os.utime(new_content, (1000, 1000))
    os.utime(old_content, (2000, 2000))

    assert N.newest([str(new_content), str(old_content)]).name == old_content.name
    assert N.newest_by_name_stamp(
        [str(new_content), str(old_content)]).name == new_content.name


def test_unstamped_paths_are_reported_never_guessed(tmp_path):
    a = tmp_path / "samples-20260824T090000Z.gz"
    b = tmp_path / "no-stamp-here.gz"
    for f in (a, b):
        f.write_text("x", encoding="utf-8")
    assert N.unstamped([str(a), str(b)]) == [str(b)]


def test_keys_disagree_is_the_warning_condition(tmp_path):
    """No threshold: the key matters exactly when the two keys pick different files."""
    import os
    old_content = tmp_path / "s-20260823T173409Z.gz"
    new_content = tmp_path / "s-20260824T090000Z.gz"
    for f in (new_content, old_content):
        f.write_text("x", encoding="utf-8")
    os.utime(new_content, (1000, 1000))
    os.utime(old_content, (2000, 2000))
    assert N.keys_disagree([str(new_content), str(old_content)]) is True

    # and the control: when the two keys agree, no warning
    os.utime(new_content, (3000, 3000))
    assert N.keys_disagree([str(new_content), str(old_content)]) is False


def test_cli_warns_when_the_keys_disagree(tmp_path):
    import os
    old_content = tmp_path / "s-20260823T173409Z.gz"
    new_content = tmp_path / "s-20260824T090000Z.gz"
    for f in (new_content, old_content):
        f.write_text("x", encoding="utf-8")
    os.utime(new_content, (1000, 1000))
    os.utime(old_content, (2000, 2000))
    proc = subprocess.run(
        [sys.executable, str(TOOL), str(new_content), str(old_content)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    assert proc.returncode == 0
    assert "--name-timestamp" in proc.stderr, proc.stderr


def test_cli_name_timestamp_selects_by_the_name(tmp_path):
    import os
    old_content = tmp_path / "s-20260823T173409Z.gz"
    new_content = tmp_path / "s-20260824T090000Z.gz"
    for f in (new_content, old_content):
        f.write_text("x", encoding="utf-8")
    os.utime(new_content, (1000, 1000))
    os.utime(old_content, (2000, 2000))
    proc = subprocess.run(
        [sys.executable, str(TOOL), "--name-timestamp", str(new_content), str(old_content)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    assert proc.returncode == 0
    assert new_content.name in proc.stdout
    assert old_content.name not in proc.stdout


def test_cli_name_timestamp_refuses_when_nothing_is_stamped(tmp_path):
    """Falling back to mtime silently would be the same defect this flag exists to fix."""
    f = tmp_path / "plain.gz"
    f.write_text("x", encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(TOOL), "--name-timestamp", str(f)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    assert proc.returncode == 1, (proc.returncode, proc.stdout, proc.stderr)
    assert "stamp" in proc.stderr.lower()


# --------------------------------------------------------------------------
# --name-timestamp must not borrow the mtime for its age, nor pick a path that is gone
# --------------------------------------------------------------------------

def _strict_json(text):
    """json.loads that refuses Infinity/NaN, the way every non-Python parser does."""
    def refuse(token):
        raise ValueError(f"non-strict JSON constant {token}")
    return json.loads(text, parse_constant=refuse)


def test_name_timestamp_age_comes_from_the_stamp_not_the_mtime(tmp_path):
    """A rewrite pass (compression) refreshes mtime. Reporting that as the age makes a stale set
    look fresh, and the age is the documented stale detector."""
    f = tmp_path / "s-20260102T000000Z.gz"
    _touch(f, time.time())                                   # rewritten just now
    stamp = N.parse_name_stamp(f.name)
    r = _run(["--name-timestamp", "--json", str(f)])
    assert r.returncode == 0, r.stderr
    item = _strict_json(r.stdout)["data"][0]
    assert abs(item["age_seconds"] - (time.time() - stamp)) < 120
    assert item["age_basis"] == "name_stamp"
    text = _run(["--name-timestamp", str(f)]).stdout
    assert "name stamp" in text


def test_default_mode_age_is_still_the_mtime(tmp_path):
    f = tmp_path / "s-20260102T000000Z.gz"
    _touch(f, time.time() - 3600)
    item = _strict_json(_run(["--json", str(f)]).stdout)["data"][0]
    assert 3500 < item["age_seconds"] < 3700
    assert item["age_basis"] == "mtime"


def test_name_timestamp_skips_a_path_that_is_gone(tmp_path):
    """A dangling stamped symlink, or a file deleted after the glob, must not be the answer -
    and the envelope must stay strict JSON (no Infinity)."""
    real = tmp_path / "s-20260101T000000Z.gz"
    _touch(real, 100.0)
    gone = str(tmp_path / "gone-20260901.gz")
    r = _run(["--name-timestamp", "--json", str(real), gone])
    assert r.returncode == 0, r.stderr
    env = _strict_json(r.stdout)
    assert [d["path"] for d in env["data"]] == [str(real)]
    assert gone in env["skipped"]
    assert "unreadable" in r.stderr


def test_name_timestamp_with_every_stamped_path_gone_is_no_match(tmp_path):
    r = _run(["--name-timestamp", str(tmp_path / "gone-20260901.gz")])
    assert r.returncode == 1
    assert "Infinity" not in r.stdout


def test_every_stamped_path_gone_is_not_reported_as_no_stamp(tmp_path):
    """The stamp parsed fine; the path is what is missing. Saying 'no parseable stamp' sends the
    reader to fix a naming scheme that is correct."""
    r = _run(["--name-timestamp", str(tmp_path / "gone-20260901.gz")])
    assert r.returncode == 1
    assert "no path carries a parseable" not in r.stderr, r.stderr
    assert "none of them could be read" in r.stderr, r.stderr


def test_no_stamp_at_all_still_names_the_stamp_forms(tmp_path):
    f = tmp_path / "plain.gz"
    f.write_text("x", encoding="utf-8")
    r = _run(["--name-timestamp", str(f)])
    assert r.returncode == 1
    assert "no path carries a parseable fixed-width name stamp" in r.stderr, r.stderr


def test_the_disagreement_warning_ignores_a_stamp_winner_that_is_gone(tmp_path):
    real = tmp_path / "s-20260101T000000Z.gz"
    _touch(real, 100.0)
    gone = str(tmp_path / "gone-20260901.gz")
    assert N.keys_disagree([str(real), gone]) is False
    r = _run([str(real), gone])
    assert r.returncode == 0
    assert "--name-timestamp" not in r.stderr


def test_the_disagreement_warning_still_fires_when_both_exist(tmp_path):
    """Control for the test above."""
    old_content = tmp_path / "s-20260101T000000Z.gz"
    new_content = tmp_path / "present-20260901.gz"
    _touch(new_content, 1000.0)
    _touch(old_content, 2000.0)
    assert N.keys_disagree([str(old_content), str(new_content)]) is True


# --------------------------------------------------------------------------
# Output that a console cannot encode must not become exit 1 ("no match")
# --------------------------------------------------------------------------

def test_a_non_latin_name_does_not_crash_a_cp1252_console(tmp_path):
    f = tmp_path / "日本-20260101"
    _touch(f, 100.0)
    r = subprocess.run([sys.executable, str(TOOL), str(f)], capture_output=True, check=False,
                       env={**os.environ, "PYTHONIOENCODING": "cp1252"})
    assert r.returncode == 0, r.stderr
    assert b"Traceback" not in r.stderr
    assert b"20260101" in r.stdout


@pytest.mark.skipif(sys.platform != "linux",
                    reason="only Linux filesystems accept a filename that is not valid UTF-8")
def test_a_filename_that_is_not_utf8_does_not_crash_text_output(tmp_path):
    raw = os.fsencode(str(tmp_path)) + b"/bad-\xff-20260101"
    fd = os.open(raw, os.O_CREAT | os.O_WRONLY, 0o644)
    os.close(fd)
    r = subprocess.run([sys.executable, str(TOOL), raw], capture_output=True, check=False,
                       env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    assert r.returncode == 0, r.stderr
    assert b"Traceback" not in r.stderr
    assert b"20260101" in r.stdout


# --------------------------------------------------------------------------
# A glob the shell did not expand (cmd.exe, PowerShell, a quoted argument)
# --------------------------------------------------------------------------

def test_an_unexpanded_glob_is_expanded_here(tmp_path):
    older = tmp_path / "s-1"
    newer = tmp_path / "s-2"
    _touch(older, 100.0)
    _touch(newer, 200.0)
    r = subprocess.run([sys.executable, str(TOOL), "s-*"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", cwd=str(tmp_path), check=False)
    assert r.returncode == 0, r.stderr
    assert r.stdout.startswith("s-2")


def test_a_glob_that_matches_nothing_is_still_no_match(tmp_path):
    r = subprocess.run([sys.executable, str(TOOL), "nothing-*"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", cwd=str(tmp_path), check=False)
    assert r.returncode == 1
    assert "nothing-*" in r.stderr


def test_an_existing_name_with_brackets_is_taken_literally(tmp_path):
    literal = tmp_path / "snap[1]"
    _touch(literal, 100.0)
    decoy = tmp_path / "snap1"
    _touch(decoy, 900.0)
    assert N.expand_args([str(literal)]) == [str(literal)]


# --------------------------------------------------------------------------
# The docstring says the FIRST stamp wins; so must the code
# --------------------------------------------------------------------------

def test_the_leftmost_stamp_wins_whatever_its_width():
    first = N.parse_name_stamp("db-20250101-restored-from-20240101-120000.sql")
    assert first == N.parse_name_stamp("x-20250101.sql")


def test_a_single_stamp_still_parses_at_full_width():
    """Control: at the same position the 14-digit form beats its own 8-digit prefix."""
    assert N.parse_name_stamp("x-20240101-120000.sql") \
        == N.parse_name_stamp("x-20240101T120000Z.sql") != N.parse_name_stamp("x-20240101.sql")


# --------------------------------------------------------------------------
# The age text itself
# --------------------------------------------------------------------------

@pytest.mark.parametrize("seconds, text", [
    (0, "0s"), (59, "59s"), (60, "1.0m"), (3599, "60.0m"), (3600, "1.0h"),
    (86399, "24.0h"), (86400, "1.0d"), (90 * 86400, "90.0d"), (float("inf"), "unknown"),
])
def test_human_age_thresholds(seconds, text):
    assert N._human_age(seconds) == text
