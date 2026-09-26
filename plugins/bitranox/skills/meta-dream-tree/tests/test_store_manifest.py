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
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import store_manifest as SM

TOOL = Path(__file__).resolve().parents[1] / "store_manifest.py"

# chmod cannot make a file unreadable on Windows, and root reads through mode 000.
NO_CHMOD = not hasattr(os, "geteuid") or os.geteuid() == 0


def make_tree(root: Path) -> Path:
    """An anchor (CLAUDE.md + store, as the engine requires) and three levels at different depths."""
    (root / "CLAUDE.md").write_text("anchor\n", encoding="utf-8")
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


# ---- a slug held at two levels, and the read errors that used to pass silently -----------------

def test_removing_one_copy_of_a_slug_held_at_two_levels_is_named(tmp_path):
    """A slug-keyed diff kept one copy per slug, so dropping the first-sorted copy verified IDENTICAL."""
    make_tree(tmp_path)
    line = "- [Dup](mem:dup) - When dup, do dup.\n"
    for lvl in ("elsewhere", "projects/app"):
        with (tmp_path / lvl / "CLAUDE.local.md").open("a", encoding="utf-8") as fh:
            fh.write(line)
    before = SM.derive(tmp_path, scope="tree", start=tmp_path)
    first = sorted(e.level for e in before if e.slug == "dup")[0]
    level_file = Path(first, "CLAUDE.local.md")
    level_file.write_text(level_file.read_text(encoding="utf-8").replace(line, ""),
                          encoding="utf-8")
    d = SM.diff(before, SM.derive(tmp_path, scope="tree", start=tmp_path))
    assert not d.identical
    assert [(e.slug, e.level) for e in d.removed] == [("dup", first)]
    assert d.moved == []


def test_a_unique_slug_that_changed_level_is_still_a_move():
    """Control for the (level, slug) key: one copy before and one after is a move, not add+remove."""
    d = SM.diff([SM.Entry("/t/a", "s", "T", False)], [SM.Entry("/t/b", "s", "T", False)])
    assert [e.level for e in d.moved] == ["/t/b"] and d.added == [] and d.removed == []


def test_a_moved_and_retitled_fact_is_both_moved_and_changed():
    d = SM.diff([SM.Entry("/t/a", "s", "T", False)], [SM.Entry("/t/b", "s", "U", False)])
    assert [e.slug for e in d.moved] == ["s"] and [c.what for c in d.changed] == [["title"]]


@pytest.mark.skipif(NO_CHMOD, reason="needs a non-root POSIX user for chmod 000")
def test_an_unreadable_level_file_refuses_instead_of_omitting_it(tmp_path):
    make_tree(tmp_path)
    locked = tmp_path / "elsewhere" / "CLAUDE.local.md"
    locked.chmod(0)
    try:
        r = run_cli(["backup", "--from", str(tmp_path), "--out", str(tmp_path / "bk"), "--json"],
                    tmp_path)
    finally:
        locked.chmod(0o644)
    assert r.returncode == 2, r.stdout + r.stderr
    env = json.loads(r.stdout)
    assert env["ok"] is False and str(locked) in " ".join(env["skipped"])
    assert not (tmp_path / "bk" / "manifest.json").exists()


def _deleting_lister(victim: Path):
    """A lister that REALLY deletes `victim` just before listing it: a concurrent cache delete
    landing between the parent's listing and the child's, reproduced with the real filesystem."""
    def list_dir(d: Path) -> list[Path]:
        if d == victim:
            shutil.rmtree(victim)
        return list(d.iterdir())
    return list_dir


def test_a_directory_deleted_mid_walk_is_gone_not_unreadable(tmp_path):
    """A directory that no longer exists holds no level. Filed as unreadable, a cache dir deleted
    by another process mid-walk refused the whole backup."""
    make_tree(tmp_path)
    victim = tmp_path / "elsewhere"
    unreadable: list[str] = []
    levels = SM.levels_under(tmp_path, unreadable=unreadable, list_dir=_deleting_lister(victim))
    assert unreadable == []
    assert victim not in levels and tmp_path / "projects" / "app" in levels


def test_a_level_file_deleted_before_it_is_read_is_gone_not_unreadable(tmp_path):
    unreadable: list[str] = []
    assert SM.read_level_text(tmp_path / "gone" / "CLAUDE.local.md", unreadable) is None
    assert unreadable == []


@pytest.mark.skipif(NO_CHMOD, reason="needs a non-root POSIX user for chmod 000")
def test_an_unreadable_directory_under_the_anchor_refuses(tmp_path):
    make_tree(tmp_path)
    locked = tmp_path / "projects"
    locked.chmod(0)
    try:
        r = run_cli(["backup", "--from", str(tmp_path), "--out", str(tmp_path / "bk"), "--json"],
                    tmp_path)
    finally:
        locked.chmod(0o755)
    assert r.returncode == 2, r.stdout + r.stderr
    assert str(locked) in " ".join(json.loads(r.stdout)["skipped"])


def test_a_non_utf8_level_is_a_typed_refusal_not_a_traceback(tmp_path):
    make_tree(tmp_path)
    (tmp_path / "elsewhere" / "CLAUDE.local.md").write_bytes(b"# Memory index\n- \xff\n")
    r = run_cli(["backup", "--from", str(tmp_path), "--out", str(tmp_path / "bk"), "--json"],
                tmp_path)
    assert r.returncode == 2, r.stdout + r.stderr
    assert "Traceback" not in r.stderr
    assert json.loads(r.stdout)["ok"] is False


def test_verify_over_a_non_utf8_level_exits_2(tmp_path):
    make_tree(tmp_path)
    out = tmp_path / "bk"
    assert run_cli(["backup", "--from", str(tmp_path), "--out", str(out)], tmp_path).returncode == 0
    (tmp_path / "elsewhere" / "CLAUDE.local.md").write_bytes(b"# Memory index\n- \xff\n")
    r = run_cli(["verify", "--out", str(out), "--json"], tmp_path)
    assert r.returncode == 2 and "Traceback" not in r.stderr


def test_a_bom_at_the_head_of_a_level_file_is_read(tmp_path):
    make_tree(tmp_path)
    lvl = tmp_path / "elsewhere" / "CLAUDE.local.md"
    lvl.write_bytes(b"\xef\xbb\xbf" + b"- [Other](mem:c-slug) - When other, do other.\n")
    slugs = {e.slug for e in SM.derive(tmp_path, scope="tree", start=tmp_path)}
    assert "c-slug" in slugs


# ---- --out and --from mistakes, and a damaged manifest ------------------------------------------

def test_an_out_dir_inside_the_store_is_refused_and_writes_nothing(tmp_path):
    make_tree(tmp_path)
    before = sorted((tmp_path / ".claude-memory").rglob("*"))
    r = run_cli(["backup", "--from", str(tmp_path),
                 "--out", str(tmp_path / ".claude-memory" / "bk"), "--json"], tmp_path)
    assert r.returncode == 2, r.stdout + r.stderr
    assert sorted((tmp_path / ".claude-memory").rglob("*")) == before


def test_an_existing_dir_that_is_not_a_backup_is_refused_as_out(tmp_path):
    """A re-backup clears its old copies first, so it may only reuse a dir that IS a backup."""
    make_tree(tmp_path)
    out = tmp_path / "someone-elses"
    (out / "levels").mkdir(parents=True)
    (out / "levels" / "keep.txt").write_text("not ours\n", encoding="utf-8")
    r = run_cli(["backup", "--from", str(tmp_path), "--out", str(out), "--json"], tmp_path)
    assert r.returncode == 2
    assert (out / "levels" / "keep.txt").is_file()


def test_a_re_backup_into_the_same_out_leaves_no_stale_level_copy(tmp_path):
    make_tree(tmp_path)
    out = tmp_path / "bk"
    assert run_cli(["backup", "--from", str(tmp_path), "--out", str(out)], tmp_path).returncode == 0
    assert (out / "levels" / "elsewhere" / "CLAUDE.local.md").is_file()
    (tmp_path / "elsewhere" / "CLAUDE.local.md").unlink()
    assert run_cli(["backup", "--from", str(tmp_path), "--out", str(out)], tmp_path).returncode == 0
    assert not (out / "levels" / "elsewhere" / "CLAUDE.local.md").exists()
    assert (out / "levels" / "CLAUDE.local.md").is_file()          # control: the rest re-copied


@pytest.mark.parametrize("payload", ['{"entries": []}', "[]", '{"anchor": "/x", "entries": [1]}',
                                     '{"anchor": "/x", "entries": [{"slug": "s"}]}'])
def test_a_wrong_shape_manifest_exits_2_with_the_envelope(tmp_path, payload):
    out = tmp_path / "bk"
    out.mkdir()
    (out / "manifest.json").write_text(payload, encoding="utf-8")
    r = run_cli(["verify", "--out", str(out), "--json"], tmp_path)
    assert r.returncode == 2, r.stdout + r.stderr
    assert "Traceback" not in r.stderr
    assert json.loads(r.stdout)["ok"] is False


def test_a_nonexistent_from_is_refused_rather_than_climbing(tmp_path):
    make_tree(tmp_path)
    r = run_cli(["backup", "--from", str(tmp_path / "projects" / "appp"), "--scope", "chain",
                 "--out", str(tmp_path / "bk"), "--json"], tmp_path)
    assert r.returncode == 2
    assert not (tmp_path / "bk").exists()


def test_verify_text_output_says_identical_then_names_what_differs(tmp_path):
    make_tree(tmp_path)
    out = tmp_path / "bk"
    assert run_cli(["backup", "--from", str(tmp_path), "--out", str(out)], tmp_path).returncode == 0
    r = run_cli(["verify", "--out", str(out)], tmp_path)
    assert r.returncode == 0 and r.stdout.startswith("IDENTICAL")
    (tmp_path / "elsewhere" / "CLAUDE.local.md").write_text("# Memory index\n", encoding="utf-8")
    r = run_cli(["verify", "--out", str(out)], tmp_path)
    assert r.returncode == 1
    assert "DIFFERS" in r.stdout and "removed  c-slug" in r.stdout


# ---- the anchor is the engine's, and output survives a cp1252 console --------------------------

def test_a_decoy_store_does_not_divert_the_backup(tmp_path):
    """The backup must copy the store the ENGINE reads, not the nearest one below it."""
    deep = make_tree(tmp_path)
    (deep / ".claude-memory" / "facts").mkdir(parents=True)
    (deep / ".claude-memory" / "facts" / "decoy.md").write_text("decoy\n", encoding="utf-8")
    (deep / "CLAUDE.md").write_text("proj\n", encoding="utf-8")
    out = tmp_path / "bk"
    r = run_cli(["backup", "--from", str(deep), "--scope", "chain", "--out", str(out), "--json"],
                tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert Path(manifest["anchor"]) == tmp_path.resolve()
    assert (out / "store" / "facts" / "a-slug.md").is_file()
    assert not (out / "store" / "facts" / "decoy.md").exists()


def test_a_cp1252_stdout_does_not_crash_on_a_non_ascii_path(tmp_path):
    root = tmp_path / "t日本"
    root.mkdir()
    make_tree(root)
    env = dict(os.environ, PYTHONIOENCODING="cp1252")
    env.pop("PYTHONUTF8", None)
    r = subprocess.run([sys.executable, str(TOOL), "backup", "--from", str(root),
                        "--out", str(root / "bk")], capture_output=True, check=False, env=env,
                       cwd=str(tmp_path))
    assert r.returncode == 0, r.stderr.decode("utf-8", "replace")
