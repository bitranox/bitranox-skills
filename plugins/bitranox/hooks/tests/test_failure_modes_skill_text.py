"""Text checks for the coding-failure-modes skill, which ships no scripts.

The skill is a numbered axis list, four verdicts and a handful of rules whose exact scope
matters. Each test pins one of them, so a later edit that drops an axis, adds a fifth verdict
or lets a silent outcome through again fails here instead of reaching readers.
"""
import re
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

SKILLS_DIR = Path(__file__).resolve().parents[2] / "skills"
SKILL = "coding-failure-modes"
REFERENCE = re.compile(r"bitranox:([a-z0-9][a-z0-9-]*[a-z0-9])")
AXIS_ROW = re.compile(r"^\| ([0-9]+) +\| ", re.MULTILINE)
VERDICT_BULLET = re.compile(r"^   - `([A-Z]+)` - ", re.MULTILINE)
AXIS_CITATION = re.compile(r"\*\*Axis ([0-9]+) ")


def _raw():
    return (SKILLS_DIR / SKILL / "SKILL.md").read_text(encoding="utf-8")


def _flat():
    return " ".join(_raw().split())


def _front_matter():
    lines = _raw().split("\n")
    assert lines[0] == "---", "SKILL.md does not open with front matter"
    return yaml.safe_load("\n".join(lines[1 : lines.index("---", 1)]))


def test_front_matter_parses_to_name_and_description_only():
    meta = _front_matter()
    assert sorted(meta) == ["description", "name"]
    assert meta["name"] == SKILL
    assert meta["description"].startswith("Use when ")
    assert len(meta["description"]) <= 1024


def test_every_cross_reference_names_an_existing_skill():
    refs = sorted(set(REFERENCE.findall(_raw())))
    assert refs, "no bitranox: reference found, so this check examined nothing"
    missing = [ref for ref in refs if not (SKILLS_DIR / ref / "SKILL.md").is_file()]
    assert missing == [], f"{SKILL} points at skills that do not exist: {missing}"


def test_the_scope_line_hands_the_neighbouring_subjects_to_their_skills():
    refs = set(REFERENCE.findall(_raw()))
    for neighbour in (
        "coding-resilience",
        "coding-input-sanitization",
        "process-test-design",
        "coding-consistency",
    ):
        assert neighbour in refs, f"{SKILL} no longer routes to {neighbour}"


def test_the_axis_table_numbers_ten_axes_and_the_text_says_ten():
    axes = [int(number) for number in AXIS_ROW.findall(_raw())]
    assert axes == list(range(1, 11)), f"axis rows are {axes}"
    assert "Walk all ten for each required behaviour." in _flat()


def test_an_emphasised_axis_is_one_the_table_numbers():
    cited = {int(number) for number in AXIS_CITATION.findall(_raw())}
    assert cited, "no emphasised axis found, so this check examined nothing"
    assert cited <= set(range(1, 11)), f"emphasised axes {sorted(cited)} are not all in the table"


def test_there_are_exactly_four_verdicts():
    assert VERDICT_BULLET.findall(_raw()) == ["HANDLED", "REFUSED", "ASSUMED", "NONE"]
    assert "There is no fifth, and an empty cell is the defect this skill exists for." in _flat()


def test_an_assumed_row_carries_statement_confirmer_and_consequence():
    text = _flat()
    assert "Write the statement, who can confirm it" in text
    assert "and what the user sees if it is false" in text
    assert 'When that last answer is "nothing", the row leads the open questions.' in text


def test_a_span_rule_needs_a_sample_count_and_a_widest_gap():
    text = _flat()
    assert "A rule over a span or a share" in text
    assert "Decide the fewest samples that may carry the verdict and, for a span, the widest gap" in text
    assert "says nothing about what lies between" in text


def test_a_handled_row_is_traced_with_a_concrete_input():
    assert "Trace one concrete input per `HANDLED` row through the code you wrote." in _flat()


def test_silent_outcomes_are_made_visible():
    text = _flat()
    for lead in (
        "**Unmatched is reported.**",
        "**A precondition that can be checked at start is checked at start.**",
        '**"No data" is a third answer, not `False`.**',
        "**Refused is not crashed.**",
    ):
        assert lead in text, f"the visible-outcome rule {lead!r} is gone"


def test_a_fixed_signature_gets_no_new_exception_and_no_companion_function():
    text = _flat()
    assert "return the answer that claims least" in text
    assert "Do not carry the third state out through a new exception or a companion function" in text


def test_an_added_condition_is_a_stated_departure():
    text = _flat()
    assert "State the condition as a departure in the commit message and the hand-over" in text
    assert "`bitranox:coding-consistency`, rule 5, has the full form" in text
    assert "Changing the signature itself is a breaking interface change, which rule 7 there admits only as a departure" in text


def test_the_reviewer_builds_an_own_table_before_reading_the_author():
    text = _flat()
    assert "Build your own table from the spec before you open the author's table or the code." in text
    assert "Return your table with the findings." in text
