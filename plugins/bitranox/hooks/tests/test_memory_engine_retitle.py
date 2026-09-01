"""Tests for `memory_engine retitle` and `amend-pinned --title`: correcting a fact's TITLE.

The title is the link text of an always-loaded pointer line, so it is the first thing a session
reads and the cheapest thing to skim. Before this verb it was the one field with no correction
path: `add` demands `--hook`/`--hook-file` on every call, so a title fix meant re-supplying the
500-character hook and risking a transcription drift in the text that actually fires; `rename`
changes the slug and never the title; and `amend-pinned` deliberately kept the stored title, which
left a pinned iron rule - the most-read title in the store - with no path at all.

A retitle touches ONE field of ONE line per level. The body must come back byte-identical, which is
the promise the `add` workaround could not make. All content ASCII.
"""

from pathlib import Path

import pytest

import memory_engine as E
import uuid_store as us


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    h.mkdir(exist_ok=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


def _three_levels(tmp_path):
    """anchor -> mid -> proj, each a CLAUDE.md-bearing rung; central store at the anchor."""
    anchor = tmp_path / "tree"
    mid = anchor / "mid"
    proj = mid / "proj"
    proj.mkdir(parents=True)
    for d in (anchor, mid, proj):
        (d / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (anchor / us.STORE_DIRNAME).mkdir()
    return str(anchor), str(mid), str(proj)


def _pointers(level):
    text = (Path(level) / "CLAUDE.local.md").read_text(encoding="utf-8")
    _scope, pointers = us.parse_pointer_index(text)
    return pointers


def _pointer(level, slug):
    return next(p for p in _pointers(level) if p.slug == slug)


# --------------------------------------------------------------------------------------------
# What a retitle changes, and what it must leave alone
# --------------------------------------------------------------------------------------------


def test_retitle_changes_the_title_and_nothing_else_on_the_pointer(tmp_path):
    _anchor, _mid, proj = _three_levels(tmp_path)
    E.add_or_update_entry(proj, "Stale title", "When testing, do the thing.", body="B")

    rep = E.retitle_entry(proj, "stale-title", "Accurate title")

    assert rep["retitled"] is True and rep["refused"] is None
    ptr = _pointer(proj, "stale-title")
    assert ptr.title == "Accurate title"
    assert ptr.hook == "When testing, do the thing."
    assert ptr.pin is False


def test_the_body_file_is_byte_identical_after_a_retitle(tmp_path):
    """The invariant the `add` workaround cannot promise: a title fix must not touch the body."""
    anchor, _mid, proj = _three_levels(tmp_path)
    E.add_or_update_entry(proj, "Stale title", "When testing, do the thing.", body="the body")
    before = us.body_path(anchor, "stale-title").read_bytes()

    E.retitle_entry(proj, "stale-title", "Accurate title")

    assert us.body_path(anchor, "stale-title").read_bytes() == before


def test_the_slug_is_untouched_so_inbound_refs_still_resolve(tmp_path):
    _anchor, _mid, proj = _three_levels(tmp_path)
    E.add_or_update_entry(proj, "Stale title", "When testing, do the thing.", body="B")

    E.retitle_entry(proj, "stale-title", "Accurate title")

    assert {p.slug for p in _pointers(proj)} == {"stale-title"}


# --------------------------------------------------------------------------------------------
# Refusals
# --------------------------------------------------------------------------------------------


def test_an_unknown_slug_is_refused(tmp_path):
    _anchor, _mid, proj = _three_levels(tmp_path)
    E.add_or_update_entry(proj, "Stale title", "When testing, do the thing.", body="B")

    rep = E.retitle_entry(proj, "no-such-fact", "Accurate title")

    assert rep["retitled"] is False and "not found" in rep["refused"]


def test_a_no_op_retitle_is_refused(tmp_path):
    _anchor, _mid, proj = _three_levels(tmp_path)
    E.add_or_update_entry(proj, "Same title", "When testing, do the thing.", body="B")

    rep = E.retitle_entry(proj, "same-title", "Same title")

    assert rep["retitled"] is False and "same" in rep["refused"]


def test_a_whitespace_only_title_is_refused(tmp_path):
    _anchor, _mid, proj = _three_levels(tmp_path)
    E.add_or_update_entry(proj, "Stale title", "When testing, do the thing.", body="B")

    rep = E.retitle_entry(proj, "stale-title", "   \n  ")

    assert rep["retitled"] is False and "empty" in rep["refused"]
    assert _pointer(proj, "stale-title").title == "Stale title"


def test_a_pinned_fact_is_refused_and_the_message_names_the_deliberate_path(tmp_path):
    """The pin gate exists so an ordinary pass cannot rewrite an iron rule; a title is no exception."""
    _anchor, _mid, proj = _three_levels(tmp_path)
    E.add_or_update_entry(proj, "Iron rule", "When testing, do the thing.", body="B", pin=True)

    rep = E.retitle_entry(proj, "iron-rule", "Accurate iron rule")

    assert rep["retitled"] is False
    assert "amend-pinned" in rep["refused"] and "--title" in rep["refused"]
    assert _pointer(proj, "iron-rule").title == "Iron rule"


def test_a_legacy_pointer_is_refused(tmp_path):
    """A legacy `uuid:` line with no bx:slug token derives its slug FROM the title, so retitling
    one changes its identity. `rename` refuses legacy for the same reason."""
    _anchor, _mid, proj = _three_levels(tmp_path)
    E.add_or_update_entry(proj, "Stale title", "When testing, do the thing.", body="B")
    local = Path(proj) / "CLAUDE.local.md"
    local.write_text(
        local.read_text(encoding="utf-8").replace("](mem:stale-title)", "](uuid:%s)" % ("a" * 36)),
        encoding="utf-8")

    rep = E.retitle_entry(proj, "stale-title", "Accurate title")

    assert rep["retitled"] is False and "legacy" in rep["refused"]


# --------------------------------------------------------------------------------------------
# The tree, not just the level
# --------------------------------------------------------------------------------------------


def test_a_duplicate_pointer_at_another_level_is_retitled_too(tmp_path):
    """Two levels holding different titles for one slug is a state `move` refuses outright, so a
    level-local retitle would arm a DIFFERENT TITLE refusal for whoever moves the fact next."""
    _anchor, mid, proj = _three_levels(tmp_path)
    E.add_or_update_entry(proj, "Stale title", "When testing, do the thing.", body="B")
    us.add_pointer(mid, slug="stale-title", title="Stale title",
                   hook="When testing, do the thing.")

    rep = E.retitle_entry(proj, "stale-title", "Accurate title")

    assert rep["retitled"] is True
    assert _pointer(mid, "stale-title").title == "Accurate title"
    assert any("ALSO" in w for w in rep["warnings"])


def test_after_a_retitle_a_move_is_not_refused_for_a_divergent_title(tmp_path):
    """The integration this exists to protect: retitle leaves the tree movable."""
    _anchor, mid, proj = _three_levels(tmp_path)
    E.add_or_update_entry(proj, "Stale title", "When testing, do the thing.", body="B")
    us.add_pointer(mid, slug="stale-title", title="Stale title",
                   hook="When testing, do the thing.")

    E.retitle_entry(proj, "stale-title", "Accurate title")
    rep = E.move_entry(proj, mid, "stale-title")

    assert rep["refused"] is None, rep["refused"]


# --------------------------------------------------------------------------------------------
# Text that would break a pointer line
# --------------------------------------------------------------------------------------------


def test_a_title_with_brackets_still_parses_back(tmp_path):
    _anchor, _mid, proj = _three_levels(tmp_path)
    E.add_or_update_entry(proj, "Stale title", "When testing, do the thing.", body="B")

    E.retitle_entry(proj, "stale-title", "Use [dev] mode")

    assert _pointer(proj, "stale-title").title == "Use (dev) mode"


def test_a_multiline_title_is_collapsed_to_one_line(tmp_path):
    """A newline in a title would split the pointer line and orphan the fact on the next parse."""
    _anchor, _mid, proj = _three_levels(tmp_path)
    E.add_or_update_entry(proj, "Stale title", "When testing, do the thing.", body="B")

    E.retitle_entry(proj, "stale-title", "First line\nsecond   line")

    assert _pointer(proj, "stale-title").title == "First line second line"
    assert len(_pointers(proj)) == 1


# --------------------------------------------------------------------------------------------
# The CLI
# --------------------------------------------------------------------------------------------


def test_cli_retitle_reports_the_new_title(tmp_path, capsys):
    _anchor, _mid, proj = _three_levels(tmp_path)
    E.add_or_update_entry(proj, "Stale title", "When testing, do the thing.", body="B")

    rc = E.main(["retitle", "--level", proj, "--slug", "stale-title",
                 "--to-title", "Accurate title"])
    out = capsys.readouterr().out

    assert rc == 0, out
    assert "Accurate title" in out and "! refused:" not in out


def test_cli_retitle_refusal_exits_nonzero(tmp_path, capsys):
    _anchor, _mid, proj = _three_levels(tmp_path)
    E.add_or_update_entry(proj, "Iron rule", "When testing, do the thing.", body="B", pin=True)

    rc = E.main(["retitle", "--level", proj, "--slug", "iron-rule", "--to-title", "New"])
    out = capsys.readouterr().out

    assert rc == 1
    assert "! refused:" in out and "amend-pinned" in out


def test_cli_retitle_emits_no_hook_advisory(tmp_path, capsys):
    """A retitle passes no hook, so `add`'s hook advisories must not run - an empty hook trips
    hook_missing_trigger and would print a warning about text this verb never touches."""
    _anchor, _mid, proj = _three_levels(tmp_path)
    E.add_or_update_entry(proj, "Stale title", "When testing, do the thing.", body="B")

    E.main(["retitle", "--level", proj, "--slug", "stale-title", "--to-title", "Accurate title"])
    out = capsys.readouterr().out

    assert "trigger phrase" not in out


# --------------------------------------------------------------------------------------------
# The pinned path
# --------------------------------------------------------------------------------------------


def test_amend_pinned_title_changes_the_title_and_keeps_everything_else(tmp_path, capsys):
    anchor, _mid, proj = _three_levels(tmp_path)
    slug = E.add_or_update_entry(proj, "Stale iron rule", "When testing, do the thing.",
                                 body="the body", pin=True)
    before = us.body_path(anchor, slug).read_bytes()

    rc = E.main(["amend-pinned", "--proj", proj, "--slug", slug, "--title", "Accurate iron rule"])
    out = capsys.readouterr().out

    assert rc == 0, out
    ptr = _pointer(proj, slug)
    assert ptr.title == "Accurate iron rule"
    assert ptr.hook == "When testing, do the thing."
    assert ptr.pin is True, "amend-pinned must not silently unpin the fact"
    assert us.body_path(anchor, slug).read_bytes() == before


def test_amend_pinned_without_a_title_keeps_the_stored_one(tmp_path, capsys):
    """Regression: the title argument is optional, and omitting it must not blank the title."""
    _anchor, _mid, proj = _three_levels(tmp_path)
    slug = E.add_or_update_entry(proj, "Iron rule", "When testing, do the original thing.",
                                 body="B", pin=True)

    rc = E.main(["amend-pinned", "--proj", proj, "--slug", slug,
                 "--hook", "When testing, do the AMENDED thing."])
    out = capsys.readouterr().out

    assert rc == 0, out
    ptr = _pointer(proj, slug)
    assert ptr.title == "Iron rule"
    assert ptr.hook == "When testing, do the AMENDED thing."


def test_amend_pinned_normalises_a_multiline_title(tmp_path, capsys):
    _anchor, _mid, proj = _three_levels(tmp_path)
    slug = E.add_or_update_entry(proj, "Iron rule", "When testing, do the thing.", body="B",
                                 pin=True)

    rc = E.main(["amend-pinned", "--proj", proj, "--slug", slug, "--title", "First\nsecond"])

    assert rc == 0
    assert _pointer(proj, slug).title == "First second"
