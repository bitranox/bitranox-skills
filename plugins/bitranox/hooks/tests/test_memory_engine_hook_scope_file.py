"""Tests for `--hook-file` on `add`, `--scope-file` on `set-scope`, and `--scope-file` on `add`.

Only the BODY could come from a file. A hook runs to 500 chars and a scope descriptor to ~120
words, so both were routinely passed as `--hook "$(cat f)"` - a command substitution in
self-authored prose, which the shipped shell-prefix-selfref-guard denies (it cannot tell a benign
`cat` from prose that executes). Worse, that denial discards the WHOLE pending command, so a
heredoc writing the file in the same call dies with it and the next call fails on a missing input,
pointing at the wrong cause.

The load-bearing parts: the file variant reaches the SAME validation the inline flag does (hook cap
and trigger warnings are computed from the resolved text, not from `args.hook`); for hook and for
`set-scope`'s scope, neither flag is silently optional - a call passing neither is refused with a
message naming both. `add`'s scope is the one exception: it is OPTIONAL there (an ordinary capture
passes no scope flag at all), so passing neither `--scope` nor `--scope-file` must stay silent and
succeed - never routed through the strict "pass one or the other" helper unguarded. All content
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
    # ONE readouterr(): each call DRAINS the capture, so a second call returns empty and
    # the stream it reads is never actually checked. Read both from a single capture.
    captured = capsys.readouterr()
    err = captured.out + captured.err
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


def test_add_with_neither_scope_flag_still_succeeds(tmp_path, capsys):
    """Regression lock for the trap: `add`'s scope is OPTIONAL (unlike `set-scope`'s mandatory
    one), and `add` is called with no scope flag at all on essentially every capture. This must
    keep passing - it fails only if `add`'s scope is later routed through `_text_from_flag_or_file`
    the way `set-scope` needs it (erroring whenever neither flag is given)."""
    _anchor, proj = _tree(tmp_path)

    rc = E.main(["add", "--proj", proj, "--title", "T", "--hook", HOOK,
                 "--body", "b", "--slug", "s-noscope"])

    assert rc == 0
    assert "! refused:" not in capsys.readouterr().out


def test_add_reads_the_scope_from_a_file(tmp_path):
    """--scope-file sets the level's scope descriptor from `add`, same as `set-scope` does, and
    survives a multi-line descriptor (the reason the file form exists at all)."""
    _anchor, proj = _tree(tmp_path)
    sf = tmp_path / "scope.txt"
    sf.write_text(SCOPE + "\n", encoding="utf-8")

    rc = E.main(["add", "--proj", proj, "--title", "T", "--hook", HOOK,
                 "--body", "b", "--slug", "s-scopefile", "--scope-file", str(sf)])

    assert rc == 0
    assert "PLACE-ELSEWHERE: b" in _scope_at(proj)


def test_add_scope_file_unreadable_path_is_a_clean_refusal(tmp_path, capsys):
    """An unreadable --scope-file must exit 1 with `! refused:`, never a traceback."""
    _anchor, proj = _tree(tmp_path)

    rc = E.main(["add", "--proj", proj, "--title", "T", "--hook", HOOK,
                 "--body", "b", "--slug", "s-scopemissing",
                 "--scope-file", str(tmp_path / "nope-scope.txt")])
    out = capsys.readouterr().out

    assert rc == 1
    assert "! refused:" in out
    assert "nope-scope.txt" in out


def test_add_scope_file_wins_over_inline_scope(tmp_path):
    """Matching --body/--body-file and set-scope's own --scope/--scope-file: the file wins when
    both are given."""
    _anchor, proj = _tree(tmp_path)
    sf = tmp_path / "scope.txt"
    sf.write_text(SCOPE + "\n", encoding="utf-8")

    rc = E.main(["add", "--proj", proj, "--title", "T", "--hook", HOOK,
                 "--body", "b", "--slug", "s-scopeboth",
                 "--scope", "WHAT: the inline one, must be ignored", "--scope-file", str(sf)])

    assert rc == 0
    scope = _scope_at(proj)
    assert "PLACE-ELSEWHERE: b" in scope
    assert "the inline one" not in scope
