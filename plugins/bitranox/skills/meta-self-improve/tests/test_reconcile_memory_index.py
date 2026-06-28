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
# reconcile
# --------------------------------------------------------------------------

def test_backfills_missing_line(tmp_path):
    write(tmp_path, "a.md", topic("a", "hook a"))
    write(tmp_path, "b.md", topic("b", "hook b"))
    write(tmp_path, "MEMORY.md", "# Memory index\n\n- [A](a.md) - hook a\n")
    rep = R.reconcile(tmp_path)
    assert rep["added"] == ["b.md"]
    idx = (tmp_path / "MEMORY.md").read_text(encoding="utf-8")
    assert "(b.md)" in idx
    assert "(a.md)" in idx  # existing line preserved


def test_idempotent(tmp_path):
    write(tmp_path, "a.md", topic("a", "hook a"))
    R.reconcile(tmp_path)
    first = (tmp_path / "MEMORY.md").read_text(encoding="utf-8")
    rep2 = R.reconcile(tmp_path)
    assert rep2["added"] == []
    assert (tmp_path / "MEMORY.md").read_text(encoding="utf-8") == first


def test_orphan_reported_not_deleted(tmp_path):
    write(tmp_path, "a.md", topic("a", "hook a"))
    write(tmp_path, "MEMORY.md", "# Memory index\n\n- [A](a.md) - hook a\n- [Ghost](ghost.md) - gone\n")
    rep = R.reconcile(tmp_path)
    assert "ghost.md" in rep["orphans"]
    assert "(ghost.md)" in (tmp_path / "MEMORY.md").read_text(encoding="utf-8")  # not deleted


def test_frontmatterless_file_still_backfilled(tmp_path):
    write(tmp_path, "plain.md", "# Plain Heading\n\nsome content.\n")
    rep = R.reconcile(tmp_path)
    assert "plain.md" in rep["added"]
    idx = (tmp_path / "MEMORY.md").read_text(encoding="utf-8")
    assert "[Plain Heading](plain.md)" in idx


def test_creates_index_when_absent(tmp_path):
    write(tmp_path, "a.md", topic("a", "hook a"))
    rep = R.reconcile(tmp_path)
    idx = (tmp_path / "MEMORY.md").read_text(encoding="utf-8")
    assert idx.startswith("# Memory index")
    assert "(a.md)" in idx
    assert rep["topics"] == 1


def test_dry_run_writes_nothing(tmp_path):
    write(tmp_path, "a.md", topic("a", "hook a"))
    rep = R.reconcile(tmp_path, dry_run=True)
    assert rep["added"] == ["a.md"]
    assert not (tmp_path / "MEMORY.md").exists()


def test_main_dry_run(tmp_path, capsys):
    write(tmp_path, "a.md", topic("a", "hook a"))
    rc = R.main([str(tmp_path), "--dry-run"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "would add" in out
    assert not (tmp_path / "MEMORY.md").exists()


# --------------------------------------------------------------------------
# cross-altitude reference integrity (upward-only, no orphans) + over-cap
# --------------------------------------------------------------------------

def _chain(tmp_path):
    """Two-altitude chain: project memory (narrow) -> global rules (broad)."""
    proj = tmp_path / "proj"
    glob = tmp_path / "global"
    proj.mkdir()
    glob.mkdir()
    return proj, glob


def test_check_references_upward_ok(tmp_path):
    proj, glob = _chain(tmp_path)
    write(proj, "delta.md", "References [[fleet-ssh]] plus our subnet detail.")
    write(glob, "fleet-ssh.md", "Log into the fleet with key X.")
    rep = R.check_references([proj, glob])
    assert rep["orphans"] == [] and rep["downward"] == []
    assert rep["checked"] >= 1


def test_check_references_orphan(tmp_path):
    proj, glob = _chain(tmp_path)
    write(proj, "delta.md", "References [[does-not-exist]].")
    rep = R.check_references([proj, glob])
    assert ("delta", "does-not-exist") in rep["orphans"]


def test_check_references_downward_flagged(tmp_path):
    proj, glob = _chain(tmp_path)
    write(proj, "local-thing.md", "project-only detail")
    write(glob, "general.md", "Bad: a global rule pointing DOWN to [[local-thing]].")
    rep = R.check_references([proj, glob])
    assert ("general", "local-thing") in rep["downward"]
    assert rep["orphans"] == []


def test_check_references_altitude_prefixed_slug(tmp_path):
    proj, glob = _chain(tmp_path)
    write(proj, "delta.md", "See [[global:fleet-ssh]] for the base rule.")
    write(glob, "fleet-ssh.md", "base rule")
    rep = R.check_references([proj, glob])
    assert rep["orphans"] == [] and rep["downward"] == []


def test_check_references_recurses_global_subdirs(tmp_path):
    proj, glob = _chain(tmp_path)
    (glob / "net").mkdir()
    write(proj, "delta.md", "References [[fleet-ssh]].")
    write(glob / "net", "fleet-ssh.md", "nested global rule")
    rep = R.check_references([proj, glob])
    assert rep["orphans"] == [] and rep["downward"] == []


def test_over_cap_ok_and_exceeds(tmp_path):
    small = write(tmp_path, "MEMORY.md", "# Memory index\n- a\n- b\n")
    ok, lines, _ = R.over_cap(small)
    assert ok and lines == 3
    big = write(tmp_path, "BIG.md", "x\n" * 250)
    ok2, lines2, _ = R.over_cap(big)
    assert not ok2 and lines2 == 250


def test_main_check_exit_codes(tmp_path, capsys):
    proj, glob = _chain(tmp_path)
    write(proj, "delta.md", "References [[fleet-ssh]].")
    write(glob, "fleet-ssh.md", "ok")
    assert R.main([str(proj), str(glob), "--check"]) == 0
    write(proj, "bad.md", "References [[nope]].")
    assert R.main([str(proj), str(glob), "--check"]) == 1
    assert "orphan ref" in capsys.readouterr().out


# --------------------------------------------------------------------------
# demotion safety (inbound refs) + forgetting (archive)
# --------------------------------------------------------------------------

def test_has_inbound_refs(tmp_path):
    proj, glob = _chain(tmp_path)
    write(proj, "delta.md", "References [[fleet-ssh]].")
    write(glob, "fleet-ssh.md", "the general rule")
    assert R.has_inbound_refs([proj, glob], "fleet-ssh") is True    # delta points up at it -> keep
    assert R.has_inbound_refs([proj, glob], "delta") is False       # nothing points at delta


def test_archive_entry_moves_body_and_drops_index(tmp_path):
    d = tmp_path / "memory"
    d.mkdir()
    write(d, "stale.md", topic("stale", "an idle note"))
    write(d, "MEMORY.md", "# Memory index\n- [Stale](stale.md) - an idle note\n- [Keep](keep.md) - x\n")
    assert R.archive_entry(d, "stale.md") is True
    assert not (d / "stale.md").exists()
    assert (d / ".archive" / "stale.md").is_file()                 # body preserved (cold), not deleted
    idx = (d / "MEMORY.md").read_text(encoding="utf-8")
    assert "stale.md" not in idx and "keep.md" in idx              # only the stale index line dropped


def test_archive_entry_refuses_missing_or_index(tmp_path):
    d = tmp_path / "memory"
    d.mkdir()
    assert R.archive_entry(d, "nope.md") is False
    assert R.archive_entry(d, "MEMORY.md") is False
