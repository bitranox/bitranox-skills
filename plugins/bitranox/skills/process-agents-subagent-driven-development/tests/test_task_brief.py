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


# ---- a trailing non-task section ----------------------------------------------------------------
def test_a_section_after_the_last_task_is_not_part_of_it():
    plan = ("# Plan\n\n## Task 1: only\n\nbody one\n\n### Step detail\n\nstill one\n\n"
            "## Rollout notes\n\nDelete the prod database\n")
    text = TB.extract_task(plan, 1)
    assert "still one" in text          # a deeper heading stays inside the task
    assert "Delete the prod database" not in text


def test_a_higher_level_heading_also_ends_the_task():
    plan = "### Task 1\none\n## Appendix\nnot one\n"
    assert "not one" not in TB.extract_task(plan, 1)


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
