"""Tests for `--hook-file` on `add` and `--scope-file` on `set-scope`.

Only the BODY could come from a file. A hook runs to 500 chars and a scope descriptor to ~120
words, so both were routinely passed as `--hook "$(cat f)"` - a command substitution in
self-authored prose, which the shipped shell-prefix-selfref-guard denies (it cannot tell a benign
`cat` from prose that executes). Worse, that denial discards the WHOLE pending command, so a
heredoc writing the file in the same call dies with it and the next call fails on a missing input,
pointing at the wrong cause.

The load-bearing parts: the file variant reaches the SAME validation the inline flag does (hook cap
and trigger warnings are computed from the resolved text, not from `args.hook`), and neither flag
is silently optional - a call passing neither is refused with a message naming both. All content
ASCII.
"""

from pathlib import Path

import pytest

import memory_engine as E
import uuid_store as us

HOOK = "When the resolved hook comes from a file, apply the same caps as the inline flag."
SCOPE = "WHAT: a level\nSTACK: none\nCHILDREN:\n- x/: y\nPLACE-HERE: a\nPLACE-ELSEWHERE: b"


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    h.mkdir(exist_ok=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


def _tree(tmp_path):
    """anchor -> proj, both CLAUDE.md-bearing rungs; central store at the anchor."""
    anchor = tmp_path / "tree"
    proj = anchor / "proj"
    proj.mkdir(parents=True)
    for d in (anchor, proj):
        (d / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (anchor / us.STORE_DIRNAME).mkdir()
    return str(anchor), str(proj)


def _scope_at(level):
    scope, _pointers = us.parse_pointer_index((Path(level) / "CLAUDE.local.md").read_text(encoding="utf-8"))
    return scope


def _hook_at(level, slug):
    _scope, pointers = us.parse_pointer_index((Path(level) / "CLAUDE.local.md").read_text(encoding="utf-8"))
    return next(p.hook for p in pointers if p.slug == slug)


def test_add_reads_the_hook_from_a_file(tmp_path, capsys):
    """--hook-file puts the file's text in the pointer line, same as --hook would."""
    _anchor, proj = _tree(tmp_path)
    hf = tmp_path / "hook.txt"
    hf.write_text(HOOK + "\n", encoding="utf-8")

    rc = E.main(["add", "--proj", proj, "--title", "T", "--hook-file", str(hf),
                 "--body", "b", "--slug", "s-hookfile"])

    assert rc == 0
    assert _hook_at(proj, "s-hookfile") == HOOK


def test_add_refuses_when_neither_hook_flag_is_given(tmp_path, capsys):
    """Making --hook optional must not make the hook optional: refuse, naming both flags."""
    _anchor, proj = _tree(tmp_path)

    rc = E.main(["add", "--proj", proj, "--title", "T", "--body", "b", "--slug", "s-nohook"])

    assert rc != 0
    err = capsys.readouterr().out + capsys.readouterr().err
    assert "--hook" in err and "--hook-file" in err


def test_hook_file_is_subject_to_the_hard_cap(tmp_path, capsys):
    """A file is not a bypass: an over-cap hook is refused whichever flag delivered it."""
    _anchor, proj = _tree(tmp_path)
    hf = tmp_path / "long.txt"
    hf.write_text("When " + ("x" * (us.HOOK_HARD_MAX + 50)), encoding="utf-8")

    rc = E.main(["add", "--proj", proj, "--title", "T", "--hook-file", str(hf),
                 "--body", "b", "--slug", "s-toolong"])

    assert rc != 0
    assert "refused" in capsys.readouterr().out


def test_set_scope_reads_the_scope_from_a_file(tmp_path):
    """--scope-file writes the level's scope descriptor, same as --scope would."""
    _anchor, proj = _tree(tmp_path)
    sf = tmp_path / "scope.txt"
    sf.write_text(SCOPE + "\n", encoding="utf-8")

    rc = E.main(["set-scope", "--proj", proj, "--scope-file", str(sf)])

    assert rc == 0
    assert "PLACE-ELSEWHERE: b" in _scope_at(proj)


def test_set_scope_refuses_when_neither_scope_flag_is_given(tmp_path, capsys):
    """Same guard on the other verb - and the refusal scaffolds NOTHING.

    set-scope calls ensure_level before writing, so resolving the argument after that would leave a
    CLAUDE.local.md behind on a rejected call. The refusal is checked first, which makes it atomic.
    """
    _anchor, proj = _tree(tmp_path)

    rc = E.main(["set-scope", "--proj", proj])

    assert rc != 0
    out = capsys.readouterr().out
    assert "--scope" in out and "--scope-file" in out
    assert not (Path(proj) / "CLAUDE.local.md").exists()


def test_a_missing_hook_file_fails_with_the_path(tmp_path, capsys):
    """A typo'd path must say which file, not raise a bare traceback."""
    _anchor, proj = _tree(tmp_path)

    rc = E.main(["add", "--proj", proj, "--title", "T", "--hook-file",
                 str(tmp_path / "nope.txt"), "--body", "b", "--slug", "s-missing"])

    assert rc != 0
    assert "nope.txt" in capsys.readouterr().out
