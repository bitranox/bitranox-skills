"""Tests for dangling-body detection + re-home in reconcile (surfacing and fixing invisible stuck
entries: a central body no level points at). All content ASCII."""


from pathlib import Path

import reconcile_memory_index as R
import memory_engine as E
import self_improve_signals as sig


def _proj(tmp_path):
    p = tmp_path / "proj"
    p.mkdir()
    return str(p)


def _drop_pointer(proj, slug):
    path = sig.claude_local_md_path(proj)
    text = path.read_text(encoding="utf-8")
    kept = [ln for ln in text.splitlines() if ("mem:%s)" % slug) not in ln]
    path.write_text("\n".join(kept) + "\n", encoding="utf-8")


def test_find_dangling_bodies_detects_only_orphans(tmp_path):
    proj = _proj(tmp_path)
    slug = E.add_or_update_entry(proj, "Fact", "When x.", body="B", type_="reference")
    assert R.find_dangling_bodies(proj) == []          # healthy: pointer present, not dangling
    _drop_pointer(proj, slug)
    assert R.find_dangling_bodies(proj) == [slug]      # orphaned body now detected


def test_rehome_reattaches_dangling_body(tmp_path):
    proj = _proj(tmp_path)
    slug = E.add_or_update_entry(proj, "Fact", "When x, do y.", body="Keep me.", type_="reference")
    _drop_pointer(proj, slug)
    assert R.find_dangling_bodies(proj) == [slug]
    done = R.rehome_dangling_bodies(proj)
    assert done == [slug]
    assert any(e.slug == slug for e in E.read_store(proj)[1])   # re-attached at the tree top
    assert "Keep me." in E.read_store(proj)[2][slug]            # body preserved
    assert R.find_dangling_bodies(proj) == []                   # nothing dangling now


def test_rehome_dry_run_writes_nothing(tmp_path):
    proj = _proj(tmp_path)
    slug = E.add_or_update_entry(proj, "Fact", "When x.", body="B", type_="reference")
    _drop_pointer(proj, slug)
    assert R.rehome_dangling_bodies(proj, dry_run=True) == [slug]
    assert R.find_dangling_bodies(proj) == [slug]               # still dangling after a dry run


def _tree(tmp_path):
    """tree -> sub -> proj, each CLAUDE.md-bearing, so the three are one tree with its store at
    the top; returns (top, proj)."""
    top = tmp_path / "tree"
    proj = top / "sub" / "proj"
    proj.mkdir(parents=True)
    for d in (top, top / "sub", proj):
        (d / "CLAUDE.md").write_text("x\n", encoding="utf-8")
    (top / ".claude-memory").mkdir()
    return str(top), str(proj)


def _lost_fact(proj):
    slug = E.add_or_update_entry(proj, "A stored title, not the slug", "When rehoming, keep it.",
                                 body="Prose.", slug="lost-fact", type_="feedback")
    E.drop_pointer(proj, slug)
    return slug


def test_rehome_keeps_the_title_the_body_stores(tmp_path):
    """The body carries the fact's title as data; a re-home derived one from the slug instead
    and, since every engine write keeps the two equal, overwrote the stored one with it."""
    top, proj = _tree(tmp_path)
    slug = _lost_fact(proj)

    assert R.rehome_dangling_bodies(top) == [slug]

    entry = next(e for e in E.read_store(top)[1] if e.slug == slug)
    assert entry.title == "A stored title, not the slug"
    assert E.body_title(E.read_store(top)[2][slug]) == "A stored title, not the slug"


def test_rehome_of_a_body_without_a_title_derives_one_from_the_slug(tmp_path):
    top, _proj = _tree(tmp_path)
    import uuid_store as us
    us.put_body(top, "old-fact", "---\nname: old-fact\ndescription: When x, do y.\n---\n\nP.\n")

    assert R.rehome_dangling_bodies(top) == ["old-fact"]

    assert next(e for e in E.read_store(top)[1] if e.slug == "old-fact").title == "old fact"


def test_rehome_prints_the_bytes_it_adds_to_the_tree_top(tmp_path, capsys):
    """A re-home to the tree top writes into the block every session in the tree loads; its
    cost is printed, as the dream reports every re-home to the top - predicted by --dry-run."""
    top, proj = _tree(tmp_path)
    _lost_fact(proj)

    assert R.main(["--rehome", "--dry-run", proj]) == 0
    dry = capsys.readouterr().out
    assert R.main(["--rehome", proj]) == 0
    real = capsys.readouterr().out

    added = E._block_bytes(top)
    assert added > 0
    assert ("cost: would add %d byte(s) to the always-loaded pointer block at %s (the tree top, "
            "loaded by every session in the tree)" % (added, top)) in dry
    assert ("cost: added %d byte(s) to the always-loaded pointer block at %s (the tree top"
            % (added, top)) in real


def test_rehome_to_a_level_below_the_top_prints_its_cost_without_the_top_note(tmp_path, capsys):
    top, proj = _tree(tmp_path)
    _lost_fact(proj)

    assert R.main(["--rehome", "--rehome-to", proj, top]) == 0
    out = capsys.readouterr().out

    assert ("cost: added %d byte(s) to the always-loaded pointer block at %s\n"
            % (E._block_bytes(proj), proj)) in out


def test_the_backend_doc_names_the_rehome_among_the_title_keeping_writes():
    """memory-backend.md is where a reader learns which writes keep a body's `title:` equal to the
    pointer (ledger d-20261120-bf284c6e); the re-home writes the pointer from the body, so the doc
    must say so or it reads as a write that may set a different title."""
    doc = Path(R.__file__).resolve().parent / "references" / "memory-backend.md"
    text = " ".join(doc.read_text(encoding="utf-8").split())
    assert ("`reconcile_memory_index.py --rehome` writes a new pointer line for a body that lost "
            "its line and takes that line's title from the body's `title:`") in text
