"""Tests that `add` of a slug another level of the same tree points at refuses, wherever that level
sits: a sibling, an ancestor or a descendant. Adopting the body at the new level wrote a second
pointer line and overwrote the fact's body with the new one (a sibling and an ancestor did; a
descendant already refused). The refusal writes nothing and names the level that owns the slug;
the upsert at that level still works, and a body no level points at is still adopted. All content
ASCII.
"""

from pathlib import Path

import memory_engine as E
import pytest
import uuid_store as us

SLUG = "reference-shared"


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    h.mkdir(exist_ok=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


@pytest.fixture
def tree(tmp_path):
    """A root with a CLAUDE.md, so every level below shares one tree and one store."""
    anchor = tmp_path / "tree"
    for rel in ("a/sub", "b"):
        (anchor / rel).mkdir(parents=True)
    (anchor / "CLAUDE.md").write_text("# root\n", encoding="utf-8")
    return anchor


def _add(level, body, hook="When x, do y."):
    return E.main(["add", "--proj", str(level), "--slug", SLUG, "--title", "Shared",
                   "--hook", hook, "--body", body, "--type", "reference"])


def _snapshot(anchor):
    return {str(p): p.read_bytes() for p in sorted(Path(anchor).rglob("*"))
            if p.is_file() and not p.name.endswith(".lock")}


def _levels_pointing(anchor):
    return sorted(Path(level).relative_to(anchor).as_posix()
                  for level, _ptr in E._copies_of(str(anchor), SLUG))


@pytest.mark.parametrize("owner,other", [
    ("a", "b"),          # a sibling: the reported repro
    ("a", "."),          # an ancestor of the owner: the tree top
    ("a", "a/sub"),      # a descendant of the owner: refused before, now names the owner
])
def test_add_of_a_slug_another_level_owns_refuses_names_the_owner_and_writes_nothing(
        tree, capsys, owner, other):
    assert _add(tree / owner, "BODY FROM THE OWNER") == 0
    before = _snapshot(tree)
    capsys.readouterr()

    rc = _add(tree / other, "BODY FROM ANOTHER LEVEL", hook="When x, do z.")

    out = capsys.readouterr().out
    assert rc == 2, out
    assert out.startswith("! refused:"), out
    owner_dir = str(tree / owner) if owner != "." else str(tree)
    assert owner_dir in out, out                        # names the level that owns the slug
    assert "--proj %s" % owner_dir in out, out          # and the route that updates it there
    assert _snapshot(tree) == before                    # nothing written, the body included
    assert "BODY FROM THE OWNER" in us.body_path(str(tree), SLUG).read_text(encoding="utf-8")
    assert _levels_pointing(tree) == [owner]            # still exactly one line


def test_the_refusal_is_a_slug_collision_carrying_the_owning_level(tree):
    assert _add(tree / "a", "BODY FROM A") == 0
    with pytest.raises(E.SlugCollision) as exc:
        E.add_or_update_entry(str(tree / "b"), "Shared", "When x, do z.", body="BODY FROM B",
                              type_="reference", slug=SLUG)
    assert isinstance(exc.value, E.SlugOwnedElsewhere)
    assert [Path(p) for p in exc.value.levels] == [tree / "a"]


def test_the_upsert_at_the_owning_level_still_updates_the_fact(tree, capsys):
    assert _add(tree / "a", "BODY FROM A") == 0
    assert _add(tree / "a", "BODY FROM A, UPDATED", hook="When x, do y better.") == 0
    body = us.body_path(str(tree), SLUG).read_text(encoding="utf-8")
    assert "BODY FROM A, UPDATED" in body and "description: When x, do y better." in body
    assert _levels_pointing(tree) == ["a"]


def test_a_body_no_level_points_at_is_still_adopted_at_a_sibling(tree):
    """A dangling body (its only pointer lost) is adopted, not refused: no level owns it."""
    assert _add(tree / "a", "BODY FROM A") == 0
    local = tree / "a" / "CLAUDE.local.md"
    local.write_text("".join(ln for ln in local.read_text(encoding="utf-8").splitlines(True)
                             if "mem:%s)" % SLUG not in ln), encoding="utf-8")
    assert _levels_pointing(tree) == []

    assert _add(tree / "b", "", hook="When x, do y sharpened.") == 0
    assert _levels_pointing(tree) == ["b"]
    assert "BODY FROM A" in us.body_path(str(tree), SLUG).read_text(encoding="utf-8")
