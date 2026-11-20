"""Another session's write placed at one exact point inside move, relocate, rename, the inbound-ref
rewrite and `add`'s commit: after the verb read the fact, before it writes.

The real-process races in test_memory_engine_writer_races.py show the lost update happens; these
pin each outcome deterministically. A profile function runs the other write once, when the verb
first calls a named function of its own. It replaces nothing; it only places the write there.

What each verb must do with it: keep the other write (its hook, title, pin or prose), and refuse,
writing nothing, when the other write took the fact's line away - never put the line back.
All content ASCII.
"""

import sys
from pathlib import Path

import pytest

import memory_engine as E
import self_improve_signals as sig
import uuid_store as us


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    h.mkdir(exist_ok=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


def _tree(root, *levels):
    root.mkdir(parents=True)
    (root / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (root / us.STORE_DIRNAME).mkdir()
    out = []
    for rel in levels:
        d = root / rel
        d.mkdir(parents=True, exist_ok=True)
        (d / "CLAUDE.md").write_text("x\n", encoding="utf-8")
        out.append(str(d))
    return out


def _line(level, slug):
    local = Path(level) / "CLAUDE.local.md"
    if not local.is_file():
        return None
    return next((p for p in us.parse_pointer_index(local.read_text(encoding="utf-8"))[1]
                 if p.slug == slug), None)


def _unlocked(level):
    return not Path(str(sig.claude_local_md_path(level)) + ".lock").exists()


def _run_with(at, action, call, level=None):
    """Run `call()`; the first time it calls a function named `at` (with `level`'s lock not held,
    when `level` is given), run `action()` first. Returns (result, fired)."""
    fired = []

    def profile(frame, event, _arg):
        if fired or event != "call" or frame.f_code.co_name != at:
            return
        if level is not None and not _unlocked(level):
            return
        fired.append(True)
        sys.setprofile(None)
        action()

    previous = sys.getprofile()
    sys.setprofile(profile)
    try:
        return call(), bool(fired)
    finally:
        sys.setprofile(previous)


def _add(level, n, slug="fact", **kw):
    return E.add_or_update_entry(level, "T%d" % n, "When racing %d, keep it." % n,
                                 body="prose %d" % n, slug=slug, **kw)


def _prose(path):
    return Path(path).read_text(encoding="utf-8").split("---")[-1].strip()


# ---- move ---------------------------------------------------------------------------------------

def _move_tree(tmp_path):
    sub, top = _tree(tmp_path / "t", "proj/sub", "proj")
    _add(sub, 0)
    return sub, top


def test_move_keeps_an_add_that_landed_after_its_read(tmp_path):
    sub, top = _move_tree(tmp_path)
    rep, fired = _run_with("_move_cap_refusal", lambda: _add(sub, 1),
                           lambda: E.move_entry(sub, top, "fact"))
    assert fired and rep.moved, rep.refused
    assert (_line(top, "fact").title, _line(top, "fact").hook) == ("T1", "When racing 1, keep it.")
    assert _line(sub, "fact") is None


def test_move_keeps_a_pin_set_after_its_read(tmp_path):
    sub, top = _move_tree(tmp_path)
    rep, fired = _run_with("_move_cap_refusal", lambda: _add(sub, 0, pin=True),
                           lambda: E.move_entry(sub, top, "fact"))
    assert fired and rep.moved, rep.refused
    assert _line(top, "fact").pin is True


def test_move_refuses_a_line_dropped_after_its_read_and_writes_nothing(tmp_path):
    sub, top = _move_tree(tmp_path)
    rep, fired = _run_with("_move_cap_refusal", lambda: E.drop_pointer(sub, "fact"),
                           lambda: E.move_entry(sub, top, "fact"))
    assert fired and rep.moved is False and "left" in rep.refused, rep
    assert _line(top, "fact") is None and _line(sub, "fact") is None


# ---- relocate -----------------------------------------------------------------------------------

def _relocate_trees(tmp_path):
    (src,) = _tree(tmp_path / "a", "proj")
    (dst,) = _tree(tmp_path / "b", "proj")
    _add(src, 0)
    return src, dst


def test_relocate_carries_an_add_that_landed_after_its_read(tmp_path):
    src, dst = _relocate_trees(tmp_path)
    rep, fired = _run_with("_move_cap_refusal", lambda: _add(src, 1),
                           lambda: E.relocate_entry(src, dst, "fact"))
    assert fired and rep.relocated, rep.refused
    assert _line(dst, "fact").hook == "When racing 1, keep it."
    assert _prose(us.body_path(str(tmp_path / "b"), "fact")) == "prose 1"


def test_relocate_refuses_a_line_dropped_after_its_read_and_writes_nothing(tmp_path):
    src, dst = _relocate_trees(tmp_path)
    rep, fired = _run_with("_move_cap_refusal", lambda: E.drop_pointer(src, "fact"),
                           lambda: E.relocate_entry(src, dst, "fact"))
    assert fired and rep.relocated is False and "left" in rep.refused, rep
    assert _line(dst, "fact") is None
    assert not us.body_path(str(tmp_path / "b"), "fact").exists()
    assert us.body_path(str(tmp_path / "a"), "fact").is_file(), "the source body stays live"


# ---- rename -------------------------------------------------------------------------------------

def test_rename_carries_an_add_that_landed_after_its_read(tmp_path):
    (proj,) = _tree(tmp_path / "t", "proj")
    _add(proj, 0)
    rep, fired = _run_with("_line_growth_refusal", lambda: _add(proj, 1),
                           lambda: E.rename_entry(proj, "fact", "renamed"))
    assert fired and rep.renamed, rep.refused
    assert _line(proj, "renamed").hook == "When racing 1, keep it."
    assert _prose(us.body_path(str(tmp_path / "t"), "renamed")) == "prose 1"


def test_rename_refuses_a_line_dropped_after_its_read_and_writes_nothing(tmp_path):
    (proj,) = _tree(tmp_path / "t", "proj")
    _add(proj, 0)
    rep, fired = _run_with("_line_growth_refusal", lambda: E.drop_pointer(proj, "fact"),
                           lambda: E.rename_entry(proj, "fact", "renamed"))
    assert fired and rep.renamed is False and "left" in rep.refused, rep
    assert _line(proj, "renamed") is None
    assert not us.body_path(str(tmp_path / "t"), "renamed").exists()


def test_rename_renames_a_duplicate_line_at_another_level_too(tmp_path):
    """The duplicate at a second level is swapped under its own lock, with its own fields."""
    top, proj = _tree(tmp_path / "t", "proj", "proj/sub")
    _add(top, 0)
    us.add_pointer(proj, "fact", "Other title", "When racing 0, keep it.")
    rep = E.rename_entry(top, "fact", "renamed")
    assert rep.renamed, rep.refused
    assert (_line(proj, "renamed").title, _line(proj, "fact")) == ("Other title", None)
    assert any("ALSO pointed at" in w for w in rep.warnings), rep.warnings
    assert not us.body_path(str(tmp_path / "t"), "fact").exists()


# ---- the inbound-ref rewrite --------------------------------------------------------------------

def test_the_ref_rewrite_keeps_a_citer_add_that_landed_during_it(tmp_path):
    (proj,) = _tree(tmp_path / "t", "proj")
    E.add_or_update_entry(proj, "Fact", "When racing, the cited fact.", body="cited", slug="fact")
    E.add_or_update_entry(proj, "Citer", "When racing 0, see [[fact]].",
                          body="prose 0 cites [[fact]].", slug="citer")

    def citer_add():
        E.add_or_update_entry(proj, "Citer", "When racing 1, see [[fact]].",
                              body="prose 1 cites [[fact]].", slug="citer")

    rep, fired = _run_with("_retarget_refs", citer_add,
                           lambda: E.rename_entry(proj, "fact", "renamed"), level=proj)
    assert fired and rep.renamed, rep.refused
    assert "racing 1" in _line(proj, "citer").hook, _line(proj, "citer").hook
    assert _prose(us.body_path(str(tmp_path / "t"), "citer")).startswith("prose 1")


# ---- add's commit -------------------------------------------------------------------------------

def test_add_writes_no_body_for_a_dangling_pointer_at_its_level(tmp_path):
    """A pointer whose body is gone reads as an empty body; the next add at the level must not
    write that as an empty file (the slug would then read as taken by a body with no prose)."""
    (proj,) = _tree(tmp_path / "t", "proj")
    _add(proj, 0)
    us.add_pointer(proj, "dangling", "Dangling", "When dangling, nothing.")
    _add(proj, 1)
    assert not us.body_path(str(tmp_path / "t"), "dangling").exists()
    assert _line(proj, "dangling") is not None, "the dangling line itself is left as it was"


def test_add_never_writes_back_another_fact_s_body(tmp_path):
    """`other` has lines at two levels, so an `add` through the second writes its body under that
    level's lock only. An `add` of a different fact at the first level, holding the first level's
    lock, read `other`'s body before that write and committed it back after."""
    top, sub = _tree(tmp_path / "t", "proj", "proj/sub")
    _add(top, 0)
    _add(top, 0, slug="other")
    us.add_pointer(sub, "other", "T0", "When racing 0, keep it.")
    rep, fired = _run_with("commit_store", lambda: _add(sub, 1, slug="other"),
                           lambda: _add(top, 1))
    assert fired and rep == "fact"
    assert _prose(us.body_path(str(tmp_path / "t"), "other")) == "prose 1"
    assert _prose(us.body_path(str(tmp_path / "t"), "fact")) == "prose 1"
