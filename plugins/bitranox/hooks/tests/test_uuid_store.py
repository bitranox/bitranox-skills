"""Tests for uuid_store.py - the central UUID body-store + pointer-index resolver.

The module is additive (the old .claude-bx-selflearning path is untouched), so these tests build
throwaway trees under tmp_path and never touch a real store. They cover: deterministic uuid identity,
sharding + central body paths, cwd-derived anchor resolution, pointer-index render/parse round-trip,
the mtime-neutral writers, and the full cwd->bodies resolver across multiple altitudes and mount points.
"""
import uuid as _uuid

import pytest

import uuid_store as us


# ---- fact_uuid: deterministic, idempotent, collision-free across altitudes ----------------------

def test_fact_uuid_is_deterministic_for_same_inputs():
    a = us.fact_uuid("/tree/proj", "no-em-dashes")
    b = us.fact_uuid("/tree/proj", "no-em-dashes")
    assert a == b


def test_fact_uuid_is_a_valid_uuid_string():
    u = us.fact_uuid("/tree/proj", "some-slug")
    assert str(_uuid.UUID(u)) == u  # round-trips through the UUID parser


def test_fact_uuid_differs_by_slug():
    assert us.fact_uuid("/tree/proj", "slug-a") != us.fact_uuid("/tree/proj", "slug-b")


def test_fact_uuid_differs_by_altitude_so_same_slug_at_two_levels_does_not_collide():
    # two altitudes under one anchor, both carrying a fact "foo": distinct bodies -> distinct uuids
    assert us.fact_uuid("/tree/proj", "foo") != us.fact_uuid("/tree", "foo")


def test_fact_uuid_normalizes_equivalent_paths():
    assert us.fact_uuid("/tree/proj", "s") == us.fact_uuid("/tree/proj/", "s")
    assert us.fact_uuid("/tree/proj", "s") == us.fact_uuid("/tree/./proj", "s")


# ---- sharding + central body paths --------------------------------------------------------------

def test_shard_is_first_two_hex_of_uuid():
    assert us.shard("abcd1234-0000-5000-8000-000000000000") == "ab"


def test_body_path_places_body_under_anchor_claude_memory_facts_shard():
    u = "abcd1234-0000-5000-8000-000000000000"
    p = us.body_path("/tree", u)
    assert p.as_posix() == "/tree/.claude-memory/facts/ab/%s.md" % u


def test_central_facts_dir_is_under_the_anchor():
    assert us.central_facts_dir("/tree").as_posix() == "/tree/.claude-memory/facts"


# ---- anchor resolution from cwd -----------------------------------------------------------------

def _mk(root, rel, *, claude_md=False, store=False):
    d = root / rel
    d.mkdir(parents=True, exist_ok=True)
    if claude_md:
        (d / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    if store:
        (d / us.STORE_DIRNAME).mkdir(exist_ok=True)
    return d


def test_resolve_anchor_picks_topmost_dir_with_claude_md_and_store(tmp_path):
    _mk(tmp_path, "top", claude_md=True, store=True)
    _mk(tmp_path, "top/mid", claude_md=True)
    proj = _mk(tmp_path, "top/mid/proj", claude_md=True)
    assert us.resolve_anchor(str(proj)) == (tmp_path / "top")


def test_resolve_anchor_bootstrap_falls_back_to_topmost_claude_md_when_no_store_yet(tmp_path):
    _mk(tmp_path, "top", claude_md=True)
    proj = _mk(tmp_path, "top/proj", claude_md=True)
    assert us.resolve_anchor(str(proj)) == (tmp_path / "top")


def test_resolve_anchor_is_not_hijacked_by_a_stray_higher_claude_md(tmp_path):
    # a store-bearing anchor lower down must win over a bare CLAUDE.md higher up
    _mk(tmp_path, "outer", claude_md=True)  # stray, no store
    _mk(tmp_path, "outer/anchor", claude_md=True, store=True)
    proj = _mk(tmp_path, "outer/anchor/proj", claude_md=True)
    assert us.resolve_anchor(str(proj)) == (tmp_path / "outer" / "anchor")


def test_resolve_anchor_returns_none_when_no_claude_md_anywhere(tmp_path):
    proj = _mk(tmp_path, "a/b/c")
    assert us.resolve_anchor(str(proj)) is None


# ---- pointer-index render / parse round-trip ----------------------------------------------------

def test_render_then_parse_round_trips_pointers_and_scope():
    ptrs = [
        us.Pointer(uuid="11111111-0000-5000-8000-000000000000", title="Root cause",
                   hook="fix the root, never a patch", source={"prov:x"}, pin=True),
        us.Pointer(uuid="22222222-0000-5000-8000-000000000000", title="No em-dashes",
                   hook="ASCII only", source={"a", "b"}, pin=False),
    ]
    block = us.render_pointer_index("what this level is for", ptrs)
    scope, got = us.parse_pointer_index(block)
    assert scope == "what this level is for"
    assert [(p.uuid, p.title, p.hook, sorted(p.source), p.pin) for p in got] == [
        ("11111111-0000-5000-8000-000000000000", "Root cause", "fix the root, never a patch", ["prov:x"], True),
        ("22222222-0000-5000-8000-000000000000", "No em-dashes", "ASCII only", ["a", "b"], False),
    ]


def test_pointer_line_uses_uuid_scheme_not_a_filesystem_path():
    block = us.render_pointer_index("", [us.Pointer(uuid="33333333-0000-5000-8000-000000000000",
                                                    title="T", hook="h")])
    assert "(uuid:33333333-0000-5000-8000-000000000000)" in block
    assert ".claude-memory" not in block  # mount-independent: no baked path


def test_parse_ignores_non_pointer_lines():
    scope, ptrs = us.parse_pointer_index("# Memory index\n\nsome prose\n- not a pointer\n")
    assert ptrs == []


# ---- splicing the managed block into a CLAUDE.local.md ------------------------------------------

def test_upsert_pointer_block_adds_a_fenced_block_to_empty_text():
    out = us.upsert_pointer_block("", "scope here",
                                  [us.Pointer(uuid="44444444-0000-5000-8000-000000000000", title="T", hook="h")])
    assert us.INDEX_BEGIN in out and us.INDEX_END in out
    assert "(uuid:44444444-0000-5000-8000-000000000000)" in out


def test_upsert_pointer_block_replaces_an_existing_block_and_preserves_surrounding_text(tmp_path):
    first = us.upsert_pointer_block("# my notes\n\nkeep me\n", "s1",
                                    [us.Pointer(uuid="55555555-0000-5000-8000-000000000000", title="A", hook="h")])
    assert "keep me" in first
    second = us.upsert_pointer_block(first, "s2",
                                     [us.Pointer(uuid="66666666-0000-5000-8000-000000000000", title="B", hook="h")])
    assert "keep me" in second                       # surrounding text survives
    assert second.count(us.INDEX_BEGIN) == 1         # exactly one managed block
    assert "(uuid:55555555-0000-5000-8000-000000000000)" not in second  # old pointers replaced
    assert "(uuid:66666666-0000-5000-8000-000000000000)" in second


# ---- mtime-neutral writers ----------------------------------------------------------------------

def test_write_if_changed_writes_then_is_a_noop(tmp_path):
    p = tmp_path / "sub" / "f.md"
    assert us.write_if_changed(p, "hello\n") is True
    assert p.read_text(encoding="utf-8") == "hello\n"
    assert us.write_if_changed(p, "hello\n") is False   # identical -> no write


def test_put_body_writes_to_the_sharded_central_path(tmp_path):
    u = "77777777-0000-5000-8000-000000000000"
    assert us.put_body(str(tmp_path), u, "BODY") is True
    assert (tmp_path / ".claude-memory" / "facts" / "77" / (u + ".md")).read_text(encoding="utf-8") == "BODY\n"


def test_add_pointer_upserts_a_pointer_into_the_altitude_claude_local_md(tmp_path):
    (tmp_path / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    u = us.add_pointer(str(tmp_path), uuid="88888888-0000-5000-8000-000000000000",
                       title="Fact", hook="a hook", source={"s"}, scope_default="lvl scope")
    assert u == "88888888-0000-5000-8000-000000000000"
    local = (tmp_path / "CLAUDE.local.md").read_text(encoding="utf-8")
    assert "(uuid:88888888-0000-5000-8000-000000000000)" in local
    scope, ptrs = us.parse_pointer_index(local)
    assert scope == "lvl scope"
    assert ptrs[0].title == "Fact" and ptrs[0].hook == "a hook"


# ---- the full resolver: cwd -> bodies, across altitudes and mount-independent -------------------

def _build_tree(prefix):
    """A 3-altitude tree with a central UUID store at the anchor and pointers at each level.
    Returns (proj_dir, {uuid: expected_body})."""
    anchor = prefix / "root"
    mid = anchor / "pub"
    proj = mid / "proj"
    for d in (anchor, mid, proj):
        d.mkdir(parents=True, exist_ok=True)
        (d / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (anchor / us.STORE_DIRNAME).mkdir(exist_ok=True)   # anchor carries the central store
    bodies = {}
    for level, slug in ((anchor, "root-fact"), (mid, "mid-fact"), (proj, "proj-fact")):
        u = us.fact_uuid(str(level), slug)
        body = "BODY_%s" % slug
        us.put_body(str(anchor), u, body)
        us.add_pointer(str(level), uuid=u, title=slug, hook="h", source={"x"})
        bodies[u] = body
    return proj, bodies


def test_resolve_collects_all_bodies_from_cwd_up_to_anchor(tmp_path):
    proj, bodies = _build_tree(tmp_path / "mountA")
    got = {r.uuid: r.body for r in us.resolve(str(proj))}
    assert got == bodies                              # every altitude contributed; none missing


def test_resolve_is_mount_independent(tmp_path):
    projA, bodiesA = _build_tree(tmp_path / "mountA")
    projB, bodiesB = _build_tree(tmp_path / "mountB")
    outA = sorted((r.body for r in us.resolve(str(projA))))
    outB = sorted((r.body for r in us.resolve(str(projB))))
    assert outA == outB                               # same logical tree, different prefix -> identical


def test_resolve_returns_empty_when_no_anchor(tmp_path):
    d = tmp_path / "x"
    d.mkdir()
    assert us.resolve(str(d)) == []
