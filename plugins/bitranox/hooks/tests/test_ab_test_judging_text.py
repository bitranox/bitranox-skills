"""Text checks for the "Judging the arms" section of meta-skill-ab-test.

The section decides how a departure from the spec is scored. Its rule is prose, so a rewording
can turn it back into "only a stated departure counts" without any script noticing.
"""
from pathlib import Path

SKILL = Path(__file__).resolve().parents[2] / "skills" / "meta-skill-ab-test" / "SKILL.md"


def _judging():
    text = SKILL.read_text(encoding="utf-8")
    return " ".join(text[text.index("## Judging the arms"):].split())


def test_a_departure_is_scored_on_its_merit_whether_stated_or_not():
    section = _judging()
    assert "is sound on its merit is no defect, stated or not" in section
    assert "the spec is unclear, incomplete or contradicts itself on that point" in section
    assert "Does the change resolve it without creating a defect of its own?" in section
    assert "Both yes scores SOUND-DEPARTURE: it counts as no defect in every tally" in section
    assert "the judge rules on the merit whether or not the arm gave a reason" in section


def test_stated_or_silent_is_a_reported_flag_and_never_counted():
    section = _judging()
    assert "records a flag, `stated`" in section
    assert "or `silent`" in section
    assert "flag is reported beside the SOUND-DEPARTURE list and never counted" in section
    assert "never on one the judge could supply" not in section
    assert "PRESENT whatever its ground" not in section
    assert "is ruled on the same way, and its entry names the callers it breaks" in section
    assert "Is it stated:" not in section


def test_every_judging_step_is_given_the_spec_and_the_statements():
    section = _judging()
    assert "the diff, the spec and the arm's statements, nothing else" in section
    assert "(the diffs, the spec and the arms' statements only)" in section
    assert "(`opus`; the diff, the spec and the arm's statements only)" in section
