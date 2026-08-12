# /// script
# requires-python = ">=3.10"
# ///
"""Will this RED/baseline scenario actually be ABLE to fail, or does it only look like it did?

A RED that cannot fail proves nothing, and it looks exactly like a good result: it fails, for the
wrong reason, and nothing about the transcript says so. Two leaks cause this, and neither is
visible from reading the scenario prompt alone:

1. INHERITED COVERAGE. An agent under test is handed everything it starts with - an ancestor
   config cascade, shipped reference material - before it ever sees your scenario. If the lesson
   the RED is meant to test is already written down there, the agent answers from that, not from
   your scenario, and the RED passes whatever the scenario says. Hermetic paths inside the
   scenario do not seal the agent against knowledge it starts with.
2. TELEGRAPHING. The scenario names the trap, pre-diagnoses the cause, or frames the decision as
   suspicious, so the prompt hands over its own answer.

Fixing one leak does not fix the other: a scenario can be moved to a domain nothing already
teaches and still telegraph the answer in its own prose, or stay perfectly quiet and still sit on
top of a lesson the agent already knows.

Stdlib only on purpose: the whole job is set arithmetic over tokens, and a tool used to decide
whether to trust a test should not itself depend on a resolver.

Run:
  `uv run scripts/redcheck.py --scenario scenario.txt --corpus docs/ --json`
  `uv run scripts/redcheck.py --scenario scenario.txt --answer conclusion.txt --corpus docs/`

Exit codes: 0 = clean (neither leak found - this does NOT prove the RED can fail, only that
these two specific reasons it might not have been ruled out), 1 = a leak was found, 2 =
usage/IO error. `--json` emits the machine-readable envelope.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Sequence

__all__ = ["audit", "Audit", "InheritedHit", "AnswerLeak", "Telegraph", "distinctive_terms"]

# Shared distinctive terms needed before a corpus document counts as prior coverage.
# 4 separates the shipped true-coverage fixture (8 shared terms) from its near-miss and
# unrelated controls (0 and 1) - see test_flags_a_scenario_the_corpus_already_teaches and
# test_near_miss_shares_terms_but_stays_below_the_threshold.
MIN_SHARED_TERMS = 4

# A term carries no evidence if much of the corpus uses it. Ordinary words otherwise accumulate to
# the absolute threshold on their own: the boilerplate fixture below ("failing", "lead",
# "reconciliation", "region", "window") collides at 33% shared terms against a scenario that
# reuses none of the corpus document's actual lesson - see
# test_common_words_over_a_large_corpus_do_not_flag.
#
# The right cutoff depends on the shape of the corpus this actually runs against (a few hundred
# skill/doc files behaves differently from a handful), so 1% is a starting floor, not a measured
# constant - re-tune it against whatever --corpus is passed, using the near-miss/rarity tests
# below as the harness: lowering the fraction should eventually make the rare-term test fail
# (test_rare_terms_still_flag_in_the_same_large_corpus), and raising it should eventually make the
# boilerplate test fail. Land the threshold between those two.
RARITY_MAX_FRACTION = 0.01

# Below this many documents the frequency estimate is noise (in a 2-document corpus every term
# looks common), so the rarity filter is skipped and the count stands alone.
MIN_CORPUS_FOR_RARITY = 20

# Fraction of the ANSWER's distinctive terms already present in the scenario.
ANSWER_LEAK_THRESHOLD = 0.5

_WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_-]{2,}|--?[A-Za-z][A-Za-z0-9-]+|/[A-Z]{2,}")

# Prose that hands over the answer. Each pattern matches a phrase that has, on its own,
# been enough to make a scenario carry its own conclusion.
_TELEGRAPH_MARKERS: tuple[tuple[str, str], ...] = (
    ("exactly", r"\b(that is|thats|which is) exactly\b|\bexactly the (thing|problem|issue|trap)\b"),
    ("the-trap", r"\bthe (trap|catch|gotcha) (here|is)\b"),
    ("as-we-know", r"\bas (we|you) (know|saw|found)\b|\bwe already know\b"),
    ("bit-us", r"\b(bit|burned|caught) (us|you|me)\b"),
    ("notorious", r"\b(notoriously|famously|well[- ]known to)\b"),
    ("beware", r"\b(beware|careful|watch out)\b"),
    ("root-caused", r"\bthe root cause is\b|\balready root[- ]caused\b"),
    ("which-is-why", r"\bwhich is why\b"),
    ("same-as", r"\b(this|it) is the same (as|thing|failure|bug)\b"),
    ("does-not-actually", r"\b(does|do|did) not actually\b"),
)

_STOP = frozenset(
    """
    the and for that with this from what next you your run ran runs job jobs was were
    are is be been being has have had will would can could should may might must
    not but out its it's they them their there then than when where which who whom
    how why all any both each few more most other some such only own same too very
    just now here also into onto over under about after before again once during
    while because since until against between through above below off out up down
    one two three four five six seven eight nine ten first second third last
    file files line lines text case cases test tests thing things way ways time times
    make made makes take takes taken get gets got give gives given see saw seen
    say says said use uses used using need needs needed want wants wanted
    left right open close start started stop stopped finish finished
    minute minutes hour hours day days week weeks
    """.split()
)


@dataclass(frozen=True)
class InheritedHit:
    """A corpus document that already teaches the scenario's lesson."""

    label: str
    shared: tuple[str, ...]
    score: float


@dataclass(frozen=True)
class AnswerLeak:
    """The scenario already contains the answer's distinctive terms."""

    overlap: float
    shared: tuple[str, ...]


@dataclass(frozen=True)
class Telegraph:
    """Prose that hands the reader the conclusion."""

    marker: str
    text: str


@dataclass
class Audit:
    verdict: str
    inherited: list[InheritedHit] = field(default_factory=list)
    telegraphs: list[Telegraph] = field(default_factory=list)
    answer_leak: AnswerLeak | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "verdict": self.verdict,
            "inherited": [
                {"label": h.label, "shared": list(h.shared), "score": round(h.score, 3)}
                for h in self.inherited
            ],
            "telegraphs": [{"marker": t.marker, "text": t.text} for t in self.telegraphs],
            "answer_leak": (
                None
                if self.answer_leak is None
                else {
                    "overlap": round(self.answer_leak.overlap, 3),
                    "shared": list(self.answer_leak.shared),
                }
            ),
        }


def distinctive_terms(text: str) -> set[str]:
    """Content-bearing tokens: lowercase words, flags and switch-like tokens."""
    terms: set[str] = set()
    for raw in _WORD.findall(text):
        token = raw.lower().strip("-")
        if not token or token in _STOP:
            continue
        if len(token) < 4 and not raw.startswith(("-", "/")):
            continue
        terms.add(token)
    return terms


def _rare_terms(documents: Sequence[tuple[str, set[str]]]) -> set[str] | None:
    """Terms used by only a small share of the corpus, or None if it is too small.

    A term most documents contain is boilerplate, and boilerplate alone reaches the
    absolute threshold once a corpus is large. Returning None means "do not filter":
    with a handful of documents the document-frequency estimate says nothing.
    """
    if len(documents) < MIN_CORPUS_FOR_RARITY:
        return None
    frequency: Counter[str] = Counter()
    for _, terms in documents:
        frequency.update(terms)
    limit = max(1, int(len(documents) * RARITY_MAX_FRACTION))
    return {term for term, count in frequency.items() if count <= limit}


def audit(
    scenario: str,
    *,
    answer: str | None = None,
    corpus: Iterable[tuple[str, str]] = (),
    min_shared: int = MIN_SHARED_TERMS,
) -> Audit:
    """Report every reason this RED scenario might be unable to fail.

    Args:
        scenario: the prompt you intend to hand the baseline agent.
        answer: the conclusion the RED is supposed to fail to reach, if known.
        corpus: (label, text) pairs the agent already has - e.g. the config cascade and
            the shipped reference material it starts a session with. Injected rather
            than discovered, so the core is testable and the caller decides what the
            agent can actually see.
        min_shared: distinct shared terms before a document counts as coverage.

    Returns:
        An Audit whose verdict is "clean" only when no leak was found.
    """
    scenario_terms = distinctive_terms(scenario)

    documents = [(label, distinctive_terms(text)) for label, text in corpus]
    rare = _rare_terms(documents)

    inherited: list[InheritedHit] = []
    for label, terms in documents:
        shared = scenario_terms & terms
        if rare is not None:
            shared &= rare
        if len(shared) >= min_shared:
            score = len(shared) / max(len(scenario_terms), 1)
            inherited.append(InheritedHit(label, tuple(sorted(shared)), score))
    inherited.sort(key=lambda h: h.score, reverse=True)

    telegraphs = [
        Telegraph(name, match.group(0))
        for name, pattern in _TELEGRAPH_MARKERS
        for match in [re.search(pattern, scenario, re.I)]
        if match
    ]

    answer_leak = None
    if answer:
        answer_terms = distinctive_terms(answer)
        if answer_terms:
            shared = scenario_terms & answer_terms
            overlap = len(shared) / len(answer_terms)
            if overlap >= ANSWER_LEAK_THRESHOLD:
                answer_leak = AnswerLeak(overlap, tuple(sorted(shared)))

    reasons = []
    if inherited:
        reasons.append("inherited")
    if telegraphs or answer_leak:
        reasons.append("telegraphed")
    return Audit(
        verdict="+".join(reasons) if reasons else "clean",
        inherited=inherited,
        telegraphs=telegraphs,
        answer_leak=answer_leak,
    )


def load_corpus(dirs: Sequence[Path], *, warn=lambda m: None) -> list[tuple[str, str]]:
    """Read every markdown document under each directory."""
    out: list[tuple[str, str]] = []
    for d in dirs:
        if not d.is_dir():
            warn(f"corpus directory not found, skipping: {d}")
            continue
        for path in sorted(d.rglob("*.md")):
            try:
                out.append((str(path), path.read_text(encoding="utf-8", errors="replace")))
            except OSError as exc:
                warn(f"unreadable, skipping: {path}: {exc}")
    return out


def _read(spec: str) -> str:
    if spec == "-":
        return sys.stdin.read()
    return Path(spec).read_text(encoding="utf-8")


def _render(result: Audit) -> str:
    lines: list[str] = []
    if result.verdict == "clean":
        lines.append("clean - no inherited coverage, no telegraphing found.")
        lines.append("This does not prove the RED can fail; it rules out the two leaks it checks.")
        return "\n".join(lines)
    if result.inherited:
        lines.append("INHERITED COVERAGE - the agent is handed this lesson before your prompt:")
        for hit in result.inherited[:10]:
            lines.append(f"  {hit.label}  ({len(hit.shared)} shared terms, {hit.score:.0%})")
            lines.append(f"    {', '.join(hit.shared[:12])}")
        lines.append("  -> move the RED to a domain the corpus does not already teach.")
    if result.telegraphs:
        lines.append("TELEGRAPHED PROSE - the scenario carries its own answer:")
        for t in result.telegraphs:
            lines.append(f"  [{t.marker}] {t.text!r}")
    if result.answer_leak:
        leak = result.answer_leak
        lines.append(f"ANSWER LEAK - {leak.overlap:.0%} of the answer's terms are in the scenario:")
        lines.append(f"  {', '.join(leak.shared[:12])}")
    if result.telegraphs or result.answer_leak:
        lines.append("  -> present the wrong action as the routine, already-reviewed next step.")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="redcheck",
        description="Check whether a RED/baseline scenario is able to fail at all.",
    )
    parser.add_argument("--scenario", required=True, help="path to the scenario, or - for stdin")
    parser.add_argument("--answer", help="path to the conclusion the RED must not contain")
    parser.add_argument(
        "--corpus",
        action="append",
        default=[],
        metavar="DIR",
        help="a directory of docs the agent already has (repeatable)",
    )
    parser.add_argument("--min-shared", type=int, default=MIN_SHARED_TERMS)
    parser.add_argument("--json", action="store_true", help="emit a JSON envelope")
    args = parser.parse_args(argv)

    warnings: list[str] = []

    def warn(message: str) -> None:
        # Always to stderr, --json included, so stdout stays a clean parseable envelope.
        warnings.append(message)
        print(message, file=sys.stderr)

    try:
        scenario = _read(args.scenario)
        answer = _read(args.answer) if args.answer else None
        corpus = load_corpus([Path(d) for d in args.corpus], warn=warn)
        if not corpus:
            warn("no corpus given: the inherited-coverage check did not run.")
        result = audit(scenario, answer=answer, corpus=corpus, min_shared=args.min_shared)
    except (OSError, ValueError) as exc:
        if args.json:
            print(json.dumps(
                {"ok": False, "command": "redcheck", "skipped": warnings, "data": None,
                 "error": str(exc)},
                indent=2,
            ))
        else:
            warn(f"redcheck: {exc}")
        return 2

    if args.json:
        print(json.dumps(
            {"ok": True, "command": "redcheck", "skipped": warnings, "data": result.as_dict()},
            indent=2,
        ))
    else:
        print(_render(result))
    return 0 if result.verdict == "clean" else 1


if __name__ == "__main__":
    raise SystemExit(main())
