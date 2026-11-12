"""Tests that `move`, `relocate` (within a tree and across trees) and `set-scope` refuse a level
whose path below the tree's anchor crosses a directory every level walk prunes, as `add` does: no
walk would read a line there. Also that a cross-tree `relocate` holds the target level to the
block cap `move` holds it to, and that the levels a `PlacedElsewhere` refusal names come in level
order. Every refusal writes nothing, prints `! refused:` and exits 2. All content ASCII.
"""

import re
import subprocess
import sys
from pathlib import Path

import memory_engine as E
import pytest
import self_improve_signals as sig
import uuid_store as us

HOOK = "When a fact is moved, move it where a walk reads it."
CAP = E.MAX_RENDER_BLOCK_BYTES
ENGINE_ROOT = Path(E.__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    h.mkdir(exist_ok=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


def _tree(tmp_path, name="tree"):
    """A tree whose top and level `a` carry a descriptor, and `feedback-mv` lives at the top."""
    anchor = tmp_path / name
    anchor.mkdir()
    (anchor / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (anchor / us.STORE_DIRNAME).mkdir()
    assert E.main(["set-scope", "--proj", str(anchor), "--scope", "WHAT: the top"]) == 0
    level = anchor / "a"
    level.mkdir()
    (level / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    assert E.main(["set-scope", "--proj", str(level), "--scope", "WHAT: a"]) == 0
    E.add_or_update_entry(str(anchor), title="T", hook=HOOK, body="b", slug="feedback-mv")
    return anchor


def _pruned_target(root, rel=".venv/lib/pkg"):
    target = Path(root, *rel.split("/"))
    target.mkdir(parents=True)
    (target / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    return target


def _snapshot(*roots):
    return {str(p): p.read_bytes() for root in roots for p in sorted(Path(root).rglob("*"))
            if p.is_file() and not p.name.endswith(".lock")}


def _slugs(level):
    text = sig.claude_local_md_path(level).read_text(encoding="utf-8")
    return sorted(p.slug for p in us.parse_pointer_index(text)[1])


def _refused(capsys, argv):
    capsys.readouterr()
    rc = E.main(argv)
    captured = capsys.readouterr()
    assert rc == 2 and captured.out.startswith("! refused: "), captured
    assert "its path crosses '.venv'" in captured.out, captured.out
    return captured.out


def _run_route(tmp_path, route):
    outside = tmp_path / "outside"
    outside.mkdir(exist_ok=True)
    script, *args = route.split()
    done = subprocess.run([sys.executable, str(ENGINE_ROOT / script), *args],
                          cwd=str(outside), capture_output=True, text=True, encoding="utf-8",
                          errors="replace", check=False)
    return done.returncode, done.stdout + done.stderr


@pytest.mark.parametrize("verb", ["move", "relocate"])
def test_moving_a_line_under_a_pruned_dir_is_refused_and_its_route_works(tmp_path, capsys, verb):
    anchor = _tree(tmp_path)
    target = _pruned_target(anchor / "a")              # a down move the chain allows
    before = _snapshot(anchor)
    out = _refused(capsys, [verb, "--from-level", str(anchor), "--to-level", str(target),
                            "--slug", "feedback-mv"])
    assert _snapshot(anchor) == before
    route = re.search(r"(hooks/memory_engine\.py %s --from-level \S+ --to-level \S+ --slug "
                      r"feedback-mv)" % verb, out)
    assert route is not None and route.group(1).split()[5] == str(anchor / "a"), out
    rc, said = _run_route(tmp_path, route.group(1))
    assert rc == 0, said
    assert _slugs(anchor / "a") == ["feedback-mv"] and _slugs(anchor) == []


def test_relocating_across_trees_under_a_pruned_dir_is_refused(tmp_path, capsys):
    source = _tree(tmp_path, "source")
    dest = _tree(tmp_path, "dest")
    target = _pruned_target(dest, "build/out")
    E.add_or_update_entry(str(source), title="T", hook=HOOK, body="b", slug="feedback-src")
    before = _snapshot(source, dest)
    capsys.readouterr()
    rc = E.main(["relocate", "--from-level", str(source), "--to-level", str(target),
                 "--slug", "feedback-src"])
    captured = capsys.readouterr()
    assert rc == 2 and "its path crosses 'build'" in captured.out, captured
    assert _snapshot(source, dest) == before


def test_set_scope_under_a_pruned_dir_is_refused(tmp_path, capsys):
    anchor = _tree(tmp_path)
    target = _pruned_target(anchor)
    before = _snapshot(anchor)
    out = _refused(capsys, ["set-scope", "--proj", str(target), "--scope", "WHAT: vendored"])
    assert _snapshot(anchor) == before
    assert not sig.claude_local_md_path(str(target)).exists()
    route = re.search(r"hooks/memory_engine\.py set-scope --proj (\S+) --scope", out)
    assert route is not None and route.group(1) == str(anchor), out


def _fill(level, total):
    """Plant lines at `level` totalling exactly `total` bytes, about 1 KB each, pointing at no
    body (lines a move or relocate never reads)."""
    local = sig.claude_local_md_path(level)
    text = local.read_text(encoding="utf-8")
    scope, have = us.parse_pointer_index(text)
    pointers, left, i = [], total, 0
    while left:
        slug = "feedback-kept%05d" % i
        base = E._line_size(us.Pointer(slug=slug, title="T", hook=""))
        full = E._line_size(us.Pointer(slug=slug, title="T", hook="k" * 1000))
        hook_len = 1000 if left - full >= base + 1 else left - base
        pointers.append(us.Pointer(slug=slug, title="T", hook="k" * hook_len))
        left -= E._line_size(pointers[-1])
        i += 1
    local.write_text(us.upsert_pointer_block(text, scope, have + pointers), encoding="utf-8")


def _block_bytes(level):
    text = sig.claude_local_md_path(level).read_text(encoding="utf-8")
    return sum(E._line_size(p) for p in us.parse_pointer_index(text)[1])


def test_a_cross_tree_relocate_that_would_pass_the_cap_is_refused(tmp_path, capsys):
    source = _tree(tmp_path, "source")
    dest = _tree(tmp_path, "dest")
    target = dest / "a"
    _fill(str(target), CAP - _block_bytes(str(target)) - 10)    # room for no line
    E.add_or_update_entry(str(source / "a"), title="T", hook=HOOK, body="b2", slug="feedback-new")
    before = _snapshot(source, dest)
    capsys.readouterr()
    rc = E.main(["relocate", "--from-level", str(source / "a"), "--to-level", str(target),
                 "--slug", "feedback-new"])
    out = capsys.readouterr().out
    assert rc == 2 and out.startswith("! refused: ") and "bytes over the %d bytes" % CAP in out, out
    assert _snapshot(source, dest) == before
    assert not us.body_path(dest, "feedback-new").exists()
    # it names relocate for taking the line elsewhere, and move for freeing room in its own tree
    take = re.search(r"hooks/memory_engine\.py relocate --from-level (\S+) --to-level <level>", out)
    free = re.search(r"(hooks/memory_engine\.py move --from-level \S+ --to-level) <level>", out)
    assert take is not None and take.group(1) == str(source / "a"), out
    assert free is not None and free.group(1).split()[3] == str(target), out
    rc, said = _run_route(tmp_path, "%s %s --slug feedback-kept00000" % (free.group(1), dest))
    assert rc == 0, said
    rep = E.relocate_entry(str(source / "a"), str(target), "feedback-new")
    assert rep["relocated"] is True, rep["refused"]
    assert _block_bytes(str(target)) <= CAP


def test_a_cross_tree_relocate_that_fits_goes_through(tmp_path):
    source = _tree(tmp_path, "source")
    dest = _tree(tmp_path, "dest")
    E.add_or_update_entry(str(source / "a"), title="T", hook=HOOK, body="b2", slug="feedback-new")
    rep = E.relocate_entry(str(source / "a"), str(dest / "a"), "feedback-new")
    assert rep["relocated"] is True and rep["refused"] is None


def test_placed_elsewhere_names_its_levels_in_level_order(tmp_path):
    top = tmp_path / "t"
    given = [top / "b", top / "a" / "z", top, top / "a"]
    exc = E.PlacedElsewhere("feedback-x", given)
    assert exc.levels == [top, top / "a", top / "a" / "z", top / "b"]
    assert "read at %s, %s, %s, %s." % tuple(exc.levels) in str(exc)
    assert "add --proj %s --slug feedback-x" % top in str(exc)
