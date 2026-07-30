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
    ("## Boundaries (the whole family", "the family Boundaries block"),
])
def test_family_literals_single_sourced_in_core(literal, desc):
    files = list(FAMILY.values()) + [CORE, PASSES]
    hits = [str(f) for f in files if literal in _read(f)]
    assert hits == [str(CORE)], "%s must live ONLY in dream-core.md; found in: %s" % (desc, hits)


def test_claude_md_policy_is_not_gated_on_version_control():
    """The CLAUDE.md policy must not key off git tracking.

    Gitignore is irrelevant to LOADING, so a `version-controlled CLAUDE.md` qualifier silently put
    every non-tracked file outside the policy, and the matching `never trim a TRACKED lower copy`
    guard made a dream HOLD a trim purely because the file was committed (observed 2026-07-30).
    The test is deliberately narrow: it bans the qualifier next to CLAUDE.md, not the words
    `tracked`/`version-controlled` generally - Durability legitimately still discusses git.
    """
    banned = ("version-controlled CLAUDE.md", "CLAUDE.md (version-controlled)",
              "`CLAUDE.md` (version-controlled)", "trim a TRACKED lower copy")
    offenders = []
    for f in list(FAMILY.values()) + [CORE, PASSES]:
        text = _read(f)
        for phrase in banned:
            if phrase in text:
                offenders.append("%s: %r" % (f.name, phrase))
    assert not offenders, (
        "the CLAUDE.md policy must be gated on ANCESTOR REACHABILITY, not git tracking; found: %s"
        % offenders)


def test_the_reachability_invariant_is_stated_in_passes():
    """dream-passes.md owns the case model, so the invariant that replaced the git guard lives there."""
    text = _read(PASSES)
    assert "ANCESTOR DIRECTORY" in text, "dream-passes.md lost the reachability invariant"
    assert "SIBLING or CHILD" in text, (
        "dream-passes.md must keep the sibling/child exclusion - it is the one way a trim can still "
        "silently lose a rule")
