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
- Anchors are compared after `normalise`: per line, leading blockquote and list markers are
  stripped, every whitespace-separated marker-only token is dropped, and whitespace collapses.
  Why: measured 2026-11-05 on 91 window commits of three skills (the plan's PREREG): re-wrapping,
  re-padding and renumbering moved no anchor, and 3 meaning changes fired. Reopen if a refusal
  log shows rewordings outnumbering meaning changes over 30 days.
- The id hashes the whole entry, so two entries written the same day in two worktrees never
  collide, and an entry edited in place no longer matches its id.
"""
import hashlib
import json
import re
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
    supersedes = entry.get("supersedes") or []
    if any(not _ID.fullmatch(x) for x in supersedes if isinstance(x, str)):
        problems.append("supersedes: every item must be an entry id")
    if entry.get("kind") == "void" and not supersedes:
        problems.append("supersedes: a void entry names the entry it withdraws")
    return problems


def _anchor_problems(entry: dict) -> list[str]:
    anchors = entry.get("anchors") or []
    if entry.get("kind") != "rule":
        return ["anchors: only a rule entry carries anchors"] if anchors else []
    if not anchors:
        return ["anchors: a rule entry needs at least one"]
    bad = [a for a in anchors if isinstance(a, str)
           and not ANCHOR_MIN <= len(normalise(a)) <= ANCHOR_MAX]
    return ["anchors: %d to %d characters after normalising: %r" % (ANCHOR_MIN, ANCHOR_MAX, a)
            for a in bad]


def validate_entry(entry: dict) -> list[str]:
    """Every problem with `entry`, one `<field>: <reason>` string each; [] when it is valid."""
    problems = ["%s: unknown field" % k for k in entry if k not in FIELDS]
    if entry.get("v") != 1:
        problems.append("v: must be 1")
    if not _DATE.fullmatch(str(entry.get("date", ""))):
        problems.append("date: YYYY-MM-DD")
    required = ("decision", "why") if entry.get("kind") == "void" else ("decision", "why", "reopen_if")
    problems += ["%s: empty" % f for f in required if not _text(entry, f)]
    problems += _vocabulary_problems(entry) + _list_problems(entry) + _anchor_problems(entry)
    if entry.get("id") != entry_id(entry):
        problems.append("id: does not match the entry (edited after it was written?)")
    return problems
