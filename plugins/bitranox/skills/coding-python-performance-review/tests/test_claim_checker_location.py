"""The diff claim checker lives in the generic performance skill; this skill names it there."""
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
GENERIC = SKILL.parent / "coding-performance-review"
REL = "../coding-performance-review/validate_perf_claims.py"


def test_skill_md_names_the_claim_checker_at_its_real_path():
    text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
    assert REL in text
    assert (SKILL / REL).resolve().is_file()


def test_no_copy_of_the_claim_checker_is_left_here():
    assert not (SKILL / "validate_perf_claims.py").exists()
    assert (GENERIC / "validate_perf_claims.py").is_file()
