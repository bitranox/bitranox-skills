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
    assert "A condition added with no such ground is a defect, stated or not." in rule
    assert "comes back from the review as a missing note for you to add" in rule
    assert "names what goes wrong without the condition" in rule


def test_the_review_rules_on_an_added_condition_by_its_merit():
    text = " ".join(_text(GENERIC).split())
    assert "ADDED (stated)" not in text and "ADDED (silent)" not in text
    assert "Both yes is `ADDED (sound)`, anything else `ADDED (unsound)`." in text
    assert "you rule on the merit of the addition whether or not one was given" in text
    assert "An `ADDED (unsound)` row is a defect, stated or not." in text
    assert "An `ADDED (sound)` row is not: list it under \"departures for the owner's decision\"" in text
    assert "A `silent` row of either kind also goes in a list of missing notes" in text
    assert "An `ADDED (sound)` row carries no rating, `stated` or `silent`" in text


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
    assert "changed with no such ground in the spec text is a defect, stated or not" in rule
    assert "comes back from the review as a missing note for you to add" in rule
    assert "your doubt goes to the spec's owner as a question" in rule


def test_a_breaking_interface_change_is_a_departure_that_names_the_callers_it_breaks():
    text = " ".join(_text(GENERIC).split())
    assert "is a departure like any other: it needs the same ground" in text
    assert "in the fourth name the callers it breaks" in text
    assert "in a published library the change ships as a broken release" in text
    assert "row names the callers it breaks where known and says whether callers outside the tree were checked" in text
    assert "whatever its ground" not in text and "whatever the reason" not in text
    assert "the existing form keeps working" not in text


def test_the_review_rules_on_a_departure_by_its_merit_and_flags_stated_or_silent():
    text = " ".join(_text(GENERIC).split())
    assert "the change is sound on its merit" in text
    assert "you rule on the merit whether or not one was given" in text
    assert "never one you could supply for it" not in text
    assert "Add the flag `stated`" in text and "else `silent`" in text
    assert "A changed fixed point that is not sound is `DISAGREE`" in text
    assert "A `DEPARTED (sound)` row is no defect either: list it there too" in text
    assert "list of missing notes for the author to add, which is not a rated defect" in text
    assert "A `DEPARTED (sound)` row carries no rating either, `stated` or `silent`" in text
    assert "is not `AGREE`, `ADDED (sound)` or `DEPARTED (sound)`" in text
