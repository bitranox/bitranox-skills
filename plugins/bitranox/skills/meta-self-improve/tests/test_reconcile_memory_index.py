"""Tests for reconcile_memory_index.py.

Builds synthetic memory dirs in tmp_path. All content ASCII.
"""

import reconcile_memory_index as R


def topic(meta_name, description, body="Some body text.", extra=""):
    fm = "---\nname: %s\ndescription: %s\nmetadata:\n  type: project\n---\n" % (meta_name, description)
    return fm + extra + "\n" + body + "\n"


def write(d, name, text):
    p = d / name
    p.write_text(text, encoding="utf-8")
    return p


# --------------------------------------------------------------------------
# frontmatter parsing
# --------------------------------------------------------------------------

def test_parse_frontmatter_basic():
    meta, body = R.parse_frontmatter("---\nname: foo\ndescription: a hook\n---\n\nbody here\n")
    assert meta["name"] == "foo"
    assert meta["description"] == "a hook"
    assert "body here" in body


def test_parse_frontmatter_quoted_multiline():
    text = '---\nname: x\ndescription: "line one\n  line two"\nmetadata:\n  type: project\n---\nB\n'
    meta, _ = R.parse_frontmatter(text)
    assert meta["description"].startswith("line one")
    assert "line two" in meta["description"]


def test_parse_frontmatter_none():
    meta, body = R.parse_frontmatter("no frontmatter here\n")
    assert meta == {}
    assert "no frontmatter" in body


# --------------------------------------------------------------------------
# derive helpers
# --------------------------------------------------------------------------

def test_derive_title_prefers_body_heading():
    assert R.derive_title({"name": "project_x"}, "# Real Title\n\nbody", "f.md") == "Real Title"


def test_derive_title_deslugs_and_drops_type_prefix():
    assert R.derive_title({"name": "project_matrix_id_scheme"}, "no heading", "f.md") == "Matrix id scheme"


def test_derive_hook_uses_description_capped():
    long = "x" * 400
    hook = R.derive_hook({"description": long}, "body")
    assert len(hook) <= R._HOOK_MAX
    assert hook.endswith("...")


def test_derive_hook_falls_back_to_first_sentence():
    assert R.derive_hook({}, "First sentence here. Second one.") == "First sentence here."




# --------------------------------------------------------------------------
# curated altitude: reconcile + reference integrity (pointer block + central bodies)
# --------------------------------------------------------------------------

import pytest  # noqa: E402

import memory_engine as ME  # noqa: E402  (reconcile put hooks/ on sys.path at import)
import uuid_store as us  # noqa: E402


@pytest.fixture
def proj(tmp_path):
    p = tmp_path / "proj"
    p.mkdir()
    return str(p)


def test_is_curated_detection(tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()
    assert R.is_curated(plain) is False
    cur = tmp_path / "lvl"
    cur.mkdir()
    ME.add_or_update_entry(str(cur), "A fact", "hook", body="b", scope_default="lvl")
    assert R.is_curated(cur) is True                    # its CLAUDE.local.md holds a pointer block


def test_reconcile_reports_orphan_pointer_when_body_missing(proj):
    slug = ME.add_or_update_entry(proj, "Heavy", "h", body="x" * 400, scope_default="lvl")
    us.body_path(proj, slug).unlink()                       # delete the central body
    rep = R.reconcile(proj)
    assert "heavy" in rep["orphans"] and rep["added"] == []  # reported, never fabricated/backfilled


def test_reconcile_no_orphans_when_bodies_present(proj):
    ME.add_or_update_entry(proj, "Tiny", "hook", body="small", scope_default="lvl")
    rep = R.reconcile(proj)
    assert rep["orphans"] == [] and rep["facts"] == 1


def test_check_references_target_resolves_no_false_orphan(proj):
    ME.add_or_update_entry(proj, "General", "the general rule", body="short", scope_default="lvl")
    ME.add_or_update_entry(proj, "Specific", "see [[general]] for the base", body="short2")
    refs = R.check_references([proj])
    assert refs["orphans"] == [] and refs["checked"] >= 1


def test_check_references_orphan_flagged(proj):
    ME.add_or_update_entry(proj, "Only", "refers [[nowhere]]", body="b", scope_default="lvl")
    refs = R.check_references([proj])
    assert ("only", "nowhere") in refs["orphans"]


def test_check_references_downward_flagged(tmp_path):
    # source at a BROADER altitude (pos 1) referencing a target only at a NARROWER one (pos 0)
    lower = str(tmp_path / "lower")
    upper = str(tmp_path / "upper")
    (tmp_path / "lower").mkdir(); (tmp_path / "upper").mkdir()
    ME.add_or_update_entry(lower, "Low fact", "narrow", body="b", scope_default="l")
    ME.add_or_update_entry(upper, "High fact", "points [[low-fact]] down", body="b", scope_default="u")
    refs = R.check_references([lower, upper])
    assert ("high-fact", "low-fact") in refs["downward"]


def test_has_inbound_refs_detects_and_is_separator_insensitive(proj):
    ME.add_or_update_entry(proj, "Base rule", "b", body="x", scope_default="lvl")
    ME.add_or_update_entry(proj, "User", "cites [[base_rule]]", body="x")  # underscore form
    assert R.has_inbound_refs([proj], "base-rule") is True
    assert R.has_inbound_refs([proj], "base_rule") is True
    assert R.has_inbound_refs([proj], "nonexistent") is False


def test_over_cap_measures_the_pointer_block(proj):
    ME.add_or_update_entry(proj, "R", "h", body="small", scope_default="lvl")
    within, lines, nbytes = R.over_cap(proj)
    assert within is True and nbytes > 0
    within2, *_ = R.over_cap(proj, max_bytes=1)          # any real block exceeds a 1-byte budget
    assert within2 is False


def test_oversize_pointer_block_is_advisory_warning_not_a_failure(proj, capsys):
    # A pointer block past the soft byte threshold WARNS but never fails --check (exit 0).
    local = ME.sig.claude_local_md_path(proj)
    lines = "\n".join("- [T%d](uuid:0000000%d-0000-5000-8000-000000000000) - a hook <!-- bx:slug=t%d -->"
                      % (i, i % 10, i) for i in range(3000))
    local.write_text("%s\n# Memory index\n\n%s\n%s\n" % (us.INDEX_BEGIN, lines, us.INDEX_END),
                     encoding="utf-8")
    assert len((local.read_text(encoding="utf-8")).encode("utf-8")) > R._WARN_BYTES
    rc = R.main(["--check", proj])
    out = capsys.readouterr().out
    assert rc == 0                          # size never contributes to the exit code
    assert "~ warning:" in out and "TOTAL warnings:" in out and "TOTAL problems: 0" in out


def test_archive_entry_drops_pointer_and_moves_central_body(proj):
    ME.add_or_update_entry(proj, "Tiny", "h", body="small", scope_default="lvl")
    heavy_slug = ME.add_or_update_entry(proj, "Heavy", "h", body="x" * 400)
    assert R.archive_entry(proj, "heavy") is True
    assert (us.central_facts_dir(proj).parent / ".archive" / (heavy_slug + ".md")).is_file()
    assert R.archive_entry(proj, "tiny") is True
    _scope, entries, _bodies = ME.read_store(proj)
    assert entries == []
    assert R.archive_entry(proj, "nonexistent") is False


# ---- tree-wide integrity (--check-tree): duplicates/orphans/dangling across siblings -----------

def _tree_two_projects(tmp_path):
    """anchor (CLAUDE.md + store) with two SIBLING project levels projA/projB below it."""
    anchor = tmp_path / "tree"
    a, b = anchor / "projA", anchor / "projB"
    a.mkdir(parents=True)
    b.mkdir(parents=True)
    for d in (anchor, a, b):
        (d / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (anchor / us.STORE_DIRNAME).mkdir()
    return str(anchor), str(a), str(b)


def test_check_tree_flags_duplicate_pointer_across_siblings(tmp_path, capsys):
    # The tree-uniqueness violation that chain-scoped --check cannot see: one slug pointed at from
    # two SIBLING levels (different chains). heal reports clean; --check-tree must catch it and exit 1.
    anchor, a, b = _tree_two_projects(tmp_path)
    ME.add_or_update_entry(a, "Shared", "hookA", body="B", scope_default="a")
    us.add_pointer(b, slug="shared", title="Shared", hook="hookB")   # duplicate pointer at the sibling
    rc = R.main(["--check-tree", anchor])
    out = capsys.readouterr().out
    assert rc == 1
    assert "duplicate pointer: shared" in out and "TOTAL tree problems: 1" in out


def test_check_tree_clean_tree_is_zero_and_exits_0(tmp_path, capsys):
    anchor, a, b = _tree_two_projects(tmp_path)
    ME.add_or_update_entry(a, "Only A", "h", body="B", scope_default="a")
    ME.add_or_update_entry(b, "Only B", "h", body="B", scope_default="b")
    rc = R.main(["--check-tree", anchor])
    out = capsys.readouterr().out
    assert rc == 0 and "TOTAL tree problems: 0" in out


def test_check_tree_flags_orphan_ref_and_reports_dangling_body(tmp_path, capsys):
    anchor, a, b = _tree_two_projects(tmp_path)
    ME.add_or_update_entry(a, "Citer", "builds on [[missing-base]]", body="B", scope_default="a")
    # a dangling body: a central body file no level points at
    us.put_body(anchor, "ghost-fact", "---\nname: ghost-fact\n---\n\norphaned body\n")
    rc = R.main(["--check-tree", anchor])
    out = capsys.readouterr().out
    assert rc == 1
    assert "orphan ref: [[missing-base]]" in out
    assert "dangling body (no pointer at any level): ghost-fact" in out


def test_check_tree_flags_downward_sideways_ref(tmp_path, capsys):
    # a fact in subtree A cites a fact that lives in SIBLING subtree B -> it resolves "somewhere" in
    # the tree (so it is NOT an orphan ref) but dangles for A's cascade -> must be flagged as
    # sideways/downward. This is the gap the earlier --check-tree missed vs the per-chain --check.
    anchor, a, b = _tree_two_projects(tmp_path)
    ME.add_or_update_entry(b, "Target", "the target", body="body", scope_default="b")   # slug 'target' at projB
    ME.add_or_update_entry(a, "Citer", "see [[target]]", body="x", scope_default="a")   # projA cites it
    rc = R.main(["--check-tree", anchor])
    out = capsys.readouterr().out
    assert rc == 1
    assert "sideways/downward ref" in out and "target" in out
    assert "TOTAL tree problems: 1" in out


def test_check_tree_upward_ref_not_flagged(tmp_path, capsys):
    # a fact citing an ANCESTOR's fact is a valid upward ref -> not flagged.
    anchor, a, b = _tree_two_projects(tmp_path)
    ME.add_or_update_entry(anchor, "Base", "base rule", body="body", scope_default="top")
    ME.add_or_update_entry(a, "Citer", "builds on [[base]]", body="x", scope_default="a")
    rc = R.main(["--check-tree", anchor])
    out = capsys.readouterr().out
    assert rc == 0 and "TOTAL tree problems: 0" in out


def test_check_tree_function_returns_duplicate_map(tmp_path):
    anchor, a, b = _tree_two_projects(tmp_path)
    ME.add_or_update_entry(a, "Shared", "hookA", body="B", scope_default="a")
    us.add_pointer(b, slug="shared", title="Shared", hook="hookB")
    rep = R.check_tree(anchor)
    assert "shared" in rep["duplicates"] and len(rep["duplicates"]["shared"]) == 2


def test_cli_archive_drops_pointer_and_moves_body(proj, capsys):
    # Defect E: archive_entry had no CLI path (was importable only). --archive <slug> <level> wires it.
    heavy_slug = ME.add_or_update_entry(proj, "Heavy one", "h", body="x" * 400, scope_default="lvl")
    rc = R.main(["--archive", heavy_slug, proj])
    out = capsys.readouterr().out
    assert rc == 0 and "archived %s" % heavy_slug in out
    assert (us.central_facts_dir(proj).parent / ".archive" / (heavy_slug + ".md")).is_file()
    assert ME.read_store(proj)[1] == []                       # pointer gone
    # archiving a slug that is not there reports so and exits 1 (a loud no-op, not silent success)
    rc = R.main(["--archive", "nonexistent", proj])
    out = capsys.readouterr().out
    assert rc == 1 and "no such entry" in out


def test_noncurated_level_contributes_nothing_no_subtree_scan(tmp_path):
    # a plain project dir (no pointer block) must NOT be rglob'd for *.md - else docs/code with
    # `[[section]]` TOML or `[[ref]]` examples manufacture false orphan refs.
    proj = tmp_path / "plainproj"
    (proj / "docs").mkdir(parents=True)
    (proj / "docs" / "guide.md").write_text("see [[tool.importlinter.contracts]] and [[nowhere]]\n",
                                             encoding="utf-8")
    assert R.is_curated(proj) is False
    assert R.altitude_targets(proj) == set()
    assert R.altitude_sources(proj) == []
    refs = R.check_references([str(proj)])
    assert refs["orphans"] == [] and refs["checked"] == 0   # nothing scanned from a plain dir
