"""RED-first tests for `confound`: may an explanation rest on this pair of arms?

The bug this tool exists to catch: "arm A differs from arm B because of X" written down while a
SECOND dimension had also moved between those two arms. It happened twice in one project, both
times with a real measurement, a working control and a green gate behind it - the number was
right and the causal sentence was not supported by it.

So the load-bearing assertions here are the ones that must come back CONFOUNDED. A tool that
calls a two-dimension pair clean is worse than no tool, because it launders the exact sentence
it was built to stop.
"""

from __future__ import annotations

import json
from typing import ClassVar

import pytest
from confound import (
    Arm,
    Verdict,
    compare_arms,
    main,
    pairs_inconclusive,
    pairs_no_effect,
    pairs_supporting,
    parse_arm,
)


def verdict_for(report, a: str, b: str) -> Verdict:
    """The verdict for one pair, whichever order the pair was emitted in."""
    for pair in report.pairs:
        if {pair.a, pair.b} == {a, b}:
            return pair.verdict
    raise AssertionError(f"no pair {a}/{b} in {[(p.a, p.b) for p in report.pairs]}")


def differing_for(report, a: str, b: str) -> tuple[str, ...]:
    for pair in report.pairs:
        if {pair.a, pair.b} == {a, b}:
            return pair.differing
    raise AssertionError(f"no pair {a}/{b}")


class TestTheVerdicts:
    """One dimension moving is the only shape that supports a causal claim."""

    def test_one_dimension_differing_is_clean(self) -> None:
        arms = [
            Arm("warm", {"model": "opus"}, outcome="100%"),
            Arm("cold", {"model": "fable"}, outcome="0%"),
        ]
        report = compare_arms(arms)
        assert verdict_for(report, "warm", "cold") is Verdict.CLEAN
        assert differing_for(report, "warm", "cold") == ("model",)

    def test_two_dimensions_differing_is_confounded(self) -> None:
        """The whole point. Both real failures had exactly this shape."""
        arms = [
            Arm("sonnet_warm", {"model": "sonnet", "tokens": "26854"}, outcome="100%"),
            Arm("haiku", {"model": "haiku", "tokens": "20350"}, outcome="0%"),
        ]
        report = compare_arms(arms)
        assert verdict_for(report, "sonnet_warm", "haiku") is Verdict.CONFOUNDED
        assert differing_for(report, "sonnet_warm", "haiku") == ("model", "tokens")

    def test_no_dimension_differing_and_the_same_outcome_is_a_replicate(self) -> None:
        arms = [
            Arm("run1", {"model": "opus"}, outcome="0%"),
            Arm("run2", {"model": "opus"}, outcome="0%"),
        ]
        report = compare_arms(arms)
        assert verdict_for(report, "run1", "run2") is Verdict.REPLICATE

    def test_no_dimension_differing_but_a_different_outcome_is_unexplained(
        self,
    ) -> None:
        """The one check that can see PAST the recorded dimensions: nothing you wrote down
        moved, and the outcome moved anyway, so something you did not record did."""
        arms = [
            Arm("run1", {"model": "opus"}, outcome="0%"),
            Arm("run2", {"model": "opus"}, outcome="100%"),
        ]
        report = compare_arms(arms)
        assert verdict_for(report, "run1", "run2") is Verdict.UNEXPLAINED

    def test_every_pair_is_reported_once(self) -> None:
        arms = [Arm(name, {"model": name}, outcome="x") for name in ("a", "b", "c")]
        report = compare_arms(arms)
        assert len(report.pairs) == 3
        assert {frozenset((p.a, p.b)) for p in report.pairs} == {
            frozenset(("a", "b")),
            frozenset(("a", "c")),
            frozenset(("b", "c")),
        }


class TestDimensionsOneArmDoesNotRecord:
    """A dimension present on one arm and absent on the other is a DIFFERENCE, not a match.
    Reading absence as agreement is how a confound hides."""

    def test_a_missing_dimension_counts_as_differing(self) -> None:
        arms = [
            Arm("with_env", {"model": "opus", "env": "full"}, outcome="1"),
            Arm("without", {"model": "opus"}, outcome="2"),
        ]
        report = compare_arms(arms)
        assert verdict_for(report, "with_env", "without") is Verdict.CLEAN
        assert differing_for(report, "with_env", "without") == ("env",)

    def test_a_missing_dimension_can_be_the_second_confounder(self) -> None:
        arms = [
            Arm("with_env", {"model": "opus", "env": "full"}, outcome="1"),
            Arm("without", {"model": "haiku"}, outcome="2"),
        ]
        report = compare_arms(arms)
        assert verdict_for(report, "with_env", "without") is Verdict.CONFOUNDED


class TestRejectedInput:
    def test_duplicate_labels_are_refused(self) -> None:
        arms = [Arm("a", {"m": "1"}, outcome="x"), Arm("a", {"m": "2"}, outcome="y")]
        with pytest.raises(ValueError, match="duplicate"):
            compare_arms(arms)

    def test_fewer_than_two_arms_is_refused(self) -> None:
        with pytest.raises(ValueError, match="two"):
            compare_arms([Arm("a", {"m": "1"}, outcome="x")])


class TestNumericTolerance:
    """A dimension that moved by a rounding error is not a second treatment. But saying so is a
    JUDGEMENT, so it has to be declared by the caller and visible in the report - never a default
    that quietly widens what counts as the same arm."""

    def test_a_declared_tolerance_makes_a_one_unit_gap_the_same_value(self) -> None:
        """The real opus/fable arms: 23556 against 23557, one token apart."""
        arms = [
            Arm("opus", {"model": "opus", "tokens": "23556"}, outcome="0"),
            Arm("fable", {"model": "fable", "tokens": "23557"}, outcome="0"),
        ]
        report = compare_arms(arms, tolerances={"tokens": "1"})
        assert verdict_for(report, "opus", "fable") is Verdict.CLEAN
        assert differing_for(report, "opus", "fable") == ("model",)

    def test_without_the_tolerance_the_same_pair_is_confounded(self) -> None:
        """Proves the tolerance is doing the work, and that the DEFAULT is strict."""
        arms = [
            Arm("opus", {"model": "opus", "tokens": "23556"}, outcome="0"),
            Arm("fable", {"model": "fable", "tokens": "23557"}, outcome="0"),
        ]
        report = compare_arms(arms)
        assert verdict_for(report, "opus", "fable") is Verdict.CONFOUNDED

    def test_a_tolerance_does_not_swallow_a_real_gap(self) -> None:
        arms = [
            Arm("sonnet", {"model": "sonnet", "tokens": "26854"}, outcome="0"),
            Arm("haiku", {"model": "haiku", "tokens": "20350"}, outcome="0"),
        ]
        report = compare_arms(arms, tolerances={"tokens": "1"})
        assert verdict_for(report, "sonnet", "haiku") is Verdict.CONFOUNDED

    def test_a_fractional_tolerance_is_relative_to_the_larger_value(self) -> None:
        arms = [
            Arm("a", {"model": "opus", "tokens": "23556"}, outcome="0"),
            Arm("b", {"model": "fable", "tokens": "23600"}, outcome="0"),
        ]
        assert (
            verdict_for(compare_arms(arms, tolerances={"tokens": "1%"}), "a", "b")
            is Verdict.CLEAN
        )
        assert (
            verdict_for(compare_arms(arms, tolerances={"tokens": "0.1%"}), "a", "b")
            is Verdict.CONFOUNDED
        )

    def test_the_report_echoes_the_tolerances_it_applied(self) -> None:
        """A reader must be able to see which differences were forgiven, and by how much."""
        arms = [
            Arm("a", {"tokens": "1"}, outcome="0"),
            Arm("b", {"tokens": "2"}, outcome="0"),
        ]
        report = compare_arms(arms, tolerances={"tokens": "1"})
        assert report.tolerances == {"tokens": "1"}

    def test_a_tolerance_on_a_non_numeric_dimension_is_refused(self) -> None:
        """Silently doing nothing would leave the caller believing a gap was forgiven."""
        arms = [
            Arm("a", {"model": "opus"}, outcome="0"),
            Arm("b", {"model": "fable"}, outcome="0"),
        ]
        with pytest.raises(ValueError, match="not numeric"):
            compare_arms(arms, tolerances={"model": "1"})

    def test_a_tolerance_naming_no_recorded_dimension_is_refused(self) -> None:
        """A typo in a dimension name would otherwise read as a tolerance that was applied."""
        arms = [
            Arm("a", {"tokens": "1"}, outcome="0"),
            Arm("b", {"tokens": "2"}, outcome="0"),
        ]
        with pytest.raises(ValueError, match="no arm records"):
            compare_arms(arms, tolerances={"toknes": "1"})

    def test_a_negative_tolerance_is_refused(self) -> None:
        arms = [
            Arm("a", {"tokens": "1"}, outcome="0"),
            Arm("b", {"tokens": "2"}, outcome="0"),
        ]
        with pytest.raises(ValueError, match="negative"):
            compare_arms(arms, tolerances={"tokens": "-1"})


class TestClaimingOneDimensionCausedIt:
    """The sentence this tool exists to check is always "A differs from B because of X". So the
    question is not "is anything confounded" but "does any pair ISOLATE X"."""

    def test_a_pair_isolating_the_claimed_dimension_supports_it(self) -> None:
        """Real arms, one token apart, off the same warm prefix - and only ONE read it."""
        arms = [
            Arm("opus", {"model": "opus", "tokens": "23556"}, outcome="read 23554"),
            Arm("fable", {"model": "fable", "tokens": "23557"}, outcome="read 0"),
        ]
        report = compare_arms(arms, tolerances={"tokens": "1"})
        supporting = pairs_supporting(report, "model")
        assert [(p.a, p.b) for p in supporting] == [("opus", "fable")]

    def test_a_pair_clean_on_a_DIFFERENT_dimension_does_not_support_the_claim(
        self,
    ) -> None:
        arms = [
            Arm("small", {"model": "opus", "tokens": "100"}, outcome="0"),
            Arm("large", {"model": "opus", "tokens": "900"}, outcome="1"),
        ]
        report = compare_arms(arms)
        assert pairs_supporting(report, "model") == ()

    def test_a_confounded_pair_never_supports_the_claim(self) -> None:
        """The whole failure, in one assertion: model DID move between these arms, and the pair
        still cannot carry a claim about it, because the size moved too."""
        arms = [
            Arm("sonnet_warm", {"model": "sonnet", "tokens": "26854"}, outcome="100%"),
            Arm("haiku", {"model": "haiku", "tokens": "20350"}, outcome="0%"),
        ]
        report = compare_arms(arms)
        assert pairs_supporting(report, "model") == ()

    def test_a_claim_naming_a_dimension_nobody_recorded_is_refused(self) -> None:
        arms = [
            Arm("a", {"model": "opus"}, outcome="0"),
            Arm("b", {"model": "fable"}, outcome="1"),
        ]
        report = compare_arms(arms)
        with pytest.raises(ValueError, match="no arm records"):
            pairs_supporting(report, "temperature")


class TestTheTwoRealFailuresThisToolWasBuiltFor:
    """Acceptance fixtures, not drivers: the unit tests above shaped the code. These two are the
    actual arm tables from the two times the mistake was made, kept verbatim so the tool can
    never quietly stop catching them. Both come from committed probe notes in the agentdag
    RESEARCH tree; the numbers are the measured ones, not illustrations."""

    def test_the_cross_model_cache_arms_are_confounded(self) -> None:
        """RESEARCH/workflow/design/probes/prefix-order.md, run 2. Three models read ZERO from a
        sonnet-warmed prefix, and "the cache key includes the model" was written down. But the CLI
        renders a different prompt SIZE per model, so the text differed too, and the text differing
        explains a zero read just as well."""
        arms = [
            Arm(
                "sonnet_warm",
                {"model": "sonnet", "rendered_tokens": "26854"},
                outcome="read 26852",
            ),
            Arm(
                "opus", {"model": "opus", "rendered_tokens": "21028"}, outcome="read 0"
            ),
            Arm(
                "haiku",
                {"model": "haiku", "rendered_tokens": "20350"},
                outcome="read 0",
            ),
        ]
        report = compare_arms(arms)
        assert all(pair.verdict is Verdict.CONFOUNDED for pair in report.pairs)
        assert pairs_supporting(report, "model") == ()

    def test_the_opus_fable_arm_is_the_one_that_settles_it(self) -> None:
        """Same note. opus renders 23,556 and fable 23,557 - one token apart - and fable still
        read zero off a prefix opus had just written. THAT pair holds the text fixed, so it is
        the only one the model claim may rest on."""
        arms = [
            Arm(
                "opus_again",
                {"model": "opus", "warmed_by": "opus", "rendered_tokens": "23556"},
                outcome="read 23554",
            ),
            Arm(
                "fable",
                {"model": "fable", "warmed_by": "opus", "rendered_tokens": "23557"},
                outcome="read 0",
            ),
            Arm(
                "haiku",
                {"model": "haiku", "warmed_by": "sonnet", "rendered_tokens": "22208"},
                outcome="read 0",
            ),
        ]
        report = compare_arms(arms, tolerances={"rendered_tokens": "1"})
        assert verdict_for(report, "opus_again", "fable") is Verdict.CLEAN
        assert verdict_for(report, "opus_again", "haiku") is Verdict.CONFOUNDED
        assert [(p.a, p.b) for p in pairs_supporting(report, "model")] == [
            ("opus_again", "fable")
        ]

    def test_the_usage_gap_arms_are_confounded_on_aggregation_and_unit(self) -> None:
        """RESEARCH/workflow/probes/2026-08-22-graph-a-first-live-run/FINDINGS.md, finding 4. A
        1.6x gap between a summed figure and a terminal one, explained as snapshot-versus-sum.
        Two things differed: HOW it was aggregated, and WHAT it was aggregated over - the stream
        repeats one request's usage per content block, so summing over events double counts."""
        arms = [
            Arm(
                "summed_over_events",
                {"aggregation": "sum", "unit": "assistant_event"},
                outcome="1.6x",
            ),
            Arm(
                "terminal_snapshot",
                {"aggregation": "snapshot", "unit": "message"},
                outcome="1.0x",
            ),
        ]
        report = compare_arms(arms)
        assert (
            verdict_for(report, "summed_over_events", "terminal_snapshot")
            is Verdict.CONFOUNDED
        )
        assert pairs_supporting(report, "aggregation") == ()

    def test_the_third_arm_both_refutes_the_wrong_cause_and_names_the_right_one(
        self,
    ) -> None:
        """The arm the probe went on to run: sum the DISTINCT per-request usages, keyed by
        message id. It equals the terminal figure exactly. With it in the table, aggregation is
        isolated and shows NO effect, and the unit is isolated and shows the whole 1.6x."""
        arms = [
            Arm(
                "summed_over_events",
                {"aggregation": "sum", "unit": "assistant_event"},
                outcome="1.6x",
            ),
            Arm(
                "summed_over_messages",
                {"aggregation": "sum", "unit": "message"},
                outcome="1.0x",
            ),
            Arm(
                "terminal_snapshot",
                {"aggregation": "snapshot", "unit": "message"},
                outcome="1.0x",
            ),
        ]
        report = compare_arms(arms)

        # Aggregation IS isolated by that pair, and across it the outcome does not move at all.
        # So the pair refutes the published explanation rather than supporting it.
        assert pairs_supporting(report, "aggregation") == ()
        inert = pairs_no_effect(report, "aggregation")
        assert [(p.a, p.b) for p in inert] == [
            ("summed_over_messages", "terminal_snapshot")
        ]
        assert inert[0].outcome_a == inert[0].outcome_b == "1.0x"

        unit_pairs = pairs_supporting(report, "unit")
        assert [(p.a, p.b) for p in unit_pairs] == [
            ("summed_over_events", "summed_over_messages")
        ]
        assert (unit_pairs[0].outcome_a, unit_pairs[0].outcome_b) == ("1.6x", "1.0x")


class TestParsingAnArmFromTheCommandLine:
    def test_an_arm_spec_becomes_a_label_dimensions_and_an_outcome(self) -> None:
        arm = parse_arm("opus model=opus rendered_tokens=23556 outcome=read 0")
        assert arm.label == "opus"
        assert arm.dimensions == {"model": "opus", "rendered_tokens": "23556"}
        assert arm.outcome == "read 0"

    def test_the_outcome_is_optional(self) -> None:
        assert parse_arm("opus model=opus").outcome is None

    def test_an_arm_with_no_dimensions_is_refused(self) -> None:
        """An arm that records nothing makes every pair with it UNEXPLAINED, which would read as
        a discovery rather than as an empty row."""
        with pytest.raises(ValueError, match="no dimensions"):
            parse_arm("opus")

    def test_a_dimension_without_an_equals_sign_is_refused(self) -> None:
        with pytest.raises(ValueError, match="expected key=value"):
            parse_arm("opus model opus")


class TestTheCommandLine:
    """Exit codes carry the answer, so they must not depend on the output format."""

    CROSS_MODEL: ClassVar[list[str]] = [
        "--arm",
        "sonnet model=sonnet rendered_tokens=26854 outcome=read 26852",
        "--arm",
        "opus model=opus rendered_tokens=21028 outcome=read 0",
    ]
    ONE_TOKEN_APART: ClassVar[list[str]] = [
        "--arm",
        "opus_again model=opus warmed_by=opus rendered_tokens=23556 outcome=read 23554",
        "--arm",
        "fable model=fable warmed_by=opus rendered_tokens=23557 outcome=read 0",
        "--tolerance",
        "rendered_tokens=1",
    ]

    def test_a_confounded_pair_exits_1(self) -> None:
        assert main(self.CROSS_MODEL) == 1

    def test_no_confounded_pair_exits_0(self) -> None:
        assert main(self.ONE_TOKEN_APART) == 0

    def test_an_unsupported_claim_exits_1(self) -> None:
        assert main([*self.CROSS_MODEL, "--claim", "model"]) == 1

    def test_a_supported_claim_exits_0(self) -> None:
        assert main([*self.ONE_TOKEN_APART, "--claim", "model"]) == 0

    def test_the_exit_code_is_the_same_in_json_mode(self) -> None:
        assert main([*self.CROSS_MODEL, "--claim", "model", "--json"]) == 1

    def test_a_bad_arm_spec_exits_2(self) -> None:
        assert main(["--arm", "opus", "--arm", "fable model=fable"]) == 2

    def test_one_arm_exits_2(self) -> None:
        assert main(["--arm", "opus model=opus"]) == 2

    def test_json_mode_still_emits_json_when_it_fails(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A caller parsing stdout must not get an empty string and read it as no findings."""
        assert main(["--arm", "opus", "--json"]) == 2
        payload = json.loads(capsys.readouterr().out)
        assert payload["ok"] is False
        assert payload["command"] == "confound"

    def test_the_json_envelope_names_every_pair_and_its_verdict(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert main([*self.CROSS_MODEL, "--json"]) == 1
        payload = json.loads(capsys.readouterr().out)
        assert payload["command"] == "confound"
        pairs = payload["data"]["pairs"]
        assert len(pairs) == 1
        assert pairs[0]["verdict"] == "confounded"
        assert pairs[0]["differing"] == ["model", "rendered_tokens"]

    def test_the_text_report_names_what_else_moved(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """The output has to answer the question that was asked, which is never "how many pairs"
        but "what ELSE moved between these two"."""
        main([*self.CROSS_MODEL, "--claim", "model"])
        out = capsys.readouterr().out
        assert "rendered_tokens" in out
        assert "confounded" in out.lower()


class TestACleanPairWhoseOutcomeDidNotMove:
    """Found by running the tool on the real arms: it called a pair "supporting" while BOTH arms
    measured the same thing. Isolating a dimension across two arms that came out identical is
    evidence the dimension did NOTHING - there is no difference for it to have caused. Reporting
    that as support is the vacuous-check failure the tool exists to prevent, one level up."""

    def test_an_isolated_dimension_with_an_unchanged_outcome_does_not_support_the_claim(
        self,
    ) -> None:
        arms = [
            Arm("opus", {"model": "opus"}, outcome="read 0"),
            Arm("fable", {"model": "fable"}, outcome="read 0"),
        ]
        report = compare_arms(arms)
        assert verdict_for(report, "opus", "fable") is Verdict.CLEAN
        assert pairs_supporting(report, "model") == ()

    def test_an_isolated_dimension_whose_outcome_moved_does_support_it(self) -> None:
        arms = [
            Arm("opus", {"model": "opus"}, outcome="read 23554"),
            Arm("fable", {"model": "fable"}, outcome="read 0"),
        ]
        report = compare_arms(arms)
        assert [(p.a, p.b) for p in pairs_supporting(report, "model")] == [
            ("opus", "fable")
        ]

    def test_with_no_outcomes_recorded_at_all_the_structure_is_all_there_is(
        self,
    ) -> None:
        """The caller opted out of effect-checking, so judge the arm table and say no more."""
        arms = [Arm("opus", {"model": "opus"}), Arm("fable", {"model": "fable"})]
        report = compare_arms(arms)
        assert [(p.a, p.b) for p in pairs_supporting(report, "model")] == [
            ("opus", "fable")
        ]

    def test_the_cli_says_the_dimension_had_no_effect_rather_than_staying_silent(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        rc = main(
            [
                "--arm",
                "opus model=opus outcome=read 0",
                "--arm",
                "fable model=fable outcome=read 0",
                "--claim",
                "model",
            ]
        )
        assert rc == 1
        out = capsys.readouterr().out
        assert "no effect" in out.lower()


class TestOutcomeTolerance:
    """Found in use, on a table a reader invented: two runs with IDENTICAL settings came out 19m
    and 20m, and the tool called that UNEXPLAINED. Strictly true - something unrecorded moved -
    but run-to-run variance is not a missing dimension, and a check that fires on every replicate
    pair gets ignored, which costs more than it catches. So the caller may declare what counts as
    the same reading, on the same terms as a dimension tolerance: explicit, and echoed back."""

    REPLICATES: ClassVar[list[Arm]] = [
        Arm("night2", {"compiler": "gcc13.1", "disk": "nvme0"}, outcome="19"),
        Arm("night3", {"compiler": "gcc13.1", "disk": "nvme0"}, outcome="20"),
    ]

    def test_variance_inside_the_declared_band_is_a_replicate(self) -> None:
        report = compare_arms(self.REPLICATES, outcome_tolerance="2")
        assert verdict_for(report, "night2", "night3") is Verdict.REPLICATE

    def test_without_it_the_same_pair_is_unexplained(self) -> None:
        """The default stays strict: an unexplained move is only forgiven when asked."""
        report = compare_arms(self.REPLICATES)
        assert verdict_for(report, "night2", "night3") is Verdict.UNEXPLAINED

    def test_a_real_effect_is_not_swallowed(self) -> None:
        arms = [
            Arm("slow", {"compiler": "gcc12.2"}, outcome="42"),
            Arm("fast", {"compiler": "gcc13.1"}, outcome="19"),
        ]
        report = compare_arms(arms, outcome_tolerance="2")
        assert [(p.a, p.b) for p in pairs_supporting(report, "compiler")] == [
            ("slow", "fast")
        ]

    def test_an_isolated_dimension_whose_outcome_moved_only_within_the_band_supports_nothing(
        self,
    ) -> None:
        """The band has to reach the claim check too, or the tool forgives a move for the
        replicate verdict and then rests a causal claim on that same move. It does NOT make
        the pair "no effect" though - see TestAMoveInsideTheDeclaredBand for why they differ."""
        arms = [
            Arm("gcc12", {"compiler": "gcc12.2"}, outcome="19"),
            Arm("gcc13", {"compiler": "gcc13.1"}, outcome="20"),
        ]
        report = compare_arms(arms, outcome_tolerance="2")
        assert pairs_supporting(report, "compiler") == ()
        assert [(p.a, p.b) for p in pairs_inconclusive(report, "compiler")] == [
            ("gcc12", "gcc13")
        ]

    def test_a_unit_suffix_is_read_as_a_number(self) -> None:
        arms = [
            Arm("night2", {"compiler": "gcc13.1"}, outcome="19m"),
            Arm("night3", {"compiler": "gcc13.1"}, outcome="20m"),
        ]
        assert verdict_for(
            compare_arms(arms, outcome_tolerance="2"), "night2", "night3"
        ) is (Verdict.REPLICATE)

    def test_an_outcome_tolerance_on_unreadable_outcomes_is_refused(self) -> None:
        """Silently falling back to an exact compare would leave the caller believing variance
        was accounted for while every replicate still reported UNEXPLAINED."""
        arms = [
            Arm("a", {"m": "1"}, outcome="passed"),
            Arm("b", {"m": "1"}, outcome="failed"),
        ]
        with pytest.raises(ValueError, match="not numeric"):
            compare_arms(arms, outcome_tolerance="2")

    def test_the_report_echoes_the_outcome_tolerance(self) -> None:
        report = compare_arms(self.REPLICATES, outcome_tolerance="2")
        assert report.outcome_tolerance == "2"

    def test_the_cli_takes_it_and_the_replicate_stops_being_a_finding(self) -> None:
        rc = main(
            [
                "--arm",
                "night2 compiler=gcc13.1 disk=nvme0 outcome=19",
                "--arm",
                "night3 compiler=gcc13.1 disk=nvme0 outcome=20",
                "--outcome-tolerance",
                "2",
            ]
        )
        assert rc == 0


class TestAMoveInsideTheDeclaredBand:
    """A band that silences a wobbling replicate must NOT also be able to answer a claim. An
    isolated dimension whose outcome moved, but by less than the caller called noise, is neither
    supported nor refuted - saying "no effect" there would launder a real small effect into
    evidence against a true cause, which is the failure this tool exists to stop."""

    ISOLATED_SMALL_MOVE: ClassVar[list[Arm]] = [
        Arm("gcc12", {"compiler": "gcc12.2"}, outcome="19"),
        Arm("gcc13", {"compiler": "gcc13.1"}, outcome="20"),
    ]

    def test_it_is_neither_supported_nor_no_effect(self) -> None:
        report = compare_arms(self.ISOLATED_SMALL_MOVE, outcome_tolerance="2")
        assert pairs_supporting(report, "compiler") == ()
        assert pairs_no_effect(report, "compiler") == ()
        assert [(p.a, p.b) for p in pairs_inconclusive(report, "compiler")] == [
            ("gcc12", "gcc13")
        ]

    def test_an_identical_reading_is_still_no_effect_not_inconclusive(self) -> None:
        """The two must not collapse: 'came out the same' is an answer, 'too close to call' is not."""
        arms = [
            Arm("gcc12", {"compiler": "gcc12.2"}, outcome="19"),
            Arm("gcc13", {"compiler": "gcc13.1"}, outcome="19"),
        ]
        report = compare_arms(arms, outcome_tolerance="2")
        assert [(p.a, p.b) for p in pairs_no_effect(report, "compiler")] == [
            ("gcc12", "gcc13")
        ]
        assert pairs_inconclusive(report, "compiler") == ()

    def test_a_move_beyond_the_band_still_supports(self) -> None:
        arms = [
            Arm("gcc12", {"compiler": "gcc12.2"}, outcome="19"),
            Arm("gcc13", {"compiler": "gcc13.1"}, outcome="42"),
        ]
        report = compare_arms(arms, outcome_tolerance="2")
        assert [(p.a, p.b) for p in pairs_supporting(report, "compiler")] == [
            ("gcc12", "gcc13")
        ]
        assert pairs_inconclusive(report, "compiler") == ()

    def test_with_no_band_declared_nothing_is_inconclusive(self) -> None:
        """Without a band there is no such thing as too close to call."""
        report = compare_arms(self.ISOLATED_SMALL_MOVE)
        assert pairs_inconclusive(report, "compiler") == ()
        assert [(p.a, p.b) for p in pairs_supporting(report, "compiler")] == [
            ("gcc12", "gcc13")
        ]

    def test_the_replicate_verdict_is_unaffected(self) -> None:
        """The band still does the job it was added for: a wobbling repeat is not a finding."""
        arms = [
            Arm("n2", {"compiler": "gcc13.1"}, outcome="19"),
            Arm("n3", {"compiler": "gcc13.1"}, outcome="20"),
        ]
        report = compare_arms(arms, outcome_tolerance="2")
        assert verdict_for(report, "n2", "n3") is Verdict.REPLICATE

    def test_the_cli_says_inconclusive_and_names_the_band(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        rc = main(
            [
                "--arm",
                "gcc12 compiler=gcc12.2 outcome=19",
                "--arm",
                "gcc13 compiler=gcc13.1 outcome=20",
                "--outcome-tolerance",
                "2",
                "--claim",
                "compiler",
            ]
        )
        assert rc == 3  # its own code: neither supported (0) nor refuted (1)
        out = capsys.readouterr().out
        assert "INCONCLUSIVE" in out
        assert "2" in out
        assert "no effect" not in out.lower()


class TestReadingAnOutcomeAsANumber:
    """A band needs a number, and people write measurements with units. Accepting a leading
    number is right; accepting it when a SECOND number follows is not - '0.5 to 1.2' is a range,
    and silently taking 0.5 as the reading is a wrong answer with no symptom. Refuse instead."""

    @pytest.mark.parametrize(
        "written", ["42m", "1.6x", "19 min", "250ms", "-3.5%", "0.75"]
    )
    def test_a_number_with_a_unit_is_accepted(self, written: str) -> None:
        arms = [
            Arm("a", {"m": "1"}, outcome=written),
            Arm("b", {"m": "2"}, outcome=written),
        ]
        report = compare_arms(arms, outcome_tolerance="1")
        assert verdict_for(report, "a", "b") is Verdict.CLEAN

    @pytest.mark.parametrize("written", ["0.5 to 1.2", "3.14 build 7", "1 of 2"])
    def test_a_second_number_in_the_tail_is_refused(self, written: str) -> None:
        arms = [
            Arm("a", {"m": "1"}, outcome=written),
            Arm("b", {"m": "2"}, outcome="1"),
        ]
        with pytest.raises(ValueError, match="not numeric"):
            compare_arms(arms, outcome_tolerance="1")

    def test_the_refusal_names_the_arm(self) -> None:
        arms = [
            Arm("ranged", {"m": "1"}, outcome="0.5 to 1.2"),
            Arm("b", {"m": "2"}, outcome="1"),
        ]
        with pytest.raises(ValueError, match="ranged"):
            compare_arms(arms, outcome_tolerance="1")

    def test_no_leading_number_is_still_refused(self) -> None:
        arms = [
            Arm("a", {"m": "1"}, outcome="read 0"),
            Arm("b", {"m": "2"}, outcome="read 5"),
        ]
        with pytest.raises(ValueError, match="not numeric"):
            compare_arms(arms, outcome_tolerance="1")

    def test_none_of_this_applies_without_a_band(self) -> None:
        """An outcome is free text by contract; only declaring a band asks it to be a number."""
        arms = [
            Arm("a", {"m": "1"}, outcome="0.5 to 1.2"),
            Arm("b", {"m": "2"}, outcome="read 0"),
        ]
        assert verdict_for(compare_arms(arms), "a", "b") is Verdict.CLEAN


class TestTheLiteralPairFromTheBrief:
    """The brief asked for exactly this: opus and fable, one token apart, reported CLEAN. It is
    kept as its own assertion because it pins the STRUCTURAL half - that a declared tolerance
    makes a one-token gap stop counting as a second dimension. The pair that carries the causal
    claim is the one in TestTheTwoRealFailuresThisToolWasBuiltFor; a pair can be clean without
    supporting anything, and separating the two is what these fixtures exist to hold."""

    def test_opus_and_fable_one_token_apart_are_structurally_clean(self) -> None:
        arms = [
            Arm(
                "opus", {"model": "opus", "rendered_tokens": "23556"}, outcome="read 0"
            ),
            Arm(
                "fable",
                {"model": "fable", "rendered_tokens": "23557"},
                outcome="read 0",
            ),
        ]
        report = compare_arms(arms, tolerances={"rendered_tokens": "1"})
        assert verdict_for(report, "opus", "fable") is Verdict.CLEAN
        assert differing_for(report, "opus", "fable") == ("model",)

    def test_and_without_the_tolerance_that_same_pair_is_confounded(self) -> None:
        arms = [
            Arm(
                "opus", {"model": "opus", "rendered_tokens": "23556"}, outcome="read 0"
            ),
            Arm(
                "fable",
                {"model": "fable", "rendered_tokens": "23557"},
                outcome="read 0",
            ),
        ]
        report = compare_arms(arms)
        assert verdict_for(report, "opus", "fable") is Verdict.CONFOUNDED


class TestTheRefusalMessageShowsTheOffendingText:
    """Two different problems reach the same refusal - no number at all, and more than one - and
    a message that describes only the first sends the reader looking for the wrong thing."""

    def test_it_quotes_the_value_it_could_not_read(self) -> None:
        arms = [
            Arm("ranged", {"m": "1"}, outcome="0.5 to 1.2"),
            Arm("b", {"m": "2"}, outcome="1"),
        ]
        with pytest.raises(ValueError, match=r"0\.5 to 1\.2"):
            compare_arms(arms, outcome_tolerance="1")

    def test_it_quotes_a_wordy_outcome_too(self) -> None:
        arms = [
            Arm("a", {"m": "1"}, outcome="passed"),
            Arm("b", {"m": "2"}, outcome="1"),
        ]
        with pytest.raises(ValueError, match="passed"):
            compare_arms(arms, outcome_tolerance="1")


class TestInconclusiveHasItsOwnExitCode:
    """The report distinguishes refuted from too-close-to-call; the exit code has to as well, or
    anything automated re-makes the conflation the distinction was added to end."""

    REFUTED: ClassVar[list[str]] = [
        "--arm",
        "gcc12 compiler=gcc12.2 outcome=19",
        "--arm",
        "gcc13 compiler=gcc13.1 outcome=19",
        "--claim",
        "compiler",
    ]
    TOO_CLOSE: ClassVar[list[str]] = [
        "--arm",
        "gcc12 compiler=gcc12.2 outcome=19",
        "--arm",
        "gcc13 compiler=gcc13.1 outcome=20",
        "--outcome-tolerance",
        "2",
        "--claim",
        "compiler",
    ]
    SUPPORTED: ClassVar[list[str]] = [
        "--arm",
        "gcc12 compiler=gcc12.2 outcome=19",
        "--arm",
        "gcc13 compiler=gcc13.1 outcome=42",
        "--outcome-tolerance",
        "2",
        "--claim",
        "compiler",
    ]

    def test_too_close_to_call_exits_3(self) -> None:
        assert main(self.TOO_CLOSE) == 3

    def test_refuted_still_exits_1(self) -> None:
        assert main(self.REFUTED) == 1

    def test_supported_still_exits_0(self) -> None:
        assert main(self.SUPPORTED) == 0

    def test_no_pair_isolating_the_claim_at_all_still_exits_1(self) -> None:
        """Nothing to be inconclusive ABOUT is a refusal, not a near miss."""
        rc = main(
            [
                "--arm",
                "a compiler=gcc12.2 disk=sata outcome=19",
                "--arm",
                "b compiler=gcc13.1 disk=nvme outcome=42",
                "--claim",
                "compiler",
            ]
        )
        assert rc == 1

    def test_the_exit_code_is_the_same_in_json_mode(self) -> None:
        assert main([*self.TOO_CLOSE, "--json"]) == 3

    def test_exit_3_needs_no_claim_to_be_meaningless(self) -> None:
        """With no --claim there is no claim to be inconclusive about, so 3 must never appear."""
        rc = main(
            [
                "--arm",
                "gcc12 compiler=gcc12.2 outcome=19",
                "--arm",
                "gcc13 compiler=gcc13.1 outcome=20",
                "--outcome-tolerance",
                "2",
            ]
        )
        assert rc == 0
