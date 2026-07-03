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
# curated store: reconcile + reference integrity (index.md + facts/)
# --------------------------------------------------------------------------

import pytest  # noqa: E402

import memory_engine as ME  # noqa: E402  (reconcile put hooks/ on sys.path at import)


@pytest.fixture
def proj(tmp_path):
    p = tmp_path / "proj"
    p.mkdir()
    return str(p)


def _curated(proj):
    return ME.sig.claude_memory_dir(proj)


def test_is_curated_detection(tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()
    assert R.is_curated(plain) is False
    cur = tmp_path / ".claude-bx-selflearning"
    cur.mkdir()
    (cur / "index.md").write_text("x", encoding="utf-8")
    assert R.is_curated(cur) is True


def test_reconcile_backfills_orphan_facts_file(proj):
    ME.add_or_update_entry(proj, "Tiny", "hook", body="small", scope_default="lvl")
    d = _curated(proj)
    (d / "facts").mkdir(exist_ok=True)
    (d / "facts" / "extra-note.md").write_text(
        "---\nname: extra-note\ndescription: an extra note\n---\nbody", encoding="utf-8")
    rep = R.reconcile(d)
    assert "extra-note.md" in rep["added"]
    _, entries = ME.parse((d / "index.md").read_text(encoding="utf-8"))
    assert "extra-note" in [e.slug for e in entries]


def test_reconcile_idempotent(proj):
    ME.add_or_update_entry(proj, "Heavy", "h", body="x" * 400, scope_default="lvl")
    d = _curated(proj)
    R.reconcile(d)
    rep2 = R.reconcile(d)
    assert rep2["added"] == []


def test_reconcile_dry_run_writes_nothing(proj):
    ME.add_or_update_entry(proj, "Tiny", "hook", body="small", scope_default="lvl")
    d = _curated(proj)
    (d / "facts").mkdir(exist_ok=True)
    (d / "facts" / "new.md").write_text("---\nname: new\ndescription: d\n---\nb", encoding="utf-8")
    before = (d / "index.md").read_text(encoding="utf-8")
    rep = R.reconcile(d, dry_run=True)
    assert rep["added"] == ["new.md"] and (d / "index.md").read_text(encoding="utf-8") == before


def test_reconcile_reports_orphan_heavy_entry(proj):
    # a heavy entry whose facts/ file was deleted -> reported, not removed
    ME.add_or_update_entry(proj, "Heavy", "h", body="x" * 400, scope_default="lvl")
    d = _curated(proj)
    (d / "facts" / "heavy.md").unlink()
    rep = R.reconcile(d)
    assert "heavy" in rep["orphans"]


def test_check_references_inline_target_is_not_a_false_orphan(proj):
    # the KEY fix: a [[ref]] to an INLINED fact resolves (inline #slug is a valid target)
    ME.add_or_update_entry(proj, "General", "the general rule", body="short", scope_default="lvl")
    ME.add_or_update_entry(proj, "Specific", "see [[general]] for the base", body="short2")
    d = _curated(proj)
    refs = R.check_references([d, str(_curated(proj)) + "-glob"])
    assert refs["orphans"] == [] and refs["checked"] >= 1


def test_check_references_orphan_flagged(proj):
    ME.add_or_update_entry(proj, "Only", "refers [[nowhere]]", body="b", scope_default="lvl")
    d = _curated(proj)
    refs = R.check_references([d])
    assert ("only", "nowhere") in refs["orphans"]


def test_check_references_downward_flagged(tmp_path):
    # source at a BROADER altitude (pos 1) referencing a target only at a NARROWER one (pos 0)
    lower = str(tmp_path / "lower")
    upper = str(tmp_path / "upper")
    (tmp_path / "lower").mkdir(); (tmp_path / "upper").mkdir()
    ME.add_or_update_entry(lower, "Low fact", "narrow", body="b", scope_default="l")
    ME.add_or_update_entry(upper, "High fact", "points [[low-fact]] down", body="b", scope_default="u")
    refs = R.check_references([_curated(lower), _curated(upper)])
    assert ("high-fact", "low-fact") in refs["downward"]


def test_has_inbound_refs_detects_and_is_separator_insensitive(proj):
    ME.add_or_update_entry(proj, "Base rule", "b", body="x", scope_default="lvl")
    ME.add_or_update_entry(proj, "User", "cites [[base_rule]]", body="x")  # underscore form
    d = _curated(proj)
    assert R.has_inbound_refs([d], "base-rule") is True
    assert R.has_inbound_refs([d], "base_rule") is True
    assert R.has_inbound_refs([d], "nonexistent") is False


def test_over_cap_within_advisory_budget_and_pin(proj):
    ME.add_or_update_entry(proj, "R", "h", body="small", pin=True, scope_default="lvl")
    within, lines, nbytes, pin_bytes = R.over_cap(_curated(proj) / "index.md")
    assert within is True and pin_bytes > 0
    within2, *_ = R.over_cap(_curated(proj) / "index.md", max_pin_bytes=1)  # pinned past tiny budget
    assert within2 is False


def test_oversize_index_is_advisory_warning_not_a_failure(proj, capsys):
    # An index.md past the soft byte threshold WARNS but never fails --check (exit 0, not counted).
    d = _curated(proj)
    d.mkdir(parents=True, exist_ok=True)
    big = "<!-- scope -->\n" + ("- [T](facts/n.md) - a hook line\n" * 2000)  # > _WARN_BYTES bytes
    (d / "index.md").write_text(big, encoding="utf-8")
    assert len(big.encode("utf-8")) > R._WARN_BYTES
    rc = R.main(["--check", str(d)])
    out = capsys.readouterr().out
    assert rc == 0                          # size never contributes to the exit code
    assert "~ warning:" in out
    assert "TOTAL warnings:" in out
    assert "TOTAL problems: 0" in out


def test_archive_entry_inline_and_heavy(proj):
    ME.add_or_update_entry(proj, "Tiny", "h", body="small", scope_default="lvl")
    ME.add_or_update_entry(proj, "Heavy", "h", body="x" * 400)
    d = _curated(proj)
    assert R.archive_entry(d, "heavy") is True
    assert (d / ".archive" / "heavy.md").is_file()
    assert R.archive_entry(d, "tiny") is True
    _, entries = ME.parse((d / "index.md").read_text(encoding="utf-8"))
    assert entries == []
    assert R.archive_entry(d, "nonexistent") is False
