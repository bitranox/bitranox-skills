"""Tests that `move` holds the level it moves lines to to the cap render-topics holds every level
to (MAX_RENDER_BLOCK_BYTES): the refusals of render-topics and set-topics that name a move promise
it. A refused move writes nothing, prints `! refused:` and exits 2, names how many bytes the block
would be over, and names a route that works; each route is run here from a cwd outside the tree.
All content ASCII.
"""

import re
import subprocess
import sys
from pathlib import Path

import memory_engine as E
import pytest
import self_improve_signals as sig
import uuid_store as us

CAP = E.MAX_RENDER_BLOCK_BYTES
ENGINE_ROOT = Path(E.__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    h.mkdir(exist_ok=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


def _chain(tmp_path):
    """A tree whose top holds the chain a -> a/b, every level with a descriptor."""
    anchor = tmp_path / "tree"
    anchor.mkdir()
    (anchor / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (anchor / us.STORE_DIRNAME).mkdir()
    assert E.main(["set-scope", "--proj", str(anchor), "--scope", "WHAT: the top"]) == 0
    levels = []
    for rel in ("a", "a/b"):
        level = Path(anchor, *rel.split("/"))
        level.mkdir(parents=True)
        (level / "CLAUDE.md").write_text("x\n", encoding="utf-8")
        assert E.main(["set-scope", "--proj", str(level), "--scope", "WHAT: " + rel]) == 0
        levels.append(str(level))
    return str(anchor), levels[0], levels[1]


def _size(slug, hook_len, pin=False):
    return E._line_size(us.Pointer(slug=slug, title="T", hook="k" * hook_len, pin=pin))


def _plant(level, pointers):
    """Append `pointers` to `level`'s block directly (lines pointing at no body: lines the
    renderer never manages, which a move takes)."""
    local = sig.claude_local_md_path(level)
    text = local.read_text(encoding="utf-8")
    scope, have = us.parse_pointer_index(text)
    local.write_text(us.upsert_pointer_block(text, scope, have + list(pointers)), encoding="utf-8")


def _fill(level, total, prefix="feedback-kept"):
    """Plant lines at `level` totalling exactly `total` bytes, about 1 KB each."""
    start = _bytes(level)
    pointers, left, i = [], total, 0
    while left:
        slug = "%s%05d" % (prefix, i)
        base = _size(slug, 0)
        hook_len = 1000 if left - _size(slug, 1000) >= base + 1 else left - base
        assert hook_len >= 1
        pointers.append(us.Pointer(slug=slug, title="T", hook="k" * hook_len))
        left -= _size(slug, hook_len)
        i += 1
    _plant(level, pointers)
    assert _bytes(level) == start + total


def _bytes(level):
    text = sig.claude_local_md_path(level).read_text(encoding="utf-8")
    return sum(E._line_size(p) for p in us.parse_pointer_index(text)[1])


def _slugs(level):
    text = sig.claude_local_md_path(level).read_text(encoding="utf-8")
    return sorted(p.slug for p in us.parse_pointer_index(text)[1])


def _snapshot(anchor):
    return {str(p): p.read_bytes() for p in sorted(Path(anchor).rglob("*"))
            if p.is_file() and not p.name.endswith(".lock")}


def _run_route(tmp_path, route, *extra):
    outside = tmp_path / "outside"
    outside.mkdir(exist_ok=True)
    script, *args = route.split()
    done = subprocess.run([sys.executable, str(ENGINE_ROOT / script), *args, *extra],
                          cwd=str(outside), capture_output=True, text=True, encoding="utf-8",
                          errors="replace", check=False)
    return done.returncode, done.stdout + done.stderr


MOVING = (("feedback-mv-small", 100), ("feedback-mv-mid", 300), ("feedback-mv-big", 480))


def _moving(level):
    _plant(level, [us.Pointer(slug=slug, title="T", hook="k" * n) for slug, n in MOVING])
    return {slug: _size(slug, n) for slug, n in MOVING}


def test_a_move_that_would_pass_the_cap_is_refused_and_its_route_works(tmp_path, capsys):
    anchor, a, b = _chain(tmp_path)
    sizes = _moving(b)
    room = sizes["feedback-mv-small"] + sizes["feedback-mv-mid"] + 5     # two of the three fit
    _fill(a, CAP - room)
    before = _snapshot(anchor)
    capsys.readouterr()
    # largest first: the count of lines that fit is taken smallest first, whatever the order given
    rc = E.main(["move", "--from-level", b, "--to-level", a, "--slug", *reversed(list(sizes))])
    captured = capsys.readouterr()
    out = captured.out
    assert rc == 2 and out.startswith("! refused: ") and captured.err == "", out
    assert _snapshot(anchor) == before
    over = re.search(r"leave its block at (\d+) bytes, (\d+) bytes over the %d bytes" % CAP, out)
    assert over is not None, out
    assert int(over.group(1)) == CAP - room + sum(sizes.values())
    assert int(over.group(2)) == sum(sizes.values()) - room
    assert "%d bytes are left there" % room in out
    assert "2 of the 3 line(s) fit there, smallest first" in out
    route = re.search(r"(hooks/memory_engine\.py move --from-level \S+ --to-level) <level> "
                      r"--slug <slug>", out)
    assert route is not None and route.group(1).split()[3] == b, out
    rc, said = _run_route(tmp_path, route.group(1), a, "--slug", "feedback-mv-small",
                          "feedback-mv-mid")
    assert rc == 0, said
    rc, said = _run_route(tmp_path, route.group(1), anchor, "--slug", "feedback-mv-big")
    assert rc == 0, said
    assert _slugs(b) == [] and _bytes(a) == CAP - 5 and _slugs(anchor) == ["feedback-mv-big"]


def test_a_full_level_names_where_else_to_move_and_how_to_free_it(tmp_path, capsys):
    anchor, a, b = _chain(tmp_path)
    sizes = _moving(b)
    _fill(a, CAP - 10)                                 # room for no line at all
    before = _snapshot(anchor)
    capsys.readouterr()
    assert E.main(["move", "--from-level", b, "--to-level", a, "--slug", "feedback-mv-small"]) == 2
    out = capsys.readouterr().out
    assert _snapshot(anchor) == before
    assert "None of the lines fits there" in out and "10 bytes are left there" in out
    assert "%d bytes over" % (sizes["feedback-mv-small"] - 10) in out
    routes = re.findall(r"(hooks/memory_engine\.py move --from-level \S+ --to-level) <level>", out)
    assert [r.split()[3] for r in routes] == [b, a], out
    # free room at `a` first, by the second route, then the move goes through
    rc, said = _run_route(tmp_path, routes[1], anchor, "--slug", "feedback-kept00000")
    assert rc == 0, said
    assert E.main(["move", "--from-level", b, "--to-level", a, "--slug", "feedback-mv-small"]) == 0
    # or the other way: another level of the chain, by the first route
    rc, said = _run_route(tmp_path, routes[0], anchor, "--slug", "feedback-mv-mid")
    assert rc == 0, said
    assert max(_bytes(a), _bytes(anchor)) <= CAP


def test_a_move_ending_exactly_at_the_cap_goes_through(tmp_path):
    _anchor, a, b = _chain(tmp_path)
    sizes = _moving(b)
    _fill(a, CAP - sizes["feedback-mv-big"])
    rep = E.move_entry(b, a, "feedback-mv-big")
    assert rep["moved"] is True and rep["refused"] is None and _bytes(a) == CAP


def test_a_down_move_is_held_to_the_cap_too(tmp_path):
    _anchor, a, b = _chain(tmp_path)
    _plant(a, [us.Pointer(slug="feedback-down", title="T", hook="k" * 200)])
    _fill(b, CAP - 50)
    rep = E.move_entry(a, b, "feedback-down")
    assert rep["moved"] is False and "bytes over the %d bytes" % CAP in rep["refused"]
    assert _slugs(a) == ["feedback-down"]


def test_completing_an_interrupted_move_onto_an_over_full_level_is_not_refused(tmp_path):
    """The target already holds the moving line (an add that succeeded before the drop did): the
    move only drops the source line, so the target grows by nothing and the move completes."""
    _anchor, a, b = _chain(tmp_path)
    sizes = _moving(b)
    _fill(a, CAP + 100)
    _plant(a, [us.Pointer(slug="feedback-mv-big", title="T", hook="k" * 480)])
    rep = E.move_entry(b, a, "feedback-mv-big")
    assert rep["moved"] is True and rep["refused"] is None
    assert "feedback-mv-big" not in _slugs(b) and _bytes(a) == CAP + 100 + sizes["feedback-mv-big"]


def test_a_forced_dedup_counts_the_kept_line_in_place_of_the_old_one(tmp_path):
    """--force keeps the longer hook: the target's shorter line is replaced, not kept beside it,
    so a block with room for the difference takes the move."""
    _anchor, a, b = _chain(tmp_path)
    _plant(b, [us.Pointer(slug="feedback-dup", title="T", hook="k" * 400)])
    _plant(a, [us.Pointer(slug="feedback-dup", title="T", hook="k" * 300)])
    _fill(a, CAP - _bytes(a) - 100, prefix="feedback-fill")
    rep = E.move_entry(b, a, "feedback-dup", force=True)
    assert rep["moved"] is True, rep["refused"]
    assert _bytes(a) == CAP and _slugs(b) == []
