"""Tests for memory_engine.py (the single write path, UUID-native). All content ASCII.

Store format under test: a per-altitude pointer block inline in `CLAUDE.local.md`
(`- [Title](uuid:X) - hook <!-- bx:src=.. bx:pin bx:slug=s -->`) + central bodies at
`<anchor>/.claude-memory/facts/<shard>/<uuid>.md`. Slug is the logical identity; uuid is the body key.
"""

import pytest

import self_improve_signals as sig
import memory_engine as E
import uuid_store as us


@pytest.fixture
def proj(tmp_path):
    p = tmp_path / "proj"
    p.mkdir()
    return str(p)


# ---- slug + Entry ------------------------------------------------------------------------------

def test_slugify():
    assert E.slugify("No em dashes") == "no-em-dashes"
    assert E.slugify("No em dashes", "feedback") == "feedback-no-em-dashes"
    assert E.slugify("feedback already", "feedback") == "feedback-already"  # no double prefix drift
    assert E.slugify("") == "note"


def test_entry_carries_slug_and_uuid_no_heavy_flag():
    e = E.Entry("s", "t", "h", body="b", source={"x"}, pin=True, uuid="u")
    assert (e.slug, e.title, e.hook, e.body, e.pin, e.uuid) == ("s", "t", "h", "b", True, "u")
    assert not hasattr(e, "heavy")                     # the inline-vs-heavy split is gone


# ---- add_or_update_entry -> pointer block + central body ---------------------------------------

def test_add_writes_pointer_and_central_body_and_reads_back(proj):
    E.add_or_update_entry(proj, "No em dashes", "use ASCII", body="Always ASCII.",
                          type_="feedback", source=["s"], scope_default="lvl")
    scope, entries, bodies = E.read_store(proj)
    assert scope == "lvl"
    e = entries[0]
    assert e.slug == "feedback-no-em-dashes" and e.source == {"s"} and not e.legacy
    assert bodies[e.slug] == "Always ASCII."
    # body landed at the slug-named central path (proj is its own anchor here)
    assert us.body_path(proj, e.slug).read_text(encoding="utf-8") == "Always ASCII.\n"
    # pointer line carries the mem: link + the block carries the retrieval recipe
    local = sig.claude_local_md_path(proj).read_text(encoding="utf-8")
    assert "(mem:feedback-no-em-dashes)" in local and "walk UP" in local
    assert "@" not in local.replace("@import", "")     # no import token
    assert not (sig.claude_memory_dir(proj)).exists()  # no legacy .claude-bx-selflearning store


def test_update_merges_source_and_pin_and_body(proj):
    E.add_or_update_entry(proj, "Rule", "hook", body="b", source=["s1"], scope_default="lvl")
    E.add_or_update_entry(proj, "Rule", "hook2", body="b2", source=["s2"], pin=True)
    scope, entries, bodies = E.read_store(proj)
    e = entries[0]
    assert e.source == {"s1", "s2"} and e.pin is True and e.hook == "hook2"
    assert bodies[e.slug] == "b2"


def test_empty_body_on_update_keeps_prior_body(proj):
    E.add_or_update_entry(proj, "Rule", "h", body="keep me", scope_default="lvl")
    E.add_or_update_entry(proj, "Rule", "h2")          # no body -> prior body retained
    _s, entries, bodies = E.read_store(proj)
    assert bodies[entries[0].slug] == "keep me"


def test_mtime_neutral_noop(proj):
    E.add_or_update_entry(proj, "Rule", "h", body="b", source=["s"], scope_default="lvl")
    local = sig.claude_local_md_path(proj)
    mt1 = local.stat().st_mtime_ns
    E.add_or_update_entry(proj, "Rule", "h", body="b", source=["s"])   # identical -> no write
    assert local.stat().st_mtime_ns == mt1


# ---- ensure_level: pointer block + scope, no @import -------------------------------------------

def test_ensure_level_creates_pointer_block_and_scope_in_claude_local_md(proj):
    E.ensure_level(proj, scope_default="what this level is for")
    local = sig.claude_local_md_path(proj).read_text(encoding="utf-8")
    assert us.INDEX_BEGIN in local and us.INDEX_END in local
    assert sig.read_scope_block(local) == "what this level is for"
    assert "@import" not in local and "@.claude" not in local        # no import wiring
    assert not sig.claude_md_path(proj).exists()                     # tracked CLAUDE.md untouched


def test_ensure_level_idempotent(proj):
    E.ensure_level(proj, scope_default="x")
    local1 = sig.claude_local_md_path(proj).read_text(encoding="utf-8")
    E.ensure_level(proj, scope_default="x")
    assert sig.claude_local_md_path(proj).read_text(encoding="utf-8") == local1   # no duplicate block


def test_ensure_level_preserves_user_claude_md(proj):
    md_path = sig.claude_md_path(proj)
    md_path.write_text("# My project\n\nHand-written user instructions.\n", encoding="utf-8")
    E.ensure_level(proj, scope_default="x")
    assert md_path.read_text(encoding="utf-8") == "# My project\n\nHand-written user instructions.\n"
    assert us.INDEX_BEGIN in sig.claude_local_md_path(proj).read_text(encoding="utf-8")


def test_ensure_level_moves_legacy_scope_block_out_of_claude_md(proj):
    md_path = sig.claude_md_path(proj)
    md_path.write_text("# Proj\n\n%s\nlegacy descriptor\n%s\n\nmore user text\n"
                       % (sig.SCOPE_MARK_BEGIN, sig.SCOPE_MARK_END), encoding="utf-8")
    E.ensure_level(proj, scope_default="ignored-because-legacy-wins")
    md = md_path.read_text(encoding="utf-8")
    assert sig.SCOPE_MARK_BEGIN not in md                            # legacy block removed from CLAUDE.md
    assert "more user text" in md and md.startswith("# Proj")
    local = sig.claude_local_md_path(proj).read_text(encoding="utf-8")
    assert sig.read_scope_block(local) == "legacy descriptor"        # relocated into the pointer block


# ---- CLI ---------------------------------------------------------------------------------------

def test_cli_add_prints_slug(proj, capsys):
    rc = E.main(["add", "--proj", proj, "--type", "feedback", "--title", "No em dashes",
                 "--hook", "use ASCII", "--body", "Always ASCII.", "--source", "a,b", "--scope", "lvl"])
    assert rc == 0
    assert capsys.readouterr().out.strip() == "feedback-no-em-dashes"
    scope, entries, _b = E.read_store(proj)
    assert entries[0].source == {"a", "b"} and scope == "lvl"


def test_cli_add_body_file(proj, tmp_path):
    bf = tmp_path / "body.txt"
    bf.write_text("line one\nline two\n", encoding="utf-8")
    rc = E.main(["add", "--proj", proj, "--title", "Multi", "--hook", "h", "--body-file", str(bf)])
    assert rc == 0
    _s, entries, bodies = E.read_store(proj)
    assert bodies[entries[0].slug] == "line one\nline two"


# ---- self-heal ---------------------------------------------------------------------------------

def test_heal_creates_missing_pointer_block(proj):
    rep = E.heal(proj)
    local = sig.claude_local_md_path(proj).read_text(encoding="utf-8")
    assert us.INDEX_BEGIN in local                                   # pointer block wired in
    assert "@import" not in local
    assert rep["levels"] >= 1


def test_heal_normalizes_a_malformed_scope_block(proj):
    E.ensure_level(proj, scope_default="what this level is for")
    local = sig.claude_local_md_path(proj)
    # corrupt: a SCOPE_BEGIN with no END inside the block
    local.write_text("%s\n%s\nbroken scope\n\n# Memory index\n%s\n"
                     % (us.INDEX_BEGIN, E.SCOPE_BEGIN, us.INDEX_END), encoding="utf-8")
    E.heal(proj)
    healed = local.read_text(encoding="utf-8")
    assert E.SCOPE_BEGIN in healed and E.SCOPE_END in healed          # scope markers restored
    _s, ptrs = us.parse_pointer_index(healed)
    assert isinstance(ptrs, list)                                    # parses cleanly


def test_heal_reports_missing_central_body_not_fabricated(proj):
    slug = E.add_or_update_entry(proj, title="Heavy one", hook="h", body="x" * 400, scope_default="lvl")
    body = us.body_path(proj, slug)
    assert body.is_file()
    body.unlink()                                                    # delete the body -> unreconstructable
    rep = E.heal(proj)
    assert (proj, slug) in rep["orphans"]                            # reported...
    assert not body.is_file()                                       # ...NOT fabricated


def test_heal_idempotent(proj):
    E.heal(proj)
    rep2 = E.heal(proj)
    assert rep2["healed"] == []                                      # second pass changes nothing


def test_heal_scaffolds_every_level_up_to_the_anchor(tmp_path):
    # CLAUDE.md only at top; heal creates a marker CLAUDE.md + CLAUDE.local.md pointer block at every gap
    # level up to it, and does NOT overwrite the top's existing CLAUDE.md. No legacy .claude-bx dir.
    (tmp_path / "top" / "mid" / "proj").mkdir(parents=True)
    (tmp_path / "top" / "CLAUDE.md").write_text("real top instructions", encoding="utf-8")
    E.heal(str(tmp_path / "top" / "mid" / "proj"))
    for level in ("top", "top/mid", "top/mid/proj"):
        d = tmp_path / level
        assert (d / "CLAUDE.md").is_file()
        assert us.INDEX_BEGIN in (d / "CLAUDE.local.md").read_text(encoding="utf-8")
        assert not (d / ".claude-bx-selflearning").exists()
    assert "bitranox memory altitude" in (tmp_path / "top" / "mid" / "CLAUDE.md").read_text(encoding="utf-8")
    assert (tmp_path / "top" / "CLAUDE.md").read_text(encoding="utf-8").strip() == "real top instructions"


def test_set_scope_upserts_and_overwrites(proj):
    rc = E.main(["set-scope", "--proj", proj, "--scope", "what this level is about"])
    assert rc == 0
    local = sig.claude_local_md_path(proj)
    assert sig.read_scope_block(local.read_text(encoding="utf-8")) == "what this level is about"
    E.main(["set-scope", "--proj", proj, "--scope", "revised classification"])   # overwrite
    assert sig.read_scope_block(local.read_text(encoding="utf-8")) == "revised classification"
    assert us.INDEX_HEADING in local.read_text(encoding="utf-8")


# ---- anchored tree: central body-store at the anchor, pointers per-altitude ---------------------

def _anchored_tree(tmp_path):
    """anchor (CLAUDE.md + .claude-memory store) -> proj altitude below it. Returns (anchor, proj)."""
    anchor = tmp_path / "tree"
    proj = anchor / "proj"
    proj.mkdir(parents=True)
    (anchor / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (proj / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (anchor / us.STORE_DIRNAME).mkdir()
    return str(anchor), str(proj)


def test_add_writes_body_to_anchor_store_and_pointer_to_altitude(tmp_path):
    anchor, proj = _anchored_tree(tmp_path)
    slug = E.add_or_update_entry(proj, "No em dashes", "use ASCII", body="Always ASCII.",
                                 type_="feedback", source=["s"], scope_default="proj scope")
    assert slug == "feedback-no-em-dashes"
    assert us.body_path(anchor, slug).read_text(encoding="utf-8") == "Always ASCII.\n"  # body at the anchor
    scope, ptrs = us.parse_pointer_index((tmp_path / "tree" / "proj" / "CLAUDE.local.md").read_text(encoding="utf-8"))
    assert scope == "proj scope"
    assert ptrs[0].slug == "feedback-no-em-dashes" and ptrs[0].source == {"s"}


def test_add_is_idempotent_and_merges_source(tmp_path):
    anchor, proj = _anchored_tree(tmp_path)
    E.add_or_update_entry(proj, "Fact", "h", body="B", source=["a"])
    E.add_or_update_entry(proj, "Fact", "h", body="B", source=["b"])  # re-run: no dupe, merge source
    _scope, ptrs = us.parse_pointer_index((tmp_path / "tree" / "proj" / "CLAUDE.local.md").read_text(encoding="utf-8"))
    assert len(ptrs) == 1 and ptrs[0].source == {"a", "b"}


def test_add_refuses_slug_collision_across_levels(tmp_path):
    # slugs are TREE-unique: the same slug captured at a DIFFERENT level is refused with a suggestion
    anchor, proj = _anchored_tree(tmp_path)
    E.add_or_update_entry(str(tmp_path / "tree"), "Setup notes", "h", body="anchor-level fact")
    import pytest as _pytest
    with _pytest.raises(E.SlugCollision) as exc:
        E.add_or_update_entry(proj, "Setup notes", "h", body="different fact, same slug")
    assert exc.value.suggestion == "setup-notes-2"
    # the suggested slug is accepted
    got = E.add_or_update_entry(proj, "Setup notes", "h", body="different fact, same slug",
                                slug="setup-notes-2")
    assert got == "setup-notes-2"


def test_add_roundtrips_through_the_resolver(tmp_path):
    anchor, proj = _anchored_tree(tmp_path)
    E.add_or_update_entry(proj, "Fact", "h", body="the body")
    got = us.resolve(proj)
    assert [(r.title, r.body, r.slug) for r in got] == [("Fact", "the body", "fact")]


def test_cli_add_collision_refusal_exit_one(tmp_path, capsys):
    anchor, proj = _anchored_tree(tmp_path)
    E.add_or_update_entry(str(tmp_path / "tree"), "T", "h", body="B")
    rc = E.main(["add", "--proj", proj, "--title", "T", "--hook", "h", "--body", "other"])
    out = capsys.readouterr().out
    assert rc == 1 and "! refused:" in out and "t-2" in out


def test_cli_add_warns_over_hook_budget(tmp_path, capsys, proj):
    long_hook = "x" * (us.HOOK_SOFT_MAX + 1)
    rc = E.main(["add", "--proj", proj, "--title", "Budget", "--hook", long_hook, "--body", "B"])
    out = capsys.readouterr().out
    assert rc == 0 and "~ warning: hook is" in out                  # advisory, exit stays 0
