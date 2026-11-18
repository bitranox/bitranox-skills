#!/usr/bin/env python3
"""Guard a review-log claim that something is NOT the user's decision: it must name a checked term.

Registered on PreToolUse(Write|Edit|MultiEdit), PreToolUse(Bash|PowerShell) and
PostToolUse(Bash|PowerShell|Monitor).

Sessions keep a git-ignored EXECUTION-USER-REVIEW.md at the repo root: the decisions they took
themselves. Writing there that a property is "not a user decision" or "my own wording" is a claim
about the user's answers, and it has been false: on 2026-11-18 a session logged "no cap" as "my own
wording, not a user decision" while the option the user had chosen said "Upside: no limit on number
or total length". The memory fact feedback-relay-a-user-decision-verbatim-with-its-negative-case-
never-a-paraphrase counts seven such relays. Every answer IS on disk (user-decision-log.py appends
each AskUserQuestion answer, every option's label and description, to USER-DECISIONS.jsonl at the
main checkout root), so the claim can be checked mechanically, and this hook makes it be.

The rule. When text ADDED to a file named EXECUTION-USER-REVIEW.md holds a trigger phrase
(`TRIGGER`: "not a user decision", "no user decision", "my own wording", "not the user's",
"the user never decided", "not decided by the user", either apostrophe), the entry holding it must
carry a marker `decision-check: "<term>"` naming the property's key term. For each marker the hook
searches every CHOSEN option's label and description in USER-DECISIONS.jsonl (a free-text answer
or a plan-rejection remark: the text the user typed), case-insensitively. A hit is refused with
the matching option quoted, since the user's answer then names the property; a missing marker is refused with how to add
one. No USER-DECISIONS.jsonl anywhere: allowed, silently. An unchosen option never counts.

An ENTRY is a top-level list item or a heading with everything up to the next one (a fenced code
block never starts one), so a marker on the item's last line belongs to the claim on its first.

Write and Edit are judged on their input, before anything is written. A Bash script can also write
the file (the 2026-11-18 session used a python heredoc), and no PreToolUse hook can see what a
script will write, so the Bash path works on disk: PreToolUse snapshots each candidate review log
(the one at the git work tree root of the cwd, at its main checkout root, and any path the command
names), and PostToolUse judges the lines the command added against that snapshot, then stores the
new state. A line is judged once: the snapshot is the record of what has been judged, so an old
entry, accepted or not, is never reported again.

Decisions:
    - Trigger phrases are claims that a property is NOT the user's decision; "(my reading)", "my
      call, not asked" and other first-person decision records are not triggers. Why: the file's
      purpose is to list decisions the session took itself, and only the denial of a user decision
      is a claim the jsonl can falsify. Evidence: measured 2026-11-18 over every
      EXECUTION-USER-REVIEW.md on the author's machine (1175 files): 12 distinct lines fire, all 12
      assert something is not (or changes no) user decision; "my call, not asked" alone would add
      routine entries. Reopen if: a false claim recurs in a phrasing the list lacks.
      Pinned by: tests/test_decision_claim_guard.py::test_trigger_phrases_cover_both_apostrophes,
      tests/test_decision_claim_guard.py::test_a_first_person_decision_record_is_no_trigger
    - Only ADDED text is searched for a trigger; the marker may sit anywhere in the entry. Why: a
      later correction appended to an entry whose old sentence holds the phrase must not be
      refused for that old sentence. Evidence: the 2026-11-18 entry was corrected by appending a
      CORRECTION sentence. Pinned by:
      tests/test_decision_claim_guard.py::test_an_edit_adding_text_beside_an_old_claim_is_allowed
    - A marker term must also occur in the entry outside the marker. Why: a term the claim never
      uses checks nothing ("decision-check: \"xyzzy\"" would pass every claim). Evidence: argued.
      Pinned by: tests/test_decision_claim_guard.py::test_a_marker_term_absent_from_the_entry_is_refused
    - The refusal quotes the user's chosen option. Why: the reader is the model mid-turn, and the
      quote is the answer it has to record instead; the jsonl holds the user's own words, which the
      session already showed the user. Evidence: brief 2026-11-18. Pinned by:
      tests/test_decision_claim_guard.py::test_a_marker_hitting_a_chosen_option_is_refused_with_the_quote
    - The Bash path names an entry by line number and its first 100 characters. Why: the command
      that wrote it is the model's own, so this hands back nothing it did not write. Pinned by:
      tests/test_decision_claim_guard.py::test_bash_post_reports_the_added_entry_once
    - A review log with no snapshot (PreToolUse did not see it) is seeded silently, never judged
      whole. Why: judging a whole pre-existing log reports months of old entries at once. A log
      the snapshot recorded as ABSENT is judged whole: the command created it. Pinned by:
      tests/test_decision_claim_guard.py::test_bash_post_without_a_snapshot_seeds_silently,
      tests/test_decision_claim_guard.py::test_bash_post_judges_a_log_the_command_created
    - A line is judged once, refused or not: PostToolUse stores the state it judged, and the next
      PreToolUse snapshot refreshes it. Why: a refused PostToolUse write already stands, so the
      model is told once and fixes it with Edit (which this hook judges again); repeating the
      report on every later command is noise. Pinned by:
      tests/test_decision_claim_guard.py::test_bash_post_reports_the_added_entry_once,
      tests/test_decision_claim_guard.py::test_a_post_with_no_pre_between_does_not_re_report
    - A term hit is refused even when the hit sits in an unrelated question; the refusal lists the
      hits newest first and says to name a more specific term when none is about the property.
      Why: the hook cannot tell which question an entry is about, and a common word ("limit")
      hits several; refusing keeps the error on the safe side, and the term must still occur in
      the entry. Evidence: measured 2026-11-18 on the defect's own log: "limit" hit two answers
      before the right one, "no cap" (the entry's own wording) hit none. KNOWN GAP: a claim worded
      with a synonym of the option's word passes; the remedy text asks for one marker per synonym.
      Reopen if: a false claim passes this way. Pinned by:
      tests/test_decision_claim_guard.py::test_a_marker_hitting_a_chosen_option_is_refused_with_the_quote
    - Rejected:a USER-DECISIONS.jsonl lookup in the launch directory's repository (as
      user-decision-log.py writes). Why: the log of the file's own repository and of the event cwd
      covers every case seen; reading the transcript per write costs more. Reopen if: a session
      launched in an umbrella writes a nested repository's review log and slips through.

Fails open: any error allows the write (exit 0). A PreToolUse refusal is exit 2 through
shell_text.refuse (reason and the whole-call footer on stderr); a PostToolUse refusal is exit 0
with {"decision": "block", "reason": ...} on stdout, because the command already ran and the
footer would say it did not. Claude reads both mid-turn.
"""

from __future__ import annotations

import collections
import dataclasses
import hashlib
import json
import os
import re
import sys
from pathlib import Path

import claude_paths
import shell_text
from self_improve_signals import main_checkout_root

__all__ = ["TRIGGER", "MARKER", "entries", "judge", "main"]

REVIEW_NAME = "EXECUTION-USER-REVIEW.md"
LOG_NAME = "USER-DECISIONS.jsonl"
_STATE_DIR = "decision-claim-guard"
_WRITE_TOOLS = frozenset({"Write", "Edit", "MultiEdit"})
_SHELL_TOOLS = frozenset({"Bash", "PowerShell"})
_POST_TOOLS = frozenset({"Bash", "PowerShell", "Monitor"})
_MAX_BYTES = 16 * 1024 * 1024          # a review log beyond this is not judged at all
_MIN_TERM = 3
_QUOTE_MAX = 400
_HEAD_MAX = 100
_RECENT = 8
_SHOWN = 3

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
_PATH_IN_TEXT = re.compile(r"[^\s'\"`;|&<>()=]*" + re.escape(REVIEW_NAME), re.IGNORECASE)
_SPACE = re.compile(r"\s+")


@dataclasses.dataclass(frozen=True)
class Entry:
    """One review-log entry: its first line number (1-based) and its lines."""

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


@dataclasses.dataclass(frozen=True)
class Problem:
    """Why one entry is refused."""

    entry: Entry
    kind: str            # "no-marker" | "bad-term" | "hit"
    detail: str


def entries(text: str) -> list[Entry]:
    """Split a review log into entries at each top-level list item or heading, outside fences."""
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


def _counts(text: str) -> collections.Counter[str]:
    return collections.Counter(_line_key(line) for line in text.splitlines())


def triggered_entries(text: str, before: collections.Counter[str]) -> list[Entry]:
    """Entries of `text` where a trigger phrase touches a line `before` did not hold. PURE."""
    excess = _counts(text) - before
    hit = []
    for entry in entries(text):
        added = []
        for line in entry.lines:
            key = _line_key(line)
            fresh = excess[key] > 0
            if fresh:
                excess[key] -= 1
            added.append(fresh)
        if any(added) and _trigger_on_added(entry, added):
            hit.append(entry)
    return hit


def _trigger_on_added(entry: Entry, added: list[bool]) -> bool:
    """True when a trigger match overlaps an added line (a match may wrap across lines)."""
    joined, owner = "", []
    for index, line in enumerate(entry.lines):
        piece = line + " "
        joined += piece
        owner.extend([index] * len(piece))
    for match in TRIGGER.finditer(joined):
        if any(added[owner[i]] for i in range(match.start(), max(match.start() + 1, match.end()))):
            return True
    return False


def _norm(text: str) -> str:
    return _SPACE.sub(" ", text).strip().lower()


def _chosen_texts(record: dict) -> list[tuple[str, str, str]]:
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


def _iter_records(logs: list[Path]):
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
    want, hits = _norm(term), []
    for record in _iter_records(logs):
        for header, label, text in _chosen_texts(record):
            if want not in _norm(text):
                continue
            sentence = next((s for s in _SENTENCE.split(text) if want in _norm(s)), text)
            hits.append(Hit(term, header, label, sentence.strip()[:_QUOTE_MAX]))
    return hits


def judge(entry: Entry, logs: list[Path]) -> Problem | None:
    """The reason `entry` is refused, or None when its markers check out. PURE but for `logs`."""
    terms = MARKER.findall(entry.text)
    if not terms:
        return Problem(entry, "no-marker", "")
    outside = _norm(MARKER.sub(" ", entry.text))
    for term in terms:
        if len(term.strip()) < _MIN_TERM:
            return Problem(entry, "bad-term", "the term %r is shorter than %d characters" % (term, _MIN_TERM))
        if _norm(term) not in outside:
            return Problem(entry, "bad-term",
                           "the term %r does not occur in the entry outside the marker" % term)
    for term in terms:
        hits = find_hits(term, logs)[::-1]             # the most recent answer first
        if hits:
            shown = [dataclasses.asdict(h) for h in hits[:_SHOWN]]
            return Problem(entry, "hit", json.dumps({"hits": shown, "more": len(hits) - len(shown)}))
    return None


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


def _recent(logs: list[Path]) -> list[str]:
    tail = collections.deque(maxlen=_RECENT)
    for record in _iter_records(logs):
        tail.append("%s: %s" % (record.get("header") or record.get("question"), record.get("chosen")))
    return list(tail)


def _head(entry: Entry) -> str:
    first = entry.lines[0].strip() if entry.lines else ""
    return first[:_HEAD_MAX] + ("..." if len(first) > _HEAD_MAX else "")


def explain(problem: Problem, logs: list[Path], where: str) -> str:
    """The refusal text for one problem, written for the model to act on."""
    lead = "DECISION CLAIM CHECK (%s, entry at line %d: %r): " % (where, problem.entry.start, _head(problem.entry))
    if problem.kind == "no-marker":
        recent = "".join("\n  - " + r for r in _recent(logs))
        return lead + (
            "this entry says something is NOT the user's decision, and every answer the user gave "
            "is in %s. Grep the CHOSEN options there (label AND description, upside and downside "
            "lines included) for the property, then add a marker line to the entry naming its key "
            "term as the entry itself spells it, e.g. decision-check: \"no cap\" (one marker per "
            "synonym if the option might use another word: decision-check: \"limit\"). This hook "
            "then searches the chosen options for each term and refuses the write if one holds "
            "it. Most recent answers:%s" % (" and ".join(str(p) for p in logs), recent))
    if problem.kind == "bad-term":
        return lead + problem.detail + ". Name the property's key term as the entry writes it, " \
            "e.g. decision-check: \"no cap\"."
    found = json.loads(problem.detail)
    hits = found["hits"]
    quotes = "".join("\n  - [%s] chose %r: \"%s\"" % (h["header"], h["label"], h["sentence"]) for h in hits)
    more = "\n  (%d more, older)" % found["more"] if found["more"] else ""
    return lead + (
        "the term %r occurs in an option the user CHOSE (most recent first):%s%s\nIf one of these "
        "covers the property, the claim is false and it IS a user decision: correct the entry - "
        "drop the 'not a user decision' claim, quote the chosen option verbatim, and if your change "
        "narrows it, put that to the user. If none of them is about this property, name a term "
        "specific to it instead (it must still occur in the entry)." % (hits[0]["term"], quotes, more))


# ---- Write / Edit / MultiEdit (PreToolUse) ----------------------------------------------------


def _is_review(path: str) -> bool:
    return os.path.basename(path.replace("\\", "/")).lower() == REVIEW_NAME.lower()


def _resolve(raw: str, cwd: str | None) -> Path:
    path = Path(os.path.expanduser(raw))
    if not path.is_absolute():
        path = Path(cwd or ".") / path
    return Path(os.path.normpath(str(path)))


def _read(path: Path) -> str | None:
    try:
        if path.stat().st_size > _MAX_BYTES:
            return None
        return path.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")
    except FileNotFoundError:
        return ""
    except OSError:
        return None


def _apply_edits(text: str, edits: list[dict]) -> tuple[str, str]:
    """(old text, new text) for the edits; an edit whose old_string is absent judges new_string alone."""
    new = text
    for edit in edits:
        old_s, new_s = str(edit.get("old_string") or ""), str(edit.get("new_string") or "")
        if old_s and old_s in new:
            new = new.replace(old_s, new_s) if edit.get("replace_all") else new.replace(old_s, new_s, 1)
        else:
            return old_s, new_s
    return text, new


def _proposed(tool_input: dict, current: str, tool: str) -> tuple[str, str]:
    if tool == "Write":
        return current, str(tool_input.get("content") or "")
    edits = tool_input.get("edits") if tool == "MultiEdit" else [tool_input]
    return _apply_edits(current, [e for e in edits or [] if isinstance(e, dict)])


def on_write(event: dict) -> str | None:
    tool_input = event.get("tool_input") or {}
    raw = tool_input.get("file_path")
    if not isinstance(raw, str) or not _is_review(raw):
        return None
    path = _resolve(raw, event.get("cwd"))
    current = _read(path)
    if current is None:
        return None
    before, after = _proposed(tool_input, current, event.get("tool_name"))
    flagged = triggered_entries(after, _counts(before))
    if not flagged:
        return None
    cwd = Path(event["cwd"]) if isinstance(event.get("cwd"), str) else None
    logs = decision_logs(path.parent, cwd)
    if not logs:
        return None
    problems = [p for p in (judge(e, logs) for e in flagged) if p is not None]
    return "\n\n".join(explain(p, logs, str(path)) for p in problems) or None


# ---- Bash / PowerShell / Monitor (PreToolUse snapshot, PostToolUse judge) ---------------------


def _linked_main_root(root: Path) -> Path | None:
    """The main checkout of the linked worktree at `root` (a `.git` FILE naming .git/worktrees/X)."""
    try:
        pointer = (root / ".git").read_text(encoding="utf-8").strip()
    except OSError:                                    # a `.git` directory: no linked worktree
        return None
    if not pointer.startswith("gitdir:"):
        return None
    gitdir = _resolve(pointer[len("gitdir:"):].strip(), str(root))
    if gitdir.parent.name == "worktrees" and gitdir.parent.parent.name == ".git":
        return gitdir.parent.parent.parent
    return None


def _work_roots(cwd: Path) -> list[Path]:
    """The git work tree root holding `cwd` and its main checkout root, found without running git."""
    for directory in (cwd, *cwd.parents):
        if shell_text.is_work_tree_root(str(directory)):
            main = _linked_main_root(directory)
            return [directory] if main is None else [directory, main]
    return [cwd]


def candidates(event: dict) -> list[Path]:
    """Review logs a shell command may have written: at the work roots and any path it names."""
    raw_cwd = event.get("cwd")
    cwd = Path(raw_cwd) if isinstance(raw_cwd, str) and raw_cwd else None
    found = [root / REVIEW_NAME for root in (_work_roots(cwd) if cwd else [])]
    command = (event.get("tool_input") or {}).get("command")
    if isinstance(command, str) and REVIEW_NAME.lower() in command.lower():
        found.extend(_resolve(m.group(0), raw_cwd) for m in _PATH_IN_TEXT.finditer(command))
    unique = []
    for path in found:
        if path not in unique:
            unique.append(path)
    return unique[:8]


def _state_path(path: Path) -> Path:
    key = hashlib.sha1(str(path).encode("utf-8", "surrogatepass")).hexdigest()[:16]
    return claude_paths.audit_dir() / _STATE_DIR / (key + ".json")


def _signature(path: Path) -> list[int] | None:
    try:
        st = path.stat()
    except OSError:
        return None
    return [st.st_mtime_ns, st.st_size]


def _load_state(path: Path) -> dict | None:
    try:
        state = json.loads(_state_path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return state if isinstance(state, dict) else None


def _save_state(path: Path, signature: list[int] | None, text: str) -> None:
    target = _state_path(path)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(".tmp%d" % os.getpid())
        tmp.write_text(json.dumps({"path": str(path), "sig": signature, "lines": _counts(text)}),
                       encoding="utf-8")
        os.replace(tmp, target)
    except OSError:
        pass


def on_shell_pre(event: dict) -> None:
    """Record each candidate log as it is before the command runs (re-read only when it changed)."""
    for path in candidates(event):
        signature = _signature(path)
        state = _load_state(path)
        if state is not None and state.get("sig") == signature:
            continue
        text = _read(path) if signature is not None else ""
        if text is not None:
            _save_state(path, signature, text)


def on_shell_post(event: dict) -> str | None:
    """Judge the lines the command added to each candidate log; store the new state either way."""
    cwd = Path(event["cwd"]) if isinstance(event.get("cwd"), str) else None
    messages = []
    for path in candidates(event):
        signature = _signature(path)
        state = _load_state(path)
        if signature is None or (state is not None and state.get("sig") == signature):
            continue
        text = _read(path)
        if text is None:
            continue
        _save_state(path, signature, text)
        if state is None:
            continue                                   # never snapshotted: seed, do not judge
        before = collections.Counter(state.get("lines") or {})
        flagged = triggered_entries(text, before)
        logs = decision_logs(path.parent, cwd) if flagged else []
        for entry in flagged if logs else []:
            problem = judge(entry, logs)
            if problem is not None:
                messages.append(explain(problem, logs, str(path)))
    if not messages:
        return None
    return "\n\n".join(messages) + (
        "\n\nThe file was already written by that command: fix the entry now (Edit the file), "
        "then go on.")


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:  # noqa: BLE001 - no or invalid stdin: nothing to judge
        return 0
    if not isinstance(event, dict):
        return 0
    tool, hook = event.get("tool_name"), event.get("hook_event_name")
    if hook == "PreToolUse" and tool in _WRITE_TOOLS:
        message = on_write(event)
        return shell_text.refuse(message) if message else 0
    if hook == "PreToolUse" and tool in _SHELL_TOOLS:
        on_shell_pre(event)
    elif hook == "PostToolUse" and tool in _POST_TOOLS:
        message = on_shell_post(event)
        if message:
            # The command already ran, so the shared refusal footer ("NOTHING in this call ran")
            # would be false here: PostToolUse blocks through its own decision field instead.
            sys.stdout.write(json.dumps({"decision": "block", "reason": message}) + "\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - a broken guard must never wedge a turn
        sys.exit(0)
