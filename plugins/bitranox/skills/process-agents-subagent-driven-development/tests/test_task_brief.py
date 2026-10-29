"""task_brief.py: task boundaries, CommonMark fences, task ids, and the default output file."""
import json
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
    assert TB.main([str(plan), "7", str(out)]) == 1
    assert out.read_text(encoding="utf-8") == "pre-existing brief\n"


# ---- one id, two headings (D4) -------------------------------------------------------------------
DUP_PLAN = ("# Plan\n\n# Phase A\n\n## Task 3: alpha\n\nbody alpha\n\n"
            "# Phase B\n\n## Task 3: beta\n\nbody beta\n\n## Task 4: other\n\nfour\n")


def test_two_headings_with_one_id_refuse_with_exit_2_and_name_both_lines(tmp_path, capsys):
    """A plan whose phases restart numbering must not hand one agent two unrelated tasks."""
    plan = tmp_path / "plan.md"
    plan.write_bytes(DUP_PLAN.encode("utf-8"))
    out = tmp_path / "brief.md"
    out.write_bytes(b"pre-existing brief\n")
    assert TB.main([str(plan), "3", str(out)]) == 2
    err = capsys.readouterr().err
    assert "line 5: ## Task 3: alpha" in err
    assert "line 11: ## Task 3: beta" in err
    assert out.read_bytes() == b"pre-existing brief\n"


def test_a_unique_id_in_the_same_plan_still_writes_its_brief(tmp_path):
    """Control for the refusal: only the duplicated id is refused."""
    plan = tmp_path / "plan.md"
    plan.write_bytes(DUP_PLAN.encode("utf-8"))
    out = tmp_path / "brief.md"
    assert TB.main([str(plan), "4", str(out)]) == 0
    assert out.read_text(encoding="utf-8") == "## Task 4: other\n\nfour\n"


def test_a_same_id_heading_inside_a_fence_is_not_a_second_task(tmp_path):
    plan = tmp_path / "plan.md"
    plan.write_bytes(b"## Task 3: real\n\nbody\n\n```\n## Task 3: quoted example\n```\n")
    assert TB.main([str(plan), "3", str(tmp_path / "brief.md")]) == 0


def test_task_headings_reports_one_based_lines_outside_fences():
    found = TB.task_headings(DUP_PLAN, "3")
    assert found == [(5, "## Task 3: alpha"), (11, "## Task 3: beta")]


# ---- a plan that cannot be read -----------------------------------------------------------------
def test_a_plan_that_is_not_utf8_is_exit_2_not_a_traceback(tmp_path, capsys):
    plan = tmp_path / "plan.md"
    plan.write_bytes(b"## Task 1\n\xff\xfe broken\n")
    assert TB.main([str(plan), "1", str(tmp_path / "brief.md")]) == 2
    assert "cannot read the plan" in capsys.readouterr().err
    assert not (tmp_path / "brief.md").exists()


def test_a_directory_given_as_the_plan_is_exit_2(tmp_path, capsys):
    assert TB.main([str(tmp_path), "1", str(tmp_path / "brief.md")]) == 2
    assert "no such plan file" in capsys.readouterr().err


# ---- the plan's Global Constraints travel with every brief (C10) --------------------------------
GC_PLAN = ("# Plan\n\n**Goal:** g\n\n## Global Constraints\n\n"
           "* Python 3.11+.\n"
           "* Every new test file is listed in SEED_SOURCES. This applies to Tasks 1 and 2,\n"
           "  so tests/test_launch.py is in scope despite not appearing in their Files lists.\n"
           "\n---\n\n### Task 1: first\n\n**Files:**\n- Create: `a.py`\n\n"
           "### Task 2: second\n\n**Files:**\n- Create: `b.py`\n\n## Self-review\n\nno\n")


def test_the_brief_carries_the_global_constraints_section_ahead_of_the_task(tmp_path):
    plan = tmp_path / "plan.md"
    plan.write_bytes(GC_PLAN.encode("utf-8"))
    out = tmp_path / "brief.md"
    assert TB.main([str(plan), "2", str(out)]) == 0
    brief = out.read_text(encoding="utf-8")
    assert brief.startswith("## Global Constraints\n")
    assert "tests/test_launch.py is in scope" in brief
    assert brief.index("## Global Constraints") < brief.index("### Task 2: second")
    assert "- Create: `b.py`" in brief
    assert "Create: `a.py`" not in brief      # the constraints section ends at the first task
    assert "no\n" not in brief.split("### Task 2: second", 1)[1]


def test_the_constraints_section_ends_at_a_heading_of_its_own_level():
    plan = "## Global constraints\n\nc1\n\n## File Structure\n\nfs\n\n## Task 1\n\none\n"
    section = TB.global_constraints(plan)
    assert "c1" in section and "fs" not in section


def test_a_plan_without_global_constraints_gives_the_task_alone(tmp_path):
    plan = tmp_path / "plan.md"
    plan.write_bytes(b"# Plan\n\n## Task 1: only\n\nbody\n")
    out = tmp_path / "brief.md"
    assert TB.main([str(plan), "1", str(out)]) == 0
    assert out.read_text(encoding="utf-8") == "## Task 1: only\n\nbody\n"


def test_a_constraints_heading_inside_a_fence_is_not_the_section():
    plan = "```\n## Global Constraints\nfake\n```\n## Task 1\none\n"
    assert TB.global_constraints(plan) == ""


def test_a_plan_with_constraints_but_no_such_task_is_still_not_found(tmp_path):
    plan = tmp_path / "plan.md"
    plan.write_bytes(GC_PLAN.encode("utf-8"))
    out = tmp_path / "brief.md"
    assert TB.main([str(plan), "9", str(out)]) == 1
    assert not out.exists()


# ---- dotted ids with a letter suffix ------------------------------------------------------------
SPLIT_PLAN = ("### Task 2.1: first half\n\nbody two-one\n\n"
              "### Task 2.1b: second half\n\nbody two-one-b\n\n"
              "### Task 3.2.1: nested\n\nbody nested\n")


def test_a_dotted_id_with_a_letter_suffix_is_its_own_task():
    """A review split 2.1 into 2.1 and 2.1b: '2.1b' must not be read as task 2."""
    assert "body two-one-b" in TB.extract_task(SPLIT_PLAN, "2.1b")
    assert "body two-one-b" not in TB.extract_task(SPLIT_PLAN, "2.1")
    assert TB.extract_task(SPLIT_PLAN, 2) == ""
    assert TB.task_headings(SPLIT_PLAN, "2.1b") == [(5, "### Task 2.1b: second half")]


def test_a_multi_level_dotted_id_is_its_own_task():
    assert "body nested" in TB.extract_task(SPLIT_PLAN, "3.2.1")
    assert TB.extract_task(SPLIT_PLAN, 3) == ""


# ---- a plan with no task headings at all --------------------------------------------------------
def test_a_plan_with_no_task_headings_says_how_to_restructure_it(tmp_path, capsys):
    """A plan written as prose or a numbered list has nothing to extract: the refusal must say the
    plan needs Task headings, not only that one id is missing."""
    plan = tmp_path / "plan.md"
    plan.write_bytes(b"# Plan\n\n## Context\n\ndecided X\n\n## 1. Spike\n\n"
                     b"1. **Spike (opus)**: go\n")
    assert TB.main([str(plan), "1", str(tmp_path / "brief.md")]) == 1
    err = capsys.readouterr().err
    assert "has no 'Task <id>' headings at all" in err
    assert "Global Constraints" in err


def test_a_plan_with_other_task_headings_gets_only_the_plain_not_found(tmp_path, capsys):
    """Control: an id that is merely absent from a structured plan is not a restructure case."""
    plan = tmp_path / "plan.md"
    plan.write_bytes(b"## Task 1\none\n")
    assert TB.main([str(plan), "7", str(tmp_path / "brief.md")]) == 1
    err = capsys.readouterr().err
    assert "no heading matching 'Task 7'" in err
    assert "at all" not in err


# ---- the enclosing section's preamble travels with the task --------------------------------------
MILESTONE_PLAN = ("# Plan title\n\n**Goal:** g\n\n## Global Constraints\n\n* gc line\n\n"
                  "## DETAILED tasks - M2\n\nShared procedures for every task below.\n\n"
                  "### P1 - privacy scan\n\nrun the scan\n\n### P2 - gate\n\nrun the gate\n\n"
                  "### Task 2.1: first\n\nbody 2.1, then P1 and P2\n\n"
                  "### Task 2.2: second\n\nbody 2.2\n\n"
                  "## M3\n\n### Task 3.1: third\n\nbody 3.1\n")


@pytest.mark.parametrize("task", ["2.1", "2.2"])
def test_every_task_of_a_milestone_carries_its_shared_preamble(task):
    brief = TB.build_brief(MILESTONE_PLAN, task)
    assert "### P1 - privacy scan" in brief and "run the gate" in brief
    assert brief.index("* gc line") < brief.index("## DETAILED tasks - M2") \
        < brief.index(f"### Task {task}")


def test_a_preamble_with_no_text_is_not_carried_and_another_milestone_is_not_either():
    brief = TB.build_brief(MILESTONE_PLAN, "3.1")
    assert "## M3" not in brief
    assert "privacy scan" not in brief
    assert brief.endswith("### Task 3.1: third\n\nbody 3.1\n")


def test_the_plan_title_section_is_not_carried_as_a_preamble():
    """The title's text is the plan header (Goal, a pointer to this skill), not a procedure."""
    plan = "# Plan title\n\n**Goal:** g\n\n> use the SDD skill\n\n## Task 1: only\n\nbody\n"
    assert TB.build_brief(plan, 1) == "## Task 1: only\n\nbody\n"


def test_a_milestone_that_opens_a_plan_without_a_title_is_still_carried():
    plan = "## M1 procedures\n\nP1: scan first\n\n### Task 1: one\n\nbody one\n"
    assert "P1: scan first" in TB.build_brief(plan, 1)


# ---- --decision: user decisions quoted verbatim -------------------------------------------------
DECISION_PLAN = "## Global Constraints\n\n* gc\n\n### Task 1: one\n\nbody one\n"


def _decision(question, chosen, options, multi=False, annotation=None):
    return {"ts": "2026-10-16T10:00:00Z", "session_id": "s", "cwd": "/opt/x", "question": question,
            "header": "H", "multiSelect": multi, "options": options, "chosen": chosen,
            "chosen_options": [o for o in options if o["label"] == chosen],
            "annotation": annotation}


DECISIONS = [
    _decision("When does the sync window start?", "Only a real sync",
              [{"label": "Every result", "description": "any attempt opens it"},
               {"label": "Only a real sync",
                "description": "only an attempt where ssh got in and ntpd ran starts the window"}]),
    _decision("Which log format?", "JSON lines",
              [{"label": "JSON lines", "description": "one object per line"},
               {"label": "Plain text", "description": "human readable"}]),
    _decision("Which log retention?", "30 days",
              [{"label": "30 days", "description": "rotate monthly"},
               {"label": "Forever", "description": "never rotate"}]),
]


def _decisions_file(tmp_path, rows=DECISIONS, extra_lines=()):
    path = tmp_path / "decisions.jsonl"
    lines = [json.dumps(r) for r in rows] + list(extra_lines)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _plan(tmp_path):
    plan = tmp_path / "plan.md"
    plan.write_text(DECISION_PLAN, encoding="utf-8")
    return plan


def test_a_matched_decision_is_appended_verbatim_under_its_own_heading(tmp_path):
    out = tmp_path / "brief.md"
    rc = TB.main([str(_plan(tmp_path)), "1", str(out), "--decision", "sync window",
                  "--decisions-file", str(_decisions_file(tmp_path))])
    assert rc == 0
    brief = out.read_text(encoding="utf-8")
    assert "## User decisions" in brief
    assert "When does the sync window start?" in brief
    assert "Only a real sync" in brief
    assert "only an attempt where ssh got in and ntpd ran starts the window" in brief
    assert "any attempt opens it" not in brief      # an option nobody chose is not relayed
    assert brief.index("* gc") < brief.index("## User decisions") < brief.index("### Task 1")


def test_the_text_may_match_the_chosen_label_and_the_flag_repeats(tmp_path):
    out = tmp_path / "brief.md"
    rc = TB.main([str(_plan(tmp_path)), "1", str(out), "--decision", "JSON lines",
                  "--decision", "30 days", "--decisions-file", str(_decisions_file(tmp_path))])
    assert rc == 0
    brief = out.read_text(encoding="utf-8")
    assert "one object per line" in brief and "rotate monthly" in brief


def test_a_decision_text_that_matches_no_record_is_refused_and_writes_nothing(tmp_path, capsys):
    out = tmp_path / "brief.md"
    out.write_text("pre-existing brief\n", encoding="utf-8")
    rc = TB.main([str(_plan(tmp_path)), "1", str(out), "--decision", "no such thing",
                  "--decisions-file", str(_decisions_file(tmp_path))])
    assert rc == 1
    assert "no such thing" in capsys.readouterr().err
    assert out.read_text(encoding="utf-8") == "pre-existing brief\n"


def test_a_decision_text_that_matches_two_records_is_refused_naming_both(tmp_path, capsys):
    out = tmp_path / "brief.md"
    rc = TB.main([str(_plan(tmp_path)), "1", str(out), "--decision", "log",
                  "--decisions-file", str(_decisions_file(tmp_path))])
    assert rc == 1
    err = capsys.readouterr().err
    assert "'log'" in err
    assert "Which log format?" in err and "Which log retention?" in err
    assert not out.exists()


def test_a_multi_select_answer_relays_every_chosen_option(tmp_path):
    rows = [_decision("Which platforms?", "Linux, Windows",
                      [{"label": "Linux", "description": "the CI default"},
                       {"label": "Windows", "description": "the self-hosted runner"},
                       {"label": "macOS", "description": "not this release"}], multi=True,
                      annotation="Windows only for the gate")]
    out = tmp_path / "brief.md"
    assert TB.main([str(_plan(tmp_path)), "1", str(out), "--decision", "platforms",
                    "--decisions-file", str(_decisions_file(tmp_path, rows))]) == 0
    brief = out.read_text(encoding="utf-8")
    assert "the CI default" in brief and "the self-hosted runner" in brief
    assert "not this release" not in brief
    assert "Windows only for the gate" in brief


def test_a_broken_line_in_the_decisions_file_is_skipped_not_fatal(tmp_path):
    out = tmp_path / "brief.md"
    path = _decisions_file(tmp_path, extra_lines=["{not json", "[1, 2]"])
    assert TB.main([str(_plan(tmp_path)), "1", str(out), "--decision", "sync window",
                    "--decisions-file", str(path)]) == 0


def test_a_missing_decisions_file_is_exit_2(tmp_path, capsys):
    rc = TB.main([str(_plan(tmp_path)), "1", str(tmp_path / "brief.md"), "--decision", "x",
                  "--decisions-file", str(tmp_path / "absent.jsonl")])
    assert rc == 2
    assert "absent.jsonl" in capsys.readouterr().err


def test_without_decision_flags_the_brief_is_unchanged(tmp_path):
    out = tmp_path / "brief.md"
    assert TB.main([str(_plan(tmp_path)), "1", str(out),
                    "--decisions-file", str(_decisions_file(tmp_path))]) == 0
    assert "User decisions" not in out.read_text(encoding="utf-8")


def test_the_default_decisions_file_is_the_main_checkout_root_of_a_linked_worktree(repo, tmp_path,
                                                                                    monkeypatch):
    """The same place hooks/user-decision-log.py writes it: a worktree finds the main checkout's."""
    git = ["git", "-c", "user.name=t", "-c", "user.email=t@example.com"]
    subprocess.run(git + ["commit", "-q", "--allow-empty", "-m", "base"], cwd=repo, check=True)
    linked = tmp_path / "linked"
    subprocess.run(["git", "worktree", "add", "-q", "--detach", str(linked)], cwd=repo, check=True)
    _decisions_file(tmp_path)  # a decoy outside the repo must not be read
    (repo / "USER-DECISIONS.jsonl").write_text(
        "\n".join(json.dumps(r) for r in DECISIONS) + "\n", encoding="utf-8")
    plan = linked / "plan.md"
    plan.write_text(DECISION_PLAN, encoding="utf-8")
    out = tmp_path / "brief.md"
    monkeypatch.chdir(linked)
    assert TB.main([str(plan), "1", str(out), "--decision", "sync window"]) == 0
    assert "ntpd ran starts the window" in out.read_text(encoding="utf-8")


def test_a_record_with_no_chosen_label_is_not_matched_by_the_text_none(tmp_path, capsys):
    # A missing `chosen` once read as the string "None", so "--decision one" matched it.
    unanswered = {**_decision("Which cache?", None, []), "chosen": None}
    out = tmp_path / "brief.md"
    rc = TB.main([str(_plan(tmp_path)), "1", str(out), "--decision", "one",
                  "--decisions-file", str(_decisions_file(tmp_path, rows=[unanswered]))])
    assert rc == 1
    assert "matches no recorded" in capsys.readouterr().err


def test_help_exits_zero(capsys):
    assert TB.main(["--help"]) == 0
    assert "usage: task_brief.py" in capsys.readouterr().out
