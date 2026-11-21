"""What decision-claim-guard.py and the backlog_add bridge share: entries, added text, the marker.

Both judge a claim about the user's answers that a session writes into a file it keeps (a review
log, a backlog, a handover, a commit message), and both check it against USER-DECISIONS.jsonl,
where user-decision-log.py records every AskUserQuestion answer with each option's label and
description. This module holds the parts that must not differ between them:

- `entries` splits a log into entries (a top-level list item or heading with everything up to the
  next one, a fenced code block never starting one);
- `triggered_entries` finds the entries in which a trigger pattern touches a line the earlier text
  did not hold, so an old entry is never judged again;
- `MARKER` is the `decision-check: "<term>"` marker, `marker_terms` checks its terms against the
  entry, and `find_hits` searches every CHOSEN option (and typed answer) for a term;
- `decision_logs` finds USER-DECISIONS.jsonl at the main checkout root of a directory's repository.

Pure standard library apart from `self_improve_signals.main_checkout_root`.
"""

from __future__ import annotations

import collections
import dataclasses
import hashlib
import json
import re
from collections.abc import Iterator
from pathlib import Path

from self_improve_signals import main_checkout_root

__all__ = ["LOG_NAME", "MARKER", "TRIGGER", "Entry", "Hit", "counts", "decision_logs", "entries",
           "chosen_texts", "find_hits", "iter_records", "marker_terms", "norm",
           "triggered_entries"]

LOG_NAME = "USER-DECISIONS.jsonl"
_MIN_TERM = 3
_QUOTE_MAX = 400

_APOS = "['" + chr(0x2019) + "]"          # straight and typographic apostrophe
TRIGGER = re.compile(
    r"\bnot\s+(?:a|the)\s+user(?:" + _APOS + r"s)?\s+decision\b"
    r"|\bno\s+user\s+decision\b"
    r"|\bmy\s+own\s+wording\b"
    r"|\bnot\s+the\s+user" + _APOS + r"s\b"
    r"|\buser\s+never\s+decided\b"
    r"|\bnot\s+decided\s+by\s+the\s+user\b",
    re.IGNORECASE,
)
_LDQ, _RDQ = chr(0x201C), chr(0x201D)              # typographic double quotes
MARKER = re.compile(r"decision-check:\s*[\"" + _LDQ + r"]([^\"" + _RDQ + r"\n]*)[\"" + _RDQ + r"]",
                    re.IGNORECASE)
_ENTRY_START = re.compile(r"^(?:[-*+]\s|\d+[.)]\s|#{1,6}\s)")
_FENCE = re.compile(r"^\s*(?:```|~~~)")
_SENTENCE = re.compile(r"(?<=[.!?;])\s+")
_SPACE = re.compile(r"\s+")


@dataclasses.dataclass(frozen=True)
class Entry:
    """One log entry: its first line number (1-based) and its lines."""

    start: int
    lines: tuple[str, ...]

    @property
    def text(self) -> str:
        return "\n".join(self.lines)


@dataclasses.dataclass(frozen=True)
class Hit:
    """A chosen option of a recorded answer whose text holds a marker term."""

    term: str
    header: str
    label: str
    sentence: str


def entries(text: str) -> list[Entry]:
    """Split a log into entries at each top-level list item or heading, outside fences."""
    out, current, start, fenced = [], [], 1, False
    for number, line in enumerate(text.splitlines(), 1):
        if _FENCE.match(line):
            fenced = not fenced
        elif not fenced and _ENTRY_START.match(line) and current:
            out.append(Entry(start, tuple(current)))
            current, start = [], number
        current.append(line)
    if current:
        out.append(Entry(start, tuple(current)))
    return out


def _line_key(line: str) -> str:
    return hashlib.sha1(line.rstrip().encode("utf-8", "surrogatepass")).hexdigest()[:12]


def counts(text: str) -> collections.Counter[str]:
    """How often each line (trailing space ignored) occurs in `text`, keyed by a short hash."""
    return collections.Counter(_line_key(line) for line in text.splitlines())


def triggered_entries(text: str, before: collections.Counter[str],
                      pattern: re.Pattern[str] = TRIGGER) -> list[Entry]:
    """Entries of `text` where `pattern` touches a line `before` did not hold. PURE."""
    excess = counts(text) - before
    hit = []
    for entry in entries(text):
        added = []
        for line in entry.lines:
            key = _line_key(line)
            fresh = excess[key] > 0
            if fresh:
                excess[key] -= 1
            added.append(fresh)
        if any(added) and _pattern_on_added(entry, added, pattern):
            hit.append(entry)
    return hit


def _pattern_on_added(entry: Entry, added: list[bool], pattern: re.Pattern[str]) -> bool:
    """True when a `pattern` match overlaps an added line (a match may wrap across lines)."""
    joined, owner = "", []
    for index, line in enumerate(entry.lines):
        piece = line + " "
        joined += piece
        owner.extend([index] * len(piece))
    for match in pattern.finditer(joined):
        if any(added[owner[i]] for i in range(match.start(), max(match.start() + 1, match.end()))):
            return True
    return False


def norm(text: str) -> str:
    """`text` with whitespace runs collapsed, stripped and lowercased."""
    return _SPACE.sub(" ", text).strip().lower()


def marker_terms(entry: Entry) -> tuple[list[str], str | None]:
    """(the entry's marker terms, why they are unusable or None). No markers: ([], None)."""
    terms = MARKER.findall(entry.text)
    outside = norm(MARKER.sub(" ", entry.text))
    for term in terms:
        if len(term.strip()) < _MIN_TERM:
            return terms, "the term %r is shorter than %d characters" % (term, _MIN_TERM)
        if norm(term) not in outside:
            return terms, "the term %r does not occur in the entry outside the marker" % term
    return terms, None


def chosen_texts(record: dict) -> list[tuple[str, str, str]]:
    """(header, label, text) for each piece of a record the user chose or typed."""
    header = str(record.get("header") or record.get("question") or "")
    chosen = record.get("chosen")
    options = record.get("chosen_options")
    if not isinstance(options, list):
        options = [o for o in record.get("options") or []
                   if isinstance(o, dict) and o.get("label") == chosen]
    out = []
    for option in options:
        if isinstance(option, dict):
            label = str(option.get("label") or "")
            out.append((header, label, label))
            out.append((header, label, str(option.get("description") or "")))
    if not out and isinstance(chosen, str):
        out.append((header, chosen[:80], chosen))          # free text or a plan-rejection remark
    annotation = record.get("annotation")
    notes = annotation.get("notes") if isinstance(annotation, dict) else None
    if isinstance(notes, str) and notes:
        out.append((header, "notes", notes))
    return out


def iter_records(logs: list[Path]) -> Iterator[dict]:
    """Every JSON object line of each log, one at a time; unreadable lines and files are skipped."""
    for log in logs:
        try:
            with open(log, encoding="utf-8", errors="replace") as handle:
                for raw in handle:
                    try:
                        record = json.loads(raw)
                    except ValueError:
                        continue
                    if isinstance(record, dict):
                        yield record
        except OSError:
            continue


def find_hits(term: str, logs: list[Path]) -> list[Hit]:
    """Every chosen option (or typed answer) in `logs` whose text holds `term`."""
    want, hits = norm(term), []
    for record in iter_records(logs):
        for header, label, text in chosen_texts(record):
            if want not in norm(text):
                continue
            sentence = next((s for s in _SENTENCE.split(text) if want in norm(s)), text)
            hits.append(Hit(term, header, label, sentence.strip()[:_QUOTE_MAX]))
    return hits


def decision_logs(*dirs: Path | None) -> list[Path]:
    """USER-DECISIONS.jsonl at the main checkout root of each dir's repository, existing, unique."""
    out = []
    for directory in dirs:
        if directory is None or not directory.is_dir():
            continue
        root = main_checkout_root(directory)
        log = root / LOG_NAME if root is not None else None
        if log is not None and log.is_file() and log not in out:
            out.append(log)
    return out
