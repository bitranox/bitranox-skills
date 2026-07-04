"""Tests for memory_engine.py (the single write path, UUID-native). All content ASCII.

Store format under test: a per-altitude pointer block inline in `CLAUDE.local.md`
(`- [Title](uuid:X) - hook <!-- bx:src=.. bx:pin bx:slug=s -->`) + central bodies at
`<anchor>/.claude-memory/facts/<shard>/<uuid>.md`. Slug is the logical identity; uuid is the body key.
"""

import json
from pathlib import Path

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
                          source=["cap"], pin=True, scope_default="proj")
    body = us.body_path(anchor, "shared-rule")
    before = body.read_text(encoding="utf-8")
    rep = E.move_entry(proj, mid, "shared-rule")
    assert rep["moved"] is True and rep["refused"] is None and rep["direction"] == "up"
    assert body.read_text(encoding="utf-8") == before            # body file untouched
    _s, ptrs_from = us.parse_pointer_index((Path(proj) / "CLAUDE.local.md").read_text(encoding="utf-8"))
    assert "shared-rule" not in {p.slug for p in ptrs_from}      # gone at source
    _s, ptrs_to = us.parse_pointer_index((Path(mid) / "CLAUDE.local.md").read_text(encoding="utf-8"))
    got = {p.slug: p for p in ptrs_to}
    assert "shared-rule" in got and got["shared-rule"].pin and got["shared-rule"].source == {"cap"}
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
    E.add_or_update_entry(proj, "F", "h", body="B", source=["s1"], scope_default="p")
    us.add_pointer(mid, slug="f", title="F", hook="h", source={"s2"})   # simulated crash residue
    rep = E.move_entry(proj, mid, "f")
    assert rep["moved"] is True
    _s, ptrs = us.parse_pointer_index((Path(mid) / "CLAUDE.local.md").read_text(encoding="utf-8"))
    got = {p.slug: p for p in ptrs}
    assert got["f"].source == {"s1", "s2"}                       # merged, single line
    assert "f" not in {p.slug for p in us.parse_pointer_index(
        (Path(proj) / "CLAUDE.local.md").read_text(encoding="utf-8"))[1]}


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
