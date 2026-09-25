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


def test_legacy_body_path_is_the_old_sharded_location():
    u = "abcd1234-0000-5000-8000-000000000000"
    p = us.legacy_body_path("/tree", u)
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
        us.Pointer(slug="root-cause", title="Root cause",
                   hook="fix the root, never a patch", pin=True),
        us.Pointer(slug="no-em-dashes", title="No em-dashes",
                   hook="ASCII only", pin=False),
    ]
    block = us.render_pointer_index("what this level is for", ptrs)
    scope, got = us.parse_pointer_index(block)
    assert scope == "what this level is for"
    got = sorted(got, key=lambda p: p.slug != "root-cause")   # pinned renders first; order by intent
    assert [(p.slug, p.title, p.hook, p.pin) for p in got] == [
        ("root-cause", "Root cause", "fix the root, never a patch", True),
        ("no-em-dashes", "No em-dashes", "ASCII only", False),
    ]


def test_pointer_link_is_a_scheme_token_not_a_filesystem_path():
    block = us.render_pointer_index("", [us.Pointer(slug="my-fact", title="T", hook="h")])
    assert "(mem:my-fact)" in block                  # the link is a token, never a path
    assert "/media/" not in block and "/tmp/" not in block   # no baked absolute path anywhere


def test_parse_ignores_non_pointer_lines():
    scope, ptrs = us.parse_pointer_index("# Memory index\n\nsome prose\n- not a pointer\n")
    assert ptrs == []


# ---- splicing the managed block into a CLAUDE.local.md ------------------------------------------

def test_upsert_pointer_block_adds_a_fenced_block_to_empty_text():
    out = us.upsert_pointer_block("", "scope here",
                                  [us.Pointer(slug="t-fact", title="T", hook="h")])
    assert us.INDEX_BEGIN in out and us.INDEX_END in out
    assert "(mem:t-fact)" in out


def test_upsert_pointer_block_replaces_an_existing_block_and_preserves_surrounding_text(tmp_path):
    first = us.upsert_pointer_block("# my notes\n\nkeep me\n", "s1",
                                    [us.Pointer(slug="a-fact", title="A", hook="h")])
    assert "keep me" in first
    second = us.upsert_pointer_block(first, "s2",
                                     [us.Pointer(slug="b-fact", title="B", hook="h")])
    assert "keep me" in second                       # surrounding text survives
    assert second.count(us.INDEX_BEGIN) == 1         # exactly one managed block
    assert "(mem:a-fact)" not in second              # old pointers replaced
    assert "(mem:b-fact)" in second


# ---- mtime-neutral writers ----------------------------------------------------------------------

def test_write_if_changed_writes_then_is_a_noop(tmp_path):
    p = tmp_path / "sub" / "f.md"
    assert us.write_if_changed(p, "hello\n") is True
    assert p.read_text(encoding="utf-8") == "hello\n"
    assert us.write_if_changed(p, "hello\n") is False   # identical -> no write


def test_put_body_writes_to_the_slug_named_path(tmp_path):
    assert us.put_body(str(tmp_path), "some-fact", "BODY") is True
    assert (tmp_path / ".claude-memory" / "facts" / "some-fact.md").read_text(encoding="utf-8") == "BODY\n"


def test_add_pointer_upserts_a_pointer_into_the_altitude_claude_local_md(tmp_path):
    (tmp_path / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    s = us.add_pointer(str(tmp_path), slug="a-fact", title="Fact", hook="a hook",
                       scope_default="lvl scope")
    assert s == "a-fact"
    local = (tmp_path / "CLAUDE.local.md").read_text(encoding="utf-8")
    assert "(mem:a-fact)" in local
    scope, ptrs = us.parse_pointer_index(local)
    assert scope == "lvl scope"
    assert ptrs[0].title == "Fact" and ptrs[0].hook == "a hook"


# ---- the full resolver: cwd -> bodies, across altitudes and mount-independent -------------------

def _build_tree(prefix):
    """A 3-altitude tree with a central store at the anchor and pointers at each level.
    Returns (proj_dir, {slug: expected_body})."""
    anchor = prefix / "root"
    mid = anchor / "pub"
    proj = mid / "proj"
    for d in (anchor, mid, proj):
        d.mkdir(parents=True, exist_ok=True)
        (d / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (anchor / us.STORE_DIRNAME).mkdir(exist_ok=True)   # anchor carries the central store
    bodies = {}
    for level, slug in ((anchor, "root-fact"), (mid, "mid-fact"), (proj, "proj-fact")):
        body = "BODY_%s" % slug
        us.put_body(str(anchor), slug, body)
        us.add_pointer(str(level), slug=slug, title=slug, hook="h")
        bodies[slug] = body
    return proj, bodies


def test_resolve_collects_all_bodies_from_cwd_up_to_anchor(tmp_path):
    proj, bodies = _build_tree(tmp_path / "mountA")
    got = {r.slug: r.body for r in us.resolve(str(proj))}
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


# ---- slug is the logical identity; uuid is only the body-file key (cutover) ---------------------

def test_legacy_pointer_renders_bx_slug_token():
    p = us.Pointer(uuid="aaaaaaaa-0000-5000-8000-000000000000", title="Root cause", hook="h",
                   pin=True, slug="root-cause", legacy=True)
    line = p.index_line()
    assert "bx:slug=root-cause" in line and "bx:pin" in line
    assert "bx:src" not in line                       # provenance is no longer rendered
    assert "uuid:aaaaaaaa" in line                    # legacy lines keep their uuid link


def test_parse_reads_slug_from_mem_link():
    block = us.render_pointer_index("", [us.Pointer(slug="my-slug", title="T", hook="h")])
    _s, ptrs = us.parse_pointer_index(block)
    assert ptrs[0].slug == "my-slug"


def test_source_is_not_rendered_but_pin_survives():
    # provenance was dropped from the always-loaded line: nothing read it, and it cost 14.9
    # percent of this machine's cascade. `pin` is a write-permission gate and stays.
    ptrs = [us.Pointer(slug="feedback-a", title="A", hook="h", pin=True)]
    rendered = us.render_pointer_index("s", ptrs)
    assert "bx:src" not in rendered
    _s, got = us.parse_pointer_index(rendered)


def test_missing_bx_slug_derives_slug_from_title():
    # a back-compat pointer line with no bx:slug token: slug derives from the title
    line = "- [No Em Dashes](uuid:dddddddd-0000-5000-8000-000000000000) - h <!-- bx:src=x -->\n"
    _s, ptrs = us.parse_pointer_index(line)
    assert ptrs[0].slug == "no-em-dashes"


def test_add_pointer_persists_slug(tmp_path):
    (tmp_path / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    us.add_pointer(str(tmp_path), slug="the-slug", title="Fact", hook="h")
    _s, ptrs = us.parse_pointer_index((tmp_path / "CLAUDE.local.md").read_text(encoding="utf-8"))
    assert ptrs[0].slug == "the-slug"


def test_resolved_carries_slug(tmp_path):
    (tmp_path / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (tmp_path / us.STORE_DIRNAME).mkdir()
    us.put_body(str(tmp_path), "a-slug", "body")
    us.add_pointer(str(tmp_path), slug="a-slug", title="A", hook="h")
    got = us.resolve(str(tmp_path))
    assert got[0].slug == "a-slug"


# ==================================================================================================
# SLUG-STORE PIVOT (user decision 2026-07-05, experiment-backed): bodies live at
# <anchor>/.claude-memory/facts/<slug>.md; the pointer line is `- [Title](mem:<slug>) - hook`;
# the block header carries the retrieval RECIPE; legacy uuid: lines parse and re-render AS legacy
# until the migration flips them (so heal never breaks an unmigrated store).
# ==================================================================================================


def test_body_path_is_slug_named_flat():
    p = us.body_path("/tree", "no-em-dashes")
    assert p.as_posix() == "/tree/.claude-memory/facts/no-em-dashes.md"


def test_render_emits_mem_link_without_bx_slug():
    line = us.Pointer(slug="root-cause", title="Root cause", hook="fix the root",
                      pin=True).index_line()
    assert "(mem:root-cause)" in line and "bx:pin" in line
    assert "bx:src" not in line                       # provenance is no longer rendered
    assert "bx:slug" not in line and "uuid:" not in line


def test_render_includes_retrieval_recipe_line():
    block = us.render_pointer_index("scope", [us.Pointer(slug="s", title="T", hook="h")])
    assert "walk UP" in block and "facts/<slug>.md" in block      # the experiment-proven recipe
    assert "NOT preloaded" in block


def test_render_pinned_first_under_iron_rules_heading():
    ptrs = [us.Pointer(slug="b", title="B", hook="h"),
            us.Pointer(slug="a", title="A", hook="h", pin=True)]
    block = us.render_pointer_index("", ptrs)
    assert "## Iron rules" in block and "## Memory index" in block
    assert block.index("## Iron rules") < block.index("(mem:a)") < block.index("## Memory index") \
        < block.index("(mem:b)")


def test_parse_new_mem_line():
    _s, ptrs = us.parse_pointer_index("- [T](mem:my-slug) - h <!-- bx:src=x bx:pin -->\n")
    assert not ptrs[0].legacy


def test_parse_legacy_uuid_line_keeps_uuid_and_flags_legacy():
    line = ("- [T](uuid:11111111-0000-5000-8000-000000000000) - h "
            "<!-- bx:src=x bx:slug=my-slug -->\n")
    _s, ptrs = us.parse_pointer_index(line)
    p = ptrs[0]
    assert p.slug == "my-slug" and p.legacy and p.uuid == "11111111-0000-5000-8000-000000000000"


def test_legacy_line_rerenders_as_legacy_until_migrated():
    # heal round-trips blocks; an unmigrated line must NOT flip to mem: (its body still lives at
    # the uuid path - flipping the line without moving the body would break resolve).
    line = ("- [T](uuid:11111111-0000-5000-8000-000000000000) - h "
            "<!-- bx:src=x bx:slug=my-slug -->")
    _s, ptrs = us.parse_pointer_index(line + "\n")
    out = ptrs[0].index_line()
    assert "uuid:11111111-0000-5000-8000-000000000000" in out and "bx:slug=my-slug" in out


def test_trailing_garbage_after_meta_comment_is_dropped():
    # the live ajnd corruption class: junk after the first meta comment disappears on re-render
    line = ("- [T](mem:my-slug) - a hook <!-- bx:src=x -->ajnd <!-- bx:slug=other -->\n")
    _s, ptrs = us.parse_pointer_index(line)
    p = ptrs[0]
    assert "ajnd" not in p.index_line() and "other" not in p.index_line()


def test_hook_soft_max_and_over_budget():
    assert us.HOOK_SOFT_MAX == 350
    assert us.hook_over_budget("x" * 351) is True
    assert us.hook_over_budget("x" * 350) is False


def test_old_and_new_fence_both_parse():
    inner = "- [T](mem:s1) - h\n"
    old = "<!-- BITRANOX-UUID-INDEX:BEGIN managed -->\n%s<!-- BITRANOX-UUID-INDEX:END -->\n" % inner
    new = us.upsert_pointer_block("", "sc", [us.Pointer(slug="s1", title="T", hook="h")])
    for text in (old, new):
        _s, ptrs = us.parse_pointer_index(text)
        assert [p.slug for p in ptrs] == ["s1"]
    assert "BITRANOX-MEMORY-INDEX:BEGIN" in new                   # renderer emits the new fence


def test_resolve_reads_slug_bodies_and_legacy_uuid_bodies(tmp_path):
    anchor = tmp_path / "tree"; proj = anchor / "proj"
    proj.mkdir(parents=True)
    (anchor / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (anchor / us.STORE_DIRNAME).mkdir()
    # new-format fact
    us.put_body(str(anchor), "new-fact", "NEW BODY")
    # legacy fact: body at the uuid path, pointer line legacy
    legacy_uuid = us.fact_uuid(str(proj), "old-fact")
    legacy_body = anchor / us.STORE_DIRNAME / "facts" / legacy_uuid[:2] / (legacy_uuid + ".md")
    legacy_body.parent.mkdir(parents=True, exist_ok=True)
    legacy_body.write_text("OLD BODY\n", encoding="utf-8")
    block = us.upsert_pointer_block("", "sc", [us.Pointer(slug="new-fact", title="N", hook="h")])
    block = block.replace("<!-- BITRANOX-MEMORY-INDEX:END -->",
                          "- [O](uuid:%s) - h <!-- bx:slug=old-fact -->\n"
                          "<!-- BITRANOX-MEMORY-INDEX:END -->" % legacy_uuid)
    (proj / "CLAUDE.local.md").write_text(block, encoding="utf-8")
    got = {r.slug: r.body for r in us.resolve(str(proj))}
    assert got == {"new-fact": "NEW BODY", "old-fact": "OLD BODY"}


def test_put_body_and_add_pointer_slug_native(tmp_path):
    (tmp_path / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    assert us.put_body(str(tmp_path), "a-slug", "BODY") is True
    assert (tmp_path / ".claude-memory" / "facts" / "a-slug.md").read_text(encoding="utf-8") == "BODY\n"
    us.add_pointer(str(tmp_path), slug="a-slug", title="A", hook="h")
    _s, ptrs = us.parse_pointer_index((tmp_path / "CLAUDE.local.md").read_text(encoding="utf-8"))
    assert ptrs[0].slug == "a-slug" and not ptrs[0].legacy


def test_hook_may_contain_angle_brackets_meta_still_parsed():
    # REGRESSION (live-data bug 2026-07-05): a hook containing placeholders like <mkt>/<plugin>
    # must NOT truncate at the first '<' - the hook runs to the FIRST '<!--' (the meta comment).
    line = ("- [Prune plugin cache](uuid:bcfd5422-cfe5-503c-b795-4fd3594904f1) - prune "
            "~/.claude/plugins/cache/<mkt>/<plugin>/ old version dirs, keeping the active one "
            "<!-- bx:src=global-rules:prune bx:slug=prune-plugin-cache-after-publish -->\n")
    _s, ptrs = us.parse_pointer_index(line)
    p = ptrs[0]
    assert p.slug == "prune-plugin-cache-after-publish"       # bx:slug honored, not title-derived
    assert "<mkt>/<plugin>/" in p.hook                        # hook intact incl. angle brackets


def test_mem_line_hook_with_angle_brackets():
    line = "- [T](mem:t-fact) - use <placeholder> then <other> <!-- bx:pin -->\n"
    _s, ptrs = us.parse_pointer_index(line)
    assert ptrs[0].hook == "use <placeholder> then <other>" and ptrs[0].pin


# ---- ghost-block collapse: a stray second managed block (old-plugin heal residue) ---------------

def test_upsert_collapses_trailing_empty_legacy_block(tmp_path):
    lvl = tmp_path / "lvl"; lvl.mkdir()
    text = ("%s\n<!-- bitranox:self-learning -->\nscope\n<!-- /bitranox:self-learning -->\n\n"
            "# Memory index\n\n- [F](mem:f) - hook\n%s\n\n"
            "%s\n<!-- bitranox:self-learning -->\n\n<!-- /bitranox:self-learning -->\n\n"
            "# Memory index\n%s\n") % (us.INDEX_BEGIN, us.INDEX_END,
                                       us.LEGACY_INDEX_BEGIN, us.LEGACY_INDEX_END)
    scope, ptrs = us.parse_pointer_index(text)
    out = us.upsert_pointer_block(text, scope, ptrs)
    assert out.count("INDEX:BEGIN") == 1 and us.LEGACY_INDEX_BEGIN not in out
    assert "(mem:f)" in out                                     # pointers survive the collapse


def test_upsert_unions_pointers_from_both_blocks(tmp_path):
    text = ("%s\n# Memory index\n- [A](mem:a) - ha\n%s\n\n"
            "%s\n# Memory index\n- [B](mem:b) - hb\n%s\n") % (
                us.INDEX_BEGIN, us.INDEX_END, us.LEGACY_INDEX_BEGIN, us.LEGACY_INDEX_END)
    scope, ptrs = us.parse_pointer_index(text)
    assert {p.slug for p in ptrs} == {"a", "b"}                 # parse reads EVERY managed block
    out = us.upsert_pointer_block(text, scope, ptrs)
    assert out.count("INDEX:BEGIN") == 1
    assert "(mem:a)" in out and "(mem:b)" in out


# ---- a line break inside a hook or title must never split the pointer line ----------------------
# The parser reads one pointer per LINE (str.splitlines), so a break inside a field truncates the
# hook, drops the fact, or lets the tail be read as a second, injected pointer.

def _round_trip(pointers):
    return us.parse_pointer_index(us.upsert_pointer_block("", "sc", pointers))[1]


def test_a_wrapped_hook_renders_as_one_line_and_keeps_its_tail():
    got = _round_trip([us.Pointer(slug="f", title="F", hook="When a long hook wraps,\ndo the thing.")])
    assert [(p.slug, p.hook) for p in got] == [("f", "When a long hook wraps, do the thing.")]


def test_a_hook_cannot_inject_a_second_pointer_line():
    hook = "When a, do b.\n- [Injected](mem:feedback-injected) - When c, do d."
    got = _round_trip([us.Pointer(slug="feedback-real-fact", title="Real", hook=hook)])
    assert [p.slug for p in got] == ["feedback-real-fact"]


@pytest.mark.parametrize("brk", ["\n", "\r\n", "\r", "\u2028", "\x0b", "\x1c", "\x85"])
def test_every_line_boundary_splitlines_honours_is_collapsed(brk):
    got = _round_trip([us.Pointer(slug="f", title="A%sB" % brk, hook="When x,%sdo y." % brk)])
    assert [(p.slug, p.title, p.hook) for p in got] == [("f", "A B", "When x, do y.")]


def test_a_multi_line_title_no_longer_drops_the_fact(tmp_path):
    (tmp_path / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    us.add_pointer(str(tmp_path), slug="feedback-nl", title="Line one\nline two", hook="When x, do y")
    _s, ptrs = us.parse_pointer_index((tmp_path / "CLAUDE.local.md").read_text(encoding="utf-8"))
    assert [(p.slug, p.title) for p in ptrs] == [("feedback-nl", "Line one line two")]


def test_a_single_line_hook_renders_byte_for_byte():
    # CONTROL: only line breaks are touched; a hook with inner double spaces or a tab is unchanged,
    # so every existing pointer line re-renders identically and heal writes nothing.
    hook = "When  x\there, do y  <placeholder> [tag]"
    line = us.Pointer(slug="f", title="T  t", hook=hook).index_line()
    assert line == "- [T  t](mem:f) - %s" % hook


# ---- pointer lines are read from the managed block only ----------------------------------------

def test_a_pointer_shaped_line_outside_the_block_is_not_parsed():
    text = ("notes:\n- [Loose](mem:loose) - When x, do y\n\n"
            + us.upsert_pointer_block("", "sc", [us.Pointer(slug="kept", title="K", hook="h")]))
    _s, ptrs = us.parse_pointer_index(text)
    assert [p.slug for p in ptrs] == ["kept"]


def test_a_loose_line_is_not_copied_into_the_block_on_every_write(tmp_path):
    (tmp_path / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    local = tmp_path / "CLAUDE.local.md"
    block = us.upsert_pointer_block("", "sc", [us.Pointer(slug="kept", title="K", hook="h")])
    local.write_text("notes:\n- [Loose](mem:loose) - When x, do y\n\n" + block, encoding="utf-8")
    counts = []
    for i in range(3):
        us.add_pointer(str(tmp_path), slug="t%d" % i, title="T", hook="h")
        counts.append(local.read_text(encoding="utf-8").count("(mem:loose)"))
    assert counts == [1, 1, 1]


def test_text_without_a_managed_block_is_parsed_whole():
    # CONTROL: a bare rendered block (no fences) and a hand-built snippet still parse.
    body = us.render_pointer_index("sc", [us.Pointer(slug="a", title="A", hook="h")])
    assert [p.slug for p in us.parse_pointer_index(body)[1]] == ["a"]
    assert [p.slug for p in us.parse_pointer_index("- [B](mem:b) - h\n")[1]] == ["b"]


# ---- one slug, one pointer: the copy that is updated is the copy that is read -------------------

def _dup_blocks():
    new_block = "%s\n%s%s" % (us.INDEX_BEGIN, us.render_pointer_index(
        "s", [us.Pointer(slug="feedback-x", title="X", hook="When old, do old")]), us.INDEX_END)
    legacy = ("%s\n- [X](uuid:1234) - When stale, do stale <!-- bx:slug=feedback-x -->\n%s"
              % (us.LEGACY_INDEX_BEGIN, us.LEGACY_INDEX_END))
    return new_block + "\n\n" + legacy + "\n"


def test_parse_keeps_the_first_copy_of_a_duplicated_slug():
    _s, ptrs = us.parse_pointer_index(_dup_blocks())
    assert [(p.slug, p.hook, p.legacy) for p in ptrs] == [("feedback-x", "When old, do old", False)]


def test_add_pointer_on_a_duplicated_slug_updates_what_resolve_reads(tmp_path):
    anchor = tmp_path / "tree"; proj = anchor / "proj"
    proj.mkdir(parents=True)
    (anchor / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    us.put_body(str(anchor), "feedback-x", "body")
    (proj / "CLAUDE.local.md").write_text(_dup_blocks(), encoding="utf-8")
    us.add_pointer(str(proj), "feedback-x", "X", "When NEW, do NEW")
    assert [(r.slug, r.hook) for r in us.resolve(str(proj))] == [("feedback-x", "When NEW, do NEW")]
    assert (proj / "CLAUDE.local.md").read_text(encoding="utf-8").count("feedback-x") == 1


def test_distinct_slugs_across_two_blocks_all_survive():
    # CONTROL: dedup keys on the slug, so two blocks with different facts still union.
    text = ("%s\n- [A](mem:a) - ha\n%s\n\n%s\n- [B](mem:b) - hb\n%s\n") % (
        us.INDEX_BEGIN, us.INDEX_END, us.LEGACY_INDEX_BEGIN, us.LEGACY_INDEX_END)
    assert [p.slug for p in us.parse_pointer_index(text)[1]] == ["a", "b"]


# ---- slug validation: a slug is a plain filename ------------------------------------------------

@pytest.mark.parametrize("slug", ["plain", "feedback-no-em-dashes", "starlette-1.2-httpx2-testclient",
                                  "a", "setup-notes-2"])
def test_is_valid_slug_accepts_real_store_shapes(slug):
    assert us.is_valid_slug(slug)


@pytest.mark.parametrize("slug", ["", "..", "../x", "a/b", "a\\b", ".x", "x.", "-x", "x-", "A",
                                  "a b", "a_b", "a\nb", None, "c:x"])
def test_is_valid_slug_rejects_anything_that_is_not_a_plain_filename(slug):
    assert not us.is_valid_slug(slug)


def test_slugify_output_is_always_a_valid_slug():
    for title in ("No em dashes", "", "  ---  ", "C:\\path\\to", "../../etc", "ps7.6 hosting"):
        assert us.is_valid_slug(us.slugify(title)), title
        assert us.is_valid_slug(us.slugify(title, "feedback")), title


# ---- Windows device names ---------------------------------------------------------------------
# A slug becomes `facts/<slug>.md`, and Windows maps CON, PRN, AUX, NUL, COM0-9 and LPT0-9 to
# devices whatever the extension: `con.md` cannot be created there, and `nul.md` swallows the write.


@pytest.mark.parametrize("slug", ["con", "prn", "aux", "nul", "com1", "com9", "com0", "lpt1",
                                  "lpt9", "lpt0", "con.backup", "nul.1.2"])
def test_is_valid_slug_rejects_a_windows_device_name(slug):
    assert not us.is_valid_slug(slug)


@pytest.mark.parametrize("slug", ["console", "aux-fact", "com10", "feedback-con", "nullable",
                                  "lpt-printing", "prn2", "a.con"])
def test_control_a_name_that_merely_contains_a_device_name_is_valid(slug):
    assert us.is_valid_slug(slug)


@pytest.mark.parametrize("title", ["CON", "Aux", "nul", "COM3", "lpt1"])
def test_slugify_never_produces_a_windows_device_name(title):
    assert us.is_valid_slug(us.slugify(title)), us.slugify(title)
    assert us.slugify(title, "feedback") == "feedback-" + title.lower()


def test_parse_prefers_a_migrated_copy_that_follows_a_legacy_one():
    legacy = ("%s\n- [X](uuid:1234) - When stale, do stale <!-- bx:pin bx:slug=feedback-x -->\n%s"
              % (us.LEGACY_INDEX_BEGIN, us.LEGACY_INDEX_END))
    new_block = "%s\n%s%s" % (us.INDEX_BEGIN, us.render_pointer_index(
        "s", [us.Pointer(slug="feedback-x", title="X", hook="When new, do new")]), us.INDEX_END)
    _s, ptrs = us.parse_pointer_index(legacy + "\n\n" + new_block + "\n")
    assert [(p.slug, p.hook, p.legacy, p.pin) for p in ptrs] == [
        ("feedback-x", "When new, do new", False, True)]       # the pin is carried over the swap


def test_parse_keeps_the_first_of_two_legacy_copies():
    # CONTROL: between copies of the same kind the first still wins.
    text = ("- [X](uuid:1111) - When one <!-- bx:slug=x -->\n"
            "- [X](uuid:2222) - When two <!-- bx:slug=x -->\n")
    assert [(p.uuid, p.hook) for p in us.parse_pointer_index(text)[1]] == [("1111", "When one")]
