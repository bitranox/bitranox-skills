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

WHAT THE CORPUS HAS TO BE. Leak 1 is about what the agent ALREADY HAS, so the corpus has to be
the agent's own always-loaded context or it is checking the wrong thing. `--corpus-cascade DIR`
assembles that: every CLAUDE.md and CLAUDE.local.md from DIR up to the filesystem root, plus every
memory fact body under a `.claude-memory/facts/` on that chain. It walks the filesystem directly -
never a search tool - because project CLAUDE.md files and memory stores are routinely gitignored,
and every gitignore-aware search drops them silently, leaving a small, falsely clean corpus.

HOW MUCH A VERDICT IS WORTH. The two directions are not symmetric, and the tool says which one it
is giving you:
  * INHERITED is STRONG. The lesson is demonstrably sitting in reachable context, and the report
    names the file it is in.
  * CLEAN is WEAK. This compares distinctive terms, so it cannot see a paraphrase. "No hit" means
    NOT CAUGHT, never "absent from the agent's context" - a clean run is not a sealed fixture.
A corpus of zero documents makes every scenario look clean, so asking for one and getting nothing
is a distinct outcome (`unchecked`, exit 3), never a quiet pass. EITHER flag arms it: naming a
directory is the caller promising a corpus, whether through `--corpus-cascade` or `--corpus`.
Passing neither flag promises nothing and stays exit 0.

Run:
  `uv run scripts/redcheck.py --scenario scenario.txt --corpus-cascade . --json`
  `uv run scripts/redcheck.py --scenario scenario.txt --corpus docs/ --json`
  `uv run scripts/redcheck.py --scenario scenario.txt --answer conclusion.txt --corpus docs/`

Exit codes: 0 = clean (neither leak found - this does NOT prove the RED can fail, only that
these two specific reasons it might not have been ruled out), 1 = a leak was found, 2 =
usage/IO error, 3 = unchecked (a corpus flag was given and assembled nothing, so the
inherited-coverage check never ran; passing no corpus flag at all stays 0). `--json` emits the
machine-readable envelope.

Installed plugin/marketplace skills are deliberately NOT assembled: their on-disk location is a
function of the reader's plugin cache and installed versions, so any built-in path would be a
guess that reports a falsely clean corpus on someone else's machine. Point `--corpus` at them
explicitly when you know where they live.
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

__all__ = [
    "audit",
    "Audit",
    "InheritedHit",
    "AnswerLeak",
    "Telegraph",
    "distinctive_terms",
    "cascade_chain",
    "load_cascade_corpus",
    "load_corpus",
]

# Format-independent, so a caller can branch on the result without parsing text.
EXIT_CLEAN, EXIT_LEAK, EXIT_ERROR, EXIT_UNCHECKED = 0, 1, 2, 3

# The always-loaded context files an agent inherits from the directory it is dispatched in.
CASCADE_FILENAMES = ("CLAUDE.md", "CLAUDE.local.md")
MEMORY_STORE_DIRNAME = ".claude-memory"
MEMORY_FACTS_SUBDIR = "facts"

# Said on every run, both directions, because the asymmetry is the whole point: the hit proves
# something and the miss does not, and a reader who is told only "clean" will take it for proof.
INHERITED_STRONG_NOTE = (
    "STRONG - the named document already contains this lesson, so an agent that can reach it "
    "answers from there, not from your scenario. Move the RED to a domain the corpus does not "
    "teach, or replace the behavioural arm with a text check of the artifact."
)
INHERITED_WEAK_NOTE = (
    "WEAK - a clean result means NOT CAUGHT, not absent. This compares distinctive terms, so it "
    "cannot see a paraphrase: the lesson may still sit in the agent's context in other words. "
    "Do not read a clean run as a sealed fixture."
)

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
# The right cutoff depends on the shape of the corpus, and an assembled cascade has a specific
# one: a few hundred documents from a single author's own notes, which reuse that author's domain
# vocabulary everywhere. Measured over one such cascade, the terms that CARRY a lesson sit around
# 1-5% document frequency while true boilerplate sits an order of magnitude higher (a third of
# the corpus and up). A cutoff below the signal band filters out the evidence itself, so every
# scenario comes back clean and the check is decorative - which is worse than absent, because it
# reads as a pass. 5% lands between the two bands.
#
# Re-tune per corpus with --rarity-max-fraction, using the tests as the harness: lowering it
# should eventually make the rare-term tests fail (test_rare_terms_still_flag_in_the_same_large
# _corpus, test_a_lesson_is_still_found_when_its_vocabulary_is_common_in_the_corpus), and raising
# it should eventually make the boilerplate tests fail. Land it between those two.
RARITY_MAX_FRACTION = 0.05

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
    corpus_documents: int = 0
    corpus_empty: bool = False

    @property
    def has_leak(self) -> bool:
        """A finding the caller must act on, as opposed to a check that could not run."""
        return bool(self.inherited or self.telegraphs or self.answer_leak)

    @property
    def evidence_strength(self) -> str:
        """How much the INHERITED result is worth: a hit proves something, a miss does not."""
        return "strong" if self.inherited else "weak"

    @property
    def evidence_note(self) -> str:
        return INHERITED_STRONG_NOTE if self.inherited else INHERITED_WEAK_NOTE

    def as_dict(self) -> dict[str, object]:
        return {
            "verdict": self.verdict,
            "corpus_documents": self.corpus_documents,
            "corpus_empty": self.corpus_empty,
            # Travels with the machine-readable result, so a caller parsing JSON cannot end up
            # with a bare "clean" and no idea how far that goes.
            "inherited_evidence": {
                "strength": self.evidence_strength,
                "note": self.evidence_note,
            },
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


def _rare_terms(
    documents: Sequence[tuple[str, set[str]]],
    max_fraction: float = RARITY_MAX_FRACTION,
) -> set[str] | None:
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
    limit = max(1, int(len(documents) * max_fraction))
    return {term for term, count in frequency.items() if count <= limit}


def audit(
    scenario: str,
    *,
    answer: str | None = None,
    corpus: Iterable[tuple[str, str]] = (),
    min_shared: int = MIN_SHARED_TERMS,
    rarity_max_fraction: float = RARITY_MAX_FRACTION,
    require_corpus: bool = False,
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
        rarity_max_fraction: a term in more than this share of the corpus carries no evidence
            and is ignored. Corpus-shape dependent - see RARITY_MAX_FRACTION.
        require_corpus: the caller promised a corpus. If it turns out empty, the verdict is
            "unchecked" rather than "clean" - zero documents make EVERY scenario look clean,
            which is the one failure of this tool a reader would never notice.

    Returns:
        An Audit whose verdict is "clean" only when no leak was found and the corpus was real.
    """
    scenario_terms = distinctive_terms(scenario)

    documents = [(label, distinctive_terms(text)) for label, text in corpus]
    rare = _rare_terms(documents, rarity_max_fraction)

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

    corpus_empty = require_corpus and not documents

    reasons = []
    if corpus_empty:
        reasons.append("unchecked")
    if inherited:
        reasons.append("inherited")
    if telegraphs or answer_leak:
        reasons.append("telegraphed")
    return Audit(
        verdict="+".join(reasons) if reasons else "clean",
        inherited=inherited,
        telegraphs=telegraphs,
        answer_leak=answer_leak,
        corpus_documents=len(documents),
        corpus_empty=corpus_empty,
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


def cascade_chain(start: Path | str, *, top: Path | str | None = None) -> list[Path]:
    """`start` and every directory above it, nearest first.

    Args:
        start: the directory the agent under test would be dispatched in.
        top: highest directory to include. None walks to the filesystem root, which is what a
            real cascade does; pass it to bound the walk to a fixture tree so the result does
            not depend on whose machine it runs on.

    Raises:
        ValueError: `top` is neither `start` nor one of its ancestors, so it cannot bound
            the walk and silently walking further would be a lie.
    """
    resolved = Path(start).resolve()
    chain = [resolved, *resolved.parents]
    if top is None:
        return chain
    ceiling = Path(top).resolve()
    if ceiling not in chain:
        raise ValueError(f"cascade top {ceiling} is not {resolved} or one of its ancestors")
    return chain[: chain.index(ceiling) + 1]


def _add_document(
    path: Path,
    documents: list[tuple[str, str]],
    seen: set[Path],
    warn,
) -> None:
    """Read one document into the corpus - at most once, and never fatally.

    A file that cannot be decoded costs that file and nothing else: one stray latin-1 byte in
    one note must not take down a walk over a whole tree. The skip is reported rather than
    swallowed, because a document missing from the corpus is a hole in a "clean" verdict.
    """
    if not path.is_file():
        return
    try:
        key = path.resolve()
    except OSError:
        key = path
    if key in seen:  # overlapping start dirs share ancestors; a double read would skew rarity
        return
    seen.add(key)
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        warn(f"not valid UTF-8, skipping: {path}: {exc.reason}")
        return
    except OSError as exc:
        warn(f"unreadable, skipping: {path}: {exc}")
        return
    documents.append((str(path), text))


def load_cascade_corpus(
    starts: Iterable[Path | str],
    *,
    top: Path | str | None = None,
    warn=lambda m: None,
) -> list[tuple[str, str]]:
    """Assemble the always-loaded context an agent dispatched from each `starts` dir inherits.

    Collected per directory on the chain: `CLAUDE.md`, `CLAUDE.local.md`, and every markdown
    fact body under a `.claude-memory/facts/`. Labels are absolute paths, because the label is
    what a hit reports back and "which file already teaches this" is the actionable half.

    Enumerated by walking the filesystem and reading the paths directly - never by shelling out
    to a search tool. Project `CLAUDE.md` files, the memory pointer blocks and the fact bodies
    are all commonly gitignored, and a gitignore-aware search drops them with no warning: the
    corpus comes back small, everything looks clean, and nothing says why.
    """
    documents: list[tuple[str, str]] = []
    seen: set[Path] = set()
    for start in starts:
        directory = Path(start)
        if not directory.is_dir():
            warn(f"cascade start is not a directory, skipping: {directory}")
            continue
        for level in cascade_chain(directory, top=top):
            for name in CASCADE_FILENAMES:
                _add_document(level / name, documents, seen, warn)
            facts = level / MEMORY_STORE_DIRNAME / MEMORY_FACTS_SUBDIR
            if facts.is_dir():
                for body in sorted(facts.rglob("*.md")):
                    _add_document(body, documents, seen, warn)
    return documents


def _read(spec: str) -> str:
    if spec == "-":
        return sys.stdin.read()
    return Path(spec).read_text(encoding="utf-8")


def _render(result: Audit) -> str:
    lines: list[str] = [f"corpus: {result.corpus_documents} document(s) read"]
    if result.corpus_empty:
        lines.append("UNCHECKED - 0 documents assembled, so the inherited-coverage check")
        lines.append("  never ran. An empty corpus makes EVERY scenario look clean; fix the")
        lines.append("  start directory before reading anything here as a result.")
    if not result.has_leak and not result.corpus_empty:
        lines.append("clean - no inherited coverage, no telegraphing found.")
        lines.append("This does not prove the RED can fail; it rules out the two leaks it checks.")
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
    lines.append(f"inherited-coverage evidence: {result.evidence_note}")
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
    parser.add_argument(
        "--corpus-cascade",
        action="append",
        default=[],
        metavar="DIR",
        help=(
            "assemble the corpus from the always-loaded context an agent dispatched in DIR "
            "inherits: every CLAUDE.md and CLAUDE.local.md from DIR up to the filesystem root, "
            "plus every memory fact body under a .claude-memory/facts/ on that chain. Walks the "
            "filesystem, so gitignored files are included (most project CLAUDE.md and every "
            "memory store are gitignored, and a search tool would drop them silently). "
            "Repeatable. Assembling nothing is exit 3, not a clean pass."
        ),
    )
    parser.add_argument(
        "--corpus-cascade-top",
        metavar="DIR",
        help=(
            "stop the --corpus-cascade walk at DIR instead of the filesystem root; DIR must be "
            "the start directory or one of its ancestors. Use it to check a self-contained "
            "fixture tree without pulling in the cascade of the machine you are on."
        ),
    )
    parser.add_argument("--min-shared", type=int, default=MIN_SHARED_TERMS)
    parser.add_argument(
        "--rarity-max-fraction",
        type=float,
        default=RARITY_MAX_FRACTION,
        metavar="F",
        help=(
            "ignore a term used by more than this share of the corpus (default "
            f"{RARITY_MAX_FRACTION}). Corpus-shape dependent: raise it when a corpus reuses one "
            "vocabulary throughout and nothing ever hits, lower it when boilerplate hits."
        ),
    )
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
        cascade_requested = bool(args.corpus_cascade)
        # EITHER flag is the caller promising a corpus, so either one arms the unchecked verdict.
        # --corpus is the mistype-prone form - a path typed by hand rather than a directory walked
        # from the cwd - and without this it warned on stderr and still exited 0 verdict clean,
        # which is what a gate reads.
        corpus_requested = cascade_requested or bool(args.corpus)
        if cascade_requested:
            corpus += load_cascade_corpus(
                args.corpus_cascade,
                top=args.corpus_cascade_top,
                warn=warn,
            )
        if not corpus and cascade_requested:
            warn("the cascade assembled 0 documents: the inherited-coverage check did not run.")
        elif not corpus and corpus_requested:
            warn("the named corpus dirs assembled 0 documents: the inherited-coverage check did not run.")
        elif not corpus:
            warn("no corpus given: the inherited-coverage check did not run.")
        result = audit(
            scenario,
            answer=answer,
            corpus=corpus,
            min_shared=args.min_shared,
            rarity_max_fraction=args.rarity_max_fraction,
            require_corpus=corpus_requested,
        )
    except (OSError, ValueError) as exc:
        if args.json:
            print(json.dumps(
                {"ok": False, "command": "redcheck", "skipped": warnings, "data": None,
                 "error": str(exc)},
                indent=2,
            ))
        else:
            warn(f"redcheck: {exc}")
        return EXIT_ERROR

    if args.json:
        print(json.dumps(
            {"ok": True, "command": "redcheck", "skipped": warnings, "data": result.as_dict()},
            indent=2,
        ))
    else:
        print(_render(result))
    if result.has_leak:
        return EXIT_LEAK
    if result.corpus_empty:
        return EXIT_UNCHECKED
    return EXIT_CLEAN


if __name__ == "__main__":
    raise SystemExit(main())
