"""Tests for anchor_edit.py - edit a file at an EXACT anchor, or refuse.

Every refusal here corresponds to a measured incident. Python's no-match branches are
success-shaped: `str.replace` is a silent no-op, `str.partition` puts everything in the head,
and `str.find` returns -1, which then indexes from the END of the string. So the failure mode
of a hand-rolled anchor edit is not a crash, it is a file that looks edited and is not, or one
edited somewhere else entirely.
"""
import json
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

    Each run therefore gets its own: `.bak` holds the original, and `.bak.1`, `.bak.2` ... hold
    the state before each later edit, higher number newer. Nothing is ever overwritten, so no run
    can destroy the state another run recorded.
    """
    target = tmp_path / "notes.md"
    target.write_text(SAMPLE, encoding="utf-8")

    first = AE.apply_to_file(target, lambda s: s.replace("return 1", "return 11"))
    after_first = target.read_text(encoding="utf-8")
    assert first.backup.name == "notes.md.bak"
    assert first.backup.read_text(encoding="utf-8") == SAMPLE

    second = AE.apply_to_file(target, lambda s: s.replace("return 2", "return 22"))
    assert second.backup.name == "notes.md.bak.1", "a later run must not reuse the .bak name"
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
        "notes.md.bak", "notes.md.bak.1", "notes.md.bak.2"]


def test_a_pre_existing_bak_from_another_tool_is_not_overwritten(tmp_path):
    """A `.bak` this tool did not write is still somebody's only copy of something."""
    target = tmp_path / "notes.md"
    target.write_text(SAMPLE, encoding="utf-8")
    (tmp_path / "notes.md.bak").write_text("SOMEBODY ELSE'S BACKUP\n", encoding="utf-8")
    result = AE.apply_to_file(target, lambda s: s.replace("return 1", "return 11"))
    assert result.backup.name == "notes.md.bak.1"
    assert (tmp_path / "notes.md.bak").read_text(encoding="utf-8") == "SOMEBODY ELSE'S BACKUP\n"


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


def test_cli_refuses_an_absent_anchor_with_exit_one_and_writes_nothing(tmp_path):
    target = tmp_path / "f.py"
    target.write_text(SAMPLE, encoding="utf-8")
    proc = _run("replace", str(target), "--anchor", "absent", "--new-text", "x")
    assert proc.returncode == 1
    assert target.read_text(encoding="utf-8") == SAMPLE


def test_cli_json_stays_parseable_on_a_refusal(tmp_path):
    """A machine-readable mode that emits nothing on failure forces the caller back to parsing
    stderr, which is where the exit code already was."""
    target = tmp_path / "f.py"
    target.write_text(SAMPLE, encoding="utf-8")
    proc = _run("replace", str(target), "--anchor", "absent", "--new-text", "x", "--json")
    assert proc.returncode == 1
    payload = json.loads(proc.stdout)
    assert payload["ok"] is False
    assert payload["command"] == "anchor_edit"


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
