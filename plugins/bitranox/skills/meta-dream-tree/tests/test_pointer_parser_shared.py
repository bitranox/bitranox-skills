"""The read-only dream tools read a level's pointers the way the engine does.

Each tool used to carry its own pointer-line regex, and every copy read more than the engine:
a pointer-shaped line in the PROSE around the managed block (which the engine never reads, and
would copy into the block on the next write) counted as a fact at that level, and a slug listed
twice counted twice. They now all parse through `uuid_store.parse_pointer_index`, so a tool and
the engine cannot disagree about which facts a level holds.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "hooks"))

import dedup_scan as DS  # noqa: E402
import statusrot  # noqa: E402
import store_manifest as SM  # noqa: E402
import uuid_store as US  # noqa: E402


def level_text(in_block: list[str], loose: list[str]) -> str:
    """A level file: loose lines BEFORE and AFTER a managed block holding `in_block`."""
    return "\n".join(
        ["# Notes", *loose, US.INDEX_BEGIN, "# Memory index", "## Memory index", *in_block,
         US.INDEX_END, *loose, ""])


BLOCK = ["- [Alpha](mem:alpha-fact) - When alpha, do alpha. <!-- bx:pin -->",
         "- [Alpha again](mem:alpha-fact) - When alpha, a stale duplicate.",
         "- [Beta](mem:beta.fact-1.2) - When beta, do beta."]
LOOSE = ["- [Loose](mem:loose-fact) - When loose, this line is prose outside the block."]


def test_store_manifest_reads_only_the_block_and_each_slug_once():
    entries = SM.parse_level(level_text(BLOCK, LOOSE), "L")
    assert [(e.slug, e.title, e.pin) for e in entries] == [
        ("alpha-fact", "Alpha", True), ("beta.fact-1.2", "Beta", False)]


def test_statusrot_reads_only_the_block_and_each_slug_once():
    pointers = statusrot.parse_pointers(level_text(BLOCK, LOOSE), "L")
    assert [(p.slug, p.hook) for p in pointers] == [
        ("alpha-fact", "When alpha, do alpha."), ("beta.fact-1.2", "When beta, do beta.")]


def test_control_a_file_without_a_managed_block_is_read_whole():
    """A bare rendered block (or a fixture) has no fences; the engine reads it whole, and so do
    the tools."""
    text = "# Memory index\n" + "\n".join([BLOCK[0], BLOCK[2]]) + "\n"
    assert [e.slug for e in SM.parse_level(text, "L")] == ["alpha-fact", "beta.fact-1.2"]
    assert [p.slug for p in statusrot.parse_pointers(text, "L")] == ["alpha-fact", "beta.fact-1.2"]


def test_dedup_scan_does_not_place_a_fact_by_a_loose_line(tmp_path):
    (tmp_path / ".claude-memory" / "facts").mkdir(parents=True)
    for slug in ("alpha-fact", "loose-fact"):
        (tmp_path / ".claude-memory" / "facts" / (slug + ".md")).write_text(
            "When %s, a body long enough to score.\n" % slug, encoding="utf-8")
    (tmp_path / "CLAUDE.local.md").write_text(level_text(BLOCK[:1], []), encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "CLAUDE.local.md").write_text(level_text([], LOOSE), encoding="utf-8")
    levels = {f.slug: f.level for f in DS.load_facts(tmp_path)}
    assert levels["alpha-fact"] == str(tmp_path)
    assert levels["loose-fact"] == str(tmp_path.resolve())     # pointed at nowhere: the anchor
