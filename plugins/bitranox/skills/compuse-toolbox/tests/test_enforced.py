"""RED-first tests for `enforced`: does anything actually DECIDE on this identifier?

The bug this tool exists to catch: a config field that is declared, typed, schema-validated and
read - and that nothing ever compares anything to. It looks like a mechanism and bounds nothing.
So the load-bearing assertions here are the ones about the DECISION bucket: a declaration, a
parse, a docstring mention and a test fixture must all stay OUT of it, or the tool reports
"enforced" for a field that is documentation.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import enforced
from enforced import Hit, HitKind, classify_source, main, verdict_of


def kinds(hits: list[Hit]) -> set[HitKind]:
    return {h.kind for h in hits}


def decisions(hits: list[Hit]) -> list[Hit]:
    return [h for h in hits if h.kind is HitKind.DECISION]


class TestTheDecisionBucket:
    """Everything here is about what must NOT be mistaken for a decision."""

    def test_a_typed_field_declaration_is_not_a_decision(self) -> None:
        src = """
class RunLimits(BaseModel):
    planner_kinds: list[Kind]
"""
        hits = classify_source(src, "planner_kinds", path=Path("policy.py"))
        assert decisions(hits) == []
        assert HitKind.DECLARATION in kinds(hits)

    def test_reading_the_attribute_is_not_a_decision(self) -> None:
        """The exact shape that fooled two reviews: a real reader, deciding nothing."""
        src = """
def load(table):
    limits = table.run_limits
    log.info("planner kinds: %s", limits.planner_kinds)
    return limits.planner_kinds
"""
        hits = classify_source(src, "planner_kinds", path=Path("loader.py"))
        assert decisions(hits) == []
        assert hits, "a plain read must still be reported, just not as a decision"

    def test_a_docstring_mention_is_not_a_decision(self) -> None:
        src = '''
def check():
    """The planner_kinds list bounds what a plan may emit."""
    return True
'''
        hits = classify_source(src, "planner_kinds", path=Path("check.py"))
        assert decisions(hits) == []
        assert HitKind.DOCSTRING in kinds(hits)

    def test_a_comment_mention_is_not_a_decision(self) -> None:
        src = """
def check(spec):
    # planner_kinds would go here
    return True
"""
        hits = classify_source(src, "planner_kinds", path=Path("check.py"))
        assert decisions(hits) == []
        assert HitKind.COMMENT in kinds(hits)

    def test_a_test_file_hit_is_not_a_decision(self) -> None:
        """A fixture asserting on the field proves the field exists, never that it binds."""
        src = """
def test_planner_kinds_is_typed():
    assert policy.planner_kinds == ["work"]
"""
        hits = classify_source(src, "planner_kinds", path=Path("tests/test_policy.py"))
        assert decisions(hits) == []
        assert HitKind.TEST in kinds(hits)


class TestWhatIsADecision:
    def test_a_membership_comparison_is_a_decision(self) -> None:
        src = """
def admit(spec, limits):
    if spec.kind not in limits.planner_kinds:
        raise Refused(spec.kind)
"""
        hits = classify_source(src, "planner_kinds", path=Path("admit.py"))
        assert len(decisions(hits)) == 1
        assert decisions(hits)[0].line == 3

    def test_an_equality_comparison_is_a_decision(self) -> None:
        src = """
def admit(spec, limits):
    if spec.kind == limits.planner_kinds:
        return True
"""
        assert len(decisions(classify_source(src, "planner_kinds", path=Path("a.py")))) == 1

    def test_a_bare_truth_test_is_a_decision(self) -> None:
        """`if limits.planner_kinds:` branches on it without comparing it to anything."""
        src = """
def admit(limits):
    if limits.planner_kinds:
        return True
"""
        assert len(decisions(classify_source(src, "planner_kinds", path=Path("a.py")))) == 1

    def test_a_while_test_is_a_decision(self) -> None:
        src = """
def drain(limits):
    while limits.planner_kinds:
        limits.planner_kinds.pop()
"""
        assert decisions(classify_source(src, "planner_kinds", path=Path("a.py")))

    def test_a_guard_raising_on_the_value_is_a_decision(self) -> None:
        src = """
def admit(spec, limits):
    if spec.kind not in limits.planner_kinds:
        raise Refused()
    return True
"""
        assert decisions(classify_source(src, "planner_kinds", path=Path("a.py")))


class TestTheVerdict:
    def test_no_decision_reads_as_parsed_but_never_enforced(self) -> None:
        src = "class C(BaseModel):\n    planner_kinds: list[str]\n"
        hits = classify_source(src, "planner_kinds", path=Path("p.py"))
        assert verdict_of(hits).enforced is False
        assert "never enforced" in verdict_of(hits).summary

    def test_a_decision_reads_as_enforced(self) -> None:
        src = "def f(s, l):\n    if s.kind not in l.planner_kinds:\n        raise E()\n"
        hits = classify_source(src, "planner_kinds", path=Path("p.py"))
        assert verdict_of(hits).enforced is True

    def test_no_hits_at_all_is_neither_enforced_nor_a_silent_pass(self) -> None:
        """An identifier nobody mentions must not read as 'not enforced' - it is a bad query."""
        hits = classify_source("x = 1\n", "planner_kinds", path=Path("p.py"))
        assert hits == []
        assert verdict_of(hits).enforced is False
        assert verdict_of(hits).found is False


class TestItDoesNotLieAboutOtherNames:
    def test_a_substring_of_another_identifier_is_not_a_hit(self) -> None:
        """`grep planner_kinds` would match `planner_kinds_extra`; an AST walk must not."""
        src = """
def admit(spec, limits):
    if spec.kind not in limits.planner_kinds_extra:
        raise E()
"""
        assert classify_source(src, "planner_kinds", path=Path("a.py")) == []

    def test_a_syntax_error_is_reported_not_swallowed(self) -> None:
        with pytest.raises(SyntaxError):
            classify_source("def (:\n", "planner_kinds", path=Path("broken.py"))


class TestAValueReboundToALocalIsStillEnforced:
    """The false-negative class that nearly shipped.

    Measured 2026-08-26 against agentdag: `tokens_per_row` IS enforced, but the enforcing
    function binds it to a local first (`ceiling = self.policy.tokens_per_row.get(row)`) and
    compares THAT. An identifier-only walk reports "parsed but never enforced" for a field that
    genuinely bounds - the exact wrong answer this tool exists to prevent, delivered confidently.
    """

    def test_a_local_alias_carries_the_decision_back(self) -> None:
        src = """
def refuse(self, row, total):
    ceiling = self.policy.tokens_per_row.get(row)
    if total > ceiling:
        raise BudgetExceeded()
"""
        hits = classify_source(src, "tokens_per_row", path=Path("ctx.py"))
        assert decisions(hits), "a decision on the local alias must count for the field"

    def test_the_alias_hit_says_it_came_via_an_alias(self) -> None:
        src = """
def refuse(self, row, total):
    ceiling = self.policy.tokens_per_row.get(row)
    if total > ceiling:
        raise BudgetExceeded()
"""
        hit = decisions(classify_source(src, "tokens_per_row", path=Path("ctx.py")))[0]
        assert hit.via == "ceiling"

    def test_a_same_named_local_in_ANOTHER_function_does_not_count(self) -> None:
        """Alias following must be scoped, or any common name manufactures a decision."""
        src = """
def reads(self, row):
    ceiling = self.policy.tokens_per_row.get(row)
    return ceiling

def unrelated(total):
    ceiling = 5
    if total > ceiling:
        raise E()
"""
        assert decisions(classify_source(src, "tokens_per_row", path=Path("ctx.py"))) == []

    def test_a_plain_read_with_no_later_decision_stays_not_enforced(self) -> None:
        src = """
def reads(self, row):
    ceiling = self.policy.tokens_per_row.get(row)
    log.info("ceiling is %s", ceiling)
    return ceiling
"""
        hits = classify_source(src, "tokens_per_row", path=Path("ctx.py"))
        assert decisions(hits) == []
        assert verdict_of(hits).enforced is False


class TestAClampBoundsWithoutBranching:
    """Third false-negative class, found by the tool's own sweep on 2026-08-26.

    `deadline_ceiling_s` IS enforced: `min(spec.deadline_s, policy.deadline_ceiling_s)` caps every
    node's deadline. There is no Compare and no If anywhere near it, so a decision-only walk calls
    a real bound "documentation". A clamp is enforcement by a different mechanism, not an absence
    of one, and the report must say WHICH - a reader checking a safety claim needs to know whether
    the value refuses or silently truncates.
    """

    def test_a_min_clamp_counts_as_enforcement(self) -> None:
        src = """
def dispatch(self, spec):
    node_deadline_s = min(spec.deadline_s, self.policy.deadline_ceiling_s)
    return node_deadline_s
"""
        hits = classify_source(src, "deadline_ceiling_s", path=Path("ctx.py"))
        assert HitKind.CLAMP in kinds(hits)
        assert verdict_of(hits).enforced is True

    def test_a_max_clamp_counts_too(self) -> None:
        src = "def f(self, v):\n    return max(v, self.policy.floor_x)\n"
        assert HitKind.CLAMP in kinds(classify_source(src, "floor_x", path=Path("a.py")))

    def test_a_clamp_is_reported_as_a_clamp_not_a_decision(self) -> None:
        """Distinct buckets: refusing and truncating are different guarantees."""
        src = "def f(self, s):\n    return min(s.d, self.policy.deadline_ceiling_s)\n"
        hits = classify_source(src, "deadline_ceiling_s", path=Path("a.py"))
        assert decisions(hits) == []
        assert verdict_of(hits).counts.get("clamp") == 1

    def test_an_ordinary_call_is_not_a_clamp(self) -> None:
        """Only the bounding builtins count; any call would make every argument enforcement."""
        src = "def f(self):\n    return log.info(self.policy.deadline_ceiling_s)\n"
        hits = classify_source(src, "deadline_ceiling_s", path=Path("a.py"))
        assert HitKind.CLAMP not in kinds(hits)
        assert verdict_of(hits).enforced is False


# ---- review fixes (rank-10 slice 2, group T3): the tree walk and the CLI ------------------------

POLICY = "class Limits:\n    planner_kinds: list[str]\n"
GUARD = "def admit(spec, limits):\n    if spec.kind not in limits.planner_kinds:\n        raise E()\n"
TEST_ASSERT = "def check(limits):\n    assert limits.planner_kinds == ['work']\n"


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def run(root: Path, identifier: str = "planner_kinds", *extra: str) -> int:
    return main([identifier, "--root", str(root), *extra])


class TestWhatCountsAsATestFile:
    @pytest.mark.parametrize("name", ["admit_test.py", "conftest.py"])
    def test_a_test_module_named_by_suffix_or_conftest_is_test(self, tmp_path: Path, name: str) -> None:
        """pytest collects `*_test.py` and runs conftest.py; an assert there is not an enforcer."""
        write(tmp_path / "colo" / "policy.py", POLICY)
        write(tmp_path / "colo" / name, TEST_ASSERT)
        assert run(tmp_path / "colo") == 1

    def test_a_test_directory_above_the_root_does_not_make_everything_test(self, tmp_path: Path) -> None:
        write(tmp_path / "test" / "app" / "admit.py", GUARD)
        assert run(tmp_path / "test" / "app") == 0

    def test_a_tests_directory_below_the_root_still_is_test(self, tmp_path: Path) -> None:
        write(tmp_path / "app" / "policy.py", POLICY)
        write(tmp_path / "app" / "tests" / "helpers.py", GUARD)
        assert run(tmp_path / "app") == 1


class TestWhatTheWalkSkips:
    def test_a_skip_dir_above_the_root_does_not_skip_the_project(self, tmp_path: Path) -> None:
        write(tmp_path / "venv" / "app" / "admit.py", GUARD)
        assert run(tmp_path / "venv" / "app") == 0

    @pytest.mark.parametrize("vendored", [".venv-win", ".venv-3.12", ".tox", "site-packages"])
    def test_vendored_trees_are_skipped(self, tmp_path: Path, vendored: str) -> None:
        """A third-party decision under a suffixed venv read as this project's enforcer."""
        write(tmp_path / "nv" / "src" / "policy.py", POLICY)
        write(tmp_path / "nv" / vendored / "lib" / "lib3p" / "core.py", GUARD)
        assert run(tmp_path / "nv") == 1

    @pytest.mark.skipif(sys.platform == "win32",
                        reason="Windows has no POSIX mode bits: chmod(0o000) leaves the dir readable")
    def test_an_unreadable_directory_makes_the_answer_incomplete(self, tmp_path: Path, capsys) -> None:
        write(tmp_path / "p" / "policy.py", POLICY)
        locked = tmp_path / "p" / "locked"
        write(locked / "admit.py", GUARD)
        locked.chmod(0o000)
        try:
            if os.access(locked, os.R_OK):
                pytest.skip("running with privileges that read a mode-000 dir (root)")
            rc = run(tmp_path / "p")
        finally:
            locked.chmod(0o755)
        assert rc == 2
        assert "UNREAD" in capsys.readouterr().out

    @pytest.mark.parametrize("name", [".env", ".env.production"])
    def test_a_dotenv_file_is_config(self, tmp_path: Path, name: str, capsys) -> None:
        write(tmp_path / name, "on_auth_failure=fail_run\n")
        assert run(tmp_path, "on_auth_failure") == 1
        assert "config (1)" in capsys.readouterr().out


class TestMoreDecisionShapes:
    def test_a_match_subject_is_a_decision(self) -> None:
        src = ("def run(policy):\n    match policy.on_auth_failure:\n        case 'fail_run':\n"
               "            raise Stop()\n")
        assert decisions(classify_source(src, "on_auth_failure", path=Path("run.py")))

    def test_a_case_guard_is_a_decision(self) -> None:
        src = ("def run(x, policy):\n    match x:\n        case 1 if policy.strict:\n"
               "            raise Stop()\n")
        assert decisions(classify_source(src, "strict", path=Path("run.py")))

    def test_a_case_body_is_not_a_decision(self) -> None:
        src = ("def run(x, policy):\n    match x:\n        case 1:\n"
               "            log(policy.strict)\n")
        assert decisions(classify_source(src, "strict", path=Path("run.py"))) == []

    def test_an_annotated_alias_carries_the_decision_back(self) -> None:
        src = """
def refuse(self, row):
    ceiling: int = self.policy.tokens_per_row.get(row)
    if row.tokens > ceiling:
        raise BudgetExceeded()
"""
        hit = decisions(classify_source(src, "tokens_per_row", path=Path("ctx.py")))[0]
        assert hit.via == "ceiling"


class TestProseMatchesWholeWords:
    @pytest.mark.parametrize("src", [
        "# rate_limit is read elsewhere\nrate_limit = 5\n",
        'x = "a # limit"\n',
        'def f():\n    """rate_limit doc"""\n',
    ])
    def test_a_longer_name_or_a_string_is_not_a_prose_hit(self, src: str) -> None:
        hits = classify_source(src, "limit", path=Path("a.py"))
        assert not [h for h in hits if h.kind in (HitKind.COMMENT, HitKind.DOCSTRING)]

    def test_a_whole_word_comment_still_counts(self) -> None:
        hits = classify_source("x = 1  # limit applies here\n", "limit", path=Path("a.py"))
        assert HitKind.COMMENT in kinds(hits)

    def test_a_longer_config_key_is_not_a_hit(self, tmp_path: Path) -> None:
        write(tmp_path / "c.yaml", "rate_limit: 5\n")
        assert run(tmp_path, "limit") == 2


class TestReadingTheSource:
    def test_a_bom_file_is_read_not_unread(self, tmp_path: Path) -> None:
        (tmp_path / "admit.py").write_bytes(b"\xef\xbb\xbf" + GUARD.encode("utf-8"))
        assert run(tmp_path) == 0

    def test_a_form_feed_does_not_shift_the_line_text(self) -> None:
        src = "x = 1\x0c\nif s.kind in l.planner_kinds:\n    pass\n"
        [hit] = decisions(classify_source(src, "planner_kinds", path=Path("a.py")))
        assert hit.line == 2 and hit.text.startswith("if s.kind")


class TestTheCli:
    def test_exit_0_when_enforced(self, tmp_path: Path) -> None:
        write(tmp_path / "admit.py", GUARD)
        assert run(tmp_path) == 0

    def test_exit_1_when_parsed_but_never_enforced(self, tmp_path: Path) -> None:
        write(tmp_path / "policy.py", POLICY)
        assert run(tmp_path) == 1

    def test_exit_2_when_not_found(self, tmp_path: Path) -> None:
        write(tmp_path / "other.py", "x = 1\n")
        assert run(tmp_path) == 2

    def test_exit_2_for_a_missing_root_with_json(self, tmp_path: Path, capsys) -> None:
        assert run(tmp_path / "nope", "planner_kinds", "--json") == 2
        assert json.loads(capsys.readouterr().out)["ok"] is False

    @pytest.mark.skipif(sys.platform == "win32",
                        reason="Windows has no POSIX mode bits: chmod(0o000) leaves the dir readable")
    @pytest.mark.parametrize("extra", [[], ["--json"]])
    def test_a_root_under_an_unreadable_dir_is_exit_2_not_a_traceback(self, tmp_path: Path, capsys,
                                                                       extra: list[str]) -> None:
        """Before Python 3.14 Path.exists() RAISES PermissionError here, and the traceback's
        exit 1 means "parsed but never enforced". It must be exit 2 naming why."""
        locked = tmp_path / "locked"
        write(locked / "app" / "admit.py", GUARD)
        locked.chmod(0o000)
        try:
            if os.access(locked, os.R_OK):
                pytest.skip("running with privileges that read a mode-000 dir (root)")
            rc = run(locked / "app", "planner_kinds", *extra)
        finally:
            locked.chmod(0o755)
        captured = capsys.readouterr()
        assert rc == 2
        said = captured.out if extra else captured.err
        assert "PermissionError" in said and "no such root" not in said
        if extra:
            assert json.loads(captured.out)["ok"] is False

    def test_a_missing_root_still_says_no_such_root(self, tmp_path: Path, capsys) -> None:
        """Control for the refusal above: a genuinely missing root keeps its own message."""
        assert run(tmp_path / "nope") == 2
        assert "no such root" in capsys.readouterr().err

    def test_an_unparsable_file_without_a_decision_is_exit_2(self, tmp_path: Path, capsys) -> None:
        write(tmp_path / "policy.py", POLICY)
        write(tmp_path / "broken.py", "def (:\n")
        assert run(tmp_path) == 2
        assert "UNREAD" in capsys.readouterr().out

    def test_json_envelope(self, tmp_path: Path, capsys) -> None:
        write(tmp_path / "admit.py", GUARD)
        assert run(tmp_path, "planner_kinds", "--json") == 0
        payload = json.loads(capsys.readouterr().out)
        assert payload["ok"] is True and payload["command"] == "enforced"
        assert payload["data"]["verdict"]["enforced"] is True
        assert [h["kind"] for h in payload["data"]["hits"]] == ["decision"]

    def test_a_single_file_root(self, tmp_path: Path) -> None:
        assert run(write(tmp_path / "admit.py", GUARD)) == 0

    def test_survives_a_cp1252_stdout(self, tmp_path: Path) -> None:
        write(tmp_path / "admit.py", GUARD.replace("raise E()", "raise E('\u2192')")
              .replace("if spec", "if '\u2192' and spec"))
        env = {**os.environ, "PYTHONIOENCODING": "cp1252"}
        env.pop("PYTHONUTF8", None)
        done = subprocess.run([sys.executable, enforced.__file__, "planner_kinds", "--root",
                               str(tmp_path)], env=env, capture_output=True, timeout=60)
        assert b"Traceback" not in done.stderr, done.stderr
        assert done.returncode == 0


# ---- review fixes (rank-8 LOW batch, group L4b) -------------------------------------------------

class TestARootThatIsATestDirectory:
    """--root pointed AT a tests dir used to judge each file only by the path below it, so a helper
    there (no test_ prefix) read as production code and its assert as the enforcer: exit 0."""

    @pytest.mark.parametrize("dirname", ["tests", "test", "Tests"])
    def test_an_assert_in_a_helper_under_a_tests_root_is_not_a_decision(self, tmp_path: Path,
                                                                       dirname: str) -> None:
        write(tmp_path / "proj" / dirname / "helpers.py", TEST_ASSERT)
        assert run(tmp_path / "proj" / dirname) == 1

    def test_a_single_file_root_inside_a_tests_dir_is_test(self, tmp_path: Path) -> None:
        assert run(write(tmp_path / "proj" / "tests" / "helpers.py", TEST_ASSERT)) == 1

    def test_a_dot_root_that_is_a_tests_dir_is_test(self, tmp_path: Path, monkeypatch) -> None:
        """`--root .` from inside tests/: the root's own name is only visible once resolved."""
        write(tmp_path / "proj" / "tests" / "helpers.py", TEST_ASSERT)
        monkeypatch.chdir(tmp_path / "proj" / "tests")
        assert run(Path(".")) == 1

    @pytest.mark.parametrize("marker", ["pyproject.toml", "setup.py", "setup.cfg", ".git"])
    def test_a_project_root_named_test_is_still_the_project(self, tmp_path: Path, marker: str) -> None:
        """A project whose own top directory is called test keeps its enforcers."""
        write(tmp_path / "test" / marker, "")
        write(tmp_path / "test" / "admit.py", GUARD)
        assert run(tmp_path / "test") == 0


class TestAPythonFileNamedLikeDotenv:
    def test_a_dotenv_named_python_file_is_parsed_as_python(self, tmp_path: Path, capsys) -> None:
        """`.env.py` starts with `.env.`, but it is a Python module and its decision counts."""
        write(tmp_path / ".env.py", GUARD)
        assert run(tmp_path) == 0
        assert "config (" not in capsys.readouterr().out


class TestACasePatternIsADecision:
    @pytest.mark.parametrize("pattern", ["Mode.STRICT", "Mode.STRICT | Mode.LAX", "[Mode.STRICT, _]",
                                         "{'k': Mode.STRICT}"])
    def test_a_value_pattern_compares_the_subject_to_it(self, pattern: str) -> None:
        src = f"def run(x):\n    match x:\n        case {pattern}:\n            raise Stop()\n"
        hits = decisions(classify_source(src, "STRICT", path=Path("run.py")))
        assert [h.line for h in hits] == [3]

    def test_a_class_pattern_branches_on_the_class(self) -> None:
        src = "def run(x):\n    match x:\n        case Strict():\n            raise Stop()\n"
        assert decisions(classify_source(src, "Strict", path=Path("run.py")))
