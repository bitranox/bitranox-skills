"""task_brief.py: task boundaries, CommonMark fences, task ids, and the default output file."""
import subprocess

import pytest

import task_brief as TB


@pytest.fixture(autouse=True)
def _hermetic_git(monkeypatch):
    for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY",
                 "GIT_COMMON_DIR"):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def repo(tmp_path, monkeypatch):
    r = tmp_path / "repo"
    r.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=r, check=True, capture_output=True)
    monkeypatch.chdir(r)
    return r


# ---- fences -------------------------------------------------------------------------------------
TILDE_PLAN = """## Task 1: one

~~~bash
## Task 2: inside a tilde fence
~~~

still task one

## Task 2: two

body two
"""


def test_a_heading_inside_a_tilde_fence_does_not_end_the_task():
    text = TB.extract_task(TILDE_PLAN, 1)
    assert "still task one" in text
    assert "body two" not in text
    assert "body two" in TB.extract_task(TILDE_PLAN, 2)


def test_a_backtick_fence_is_not_closed_by_a_tilde_line():
    plan = "## Task 1\n```\n~~~\n## Task 2 decoy\n```\nafter\n## Task 2\ntwo\n"
    assert "after" in TB.extract_task(plan, 1)
    assert "decoy" not in TB.extract_task(plan, 2)


def test_a_closing_fence_must_be_at_least_as_long_as_the_opener():
    plan = "## Task 1\n````\n```\n## Task 2 decoy\n````\nafter\n## Task 2\ntwo\n"
    assert "after" in TB.extract_task(plan, 1)
    assert TB.extract_task(plan, 2).startswith("## Task 2\n")


def test_a_line_starting_with_inline_code_is_not_a_fence():
    """```x``` at column 0 is inline code (its info string holds a backtick), not an opener."""
    plan = "## Task 1\n```x``` is inline code\none\n## Task 2\ntwo\n"
    assert "two" not in TB.extract_task(plan, 1)
    assert "two" in TB.extract_task(plan, 2)


def test_an_indented_fence_of_up_to_three_spaces_still_counts():
    plan = "## Task 1\n   ```\n## Task 2 decoy\n   ```\nafter\n## Task 2\ntwo\n"
    assert "after" in TB.extract_task(plan, 1)


# ---- task ids -----------------------------------------------------------------------------------
ID_PLAN = """## Task 3: three

body three

### Task 3.5: hotfix

body three-five

## Task 3a: variant

body three-a

## Task 30: thirty

body thirty
"""


def test_an_inserted_decimal_task_is_its_own_task():
    three = TB.extract_task(ID_PLAN, 3)
    assert "body three" in three and "three-five" not in three
    assert "body three-five" in TB.extract_task(ID_PLAN, "3.5")


def test_a_lettered_task_is_its_own_task():
    assert "body three-a" in TB.extract_task(ID_PLAN, "3a")
    assert "three-a" not in TB.extract_task(ID_PLAN, 3)


def test_task_30_still_does_not_fold_into_task_3():
    assert "thirty" not in TB.extract_task(ID_PLAN, 3)
    assert "body thirty" in TB.extract_task(ID_PLAN, 30)


# ---- where a task ends --------------------------------------------------------------------------
# Real plans put a task's own sections (Steps, Files, a run record) at or below the task heading's
# level, and plan-level sections (a phase, a milestone, Self-review) ABOVE it: the writing-plans
# template writes "### Task N" under "## Global Constraints" / "## Self-review".

def test_a_section_after_the_last_task_is_not_part_of_it():
    """The template's shape: ### tasks, then a ## Self-review the implementer must not act on."""
    plan = ("# Plan\n\n## Global Constraints\n\nc\n\n### Task 1: first\n\none\n\n"
            "### Task 2: only\n\nbody two\n\n#### Step detail\n\nstill two\n\n"
            "## Self-review\n\nDelete the prod database\n")
    text = TB.extract_task(plan, 2)
    assert "still two" in text          # a deeper heading stays inside the task
    assert "Delete the prod database" not in text


def test_a_higher_level_heading_also_ends_the_task():
    plan = "### Task 1\none\n## Appendix\nnot one\n"
    assert "not one" not in TB.extract_task(plan, 1)


def test_a_milestone_heading_between_tasks_ends_the_task_before_it():
    plan = ("### Task 7: adopt\n\nseven\n\n## M2 - the kernel (Tasks 8-18)\n\nmilestone intro\n\n"
            "### Task 8: token\n\neight\n")
    assert "milestone intro" not in TB.extract_task(plan, 7)
    assert "milestone intro" not in TB.extract_task(plan, 8)


FLAT_PLAN = """# Plan

## Task 1: one

intro one

## Steps

step one

## Files

file_one.py

## Task 2: two

intro two

## Steps

step two

## Files

file_two.py
"""


@pytest.mark.parametrize("task, own, foreign", [
    (1, ["intro one", "step one", "file_one.py"], ["intro two", "step two"]),
    (2, ["intro two", "step two", "file_two.py"], ["intro one", "step one"]),  # the last task too
])
def test_a_task_section_at_the_task_heading_level_stays_inside_the_task(task, own, foreign):
    """"## Task 1" then "## Steps" / "## Files": the task's own sections, not its end."""
    text = TB.extract_task(FLAT_PLAN, task)
    for needle in own:
        assert needle in text, needle
    for needle in foreign:
        assert needle not in text, needle


def test_a_single_task_with_same_level_sections_keeps_them():
    plan = "# Plan\n\n## Task 1: only\n\nintro\n\n## Steps\n\nstep one\n\n## Files\n\nf.py\n"
    text = TB.extract_task(plan, 1)
    assert "step one" in text and "f.py" in text


def test_a_run_record_under_the_last_task_of_a_part_stays_with_it():
    """A real plan's shape: a ### record under ### Task 4, then a # Part heading, then Task 1."""
    plan = ("# Part C\n\n### Task 4: the measurement run\n\nsteps\n\n"
            "### What the run actually did\n\nthe record\n\n"
            "# Part D: M1 only\n\npart intro\n\n### Task 1: the registry\n\nbody one\n")
    four = TB.extract_task(plan, 4)
    assert "the record" in four
    assert "part intro" not in four and "body one" not in four


def test_a_same_level_trailing_section_is_kept_with_the_last_task():
    """The price of the rule above: after the last task, a section written at the task's own level
    cannot be told from that task's Steps, so it stays in the brief rather than cutting the
    task short. Write plan-level sections above the task level (the template does)."""
    plan = "## Task 1: only\n\nbody one\n\n## Rollout notes\n\nnotes text\n"
    assert "notes text" in TB.extract_task(plan, 1)


# ---- line handling ------------------------------------------------------------------------------
def test_a_form_feed_inside_a_line_does_not_split_it():
    """splitlines() breaks on \\f and U+2028, turning mid-line text into a fake heading line."""
    plan = "## Task 1\nbody\x0c## Task 2 is mentioned here\nmore one\n## Task 2\ntwo\n"
    assert "more one" in TB.extract_task(plan, 1)


def test_a_plan_saved_with_a_bom_still_finds_its_first_task(tmp_path):
    plan = tmp_path / "plan.md"
    plan.write_bytes(b"\xef\xbb\xbf## Task 1: first\nbody one\n")
    out = tmp_path / "brief.md"
    assert TB.main([str(plan), "1", str(out)]) == 0
    assert "body one" in out.read_text(encoding="utf-8")


# ---- default output file ------------------------------------------------------------------------
def test_two_plans_in_one_worktree_do_not_share_a_brief_file(repo, capsys):
    (repo / "a.md").write_text("## Task 1: plan A\nA\n", encoding="utf-8")
    (repo / "b.md").write_text("## Task 1: plan B\nB\n", encoding="utf-8")
    assert TB.main([str(repo / "a.md"), "1"]) == 0
    assert TB.main([str(repo / "b.md"), "1"]) == 0
    briefs = sorted((repo / ".bitranox" / "sdd").glob("task-1-*brief.md"))
    assert len(briefs) == 2
    assert {b.read_text(encoding="utf-8").split("\n")[0] for b in briefs} == {
        "## Task 1: plan A", "## Task 1: plan B"}


def test_the_default_brief_name_is_stable_for_one_plan(repo, capsys):
    (repo / "a.md").write_text("## Task 1: plan A\nA\n", encoding="utf-8")
    assert TB.main([str(repo / "a.md"), "1"]) == 0
    first = capsys.readouterr().out
    assert TB.main([str(repo / "a.md"), "1"]) == 0
    assert capsys.readouterr().out == first


def test_a_task_that_is_not_found_leaves_an_existing_brief_alone(tmp_path):
    plan = tmp_path / "plan.md"
    plan.write_text("## Task 1\none\n", encoding="utf-8")
    out = tmp_path / "brief.md"
    out.write_text("pre-existing brief\n", encoding="utf-8")
    assert TB.main([str(plan), "7", str(out)]) == 3
    assert out.read_text(encoding="utf-8") == "pre-existing brief\n"
