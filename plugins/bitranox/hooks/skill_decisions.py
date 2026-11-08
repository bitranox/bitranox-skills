#!/usr/bin/env python3
"""The per-skill decision ledger: what a skill decided, why, and what would reopen it.

Each skill keeps one append-only JSON Lines file at `<skill>/.skillwriter/decisions.jsonl`.
An entry records one decision about the skill's text: a `rule` the text states (bound to the
text by anchors, phrases that must keep occurring in the skill's Markdown), a `removed` rule, a
`rejected` alternative, or a `void` that withdraws an entry written in error and its effects:
what that entry superseded is live again. An entry is LIVE while no entry that is not itself
voided names it in `supersedes`.

The commit gate (`repo-gate.py`) refuses a change whose shipped text loses a live anchor, and
the SKILL.md edit guard hands an editing agent the skill's rejected and removed entries before
its first edit. Both read this module, so it is standard library only. Run as a script it is
the ledger's only writer: `add`, `show` and `check` (`--help` lists their flags).

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
import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import NoReturn

import claude_paths
import tell_chars

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
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


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
    elif set(evidence) != {"tier", "text"}:
        problems.append("evidence: exactly the fields tier and text")
    # A str check first: str(7) matches the pattern, and `show --topic 7` never matches an int.
    topic = entry.get("topic")
    if not isinstance(topic, str) or not _TOPIC.fullmatch(topic):
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
    texts = [a for a in anchors if isinstance(a, str)]
    problems = ["anchors: %d to %d characters after normalising: %r" % (ANCHOR_MIN, ANCHOR_MAX, a)
                for a in texts if not ANCHOR_MIN <= len(normalise(a)) <= ANCHOR_MAX]
    # A control character is no text a skill shows, and a NUL would let an anchor match across the
    # file separator corpus_text puts between two files.
    problems += ["anchors: contains a control character: %r" % a
                 for a in texts if _CONTROL.search(a)]
    return problems


def _date_problems(entry: dict) -> list[str]:
    date = str(entry.get("date", ""))
    if not _DATE.fullmatch(date):
        return ["date: YYYY-MM-DD"]
    try:
        datetime.date.fromisoformat(date)
    except ValueError:
        return ["date: not a calendar date"]
    return []


def _unencodable_problems(entry: dict) -> list[str]:
    """One `<field>: <reason>` per field that UTF-8 cannot encode; [] for the usual entry.

    entry_id and the stored line both encode the entry as UTF-8, and json.loads turns a "\\udcff"
    escape into a lone surrogate that no UTF-8 encoder accepts; asking first keeps that a problem
    with a field name instead of a UnicodeEncodeError.
    """
    def encodable(value: object) -> bool:
        try:
            json.dumps(value, ensure_ascii=False).encode("utf-8")
        except UnicodeEncodeError:
            return False
        return True
    if encodable(entry):
        return []
    # backslashreplace: a surrogate in a field NAME must not make the problem text unprintable.
    return ["%s: not encodable as UTF-8 (a lone surrogate?)"
            % str(k).encode("utf-8", "backslashreplace").decode("utf-8")
            for k, v in entry.items() if not (encodable(k) and encodable(v))]


def validate_entry(entry: dict) -> list[str]:
    """Every problem with `entry`, one `<field>: <reason>` string each; [] when it is valid."""
    problems = ["%s: unknown field" % k for k in entry if k not in FIELDS]
    # type() and not ==: True == 1 in Python, and 1.0 == 1 too.
    if type(entry.get("v")) is not int or entry.get("v") != 1:
        problems.append("v: must be the integer 1")
    problems += _date_problems(entry)
    required = ("decision", "why") if entry.get("kind") == "void" else ("decision", "why", "reopen_if")
    problems += ["%s: empty" % f for f in required if not _text(entry, f)]
    problems += _vocabulary_problems(entry) + _list_problems(entry) + _anchor_problems(entry)
    unencodable = _unencodable_problems(entry)
    if unencodable:
        problems += unencodable         # no id can be computed for it, so none can match
    elif entry.get("id") != entry_id(entry):
        problems.append("id: does not match the entry (edited after it was written?)")
    return problems


# ---- reading a ledger ----
# Every reader takes the ledger as an iterable of lines, or a factory returning a fresh one for each
# pass, so a ledger is never held whole: what a pass keeps is the id sets below and the brief's
# budget, never an entry's text.

_CORPUS_SEP = "\n\x00\n"   # a NUL token: no anchor can match across two files
_CORPUS_SKIP = (".skillwriter/", "tests/")

LinesFactory = Callable[[], Iterable[str | bytes]]


def file_lines(path: str | Path) -> Iterator[bytes]:
    """The lines of `path` as bytes, read one at a time; nothing for a missing file.

    Bytes, so `parse_entries` decodes each line inside its per-line check: a line that is not
    UTF-8 becomes a `LedgerError` naming it, never a UnicodeDecodeError raised by the read.
    """
    path = Path(path)
    if not path.is_file():
        return
    # Iterating a binary file splits on b"\n" only; str.splitlines would also split a JSON string
    # holding a raw U+2028.
    with path.open("rb") as fh:
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
        except RecursionError:
            raise LedgerError(line_no, "not JSON (nested too deeply)") from None
        if not isinstance(entry, dict):
            raise LedgerError(line_no, "not a JSON object")
        problems = validate_entry(entry)
        if problems:
            raise LedgerError(line_no, "; ".join(problems))
        yield entry


def live_entries(lines_factory: LinesFactory) -> Iterator[dict]:
    """Entries no later entry supersedes, voids excluded. Two passes over `lines_factory()`.

    A void withdraws its targets AND what they did: a voided entry's own `supersedes` count for
    nothing, so the entry it superseded is live again. A void that names a void does not bring
    the first void's target back (`append_entries` refuses one), so no fixpoint is needed.
    """
    voided: set[str] = set()
    supersedes: dict[str, list[str]] = {}     # ids only, never an entry's text
    for entry in parse_entries(lines_factory()):
        if entry["kind"] == "void":
            voided.update(entry["supersedes"])
        elif entry["supersedes"]:
            supersedes[entry["id"]] = entry["supersedes"]
    superseded = set(voided)
    for entry_id, targets in supersedes.items():
        if entry_id not in voided:
            superseded.update(targets)
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
                # anchor_occurs, with the corpus normalised once: keep the two tests identical.
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


def render_brief(lines_factory: LinesFactory, *, skill: str, budget_chars: int = 6000,
                 show_command: str | None = None) -> str:
    """The live rejected and removed entries, in full until `budget_chars` is spent, then a count.

    `show_command` is the command the "more not shown" trailer names. A caller that knows where
    this script and the skill really live passes a runnable one; the default is a placeholder,
    because `show <skill>` alone resolves the name against the cwd's repo, which outside the
    marketplace is a different ledger or none.
    """
    blocks, used, left = [], 0, 0
    for entry in live_entries(lines_factory):
        if entry["kind"] not in ("rejected", "removed"):
            continue
        block = None if left else _brief_block(entry)
        # A strict oldest-first prefix: once one block does not fit, every later entry is counted,
        # a shorter one too, so the brief never shows a newer decision while hiding an older one.
        if block is None or used + len(block) > budget_chars:
            left += 1
            continue
        blocks.append(block)
        used += len(block)
    if not blocks and not left:
        return ""
    text = "Decisions already taken for %s (rejected or removed, oldest first):\n" % skill + "\n".join(blocks)
    if left:
        command = show_command or ("python3 <plugin>/hooks/skill_decisions.py show %s "
                                   "--kind rejected,removed --full" % skill)
        text += "\n%d more not shown: %s" % (left, command)
    return text


# ---- writing a ledger ----

class EntryRefused(ValueError):
    """`append_entries` wrote nothing; `problems` says why, one `entry <n>: <field>: <reason>` each."""

    def __init__(self, problems: Iterable[str]) -> None:
        self.problems = list(problems)
        super().__init__("; ".join(self.problems))


_TELL_FIELDS = ("decision", "why", "reopen_if", "topic")


def _tell_problem(field: str, text: str) -> list[str]:
    hits = tell_chars.find_tell_codepoints(text)
    return ["%s: typographic tell (line %s); use ASCII punctuation" % (field, "; line ".join(hits))] if hits else []


def _tell_problems(entry: dict) -> list[str]:
    problems = [p for field in _TELL_FIELDS for p in _tell_problem(field, _text(entry, field))]
    evidence = entry.get("evidence")
    if isinstance(evidence, dict):
        problems += _tell_problem("evidence", _text(evidence, "text"))
    return problems


def _occurrences(needle: str, haystack: str) -> int:
    """How many places `needle` starts at in `haystack`, overlapping ones included.

    str.count counts NON-overlapping hits, so an anchor such as "a b a b" in "a b a b a b" would
    read as unique while it starts at two places.
    """
    count, start = 0, haystack.find(needle)
    while start != -1:
        count += 1
        start = haystack.find(needle, start + 1)
    return count


_UNTRACKED_HINT = " (untracked files are not read: git add them first)"


def _anchor_count_problems(entry: dict, normalised_corpus: str, untracked_md: bool) -> list[str]:
    problems = []
    for anchor in _list(entry, "anchors"):
        needle = normalise(anchor) if isinstance(anchor, str) else ""
        if not ANCHOR_MIN <= len(needle) <= ANCHOR_MAX:
            continue        # validate_entry already refuses it; counting it would only add noise
        hits = _occurrences(needle, normalised_corpus)
        if hits != 1:
            problems.append("anchors: must occur exactly once in the skill text, found %d: %r%s"
                            % (hits, anchor, _UNTRACKED_HINT if not hits and untracked_md else ""))
    return problems


@dataclass(frozen=True)
class _Known:
    """What a batch is checked against: the ids the ledger and the batch hold so far, and which
    of them are voids."""

    ids: set[str]
    voids: set[str]


def _entry_problems(entry: dict, known: _Known, corpus: str, untracked_md: bool) -> list[str]:
    found = (validate_entry(entry) + _tell_problems(entry)
             + _anchor_count_problems(entry, corpus, untracked_md))
    if entry["id"] in known.ids:
        found.append("id: an identical entry is already in the ledger or earlier in this batch")
    targets = [s for s in _list(entry, "supersedes") if isinstance(s, str)]
    found += ["supersedes: unknown id %s" % s for s in targets if s not in known.ids]
    if entry.get("kind") == "void":
        found += ["supersedes: %s is a void; a void cannot be voided" % s
                  for s in targets if s in known.voids]
    return found


def _untracked_markdown(skill_dir: Path) -> bool:
    """True when git lists an untracked, not ignored `.md` file under `skill_dir`."""
    try:
        out = subprocess.run(["git", "ls-files", "-z", "-o", "--exclude-standard", "--", "."],
                             cwd=str(skill_dir), capture_output=True, env=_git_env(), check=False)
    except OSError:
        return False
    return out.returncode == 0 and any(p.endswith(b".md") for p in out.stdout.split(b"\0"))


def _encoded(entry: dict) -> bytes:
    # Raw UTF-8 keeps the ledger readable in a diff; append_entries has already refused an entry
    # holding a lone surrogate, the one value this encode would fail on.
    return (json.dumps(entry, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


@dataclass(frozen=True)
class PreparedBatch:
    """A batch `prepare_entries` validated: the ledger to append to, the bytes and their ids."""

    path: Path
    chunks: tuple[bytes, ...]
    ids: tuple[str, ...]


def prepare_entries(skill_dir: str | Path, entries: list[dict], *,
                    today: str | None = None) -> PreparedBatch:
    """Validate `entries` for the skill's ledger and encode them, writing nothing.

    Each entry gets `v` 1, a `date` (its own, else `today`, else today's UTC date) and its `id`.
    Beyond `validate_entry`, an entry is refused for a typographic tell, a rule anchor that does
    not occur EXACTLY once in `corpus_from_dir(skill_dir)` (git-tracked files only; a refusal
    finding none says so when untracked Markdown sits in the skill), an id the ledger or the batch
    already holds, a `supersedes` id that neither holds before it, and a void naming a void.

    Raises:
        EntryRefused: each problem names its entry by place in `entries`.
        LedgerError: the existing ledger does not parse.
    """
    today = today or datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    path = ledger_path(skill_dir)
    known = _Known(set(), set())
    for e in parse_entries(file_lines(path)):
        known.ids.add(e["id"])
        if e["kind"] == "void":
            known.voids.add(e["id"])
    corpus = normalise(corpus_from_dir(skill_dir))
    untracked_md = _untracked_markdown(Path(skill_dir))
    problems, chunks, ids = [], [], []
    for n, draft in enumerate(entries, 1):
        if not isinstance(draft, dict):
            problems.append("entry %d: not a JSON object" % n)
            continue
        entry = dict(draft, v=1, date=draft.get("date") or today)
        if _unencodable_problems(entry):
            # Before entry_id, which encodes the entry: validate_entry names the field instead.
            problems += ["entry %d: %s" % (n, p) for p in validate_entry(entry)]
            continue
        entry["id"] = entry_id(entry)
        problems += ["entry %d: %s" % (n, p)
                     for p in _entry_problems(entry, known, corpus, untracked_md)]
        known.ids.add(entry["id"])
        if entry.get("kind") == "void":
            known.voids.add(entry["id"])
        ids.append(entry["id"])
        chunks.append(_encoded(entry))
    if problems:
        raise EntryRefused(problems)
    return PreparedBatch(path, tuple(chunks), tuple(ids))


def write_prepared(batch: PreparedBatch) -> list[str]:
    """Append a `prepare_entries` batch to its ledger in one write; return its ids."""
    if not batch.chunks:
        return []
    batch.path.parent.mkdir(parents=True, exist_ok=True)
    prefix = b"\n" if _ends_without_newline(batch.path) else b""
    # One write in binary mode: no newline translation on Windows, and the batch lands together.
    with batch.path.open("ab") as fh:
        fh.write(prefix + b"".join(batch.chunks))
    return list(batch.ids)


def append_entries(skill_dir: str | Path, entries: list[dict], *, today: str | None = None) -> list[str]:
    """Validate `entries` and append them to the skill's ledger, all or nothing; return their ids.

    `prepare_entries` then `write_prepared`; see the first for what is refused.

    Raises:
        EntryRefused: nothing was written; each problem names its entry by place in `entries`.
        LedgerError: the existing ledger does not parse.
    """
    return write_prepared(prepare_entries(skill_dir, entries, today=today))


def _ends_without_newline(path: Path) -> bool:
    """True when a non-empty `path` lacks a final newline; reads one byte, not the ledger."""
    if not path.is_file() or path.stat().st_size == 0:
        return False
    with path.open("rb") as fh:
        fh.seek(-1, os.SEEK_END)
        return fh.read(1) != b"\n"


# ---- the command line ----
# Exit 0 yes, 1 findings or refused, 2 could not run. With --json the envelope
# {ok, command, data, skipped} goes to stdout even on a failure; diagnostics go to stderr.

_PROG = "skill_decisions.py"
_SKILL_NAME = re.compile(r"[a-z0-9][a-z0-9-]*")
_SHORT_FIELDS = ("id", "kind", "topic", "decision")
_PROBLEM_PLACE = re.compile(r"entry ([0-9]+): ")


class _RunError(Exception):
    """The verb could not run (exit 2); `data` joins the error in the --json envelope."""

    def __init__(self, message: str, data: dict | None = None) -> None:
        super().__init__(message)
        self.data = data or {}


class _UsageError(Exception):
    """argparse refused the command line (exit 2)."""


class _Parser(argparse.ArgumentParser):
    # argparse's own error() prints usage and exits; this keeps the --json envelope possible.
    def error(self, message: str) -> NoReturn:
        raise _UsageError("%s: %s" % (self.prog, message))


def _installed_plugins_dir() -> Path | None:
    try:
        return claude_paths.config_dir() / "plugins"
    except RuntimeError:        # no home directory to resolve
        return None


def _is_within(path: Path, root: Path | None) -> bool:
    if root is None:
        return False
    try:
        path.resolve().relative_to(root.resolve())
    except (ValueError, OSError):
        return False
    return True


def _repo_skills_dir() -> Path | None:
    """`plugins/bitranox/skills` at the git top of the cwd; None outside such a repo."""
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True,
                             encoding="utf-8", errors="replace", env=_git_env(), check=False)
    except OSError:
        return None
    candidate = Path(out.stdout.strip()) / "plugins" / "bitranox" / "skills"
    return candidate if out.returncode == 0 and candidate.is_dir() else None


def _skills_dir(arg: str | None, *, writing: bool = False) -> Path:
    if arg:
        if not Path(arg).is_dir():
            raise _RunError("--skills-dir %s is not a directory" % arg)
        return Path(arg)
    found = _repo_skills_dir()
    if found is None:
        raise _RunError("no skills dir: run inside the marketplace repo or pass --skills-dir")
    # The marketplace clone Claude Code keeps under its plugins dir is a git repo too; a write
    # there would land in an installed copy, which the next update overwrites.
    if writing and _is_within(found, _installed_plugins_dir()):
        raise _RunError("%s is an installed plugin copy: run inside the marketplace repo or pass "
                        "--skills-dir" % found)
    return found


def _named_skill(root: Path, name: object) -> Path:
    # One lowercase path component: a name like "../x" must not reach a ledger outside `root`.
    if not isinstance(name, str) or not _SKILL_NAME.fullmatch(name) or not (root / name).is_dir():
        raise _RunError("no skill %r in %s" % (name, root))
    return root / name


def _read_drafts(from_file: str) -> list:
    try:
        raw = json.loads(Path(from_file).read_text(encoding="utf-8"))
    except (OSError, ValueError, RecursionError) as exc:
        # RecursionError: json.loads gives up on deep nesting by raising it, not a ValueError.
        raise _RunError("cannot read %s: %s" % (from_file, exc)) from None
    drafts = raw if isinstance(raw, list) else [raw]
    if not drafts:
        raise _RunError("%s holds no entries" % from_file)
    return drafts


def _group_by_skill(root: Path, drafts: list) -> dict[Path, list[tuple[int, dict]]]:
    """Every draft under its skill dir, with its place in the file.

    Raises _RunError for a draft that is no object or names no skill under `root`. `_cmd_add`
    then validates every skill's batch before it writes any, so a file is all or nothing.
    """
    by_skill: dict[Path, list[tuple[int, dict]]] = {}
    for n, draft in enumerate(drafts, 1):
        if not isinstance(draft, dict):
            raise _RunError("entry %d: not a JSON object" % n)
        draft = dict(draft)
        skill_dir = _named_skill(root, draft.pop("skill", None))
        by_skill.setdefault(skill_dir, []).append((n, draft))
    return by_skill


def _renumbered(problem: str, places: list[int]) -> str:
    # append_entries numbers an entry by its place in ONE skill's batch; the reader fixes the FILE.
    match = _PROBLEM_PLACE.match(problem)
    if not match:
        return problem
    return "entry %d: %s" % (places[int(match.group(1)) - 1], problem[match.end():])


def _cmd_add(args: argparse.Namespace) -> tuple[int, dict]:
    """All or nothing across the whole file: every skill's batch is validated before any is
    written, so a refusal in one skill never leaves another written and the retry refused as
    identical."""
    drafts = _read_drafts(args.from_file)
    by_skill = _group_by_skill(_skills_dir(args.skills_dir, writing=True), drafts)
    prepared: list[tuple[Path, PreparedBatch]] = []
    refused: list[str] = []
    for skill_dir, batch in by_skill.items():
        places = [n for n, _draft in batch]
        try:
            prepared.append((skill_dir, prepare_entries(skill_dir, [d for _n, d in batch])))
        except EntryRefused as exc:
            refused += [_renumbered(p, places) for p in exc.problems]
        except (LedgerError, OSError) as exc:
            raise _RunError("%s: %s" % (ledger_path(skill_dir), exc), {"written": {}}) from None
    if refused:
        return 1, {"written": {}, "refused": sorted(refused, key=_place)}
    written: dict[str, list[str]] = {}
    for skill_dir, ready in prepared:
        try:
            written[skill_dir.name] = write_prepared(ready)
        except OSError as exc:
            # A failed write cannot be rolled back across files: say what did land.
            raise _RunError("%s: %s" % (ready.path, exc), {"written": written}) from None
    return 0, {"written": written}


def _place(problem: str) -> int:
    """The entry number a refusal starts with, so refusals read in file order across skills."""
    match = _PROBLEM_PLACE.match(problem)
    return int(match.group(1)) if match else 0


def _show_dir(args: argparse.Namespace) -> Path:
    if args.skill_dir:
        if not Path(args.skill_dir).is_dir():
            raise _RunError("--skill-dir %s is not a directory" % args.skill_dir)
        return Path(args.skill_dir)
    # Reading is safe anywhere, so an install falls back to the skills it ships beside this script.
    root = _repo_skills_dir() or Path(__file__).resolve().parents[1] / "skills"
    return _named_skill(root, args.skill)


def _kinds(arg: str | None) -> set[str]:
    kinds = set(arg.split(",")) if arg else set(KINDS)
    if not kinds <= set(KINDS):
        raise _RunError("--kind: each must be one of %s" % ", ".join(KINDS))
    return kinds


def _cmd_show(args: argparse.Namespace) -> tuple[int, dict]:
    skill_dir, kinds = _show_dir(args), _kinds(args.kind)
    path = ledger_path(skill_dir)
    try:
        for _entry in parse_entries(file_lines(path)):
            pass        # a whole pass first, so a bad line exits 2 before any entry is printed
    except LedgerError as exc:
        raise _RunError("%s: %s" % (path, exc)) from None
    entries = parse_entries(file_lines(path)) if args.all else live_entries(lambda: file_lines(path))
    return 0, {"skill": skill_dir.name, "entries": _shown(entries, args, kinds)}


_ALL_HINT = ("%s show: void and superseded entries are listed only with --all"
             % _PROG)


def _shown(entries: Iterable[dict], args: argparse.Namespace, kinds: set[str]) -> Iterator[dict]:
    """The entries `show` prints, streamed one at a time and never held together.

    Without --all, a show asking for voids, or for an id that matched nothing, ends with a stderr
    hint: those entries are never live, so the empty answer would read as "not recorded".
    """
    count = 0
    for e in entries:
        if e["kind"] in kinds and args.topic in (None, e["topic"]) and args.id in (None, e["id"]):
            count += 1
            yield e if args.full else {k: e[k] for k in _SHORT_FIELDS}
    if not args.all and ((args.kind and "void" in kinds) or (args.id and not count)):
        print(_ALL_HINT, file=sys.stderr)


def _cmd_check(args: argparse.Namespace) -> tuple[int, dict]:
    root = _skills_dir(args.skills_dir)
    dirs = ([_named_skill(root, name) for name in args.skills]
            or sorted(p.parent.parent for p in root.glob("*/" + LEDGER_REL)))
    if not dirs:
        # Exit 0 stands (nothing found is nothing wrong), but a check that read nothing must say
        # where it looked: a wrong cwd or --skills-dir reads exactly like a clean store.
        print("%s check: no ledger found under %s (*/%s)" % (_PROG, root, LEDGER_REL),
              file=sys.stderr)
    findings = []
    for skill_dir in dirs:
        path = ledger_path(skill_dir)
        for finding in check_ledger(lambda p=path: file_lines(p), corpus_from_dir(skill_dir)):
            findings.append({"skill": skill_dir.name, "text": finding.render()})
    return (1 if findings else 0), {"checked": [d.name for d in dirs], "findings": findings}


_VERBS = {"add": _cmd_add, "show": _cmd_show, "check": _cmd_check}


def _parser() -> argparse.ArgumentParser:
    parser = _Parser(prog=_PROG, description=__doc__.split("\n")[0])
    parser.add_argument("--json", action="store_true", help="print a JSON envelope")
    sub = parser.add_subparsers(dest="command", required=True)
    add = sub.add_parser("add", help="append entries from a JSON file")
    add.add_argument("--from-file", required=True, help="one entry object or a list; each names its 'skill'")
    add.add_argument("--skills-dir", help="default: plugins/bitranox/skills at the git top of the cwd")
    show = sub.add_parser("show", help="list a skill's decisions")
    show.add_argument("skill")
    show.add_argument("--skill-dir", help="the skill's own dir, instead of looking SKILL up")
    show.add_argument("--kind", help="comma-separated: %s" % ",".join(KINDS))
    show.add_argument("--topic")
    show.add_argument("--id")
    show.add_argument("--all", action="store_true", help="include superseded and void entries")
    show.add_argument("--full", action="store_true", help="every field, not one line each")
    check = sub.add_parser("check", help="check ledgers against their skill text")
    check.add_argument("skills", nargs="*", help="default: every skill holding a ledger")
    check.add_argument("--skills-dir", help="default: plugins/bitranox/skills at the git top of the cwd")
    for verb in (add, show, check):
        verb.add_argument("--json", action="store_true", default=argparse.SUPPRESS,
                          help="print a JSON envelope")
    return parser


def _write_envelope(ok: bool, command: str, data: Mapping[str, object]) -> None:
    """The --json envelope on stdout; an iterator in `data` streams as a list, item by item."""
    out = sys.stdout
    out.write('{"ok": %s, "command": %s, "data": {' % (json.dumps(ok), json.dumps(command)))
    for n, (key, value) in enumerate(data.items()):
        out.write("%s%s: " % (", " if n else "", json.dumps(key)))
        if isinstance(value, Iterator):
            out.write("[")
            for i, item in enumerate(value):
                out.write((", " if i else "") + json.dumps(item))
            out.write("]")
        else:
            out.write(json.dumps(value))
    out.write('}, "skipped": []}\n')


def _print_text(command: str, data: Mapping) -> None:
    if command == "show":
        for e in data["entries"]:
            print(json.dumps(e, ensure_ascii=False) if "why" in e else
                  "%s  %-8s %-24s %s" % (e["id"], e["kind"], e["topic"], e["decision"]))
    elif command == "check":
        for f in data["findings"]:
            print("%s: %s" % (f["skill"], f["text"]))
        print("checked %d ledger(s), %d finding(s)" % (len(data["checked"]), len(data["findings"])))
    else:
        for skill, ids in data.get("written", {}).items():
            print("%s: %s" % (skill, ", ".join(ids)))
        for problem in data.get("refused", []):
            print("refused: " + problem, file=sys.stderr)


def _fail(as_json: bool, command: str, line: str, data: Mapping) -> int:
    """Report a verb that could not run: the envelope (--json), one stderr line, exit 2."""
    if as_json:
        _write_envelope(False, command, dict(data, error=line))
    elif data.get("written"):
        _print_text("add", {"written": data["written"]})
    print(line, file=sys.stderr)
    return 2


def _tolerant_streams() -> None:
    # Run directly, not through run-python.sh, the script inherits the console's codepage: on a
    # cp1252 Windows console a non-ASCII decision would otherwise end in a UnicodeEncodeError.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(errors="backslashreplace")


def main(argv: list[str] | None = None) -> int:
    """Run one verb; see the module docstring and `--help`."""
    _tolerant_streams()
    argv = sys.argv[1:] if argv is None else list(argv)
    try:
        args = _parser().parse_args(argv)
    except _UsageError as exc:
        return _fail("--json" in argv, next((a for a in argv if a in _VERBS), ""), str(exc), {})
    try:
        rc, data = _VERBS[args.command](args)
        if args.json:
            _write_envelope(rc == 0, args.command, data)
        else:
            _print_text(args.command, data)
    except _RunError as exc:
        return _fail(args.json, args.command, "%s %s: %s" % (_PROG, args.command, exc), exc.data)
    except (LedgerError, OSError) as exc:
        return _fail(args.json, args.command, "%s %s: %s" % (_PROG, args.command, exc), {})
    return rc


if __name__ == "__main__":
    sys.exit(main())
