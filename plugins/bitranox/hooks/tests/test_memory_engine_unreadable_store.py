"""A store file that cannot be read is a named error, and the CLI says so with exit 2.

Two halves of one defect. The level walk (`curated_levels_under`) already raised `TreeWalkError`
for a `CLAUDE.local.md` that is not UTF-8, but the CLI verbs let it escape as a traceback, so the
process exited 1 - which every verb here uses for "refused" or "found something". And the engine's
own re-reads of a level file or a fact body decoded strictly behind an `except OSError` that a
`UnicodeDecodeError` walks straight past, so `read_store` and everything built on it crashed with
an error that named no file. All content ASCII.
"""

import os
from pathlib import Path

import pytest

import memory_engine as E

BLOCK = """<!-- BITRANOX-MEMORY-INDEX:BEGIN managed by bitranox self-improve; do not hand-edit. -->

## Memory index
- [A fact](mem:a-fact) - When something, do something.
<!-- BITRANOX-MEMORY-INDEX:END -->
"""
BODY = ("---\nname: a-fact\ndescription: When something, do something.\nmetadata:\n  type: project\n"
        "---\n\nThe body.\n\n**Why:** w\n\n**How to apply:** h\n")
CP1252 = b"caf\xe9\n"


@pytest.fixture
def tree(tmp_path, monkeypatch):
    """An anchor holding `a-fact`, plus a `sub` level holding `b-fact`; HOME kept in tmp_path."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setattr(Path, "home", staticmethod(lambda: home))
    anchor = tmp_path / "tree"
    facts = anchor / ".claude-memory" / "facts"
    facts.mkdir(parents=True)
    (anchor / "CLAUDE.md").write_text("# tree\n", encoding="utf-8")
    (anchor / "CLAUDE.local.md").write_text(BLOCK, encoding="utf-8")
    (facts / "a-fact.md").write_text(BODY, encoding="utf-8")
    sub = anchor / "sub"
    sub.mkdir()
    (sub / "CLAUDE.md").write_text("# sub\n", encoding="utf-8")
    (sub / "CLAUDE.local.md").write_text(BLOCK.replace("a-fact", "b-fact"), encoding="utf-8")
    (facts / "b-fact.md").write_text(BODY.replace("a-fact", "b-fact"), encoding="utf-8")
    return anchor


def _spoil_level(level):
    """Append a cp1252 byte to a level file: the text is intact, the encoding is not."""
    path = level / "CLAUDE.local.md"
    path.write_bytes(path.read_bytes() + CP1252)
    return path


def _spoil_body(anchor, slug):
    path = anchor / ".claude-memory" / "facts" / (slug + ".md")
    path.write_bytes(path.read_bytes() + CP1252)
    return path


# ---- R1.1: the CLI maps the typed error to exit 2 ------------------------------------------------

CLI_CASES = {
    "lint": lambda a: ["lint", "--tree", str(a)],
    "retitle": lambda a: ["retitle", "--level", str(a), "--slug", "a-fact", "--to-title", "New"],
    "relocate": lambda a: ["relocate", "--from-level", str(a), "--to-level", str(a / "sub"),
                           "--slug", "a-fact"],
    "rename": lambda a: ["rename", "--level", str(a), "--slug", "a-fact", "--to-slug", "a-fact2"],
}


@pytest.mark.parametrize("verb", sorted(CLI_CASES))
def test_an_unreadable_level_makes_the_verb_exit_two_naming_the_file(tree, verb, capsys):
    bad = _spoil_level(tree / "sub")
    assert E.main(CLI_CASES[verb](tree)) == 2
    err = capsys.readouterr().err
    assert str(bad) in err and "UTF-8" in err
    assert "Traceback" not in err


@pytest.mark.parametrize("verb", sorted(CLI_CASES))
def test_control_the_same_tree_saved_as_utf8_runs_the_verb(tree, verb, capsys):
    assert E.main(CLI_CASES[verb](tree)) == 0, capsys.readouterr()


def test_add_beside_an_undecodable_body_exits_two_naming_the_body(tree, capsys):
    """`add` at a level reads every body there; one cp1252 body used to crash it unnamed."""
    bad = _spoil_body(tree, "b-fact")
    code = E.main(["add", "--proj", str(tree / "sub"), "--title", "New fact",
                   "--hook", "When new, do new.", "--body", "New body."])
    assert code == 2
    err = capsys.readouterr().err
    assert str(bad) in err and "UTF-8" in err


# ---- R1.2: the engine's re-reads raise the named error, never a bare decode error ----------------

def test_read_store_names_an_undecodable_level_file(tree):
    bad = _spoil_level(tree / "sub")
    with pytest.raises(E.TreeWalkError) as info:
        E.read_store(str(tree / "sub"))
    assert info.value.path == str(bad)


def test_read_store_names_an_undecodable_body(tree):
    bad = _spoil_body(tree, "b-fact")
    with pytest.raises(E.TreeWalkError) as info:
        E.read_store(str(tree / "sub"))
    assert info.value.path == str(bad)


def test_control_read_store_reads_the_utf8_level_and_a_missing_body_as_empty(tree):
    (tree / ".claude-memory" / "facts" / "b-fact.md").unlink()
    _scope, entries, bodies = E.read_store(str(tree / "sub"))
    assert [e.slug for e in entries] == ["b-fact"] and bodies["b-fact"] == ""


def test_read_store_keeps_a_bom_level_readable(tree):
    """A BOM is UTF-8; it must not turn into an error on the way to closing the decode hole."""
    path = tree / "sub" / "CLAUDE.local.md"
    path.write_bytes(b"\xef\xbb\xbf" + path.read_bytes())
    assert [e.slug for e in E.read_store(str(tree / "sub"))[1]] == ["b-fact"]


def test_existing_slugs_names_an_undecodable_level(tree):
    """Its own re-read can only meet the bad bytes in a race, since the walk decodes first; what
    matters is that the answer is the named error rather than a partial slug set."""
    _spoil_level(tree / "sub")
    with pytest.raises(E.TreeWalkError):
        E._existing_slugs(str(tree))


def test_lint_tree_names_an_undecodable_level(tree):
    bad = _spoil_level(tree / "sub")
    with pytest.raises(E.TreeWalkError) as info:
        E.lint_tree(str(tree))
    assert info.value.path == str(bad)


def test_heal_reports_an_undecodable_level_instead_of_skipping_it(tree):
    """heal is fail-open, so it must not raise - but a level it could not read was dropped from
    the report without a word, which reads exactly like a healthy level."""
    bad = _spoil_level(tree / "sub")
    rep = E.heal(str(tree / "sub"))
    assert [lvl for lvl, _why in rep["unreadable"]] == [str(tree / "sub")]
    assert str(bad) in rep["unreadable"][0][1]
    assert bad.read_bytes().endswith(CP1252)            # nothing was rewritten over it


def test_control_heal_reports_no_unreadable_level_on_a_utf8_tree(tree):
    assert E.heal(str(tree / "sub"))["unreadable"] == []


def test_the_heal_cli_prints_the_unreadable_level(tree, capsys):
    bad = _spoil_level(tree / "sub")
    assert E.main(["heal", "--proj", str(tree / "sub")]) == 0
    out = capsys.readouterr().out
    assert "unreadable" in out and str(bad) in out


@pytest.mark.skipif(os.name == "nt" or (hasattr(os, "geteuid") and os.geteuid() == 0),
                    reason="POSIX mode bits cannot make a file unreadable on Windows or for root")
def test_read_store_names_an_unreadable_level_file_instead_of_reading_it_empty(tree):
    """A level file the process cannot open read as an EMPTY level - every fact at it silently
    absent from whatever asked. The walk already refuses that; the re-read now matches it."""
    path = tree / "sub" / "CLAUDE.local.md"
    path.chmod(0)
    try:
        with pytest.raises(E.TreeWalkError) as info:
            E.read_store(str(tree / "sub"))
    finally:
        path.chmod(0o644)
    assert info.value.path == str(path)


# ---- the files a caller names on the command line ------------------------------------------------

@pytest.mark.parametrize("flag", ["--hook-file", "--body-file"])
def test_an_undecodable_input_file_is_a_refusal_naming_it(tree, tmp_path, flag, capsys):
    """A cp1252 --hook-file or --body-file escaped as a UnicodeDecodeError traceback."""
    bad = tmp_path / "input.txt"
    bad.write_bytes(b"When caf\xe9, do x.\n")
    argv = ["add", "--proj", str(tree), "--title", "New fact", "--hook", "When new, do new.",
            "--body", "New body."]
    argv[argv.index("--hook" if flag == "--hook-file" else "--body")] = flag
    argv[argv.index(flag) + 1] = str(bad)
    assert E.main(argv) == 1
    out = capsys.readouterr().out
    assert "refused" in out and str(bad) in out and "UTF-8" in out


def test_a_hook_file_with_a_bom_stores_no_invisible_first_character(tree, tmp_path):
    """Kept, the BOM rides into the always-loaded pointer line; `strip()` does not remove it."""
    hook_file = tmp_path / "hook.txt"
    hook_file.write_bytes(b"\xef\xbb\xbfWhen new, do new.\n")
    assert E.main(["add", "--proj", str(tree), "--title", "New fact", "--hook-file",
                   str(hook_file), "--body", "New body."]) == 0
    entry = next(e for e in E.read_store(str(tree))[1] if e.slug == "new-fact")
    assert entry.hook == "When new, do new."


# ---- relocate copies a body across trees VERBATIM ------------------------------------------------

def _second_tree(tmp_path):
    other = tmp_path / "other"
    (other / ".claude-memory" / "facts").mkdir(parents=True)
    (other / "CLAUDE.md").write_text("# other\n", encoding="utf-8")
    (other / "CLAUDE.local.md").write_text(BLOCK.replace("a-fact", "c-fact"), encoding="utf-8")
    (other / ".claude-memory" / "facts" / "c-fact.md").write_text(
        BODY.replace("a-fact", "c-fact"), encoding="utf-8")
    return other


def test_a_cross_tree_relocate_keeps_the_body_bytes(tree, tmp_path):
    """The docstring promises the body is copied VERBATIM; a text round-trip turned CRLF into LF."""
    body = tree / ".claude-memory" / "facts" / "a-fact.md"
    raw = BODY.replace("\n", "\r\n").encode("utf-8")
    body.write_bytes(raw)
    other = _second_tree(tmp_path)
    rep = E.relocate_entry(str(tree), str(other), "a-fact")
    assert rep["relocated"], rep
    assert (other / ".claude-memory" / "facts" / "a-fact.md").read_bytes() == raw


def test_a_cross_tree_relocate_onto_an_undecodable_body_refuses_instead_of_crashing(tree, tmp_path):
    other = _second_tree(tmp_path)
    clash = other / ".claude-memory" / "facts" / "a-fact.md"
    clash.write_bytes(BODY.encode("utf-8") + CP1252)
    rep = E.relocate_entry(str(tree), str(other), "a-fact")
    assert not rep["relocated"] and "DIFFERENT body" in rep["refused"]
    assert clash.read_bytes().endswith(CP1252)
