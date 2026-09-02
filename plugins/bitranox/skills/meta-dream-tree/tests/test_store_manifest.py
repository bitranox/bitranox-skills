"""Tests for store_manifest.py - back up the in-scope stores and prove nothing was lost.

Every dream and nap owes the same two steps: copy the stores it is about to rewrite, and record
an order-independent manifest it can re-derive and diff at the end. Hand-rolled twice in one
session at two scopes, which is what a jig is for - and the diff half is what makes the
verification contract checkable instead of asserted.

The enumeration is the part that goes wrong. A gitignore-aware grep silently drops the pointer
files (they are gitignored), and a bare walk over-counts: the plugin vendors CLAUDE.local.md
into site-packages, so any unpruned virtualenv turns a vendored copy into an apparent level.
Those two are pinned here rather than left to each re-implementation.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import store_manifest as SM

TOOL = Path(__file__).resolve().parents[1] / "store_manifest.py"


def make_tree(root: Path) -> Path:
    """An anchor with a store and three levels at different depths."""
    (root / ".claude-memory" / "facts").mkdir(parents=True)
    (root / ".claude-memory" / "facts" / "a-slug.md").write_text("body a\n", encoding="utf-8")
    (root / "CLAUDE.local.md").write_text(
        "# Memory index\n- [Top](mem:a-slug) - When top, do top. <!-- bx:pin -->\n",
        encoding="utf-8")
    deep = root / "projects" / "app"
    deep.mkdir(parents=True)
    (deep / "CLAUDE.local.md").write_text(
        "# Memory index\n- [Deep](mem:b-slug) - When deep, do deep.\n", encoding="utf-8")
    other = root / "elsewhere"
    other.mkdir()
    (other / "CLAUDE.local.md").write_text(
        "# Memory index\n- [Other](mem:c-slug) - When other, do other.\n", encoding="utf-8")
    return deep


# ---- the manifest ----------------------------------------------------------------------------

def test_the_manifest_records_level_slug_title_and_pin(tmp_path):
    make_tree(tmp_path)
    entries = SM.derive(tmp_path, scope="tree", start=tmp_path)
    top = [e for e in entries if e.slug == "a-slug"][0]
    assert top.title == "Top" and top.pin is True
    assert [e.pin for e in entries if e.slug == "b-slug"] == [False]


def test_the_manifest_is_order_independent(tmp_path):
    """Two stores holding the same facts must produce the same manifest whatever order the
    pointer lines sit in, or the end-of-run diff reports a spurious change every time a level
    is re-rendered."""
    make_tree(tmp_path)
    level = tmp_path / "CLAUDE.local.md"
    level.write_text("# Memory index\n"
                     "- [Second](mem:z-slug) - When z, do z.\n"
                     "- [Top](mem:a-slug) - When top, do top. <!-- bx:pin -->\n",
                     encoding="utf-8")
    first = SM.manifest_key(SM.derive(tmp_path, scope="tree", start=tmp_path))
    level.write_text("# Memory index\n"
                     "- [Top](mem:a-slug) - When top, do top. <!-- bx:pin -->\n"
                     "- [Second](mem:z-slug) - When z, do z.\n",
                     encoding="utf-8")
    assert SM.manifest_key(SM.derive(tmp_path, scope="tree", start=tmp_path)) == first


def test_tree_scope_sees_every_level_and_chain_scope_only_the_ancestors(tmp_path):
    deep = make_tree(tmp_path)
    tree_slugs = {e.slug for e in SM.derive(tmp_path, scope="tree", start=tmp_path)}
    chain_slugs = {e.slug for e in SM.derive(tmp_path, scope="chain", start=deep)}
    assert tree_slugs == {"a-slug", "b-slug", "c-slug"}
    # `elsewhere` is a sibling of the starting level, not an ancestor, so a nap must not see it.
    assert chain_slugs == {"a-slug", "b-slug"}


def test_a_vendored_copy_under_any_virtualenv_is_not_a_level(tmp_path):
    """`.venv-win`, `.venv-3.13`, `venv-<user>` and `venv_<project>` are all real names, and the
    plugin vendors CLAUDE.local.md into site-packages. An exact-match prune covers none of them,
    so the manifest would record levels nobody can edit and the end-of-run diff would be noise."""
    make_tree(tmp_path)
    for venv in (".venv", ".venv-win", ".venv-3.13", "venv-alice", "venv_thing"):
        vendored = tmp_path / venv / "lib" / "site-packages" / "pkg"
        vendored.mkdir(parents=True)
        (vendored / "CLAUDE.local.md").write_text("- [V](mem:vendored) - hook\n",
                                                  encoding="utf-8")
    slugs = {e.slug for e in SM.derive(tmp_path, scope="tree", start=tmp_path)}
    assert "vendored" not in slugs
    assert slugs == {"a-slug", "b-slug", "c-slug"}          # control: real levels still found


def test_deriving_from_a_tree_with_no_store_refuses(tmp_path):
    (tmp_path / "x").mkdir()
    try:
        SM.derive(tmp_path / "x", scope="tree", start=tmp_path / "x")
    except SM.NoAnchor:
        pass
    else:
        raise AssertionError("a tree with no .claude-memory must refuse, not return zero entries")


# ---- the diff, which is the half that makes the contract checkable ----------------------------

def test_an_untouched_tree_verifies_clean(tmp_path):
    make_tree(tmp_path)
    before = SM.derive(tmp_path, scope="tree", start=tmp_path)
    assert SM.diff(before, SM.derive(tmp_path, scope="tree", start=tmp_path)).identical


def test_a_dropped_fact_is_named_by_the_diff(tmp_path):
    make_tree(tmp_path)
    before = SM.derive(tmp_path, scope="tree", start=tmp_path)
    (tmp_path / "elsewhere" / "CLAUDE.local.md").write_text("# Memory index\n", encoding="utf-8")
    d = SM.diff(before, SM.derive(tmp_path, scope="tree", start=tmp_path))
    assert not d.identical
    assert [e.slug for e in d.removed] == ["c-slug"]


def test_an_added_fact_is_named_by_the_diff(tmp_path):
    make_tree(tmp_path)
    before = SM.derive(tmp_path, scope="tree", start=tmp_path)
    with (tmp_path / "elsewhere" / "CLAUDE.local.md").open("a", encoding="utf-8") as fh:
        fh.write("- [New](mem:d-slug) - When new, do new.\n")
    d = SM.diff(before, SM.derive(tmp_path, scope="tree", start=tmp_path))
    assert [e.slug for e in d.added] == ["d-slug"]


def test_a_retitled_or_unpinned_fact_is_a_change_not_a_silent_pass(tmp_path):
    """A slug that survives with a different title or pin is exactly the loss a slug-only
    manifest cannot see - the fact is still listed while what it says has changed."""
    make_tree(tmp_path)
    before = SM.derive(tmp_path, scope="tree", start=tmp_path)
    (tmp_path / "CLAUDE.local.md").write_text(
        "# Memory index\n- [Retitled](mem:a-slug) - When top, do top.\n", encoding="utf-8")
    d = SM.diff(before, SM.derive(tmp_path, scope="tree", start=tmp_path))
    assert not d.identical
    assert [c.slug for c in d.changed] == ["a-slug"]
    assert "title" in d.changed[0].what and "pin" in d.changed[0].what


def test_a_fact_that_moved_level_is_reported_as_moved_not_as_add_plus_remove(tmp_path):
    """A dream MOVES facts on purpose. Reporting one move as an unrelated add and remove makes
    the end-of-run diff unreadable exactly when it is being used."""
    make_tree(tmp_path)
    before = SM.derive(tmp_path, scope="tree", start=tmp_path)
    (tmp_path / "elsewhere" / "CLAUDE.local.md").write_text("# Memory index\n", encoding="utf-8")
    with (tmp_path / "CLAUDE.local.md").open("a", encoding="utf-8") as fh:
        fh.write("- [Other](mem:c-slug) - When other, do other.\n")
    d = SM.diff(before, SM.derive(tmp_path, scope="tree", start=tmp_path))
    assert [m.slug for m in d.moved] == ["c-slug"]
    assert d.added == [] and d.removed == []


# ---- backup + CLI ------------------------------------------------------------------------------

def run_cli(args, cwd):
    return subprocess.run([sys.executable, str(TOOL), *args], capture_output=True, text=True,
                          encoding="utf-8", check=False, cwd=str(cwd))


def test_backup_copies_the_store_and_the_level_files_and_writes_a_manifest(tmp_path):
    make_tree(tmp_path)
    out = tmp_path / "bk"
    r = run_cli(["backup", "--from", str(tmp_path), "--scope", "tree", "--out", str(out),
                 "--json"], tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    assert (out / "manifest.json").is_file()
    assert (out / "store" / "facts" / "a-slug.md").is_file()
    assert json.loads(r.stdout)["data"]["entries"] == 3


def test_verify_exits_1_and_names_what_changed(tmp_path):
    make_tree(tmp_path)
    out = tmp_path / "bk"
    assert run_cli(["backup", "--from", str(tmp_path), "--out", str(out)], tmp_path).returncode == 0
    (tmp_path / "elsewhere" / "CLAUDE.local.md").write_text("# Memory index\n", encoding="utf-8")
    r = run_cli(["verify", "--out", str(out), "--json"], tmp_path)
    assert r.returncode == 1
    env = json.loads(r.stdout)
    assert env["ok"] is False
    assert env["data"]["removed"][0]["slug"] == "c-slug"


def test_verify_exits_0_on_an_untouched_tree(tmp_path):
    make_tree(tmp_path)
    out = tmp_path / "bk"
    assert run_cli(["backup", "--from", str(tmp_path), "--out", str(out)], tmp_path).returncode == 0
    assert run_cli(["verify", "--out", str(out), "--json"], tmp_path).returncode == 0


def test_backup_refuses_an_empty_scope_rather_than_writing_a_manifest_of_nothing(tmp_path):
    """A manifest of zero entries verifies clean against anything, so it is worse than no
    manifest: it reports a passing contract while covering nothing."""
    (tmp_path / ".claude-memory" / "facts").mkdir(parents=True)
    r = run_cli(["backup", "--from", str(tmp_path), "--out", str(tmp_path / "bk"), "--json"],
                tmp_path)
    assert r.returncode == 2
    assert json.loads(r.stdout)["ok"] is False


def test_the_cli_emits_json_on_the_error_path(tmp_path):
    r = run_cli(["verify", "--out", str(tmp_path / "absent"), "--json"], tmp_path)
    assert r.returncode == 2
    assert "Traceback" not in r.stderr
    assert json.loads(r.stdout)["ok"] is False


def test_a_backup_written_inside_the_tree_does_not_become_part_of_the_scope(tmp_path):
    """The backup copies every level file. Written under the anchor - the obvious place - those
    copies sit INSIDE the scope, so the next walk finds them and verify reports the whole tree
    as moved. The tool would break exactly the check it exists to perform, and it would do so
    on a clean tree, which reads as the tree being wrong rather than the tool.

    Measured while building this: 2 of 15 tests failed this way before the exclusion landed.
    """
    make_tree(tmp_path)
    out = tmp_path / "inside-the-tree"
    assert run_cli(["backup", "--from", str(tmp_path), "--out", str(out)], tmp_path).returncode == 0
    copied = list((out / "levels").rglob("CLAUDE.local.md"))
    assert copied, "control: the backup must actually have copied level files inside the anchor"
    assert run_cli(["verify", "--out", str(out), "--json"], tmp_path).returncode == 0
