"""Contract test: the dream-skill FAMILY must not drift. ASCII.

Invariants over meta-dream-nap / meta-dream-tree / meta-dream-crosstree(+deep) + dream-core.md:
  1. each skill states its canonical SCOPE rung (nap=chain, project=tree-wide, global=cross-tree);
  2. nap + project + global REQUIRED-reference the shared dream-core.md;
  3. family literals live EXACTLY ONCE across the family files: the routing prompt and the mode
     bullets are single-sourced in dream-core.md - restating them in a skill is drift.
"""
from pathlib import Path

import pytest

SKILLS = Path(__file__).resolve().parents[2] / "skills"
FAMILY = {
    "meta-dream-nap": SKILLS / "meta-dream-nap" / "SKILL.md",
    "meta-dream-tree": SKILLS / "meta-dream-tree" / "SKILL.md",
    "meta-dream-crosstree": SKILLS / "meta-dream-crosstree" / "SKILL.md",
    "meta-dream-crosstree-deep": SKILLS / "meta-dream-crosstree-deep" / "SKILL.md",
}
CORE = SKILLS / "meta-dream-tree" / "references" / "dream-core.md"
PASSES = SKILLS / "meta-dream-tree" / "references" / "dream-passes.md"


def _read(p):
    return p.read_text(encoding="utf-8")


SCOPE_MARKERS = {
    "meta-dream-nap": "ALTITUDE CHAIN ONLY",
    "meta-dream-tree": "TREE-WIDE",
    "meta-dream-crosstree": "cross-project/cross-tree pass",
}


@pytest.mark.parametrize("name,marker", sorted(SCOPE_MARKERS.items()))
def test_each_skill_states_its_scope_rung(name, marker):
    assert marker in _read(FAMILY[name]), "%s lost its canonical scope statement" % name


@pytest.mark.parametrize("name", ["meta-dream-nap", "meta-dream-tree", "meta-dream-crosstree"])
def test_each_skill_references_the_core(name):
    assert "dream-core.md" in _read(FAMILY[name]), "%s no longer references dream-core.md" % name


@pytest.mark.parametrize("literal,desc", [
    ("NARROWEST level whose PLACE-HERE", "the placement routing prompt"),
    ("**`propose`** (default)", "the mode-knob bullets"),
])
def test_family_literals_single_sourced_in_core(literal, desc):
    files = list(FAMILY.values()) + [CORE, PASSES]
    hits = [str(f) for f in files if literal in _read(f)]
    assert hits == [str(CORE)], "%s must live ONLY in dream-core.md; found in: %s" % (desc, hits)
