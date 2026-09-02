# /// script
# requires-python = ">=3.10"
# ///
"""Can I say A caused this, or did something ELSE move between those two arms as well?

You measured some arms, one number came out different, and you are about to write "arm A differs
from arm B because of X". This checks whether that sentence is supported: it takes the arms, the
dimensions you varied, and what came out, and reports which pairwise comparisons are CONFOUNDED -
more than one dimension moved between them, so no claim about any single one is supported. Only a
pair where exactly ONE dimension moved, AND the outcome moved with it, can carry the explanation.

Built after making the mistake twice in one project, both times with a real measurement, a working
control and a green gate behind it. The number was right; the causal sentence was not supported by
it, and nothing in the transcript said so.

  1. Three models read ZERO from a prefix a fourth had warmed, and "the prompt cache key includes
     the model" was written down. But the CLI renders a different prompt SIZE per model, so the
     TEXT differed between those arms too, and differing text explains a zero read just as well.
     It took a controlled pair (two rows rendering one token apart) to settle it.
  2. A 1.6x gap between a summed usage figure and a terminal one, explained as snapshot-versus-sum.
     Two things differed: HOW it was aggregated, and WHAT it was aggregated over. It was the
     second one - the stream repeats a request's usage per content block, so summing over events
     double counts. Summing over messages instead matches the terminal figure exactly.

Two rules it applies that are easy to skip by hand:

  A dimension recorded on one arm and ABSENT on the other DIFFERS. Reading an absence as agreement
  is how a second moving dimension stays invisible.

  An isolated dimension whose OUTCOME did not move supports nothing. Two arms that came out
  identical have no difference for anything to have caused, so that pair is evidence the dimension
  did nothing - which is a useful answer, and never support for a claim.

A numeric dimension that moved by a rounding error is not a second treatment, and run-to-run
variance is not a missing dimension - but saying either is a JUDGEMENT, so both are declared
(--tolerance for a dimension, --outcome-tolerance for the reading) and the report echoes what was
forgiven, so a reader sees the call that was made. Neither has a default.

An outcome band silences a wobbling replicate; it never answers a claim. A pair that isolates the
claimed dimension and whose outcome moved by LESS than the band comes back INCONCLUSIVE - neither
supported nor refuted - because calling that "no effect" would turn your own noise estimate into
evidence against a true cause. Tighten the band, or measure again. The band needs a number, so an
outcome is read leniently (42m, 1.6x, 250ms) but REFUSED when a second number follows it: "0.5 to
1.2" is a range, and quietly taking 0.5 as the reading is the sort of wrong answer with no symptom
that this tool exists to stop.

KNOWN LIMIT, and it is the honest one: this only sees confounds among the dimensions you thought
to RECORD. It is a floor, never a proof. The one check that can see past your own table is the
UNEXPLAINED verdict - nothing you wrote down moved and the outcome moved anyway, so something you
did not write down did. Without --outcome-tolerance that verdict fires on any repeated measurement
that wobbled, so declare the band you consider noise and it reports those pairs as REPLICATE.

Run: uv run scripts/confound.py --claim model --tolerance rendered_tokens=1 \
       --arm 'opus model=opus warmed_by=opus rendered_tokens=23556 outcome=read 23554' \
       --arm 'fable model=fable warmed_by=opus rendered_tokens=23557 outcome=read 0'
Exit 0 = the claim is supported (or, with no --claim, no pair is confounded);
     1 = REFUTED - a confounded or unexplained pair exists, or the claimed dimension is isolated
         and the outcome did not move, or no pair isolates it at all;
     2 = usage error;
     3 = INCONCLUSIVE - the claim is isolated but the outcome moved less than the declared band.
         Only reachable with --claim, because without one there is no claim to be unsure about.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from itertools import combinations

__all__ = [
    "Arm",
    "OutcomeChange",
    "Pair",
    "Report",
    "Verdict",
    "compare_arms",
    "main",
    "pairs_inconclusive",
    "pairs_no_effect",
    "pairs_supporting",
    "parse_arm",
]

_UNSET = object()


class OutcomeChange(Enum):
    """What the OUTCOME did across a pair, which is a separate question from what the arms did."""

    MOVED = "moved"
    SAME = "same"
    WITHIN_BAND = "within_band"
    """It moved by less than the caller called noise: too close to call, not an answer."""
    UNRECORDED = "unrecorded"
    """Neither arm recorded one, so the caller opted out of effect-checking."""


class Verdict(Enum):
    """What a PAIR of arms can support."""

    CLEAN = "clean"
    """Exactly one recorded dimension differs, so a claim about that dimension is supported."""
    CONFOUNDED = "confounded"
    """Two or more differ, so no claim about any one of them is supported by this pair."""
    REPLICATE = "replicate"
    """Nothing differs and the outcome agrees: this pair measures repeatability, not a cause."""
    UNEXPLAINED = "unexplained"
    """Nothing RECORDED differs and the outcome moved anyway, so an unrecorded dimension did."""


@dataclass(frozen=True)
class Arm:
    """One measured arm: what it was, and what came out."""

    label: str
    dimensions: Mapping[str, str]
    outcome: str | None = None


@dataclass(frozen=True)
class Pair:
    a: str
    b: str
    differing: tuple[str, ...]
    verdict: Verdict
    outcome_a: str | None = None
    outcome_b: str | None = None
    outcome_change: OutcomeChange = OutcomeChange.UNRECORDED


@dataclass(frozen=True)
class Report:
    pairs: tuple[Pair, ...]
    tolerances: Mapping[str, str]
    dimensions: tuple[str, ...]
    outcome_tolerance: str | None = None


@dataclass(frozen=True)
class _Tolerance:
    """How far two readings of one dimension may sit apart and still count as the same arm."""

    amount: float
    fractional: bool

    def forgives(self, left: float, right: float) -> bool:
        gap = abs(left - right)
        if not self.fractional:
            return gap <= self.amount
        return gap <= self.amount * max(abs(left), abs(right))


def _parse_tolerance(name: str, spec: str) -> _Tolerance:
    text = spec.strip()
    fractional = text.endswith("%")
    try:
        amount = float(text[:-1] if fractional else text)
    except ValueError:
        raise ValueError(f"tolerance for {name!r} is not a number: {spec!r}") from None
    if amount < 0:
        raise ValueError(f"tolerance for {name!r} is negative: {spec!r}")
    return _Tolerance(amount / 100 if fractional else amount, fractional)


_LEADING_NUMBER = re.compile(r"^\s*([+-]?\d+(?:\.\d+)?)")


def _as_measurement(value: str) -> float | None:
    """Read an OUTCOME as a number, allowing the unit people actually write (42m, 1.6x, 19 min).

    Deliberately more lenient than `_as_number`, which serves DIMENSIONS: reading a leading digit
    out of a dimension label like `3rd_gen` would let a tolerance merge two distinct treatments.
    An outcome is free text by contract, so a leading measurement is the only sensible reading -
    but only while it is UNAMBIGUOUS: a second number in the tail makes it a range or a compound
    reading, and that is refused rather than guessed at.
    """
    text = str(value)
    match = _LEADING_NUMBER.match(text)
    if match is None:
        return None
    if any(char.isdigit() for char in text[match.end() :]):
        # A second number in the tail means this is a range or a compound reading ("0.5 to 1.2",
        # "3.14 build 7"), and taking the first one would silently compare the wrong thing. The
        # caller must say which number is the reading.
        return None
    return float(match.group(1))


def _as_number(value: str) -> float | None:
    try:
        return float(str(value).strip().replace(",", "").rstrip("%"))
    except ValueError:
        return None


def _resolve_tolerances(
    arms: Sequence[Arm], tolerances: Mapping[str, str]
) -> dict[str, _Tolerance]:
    """Parse every declared tolerance and REFUSE one that cannot do what it says.

    A tolerance on a dimension nobody records, or on one whose readings are not numbers, would
    silently forgive nothing while the caller believes a gap was accounted for - the same
    failure mode as the confound itself, one level up.
    """
    resolved: dict[str, _Tolerance] = {}
    for name, spec in tolerances.items():
        parsed = _parse_tolerance(name, spec)
        recorded = [arm for arm in arms if name in arm.dimensions]
        if not recorded:
            raise ValueError(
                f"tolerance for {name!r} applies to nothing: no arm records it"
            )
        unparsable = [
            arm.label for arm in recorded if _as_number(arm.dimensions[name]) is None
        ]
        if unparsable:
            raise ValueError(
                f"tolerance for {name!r} is not numeric on arm(s) {sorted(unparsable)}"
            )
        resolved[name] = parsed
    return resolved


def _same_value(
    name: str, left: object, right: object, tolerances: Mapping[str, _Tolerance]
) -> bool:
    if left is _UNSET or right is _UNSET:
        return False
    tolerance = tolerances.get(name)
    if tolerance is None:
        return left == right
    a, b = _as_number(str(left)), _as_number(str(right))
    if a is None or b is None:
        return left == right
    return tolerance.forgives(a, b)


def _differing_dimensions(
    a: Arm, b: Arm, tolerances: Mapping[str, _Tolerance]
) -> tuple[str, ...]:
    """Every dimension whose value is not the same on both arms.

    A dimension recorded on one arm and absent on the other DIFFERS. Reading an absence as
    agreement is precisely how a second moving dimension stays invisible.
    """
    names = set(a.dimensions) | set(b.dimensions)
    return tuple(
        sorted(
            n
            for n in names
            if not _same_value(
                n, a.dimensions.get(n, _UNSET), b.dimensions.get(n, _UNSET), tolerances
            )
        )
    )


def _classify_outcome(a: Arm, b: Arm, tolerance: _Tolerance | None) -> OutcomeChange:
    """MOVED, SAME, WITHIN_BAND or UNRECORDED.

    WITHIN_BAND exists so a declared noise band can silence a wobbling replicate WITHOUT also
    being able to answer a claim. Collapsing it into SAME would report "no effect" for a real
    effect smaller than the band, turning the caller's own noise estimate into evidence against a
    true cause - the failure this whole tool exists to stop, one level up.
    """
    if a.outcome is None and b.outcome is None:
        return OutcomeChange.UNRECORDED
    if tolerance is None:
        return OutcomeChange.SAME if a.outcome == b.outcome else OutcomeChange.MOVED
    left, right = _as_measurement(a.outcome or ""), _as_measurement(b.outcome or "")
    if (
        left is None or right is None
    ):  # pragma: no cover - _resolve_outcome_tolerance refuses these
        return OutcomeChange.SAME if a.outcome == b.outcome else OutcomeChange.MOVED
    if left == right:
        return OutcomeChange.SAME
    return (
        OutcomeChange.WITHIN_BAND
        if tolerance.forgives(left, right)
        else OutcomeChange.MOVED
    )


def _verdict(differing: tuple[str, ...], change: OutcomeChange) -> Verdict:
    if len(differing) > 1:
        return Verdict.CONFOUNDED
    if len(differing) == 1:
        return Verdict.CLEAN
    return Verdict.UNEXPLAINED if change is OutcomeChange.MOVED else Verdict.REPLICATE


def _isolates(pair: Pair, dimension: str) -> bool:
    return pair.verdict is Verdict.CLEAN and pair.differing == (dimension,)


def _isolated_with(
    report: Report, dimension: str, *changes: OutcomeChange
) -> tuple[Pair, ...]:
    return tuple(
        pair
        for pair in report.pairs
        if _isolates(pair, dimension) and pair.outcome_change in changes
    )


def pairs_no_effect(report: Report, dimension: str) -> tuple[Pair, ...]:
    """Pairs isolating `dimension` where the outcome came out the SAME: evidence it did nothing."""
    return _isolated_with(report, dimension, OutcomeChange.SAME)


def pairs_inconclusive(report: Report, dimension: str) -> tuple[Pair, ...]:
    """Pairs isolating `dimension` where the outcome moved by less than the declared band.

    Neither supported nor refuted. Tighten the band, or measure again.
    """
    return _isolated_with(report, dimension, OutcomeChange.WITHIN_BAND)


def pairs_supporting(report: Report, dimension: str) -> tuple[Pair, ...]:
    """The pairs on which a claim that `dimension` caused the difference may rest.

    Two conditions, and the second is the one that is easy to forget. `dimension` must be the ONLY
    thing that moved - a pair where it moved along with something else says nothing about it,
    however large the measured gap. And the OUTCOME must have moved too: isolating a dimension
    across two arms that came out identical is evidence it did NOTHING, not support for a claim
    that it caused something.
    """
    if dimension not in report.dimensions:
        raise ValueError(
            f"claim names {dimension!r}, but no arm records it; recorded: {list(report.dimensions)}"
        )
    return _isolated_with(
        report, dimension, OutcomeChange.MOVED, OutcomeChange.UNRECORDED
    )


def _resolve_outcome_tolerance(
    arms: Sequence[Arm], spec: str | None
) -> _Tolerance | None:
    if spec is None:
        return None
    parsed = _parse_tolerance("outcome", spec)
    unreadable = [
        (arm.label, arm.outcome)
        for arm in arms
        if arm.outcome is not None and _as_measurement(arm.outcome) is None
    ]
    if unreadable:
        shown = ", ".join(f"{label}={value!r}" for label, value in sorted(unreadable))
        raise ValueError(
            f"outcome tolerance needs ONE unambiguous number per arm; not numeric: {shown}. "
            f"A word ('passed') has no band, and a second number ('0.5 to 1.2') is a range - "
            f"say which number is the reading"
        )
    return parsed


def compare_arms(
    arms: Sequence[Arm],
    *,
    tolerances: Mapping[str, str] | None = None,
    outcome_tolerance: str | None = None,
) -> Report:
    """Classify every pairwise comparison among `arms`."""
    if len(arms) < 2:
        raise ValueError("need at least two arms to compare")
    labels = [arm.label for arm in arms]
    if len(set(labels)) != len(labels):
        raise ValueError(f"duplicate arm label in {labels}")
    declared = dict(tolerances or {})
    resolved = _resolve_tolerances(arms, declared)
    outcome_band = _resolve_outcome_tolerance(arms, outcome_tolerance)
    pairs = []
    for a, b in combinations(arms, 2):
        differing = _differing_dimensions(a, b, resolved)
        change = _classify_outcome(a, b, outcome_band)
        pairs.append(
            Pair(
                a.label,
                b.label,
                differing,
                _verdict(differing, change),
                a.outcome,
                b.outcome,
                change,
            )
        )
    recorded = sorted({name for arm in arms for name in arm.dimensions})
    return Report(tuple(pairs), declared, tuple(recorded), outcome_tolerance)


_OUTCOME_KEY = "outcome="


def parse_arm(spec: str) -> Arm:
    """Parse one `--arm` spec: `LABEL key=value key=value [outcome=REST OF LINE]`.

    `outcome=` swallows the remainder of the spec, so a measured result may carry spaces
    (`outcome=read 0 of 23556`) without needing to be quoted twice.
    """
    tokens = spec.split()
    if not tokens:
        raise ValueError("empty arm spec")
    label, rest = tokens[0], tokens[1:]
    outcome: str | None = None
    for index, token in enumerate(rest):
        if token.startswith(_OUTCOME_KEY):
            outcome = " ".join(rest[index:])[len(_OUTCOME_KEY) :]
            rest = rest[:index]
            break
    dimensions: dict[str, str] = {}
    for token in rest:
        if "=" not in token:
            raise ValueError(f"arm {label!r}: expected key=value, got {token!r}")
        key, _, value = token.partition("=")
        dimensions[key] = value
    if not dimensions:
        raise ValueError(
            f"arm {label!r} records no dimensions, so it can be compared to nothing"
        )
    return Arm(label, dimensions, outcome)


def _parse_tolerance_spec(spec: str) -> tuple[str, str]:
    if "=" not in spec:
        raise ValueError(f"expected key=value for --tolerance, got {spec!r}")
    key, _, value = spec.partition("=")
    return key, value


def _outcomes(pair: Pair) -> str:
    if pair.outcome_a is None and pair.outcome_b is None:
        return ""
    return f"  [{pair.outcome_a} -> {pair.outcome_b}]"


def _render(
    report: Report, claim: str | None, supporting: tuple[Pair, ...] | None
) -> str:
    lines = []
    applied = [f"{k}={v}" for k, v in sorted(report.tolerances.items())]
    if report.outcome_tolerance is not None:
        applied.append(f"outcome={report.outcome_tolerance}")
    if applied:
        lines.append(f"tolerances applied: {', '.join(applied)}")
        lines.append("")
    for pair in report.pairs:
        moved = ", ".join(pair.differing) or "nothing recorded"
        lines.append(f"{pair.verdict.value.upper():<12} {pair.a} vs {pair.b}")
        lines.append(f"             moved: {moved}{_outcomes(pair)}")
    if claim is None:
        return "\n".join(lines)
    lines.append("")
    if supporting:
        rested_on = ", ".join(f"{p.a} vs {p.b}" for p in supporting)
        lines.append(f"CLAIM SUPPORTED: {claim!r} is isolated by {rested_on}")
    else:
        unresolved = pairs_inconclusive(report, claim)
        inert = pairs_no_effect(report, claim)
        if unresolved:
            pairs = ", ".join(f"{p.a} vs {p.b}" for p in unresolved)
            lines.append(
                f"INCONCLUSIVE: {claim!r} is isolated by {pairs}, but the outcome moved by less "
                f"than your declared band of {report.outcome_tolerance}. Neither supported nor "
                f"refuted - tighten the band, or measure again"
            )
        elif inert:
            pairs = ", ".join(f"{p.a} vs {p.b}" for p in inert)
            lines.append(
                f"CLAIM NOT SUPPORTED: {claim!r} is isolated by {pairs}, and had NO EFFECT there "
                f"(the outcome did not move), which is evidence against it"
            )
        else:
            lines.append(f"CLAIM NOT SUPPORTED: no pair isolates {claim!r}")
        for pair in report.pairs:
            if claim in pair.differing and len(pair.differing) > 1:
                others = ", ".join(d for d in pair.differing if d != claim)
                lines.append(
                    f"  {pair.a} vs {pair.b}: {claim} moved, but so did {others}"
                )
    return "\n".join(lines)


def _fail(message: str, as_json: bool) -> int:
    if as_json:
        print(
            json.dumps(
                {
                    "ok": False,
                    "command": "confound",
                    "data": {"error": message},
                    "skipped": [],
                },
                indent=1,
            )
        )
    else:
        print(message, file=sys.stderr)
    return 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--arm",
        action="append",
        metavar="'LABEL k=v k=v outcome=...'",
        help="one measured arm; repeat. Everything after outcome= is the measured result",
    )
    parser.add_argument(
        "--tolerance",
        action="append",
        default=[],
        metavar="DIM=N[%]",
        help="how far this dimension may move and still count as the same arm (1, or 0.5%%)",
    )
    parser.add_argument(
        "--outcome-tolerance",
        metavar="N[%]",
        help="how far two outcomes may sit apart and still count as the same reading, so "
        "run-to-run variance is not reported as an unrecorded dimension",
    )
    parser.add_argument(
        "--claim",
        metavar="DIM",
        help="the dimension you want to say caused the difference; exit 1 if no pair isolates it",
    )
    parser.add_argument(
        "--json", action="store_true", help="emit a JSON envelope on stdout"
    )
    args = parser.parse_args(argv)

    try:
        arms = [parse_arm(spec) for spec in args.arm or []]
        tolerances = dict(_parse_tolerance_spec(spec) for spec in args.tolerance)
        report = compare_arms(
            arms, tolerances=tolerances, outcome_tolerance=args.outcome_tolerance
        )
        supporting = pairs_supporting(report, args.claim) if args.claim else None
    except ValueError as error:
        return _fail(str(error), args.json)

    if args.json:
        print(
            json.dumps(
                {
                    "ok": bool(supporting) if args.claim else not _has_finding(report),
                    "command": "confound",
                    "data": {
                        "claim": args.claim,
                        "tolerances": dict(report.tolerances),
                        "outcome_tolerance": report.outcome_tolerance,
                        "dimensions": list(report.dimensions),
                        "supporting": [[p.a, p.b] for p in supporting or ()],
                        "inconclusive": (
                            [[p.a, p.b] for p in pairs_inconclusive(report, args.claim)]
                            if args.claim
                            else []
                        ),
                        "pairs": [
                            {
                                "a": p.a,
                                "b": p.b,
                                "differing": list(p.differing),
                                "verdict": p.verdict.value,
                                "outcome_a": p.outcome_a,
                                "outcome_b": p.outcome_b,
                                "outcome_change": p.outcome_change.value,
                            }
                            for p in report.pairs
                        ],
                    },
                    "skipped": [],
                },
                indent=1,
            )
        )
    else:
        print(_render(report, args.claim, supporting))

    unexplained = [p for p in report.pairs if p.verdict is Verdict.UNEXPLAINED]
    if unexplained and args.claim:
        # Not the question that was asked, so it must not change the claim's exit code - but a
        # pair whose outcome moved with nothing recorded moving is a hole in the arm table
        # itself, and swallowing it would leave the caller reading a supported claim off a
        # table that is missing a dimension.
        pairs = ", ".join(f"{p.a} vs {p.b}" for p in unexplained)
        print(
            f"warning: {len(unexplained)} pair(s) moved with no recorded dimension differing "
            f"({pairs}); the arm table is missing something",
            file=sys.stderr,
        )

    if args.claim:
        if supporting:
            return 0
        # Too close to call is not the same answer as refuted, and a caller that can only read the
        # exit code would otherwise re-make exactly the conflation the INCONCLUSIVE verdict ends.
        return 3 if pairs_inconclusive(report, args.claim) else 1
    return 1 if _has_finding(report) else 0


def _has_finding(report: Report) -> bool:
    """A table is clean only if no pair is confounded AND none moved unexplained."""
    return any(
        pair.verdict in (Verdict.CONFOUNDED, Verdict.UNEXPLAINED)
        for pair in report.pairs
    )


if __name__ == "__main__":
    raise SystemExit(main())
