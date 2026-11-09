"""Text checks for the Rust skill family, which ships no scripts.

A skill without scripts has no behaviour a unit test can run, but two properties of its text
still break silently: front matter a YAML loader rejects (the router then never sees the
description), and a `bitranox:<name>` cross-reference naming a skill that does not exist, which
sends the reader to instructions that are not installed.
"""
import re
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

SKILLS_DIR = Path(__file__).resolve().parents[2] / "skills"
RUST_SKILLS = ("coding-rust", "coding-rust-data-architecture", "coding-rust-performance-review")
REFERENCE = re.compile(r"bitranox:([a-z0-9][a-z0-9-]*[a-z0-9])")


def _front_matter(skill):
    lines = (SKILLS_DIR / skill / "SKILL.md").read_text(encoding="utf-8").split("\n")
    assert lines[0] == "---", f"{skill}: SKILL.md does not open with front matter"
    end = lines.index("---", 1)
    return yaml.safe_load("\n".join(lines[1:end]))


def _references(skill):
    text = (SKILLS_DIR / skill / "SKILL.md").read_text(encoding="utf-8")
    return sorted(set(REFERENCE.findall(text)))


@pytest.mark.parametrize("skill", RUST_SKILLS)
def test_front_matter_parses_to_name_and_description_only(skill):
    meta = _front_matter(skill)
    assert sorted(meta) == ["description", "name"]
    assert meta["name"] == skill
    assert meta["description"].startswith("Use when ")
    assert len(meta["description"]) <= 1024


@pytest.mark.parametrize("skill", RUST_SKILLS)
def test_every_cross_reference_names_an_existing_skill(skill):
    refs = _references(skill)
    assert refs, f"{skill}: no bitranox: reference found, so this check examined nothing"
    missing = [ref for ref in refs if not (SKILLS_DIR / ref / "SKILL.md").is_file()]
    assert missing == [], f"{skill} points at skills that do not exist: {missing}"



def test_the_data_architecture_skill_routes_to_the_generic_and_back():
    assert "coding-data-architecture" in _references("coding-rust-data-architecture")
    assert "coding-rust-data-architecture" in _references("coding-rust")
