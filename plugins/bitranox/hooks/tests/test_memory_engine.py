"""Tests for memory_engine.py (the single write path). All content ASCII.

Store format under test: a per-altitude pointer block inline in `CLAUDE.local.md`
(`- [Title](mem:<slug>) - hook <!-- bx:pin -->`) + central bodies at
`<anchor>/.claude-memory/facts/<slug>.md`. The slug IS the identity, unique per tree.

Pre-pivot lines (`- [Title](uuid:X) - hook <!-- bx:slug=s -->`, bodies sharded at
`facts/<2-hex>/<uuid>.md`) are still parsed and are exercised here too, so the legacy shapes below
are deliberate. A `bx:src=` token on such a line is consumed and discarded: provenance is no longer
rendered on any line.
"""

import json
from pathlib import Path

import pytest

import self_improve_signals as sig
import memory_engine as E
import uuid_store as us


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    # the stores-generation marker + recall caches live under ~/.claude; keep tests hermetic. Create
    # only `home` (not `.claude`) so a test that builds its own `home/.claude` does not collide;
    # bump/cache code mkdir their own subdirs on demand.
    h = tmp_path / "home"
    h.mkdir(exist_ok=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


@pytest.fixture
def proj(tmp_path):
    p = tmp_path / "proj"
    p.mkdir()
    return str(p)


def test_new_store_creation_bumps_generation_once(proj):
    assert sig.stores_generation() == 0
    E.add_or_update_entry(proj, "Rule", "hook", body="b", scope_default="lvl")   # creates the store dir
    assert sig.stores_generation() == 1                                          # new store -> bump
    E.add_or_update_entry(proj, "Another", "hook2", body="b2")                   # same store -> no bump
    assert sig.stores_generation() == 1


# ---- slug + Entry ------------------------------------------------------------------------------

def test_slugify():
    assert E.slugify("No em dashes") == "no-em-dashes"
    assert E.slugify("No em dashes", "feedback") == "feedback-no-em-dashes"
    assert E.slugify("feedback already", "feedback") == "feedback-already"  # no double prefix drift
    assert E.slugify("") == "note"


def test_entry_carries_slug_and_uuid_no_heavy_flag():
    e = E.Entry("s", "t", "h", body="b", pin=True, uuid="u")
    assert (e.slug, e.title, e.hook, e.body, e.pin, e.uuid) == ("s", "t", "h", "b", True, "u")
    assert not hasattr(e, "heavy")                     # the inline-vs-heavy split is gone


# ---- add_or_update_entry -> pointer block + central body ---------------------------------------

def test_add_writes_pointer_and_central_body_and_reads_back(proj):
    E.add_or_update_entry(proj, "No em dashes", "use ASCII", body="Always ASCII.",
                          type_="feedback", scope_default="lvl")
    scope, entries, bodies = E.read_store(proj)
    assert scope == "lvl"
    e = entries[0]
    assert e.slug == "feedback-no-em-dashes" and not e.legacy
    assert "Always ASCII." in bodies[e.slug]
    # body landed at the slug-named central path, framed as a native memory entry
    disk = us.body_path(proj, e.slug).read_text(encoding="utf-8")
    assert disk.startswith("---\nname: feedback-no-em-dashes\n") and disk.endswith("Always ASCII.\n")
    # pointer line carries the mem: link + the block carries the retrieval recipe
    local = sig.claude_local_md_path(proj).read_text(encoding="utf-8")
    assert "(mem:feedback-no-em-dashes)" in local and "walk UP" in local
    assert "@" not in local.replace("@import", "")     # no import token
    assert not (sig.claude_memory_dir(proj)).exists()  # no legacy .claude-bx-selflearning store


def test_update_merges_pin_and_body_and_does_not_persist_source(proj):
    E.add_or_update_entry(proj, "Rule", "hook", body="b", scope_default="lvl")
    E.add_or_update_entry(proj, "Rule", "hook2", body="b2", pin=True)
    scope, entries, bodies = E.read_store(proj)
    e = entries[0]
    assert e.pin is True and e.hook == "hook2"
    assert bodies[e.slug].endswith("b2") and "b\n" not in bodies[e.slug]


def test_empty_body_on_update_keeps_prior_body(proj):
    E.add_or_update_entry(proj, "Rule", "h", body="keep me", scope_default="lvl")
    E.add_or_update_entry(proj, "Rule", "h2")          # no body -> prior body retained
    _s, entries, bodies = E.read_store(proj)
    assert bodies[entries[0].slug].endswith("keep me")


def test_hook_only_update_resyncs_body_description(proj):
    # A slug-stable hook rewrite (new --hook, no --body) must keep the body's `description:`
    # frontmatter in sync with the pointer hook; otherwise the pointer shows the new hook while the
    # body keeps the stale one (spec: the body description IS the hook).
    slug = E.add_or_update_entry(proj, "Rule", "When A happens, do X.",
                                 body="the prose", type_="reference", scope_default="lvl")
    E.add_or_update_entry(proj, "Rule", "When B happens, do Y.", slug=slug)   # hook-only update
    body = us.body_path(proj, slug).read_text(encoding="utf-8")
    assert "description: When B happens, do Y." in body    # description tracks the new hook
    assert "When A happens, do X." not in body             # stale description gone
    assert "the prose" in body                             # prose preserved


def test_mtime_neutral_noop(proj):
    E.add_or_update_entry(proj, "Rule", "h", body="b", scope_default="lvl")
    local = sig.claude_local_md_path(proj)
    mt1 = local.stat().st_mtime_ns
    E.add_or_update_entry(proj, "Rule", "h", body="b")   # identical -> no write
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
                 "--hook", "use ASCII", "--body", "Always ASCII.", "--scope", "lvl"])
    assert rc == 0
    out = capsys.readouterr().out
    assert out.splitlines()[0] == "feedback-no-em-dashes"    # warnings may follow the slug
    scope, entries, _b = E.read_store(proj)


def test_cli_add_body_file(proj, tmp_path):
    bf = tmp_path / "body.txt"
    bf.write_text("line one\nline two\n", encoding="utf-8")
    rc = E.main(["add", "--proj", proj, "--title", "Multi", "--hook", "h", "--body-file", str(bf)])
    assert rc == 0
    _s, entries, bodies = E.read_store(proj)
    assert bodies[entries[0].slug].endswith("line one\nline two")


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
                                 type_="feedback", scope_default="proj scope")
    assert slug == "feedback-no-em-dashes"
    disk = us.body_path(anchor, slug).read_text(encoding="utf-8")   # body at the anchor, framed
    assert disk.startswith("---\nname: feedback-no-em-dashes\n") and disk.endswith("Always ASCII.\n")
    scope, ptrs = us.parse_pointer_index((tmp_path / "tree" / "proj" / "CLAUDE.local.md").read_text(encoding="utf-8"))
    assert scope == "proj scope"


def test_add_is_idempotent_and_does_not_persist_source(tmp_path):
    anchor, proj = _anchored_tree(tmp_path)
    E.add_or_update_entry(proj, "Fact", "h", body="B")
    E.add_or_update_entry(proj, "Fact", "h", body="B")   # re-run must not duplicate the pointer
    _scope, ptrs = us.parse_pointer_index((tmp_path / "tree" / "proj" / "CLAUDE.local.md").read_text(encoding="utf-8"))
    assert len(ptrs) == 1 and ptrs[0].slug == "fact"


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
    assert [(r.title, r.slug) for r in got] == [("Fact", "fact")]
    assert got[0].body.startswith("---\nname: fact\n") and got[0].body.endswith("the body")


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


def test_cli_add_over_hard_cap_refusal_exit_one(tmp_path, capsys, proj):
    over = "x" * (us.HOOK_HARD_MAX + 1)
    rc = E.main(["add", "--proj", proj, "--title", "Over", "--hook", over, "--body", "B"])
    out = capsys.readouterr().out
    assert rc == 1 and "! refused:" in out and "hard cap" in out
    assert E.read_store(proj)[1] == []                              # refused BEFORE any write


# ---- move: the dream's re-leveling primitive (pointer-line ops only; the body never moves) -------

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


def test_move_up_relocates_pointer_only_body_untouched(tmp_path):
    anchor, mid, proj = _three_levels(tmp_path)
    E.add_or_update_entry(proj, "Shared rule", "applies to the whole dept", body="B",
                          pin=True, scope_default="proj")
    body = us.body_path(anchor, "shared-rule")
    before = body.read_text(encoding="utf-8")
    rep = E.move_entry(proj, mid, "shared-rule")
    assert rep["moved"] is True and rep["refused"] is None and rep["direction"] == "up"
    assert body.read_text(encoding="utf-8") == before            # body file untouched
    _s, ptrs_from = us.parse_pointer_index((Path(proj) / "CLAUDE.local.md").read_text(encoding="utf-8"))
    assert "shared-rule" not in {p.slug for p in ptrs_from}      # gone at source
    _s, ptrs_to = us.parse_pointer_index((Path(mid) / "CLAUDE.local.md").read_text(encoding="utf-8"))
    got = {p.slug: p for p in ptrs_to}
    assert "shared-rule" in got and got["shared-rule"].pin       # pin survives a move
    assert {r.slug for r in us.resolve(proj)} == {"shared-rule"}  # still visible from below


def test_move_down_works_without_refs(tmp_path):
    anchor, mid, proj = _three_levels(tmp_path)
    E.add_or_update_entry(anchor, "Proj detail", "belongs lower", body="B", scope_default="a")
    rep = E.move_entry(anchor, proj, "proj-detail")
    assert rep["moved"] is True and rep["direction"] == "down"
    assert "proj-detail" in {p.slug for p in us.parse_pointer_index(
        (Path(proj) / "CLAUDE.local.md").read_text(encoding="utf-8"))[1]}


def test_move_down_refused_when_a_ref_would_dangle_force_overrides(tmp_path):
    anchor, mid, proj = _three_levels(tmp_path)
    E.add_or_update_entry(anchor, "Base rule", "the base", body="B", scope_default="a")
    E.add_or_update_entry(mid, "Citing fact", "builds on [[base-rule]]", body="B2", scope_default="m")
    rep = E.move_entry(anchor, proj, "base-rule")
    assert rep["moved"] is False and "dangle" in (rep["refused"] or "")
    rep2 = E.move_entry(anchor, proj, "base-rule", force=True)
    assert rep2["moved"] is True and rep2["warnings"]            # forced through, with a warning


def test_move_refusals_sibling_sametree_crosslevel(tmp_path):
    anchor, mid, proj = _three_levels(tmp_path)
    sib = Path(anchor) / "sibling"
    sib.mkdir(); (sib / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    E.add_or_update_entry(proj, "F", "h", body="B", scope_default="p")
    assert "sibling" in (E.move_entry(proj, str(sib), "f")["refused"] or "")
    assert E.move_entry(proj, proj, "f")["refused"]              # same level
    assert "not found" in (E.move_entry(mid, anchor, "nope")["refused"] or "")


def test_move_refuses_cross_tree(two_trees):
    E.add_or_update_entry(str(two_trees.proj_a), "F", "h", body="B", scope_default="p")
    rep = E.move_entry(str(two_trees.proj_a), str(two_trees.top_b), "f")
    assert rep["moved"] is False and "tree" in (rep["refused"] or "")


def test_move_completes_after_crash_duplicate(tmp_path):
    # add-then-remove crash residue: the pointer exists at BOTH levels; re-running the move
    # merges at the target and drops the source line (never a lost fact).
    anchor, mid, proj = _three_levels(tmp_path)
    E.add_or_update_entry(proj, "F", "h", body="B", scope_default="p")
    us.add_pointer(mid, slug="f", title="F", hook="h")   # simulated crash residue
    rep = E.move_entry(proj, mid, "f")
    assert rep["moved"] is True
    _s, ptrs = us.parse_pointer_index((Path(mid) / "CLAUDE.local.md").read_text(encoding="utf-8"))
    got = {p.slug: p for p in ptrs}
    assert len([p for p in ptrs if p.slug == "f"]) == 1          # merged to a single line
    assert "f" not in {p.slug for p in us.parse_pointer_index(
        (Path(proj) / "CLAUDE.local.md").read_text(encoding="utf-8"))[1]}


def test_move_refuses_divergent_duplicate_target_no_silent_overwrite(tmp_path):
    # Defect A: when the target ALREADY points at the slug with a DIFFERENT hook, a plain move would
    # overwrite the target's (richer) hook with the source's - silent, direction-dependent data loss.
    # Without --force it must refuse and leave BOTH pointer lines untouched.
    anchor, mid, proj = _three_levels(tmp_path)
    E.add_or_update_entry(proj, "Tell sweep", "thin source hook", body="B", scope_default="p")
    us.add_pointer(mid, slug="tell-sweep", title="Tell sweep",
                   hook="RICH target hook naming strip_typographic_tells.py and reformat_tables.py")
    rep = E.move_entry(proj, mid, "tell-sweep")
    assert rep["moved"] is False and "duplicate" in (rep["refused"] or "")
    tgt = {p.slug: p for p in us.parse_pointer_index((Path(mid) / "CLAUDE.local.md").read_text(encoding="utf-8"))[1]}
    assert tgt["tell-sweep"].hook.startswith("RICH target hook")          # target hook intact
    srcp = {p.slug: p for p in us.parse_pointer_index((Path(proj) / "CLAUDE.local.md").read_text(encoding="utf-8"))[1]}
    assert srcp["tell-sweep"].hook == "thin source hook"                  # source hook intact


def test_move_force_dedup_keeps_longer_hook_when_source_is_richer(tmp_path):
    # --force dedups a divergent duplicate by keeping the LONGER (information-richer) hook regardless
    # of move direction, dropping the other pointer. Source is the rich one.
    anchor, mid, proj = _three_levels(tmp_path)
    E.add_or_update_entry(proj, "Fact", "a much longer richer hook with the load-bearing detail",
                          body="B", scope_default="p")
    us.add_pointer(mid, slug="fact", title="Fact", hook="thin")
    rep = E.move_entry(proj, mid, "fact", force=True)
    assert rep["moved"] is True and rep["warnings"]
    tgt = {p.slug: p for p in us.parse_pointer_index((Path(mid) / "CLAUDE.local.md").read_text(encoding="utf-8"))[1]}
    assert tgt["fact"].hook.startswith("a much longer richer hook")       # longer hook won
    assert "fact" not in {p.slug for p in us.parse_pointer_index(
        (Path(proj) / "CLAUDE.local.md").read_text(encoding="utf-8"))[1]}


def test_move_force_dedup_keeps_longer_hook_when_target_is_richer(tmp_path):
    # The direction-independence guarantee: even when the RICHER hook lives at the target and the
    # move flows the other way, --force must keep it (a plain move would have picked by direction).
    anchor, mid, proj = _three_levels(tmp_path)
    E.add_or_update_entry(mid, "Fact", "thin", body="B", scope_default="m")           # source: thin
    us.add_pointer(proj, slug="fact", title="Fact", hook="the much longer richer target hook here")
    rep = E.move_entry(mid, proj, "fact", force=True)                                 # down-move dedup
    assert rep["moved"] is True
    tgt = {p.slug: p for p in us.parse_pointer_index((Path(proj) / "CLAUDE.local.md").read_text(encoding="utf-8"))[1]}
    assert tgt["fact"].hook.startswith("the much longer richer target hook")
    assert "fact" not in {p.slug for p in us.parse_pointer_index(
        (Path(mid) / "CLAUDE.local.md").read_text(encoding="utf-8"))[1]}


def test_move_refuses_unmigrated_legacy_entry(tmp_path):
    anchor, mid, proj = _three_levels(tmp_path)
    u = "11111111-0000-5000-8000-000000000000"
    bp = us.legacy_body_path(anchor, u)
    bp.parent.mkdir(parents=True, exist_ok=True)
    bp.write_text("OLD\n", encoding="utf-8")
    (Path(proj) / "CLAUDE.local.md").write_text(
        "%s\n# Memory index\n- [Old](uuid:%s) - h <!-- bx:slug=old-fact -->\n%s\n"
        % (us.LEGACY_INDEX_BEGIN, u, us.LEGACY_INDEX_END), encoding="utf-8")
    rep = E.move_entry(proj, mid, "old-fact")
    assert rep["moved"] is False and "migrate" in (rep["refused"] or "").lower()


# ---- move: a SET of slugs that moves TOGETHER (the mutually-citing pair the guard could not free)

def _citing_pair(level):
    """Two facts at `level` that cite EACH OTHER: each one's only inbound ref is the other."""
    E.add_or_update_entry(level, "Fact a", "pairs with [[fact-b]]", body="A", scope_default="a")
    E.add_or_update_entry(level, "Fact b", "pairs with [[fact-a]]", body="B")
    return "fact-a", "fact-b"


def _slugs_at(level):
    """The slugs in a level's pointer block (empty when the level has no block yet)."""
    try:
        text = (Path(level) / "CLAUDE.local.md").read_text(encoding="utf-8")
    except OSError:
        return set()
    return {p.slug for p in us.parse_pointer_index(text)[1]}


def test_move_down_single_slug_deadlocks_on_a_mutually_citing_pair(tmp_path):
    # The motivating defect, pinned as a regression: each fact's inbound ref is the other, so the
    # ref guard refuses BOTH, in EITHER order, and the only escape was --force (which is how a ref
    # actually gets stranded). Single-slug moves must KEEP refusing - taken alone, either move
    # really would leave a ref above its target. The set form below is the correct way out.
    anchor, mid, proj = _three_levels(tmp_path)
    a, b = _citing_pair(anchor)
    assert "dangle" in (E.move_entry(anchor, proj, a)["refused"] or "")
    assert "dangle" in (E.move_entry(anchor, proj, b)["refused"] or "")
    assert _slugs_at(anchor) == {a, b}                     # neither moved, nothing lost


def test_move_down_multi_slug_releases_the_mutually_citing_pair(tmp_path):
    # The whole set is evaluated against its POST-move placement, so a member citing another member
    # is not dangling - both land at the target together.
    anchor, mid, proj = _three_levels(tmp_path)
    a, b = _citing_pair(anchor)
    rep = E.move_entry(anchor, proj, [a, b])
    assert rep["moved"] is True and rep["refused"] is None and rep["direction"] == "down"
    assert rep["slugs"] == [a, b] and rep["moved_slugs"] == [a, b]
    assert _slugs_at(proj) == {a, b} and _slugs_at(anchor) == set()
    assert us.body_path(anchor, a).is_file()               # bodies never move, only pointers


def test_move_multi_slug_is_order_independent(tmp_path):
    # Moving {A,B} must equal moving {B,A}: the guard reads the whole set at once, so no result may
    # depend on which member is processed first.
    def run(order):
        root = tmp_path / ("order-" + "-".join(order))
        root.mkdir()
        anchor, _mid, proj = _three_levels(root)
        a, b = _citing_pair(anchor)
        rep = E.move_entry(anchor, proj, [{"a": a, "b": b}[k] for k in order])
        return rep["moved"], _slugs_at(proj), _slugs_at(anchor)

    assert run(["a", "b"]) == run(["b", "a"]) == (True, {"fact-a", "fact-b"}, set())


def test_move_multi_slug_still_refuses_a_citer_outside_the_set(tmp_path):
    # The guard is made set-aware, never weakened: a third fact staying ABOVE the new home still
    # dangles, so the whole set is refused. Without this, "move them together" would be a blanket
    # bypass of the one check that keeps cascade reach intact.
    anchor, mid, proj = _three_levels(tmp_path)
    a, b = _citing_pair(anchor)
    E.add_or_update_entry(mid, "Outsider", "also builds on [[fact-a]]", body="C", scope_default="m")
    rep = E.move_entry(anchor, proj, [a, b])
    assert rep["moved"] is False and "dangle" in (rep["refused"] or "")
    assert "outsider" in rep["refused"]                    # the blocking citer is named
    assert _slugs_at(anchor) == {a, b} and _slugs_at(proj) == set()      # nothing moved
    rep2 = E.move_entry(anchor, proj, [a, b], force=True)  # --force still overrides, with a warning
    assert rep2["moved"] is True and rep2["warnings"] and _slugs_at(proj) == {a, b}


def test_move_multi_slug_exemption_covers_only_the_pointer_that_moves(tmp_path):
    # The co-mover exemption is keyed to the POINTER at the from-level, not to the slug NAME: a
    # stray duplicate pointer for a moving slug left at a higher level does not move with the set,
    # so its [[ref]] would still dangle and the move must keep refusing.
    anchor, mid, proj = _three_levels(tmp_path)
    a, b = _citing_pair(anchor)
    us.add_pointer(mid, slug=b, title="Fact b", hook="stray copy citing [[fact-a]]")
    rep = E.move_entry(anchor, proj, [a, b])
    assert rep["moved"] is False and "dangle" in (rep["refused"] or "")
    assert _slugs_at(anchor) == {a, b}


def test_move_multi_slug_refusal_is_atomic_nothing_moves(tmp_path):
    # A set is validated in FULL before any write: one bad member (here, absent at the from-level)
    # must leave every other member's pointer exactly where it was. A partial move would strand
    # precisely the refs the set form exists to keep whole.
    anchor, mid, proj = _three_levels(tmp_path)
    a, b = _citing_pair(anchor)
    rep = E.move_entry(anchor, proj, [a, b, "no-such-fact"])
    assert rep["moved"] is False and "not found" in (rep["refused"] or "")
    assert _slugs_at(anchor) == {a, b} and _slugs_at(proj) == set()


def test_move_multi_slug_divergent_duplicate_refuses_before_any_write(tmp_path):
    # The duplicate-pointer refusal (defect A) is also evaluated for the WHOLE set first: a second
    # member's divergent duplicate at the target may not be discovered only after the first member
    # has already been written.
    anchor, mid, proj = _three_levels(tmp_path)
    a, b = _citing_pair(anchor)
    us.add_pointer(proj, slug=b, title="Fact b", hook="a DIFFERENT hook already at the target")
    rep = E.move_entry(anchor, proj, [a, b])
    assert rep["moved"] is False and "duplicate" in (rep["refused"] or "")
    assert _slugs_at(anchor) == {a, b}                     # a was NOT moved ahead of the refusal


def test_move_multi_slug_legacy_member_refuses_and_names_it(tmp_path):
    # The legacy-pointer refusal survives the set form, and names WHICH member is unmigrated.
    anchor, mid, proj = _three_levels(tmp_path)
    E.add_or_update_entry(mid, "Fresh", "h", body="B", scope_default="m")
    u = "22222222-0000-5000-8000-000000000000"
    bp = us.legacy_body_path(anchor, u)
    bp.parent.mkdir(parents=True, exist_ok=True)
    bp.write_text("OLD\n", encoding="utf-8")
    local = Path(mid) / "CLAUDE.local.md"
    local.write_text(local.read_text(encoding="utf-8").replace(
        us.INDEX_END, "- [Old](uuid:%s) - h <!-- bx:slug=old-fact -->\n%s" % (u, us.INDEX_END)),
        encoding="utf-8")
    rep = E.move_entry(mid, proj, ["fresh", "old-fact"])
    assert rep["moved"] is False and "migrate" in (rep["refused"] or "").lower()
    assert "old-fact" in rep["refused"] and _slugs_at(proj) == set()


def test_cli_move_accepts_a_set_and_keeps_the_single_slug_form(tmp_path, capsys):
    anchor, mid, proj = _three_levels(tmp_path)
    a, b = _citing_pair(anchor)
    rc = E.main(["move", "--from-level", anchor, "--to-level", proj, "--slug", a, "--slug", b])
    out = capsys.readouterr().out
    assert rc == 0 and "moved" in out and a in out and b in out
    assert _slugs_at(proj) == {a, b}
    rc = E.main(["move", "--from-level", proj, "--to-level", anchor, "--slug", a, b])  # one flag
    out = capsys.readouterr().out
    assert rc == 0 and _slugs_at(anchor) == {a, b}
    E.add_or_update_entry(anchor, "Solo", "no refs at all", body="S")
    rc = E.main(["move", "--from-level", anchor, "--to-level", mid, "--slug", "solo"])
    out = capsys.readouterr().out
    assert rc == 0 and out.startswith("moved solo: ")     # unchanged single-slug success line
    assert _slugs_at(mid) == {"solo"}


def test_inbound_ref_sources_scans_hooks_and_bodies(tmp_path):
    anchor, mid, proj = _three_levels(tmp_path)
    E.add_or_update_entry(anchor, "Base rule", "the base", body="B", scope_default="a")
    E.add_or_update_entry(mid, "Hook citer", "see [[base-rule]]", body="plain", scope_default="m")
    E.add_or_update_entry(proj, "Body citer", "h", body="details in [[base_rule]] apply",
                          scope_default="p")
    src = E.inbound_ref_sources([anchor, mid, proj], "base-rule")
    assert {(Path(lvl).name, s) for lvl, s in src} == {("mid", "hook-citer"), ("proj", "body-citer")}
    assert E.has_inbound_refs([anchor, mid, proj], "base-rule") is True
    assert E.has_inbound_refs([anchor, mid, proj], "unreferenced") is False


def test_cli_move_success_and_refusal(tmp_path, capsys):
    anchor, mid, proj = _three_levels(tmp_path)
    E.add_or_update_entry(proj, "F", "h", body="B", scope_default="p")
    rc = E.main(["move", "--from-level", proj, "--to-level", mid, "--slug", "f"])
    out = capsys.readouterr().out
    assert rc == 0 and "moved" in out
    rc = E.main(["move", "--from-level", proj, "--to-level", mid, "--slug", "f"])   # gone now
    out = capsys.readouterr().out
    assert rc == 1 and "! refused:" in out


# ---- lint --tree: voice/frame sweep (defect J) ---------------------------------------------------

def test_lint_tree_reports_over_cap_triggerless_and_unframed(tmp_path, capsys):
    anchor, mid, proj = _three_levels(tmp_path)
    # a within-cap, trigger-first, fully framed entry -> clean, not flagged
    E.add_or_update_entry(proj, "Good", "When X happens, do Y.",
                          body="Prose.\n\n**Why:** reason\n\n**How to apply:** steps", scope_default="p")
    # trigger-less hook + unframed body (no **Why:**/**How to apply:**)
    E.add_or_update_entry(mid, "Bad", "just a statement, no trigger", body="bare prose", scope_default="m")
    # over-HARD-cap hook: add() refuses one, so inject directly to simulate a hand-edited/legacy line
    us.add_pointer(anchor, slug="huge", title="Huge", hook="When " + ("x" * 600) + " do z")
    rc = E.main(["lint", "--tree", proj])
    out = capsys.readouterr().out
    assert rc == 0
    assert "hook over HARD cap" in out and "huge" in out
    assert "hook missing trigger" in out and "bad" in out
    assert "body missing" in out
    # huge (no body) + bad (bare prose) are unframed; good is framed -> exactly 2
    assert "TOTAL over-cap hooks: 1 | trigger-less hooks: 1 | unframed bodies: 2" in out


def test_lint_tree_clean_store_reports_zeros(tmp_path, capsys):
    anchor, mid, proj = _three_levels(tmp_path)
    E.add_or_update_entry(proj, "Fine", "When it applies, act.",
                          body="P.\n\n**Why:** r\n\n**How to apply:** s", scope_default="p")
    rc = E.main(["lint", "--tree", anchor])
    out = capsys.readouterr().out
    assert rc == 0 and "TOTAL over-cap hooks: 0 | trigger-less hooks: 0 | unframed bodies: 0" in out


# ---- multi-tree: tree-top + ensure-all-trees -----------------------------------------------------

def test_tree_top_reports_top_store_and_bootstrap(two_trees):
    info = E.tree_top(str(two_trees.proj_a))
    assert info["top"] == str(two_trees.top_a)
    assert info["store"] == str(two_trees.top_a / ".claude-memory")
    assert info["bootstrap"] is False
    fresh = two_trees.root / "fresh"; fresh.mkdir()
    (fresh / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    assert E.tree_top(str(fresh))["bootstrap"] is True


def test_ensure_all_trees_dry_run_reports_and_writes_nothing(two_trees):
    rep = E.ensure_all_trees(roots=[str(two_trees.root)], apply=False)
    assert {t["top"] for t in rep["trees"]} == {str(two_trees.top_a), str(two_trees.top_b)}
    assert all(t["created"] == [] for t in rep["trees"])
    # the gap level (campaigns/) got NO scaffold in dry-run
    assert not (two_trees.top_a / "campaigns" / "CLAUDE.local.md").exists()


def test_ensure_all_trees_apply_scaffolds_every_member_chain(two_trees):
    rep = E.ensure_all_trees(roots=[str(two_trees.root)], apply=True)
    for tr in rep["trees"]:
        assert tr["status"] == "ok"
    # both trees fully prefilled: every rung between deepest CLAUDE.md and top has both files
    for lvl in (two_trees.proj_a, two_trees.top_a / "campaigns", two_trees.top_a,
                two_trees.proj_b, two_trees.top_b / "recipes", two_trees.top_b):
        assert (lvl / "CLAUDE.md").is_file(), lvl
        assert (lvl / "CLAUDE.local.md").is_file(), lvl
    # trees stay independent: no file written above the tops
    assert not (two_trees.root / "CLAUDE.local.md").exists()


def test_ensure_all_trees_refuses_stray_top_bootstrap(two_trees):
    # a stray CLAUDE.md ABOVE both store-bearing trees must never merge them
    (two_trees.root / "CLAUDE.md").write_text("stray\n", encoding="utf-8")
    rep = E.ensure_all_trees(roots=[str(two_trees.root)], apply=True)
    by_top = {t["top"]: t for t in rep["trees"]}
    stray = by_top[str(two_trees.root)]
    assert stray["status"] == "ambiguous" and "merge" in stray["why"]
    assert stray["created"] == []
    assert not (two_trees.root / "CLAUDE.local.md").exists()   # nothing scaffolded at the stray top
    assert by_top[str(two_trees.top_a)]["status"] == "ok"      # real trees still scaffolded


def test_ensure_all_trees_scaffolds_isolated_bootstrap_tree(tmp_path, monkeypatch):
    home = tmp_path / "home"; (home / ".claude").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home)); monkeypatch.setenv("USERPROFILE", str(home))
    solo = tmp_path / "solo" / "proj"
    solo.mkdir(parents=True)
    (tmp_path / "solo" / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (solo / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    rep = E.ensure_all_trees(roots=[str(tmp_path / "solo")], apply=True)
    assert rep["trees"][0]["status"] == "ok"                   # bootstrap alone is legitimate
    assert (solo / "CLAUDE.local.md").is_file()


def test_cli_tree_top_json(two_trees, capsys):
    rc = E.main(["tree-top", "--proj", str(two_trees.proj_b), "--json"])
    assert rc == 0
    got = json.loads(capsys.readouterr().out)
    assert got["top"] == str(two_trees.top_b) and got["bootstrap"] is False


def test_cli_ensure_all_trees_dry_run_default(two_trees, capsys):
    rc = E.main(["ensure-all-trees", "--roots", str(two_trees.root)])
    out = capsys.readouterr().out
    assert rc == 0 and "DRY-RUN" in out and "2 tree(s)" in out


# ---- heal skip-fast: healthy chain = read-only probe, no lock churn ------------------------------

def test_level_needs_heal_probe(proj):
    E.add_or_update_entry(proj, "F", "h", body="B", scope_default="lvl")
    assert E._level_needs_heal(proj) is True                     # CLAUDE.md marker still missing
    E.heal(proj)
    assert E._level_needs_heal(proj) is False                    # settled = canonical
    local = sig.claude_local_md_path(proj)
    local.write_text(local.read_text(encoding="utf-8") + "\ntrailing junk\n", encoding="utf-8")
    assert E._level_needs_heal(proj) is False                    # outside-block text is the user's
    # corrupt the block itself -> needs heal
    txt = local.read_text(encoding="utf-8").replace("(mem:f)", "(mem:f)  ")
    local.write_text(txt, encoding="utf-8")
    assert E._level_needs_heal(proj) is True


def test_heal_healthy_chain_takes_no_lock(proj, monkeypatch):
    E.add_or_update_entry(proj, "F", "h", body="B", scope_default="lvl")
    E.heal(proj)                                                 # settle to canonical
    calls = []
    real_lock = sig.memory_lock
    monkeypatch.setattr(sig, "memory_lock", lambda p: calls.append(str(p)) or real_lock(p))
    rep = E.heal(proj)
    assert rep["healed"] == [] and calls == []                   # read-only pass, zero locks


def test_heal_still_repairs_when_needed(proj, monkeypatch):
    E.add_or_update_entry(proj, "F", "h", body="B", scope_default="lvl")
    local = sig.claude_local_md_path(proj)
    local.write_text(local.read_text(encoding="utf-8").replace("# Memory index", "# memory index"),
                     encoding="utf-8")
    rep = E.heal(proj)
    assert rep["healed"]                                         # repaired via the lock path
    assert "# Memory index" in local.read_text(encoding="utf-8")


def test_heal_orphan_check_does_not_read_body_contents(proj, monkeypatch):
    E.add_or_update_entry(proj, "F", "h", body="B", scope_default="lvl")
    E.heal(proj)
    reads = []
    real_read = Path.read_text
    def spy(self, *a, **k):
        if str(self).endswith("f.md"):
            reads.append(str(self))
        return real_read(self, *a, **k)
    monkeypatch.setattr(Path, "read_text", spy)
    rep = E.heal(proj)
    assert rep["orphans"] == [] and reads == []                  # stat-only, bodies never opened


# ---- authentic body shape: capture wraps bodies in the native memory-entry frame ----------------

def test_add_wraps_body_with_frontmatter(proj):
    E.add_or_update_entry(proj, "Sunset log", "When renaming, add a sunset line.",
                          body="Renames need a SUNSET.md line.", type_="feedback",
                          scope_default="lvl")
    body = us.body_path(proj, "feedback-sunset-log").read_text(encoding="utf-8")
    assert body.startswith("---\nname: feedback-sunset-log\n")
    assert "description: When renaming, add a sunset line." in body
    assert "  type: feedback" in body
    assert "Renames need a SUNSET.md line." in body


def test_add_keeps_already_framed_body(proj):
    framed = "---\nname: x\ndescription: d\nmetadata:\n  type: project\n---\n\nBody here."
    E.add_or_update_entry(proj, "X", "When x-ing, do y.", body=framed, scope_default="lvl")
    body = us.body_path(proj, "x").read_text(encoding="utf-8")
    assert body.count("---\n") == 2 and "Body here." in body     # not double-framed


def test_add_derives_type_from_slug_prefix_when_untyped(proj):
    E.add_or_update_entry(proj, "Reference thing", "When looking up thing, read this.",
                          body="B", type_="reference", scope_default="lvl")
    E.add_or_update_entry(proj, "Reference thing", "When looking up thing, read this.",
                          body="B2")                              # upsert without type_
    body = us.body_path(proj, "reference-thing").read_text(encoding="utf-8")
    assert "  type: reference" in body                            # type survives via slug prefix


# ---- trigger-first hook lint (advisory, like the length cap) ------------------------------------

def test_hook_missing_trigger_heuristic():
    assert us.hook_missing_trigger("Fix the ROOT cause, never a workaround.") is True
    assert us.hook_missing_trigger("When you hit an error, fix the ROOT cause.") is False
    assert us.hook_missing_trigger("Before committing, run the full suite.") is False
    assert us.hook_missing_trigger("If a hook needs a legend, rename it.") is False
    assert us.hook_missing_trigger("Use when parsing gitignore files.") is False
    assert us.hook_missing_trigger("On every release, prune the plugin cache.") is False


def test_cli_add_warns_on_triggerless_hook(proj, capsys):
    rc = E.main(["add", "--proj", proj, "--title", "T", "--hook",
                 "Do the thing properly.", "--body", "B"])
    out = capsys.readouterr().out
    assert rc == 0 and "~ warning:" in out and "trigger" in out


# ---- recurrence lint: a body recording a repeat IS the escalate signal (advisory) ---------------

def test_recurrence_count_reads_the_explicit_markers():
    assert us.recurrence_count("**Why:** ... recurrence: 3 (last 2026-07-27).") == 3
    assert us.recurrence_count("recurrence 2") == 2
    assert us.recurrence_count("Third occurrence for the runner fleet:") == 3
    assert us.recurrence_count("this is the second occurrence") == 2
    assert us.recurrence_count("4th occurrence, in a shape the guard missed") == 4
    assert us.recurrence_count("hit 4 times in one day") == 4
    assert us.recurrence_count("recurrence: 3 in one session") == 3


def test_recurrence_count_takes_the_highest_marker_present():
    assert us.recurrence_count("recurrence: 2 (last 2026-01-01). Later: 5th occurrence.") == 5


def test_recurrence_count_ignores_prose_that_merely_mentions_recurring():
    """The negative must be reachable, or every add would warn and the signal would be noise."""
    assert us.recurrence_count("When a recurring chore shows up, propose a jig.") is None
    assert us.recurrence_count("this recurrence is annoying") is None
    assert us.recurrence_count("occurrence of a race condition") is None
    assert us.recurrence_count("") is None
    assert us.recurrence_count(None) is None


def test_recurrence_below_the_threshold_is_still_reported_but_does_not_escalate():
    assert us.recurrence_count("recurrence: 1 (last 2026-01-01)") == 1
    assert us.RECURRENCE_ESCALATE_AT == 2


def test_cli_add_warns_when_the_body_records_a_repeat(proj, capsys):
    rc = E.main(["add", "--proj", proj, "--title", "T", "--hook",
                 "When it breaks, fix it.", "--body",
                 "The thing broke again. recurrence: 3 (last 2026-07-27)."])
    out = capsys.readouterr().out
    assert rc == 0, "the recurrence advisory must never fail the add"
    assert "~ warning:" in out and "recurrence 3" in out
    assert "GUARD" in out and "JIG" in out, "it must force the choice between BOTH ladders"


def test_cli_add_stays_quiet_when_the_body_records_no_repeat(proj, capsys):
    rc = E.main(["add", "--proj", proj, "--title", "T2", "--hook",
                 "When it breaks, fix it.", "--body", "A plain fact with no repeat marker."])
    out = capsys.readouterr().out
    assert rc == 0 and "recurrence" not in out


def test_cli_add_slug_targets_existing_identity(proj, capsys):
    E.add_or_update_entry(proj, "Old title", "When testing, hook.", body="B",
                          scope_default="lvl", slug="my-stable-slug")
    rc = E.main(["add", "--proj", proj, "--slug", "my-stable-slug", "--title", "New title",
                 "--hook", "When testing, sharper hook.", "--body", ""])
    assert rc == 0
    _s, entries, _b = E.read_store(proj)
    assert [e.title for e in entries] == ["New title"]            # same identity, no second entry


def test_excluded_dirs_are_never_an_altitude(tmp_path, monkeypatch):
    # /tmp-class dirs (home, tempdir, fs root) must never be scaffolded as a tree top:
    # the anchor resolver already excludes them, but the altitude_chain fallback used to
    # declare the excluded dir "its own top" and scaffold it (bit twice on 2026-07-05).
    import tempfile as TF
    import self_improve_signals as sig
    fake_tmp = tmp_path / "faketmp"
    fake_tmp.mkdir()
    monkeypatch.setattr(TF, "gettempdir", lambda: str(fake_tmp))
    assert sig.altitude_chain(str(fake_tmp)) == []
    created = E.scaffold(str(fake_tmp))
    assert created == []
    assert not (fake_tmp / "CLAUDE.md").exists()
    assert not (fake_tmp / "CLAUDE.local.md").exists()


def test_add_refuses_excluded_proj(tmp_path, monkeypatch):
    import tempfile as TF
    fake_tmp = tmp_path / "faketmp"
    fake_tmp.mkdir()
    monkeypatch.setattr(TF, "gettempdir", lambda: str(fake_tmp))
    import pytest as _pt
    with _pt.raises(Exception):
        E.add_or_update_entry(str(fake_tmp), "T", "When x, do y", body="b", scope_default="lvl")
    assert not (fake_tmp / "CLAUDE.local.md").exists()


# ---- P0-back: relocate (the TRUE cross-tree move) ---------------------------------------
# move_entry refuses cross-tree because the BODY is anchored per tree - moving only the pointer
# would strand it. The only cross-tree path was a COPY, which leaves the stale original behind:
# a learning captured in the wrong tree could never be fully re-homed. relocate closes that.

def _body_text(anchor, slug):
    return us.body_path(us.resolve_anchor(str(anchor)), slug).read_text(encoding="utf-8")


def test_relocate_cross_tree_moves_body_and_leaves_no_duplicate(two_trees):
    """The defining invariant: after a cross-tree relocate the fact exists ONCE, in the target
    tree. A copy that leaves the original is what this verb exists to stop."""
    E.add_or_update_entry(str(two_trees.proj_a), "Bakery Oven Rule", "When baking, preheat.",
                          body="The oven needs 20 minutes.", scope_default="p")
    rep = E.relocate_entry(str(two_trees.proj_a), str(two_trees.proj_b), "bakery-oven-rule")
    assert rep["relocated"] is True and rep["cross_tree"] is True, rep

    # present in the target tree: pointer + body
    _s, ptrs = us.parse_pointer_index(
        (Path(str(two_trees.proj_b)) / "CLAUDE.local.md").read_text(encoding="utf-8"))
    assert "bakery-oven-rule" in {p.slug for p in ptrs}
    assert "oven needs 20 minutes" in _body_text(two_trees.proj_b, "bakery-oven-rule")

    # GONE from the source tree: no pointer, and the body is archived (not live)
    _s2, ptrs2 = us.parse_pointer_index(
        (Path(str(two_trees.proj_a)) / "CLAUDE.local.md").read_text(encoding="utf-8"))
    assert "bakery-oven-rule" not in {p.slug for p in ptrs2}
    assert not us.body_path(us.resolve_anchor(str(two_trees.proj_a)), "bakery-oven-rule").exists()


def test_relocate_archives_the_source_body_rather_than_deleting_it(two_trees):
    E.add_or_update_entry(str(two_trees.proj_a), "F", "h", body="recoverable", scope_default="p")
    E.relocate_entry(str(two_trees.proj_a), str(two_trees.proj_b), "f")
    anchor_a = us.resolve_anchor(str(two_trees.proj_a))
    archived = list((us.central_facts_dir(anchor_a).parent / ".archive").glob("*.md"))
    assert archived and "recoverable" in archived[0].read_text(encoding="utf-8")


def test_relocate_same_tree_delegates_to_move(tmp_path):
    """One verb for callers: within a tree the body already sits at the right anchor, so this is
    exactly a pointer move - do not copy/archive a body that never needed to move."""
    anchor, mid, proj = _three_levels(tmp_path)
    E.add_or_update_entry(proj, "F", "h", body="B", scope_default="p")
    rep = E.relocate_entry(proj, mid, "f")
    assert rep["relocated"] is True and rep["cross_tree"] is False
    assert us.body_path(us.resolve_anchor(proj), "f").is_file()   # body untouched, still live
    _s, ptrs = us.parse_pointer_index((Path(mid) / "CLAUDE.local.md").read_text(encoding="utf-8"))
    assert "f" in {p.slug for p in ptrs}


def test_relocate_refuses_when_target_tree_has_a_divergent_slug(two_trees):
    """Slugs are TREE-unique. Landing on an existing, different fact would silently destroy it."""
    E.add_or_update_entry(str(two_trees.proj_a), "F", "hook one", body="B1", scope_default="p")
    E.add_or_update_entry(str(two_trees.proj_b), "F", "hook two - different", body="B2",
                          scope_default="p")
    rep = E.relocate_entry(str(two_trees.proj_a), str(two_trees.proj_b), "f")
    assert rep["relocated"] is False and "already" in (rep["refused"] or "").lower(), rep
    # nothing destroyed on either side
    assert "B1" in _body_text(two_trees.proj_a, "f")
    assert "B2" in _body_text(two_trees.proj_b, "f")


def test_relocate_refuses_when_it_would_dangle_an_inbound_ref(two_trees):
    """A fact leaving the tree dangles every [[ref]] to it that stays behind."""
    E.add_or_update_entry(str(two_trees.proj_a), "Target", "t", body="B", scope_default="p")
    E.add_or_update_entry(str(two_trees.proj_a), "Citer", "c", body="see [[target]]",
                          scope_default="p")
    rep = E.relocate_entry(str(two_trees.proj_a), str(two_trees.proj_b), "target")
    assert rep["relocated"] is False and "dangl" in (rep["refused"] or "").lower(), rep


def test_relocate_force_overrides_the_dangling_refusal_with_a_warning(two_trees):
    E.add_or_update_entry(str(two_trees.proj_a), "Target", "t", body="B", scope_default="p")
    E.add_or_update_entry(str(two_trees.proj_a), "Citer", "c", body="see [[target]]",
                          scope_default="p")
    rep = E.relocate_entry(str(two_trees.proj_a), str(two_trees.proj_b), "target", force=True)
    assert rep["relocated"] is True and any("dangl" in w.lower() for w in rep["warnings"]), rep


def test_relocate_missing_slug_is_refused(two_trees):
    rep = E.relocate_entry(str(two_trees.proj_a), str(two_trees.proj_b), "nope")
    assert rep["relocated"] is False and "not found" in (rep["refused"] or "")


# ---- an empty body on a NEW fact is data loss, not a terse entry --------------------------------

def test_a_new_fact_with_an_empty_body_is_refused(proj):
    """A frame-only fact ships a convincing always-loaded hook with nothing behind it.

    The pointer promises a rule and the retrieval recipe delivers an empty file, and no integrity
    check reports it - so refuse at the only moment the content still exists to supply.
    """
    for empty in ("", "   \n\n  "):
        with pytest.raises(E.EmptyBody):
            E.add_or_update_entry(proj, "Bodyless", "When x happens, do y.", body=empty)


def test_the_refusal_writes_nothing(proj):
    """Refused BEFORE the lock, like an over-cap hook: no pointer line, no body file."""
    with pytest.raises(E.EmptyBody):
        E.add_or_update_entry(proj, "Bodyless", "When x happens, do y.", body="")
    local = Path(proj) / "CLAUDE.local.md"
    assert not local.exists() or "bodyless" not in local.read_text(encoding="utf-8")


def test_an_UPDATE_may_still_omit_the_body(proj):
    """Empty body on an existing slug keeps the stored one - that is the documented update path."""
    slug = E.add_or_update_entry(proj, "Real", "When x, do y.", body="a real body")
    again = E.add_or_update_entry(proj, "Real", "When x, do z.", body="")
    assert again == slug
    body = us.body_path(Path(E._anchor(proj)), slug).read_text(encoding="utf-8")
    assert "a real body" in body


def test_a_new_fact_with_a_real_body_still_works(proj):
    """Must-not-break: the refusal is for EMPTY only."""
    slug = E.add_or_update_entry(proj, "Fine", "When x, do y.", body="something worth reading")
    assert us.body_path(Path(E._anchor(proj)), slug).is_file()


def test_move_refusal_names_the_field_that_actually_differs(tmp_path):
    # The refusal condition compares the (title, hook) TUPLE, so it also fires when ONLY the title
    # differs - and then "a DIFFERENT hook" sends the reader to diff two identical hooks. Measured
    # on the real store: two pointers with byte-identical 497-char hooks whose titles differed by a
    # leading "The ". Name the field that actually differs.
    anchor, mid, proj = _three_levels(tmp_path)
    same_hook = "When several agents work together, derive the structure from the real constraints."
    E.add_or_update_entry(proj, "Dag scheduler", same_hook, body="B", scope_default="p")
    us.add_pointer(mid, slug="dag-scheduler", title="The Dag scheduler", hook=same_hook)
    rep = E.move_entry(proj, mid, "dag-scheduler")
    assert rep["moved"] is False
    msg = rep["refused"] or ""
    assert "TITLE" in msg, msg
    assert "DIFFERENT hook" not in msg, msg


def test_move_refusal_still_names_the_hook_when_the_hook_differs(tmp_path):
    # The direction where the exemption must NOT apply: a genuinely divergent hook still reports
    # HOOK, so narrowing the message cannot silence the case the guard was built for.
    anchor, mid, proj = _three_levels(tmp_path)
    E.add_or_update_entry(proj, "Fact", "thin source hook", body="B", scope_default="p")
    us.add_pointer(mid, slug="fact", title="Fact", hook="a much richer target hook with detail")
    rep = E.move_entry(proj, mid, "fact")
    assert rep["moved"] is False
    assert "HOOK" in (rep["refused"] or ""), rep["refused"]


def test_update_with_a_new_body_keeps_the_stored_type(proj):
    # A slug carries a type only when it was minted WITH one ("feedback-..."). 71 of the tree's
    # prefix-less facts record a non-project type, and for those the body's frontmatter is the ONLY
    # record of it - so re-deriving the type from the slug on an update silently rewrites the fact's
    # kind. Nothing downstream reports it: store_manifest verify reads (level, slug, title, pin),
    # lint --tree looks for UNFRAMED bodies, and the engine prints its usual success line.
    slug = E.add_or_update_entry(proj, "A configured gate can enforce nothing",
                                 "When you add a tool to a gate, verify what it ENFORCES.",
                                 body="the prose", type_="feedback",
                                 slug="a-configured-gate-can-enforce-nothing", scope_default="lvl")
    assert "type: feedback" in us.body_path(proj, slug).read_text(encoding="utf-8")
    E.add_or_update_entry(proj, "A configured gate can enforce nothing",
                          "When you add a tool to a gate, verify what it ENFORCES, not that it runs.",
                          body="the amended prose", slug=slug)      # no type_ -> must not re-derive
    body = us.body_path(proj, slug).read_text(encoding="utf-8")
    assert "type: feedback" in body and "type: project" not in body
    assert "the amended prose" in body


def test_an_explicit_type_still_wins_on_update(proj):
    # The preservation above must not freeze the type: a caller that PASSES one is changing it
    # deliberately, and that is the one route to a re-classification.
    slug = E.add_or_update_entry(proj, "Note", "When X, do Y.", body="b", type_="feedback",
                                 slug="note-under-test", scope_default="lvl")
    E.add_or_update_entry(proj, "Note", "When X, do Y.", body="b2", type_="reference", slug=slug)
    body = us.body_path(proj, slug).read_text(encoding="utf-8")
    assert "type: reference" in body and "type: feedback" not in body


def test_amend_pinned_keeps_the_stored_type_when_none_is_given(proj):
    slug = E.add_or_update_entry(proj, "Iron rule", "When X happens, do Y.", body="prose",
                                 type_="feedback", pin=True, slug="iron-rule-under-test",
                                 scope_default="lvl")
    E.amend_pinned_entry(proj, slug, body="amended prose")
    body = us.body_path(proj, slug).read_text(encoding="utf-8")
    assert "type: feedback" in body and "type: project" not in body


def test_amend_pinned_can_change_the_type_deliberately(proj):
    # A pinned fact is exactly the kind whose classification matters most - the always-loaded iron
    # rules - and `add` refuses a pinned entry, so this verb is the ONLY route to its type. Without
    # it a pinned fact captured under the wrong kind is frozen for good.
    slug = E.add_or_update_entry(proj, "Iron rule", "When X happens, do Y.", body="prose",
                                 type_="project", pin=True, slug="iron-rule-retype-test",
                                 scope_default="lvl")
    E.amend_pinned_entry(proj, slug, body="amended prose", type_="feedback")
    body = us.body_path(proj, slug).read_text(encoding="utf-8")
    assert "type: feedback" in body and "type: project" not in body
    _s, entries, _b = E.read_store(proj)
    assert [e for e in entries if e.slug == slug][0].pin is True    # re-typing never unpins
