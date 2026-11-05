#!/usr/bin/env python3
"""The per-skill decision ledger: what a skill decided, why, and what would reopen it.

Each skill keeps one append-only JSON Lines file at `<skill>/.skillwriter/decisions.jsonl`.
An entry records one decision about the skill's text: a `rule` the text states (bound to the
text by anchors, phrases that must keep occurring in the skill's Markdown), a `removed` rule, a
`rejected` alternative, or a `void` that withdraws an entry written in error. An entry is LIVE
while no later entry names it in `supersedes`.

The commit gate (`repo-gate.py`) refuses a change whose shipped text loses a live anchor, and
the SKILL.md edit guard hands an editing agent the skill's rejected and removed entries before
its first edit. Both read this module, so it is standard library only.

Decisions:
- Anchors are compared after `normalise`: per line, leading blockquote markers are stripped,
  every whitespace-separated marker-only token (a list marker, a stray ">") is dropped, and
  whitespace collapses.
  Why: measured 2026-11-05 on 91 window commits of three skills (the plan's PREREG): re-wrapping,
  re-padding and renumbering moved no anchor, and 3 meaning changes fired. Reopen if a refusal
  log shows rewordings outnumbering meaning changes over 30 days.
- The id hashes the whole entry, so two entries written the same day in two worktrees never
  collide, and an entry edited in place no longer matches its id.
"""
import datetime
import hashlib
import json
import os
import re
import subprocess
from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path

LEDGER_REL = ".skillwriter/decisions.jsonl"
KINDS = ("rule", "removed", "rejected", "void")
TIERS = ("measured", "user", "argued", "inherited")
ORIGINS = ("authored", "imported", "baseline", "ab")
FIELDS = ("v", "id", "date", "kind", "topic", "decision", "why", "evidence", "reopen_if",
          "anchors", "supersedes", "refs", "origin")
ANCHOR_MIN, ANCHOR_MAX = 20, 200

_ID = re.compile(r"d-[0-9]{8}-[0-9a-f]{8}")
_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_TOPIC = re.compile(r"[a-z0-9][a-z0-9-]{0,39}")
_QUOTE_MARKERS = re.compile(r"^(?:>[ \t]?)+")
# No separate line-start list-marker strip: a list marker is always followed by whitespace, so it
# is a whole token that _MARKER_TOKEN already drops, and a strip of it could never change the
# result.
_MARKER_TOKEN = re.compile(r"^(?:[-*+>]+|[0-9]+[.)])$")


class LedgerError(ValueError):
    """A ledger line that is not a valid entry; `line_no` is 1-based."""

    def __init__(self, line_no: int, reason: str) -> None:
        super().__init__("line %d: %s" % (line_no, reason))
        self.line_no, self.reason = line_no, reason


def normalise(text: str) -> str:
    """One-space-separated words of `text`, without blockquote and list markers.

    Blockquote markers are stripped at line starts, where they may touch the first word
    (">word"); list markers and stray ">" are dropped as standalone tokens anywhere, on the anchor
    and the text alike: an anchor quoted across two list items carries the inner "2.", which only
    a token-level drop keeps stable under renumbering. Both sides lose the same tokens, so a match
    stays sound; prose dashes and "step 2." become invisible to it.
    """
    words = []
    for line in text.splitlines():
        line = _QUOTE_MARKERS.sub("", line.strip())
        words.extend(w for w in line.split() if not _MARKER_TOKEN.match(w))
    return " ".join(words)


def anchor_occurs(anchor: str, text: str) -> bool:
    """True when `anchor` occurs in `text` after both are normalised (case-sensitive)."""
    return normalise(anchor) in normalise(text)


def ledger_path(skill_dir: str | Path) -> Path:
    """The ledger file of the skill at `skill_dir` (it need not exist yet)."""
    return Path(skill_dir) / LEDGER_REL


def _canonical(entry: dict) -> str:
    body = {k: v for k, v in entry.items() if k != "id"}
    return json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def entry_id(entry: dict) -> str:
    """`d-<yyyymmdd>-<first 8 hex of sha256 over the entry without its id>`."""
    digest = hashlib.sha256(_canonical(entry).encode("utf-8")).hexdigest()[:8]
    return "d-%s-%s" % (str(entry.get("date", "")).replace("-", ""), digest)


def _list(entry: dict, field: str) -> list:
    # A field the list check refuses must not crash the checks that iterate it.
    value = entry.get(field)
    return value if isinstance(value, list) else []


def _text(entry: dict, field: str) -> str:
    value = entry.get(field)
    return value.strip() if isinstance(value, str) else ""


def _vocabulary_problems(entry: dict) -> list[str]:
    problems = []
    for field, allowed in (("kind", KINDS), ("origin", ORIGINS)):
        if entry.get(field) not in allowed:
            problems.append("%s: must be one of %s" % (field, ", ".join(allowed)))
    evidence = entry.get("evidence")
    if not isinstance(evidence, dict) or evidence.get("tier") not in TIERS:
        problems.append("evidence: tier must be one of %s" % ", ".join(TIERS))
    elif not _text(evidence, "text"):
        problems.append("evidence: text is empty")
    if not _TOPIC.fullmatch(str(entry.get("topic", ""))):
        problems.append("topic: lowercase letters, digits and dashes, 1 to 40 characters")
    return problems


def _list_problems(entry: dict) -> list[str]:
    problems = []
    for field in ("anchors", "supersedes", "refs"):
        value = entry.get(field)
        if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
            problems.append("%s: must be a list of strings" % field)
    supersedes = _list(entry, "supersedes")
    if any(not _ID.fullmatch(x) for x in supersedes if isinstance(x, str)):
        problems.append("supersedes: every item must be an entry id")
    if entry.get("kind") == "void" and not supersedes:
        problems.append("supersedes: a void entry names the entry it withdraws")
    return problems


def _anchor_problems(entry: dict) -> list[str]:
    anchors = _list(entry, "anchors")
    if entry.get("kind") != "rule":
        return ["anchors: only a rule entry carries anchors"] if anchors else []
    if not anchors:
        return ["anchors: a rule entry needs at least one"]
    bad = [a for a in anchors if isinstance(a, str)
           and not ANCHOR_MIN <= len(normalise(a)) <= ANCHOR_MAX]
    return ["anchors: %d to %d characters after normalising: %r" % (ANCHOR_MIN, ANCHOR_MAX, a)
            for a in bad]


def _date_problems(entry: dict) -> list[str]:
    date = str(entry.get("date", ""))
    if not _DATE.fullmatch(date):
        return ["date: YYYY-MM-DD"]
    try:
        datetime.date.fromisoformat(date)
    except ValueError:
        return ["date: not a calendar date"]
    return []


def validate_entry(entry: dict) -> list[str]:
    """Every problem with `entry`, one `<field>: <reason>` string each; [] when it is valid."""
    problems = ["%s: unknown field" % k for k in entry if k not in FIELDS]
    if entry.get("v") != 1:
        problems.append("v: must be 1")
    problems += _date_problems(entry)
    required = ("decision", "why") if entry.get("kind") == "void" else ("decision", "why", "reopen_if")
    problems += ["%s: empty" % f for f in required if not _text(entry, f)]
    problems += _vocabulary_problems(entry) + _list_problems(entry) + _anchor_problems(entry)
    if entry.get("id") != entry_id(entry):
        problems.append("id: does not match the entry (edited after it was written?)")
    return problems


# ---- reading a ledger ----
# Every reader takes the ledger as an iterable of lines, or a factory returning a fresh one for each
# pass, so a ledger is never held whole: what a pass keeps is the id sets below and the brief's
# budget, never an entry's text.

_CORPUS_SEP = "\n\x00\n"   # a NUL token: no anchor can match across two files
_CORPUS_SKIP = (".skillwriter/", "tests/")

LinesFactory = Callable[[], Iterable[str | bytes]]


def file_lines(path: str | Path) -> Iterator[str]:
    """The lines of `path`, read one at a time; nothing for a missing file."""
    path = Path(path)
    if not path.is_file():
        return
    # Iterating the file splits on newlines only; str.splitlines would also split a JSON string
    # holding a raw U+2028.
    with path.open(encoding="utf-8", newline="") as fh:
        yield from fh


def parse_entries(lines: Iterable[str | bytes]) -> Iterator[dict]:
    """Yield each entry of `lines` (str or bytes), validated; blank lines are skipped.

    Raises:
        LedgerError: at the first line that is not UTF-8, not a JSON object, or not a valid entry.
    """
    for line_no, raw in enumerate(lines, 1):
        try:
            text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
        except UnicodeDecodeError:
            raise LedgerError(line_no, "not UTF-8") from None
        if not text.strip():
            continue
        try:
            entry = json.loads(text)
        except ValueError as exc:
            raise LedgerError(line_no, "not JSON (%s)" % exc) from None
        if not isinstance(entry, dict):
            raise LedgerError(line_no, "not a JSON object")
        problems = validate_entry(entry)
        if problems:
            raise LedgerError(line_no, "; ".join(problems))
        yield entry


def live_entries(lines_factory: LinesFactory) -> Iterator[dict]:
    """Entries no later entry supersedes, voids excluded. Two passes over `lines_factory()`."""
    superseded = set()
    for entry in parse_entries(lines_factory()):
        superseded.update(entry["supersedes"])
    for entry in parse_entries(lines_factory()):
        if entry["id"] not in superseded and entry["kind"] != "void":
            yield entry


def corpus_text(files: Mapping[str, bytes]) -> str:
    """The skill's Markdown a rule anchor must occur in: `*.md` outside `.skillwriter/`, `tests/`."""
    parts = [data.decode("utf-8", errors="replace") for rel, data in sorted(files.items())
             if rel.endswith(".md") and not rel.startswith(_CORPUS_SKIP)]
    return _CORPUS_SEP.join(parts)


def _git_env() -> dict[str, str]:
    # A GIT_DIR or pathspec variable inherited from a hook would point git at another repo.
    return {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


def _tracked_files(skill_dir: Path) -> list[str] | None:
    """Paths git tracks under `skill_dir`, relative to it; None when git cannot answer."""
    try:
        out = subprocess.run(["git", "ls-files", "-z", "--", "."], cwd=str(skill_dir),
                             capture_output=True, env=_git_env(), check=False)
    except OSError:
        return None
    return os.fsdecode(out.stdout).split("\0") if out.returncode == 0 else None


def corpus_from_dir(skill_dir: str | Path) -> str:
    """`corpus_text` of the files git tracks under `skill_dir`; every file there without git."""
    skill_dir = Path(skill_dir)
    listed = _tracked_files(skill_dir)
    if listed is None:
        listed = [p.relative_to(skill_dir).as_posix() for p in skill_dir.rglob("*") if p.is_file()]
    files = {}
    for rel in filter(None, listed):
        try:
            files[rel] = (skill_dir / rel).read_bytes()
        except OSError:
            continue        # listed but gone from disk: a deletion this corpus does not hold
    return corpus_text(files)


@dataclass(frozen=True)
class Finding:
    """One problem `check_ledger` found; an anchor finding carries the entry's reasons."""

    entry_id: str
    problem: str
    anchor: str = ""
    decision: str = ""
    why: str = ""
    reopen_if: str = ""

    def render(self) -> str:
        if not self.anchor:
            return "%s: %s" % (self.entry_id or "ledger", self.problem)
        return ("%s: %s %r\n  decision: %s\n  why: %s\n  reopen if: %s"
                % (self.entry_id, self.problem, self.anchor, self.decision, self.why, self.reopen_if))


def _integrity_findings(lines_factory: LinesFactory) -> list[Finding]:
    findings, seen = [], set()
    for entry in parse_entries(lines_factory()):
        if entry["id"] in seen:
            findings.append(Finding(entry["id"], "duplicate id"))
        unknown = [s for s in entry["supersedes"] if s not in seen]
        if unknown:
            findings.append(Finding(entry["id"], "supersedes unknown or later id %s" % ", ".join(unknown)))
        seen.add(entry["id"])
    return findings


def check_ledger(lines_factory: LinesFactory, corpus: str) -> list[Finding]:
    """Findings for a ledger against its skill's text: integrity first, then every live anchor."""
    try:
        findings = _integrity_findings(lines_factory)
        text = normalise(corpus)
        for entry in live_entries(lines_factory):
            for anchor in entry["anchors"]:
                if normalise(anchor) not in text:
                    findings.append(Finding(entry["id"], "anchor no longer in the skill text:", anchor,
                                            entry["decision"], entry["why"], entry["reopen_if"]))
    except LedgerError as exc:
        return [Finding("", str(exc))]
    return findings


def _brief_block(entry: dict) -> str:
    return ("- [%s] %s (%s, %s)\n  why: %s\n  reopen if: %s"
            % (entry["kind"], entry["decision"], entry["id"], entry["evidence"]["tier"],
               entry["why"], entry["reopen_if"]))


def render_brief(lines_factory: LinesFactory, *, skill: str, budget_chars: int = 6000) -> str:
    """The live rejected and removed entries, in full until `budget_chars` is spent, then a count."""
    blocks, used, left = [], 0, 0
    for entry in live_entries(lines_factory):
        if entry["kind"] not in ("rejected", "removed"):
            continue
        block = _brief_block(entry)
        if used + len(block) > budget_chars:
            left += 1
            continue
        blocks.append(block)
        used += len(block)
    if not blocks and not left:
        return ""
    text = "Decisions already taken for %s (rejected or removed, oldest first):\n" % skill + "\n".join(blocks)
    if left:
        text += ("\n%d more not shown: python3 <plugin>/hooks/skill_decisions.py show %s "
                 "--kind rejected,removed --full" % (left, skill))
    return text
