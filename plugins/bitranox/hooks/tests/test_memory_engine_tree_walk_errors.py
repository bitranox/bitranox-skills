"""The tree walk must not answer "fewer levels" when it could not look.

`curated_levels_under` is THE walk behind check-tree, relocate's dangling-ref guard and every
"does any other level point at this slug" question. An os.walk with no onerror skips a directory it
cannot list and says nothing, so an unreadable subtree read exactly like one holding no levels:
check-tree reported the tree clean and relocate saw no inbound refs to protect. A CLAUDE.local.md
that is not UTF-8 raised a bare UnicodeDecodeError that named no file. Both now raise
`TreeWalkError` naming the path. All content ASCII.
"""

import os
import sys
from pathlib import Path

import pytest

import memory_engine as E


POINTER_BLOCK = """<!-- BITRANOX-MEMORY-INDEX:BEGIN managed by bitranox self-improve; do not hand-edit. -->

## Memory index
- [A fact](mem:a-fact) - When something, do something.
<!-- BITRANOX-MEMORY-INDEX:END -->
"""


@pytest.fixture
def tree(tmp_path, monkeypatch):
    """An anchor with one ordinary level; HOME kept inside tmp_path."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "home"))
    anchor = tmp_path / "tree"
    anchor.mkdir()
    (anchor / "CLAUDE.md").write_text("# tree\n", encoding="utf-8")
    (anchor / "CLAUDE.local.md").write_text(POINTER_BLOCK, encoding="utf-8")
    return anchor


def _level_bytes(d, data):
    d.mkdir(parents=True, exist_ok=True)
    (d / "CLAUDE.local.md").write_bytes(data)
    return d


def test_a_non_utf8_level_file_raises_a_named_error(tree):
    """B3b: a cp1252 save of a CLAUDE.local.md crashed check-tree and relocate with a bare
    UnicodeDecodeError naming nothing."""
    bad = _level_bytes(tree / "sub", POINTER_BLOCK.encode("utf-8") + b"caf\xe9\n")
    with pytest.raises(E.TreeWalkError) as info:
        E.curated_levels_under(str(tree))
    assert str(bad / "CLAUDE.local.md") in str(info.value)
    assert "UTF-8" in str(info.value)


def test_the_same_level_file_saved_as_utf8_is_found(tree):
    """Control: identical text as UTF-8 is an ordinary level."""
    good = _level_bytes(tree / "sub", (POINTER_BLOCK + "caf\u00e9\n").encode("utf-8"))
    found = {Path(p).resolve() for p in E.curated_levels_under(str(tree))}
    assert found == {tree.resolve(), good.resolve()}


def test_a_level_file_with_a_bom_is_found(tree):
    """A BOM is what a Windows editor leaves; it is UTF-8, so it is a level, not an error."""
    bom = _level_bytes(tree / "sub", b"\xef\xbb\xbf" + POINTER_BLOCK.encode("utf-8"))
    assert bom.resolve() in {Path(p).resolve() for p in E.curated_levels_under(str(tree))}


def test_a_non_utf8_file_without_a_block_is_still_an_error(tree):
    """Whether the file carries a block cannot be known from bytes that do not decode, so a
    non-level with a stray byte is refused too rather than guessed at."""
    _level_bytes(tree / "sub", b"notes caf\xe9\n")
    with pytest.raises(E.TreeWalkError):
        E.curated_levels_under(str(tree))


@pytest.mark.skipif(os.name == "nt" or (hasattr(os, "geteuid") and os.geteuid() == 0),
                    reason="POSIX mode bits cannot make a dir unlistable on Windows or for root")
def test_an_unlistable_directory_raises_a_named_error(tree):
    """B3: an unreadable dir was skipped in silence - an undercount that reads as a clean tree."""
    locked = tree / "locked"
    _level_bytes(locked / "inner", POINTER_BLOCK.encode("utf-8"))
    locked.chmod(0)
    try:
        with pytest.raises(E.TreeWalkError) as info:
            E.curated_levels_under(str(tree))
    finally:
        locked.chmod(0o755)
    assert str(locked) in str(info.value)


def test_a_missing_anchor_raises_rather_than_reading_as_an_empty_tree(tmp_path, monkeypatch):
    """The walk's own top failing is the same silent skip: a typo'd anchor read as "no levels"."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "home"))
    with pytest.raises(E.TreeWalkError) as info:
        E.curated_levels_under(str(tmp_path / "absent"))
    assert str(tmp_path / "absent") in str(info.value)


def test_a_readable_tree_still_lists_every_level(tree):
    """Control for the error cases: nothing unreadable, nothing raised, nothing lost."""
    nested = _level_bytes(tree / "a" / "b", POINTER_BLOCK.encode("utf-8"))
    (tree / "plain").mkdir()
    (tree / "plain" / "CLAUDE.local.md").write_text("no block here\n", encoding="utf-8")
    found = {Path(p).resolve() for p in E.curated_levels_under(str(tree))}
    assert found == {tree.resolve(), nested.resolve()}


def test_a_collecting_caller_gets_the_readable_levels_and_the_failed_path(tree):
    """A report (check-tree) asks to collect instead: every readable level, plus each path it
    could not read, and no raise."""
    good = _level_bytes(tree / "good", POINTER_BLOCK.encode("utf-8"))
    bad = _level_bytes(tree / "bad", POINTER_BLOCK.encode("utf-8") + b"caf\xe9\n")
    unreadable = []
    found = {Path(p).resolve() for p in E.curated_levels_under(str(tree), unreadable=unreadable)}
    assert found == {tree.resolve(), good.resolve()}
    assert unreadable == [str(bad / "CLAUDE.local.md")]


def test_a_collecting_caller_of_a_readable_tree_collects_nothing(tree):
    """Control: an empty list back is the healthy answer, not a missing one."""
    unreadable = []
    E.curated_levels_under(str(tree), unreadable=unreadable)
    assert unreadable == []


@pytest.mark.skipif(os.name == "nt" or (hasattr(os, "geteuid") and os.geteuid() == 0),
                    reason="POSIX mode bits cannot make a dir unlistable on Windows or for root")
def test_a_collecting_caller_is_told_about_an_unlistable_directory(tree):
    locked = tree / "locked"
    _level_bytes(locked / "inner", POINTER_BLOCK.encode("utf-8"))
    locked.chmod(0)
    unreadable = []
    try:
        found = E.curated_levels_under(str(tree), unreadable=unreadable)
    finally:
        locked.chmod(0o755)
    assert [Path(p).resolve() for p in found] == [tree.resolve()]
    assert unreadable == [str(locked)]


@pytest.mark.skipif(sys.platform == "win32", reason="symlink creation needs a privilege on Windows")
def test_a_dangling_level_symlink_is_not_a_level_and_not_an_error(tree):
    """A CLAUDE.local.md symlink whose target is gone carries no block; reading it is "not
    there", which is a fact about the tree rather than a failure to read it."""
    (tree / "sub").mkdir()
    (tree / "sub" / "CLAUDE.local.md").symlink_to(tree / "gone.md")
    assert {Path(p).resolve() for p in E.curated_levels_under(str(tree))} == {tree.resolve()}
