"""Text checks for the failure-modes review that ends every plan run.

The plan executor dispatches one reviewer after the final whole-branch review that follows only
the reviewer side of coding-failure-modes over the whole branch. Four things break that silently:
the step dropping out of the section, the flowchart or Attended Mode; a brief that lets the
reviewer do a general code review; a rating taken over without a check against the code; and a
cost sentence that claims a measurement nobody made.
"""
import re
from pathlib import Path

SKILLS_DIR = Path(__file__).resolve().parents[2] / "skills"
EXECUTOR = SKILLS_DIR / "process-agents-subagent-driven-development" / "SKILL.md"
REVIEWER_SKILL = SKILLS_DIR / "coding-failure-modes" / "SKILL.md"
SECTION_HEADING = "## Failure-Modes Review\n"
FINAL_NODE = (
    '"Dispatch final code reviewer subagent '
    '(../process-review-requesting-code-review/code-reviewer.md)"')
FAILURE_MODES_NODE = (
    '"Dispatch failure-modes reviewer subagent '
    '(bitranox:coding-failure-modes, reviewer side only)"')
FINISH_NODE = '"Use bitranox:process-ship-finishing-development-branch"'
QUOTED_SECTION = re.compile(r'follow its section "([^"]+)"')


def _flat(text):
    return " ".join(text.split())


def _executor():
    return EXECUTOR.read_text(encoding="utf-8")


def _section():
    text = _executor()
    start = text.index(SECTION_HEADING)
    return _flat(text[start:text.index("\n## ", start + len(SECTION_HEADING))])


def _attended():
    text = _executor()
    start = text.index("## Attended Mode\n")
    return _flat(text[start:text.index("\n## ", start + 1)])


def test_the_section_follows_the_final_whole_branch_review():
    text = _executor()
    assert text.count(SECTION_HEADING) == 1
    assert text.index("## Final Whole-Branch Review\n") < text.index(SECTION_HEADING)


def test_every_run_dispatches_it_once_on_opus_at_medium_after_the_final_review():
    section = _section()
    assert "Every run ends with one more reviewer" in section
    assert "Dispatch it once per run, to a fresh `opus` agent at effort `medium`" in section
    assert "after the final whole-branch review" in section


def test_no_kind_of_run_drops_it():
    section = _section()
    for kind in ("not a small plan", "ran on `haiku`", "asked to be cheap",
                 'marked "no human" or "full automatic" dispatches it'):
        assert kind in section, f"the section no longer says a run {kind!r} keeps the review"


def test_a_run_that_stops_before_its_end_has_not_reached_the_step():
    section = _section()
    assert "A run that has parked a task" in section
    assert "has not reached this step" in section
    assert "this review waits until nothing is parked" in section


def test_it_stays_one_reviewer_where_the_final_review_was_split():
    assert "It is one reviewer, also where the final review was split by system." in _section()


def test_the_section_hands_attended_mode_to_its_own_step():
    assert "step 5 of that section says when to dispatch this reviewer" in _section()


def test_a_plan_without_a_source_design_is_said_in_the_dispatch():
    section = _section()
    assert "If the plan names no source design, say so in the dispatch" in section


def test_the_table_goes_to_a_scratch_directory_outside_the_worktree():
    assert "created with `mktemp -d` outside the worktree" in _section()


def test_the_brief_is_the_reviewer_side_of_the_skill_and_nothing_else():
    section = _section()
    assert "`bitranox:coding-failure-modes`" in section
    assert "and nothing else" in section
    assert "Code quality, style and plan alignment are not its job" in section
    assert "$CLAUDE_PLUGIN_ROOT/skills/coding-failure-modes/SKILL.md" in section


def test_the_section_it_names_exists_in_the_reviewer_skill_with_six_steps():
    names = QUOTED_SECTION.findall(_section())
    assert names == ["When you review the change"]
    reviewer = REVIEWER_SKILL.read_text(encoding="utf-8")
    heading = f"## {names[0]}\n"
    assert reviewer.count(heading) == 1
    start = reviewer.index(heading)
    body = reviewer[start:reviewer.index("\n## ", start + len(heading))]
    steps = re.findall(r"^([0-9]+)\. \*\*", body, re.MULTILINE)
    assert steps == ["1", "2", "3", "4", "5", "6"]
    assert "all six steps" in _section()


def test_the_table_is_built_from_design_and_whole_plan_before_the_diff():
    section = _section()
    assert "the required behaviours come from the source design and the whole plan" in section
    assert "before opening the review package" in section


def test_it_says_why_the_reviewer_is_separate():
    section = _section()
    assert "It is a separate reviewer because" in section
    assert "is in none of its diffs" in section
    assert "every task's piece is right and the delivered behaviour is still wrong" in section


def test_findings_take_the_final_review_route():
    section = _section()
    assert "handle its findings as you handle the final review's DEFECTS" in section
    assert "ONE fix subagent with the confirmed list" in section
    assert '"When No Human Can Answer"' in section
    assert "not dispatched a second time" in section


def test_a_rating_is_checked_against_the_code_before_a_fix():
    section = _section()
    assert "**Its rating is a claim until you have checked it against the code:**" in section
    assert "rate it yourself from that" in section
    assert "rated two findings higher than the code supported" in section


def test_the_cost_sentence_claims_no_measurement_inside_a_run():
    section = _section()
    assert "Its cost inside a plan run is not measured." in section
    assert "390k to 465k tokens" in section


def test_the_flowchart_puts_it_between_the_final_review_and_finishing():
    text = _executor()
    assert f"{FINAL_NODE} -> {FAILURE_MODES_NODE};" in text
    assert f"{FAILURE_MODES_NODE} -> {FINISH_NODE};" in text
    assert f"{FINAL_NODE} -> {FINISH_NODE};" not in text


def test_attended_mode_dispatches_it_before_the_gate_is_disarmed():
    attended = _attended()
    step = attended[attended.index("5. **Finish.**"):]
    assert 'dispatch the one reviewer of "Failure-Modes Review" below' in step
    assert step.index("Failure-Modes Review") < step.index("end plan-execution")
    assert 'say "Ready for feedback." and wait as in step 3' in step
    assert "make the fixes they ask for yourself" in step


def test_the_gate_stays_armed_through_the_fix_round():
    assert "(after the final review, the failure-modes review and its fix round)" in _flat(
        _executor())


def test_it_is_listed_as_a_review_dispatch():
    text = _executor()
    start = text.index("### Review dispatches")
    paragraph = _flat(text[start:text.index("\n\n", text.index("\n\n", start) + 2)])
    assert "the failure-modes review after it" in paragraph

