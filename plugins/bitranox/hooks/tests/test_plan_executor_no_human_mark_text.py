"""Text checks for when a plan executor may end its turn on a question.

The executor asks whenever a decision is the user's, and takes its no-human routing only in a run
whose prompt, brief or plan says "no human" or "full automatic". Three things break that silently:
a sentence that again infers an absent human from how the run was launched, a pointer to the
routing that drops the mark, and an A/B note that no longer carries the words the executor reads.
"""
import re
from pathlib import Path

SKILLS_DIR = Path(__file__).resolve().parents[2] / "skills"
EXECUTOR = SKILLS_DIR / "process-agents-subagent-driven-development" / "SKILL.md"
AB_TEST = SKILLS_DIR / "meta-skill-ab-test"
SECTION_HEADING = "## When No Human Can Answer\n"
MARK_PHRASE = 'marked "no human" or "full automatic"'
# The mark as the section defines it: the two phrases and their five variants, any capitals, a
# space, hyphen or line break between two words. "no humans" and "full automatic" are matched by
# their shorter forms.
VARIANTS = ("no humans", "full auto", "fully automatic", "kein Mensch", "vollautomatisch")
MARK = re.compile(
    r"no[\s-]+human|full[\s-]+auto|fully[\s-]+automatic|kein[\s-]+mensch|vollautomatisch",
    re.IGNORECASE)


def _flat(text):
    return " ".join(text.split())


def _executor():
    return EXECUTOR.read_text(encoding="utf-8")


def _section():
    text = _executor()
    start = text.index(SECTION_HEADING)
    return _flat(text[start:text.index("\n## ", start + len(SECTION_HEADING))])


def test_the_section_names_the_two_phrases_as_the_only_mark():
    section = _section()
    assert 'The mark is the words "no human" or "full automatic"' in section
    assert "Only a run marked as having no human does not ask." in section
    assert "Any other wording you are unsure about is not the mark: ask." in section


def test_the_section_lists_the_five_variants_as_the_mark():
    section = _section()
    sentence = section[section.index("Five variants are the mark as well:"):]
    sentence = sentence[:sentence.index(". Capitals")]
    for variant in VARIANTS:
        assert f'"{variant}"' in sentence, variant
        assert MARK.search(variant), variant
    assert '"not a full auto run"' in section


def test_the_section_says_what_is_not_the_mark():
    section = _section()
    assert "not the way the run was launched" in section
    assert 'not "unattended", "headless" or "autonomous" without those words' in section
    assert "not a human who is slow to answer, away or not watching" in section


def test_the_section_no_longer_infers_an_absent_human_from_the_launch():
    section = _section()
    assert "Never conclude that nobody will answer from the launch" in section
    assert "started with nobody to ask" not in section
    assert "has no one" not in section


def test_no_sentence_of_the_skill_routes_by_a_headless_run():
    assert "in a headless run" not in _flat(_executor()).lower()


def test_every_pointer_to_the_section_names_the_mark():
    flat = _flat(_executor())
    pointers = [m.start() for m in re.finditer(re.escape('"When No Human Can Answer"'), flat)]
    assert len(pointers) == 4
    for at in pointers:
        assert MARK_PHRASE in flat[at - 120:at], flat[at - 120:at + 30]


def test_a_question_that_ends_the_turn_cannot_read_as_completion():
    section = _section()
    assert "begin that final message with `QUESTION - RUN NOT FINISHED:`" in section
    assert "then each parked task with the reason it is parked, then every open question" in section
    assert "end the message on the questions themselves" in section
    assert "a controller asked one after 3 of 14 tasks and the run exited as a success" in section


def test_a_mid_run_decision_parks_its_dependents_and_the_rest_carries_on():
    section = _section()
    assert ("Park the task that holds the decision and every task that depends on the answer, "
            "execute every task that does not") in section
    assert "only then end the turn, once, on all open questions together" in section
    assert ("A task depends on the answer when it touches the same files, the same interface or "
            "the same behaviour the decision is about, or when the plan orders it after a parked "
            "task") in section
    assert "When you are unsure whether a task depends, park it." in section
    assert "The final whole-branch review waits until nothing is parked." in section
    assert "the pre-flight question is put before execution begins" in section


def test_continuous_execution_lists_the_parked_decision_as_a_reason_to_stop():
    flat = _flat(_executor())
    stop_list = flat[flat.index("The only reasons to stop are:"):]
    stop_list = stop_list[:stop_list.index("or all tasks complete.")]
    assert ("a decision that is your human partner's once every task that does not depend on it "
            "is done") in stop_list
    assert '"Park and Carry On"' in stop_list


def test_the_marked_run_keeps_its_routing():
    section = _section()
    assert "does the fix change behaviour a release already ships?" in section
    assert "begin the final message with `UNFINISHED:`" in section
    assert "a question is never answered and nothing is parked" in section
    assert "A run without the mark is unchanged: ask, as the rules above say." in section


def test_the_ab_test_skill_says_the_note_must_carry_the_mark():
    flat = _flat((AB_TEST / "SKILL.md").read_text(encoding="utf-8"))
    assert ('takes its no-human routing only when the note holds the words "no human" or '
            '"full automatic"') in flat
    assert "or one of the variants that skill lists" in flat
    assert MARK.search("There is no human in this session")


def test_the_example_note_in_the_profile_skeleton_carries_the_mark():
    source = (AB_TEST / "scripts" / "abprofile.py").read_text(encoding="utf-8")
    example = re.search(r'^# unattended_note = "(.*)"$', source, re.MULTILINE)
    assert example, "the skeleton no longer shows an example unattended_note"
    assert MARK.search(example.group(1)), example.group(1)


def test_the_mark_pattern_rejects_what_the_section_says_is_not_the_mark():
    for text in ("The human may be slow to answer.", "UNATTENDED RUN.", "a headless SDK node",
                 "run autonomously", "nobody is watching"):
        assert not MARK.search(text), text
    for text in ("NO HUMAN will read this", "this is a no-human run", "Run this full automatic.",
                 "Full-Automatic mode", "there is no\nhuman here", "run it FULL AUTO",
                 "den Plan vollautomatisch ausfuehren", "Kein Mensch liest mit",
                 "no humans are present", "a fully automatic run"):
        assert MARK.search(text), text
