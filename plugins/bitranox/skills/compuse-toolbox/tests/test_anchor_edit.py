"""Tests for anchor_edit.py - edit a file at an EXACT anchor, or refuse.

Every refusal here corresponds to a measured incident. Python's no-match branches are
success-shaped: `str.replace` is a silent no-op, `str.partition` puts everything in the head,
and `str.find` returns -1, which then indexes from the END of the string. So the failure mode
of a hand-rolled anchor edit is not a crash, it is a file that looks edited and is not, or one
edited somewhere else entirely.
"""
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

import anchor_edit as AE

TOOL = Path(__file__).resolve().parents[1] / "scripts" / "anchor_edit.py"

SAMPLE = """alpha
def keep_me():
    return 1

def target():
    return 2

def also_keep():
    return 3
"""


# --- the refusals, which are the whole point ---------------------------------------------------

def test_replace_refuses_an_anchor_that_is_absent():
    """The wrong-file and wrong-repo catch.

    A file in the wrong repository rarely contains your exact expected text, so an absent-anchor
    refusal is a cheap, guard-free check that happens to catch a wrong cwd as a side effect. The
    silent alternative is `str.replace`, which returns the string unchanged and reports nothing.
    """
    with pytest.raises(AE.AnchorError) as exc:
        AE.replace_exact(SAMPLE, "def not_here():", "x")
    assert "0 times" in str(exc.value)


def test_replace_refuses_an_ambiguous_anchor():
    """Two matches means the edit lands on whichever came first, which is a coin toss.

    `str.replace(old, new, 1)` picks the first without a word, and the second occurrence is
    usually the one you meant when the first is in a docstring or a comment.
    """
    text = "marker\nbody\nmarker\n"
    with pytest.raises(AE.AnchorError) as exc:
        AE.replace_exact(text, "marker", "x")
    assert "2 times" in str(exc.value)


def test_replace_applies_when_the_anchor_is_unique():
    """It must be able to report the other answer, or the refusals above assert nothing."""
    out = AE.replace_exact(SAMPLE, "    return 2", "    return 22")
    assert "    return 22" in out
    assert "    return 1" in out


# --- insertion: zero removals is a postcondition, not an assumption ----------------------------

def test_insert_after_keeps_every_original_line():
    out = AE.insert_at(SAMPLE, "def target():", "# note\n", where="after")
    assert "# note" in out
    AE.assert_no_removals(SAMPLE, out)


def test_insert_before_puts_the_text_ahead_of_the_anchor():
    out = AE.insert_at(SAMPLE, "def target():", "# note\n", where="before")
    assert out.index("# note") < out.index("def target():")


def test_insert_refuses_an_absent_anchor():
    with pytest.raises(AE.AnchorError):
        AE.insert_at(SAMPLE, "def nope():", "# note\n", where="after")


def test_assert_no_removals_fires_when_a_line_disappeared():
    """The check must be able to fail, or every insertion above is asserting nothing.

    Driven directly rather than through a correct insert, because a correct insert cannot
    remove a line - which is exactly why the postcondition needs its own test.
    """
    with pytest.raises(AE.AnchorError) as exc:
        AE.assert_no_removals("a\nb\nc\n", "a\nc\n")
    assert "b" in str(exc.value)


def test_assert_no_removals_accepts_an_insertion():
    AE.assert_no_removals("a\nb\n", "a\nnew\nb\n")


# --- span replacement: the shape that deleted two functions in a measured incident -------------

def test_span_refuses_when_the_end_marker_only_occurs_before_the_start():
    """The end marker must be searched FROM the start offset, never from position 0.

    Measured shape: `text.index(end)` finds an earlier occurrence, the computed span runs
    backwards, and the slice silently produces nonsense rather than raising.
    """
    text = "def also_keep():\n    pass\n\ndef target():\n    pass\n"
    with pytest.raises(AE.AnchorError) as exc:
        AE.replace_span(text, "def target():", "def also_keep():", "", expect_removed_lines=2)
    assert "after" in str(exc.value)


def test_span_refuses_when_it_would_remove_more_lines_than_expected():
    """The harness_checks incident: a span meant for one function ate the two beside it.

    The write succeeded, the file still parsed, and 19 tests in two other modules were the only
    signal. Stating the expected removal count turns that silent deletion into a refusal.
    """
    with pytest.raises(AE.AnchorError) as exc:
        AE.replace_span(SAMPLE, "def target():", "def also_keep():", "", expect_removed_lines=2)
    assert "expected 2" in str(exc.value)


def test_span_applies_when_the_removal_count_matches():
    out = AE.replace_span(SAMPLE, "def target():", "def also_keep():", "",
                          expect_removed_lines=3)
    assert "def target():" not in out
    assert "def also_keep():" in out
    assert "def keep_me():" in out


def test_span_refuses_when_a_must_keep_construct_vanished():
    """Naming what must survive is the second half of the lesson, checked AFTER the edit."""
    with pytest.raises(AE.AnchorError) as exc:
        AE.replace_span(SAMPLE, "def keep_me():", "def also_keep():", "",
                        expect_removed_lines=6, must_keep=["def target():"])
    assert "def target():" in str(exc.value)


# --- file handling ----------------------------------------------------------------------------

def test_an_untracked_file_is_backed_up_before_it_is_written(tmp_path):
    """git is not the backup for a file git does not track, and gitignored files are the ones
    most often edited this way - a handover, a decision log, a scratch note."""
    target = tmp_path / "notes.md"
    target.write_text(SAMPLE, encoding="utf-8")
    result = AE.apply_to_file(target, lambda s: s.replace("return 2", "return 22"))
    assert result.backup is not None and result.backup.exists()
    assert result.backup.read_text(encoding="utf-8") == SAMPLE


def _git_repo(tmp_path, *, name="f.md", body=SAMPLE, commit=True, ignore=False):
    """A real git repo with one file, committed or not. Real git, because the question the code
    asks is 'can git restore this', and a fake cannot answer it wrongly the way git can."""
    run = lambda *a: subprocess.run(["git", *a], cwd=str(tmp_path), check=True,
                                    capture_output=True, text=True)
    run("init", "-q", ".")
    run("config", "user.email", "t@example.com")
    run("config", "user.name", "t")
    if ignore:
        (tmp_path / ".gitignore").write_text(name + "\n", encoding="utf-8")
    target = tmp_path / name
    target.write_text(body, encoding="utf-8")
    if commit and not ignore:
        run("add", name)
        run("commit", "-qm", "base")
    return target


def test_a_tracked_file_with_uncommitted_work_is_still_backed_up(tmp_path):
    """git is not the backup for changes git has never seen.

    `git checkout -- <file>` restores from HEAD, so it DISCARDS every uncommitted change in that
    file and exits 0. A rule that skips the backup for anything merely TRACKED therefore skips it
    in the one state the backup exists for.
    """
    target = _git_repo(tmp_path)
    target.write_text(SAMPLE + "uncommitted work\n", encoding="utf-8")
    before = target.read_text(encoding="utf-8")
    result = AE.apply_to_file(target, lambda s: s.replace("return 2", "return 22"))
    assert result.backup is not None, "a dirty tracked file must be backed up"
    assert result.backup.read_text(encoding="utf-8") == before


def test_a_tracked_and_clean_file_is_not_backed_up(tmp_path):
    """It must be able to answer the other way, or the test above proves nothing.

    Here git genuinely holds the content, so a .bak would be litter.
    """
    target = _git_repo(tmp_path)
    result = AE.apply_to_file(target, lambda s: s.replace("return 2", "return 22"))
    assert result.backup is None


def test_a_gitignored_file_is_backed_up(tmp_path):
    """`git status --porcelain <path>` is EMPTY for a gitignored file exactly as for a clean one.

    So a cleanliness test alone reads an ignored file as safely stored in git, which is the
    opposite of true. Tracking has to be asked separately, and it is.
    """
    target = _git_repo(tmp_path, ignore=True)
    result = AE.apply_to_file(target, lambda s: s.replace("return 2", "return 22"))
    assert result.backup is not None, "a gitignored file is not in git and must be backed up"


def test_every_run_keeps_its_own_backup(tmp_path):
    """The .bak is written only for a file git cannot restore, so it IS the only copy.

    Each run therefore gets its own: `.bak` holds the original, and `.bak.001`, `.bak.002` ...
    hold the state before each later edit, higher number newer. Nothing is ever overwritten, so no run
    can destroy the state another run recorded.
    """
    target = tmp_path / "notes.md"
    target.write_text(SAMPLE, encoding="utf-8")

    first = AE.apply_to_file(target, lambda s: s.replace("return 1", "return 11"))
    after_first = target.read_text(encoding="utf-8")
    assert first.backup.name == "notes.md.bak"
    assert first.backup.read_text(encoding="utf-8") == SAMPLE

    second = AE.apply_to_file(target, lambda s: s.replace("return 2", "return 22"))
    assert second.backup.name == "notes.md.bak.001", "a later run must not reuse the .bak name"
    assert second.backup.read_text(encoding="utf-8") == after_first
    assert (tmp_path / "notes.md.bak").read_text(encoding="utf-8") == SAMPLE, (
        "the original must survive every later run")


def test_backups_number_upward_without_a_gap(tmp_path):
    """It must be able to go past the second run, or the numbering is untested beyond one step."""
    target = tmp_path / "notes.md"
    target.write_text(SAMPLE, encoding="utf-8")
    for replacement in ("return 11", "return 22", "return 33"):
        AE.apply_to_file(target, lambda s, r=replacement: s.replace("return 1", r))
    assert sorted(p.name for p in tmp_path.glob("notes.md.bak*")) == [
        "notes.md.bak", "notes.md.bak.001", "notes.md.bak.002"]


def test_a_pre_existing_bak_from_another_tool_is_not_overwritten(tmp_path):
    """A `.bak` this tool did not write is still somebody's only copy of something."""
    target = tmp_path / "notes.md"
    target.write_text(SAMPLE, encoding="utf-8")
    (tmp_path / "notes.md.bak").write_text("SOMEBODY ELSE'S BACKUP\n", encoding="utf-8")
    result = AE.apply_to_file(target, lambda s: s.replace("return 1", "return 11"))
    assert result.backup.name == "notes.md.bak.001"
    assert (tmp_path / "notes.md.bak").read_text(encoding="utf-8") == "SOMEBODY ELSE'S BACKUP\n"


def test_backup_names_sort_in_the_order_they_were_written(tmp_path):
    """The number is zero-padded so a plain name sort is age order, past the ninth run too.

    Unpadded, `.bak.10` sorts between `.bak.1` and `.bak.2`, so `ls` and `sorted()` hand back
    the backups shuffled. Eleven runs cross that point.
    """
    target = tmp_path / "notes.md"
    target.write_text(SAMPLE, encoding="utf-8")
    written = []
    for run in range(11):
        result = AE.apply_to_file(target, lambda s, r=run: s + f"# run {r}\n")
        written.append(result.backup.name)
    assert sorted(written) == written


def test_numbering_continues_after_unpadded_backups_already_on_disk(tmp_path):
    """Backups an older version wrote as `.bak.1`, `.bak.2` already hold those numbers.

    Padding must not hand out `.bak.001` beside `.bak.1`: that is two copies claiming one place
    in the sequence, and the newer one would sort as the older.
    """
    target = tmp_path / "notes.md"
    target.write_text(SAMPLE, encoding="utf-8")
    for name in ("notes.md.bak", "notes.md.bak.1", "notes.md.bak.2"):
        (tmp_path / name).write_text("OLD\n", encoding="utf-8")
    assert AE.next_backup_path(target).name == "notes.md.bak.003"


def test_a_deleted_middle_backup_is_not_refilled(tmp_path):
    """Reusing a freed low number would file the newest state under an old number."""
    target = tmp_path / "notes.md"
    target.write_text(SAMPLE, encoding="utf-8")
    for name in ("notes.md.bak", "notes.md.bak.003"):
        (tmp_path / name).write_text("OLD\n", encoding="utf-8")
    assert AE.next_backup_path(target).name == "notes.md.bak.004"


def test_numbering_keeps_counting_past_999(tmp_path):
    """Past 999 the number widens rather than refusing: a refused safety copy blocks the edit.

    Name order breaks again from there (`.bak.1000` sorts before `.bak.101`); a thousand
    backups of one file means nobody reaped them, and losing the sort is the cheaper failure.
    """
    target = tmp_path / "notes.md"
    target.write_text(SAMPLE, encoding="utf-8")
    for name in ("notes.md.bak", "notes.md.bak.999"):
        (tmp_path / name).write_text("OLD\n", encoding="utf-8")
    assert AE.next_backup_path(target).name == "notes.md.bak.1000"


def test_a_file_name_with_glob_characters_finds_its_own_backups(tmp_path):
    """`a[1].md` as a glob pattern matches `a1.md`, never itself, so its numbers would be missed."""
    target = tmp_path / "a[1].md"
    target.write_text(SAMPLE, encoding="utf-8")
    for name in ("a[1].md.bak", "a[1].md.bak.004"):
        (tmp_path / name).write_text("OLD\n", encoding="utf-8")
    assert AE.next_backup_path(target).name == "a[1].md.bak.005"


def test_a_non_numeric_bak_suffix_does_not_count_as_a_number(tmp_path):
    """`.bak.orig` or `.bak.tmp` from another tool is left alone and does not shift the count."""
    target = tmp_path / "notes.md"
    target.write_text(SAMPLE, encoding="utf-8")
    for name in ("notes.md.bak", "notes.md.bak.orig", "notes.md.bak.12x"):
        (tmp_path / name).write_text("OTHER\n", encoding="utf-8")
    assert AE.next_backup_path(target).name == "notes.md.bak.001"


def test_a_dry_run_does_not_touch_the_file(tmp_path):
    target = tmp_path / "notes.md"
    target.write_text(SAMPLE, encoding="utf-8")
    result = AE.apply_to_file(target, lambda s: s.replace("return 2", "return 22"), dry_run=True)
    assert target.read_text(encoding="utf-8") == SAMPLE
    assert result.line_delta == 0


# --- CLI ---------------------------------------------------------------------------------------

def _run(*args, **kw):
    return subprocess.run([sys.executable, str(TOOL), *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", **kw)


def test_cli_applies_a_replacement_and_exits_zero(tmp_path):
    target = tmp_path / "f.py"
    target.write_text(SAMPLE, encoding="utf-8")
    proc = _run("replace", str(target), "--anchor", "    return 2", "--new-text", "    return 22")
    assert proc.returncode == 0, proc.stderr
    assert "    return 22" in target.read_text(encoding="utf-8")


def test_cli_refuses_an_absent_anchor_with_exit_two_and_writes_nothing(tmp_path):
    """A refusal of the whole edit is "could not run" (2) under the 0/1/2 standard."""
    target = tmp_path / "f.py"
    target.write_text(SAMPLE, encoding="utf-8")
    proc = _run("replace", str(target), "--anchor", "absent", "--new-text", "x")
    assert proc.returncode == 2
    assert target.read_text(encoding="utf-8") == SAMPLE


def test_cli_json_stays_parseable_on_a_refusal(tmp_path):
    """A machine-readable mode that emits nothing on failure forces the caller back to parsing
    stderr, which is where the exit code already was."""
    target = tmp_path / "f.py"
    target.write_text(SAMPLE, encoding="utf-8")
    proc = _run("replace", str(target), "--anchor", "absent", "--new-text", "x", "--json")
    assert proc.returncode == 2
    payload = json.loads(proc.stdout)
    assert payload["ok"] is False
    assert payload["command"] == "anchor_edit"
    assert payload["data"]["refused"] is True and "appears 0 times" in payload["error"]


def test_cli_usage_error_exits_two(tmp_path):
    proc = _run("replace", str(tmp_path / "missing.py"), "--anchor", "a", "--new-text", "b")
    assert proc.returncode == 2


def test_a_relative_path_is_refused_because_it_names_a_different_file_per_directory(tmp_path):
    """Which file `notes.md` names depends on the cwd, and a cwd persists across calls. The
    measured failure is not a crash: the edit lands in a SIBLING repo's file of the same name
    and exits 0.

    The absent-anchor check does not cover this. Sibling repos are the case where the anchor is
    most likely to be PRESENT in the wrong file - template-copied docs, a section duplicated
    across repos, a shared heading - so the one guard that would catch it is refusing to accept
    a path whose meaning depends on where you happen to be standing.
    """
    (tmp_path / "notes.md").write_text("alpha\nbravo\n", encoding="utf-8")
    r = subprocess.run([sys.executable, str(TOOL), "replace", "notes.md",
                        "--anchor", "alpha", "--new-text", "charlie"],
                       capture_output=True, text=True, check=False, cwd=str(tmp_path))
    assert r.returncode == 2, r.stdout + r.stderr
    assert "absolute" in (r.stderr + r.stdout).lower()
    # Control: the file is untouched, so the refusal really did happen before any write.
    assert (tmp_path / "notes.md").read_text(encoding="utf-8") == "alpha\nbravo\n"


def test_an_absolute_path_is_accepted(tmp_path):
    """Control for the refusal above: it must reject the relative form only, not every path."""
    target = tmp_path / "notes.md"
    target.write_text("alpha\nbravo\n", encoding="utf-8")
    r = subprocess.run([sys.executable, str(TOOL), "replace", str(target),
                        "--anchor", "alpha", "--new-text", "charlie", "--no-backup"],
                       capture_output=True, text=True, check=False, cwd=str(tmp_path))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "charlie" in target.read_text(encoding="utf-8")


# --- recoverability must be asked about THIS file, literally ------------------------------------

def _git(tmp_path, *a):
    return subprocess.run(["git", *a], cwd=str(tmp_path), check=True, capture_output=True,
                          text=True)


def test_a_gitignored_file_with_glob_characters_in_its_name_is_backed_up(tmp_path):
    """`f[1].md` as a pathspec is a glob matching the tracked `f1.md`, so the ignored file read
    as tracked and clean, got no backup, and its only copy was overwritten."""
    _git_repo(tmp_path, name="f1.md")
    (tmp_path / ".gitignore").write_text("f[[]1].md\n", encoding="utf-8")
    target = tmp_path / "f[1].md"
    target.write_bytes(SAMPLE.encode("utf-8"))
    result = AE.apply_to_file(target, lambda s: s.replace("return 2", "return 22"))
    assert result.backup is not None, "an ignored file must be backed up"
    assert result.backup.read_bytes() == SAMPLE.encode("utf-8")


def test_a_tracked_clean_file_with_glob_characters_is_still_recognised(tmp_path):
    """Control: literal matching must still find a tracked file whose name holds [ ]."""
    target = _git_repo(tmp_path, name="g[1].md")
    assert AE.is_recoverable_from_git(target) is True


def test_a_skip_worktree_file_with_local_edits_is_backed_up(tmp_path):
    """--skip-worktree makes `git status` report the file clean while it holds local work that
    exists nowhere in git."""
    target = _git_repo(tmp_path, name="cfg.ini", body="committed\n")
    _git(tmp_path, "update-index", "--skip-worktree", "cfg.ini")
    target.write_bytes(b"local work\n")
    assert AE.is_recoverable_from_git(target) is False
    result = AE.apply_to_file(target, lambda s: s.replace("local", "LOCAL"))
    assert result.backup is not None and result.backup.read_bytes() == b"local work\n"


def test_an_assume_unchanged_file_with_local_edits_is_backed_up(tmp_path):
    target = _git_repo(tmp_path, name="cfg.ini", body="committed\n")
    _git(tmp_path, "update-index", "--assume-unchanged", "cfg.ini")
    target.write_bytes(b"local work\n")
    assert AE.is_recoverable_from_git(target) is False


# --- overlapping anchors ------------------------------------------------------------------------

def test_an_overlapping_second_occurrence_makes_the_anchor_ambiguous():
    """str.count skips overlapping matches: "}\\n}" occurs at 0 AND 2 in "}\\n}\\n}\\n"."""
    assert AE.occurrences("}\n}\n}\n", "}\n}") == 2
    with pytest.raises(AE.AnchorError, match="2 times"):
        AE.replace_exact("}\n}\n}\n", "}\n}", "X")


def test_a_non_overlapping_unique_anchor_still_applies():
    assert AE.replace_exact("}\n}\nz\n", "}\n}", "X") == "X\nz\n"


def test_span_refuses_an_overlapping_second_end_marker():
    text = "start\nbody\n}\n}\n}\n"
    with pytest.raises(AE.AnchorError, match="more than once"):
        AE.replace_span(text, "start\n", "}\n}", "", expect_removed_lines=1)


def test_span_refuses_a_second_end_marker_after_the_first():
    text = "start\nbody\nEND\nmiddle\nEND\n"
    with pytest.raises(AE.AnchorError, match="more than once"):
        AE.replace_span(text, "start\n", "END", "", expect_removed_lines=2)


# --- line endings and bytes ---------------------------------------------------------------------

def test_a_crlf_file_keeps_its_crlf_line_endings(tmp_path):
    target = tmp_path / "w.txt"
    target.write_bytes(b"a\r\nb\r\nc\r\n")
    result = AE.apply_to_file(target, lambda s: AE.replace_exact(s, "b", "B"))
    assert target.read_bytes() == b"a\r\nB\r\nc\r\n"
    assert result.backup.read_bytes() == b"a\r\nb\r\nc\r\n"


def test_a_multiline_lf_anchor_matches_in_a_crlf_file(tmp_path):
    target = tmp_path / "w.txt"
    target.write_bytes(b"a\r\nb\r\nc\r\n")
    AE.apply_to_file(target, lambda s: AE.insert_at(s, "a\nb\n", "new\n"))
    assert target.read_bytes() == b"a\r\nb\r\nnew\r\nc\r\n"


def test_crlf_new_text_in_a_crlf_file_is_not_doubled_to_cr_cr_lf(tmp_path):
    """The file is edited as LF and written back by turning every LF into CRLF, so a CRLF that
    arrived IN the new text came out as CR CR LF."""
    target = tmp_path / "w.txt"
    target.write_bytes(b"a\r\nb\r\nc\r\n")
    AE.apply_to_file(target, lambda s: AE.replace_exact(s, "b\n", "x\r\ny\r\n"))
    assert target.read_bytes() == b"a\r\nx\r\ny\r\nc\r\n"


def test_cli_crlf_new_text_in_a_crlf_file_is_not_doubled(tmp_path):
    target = tmp_path / "w.txt"
    target.write_bytes(b"a\r\nb\r\n")
    proc = _run("replace", str(target), "--anchor", "a", "--new-text", "x\r\ny")
    assert proc.returncode == 0, proc.stderr
    assert target.read_bytes() == b"x\r\ny\r\nb\r\n"


def test_a_crlf_file_holding_cr_cr_lf_still_round_trips_byte_exact(tmp_path):
    """Every newline is part of a CRLF here too, so it is edited as LF with a CR left before one
    LF; that CR is file content and must survive the write-back."""
    target = tmp_path / "w.txt"
    target.write_bytes(b"a\r\r\nb\r\n")
    AE.apply_to_file(target, lambda s: AE.replace_exact(s, "b", "B"))
    assert target.read_bytes() == b"a\r\r\nB\r\n"


def test_an_lf_file_stays_lf(tmp_path):
    target = tmp_path / "u.txt"
    target.write_bytes(b"a\nb\nc\n")
    result = AE.apply_to_file(target, lambda s: AE.replace_exact(s, "b", "B"))
    assert target.read_bytes() == b"a\nB\nc\n"
    assert result.backup.read_bytes() == b"a\nb\nc\n"


def test_a_lone_cr_and_a_mixed_file_are_left_byte_exact(tmp_path):
    target = tmp_path / "m.txt"
    target.write_bytes(b"a\rb\r\nc\nd\n")
    AE.apply_to_file(target, lambda s: AE.replace_exact(s, "d", "D"))
    assert target.read_bytes() == b"a\rb\r\nc\nD\n"


def test_a_utf8_bom_on_the_target_is_preserved(tmp_path):
    target = tmp_path / "bom.txt"
    target.write_bytes(b"\xef\xbb\xbfalpha\nbravo\n")
    AE.apply_to_file(target, lambda s: AE.replace_exact(s, "bravo", "charlie"))
    assert target.read_bytes() == b"\xef\xbb\xbfalpha\ncharlie\n"


def test_a_form_feed_does_not_count_as_a_line_break():
    """A Python file may hold a form feed; splitlines() would count it as a line break."""
    text = "start\na\x0cb\nEND\n"
    out = AE.replace_span(text, "start\n", "END", "", expect_removed_lines=2)
    assert out == "END\n"


def test_an_anchor_file_with_a_bom_still_matches(tmp_path):
    target = tmp_path / "f.txt"
    target.write_bytes(b"alpha\nbravo\n")
    anchor = tmp_path / "a.txt"
    anchor.write_bytes(b"\xef\xbb\xbfbravo")
    proc = _run("replace", str(target), "--anchor-file", str(anchor), "--new-text", "charlie")
    assert proc.returncode == 0, proc.stderr
    assert target.read_bytes() == b"alpha\ncharlie\n"


# --- exit codes: 1 is a refusal, 2 is usage or IO ------------------------------------------------

def test_a_non_utf8_file_is_exit_2_not_a_traceback(tmp_path):
    target = tmp_path / "latin.txt"
    target.write_bytes(b"caf\xe9\n")
    proc = _run("replace", str(target), "--anchor", "caf", "--new-text", "x", "--json")
    assert proc.returncode == 2
    assert "Traceback" not in proc.stderr
    assert json.loads(proc.stdout)["ok"] is False
    assert target.read_bytes() == b"caf\xe9\n"


def test_a_missing_anchor_file_is_exit_2(tmp_path):
    target = tmp_path / "f.txt"
    target.write_bytes(b"alpha\n")
    proc = _run("replace", str(target), "--anchor-file", str(tmp_path / "nope"),
                "--new-text", "x")
    assert proc.returncode == 2


def test_no_anchor_at_all_is_exit_2(tmp_path):
    target = tmp_path / "f.txt"
    target.write_bytes(b"alpha\n")
    assert _run("replace", str(target), "--new-text", "x").returncode == 2


def test_anchor_and_anchor_file_together_is_exit_2(tmp_path):
    target = tmp_path / "f.txt"
    target.write_bytes(b"alpha\n")
    anchor = tmp_path / "a.txt"
    anchor.write_bytes(b"alpha")
    assert _run("replace", str(target), "--anchor", "alpha", "--anchor-file", str(anchor),
                "--new-text", "x").returncode == 2


_ROOT = hasattr(os, "geteuid") and os.geteuid() == 0


@pytest.mark.skipif(_ROOT, reason="root ignores file permission bits")
def test_a_read_only_target_is_exit_2_and_does_not_claim_nothing_was_written(tmp_path):
    target = tmp_path / "f.txt"
    target.write_bytes(b"alpha\n")
    os.chmod(target, stat.S_IREAD)
    try:
        proc = _run("replace", str(target), "--anchor", "alpha", "--new-text", "x")
    finally:
        os.chmod(target, stat.S_IREAD | stat.S_IWRITE)
    assert proc.returncode == 2
    assert "Traceback" not in proc.stderr
    assert "nothing written" not in proc.stderr
    assert "f.txt.bak" in proc.stderr
    assert target.read_bytes() == b"alpha\n"


@pytest.mark.skipif(_ROOT or sys.platform == "win32",
                    reason="root ignores permission bits; a read-only DIRECTORY attribute does "
                           "not block creating files in it on Windows")
def test_a_backup_that_cannot_be_written_is_exit_2_and_leaves_the_file(tmp_path):
    d = tmp_path / "ro"
    d.mkdir()
    target = d / "f.txt"
    target.write_bytes(b"alpha\n")
    os.chmod(d, stat.S_IREAD | stat.S_IEXEC)
    try:
        proc = _run("replace", str(target), "--anchor", "alpha", "--new-text", "x")
    finally:
        os.chmod(d, stat.S_IRWXU)
    assert proc.returncode == 2
    assert "Traceback" not in proc.stderr
    assert target.read_bytes() == b"alpha\n"


def test_a_non_cp1252_path_does_not_crash_a_cp1252_stdout(tmp_path):
    """The success line prints the path on stdout, which is strict on a cp1252 stream."""
    target = tmp_path / "f\u2717.txt"
    target.write_bytes(b"alpha\n")
    proc = subprocess.run([sys.executable, str(TOOL), "replace", str(target), "--anchor",
                           "alpha", "--new-text", "x", "--no-backup"], capture_output=True,
                          env={**os.environ, "PYTHONIOENCODING": "cp1252"}, timeout=60)
    assert proc.returncode == 0, proc.stderr
    assert b"Traceback" not in proc.stderr
    assert target.read_bytes() == b"x\n"


# --- the CLI paths beyond a plain replace --------------------------------------------------------

def test_cli_insert_defaults_to_after(tmp_path):
    target = tmp_path / "f.txt"
    target.write_bytes(b"alpha\nbravo\n")
    proc = _run("insert", str(target), "--anchor", "alpha\n", "--new-text", "NEW\n", "--no-backup")
    assert proc.returncode == 0, proc.stderr
    assert target.read_bytes() == b"alpha\nNEW\nbravo\n"


def test_cli_insert_before(tmp_path):
    target = tmp_path / "f.txt"
    target.write_bytes(b"alpha\nbravo\n")
    proc = _run("insert", str(target), "--anchor", "bravo\n", "--new-text", "NEW\n", "--before",
                "--no-backup")
    assert proc.returncode == 0, proc.stderr
    assert target.read_bytes() == b"alpha\nNEW\nbravo\n"


def test_cli_replace_span_with_must_keep(tmp_path):
    target = tmp_path / "f.py"
    target.write_bytes(SAMPLE.encode("utf-8"))
    ok = _run("replace-span", str(target), "--start", "def target():", "--end", "def also_keep():",
              "--new-text", "", "--expect-removed-lines", "3", "--must-keep", "def keep_me():",
              "--no-backup")
    assert ok.returncode == 0, ok.stderr
    assert "def target():" not in target.read_text(encoding="utf-8")


def test_cli_replace_span_refuses_when_must_keep_is_lost(tmp_path):
    target = tmp_path / "f.py"
    target.write_bytes(SAMPLE.encode("utf-8"))
    bad = _run("replace-span", str(target), "--start", "def keep_me():", "--end",
               "def also_keep():", "--new-text", "", "--expect-removed-lines", "6",
               "--must-keep", "def target():")
    assert bad.returncode == 2
    assert target.read_bytes() == SAMPLE.encode("utf-8")


def test_cli_anchor_from_stdin_with_dry_run(tmp_path):
    target = tmp_path / "f.txt"
    target.write_bytes(b"alpha\nbravo\n")
    proc = subprocess.run([sys.executable, str(TOOL), "replace", str(target), "--anchor-file", "-",
                           "--new-text", "one\ntwo", "--dry-run"], input=b"bravo",
                          capture_output=True, timeout=60)
    assert proc.returncode == 0, proc.stderr
    assert b"would change" in proc.stdout and b"+1 lines" in proc.stdout
    assert target.read_bytes() == b"alpha\nbravo\n"
    assert not (tmp_path / "f.txt.bak").exists()


# ---- reap: delete a file's backups once git can restore the file ------------------------------

def _plant_backups(target, *suffixes):
    for suffix in suffixes:
        target.with_name(target.name + suffix).write_text("OLD\n", encoding="utf-8")


def test_reap_lists_but_deletes_nothing_without_apply(tmp_path):
    """Deletion is asked for, never implied: the bare verb is the preview."""
    target = _git_repo(tmp_path)
    _plant_backups(target, ".bak", ".bak.001")
    proc = _run("reap", str(target))
    assert proc.returncode == 0, proc.stderr
    assert "f.md.bak.001" in proc.stdout
    assert (tmp_path / "f.md.bak").exists() and (tmp_path / "f.md.bak.001").exists()


def test_reap_apply_deletes_every_backup_spelling_and_nothing_else(tmp_path):
    """`.bak`, padded and legacy unpadded numbers go; the file, a non-numeric suffix and a
    directory that happens to carry a backup-shaped name stay."""
    target = _git_repo(tmp_path)
    _plant_backups(target, ".bak", ".bak.001", ".bak.2", ".bak.orig")
    (tmp_path / "f.md.bak.003").mkdir()
    proc = _run("reap", str(target), "--apply")
    assert proc.returncode == 0, proc.stderr
    left = sorted(p.name for p in tmp_path.iterdir() if p.name.startswith("f.md"))
    assert left == ["f.md", "f.md.bak.003", "f.md.bak.orig"]


def test_reap_refuses_a_file_git_cannot_restore(tmp_path):
    """Untracked: the backups may be the only copies there are."""
    target = _git_repo(tmp_path, commit=False)
    _plant_backups(target, ".bak")
    proc = _run("reap", str(target), "--apply")
    assert proc.returncode == 2
    assert (tmp_path / "f.md.bak").exists()


def test_reap_refuses_a_tracked_file_with_uncommitted_work(tmp_path):
    """Tracked is not committed: the working copy holds content git has never seen."""
    target = _git_repo(tmp_path)
    target.write_text(SAMPLE + "# local work\n", encoding="utf-8")
    _plant_backups(target, ".bak")
    proc = _run("reap", str(target), "--apply")
    assert proc.returncode == 2
    assert (tmp_path / "f.md.bak").exists()


def test_reap_with_no_backups_is_a_clean_success(tmp_path):
    target = _git_repo(tmp_path)
    proc = _run("reap", str(target), "--apply")
    assert proc.returncode == 0, proc.stderr


def test_reap_json_envelope_names_what_it_deleted(tmp_path):
    target = _git_repo(tmp_path)
    _plant_backups(target, ".bak", ".bak.001")
    proc = _run("reap", str(target), "--apply", "--json")
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)["data"]
    assert [Path(p).name for p in data["backups"]] == ["f.md.bak", "f.md.bak.001"]
    assert data["deleted"] is True


def test_reap_refuses_a_relative_path(tmp_path):
    target = _git_repo(tmp_path)
    _plant_backups(target, ".bak")
    proc = _run("reap", "f.md", "--apply", cwd=str(tmp_path))
    assert proc.returncode == 2
    assert "relative" in proc.stderr, "exit 2 must come from the path check, not a usage error"
    assert (tmp_path / "f.md.bak").exists()


def test_an_edit_that_writes_a_backup_names_the_reap_command(tmp_path):
    """The backup line is where the reader learns a backup exists, so it is where they learn how
    to clear it."""
    target = tmp_path / "f.py"
    target.write_text(SAMPLE, encoding="utf-8")
    proc = _run("replace", str(target), "--anchor", "    return 2", "--new-text", "    return 22")
    assert proc.returncode == 0, proc.stderr
    assert "reap" in proc.stdout


# ---- wave D: unified exit codes and the D2 envelope ---------------------------------------------

def test_cli_json_relative_path_prints_the_envelope(tmp_path):
    (tmp_path / "notes.md").write_text("alpha\n", encoding="utf-8")
    proc = _run("replace", "notes.md", "--anchor", "alpha", "--new-text", "b", "--json",
                cwd=str(tmp_path))
    assert proc.returncode == 2
    payload = json.loads(proc.stdout)
    assert payload["ok"] is False and "absolute" in payload["error"]


def test_cli_json_missing_file_prints_the_envelope(tmp_path):
    proc = _run("replace", str(tmp_path / "missing.py"), "--anchor", "a", "--new-text", "b",
                "--json")
    assert proc.returncode == 2
    payload = json.loads(proc.stdout)
    assert payload["ok"] is False and "no such file" in payload["error"]


def test_cli_json_argparse_error_prints_the_envelope(tmp_path):
    proc = _run("replace", str(tmp_path / "f.py"), "--json", "--no-such-flag")
    assert proc.returncode == 2
    payload = json.loads(proc.stdout)
    assert payload["ok"] is False and payload["command"] == "anchor_edit"


def test_cli_json_crash_prints_the_envelope(tmp_path, monkeypatch, capsys):
    target = tmp_path / "f.py"
    target.write_text(SAMPLE, encoding="utf-8")

    def boom(*_a, **_k):
        raise RuntimeError("writer broke")
    monkeypatch.setattr(AE, "apply_to_file", boom)
    rc = AE.main(["replace", str(target), "--anchor", "alpha", "--new-text", "b", "--json"])
    assert rc == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False and "writer broke" in payload["error"]


def test_cli_json_reap_refusal_marks_refused(tmp_path):
    target = _git_repo(tmp_path, commit=False)
    proc = _run("reap", str(target), "--apply", "--json")
    assert proc.returncode == 2
    assert json.loads(proc.stdout)["data"]["refused"] is True


# ---- batch: every edit checked before any write ------------------------------------------------

def _spec(tmp_path, doc):
    spec = tmp_path / "spec.json"
    spec.write_bytes(json.dumps(doc).encode("utf-8"))
    return spec


def test_batch_applies_edits_across_files(tmp_path):
    a, b = tmp_path / "a.md", tmp_path / "b.md"
    a.write_bytes(b"one\ntwo\n")
    b.write_bytes(b"three\nfour\n")
    spec = _spec(tmp_path, [{"file": str(a), "old": "two", "new": "TWO"},
                            {"file": str(b), "old": "three\n", "new": "3\n3b\n"}])
    proc = _run("batch", "--spec", str(spec), "--no-backup", "--json")
    assert proc.returncode == 0, proc.stderr
    assert a.read_bytes() == b"one\nTWO\n" and b.read_bytes() == b"3\n3b\nfour\n"
    files = {Path(f["path"]).name: f for f in json.loads(proc.stdout)["data"]["files"]}
    assert files["a.md"]["line_delta"] == 0 and files["b.md"]["line_delta"] == 1


def test_batch_refuses_everything_when_one_anchor_is_absent(tmp_path):
    """The point of the verb: the bad pair is the LAST one, and the first file is still untouched."""
    a, b = tmp_path / "a.md", tmp_path / "b.md"
    a.write_bytes(b"one\n")
    b.write_bytes(b"two\n")
    spec = _spec(tmp_path, [{"file": str(a), "old": "one", "new": "ONE"},
                            {"file": str(b), "old": "absent", "new": "x"}])
    proc = _run("batch", "--spec", str(spec), "--no-backup", "--json")
    assert proc.returncode == 2
    payload = json.loads(proc.stdout)
    assert payload["ok"] is False and payload["data"]["refused"] is True
    assert payload["data"]["edit"] == 2
    assert a.read_bytes() == b"one\n" and b.read_bytes() == b"two\n"


def test_batch_count_must_match_exactly(tmp_path):
    a = tmp_path / "a.md"
    a.write_bytes(b"x x x\n")
    refused = _run("batch", "--spec",
                   str(_spec(tmp_path, [{"file": str(a), "old": "x", "new": "y", "count": 2}])),
                   "--no-backup")
    assert refused.returncode == 2 and a.read_bytes() == b"x x x\n"
    assert "3 times" in refused.stderr
    done = _run("batch", "--spec",
                str(_spec(tmp_path, [{"file": str(a), "old": "x", "new": "y", "count": 3}])),
                "--no-backup")
    assert done.returncode == 0, done.stderr
    assert a.read_bytes() == b"y y y\n"


def test_batch_count_refuses_overlapping_occurrences(tmp_path):
    """'aa' occurs at 0 and 1 in 'aaa': str.replace would rewrite only one of the two."""
    a = tmp_path / "a.md"
    a.write_bytes(b"aaa\n")
    proc = _run("batch", "--spec",
                str(_spec(tmp_path, [{"file": str(a), "old": "aa", "new": "b", "count": 2}])),
                "--no-backup")
    assert proc.returncode == 2 and a.read_bytes() == b"aaa\n"


def test_batch_expect_line_delta_refuses_a_one_line_edit_that_grew(tmp_path):
    """#42/#100: a one-line record edit must leave the line count unchanged."""
    a = tmp_path / "a.md"
    a.write_bytes(b"- [ ] item\nnext\n")
    doc = {"edits": [{"file": str(a), "old": "- [ ] item\n", "new": "- [x] item\nstray\n"}],
           "expect_line_delta": {str(a): 0}}
    proc = _run("batch", "--spec", str(_spec(tmp_path, doc)), "--no-backup")
    assert proc.returncode == 2 and a.read_bytes() == b"- [ ] item\nnext\n"
    assert "+1" in proc.stderr
    doc["edits"][0]["new"] = "- [x] item\n"
    ok = _run("batch", "--spec", str(_spec(tmp_path, doc)), "--no-backup")
    assert ok.returncode == 0, ok.stderr
    assert a.read_bytes() == b"- [x] item\nnext\n"


def test_batch_dry_run_reports_per_file_delta_and_writes_nothing(tmp_path):
    a = tmp_path / "a.md"
    a.write_bytes(b"one\n")
    spec = _spec(tmp_path, [{"file": str(a), "old": "one\n", "new": "one\ntwo\n"}])
    proc = _run("batch", "--spec", str(spec), "--dry-run")
    assert proc.returncode == 0, proc.stderr
    assert "would change" in proc.stdout and "+1 lines" in proc.stdout
    assert a.read_bytes() == b"one\n"
    assert not (tmp_path / "a.md.bak").exists()


def test_batch_edits_to_one_file_apply_in_order(tmp_path):
    """The second edit sees the first one's result, so it can anchor on what the first wrote."""
    a = tmp_path / "a.md"
    a.write_bytes(b"one\n")
    spec = _spec(tmp_path, [{"file": str(a), "old": "one", "new": "two"},
                            {"file": str(a), "old": "two", "new": "three"}])
    proc = _run("batch", "--spec", str(spec), "--no-backup")
    assert proc.returncode == 0, proc.stderr
    assert a.read_bytes() == b"three\n"


def test_batch_two_spellings_of_one_file_are_one_file(tmp_path):
    """Planned separately, the second write would silently discard the first edit."""
    sub = tmp_path / "sub"
    sub.mkdir()
    a = tmp_path / "a.md"
    a.write_bytes(b"one two\n")
    other = str(sub / ".." / "a.md")
    spec = _spec(tmp_path, [{"file": str(a), "old": "one", "new": "ONE"},
                            {"file": other, "old": "two", "new": "TWO"}])
    proc = _run("batch", "--spec", str(spec), "--no-backup")
    assert proc.returncode == 0, proc.stderr
    assert a.read_bytes() == b"ONE TWO\n"


@pytest.mark.parametrize("doc,needle", [
    ([{"file": "rel.md", "old": "a", "new": "b"}], "absolute"),
    # Filled in with an absolute path under tmp_path: "/no/such" is DRIVE-relative on Windows.
    ([{"file": "{missing}", "old": "a", "new": "b"}], "no such file"),
    ([{"file": "/x", "old": "a"}], "new"),
    ([{"file": "/x", "old": "", "new": "b"}], "empty"),
    ([{"file": "/x", "old": "a", "new": "b", "count": 0}], "count"),
    ([], "no edits"),
    ({"edits": [{"file": "/x", "old": "a", "new": "b"}], "bogus": 1}, "bogus"),
])
def test_batch_a_malformed_spec_is_a_usage_error(tmp_path, doc, needle):
    if isinstance(doc, list) and doc and doc[0].get("file") == "{missing}":
        doc = [{**doc[0], "file": str(tmp_path / "no-such-file.md")}]
    proc = _run("batch", "--spec", str(_spec(tmp_path, doc)), "--json")
    assert proc.returncode == 2
    payload = json.loads(proc.stdout)
    assert payload["ok"] is False and needle in payload["error"]
    assert "refused" not in payload["data"]


def test_batch_spec_from_stdin(tmp_path):
    a = tmp_path / "a.md"
    a.write_bytes(b"one\n")
    doc = json.dumps([{"file": str(a), "old": "one", "new": "1"}]).encode("utf-8")
    proc = subprocess.run([sys.executable, str(TOOL), "batch", "--spec", "-", "--no-backup"],
                          input=doc, capture_output=True, timeout=60)
    assert proc.returncode == 0, proc.stderr
    assert a.read_bytes() == b"1\n"


def test_batch_keeps_crlf_and_backs_up_an_untracked_file(tmp_path):
    a = tmp_path / "a.md"
    a.write_bytes(b"one\r\ntwo\r\n")
    spec = _spec(tmp_path, [{"file": str(a), "old": "one\n", "new": "one\nhalf\n"}])
    proc = _run("batch", "--spec", str(spec))
    assert proc.returncode == 0, proc.stderr
    assert a.read_bytes() == b"one\r\nhalf\r\ntwo\r\n"
    assert AE.existing_backups(a), "an untracked file must be backed up before the write"


# ---- C90: inside a git work tree the backup lives OUTSIDE it, where no `git add` reaches -------

def _porcelain(root):
    return subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"],
                          cwd=str(root), check=True, capture_output=True, text=True).stdout


@pytest.mark.parametrize("kind", ["untracked", "ignored", "dirty"])
def test_a_backup_in_a_work_tree_is_never_stageable(tmp_path, kind):
    """A sibling .bak is an untracked file: `git add -A`, an IDE's auto-add or a release tool's
    blanket stage puts the pre-image into the next commit (measured: a 2846-line .bak staged in a
    repo one push away from a public PR). Under the git dir no `git add` can reach it."""
    target = _git_repo(tmp_path, commit=(kind == "dirty"), ignore=(kind == "ignored"))
    if kind == "dirty":
        target.write_text(SAMPLE + "local\n", encoding="utf-8")
    before = target.read_bytes()
    result = AE.apply_to_file(target, lambda s: s.replace("return 2", "return 22"))
    assert result.backup is not None and result.backup.read_bytes() == before
    # Both resolved: a Windows temp dir can be spelled with 8.3 short names on one side only.
    git_dir = Path(_git(tmp_path, "rev-parse", "--absolute-git-dir").stdout.strip()).resolve()
    assert git_dir in result.backup.resolve().parents
    assert ".bak" not in _porcelain(tmp_path)
    _git(tmp_path, "add", "-A")
    staged = _git(tmp_path, "diff", "--cached", "--name-only").stdout
    assert ".bak" not in staged


def test_a_backup_outside_any_work_tree_stays_beside_the_file(tmp_path):
    """Control: with no git dir to hold it, the sibling .bak is still the place."""
    target = tmp_path / "plain.md"
    target.write_bytes(b"one\n")
    result = AE.apply_to_file(target, lambda s: s.replace("one", "two"))
    assert result.backup == tmp_path / "plain.md.bak"


def test_backups_in_the_git_dir_are_numbered_and_never_overwritten(tmp_path):
    (tmp_path / "sub").mkdir()
    _git_repo(tmp_path, name="other.md")
    target = tmp_path / "sub" / "f.md"
    target.write_bytes(b"v1\n")
    first = AE.apply_to_file(target, lambda s: s.replace("v1", "v2")).backup
    second = AE.apply_to_file(target, lambda s: s.replace("v2", "v3")).backup
    assert first.name == "f.md.bak" and second.name == "f.md.bak.001"
    assert first.parent.name == "sub", "the work-tree layout is mirrored, so names cannot collide"
    assert first.read_bytes() == b"v1\n" and second.read_bytes() == b"v2\n"


def test_reap_deletes_git_dir_backups_and_legacy_sibling_ones(tmp_path):
    target = _git_repo(tmp_path, commit=False)
    _plant_backups(target, ".bak")                       # one an older version left beside it
    AE.apply_to_file(target, lambda s: s.replace("return 2", "return 22"))
    _git(tmp_path, "add", "f.md")
    _git(tmp_path, "commit", "-qm", "now restorable")
    found = AE.existing_backups(target)
    assert len(found) == 2 and (tmp_path / "f.md.bak") in found
    proc = _run("reap", str(target), "--apply")
    assert proc.returncode == 0, proc.stderr
    assert not any(b.exists() for b in found)


def test_a_file_inside_the_git_dir_falls_back_to_a_sibling_backup(tmp_path):
    """No work tree contains .git/info/exclude, so there is nothing to keep the backup out of."""
    _git_repo(tmp_path)
    exclude = tmp_path / ".git" / "info" / "exclude"
    exclude.parent.mkdir(parents=True, exist_ok=True)
    exclude.write_bytes(b"# x\n")
    result = AE.apply_to_file(exclude, lambda s: s + "*.log\n")
    assert result.backup == exclude.with_name("exclude.bak")

