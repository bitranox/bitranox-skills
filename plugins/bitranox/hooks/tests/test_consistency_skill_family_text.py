"""Text checks for the consistency skill family, which ships no scripts.

Three properties of the family's text break silently: front matter a YAML loader rejects (the
router then never sees the description), a `bitranox:<name>` cross-reference naming a skill that
does not exist, and a routing link lost on one side, which leaves a companion skill that nothing
sends the reader to, or a companion that no longer names the text its own terms come from.
"""
import re
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

SKILLS_DIR = Path(__file__).resolve().parents[2] / "skills"
GENERIC = "coding-consistency"
COMPANIONS = ("coding-python-consistency", "coding-rust-consistency")
FAMILY = (GENERIC, *COMPANIONS)
REFERENCE = re.compile(r"bitranox:([a-z0-9][a-z0-9-]*[a-z0-9])")
PAIRING_ROW = re.compile(r"^\| ([0-9]+) \| ", re.MULTILINE)
SOURCE_REFERENCE = re.compile(r"[Ss]ources? ([0-9])(?: to ([0-9]))?")


def _text(skill):
    return (SKILLS_DIR / skill / "SKILL.md").read_text(encoding="utf-8")


def _front_matter(skill):
    lines = _text(skill).split("\n")
    assert lines[0] == "---", f"{skill}: SKILL.md does not open with front matter"
    end = lines.index("---", 1)
    return yaml.safe_load("\n".join(lines[1:end]))


def _references(skill):
    return sorted(set(REFERENCE.findall(_text(skill))))


@pytest.mark.parametrize("skill", FAMILY)
def test_front_matter_parses_to_name_and_description_only(skill):
    meta = _front_matter(skill)
    assert sorted(meta) == ["description", "name"]
    assert meta["name"] == skill
    assert meta["description"].startswith("Use when ")
    assert len(meta["description"]) <= 1024


@pytest.mark.parametrize("skill", FAMILY)
def test_every_cross_reference_names_an_existing_skill(skill):
    refs = _references(skill)
    assert refs, f"{skill}: no bitranox: reference found, so this check examined nothing"
    missing = [ref for ref in refs if not (SKILLS_DIR / ref / "SKILL.md").is_file()]
    assert missing == [], f"{skill} points at skills that do not exist: {missing}"


def test_the_generic_skill_routes_to_each_companion_in_body_and_description():
    refs = _references(GENERIC)
    description = _front_matter(GENERIC)["description"]
    for companion in COMPANIONS:
        assert companion in refs, f"{GENERIC} body does not route to {companion}"
        assert companion in description, f"{GENERIC} description does not name {companion}"


@pytest.mark.parametrize("companion", COMPANIONS)
def test_each_companion_loads_the_generic_skill(companion):
    assert GENERIC in _references(companion)
    assert f"bitranox:{GENERIC}" in _front_matter(companion)["description"]


@pytest.mark.parametrize("companion", COMPANIONS)
def test_a_companion_cites_only_review_sources_the_generic_skill_numbers(companion):
    pairings = {int(number) for number in PAIRING_ROW.findall(_text(GENERIC))}
    assert pairings == set(range(1, 8)), f"{GENERIC}: pairing table rows are {sorted(pairings)}"
    cited = set()
    for first, last in SOURCE_REFERENCE.findall(_text(companion)):
        cited.update(range(int(first), int(last or first) + 1))
    assert cited, f"{companion}: cites no numbered source, so this check examined nothing"
    assert cited <= pairings, f"{companion} cites sources {sorted(cited - pairings)} the generic skill lacks"
