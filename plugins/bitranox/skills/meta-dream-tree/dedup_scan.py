# /// script
# requires-python = ">=3.10"
# ///
"""Near-duplicate CANDIDATES across a curated memory tree - with a control that proves it fired.

The dream needs this twice per run and has always hand-rolled it. The reason that keeps going
wrong is not the scoring, it is what a zero means: a scorer that silently cannot fire returns no
candidates, and so does a genuinely clean tree. The two are indistinguishable at exactly the
moment the good one is the convenient answer.

So every run plants a POSITIVE of its own - a paraphrase of a real fact from this very corpus,
scored through the same code path - and reports whether it was found. A run whose control did
not fire is an INSTRUMENT FAILURE and exits non-zero; its empty candidate list means nothing.

The SCORE DISTRIBUTION is printed for the same reason. A pair sitting at 0.49 under a 0.50
threshold is the one a reader most needs to see, and dropping it silently is how a threshold
turns into a way of not looking.

The output is CANDIDATES, never duplicates. This scores WORDS; whether two facts say the same
thing is a judgement that needs both bodies read, and the tool's job ends at naming the pair and
where each one lives. Only the words a fact SAYS are scored: the engine's frontmatter keys
(`name:`, `metadata:`, `type:`) sit on every body and would lift every pair off zero, so the frame
is stripped and only its `description:` value is kept.

A fact or level the scan could not read (a permission error, bytes that are not UTF-8) is named in
`skipped` and the run exits 2: a scan that silently dropped one reads exactly like a clean one.

Run (from the plugin root, via the launcher that forces UTF-8):
  `bash hooks/run-python.sh skills/meta-dream-tree/dedup_scan.py --from . --threshold 0.5`
  `bash hooks/run-python.sh skills/meta-dream-tree/dedup_scan.py --from . --threshold 0.4 --json`
  `bash hooks/run-python.sh skills/meta-dream-tree/dedup_scan.py --from . --top 20`

Exit codes: 0 = scanned, no candidates at or above the threshold (and the control fired),
1 = candidates to read, 2 = refused, something could not be read, or the control did NOT fire
(the run proves nothing).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

# The engine's pointer parser and anchor resolver, from the plugin's hooks dir:
# skills/<skill> -> skills -> bitranox. A private regex read loose pointer-shaped prose outside
# the managed block as facts at that level.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hooks"))
import uuid_store  # noqa: E402

# tree_support is this script's sibling; a caller loading the script by path does not put this
# dir on sys.path the way running it directly does.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from tree_support import STORE_DIR, store_anchor, utf8_stdio  # noqa: E402

__all__ = ["Fact", "Candidate", "Control", "Result", "similarity", "run", "load_facts", "main"]

FACTS_SUBDIR = "facts"
LEVEL_FILE = "CLAUDE.local.md"
WORD_RX = re.compile(r"[a-z0-9]+")
# The engine's body frame: a leading `---` line, the keys, a closing `---` line.
_FRAME_RX = re.compile(r"\A\s*---[ \t]*\r?\n(.*?)^---[ \t]*\r?$", re.DOTALL | re.MULTILINE)
_DESC_RX = re.compile(r"(?m)^description:[ \t]*(.*?)[ \t]*\r?$")
CONTROL_PREFIX = "__control__"
# The control asks "can this scorer see a paraphrase AT ALL", which is a property of the scorer
# and not of the caller's threshold. Tying it to --threshold would make raising the threshold
# report the instrument as broken, which teaches a reader to ignore the one line that matters.
CONTROL_MIN = 0.5

# Words carried by nearly every entry in a store of directives. Left in, they lift every pair's
# score toward a common floor and squeeze the gap the threshold has to sit in.
STOPWORDS = frozenset("""
a an the and or but if then than that this these those of to in on at by for with from as is are
was were be been being it its it's not no never always when while which who whom whose what how
why do does did done doing you your yours we our us they them their he she his her i me my
one two so such only just also very can could should would may might must shall will
""".split())

# A dir a curated memory tree never keeps facts in. Prefixes because a venv is named for its
# python or its project: `.venv-win`, `.venv-3.13`, `venv-<user>`, `venv_<project>`.
PRUNE_NAMES = {".git", "node_modules", "__pycache__", "target", "site-packages"}
PRUNE_PREFIXES = (".venv", "venv-", "venv_")


class DedupScanError(Exception):
    """Reported as a typed message and exit 2, never as a traceback."""


@dataclass(frozen=True)
class Fact:
    """One stored fact, with enough location to open it."""

    slug: str
    level: str
    title: str
    text: str


@dataclass(frozen=True)
class Candidate:
    """Two facts whose WORDS overlap enough to be worth reading side by side."""

    a: Fact
    b: Fact
    score: float

    def as_dict(self) -> dict:
        return {"score": round(self.score, 4),
                "a": {"slug": self.a.slug, "level": self.a.level, "title": self.a.title},
                "b": {"slug": self.b.slug, "level": self.b.level, "title": self.b.title}}


@dataclass(frozen=True)
class Control:
    """The planted positive: what it scored, and whether the run found it."""

    detected: bool
    score: float
    source_slug: str

    def as_dict(self) -> dict:
        return {"detected": self.detected, "score": round(self.score, 4),
                "planted_from": self.source_slug}


@dataclass
class Result:
    """Candidates, the control, and the distribution - none of them optional."""

    candidates: list[Candidate] = field(default_factory=list)
    control: Control = Control(False, 0.0, "")
    distribution: dict[float, int] = field(default_factory=dict)
    compared_pairs: int = 0
    facts_scanned: int = 0
    skipped: list[str] = field(default_factory=list)

    @property
    def instrument_failed(self) -> bool:
        """A run whose control did not fire proves nothing, whatever its candidate list says."""
        return not self.control.detected

    def as_dict(self) -> dict:
        return {"candidates": [c.as_dict() for c in self.candidates],
                "control": self.control.as_dict(),
                "instrument_failed": self.instrument_failed,
                "distribution": {str(k): v for k, v in sorted(self.distribution.items())},
                "compared_pairs": self.compared_pairs,
                "facts_scanned": self.facts_scanned}


def tokens(text: str) -> set[str]:
    """Content words of `text`, lowercased. PURE."""
    return {w for w in WORD_RX.findall((text or "").lower()) if w not in STOPWORDS and len(w) > 2}


def body_content(text: str) -> str:
    """What a fact SAYS: its body without the engine's frontmatter frame, keeping `description:`.

    The frame's keys (`name`, `description`, `metadata`, `type` and the type value) are the same
    on every engine-written body, so scoring them gave two facts with disjoint prose a Jaccard of
    about 0.3 - measured - and squeezed the gap a threshold has to sit in. The description value
    is kept because it is the hook, the fact's own summary. Text with no leading frame is
    returned unchanged. PURE.
    """
    text = text or ""
    m = _FRAME_RX.match(text)
    if not m:
        return text
    desc = _DESC_RX.search(m.group(1))
    return (desc.group(1) if desc else "") + "\n" + text[m.end():]


def _scored(f: Fact) -> str:
    """The text a fact is scored on: its title plus what it says."""
    return f.title + " " + body_content(f.text)


def similarity(a: str, b: str) -> float:
    """Jaccard overlap of content words: 1.0 identical, 0.0 disjoint. PURE and symmetric.

    Word-set overlap rather than sequence matching on purpose - the store's duplicates are
    re-statements in a different order, which a sequence measure scores low and a set measure
    scores high. It cannot see meaning, which is why the output is candidates. A leading engine
    frontmatter frame is stripped first (see body_content).
    """
    ta, tb = tokens(body_content(a)), tokens(body_content(b))
    if not ta and not tb:
        return 1.0
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def _paraphrase(text: str) -> str:
    """A reworded copy: most of the content words, reordered, with some dropped and some added.

    Every clause here is load-bearing, and the first version got it wrong. Merely REORDERING the
    words produces an identical word SET, so a set-based scorer returns exactly 1.0 - measured on
    the real store. A control like that proves only that the scorer is not string equality, and
    would fire on an instrument that misses every genuine near-duplicate.

    So the plant DROPS about a quarter of the content words and ADDS words the source never had.
    That lands it where real duplicates live: high overlap, well under 1.0.

    A source under eight words cannot lose a quarter and keep half: appending a fixed tail there
    scored 0.42 on a store of one-sentence facts, so EVERY run reported an instrument failure. A
    short source is instead kept whole plus ONE new word, a Jaccard of k/(k+1) - at least 0.5 for
    any source with a content word, and still under 1.0.
    """
    words = [w for w in (text or "").split() if w]
    if len(words) < 8:
        return f"{text} restated"
    kept = [w for i, w in enumerate(words) if i % 4 != 3]        # drop every fourth word
    head, tail = kept[: len(kept) // 2], kept[len(kept) // 2:]
    return " ".join(tail + ["moreover", "restated", "differently", "herein"] + head)


def _plant_control(facts: list[Fact]) -> tuple[list[Fact], Fact, Fact]:
    """Insert a paraphrase of the longest real fact, so the control runs the real code path.

    The plant paraphrases what the source SAYS (frame stripped) and keeps its title, so the only
    differences from the source are the ones `_paraphrase` makes on purpose.
    """
    source = max(facts, key=lambda f: len(body_content(f.text)))
    planted = Fact(slug=f"{CONTROL_PREFIX}{source.slug}", level=source.level,
                   title=source.title, text=_paraphrase(body_content(source.text)))
    return facts + [planted], source, planted


def _candidate_pairs(facts: list[Fact]) -> list[tuple[int, int]]:
    """Index-pairs worth scoring: those sharing at least two reasonably rare content words.

    Scoring every pair is quadratic and a real store holds ~1000 facts. The index keeps the work
    proportional to actual overlap; a token carried by more than a fifth of the corpus is
    dropped, since it separates nothing.
    """
    n = len(facts)
    if n < 2:
        return []
    postings: dict[str, list[int]] = defaultdict(list)
    for i, f in enumerate(facts):
        for tok in tokens(_scored(f)):
            postings[tok].append(i)
    # A floor of 5 as well as a fraction: on a small corpus every shared word is also carried by
    # the planted control, so a pure fraction drops exactly the tokens that link the pair the
    # scan exists to find - and the tool reports a clean tree of three facts.
    ceiling = max(5, n // 5)
    shared: dict[tuple[int, int], int] = defaultdict(int)
    for idxs in postings.values():
        if len(idxs) > ceiling:
            continue
        for x in range(len(idxs)):
            for y in range(x + 1, len(idxs)):
                shared[(idxs[x], idxs[y])] += 1
    return [pair for pair, count in shared.items() if count >= 2]


def _bucket(score: float) -> float:
    return round(int(score * 20) / 20, 2)


def run(facts: list[Fact], *, threshold: float = 0.5, scorer=similarity,
        top: int | None = None) -> Result:
    """Score the corpus, with a planted positive scored through the same path. PURE given `facts`."""
    if not facts:
        raise DedupScanError("no facts to scan - an empty corpus cannot be clean or dirty")
    corpus, source, planted = _plant_control(facts)
    candidates: list[Candidate] = []
    distribution: dict[float, int] = defaultdict(int)
    control_score = 0.0
    real_pairs = 0
    for i, j in _candidate_pairs(corpus):
        fa, fb = corpus[i], corpus[j]
        if {fa.slug, fb.slug} == {planted.slug, source.slug}:
            control_score = max(control_score, scorer(_scored(fa), _scored(fb)))
            continue
        if fa.slug.startswith(CONTROL_PREFIX) or fb.slug.startswith(CONTROL_PREFIX):
            # The plant against a third fact is not a pair anyone can merge. Counted, it put
            # phantom near-misses in the very distribution a reader is told to inspect.
            continue
        score = scorer(_scored(fa), _scored(fb))
        real_pairs += 1
        distribution[_bucket(score)] += 1
        if score >= threshold:
            candidates.append(Candidate(fa, fb, score))
    candidates.sort(key=lambda c: (-c.score, c.a.slug, c.b.slug))
    if top is not None:
        candidates = candidates[:top]
    return Result(candidates=candidates,
                  control=Control(control_score >= CONTROL_MIN, control_score, source.slug),
                  distribution=dict(distribution), compared_pairs=real_pairs,
                  facts_scanned=len(facts))


# ---- reading the tree ---------------------------------------------------------------------------

def _is_pruned(name: str) -> bool:
    return name in PRUNE_NAMES or name.startswith(PRUNE_PREFIXES)


def anchor_dir(start: Path) -> Path:
    """The tree anchor the ENGINE uses for `start` (see tree_support.store_anchor)."""
    anchor = store_anchor(start, uuid_store.resolve_anchor)
    if anchor is None:
        raise DedupScanError(f"no {STORE_DIR}/ store at the memory anchor of "
                             f"{Path(start).resolve()} (the topmost dir holding a CLAUDE.md and "
                             "a store)")
    return anchor


def _levels(anchor: Path, skipped: list[str]) -> list[Path]:
    """Every level dir under `anchor`; a directory that cannot be listed goes into `skipped`."""
    found, stack = [], [Path(anchor)]
    while stack:
        d = stack.pop()
        try:
            entries = list(d.iterdir())
        except OSError as exc:
            skipped.append(f"{d} ({type(exc).__name__})")
            continue
        for e in entries:
            if e.is_dir() and not e.is_symlink() and not _is_pruned(e.name):
                stack.append(e)
            elif e.is_file() and e.name == LEVEL_FILE:
                found.append(d)
    return sorted(found)


def _read(path: Path, skipped: list[str]) -> str | None:
    """A text file's content, or None with the reason recorded in `skipped`.

    utf-8-sig so a BOM left by a Windows editor is not read as part of the first word."""
    try:
        return path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        skipped.append(f"{path} ({type(exc).__name__})")
        return None


def load_facts(start: Path, skipped: list[str] | None = None) -> list[Fact]:
    """Every fact in the tree, each tagged with the level whose pointer block names it.

    A level, directory or fact body that cannot be read is appended to `skipped` (when given)
    and left out; the caller decides that an incomplete scan is not a clean one.
    """
    skipped = [] if skipped is None else skipped
    anchor = anchor_dir(start)
    level_of: dict[str, str] = {}
    for lvl in _levels(anchor, skipped):
        text = _read(lvl / LEVEL_FILE, skipped)
        for pointer in uuid_store.parse_pointer_index(text or "")[1]:
            if not pointer.legacy:
                level_of.setdefault(pointer.slug, str(lvl))
    out: list[Fact] = []
    for path in sorted((anchor / STORE_DIR / FACTS_SUBDIR).glob("*.md")):
        body = _read(path, skipped)
        if body is None:
            continue
        out.append(Fact(slug=path.stem, level=level_of.get(path.stem, str(anchor)),
                        title=path.stem.replace("-", " "), text=body))
    if not out:
        raise DedupScanError(f"no fact bodies under {anchor / STORE_DIR / FACTS_SUBDIR}")
    return out


# ---- CLI -----------------------------------------------------------------------------------------

def _render(result: Result, threshold: float) -> str:
    lines = [f"scanned {result.facts_scanned} fact(s), scored {result.compared_pairs} pair(s) "
             f"at threshold {threshold}"]
    ctrl = result.control
    lines.append(f"control  planted from {ctrl.source_slug}: scored {ctrl.score:.2f} - "
                 + ("FIRED" if ctrl.detected else "DID NOT FIRE, this run proves nothing"))
    lines.append("distribution (score bucket: pairs)")
    lines += [f"  {bucket:.2f}  {'#' * min(n, 40)} {n}"
              for bucket, n in sorted(result.distribution.items()) if n]
    if not result.candidates:
        lines.append("no CANDIDATES at or above the threshold")
    else:
        lines.append(f"{len(result.candidates)} CANDIDATE pair(s) - read both bodies before "
                     "merging:")
        for c in result.candidates:
            lines.append(f"  {c.score:.2f}  {c.a.slug}  ({c.a.level})")
            lines.append(f"        {c.b.slug}  ({c.b.level})")
    if result.skipped:
        lines.append(f"INCOMPLETE: {len(result.skipped)} path(s) could not be read, so this scan "
                     "proves nothing about them:")
        lines += [f"  {s}" for s in result.skipped]
    return "\n".join(lines)


def _positive_int(raw: str) -> int:
    """argparse type for --top: N < 1 would silently drop every candidate and exit 0."""
    try:
        n = int(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"not an integer: {raw!r}") from exc
    if n < 1:
        raise argparse.ArgumentTypeError(f"must be 1 or more, got {n}")
    return n


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--from", dest="start", default=".", help="a dir inside the tree")
    p.add_argument("--threshold", type=float, default=0.5,
                   help="report pairs scoring at or above this (default 0.5)")
    p.add_argument("--top", type=_positive_int, default=None,
                   help="keep only the N strongest candidates (N >= 1)")
    p.add_argument("--json", action="store_true", dest="as_json", help="emit a JSON envelope")
    return p


def main(argv: list[str] | None = None) -> int:
    utf8_stdio()
    args = build_parser().parse_args(argv)
    skipped: list[str] = []
    try:
        result = run(load_facts(Path(args.start).expanduser(), skipped),
                     threshold=args.threshold, top=args.top)
    except DedupScanError as exc:
        payload = {"ok": False, "command": "dedup_scan", "data": {"error": str(exc)},
                   "skipped": skipped}
        print(json.dumps(payload, indent=2) if args.as_json else f"error: {exc}")
        if not args.as_json:
            print(f"error: {exc}", file=sys.stderr)
        return 2
    result.skipped = sorted(skipped)
    ok = not result.instrument_failed and not result.candidates and not result.skipped
    if args.as_json:
        print(json.dumps({"ok": ok, "command": "dedup_scan", "data": result.as_dict(),
                          "skipped": result.skipped}, indent=2))
    else:
        print(_render(result, args.threshold))
    if result.instrument_failed or result.skipped:
        return 2
    return 1 if result.candidates else 0


if __name__ == "__main__":
    sys.exit(main())
