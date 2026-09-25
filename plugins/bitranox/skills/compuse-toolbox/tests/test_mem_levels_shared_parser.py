"""mem_levels answers "which facts sit at this level" the way the engine does.

Its own regex matched `](mem:slug)` anywhere in the file, so a pointer-shaped line in the prose
around the managed block, or a slug merely linked from a sentence, counted as a fact at that level
- and could hide a real dangling body behind it.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "hooks"))

import mem_levels  # noqa: E402
import uuid_store as US  # noqa: E402


def _text(in_block, loose):
    return "\n".join(["# Notes", *loose, US.INDEX_BEGIN, "## Memory index", *in_block,
                      US.INDEX_END, ""])


def test_only_the_managed_block_holds_facts():
    text = _text(["- [A](mem:a-fact) - When a, do a.",
                  "- [B](mem:b.fact-1.2) - When b, do b."],
                 ["See [the a note](mem:c-fact) - a sentence, not a pointer.",
                  "- [Loose](mem:loose-fact) - When loose, prose outside the block."])
    assert mem_levels.slugs_in(text) == ["a-fact", "b.fact-1.2"]


def test_a_body_named_only_by_a_loose_line_is_reported_dangling(tmp_path):
    (tmp_path / ".claude-memory" / "facts").mkdir(parents=True)
    for slug in ("a-fact", "loose-fact"):
        (tmp_path / ".claude-memory" / "facts" / (slug + ".md")).write_text("x\n", encoding="utf-8")
    (tmp_path / "CLAUDE.local.md").write_text(
        _text(["- [A](mem:a-fact) - When a, do a."],
              ["- [Loose](mem:loose-fact) - When loose, prose outside the block."]),
        encoding="utf-8")
    report = mem_levels.scan(tmp_path)
    assert report.dangling == ["loose-fact"]


def test_control_a_file_without_a_block_is_read_whole():
    assert mem_levels.slugs_in("- [A](mem:a-fact) - When a, do a.\n") == ["a-fact"]
