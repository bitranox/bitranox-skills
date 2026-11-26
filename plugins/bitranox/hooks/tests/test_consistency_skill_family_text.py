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


def _rule_five():
    text = _text(GENERIC)
    start = text.index("\n5. **")
    return " ".join(text[start:text.index("\n6. **", start)].split())


def test_rule_five_allows_an_added_condition_only_as_a_stated_departure():
    rule = _rule_five()
    assert "You may add one when you judge it sensible." in rule
    assert "in the commit message AND in your hand-over" in rule
    for part in ("what the condition is", "why you added it", "what the user sees differently"):
        assert part in rule, f"rule 5 lost the statement part {part!r}"
    assert "SUPPRESSES an output the spec promised" in rule
    assert "is a defect" in rule


def test_the_review_separates_a_stated_added_condition_from_a_silent_one():
    text = " ".join(_text(GENERIC).split())
    assert "An `ADDED (silent)` row is a defect." in text
    assert "An `ADDED (stated)` row is not: list it under \"departures for the owner's decision\"" in text


def _rule_four():
    text = _text(GENERIC)
    start = text.index("\n4. **")
    return " ".join(text[start:text.index("\n5. **", start)].split())


def test_rule_four_allows_a_changed_fixed_point_only_as_a_stated_departure_with_a_reason():
    rule = _rule_four()
    assert "You may change one when you judge it sensible," in rule
    assert "unclear, incomplete or contradicts itself" in rule
    assert "in the commit message AND in your hand-over" in rule
    for part in ("what the spec says", "what the code does instead", "why",
                 "what a user or caller sees differently"):
        assert part in rule, f"rule 4 lost the statement part {part!r}"
    assert "or with a reason that does not hold against the spec text, is a defect" in rule
    assert "your doubt goes to the spec's owner as a question" in rule


def test_a_departure_never_covers_breaking_a_caller_outside_the_change():
    text = " ".join(_text(GENERIC).split())
    assert "the statement reaches the spec's owner, never a caller you cannot see" in text
    assert "A departure that breaks a caller outside the change is `DISAGREE` whatever its reason." in text


def test_the_review_separates_a_sound_stated_departure_from_a_silent_or_unsound_one():
    text = " ".join(_text(GENERIC).split())
    assert "Judge the reason the statement gives, never one you could supply for it" in text
    assert "or with a reason that does not hold, is `DISAGREE`" in text
    assert "A `DEPARTED (stated)` row is no defect either: list it there too" in text
    assert "A `DEPARTED (stated)` row carries no rating either" in text
    assert "is not `AGREE`, `ADDED (stated)` or `DEPARTED (stated)`" in text
