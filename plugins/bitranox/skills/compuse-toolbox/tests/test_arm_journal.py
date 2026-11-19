"""Tests for _arm_journal.py - the on-disk restore journal behind mutation_arm.

The journal exists for the kill nothing can catch, so each case builds a REAL journal with
Journal.create, hands it to a process that is really gone (a reaped child) or really running (a
live child), and asks recover() what it does with the files on disk.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import _arm_journal as J

ORIGINAL = 'def f():\n    return "zero"\n'
MUTANT = 'def f():\n    return "ZERO"\n'


@pytest.fixture
def root(tmp_path: Path) -> Path:
    return tmp_path / "journals"


@pytest.fixture
def src(tmp_path: Path) -> Path:
    path = tmp_path / "src.py"
    path.write_bytes(ORIGINAL.encode("utf-8"))
    return path


def _dead_pid() -> int:
    proc = subprocess.Popen([sys.executable, "-c", "pass"])
    proc.wait()
    return proc.pid


def _journal_as(journal: J.Journal, pid: int) -> Path:
    """Hand the journal to another process: recovery reads the owner from the directory name."""
    moved = journal.directory.with_name(f"{pid}-{journal.directory.name.split('-', 1)[1]}")
    journal.directory.rename(moved)
    return moved


def _killed_run(src: Path, root: Path) -> Path:
    """What a SIGKILL mid-arm leaves: a journal of a dead process and the mutant on disk."""
    journal = J.Journal.create({src: MUTANT.encode("utf-8")}, root)
    # The exact bytes the journal recorded, as mutation_arm writes them (newline=""): a text-mode
    # write turns each \n into \r\n on Windows, and a file matching neither its original nor the
    # recorded mutant is a conflict, never restored.
    src.write_bytes(MUTANT.encode("utf-8"))
    return _journal_as(journal, _dead_pid())


def test_a_live_pid_is_alive_and_a_reaped_one_is_not() -> None:
    assert J.pid_alive(os.getpid())
    assert not J.pid_alive(_dead_pid())
    assert not J.pid_alive(0)


def test_the_journal_is_durable_before_create_returns(src: Path, root: Path) -> None:
    journal = J.Journal.create({src: MUTANT.encode("utf-8")}, root)
    assert (journal.directory / J.JOURNAL_FILE).is_file()
    (entry,) = journal.entries
    assert journal.original(entry).read_text(encoding="utf-8") == ORIGINAL
    assert entry["path"] == str(src.resolve())


def test_the_root_comes_from_the_environment_override(tmp_path: Path,
                                                    monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(J.STATE_DIR_ENV, str(tmp_path / "x"))
    assert J.journal_root() == tmp_path / "x"


def test_a_killed_runs_mutant_is_restored_and_its_journal_removed(src: Path, root: Path) -> None:
    directory = _killed_run(src, root)
    result = J.recover(root)
    assert result.restored == [str(src.resolve())]
    assert src.read_text(encoding="utf-8") == ORIGINAL
    assert not directory.exists()


def test_a_file_edited_after_the_kill_is_a_conflict_and_left_alone(src: Path, root: Path) -> None:
    directory = _killed_run(src, root)
    src.write_text(MUTANT + "# edited by hand\n", encoding="utf-8")
    result = J.recover(root)
    assert [c.path for c in result.conflicts] == [str(src.resolve())]
    assert src.read_text(encoding="utf-8").endswith("# edited by hand\n")
    assert directory.exists(), "the copy of the original is the only one left"
    assert result.blocking([src]) and "differs from both" in result.blocking([src])[0]
    assert result.blocking([src.with_name("other.py")]) == []


def test_a_file_already_back_to_its_original_just_drops_the_journal(src: Path, root: Path) -> None:
    directory = _killed_run(src, root)
    src.write_bytes(ORIGINAL.encode("utf-8"))
    result = J.recover(root)
    assert (result.restored, result.conflicts) == ([], [])
    assert not directory.exists()


def test_a_running_owners_journal_is_held_not_restored(src: Path, root: Path) -> None:
    journal = J.Journal.create({src: MUTANT.encode("utf-8")}, root)
    src.write_bytes(MUTANT.encode("utf-8"))
    live = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    try:
        directory = _journal_as(journal, live.pid)
        result = J.recover(root)
    finally:
        live.kill()
        live.wait()
    assert result.held == {str(src.resolve()): live.pid}
    assert src.read_text(encoding="utf-8") == MUTANT, "a live run's mutation is not touched"
    assert directory.exists()
    assert "another mutation_arm run" in result.blocking([src])[0]


def test_a_dead_journal_without_a_record_mutated_nothing_and_is_removed(root: Path) -> None:
    directory = root / f"{_dead_pid()}-abc"
    directory.mkdir(parents=True)
    (directory / "0-src.py").write_text(ORIGINAL, encoding="utf-8")
    J.recover(root)
    assert not directory.exists()


def test_an_unreadable_record_is_reported_never_guessed(root: Path) -> None:
    directory = root / f"{_dead_pid()}-abc"
    directory.mkdir(parents=True)
    (directory / J.JOURNAL_FILE).write_text("{not json", encoding="utf-8")
    assert J.recover(root).unreadable == [str(directory)]
    assert directory.exists()


@pytest.mark.parametrize("original", ["../outside.py", "", None])
def test_a_malformed_entry_makes_the_journal_unreadable_not_partly_applied(
        src: Path, root: Path, original: str | None) -> None:
    """Skipping one bad entry and discarding the rest would lose the copy of a file still
    mutated; a copy name with a path in it would restore from outside the journal."""
    directory = _killed_run(src, root)
    record = directory / J.JOURNAL_FILE
    data = json.loads(record.read_text(encoding="utf-8"))
    data["files"][0]["original"] = original
    record.write_text(json.dumps(data), encoding="utf-8")
    result = J.recover(root)
    assert result.unreadable == [str(directory)] and result.restored == []
    assert src.read_text(encoding="utf-8") == MUTANT


def test_a_directory_that_is_not_a_journal_is_ignored(root: Path) -> None:
    stray = root / "notes"
    stray.mkdir(parents=True)
    assert J.recover(root) == J.Recovery()
    assert stray.exists()


def test_a_missing_root_recovers_nothing(tmp_path: Path) -> None:
    assert J.recover(tmp_path / "absent") == J.Recovery()


def test_an_unwritable_root_names_the_override(src: Path, tmp_path: Path) -> None:
    blocker = tmp_path / "file-not-dir"
    blocker.write_text("x", encoding="utf-8")
    with pytest.raises(OSError, match=J.STATE_DIR_ENV):
        J.Journal.create({src: MUTANT.encode("utf-8")}, blocker / "journals")
