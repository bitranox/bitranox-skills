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
