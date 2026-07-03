"""Tests for memory_engine.py (the single write path + index.md grammar). All content ASCII."""

import re

import pytest

import self_improve_signals as sig
import memory_engine as E


@pytest.fixture
def proj(tmp_path):
    p = tmp_path / "proj"
    p.mkdir()
    return str(p)


# ---- slug + heavy/inline decision --------------------------------------------------------------

def test_slugify():
    assert E.slugify("No em dashes") == "no-em-dashes"
    assert E.slugify("No em dashes", "feedback") == "feedback-no-em-dashes"
    assert E.slugify("feedback already", "feedback") == "feedback-already"  # no double prefix drift
    assert E.slugify("") == "note"


def test_decide_heavy():
    assert E.Entry("s", "t", "h", body="short and clean").heavy is False
    assert E.Entry("s", "t", "h", body="x" * 400).heavy is True                  # too big -> heavy
    assert E.Entry("s", "t", "h", body="see @docs/readme.md").heavy is True      # import-like @ -> heavy
    assert E.Entry("s", "t", "h", body="ping @someone now").heavy is True        # inline @ -> heavy
    assert E.Entry("s", "t", "h", body="mail a@b.com please").heavy is False     # email -> stays inline
    assert E.Entry("s", "t", "h", body="").heavy is False


# ---- parse / render round-trip -----------------------------------------------------------------

def test_parse_render_roundtrip():
    text = ("<!-- bitranox:self-learning -->\nwhat this level is for\n<!-- /bitranox:self-learning -->\n\n"
            "# Memory index\n\n"
            "- [Tiny](#a-slug) - a hook <!-- bx:src=x,y bx:pin -->\n  a small body\n  second line\n"
            "- [Heavy](facts/b-slug.md) - b hook <!-- bx:src=z -->\n")
    scope, entries = E.parse(text)
    assert scope == "what this level is for"
    assert [e.slug for e in entries] == ["a-slug", "b-slug"]
    tiny = entries[0]
    assert tiny.heavy is False and tiny.pin is True and tiny.source == {"x", "y"}
    assert tiny.body == "a small body\nsecond line"
    heavy = entries[1]
    assert heavy.heavy is True and heavy.source == {"z"}
    # render is stable (re-parsing yields the same entries)
    scope2, entries2 = E.parse(E.render(scope, entries))
    assert scope2 == scope and [e.slug for e in entries2] == ["a-slug", "b-slug"]
    assert entries2[0].body == tiny.body and entries2[0].pin is True


# ---- add_or_update_entry -----------------------------------------------------------------------

def test_add_new_inline_and_heavy(proj):
    E.add_or_update_entry(proj, "No em dashes", "use ASCII", body="Always ASCII.",
                          type_="feedback", source=["feedback-no-em-dashes"], scope_default="lvl")
    E.add_or_update_entry(proj, "Big proc", "the long one", body="x" * 400, source=["ref-big"])
    scope, entries, bodies = E.read_store(proj)
    assert scope == "lvl"
    by = {e.slug: e for e in entries}
    assert by["feedback-no-em-dashes"].heavy is False
    assert by["big-proc"].heavy is True
    facts = sig.claude_memory_dir(proj) / "facts" / "big-proc.md"
    assert facts.is_file() and "x" * 400 in facts.read_text(encoding="utf-8")


def test_update_merges_source_and_pin(proj):
    E.add_or_update_entry(proj, "Rule", "hook", body="b", source=["s1"], scope_default="lvl")
    E.add_or_update_entry(proj, "Rule", "hook2", body="b2", source=["s2"], pin=True)
    scope, entries, bodies = E.read_store(proj)
    e = entries[0]
    assert e.source == {"s1", "s2"} and e.pin is True and e.hook == "hook2"
    assert bodies.get(e.slug, e.body) == "b2"


def test_no_import_like_at_is_inlined(proj):
    E.add_or_update_entry(proj, "Handle", "h", body="ping @someone about @docs/x.md", scope_default="lvl")
    mem = sig.curated_index(proj).read_text(encoding="utf-8")
    inlined = [ln for ln in mem.splitlines() if ln.startswith("  ") and re.search(r"(?:^|\s)@[\w./~-]", ln)]
    assert inlined == []                                   # never inline an import-like @token


def test_mtime_neutral_noop(proj):
    E.add_or_update_entry(proj, "Rule", "h", body="b", source=["s"], scope_default="lvl")
    mem = sig.curated_index(proj)
    mt1 = mem.stat().st_mtime_ns
    E.add_or_update_entry(proj, "Rule", "h", body="b", source=["s"])   # identical -> no write
    assert mem.stat().st_mtime_ns == mt1


# ---- ensure_level ------------------------------------------------------------------------------

def test_import_line_targets_index_md():
    assert E.IMPORT_LINE.endswith("/index.md")          # never memory.md (confusable with native MEMORY.md)
    assert E.IMPORT_LINE == "@.claude-bx-selflearning/index.md"


def test_ensure_level_creates_import_in_claude_local_md(proj):
    E.ensure_level(proj, scope_default="what this level is for")
    # default (track_private off): the @import lives in the UNTRACKED CLAUDE.local.md, never CLAUDE.md
    local = sig.claude_local_md_path(proj).read_text(encoding="utf-8")
    assert E.IMPORT_LINE in local and E.IMPORT_BEGIN in local and E.IMPORT_END in local
    assert not sig.claude_md_path(proj).exists()          # tracked CLAUDE.md untouched (not even created)
    mem = sig.curated_index(proj).read_text(encoding="utf-8")
    assert sig.read_scope_block(mem) == "what this level is for"


def test_ensure_level_idempotent(proj):
    E.ensure_level(proj, scope_default="x")
    local1 = sig.claude_local_md_path(proj).read_text(encoding="utf-8")
    E.ensure_level(proj, scope_default="x")
    assert sig.claude_local_md_path(proj).read_text(encoding="utf-8") == local1   # no duplicate block


def test_ensure_level_preserves_user_claude_md(proj):
    md_path = sig.claude_md_path(proj)
    md_path.write_text("# My project\n\nHand-written user instructions.\n", encoding="utf-8")
    E.ensure_level(proj, scope_default="x")
    # tracked CLAUDE.md is left byte-identical; the import goes to CLAUDE.local.md
    assert md_path.read_text(encoding="utf-8") == "# My project\n\nHand-written user instructions.\n"
    assert E.IMPORT_LINE in sig.claude_local_md_path(proj).read_text(encoding="utf-8")


def test_ensure_level_track_private_uses_claude_md(proj, tmp_path, monkeypatch):
    home = tmp_path / "home"; (home / ".claude").mkdir(parents=True)   # isolate config; don't pollute real
    monkeypatch.setenv("HOME", str(home)); monkeypatch.setenv("USERPROFILE", str(home))
    sig.save_config({"track_private": True})
    E.ensure_level(proj, scope_default="x")
    # track_private on: import goes in the TRACKED CLAUDE.md (so a clone loads it), not CLAUDE.local.md
    assert E.IMPORT_LINE in sig.claude_md_path(proj).read_text(encoding="utf-8")
    assert not sig.claude_local_md_path(proj).exists()


def test_ensure_level_moves_legacy_scope_block_out_of_claude_md(proj):
    md_path = sig.claude_md_path(proj)
    md_path.write_text("# Proj\n\n%s\nlegacy descriptor\n%s\n\nmore user text\n"
                       % (sig.SCOPE_MARK_BEGIN, sig.SCOPE_MARK_END), encoding="utf-8")
    E.ensure_level(proj, scope_default="ignored-because-legacy-wins")
    md = md_path.read_text(encoding="utf-8")
    assert sig.SCOPE_MARK_BEGIN not in md                 # legacy block removed from CLAUDE.md
    assert "more user text" in md and md.startswith("# Proj")
    assert E.IMPORT_LINE in sig.claude_local_md_path(proj).read_text(encoding="utf-8")   # import in local
    mem = sig.curated_index(proj).read_text(encoding="utf-8")
    assert sig.read_scope_block(mem) == "legacy descriptor"   # relocated into index.md


def test_cli_add(proj, capsys, tmp_path):
    rc = E.main(["add", "--proj", proj, "--type", "feedback", "--title", "No em dashes",
                 "--hook", "use ASCII", "--body", "Always ASCII.", "--source", "a,b", "--scope", "lvl"])
    assert rc == 0
    assert capsys.readouterr().out.strip() == "feedback-no-em-dashes"
    scope, entries, bodies = E.read_store(proj)
    e = entries[0]
    assert e.slug == "feedback-no-em-dashes" and e.source == {"a", "b"} and scope == "lvl"


def test_cli_add_body_file(proj, tmp_path):
    bf = tmp_path / "body.txt"
    bf.write_text("line one\nline two\n", encoding="utf-8")
    rc = E.main(["add", "--proj", proj, "--title", "Multi", "--hook", "h", "--body-file", str(bf),
                 "--scope", "lvl"])
    assert rc == 0
    _, _, _ = E.read_store(proj)
    assert "line one" in (E.sig.curated_index(proj).read_text(encoding="utf-8"))


# ---- self-heal ---------------------------------------------------------------------------------

def _local(proj):
    return sig.claude_local_md_path(proj)


def test_heal_creates_missing_store_and_import(proj):
    rep = E.heal(proj)
    assert sig.curated_index(proj).is_file()                       # index.md created
    assert E.IMPORT_LINE in _local(proj).read_text(encoding="utf-8")   # @import wired in CLAUDE.local.md
    assert rep["levels"] >= 1


def test_heal_normalizes_malformed_import_block(proj):
    # a stray bare import line + a duplicate BEGIN, no clean block -> healed to exactly one canonical block
    _local(proj).write_text("intro\n%s\nleftover\n%s\n%s\n" % (E.IMPORT_LINE, E.IMPORT_BEGIN, E.IMPORT_LINE),
                            encoding="utf-8")
    E.heal(proj)
    txt = _local(proj).read_text(encoding="utf-8")
    assert txt.count(E.IMPORT_BEGIN) == 1 and txt.count(E.IMPORT_END) == 1
    assert sum(1 for ln in txt.split("\n") if ln.strip() == E.IMPORT_LINE) == 1
    assert E._IMPORT_BLOCK in txt and "intro" in txt


def test_heal_normalizes_malformed_scope_and_grammar(proj):
    E.ensure_level(proj, scope_default="what this level is for")
    mem = sig.curated_index(proj)
    # corrupt: a SCOPE_BEGIN with no END, plus a stray non-canonical line
    mem.write_text("%s\nwhat this level is for\n\n# Memory index\n\ngarbage line\n" % E.SCOPE_BEGIN,
                   encoding="utf-8")
    E.heal(proj)
    healed = mem.read_text(encoding="utf-8")
    assert E.SCOPE_BEGIN in healed and E.SCOPE_END in healed          # scope markers restored (round-trip)
    assert healed == E.render(*E.parse(healed))                       # now canonical / round-trips


def test_heal_reports_missing_facts_body_not_fabricated(proj):
    slug = E.add_or_update_entry(proj, title="Heavy one", hook="h", body="x" * 400, scope_default="lvl")
    facts = sig.claude_memory_dir(proj) / "facts" / (slug + ".md")
    assert facts.is_file()
    facts.unlink()                                                   # delete the body -> unreconstructable
    rep = E.heal(proj)
    store = str(sig.claude_memory_dir(proj))
    assert (store, slug) in rep["orphans"]                           # reported...
    assert not facts.is_file()                                       # ...NOT fabricated


def test_heal_idempotent(proj):
    E.heal(proj)
    rep2 = E.heal(proj)
    assert rep2["healed"] == []                                      # second pass changes nothing


def test_heal_strips_drifted_note_import_block(proj):
    # an OLD-format managed block (NOTE text differs from the current constant) must be fully removed,
    # not leave the drifted NOTE line orphaned, then re-added canonical.
    old = ("preamble\n%s\n     Target is gitignored/local; older note wording. -->\n%s\n%s\n"
           % (E.IMPORT_BEGIN, E.IMPORT_LINE, E.IMPORT_END))
    _local(proj).write_text(old, encoding="utf-8")
    E.heal(proj)
    txt = _local(proj).read_text(encoding="utf-8")
    assert "older note wording" not in txt                 # drifted NOTE taken with the span
    assert txt.count(E.IMPORT_BEGIN) == 1 and E._IMPORT_BLOCK in txt and "preamble" in txt


def test_heal_scaffolds_claude_md_at_every_level(tmp_path):
    # CLAUDE.md exists only at the top; heal must create a marker CLAUDE.md + wiring + store at every
    # gap level up to it, and NOT overwrite the top's existing CLAUDE.md.
    (tmp_path / "top" / "mid" / "proj").mkdir(parents=True)
    (tmp_path / "top" / "CLAUDE.md").write_text("real top instructions", encoding="utf-8")
    E.heal(str(tmp_path / "top" / "mid" / "proj"))
    for level in ("top", "top/mid", "top/mid/proj"):
        d = tmp_path / level
        assert (d / "CLAUDE.md").is_file()
        assert (d / "CLAUDE.local.md").is_file()
        assert (d / ".claude-bx-selflearning" / "index.md").is_file()
    assert "bitranox memory altitude" in (tmp_path / "top" / "mid" / "CLAUDE.md").read_text(encoding="utf-8")
    assert (tmp_path / "top" / "CLAUDE.md").read_text(encoding="utf-8").strip() == "real top instructions"


def test_set_scope_upserts_and_overwrites(proj, capsys):
    rc = E.main(["set-scope", "--proj", proj, "--scope", "what this level is about"])
    assert rc == 0
    assert sig.read_scope_block(sig.curated_index(proj).read_text(encoding="utf-8")) == "what this level is about"
    E.main(["set-scope", "--proj", proj, "--scope", "revised classification"])   # overwrite
    assert sig.read_scope_block(sig.curated_index(proj).read_text(encoding="utf-8")) == "revised classification"
    # the index heading + grammar survive the scope replacement
    assert "# Memory index" in sig.curated_index(proj).read_text(encoding="utf-8")
