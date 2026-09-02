"""RED-first tests for `enforced`: does anything actually DECIDE on this identifier?

The bug this tool exists to catch: a config field that is declared, typed, schema-validated and
read - and that nothing ever compares anything to. It looks like a mechanism and bounds nothing.
So the load-bearing assertions here are the ones about the DECISION bucket: a declaration, a
parse, a docstring mention and a test fixture must all stay OUT of it, or the tool reports
"enforced" for a field that is documentation.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from enforced import Hit, HitKind, classify_source, verdict_of


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
