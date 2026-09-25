"""ref_map places a fact by the level whose managed block names it, the way the engine does.

Its own regex read every pointer-shaped line of a level file, so a line in the prose outside the
block (which the engine never reads) could claim a fact for the wrong level.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "hooks"))

import ref_map  # noqa: E402
import uuid_store as US  # noqa: E402


def _level(path: Path, in_block: list[str], loose: list[str]) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "CLAUDE.local.md").write_text(
        "\n".join(["# Notes", US.INDEX_BEGIN, "## Memory index", *in_block, US.INDEX_END,
                   *loose, ""]), encoding="utf-8")


def test_a_loose_line_outside_the_block_does_not_claim_a_fact(tmp_path):
    _level(tmp_path, ["- [A](mem:a-fact) - When a, do a."], [])
    _level(tmp_path / "zz", [], ["- [A](mem:a-fact) - When a, prose that only looks like one."])
    assert ref_map.read_levels(tmp_path) == {"a-fact": str(tmp_path)}


def test_control_a_pointer_inside_a_deeper_block_is_still_read(tmp_path):
    _level(tmp_path, [], [])
    _level(tmp_path / "zz", ["- [B](mem:b.fact-1.2) - When b, do b."], [])
    assert ref_map.read_levels(tmp_path) == {"b.fact-1.2": str(tmp_path / "zz")}
