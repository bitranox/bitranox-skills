#!/usr/bin/env python3
"""Guard written claims about the user's answers: "not a user decision" and "the user approved".

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

The approval rule. The same file has a second duty for OPEN-WORK.md, any handover.md and the
messages of a git command (`-m`, `-F` file, a stdin heredoc, read through commit-tell-sweep.py,
which owns that parsing). Text added there that claims the USER approved something
(approval_claims.APPROVAL: "the user approved / agreed / accepted / said yes", "user-approved",
"as the user approved", "der Benutzer hat ... freigegeben / zugestimmt", "vom Benutzer
freigegeben") passes only when the same entry carries the user's own words in quotes, found in a
message the person typed (task notifications, teammate and peer messages excluded), a chosen
AskUserQuestion answer in the transcript or in USER-DECISIONS.jsonl, or names the file of a plan the
user approved in plan mode; or a `decision-check: "<term>"` marker that resolves in
USER-DECISIONS.jsonl (decision_claims, shared with the review-log rule). A bare paraphrase is
refused, and so is a quote the user never typed, naming the nearest message the user did type. A
claim that passes but reaches past its evidence (a widening word such as "as is" or "everything"
the quote lacks, or an iron-rule area it does not name) gets an advisory, never a block. A commit
message from a -F file is reported by line, never quoted back: this runs before the call is
approved. The backlog_add tool writes OPEN-WORK.md itself, outside every hook, so mod_bridge.py
applies the same rule (approval_claims) there.

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

    - The approval rule's triggers are the requested phrase list and its German forms only; the
      passive "approved by the user" and "with the user's go" were tried and left out. Why: replayed
      2026-11-20 over 7,418 real writes to the watched files (3,875 commit -F, 461 commit -m, 2,130
      handover, 745 OPEN-WORK, 207 backlog_add; deduped by tool_use id), the wider list refused
      56 (0.75%), mostly plan approvals and prospective "only with the user's go"; the list as
      shipped refuses 38 (0.51%, about 1 in 195), 33 bare paraphrases and 5 quotes the user never
      typed, against 0 of 7,211 for the pre-change guard. KNOWN GAP: "pushed with the user's go"
      (7 of those 56, each a real push claim) passes unchecked. Reopen if: a false claim recurs in
      a passive or "go" phrasing. Pinned by:
      tests/test_approval_claim_guard.py::test_approval_phrases_trigger,
      tests/test_approval_claim_guard.py::test_passive_and_go_forms_are_deliberately_no_triggers
    - A quote passes only when the user typed it (transcript_turns.human_text), chose it
      (an AskUserQuestion answer: chosen label and description), or it is in a chosen
      USER-DECISIONS.jsonl answer; on a miss the project's earlier transcripts are searched (64 MiB,
      newest first). Why: a teammate or task message reads like the user and is not; handovers cite
      approvals from the session before. With no transcript and no decision log readable a quote
      passes unverified. Pinned by: tests/test_approval_claim_guard.py::test_a_quote_only_a_teammate_sent_is_not_the_users_words,
      tests/test_approval_claim_guard.py::test_a_quote_typed_in_an_earlier_session_of_the_project_passes,
      tests/test_approval_claim_guard.py::test_an_unchosen_ask_user_question_option_is_not_the_users_words,
      tests/test_approval_claim_guard.py::test_a_quote_passes_unverified_when_no_transcript_is_readable
    - A plan approved in plan mode (ExitPlanMode's success result) counts when the entry names the
      plan's file. Why: the approval is a click, so there are no words to quote. Pinned by:
      tests/test_approval_claim_guard.py::test_a_plan_approved_in_plan_mode_passes_when_the_entry_names_its_file,
      tests/test_approval_claim_guard.py::test_a_plan_the_user_rejected_in_plan_mode_does_not_pass
    - MY READING, NOT A USER DECISION (the user asked for duty 2 in these words, umlauts written as ASCII: "das soll aber auch
      Benutzerangaben kritisch pruefen - wenn diese schaedlich sind, darauf hinweisen und den
      Benutzer eine Empfehlung aussprechen, mit Begruendung"; how it is built was not put to the
      user): duty 2 is ADVISORY (additionalContext), never a block, and fires only when the claim
      outside its quotes holds a widening word (approval_claims._WIDEN) or an iron-rule area
      (approval_claims._IRON: secrets or credentials, a public push or release, a force push,
      deleting data or history, AI attribution) that the evidence does not itself name. An area the
      user's own words name raises nothing. Why: the user named the claim's scope; a block on what
      the user said would override the user. Replayed: 1 advisory in 7,418 writes (9 in the wider
      draft). Reopen if: the user rules otherwise. Pinned by:
      tests/test_approval_claim_guard.py::test_a_claim_reaching_past_its_quote_gets_an_advisory_not_a_block,
      tests/test_approval_claim_guard.py::test_a_claim_touching_an_iron_rule_area_the_quote_never_named_gets_an_advisory,
      tests/test_approval_claim_guard.py::test_a_claim_naming_only_what_the_quote_names_gets_no_advisory
    - Commit messages are judged at PreToolUse Bash (the `git commit -F` / `-m` call), not when the
      message file is written. Why: a message file has no fixed name, so only the commit call says a
      file is one; the commit is refused before it runs. Pinned by:
      tests/test_approval_claim_guard.py::test_a_commit_message_file_with_a_paraphrase_is_refused_without_echoing_it
    - The backlog_add tool is judged in mod_bridge.py. Why: probed 2026-11-20 on CLI 2.1.329, a
      settings PreToolUse/PostToolUse hook matching mcp__bitranox__backlog_list never fired while a
      Bash hook in the same settings did. The bridge finds the transcript by CLAUDE_CODE_SESSION_ID;
      whether the mod process inherits it was not measured, and without it a quote passes
      unverified. Pinned by: tests/test_approval_claim_guard.py::test_backlog_add_refuses_a_bare_paraphrase
    - A shell command's OPEN-WORK.md and handover.md candidates come from their own function,
      `approval_candidates`, and `candidates` keeps finding review logs only; `shell_candidates`
      joins the two for the Bash snapshot and judge. A path the command names goes through
      shell_text.msys_drive_path_for_tool first, so on Windows Git Bash's `/c/...` is drive C and
      a mount (`/tmp/...`) names no candidate. Why: the review-log reader is changed by other work
      on its own schedule; keeping the approval files out of it keeps the two from colliding.
      Pinned by: tests/test_approval_claim_guard.py::test_review_log_candidates_stay_review_logs_only,
      tests/test_approval_claim_guard.py::test_a_git_bash_drive_path_to_a_handover_is_read_as_its_drive,
      tests/test_approval_claim_guard.py::test_a_git_bash_mount_path_to_a_backlog_names_no_candidate

Fails open: any error allows the write (exit 0). A PreToolUse refusal is exit 2 through
shell_text.refuse (reason and the whole-call footer on stderr); a PostToolUse refusal is exit 0
with {"decision": "block", "reason": ...} on stdout, because the command already ran and the
footer would say it did not. Claude reads both mid-turn.
"""

from __future__ import annotations

import collections
import dataclasses
import hashlib
import importlib.util
import json
import os
import re
import sys
from pathlib import Path

import approval_claims
import claude_paths
import shell_text
from decision_claims import (MARKER, TRIGGER, Entry, decision_logs, entries, find_hits,
                             iter_records, marker_terms, triggered_entries)
from decision_claims import counts as _counts

__all__ = ["TRIGGER", "MARKER", "entries", "judge", "main"]

REVIEW_NAME = "EXECUTION-USER-REVIEW.md"
_STATE_DIR = "decision-claim-guard"
_WRITE_TOOLS = frozenset({"Write", "Edit", "MultiEdit"})
_SHELL_TOOLS = frozenset({"Bash", "PowerShell"})
_POST_TOOLS = frozenset({"Bash", "PowerShell", "Monitor"})
_MAX_BYTES = 16 * 1024 * 1024          # a watched file beyond this is not judged at all
_HEAD_MAX = 100
_RECENT = 8
_SHOWN = 3

_PATH_IN_TEXT = re.compile(r"[^\s'\"`;|&<>()=]*" + re.escape(REVIEW_NAME), re.IGNORECASE)
_APPROVAL_NAMES = ("OPEN-WORK.md", "handover.md")
_APPROVAL_PATH_IN_TEXT = re.compile(
    r"[^\s'\"`;|&<>()=]*(?:" + "|".join(re.escape(n) for n in _APPROVAL_NAMES) + ")", re.IGNORECASE)
_COMMIT_SWEEP = "commit-tell-sweep.py"
_GIT_MESSAGE = re.compile(r"\bgit\b[\s\S]*(?:\s-\w*[mF]|--message|--file)")


@dataclasses.dataclass(frozen=True)
class Problem:
    """Why one entry is refused."""

    entry: Entry
    kind: str            # "no-marker" | "bad-term" | "hit"
    detail: str


def judge(entry: Entry, logs: list[Path]) -> Problem | None:
    """The reason `entry` is refused, or None when its markers check out. PURE but for `logs`."""
    terms, bad = marker_terms(entry)
    if not terms:
        return Problem(entry, "no-marker", "")
    if bad is not None:
        return Problem(entry, "bad-term", bad)
    for term in terms:
        hits = find_hits(term, logs)[::-1]             # the most recent answer first
        if hits:
            shown = [dataclasses.asdict(h) for h in hits[:_SHOWN]]
            return Problem(entry, "hit", json.dumps({"hits": shown, "more": len(hits) - len(shown)}))
    return None


def _recent(logs: list[Path]) -> list[str]:
    tail = collections.deque(maxlen=_RECENT)
    for record in iter_records(logs):
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


@dataclasses.dataclass(frozen=True)
class Outcome:
    """What one hook run found: a refusal to show the model, an advisory, or neither."""

    refusal: str | None = None
    advice: str | None = None


def _event_cwd(event: dict) -> Path | None:
    return Path(event["cwd"]) if isinstance(event.get("cwd"), str) else None


def _words(event: dict, logs: list[Path]) -> approval_claims.WordSource:
    raw = event.get("transcript_path")
    return approval_claims.WordSource(Path(raw) if isinstance(raw, str) and raw else None, logs)


def judge_approvals(flagged: list[Entry], logs: list[Path], words: approval_claims.WordSource,
                    where: str, echo: bool = True) -> Outcome:
    """Duty 1 (refuse) and duty 2 (advise) for each entry holding an approval claim."""
    refusals, advice = [], []
    for entry in flagged:
        verdict = approval_claims.judge(entry, logs, words)
        if verdict.problem is not None:
            refusals.append(approval_claims.explain(verdict, logs, where, echo))
            continue
        found = approval_claims.concerns(verdict)
        if found:
            advice.append(approval_claims.advice_text(verdict, found, where, echo))
    return Outcome("\n\n".join(refusals) or None, "\n\n".join(advice) or None)


def _judge_review(text: str, before: collections.Counter[str], path: Path, cwd: Path | None) -> list[str]:
    flagged = triggered_entries(text, before)
    logs = decision_logs(path.parent, cwd) if flagged else []
    problems = [p for p in (judge(e, logs) for e in flagged) if p is not None] if logs else []
    return [explain(p, logs, str(path)) for p in problems]


def _judge_target(text: str, before: collections.Counter[str], path: Path, event: dict) -> Outcome:
    flagged = triggered_entries(text, before, approval_claims.APPROVAL)
    if not flagged:
        return Outcome()
    logs = decision_logs(path.parent, _event_cwd(event))
    return judge_approvals(flagged, logs, _words(event, logs), str(path))


def on_write(event: dict) -> Outcome:
    tool_input = event.get("tool_input") or {}
    raw = tool_input.get("file_path")
    if not isinstance(raw, str) or not (_is_review(raw) or approval_claims.is_target(raw)):
        return Outcome()
    path = _resolve(raw, event.get("cwd"))
    current = _read(path)
    if current is None:
        return Outcome()
    before, after = _proposed(tool_input, current, event.get("tool_name"))
    if not _is_review(raw):
        return _judge_target(after, _counts(before), path, event)
    return Outcome("\n\n".join(_judge_review(after, _counts(before), path, _event_cwd(event))) or None)


# ---- git commit messages (PreToolUse Bash) ----------------------------------------------------


def _commit_sweep():
    """commit-tell-sweep.py, loaded once: it owns reading a git command's messages (-m, -F, stdin)."""
    name = "_dcg_commit_tell_sweep"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(_COMMIT_SWEEP))
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module                     # registered before exec, as a dataclass needs
        spec.loader.exec_module(module)
    return sys.modules[name]


def on_commit(event: dict) -> Outcome:
    """Judge the approval claims in the messages a git command passes inline or by -F file."""
    command = (event.get("tool_input") or {}).get("command")
    if not isinstance(command, str) or not _GIT_MESSAGE.search(command):
        return Outcome()                               # cheap test before splitting the command
    sweep = _commit_sweep()
    tool = event.get("tool_name") or "Bash"
    written, _unread = sweep.same_command_messages(command, tool)
    refusals, advice = [], []
    logs: list[Path] | None = None
    for message in sweep._messages(command, tool) + written:
        if not approval_claims.APPROVAL.search(message.text):
            continue
        if logs is None:
            logs = decision_logs(_event_cwd(event))
        entry = Entry(1, tuple(message.text.splitlines()))
        where = "commit message file %s" % message.path if message.path else "commit message"
        found = judge_approvals([entry], logs, _words(event, logs), where, echo=not message.from_file)
        refusals += [found.refusal] if found.refusal else []
        advice += [found.advice] if found.advice else []
    return Outcome("\n\n".join(refusals) or None, "\n\n".join(advice) or None)


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


def candidates(event: dict, *, os_name: str = os.name) -> list[Path]:
    """Review logs a shell command may have written: at the work roots and any path it names.

    A path the command names is a word of its shell, so it is read the way that shell reads it
    before `_resolve` places it: on a Windows host Git Bash reads `/c/repo/...` as drive C and
    `/tmp/...` through its mount table, where pathlib joined both onto the cwd's drive and named
    a file the command never wrote. `shell_text.msys_drive_path_for_tool` spells the drive, and a
    mount no reader can place is skipped. `os_name` is a parameter so tests reach the Windows
    reading on any host.
    """
    raw_cwd = event.get("cwd")
    cwd = Path(raw_cwd) if isinstance(raw_cwd, str) and raw_cwd else None
    found = [root / REVIEW_NAME for root in (_work_roots(cwd) if cwd else [])]
    command = (event.get("tool_input") or {}).get("command")
    if isinstance(command, str) and REVIEW_NAME.lower() in command.lower():
        tool = event.get("tool_name") if isinstance(event.get("tool_name"), str) else "Bash"
        for m in _PATH_IN_TEXT.finditer(command):
            word = shell_text.msys_drive_path_for_tool(m.group(0), tool, os_name)
            if word is not None:
                found.append(_resolve(word, raw_cwd))
    unique = []
    for path in found:
        if path not in unique:
            unique.append(path)
    return unique[:8]


def approval_candidates(event: dict, *, os_name: str = os.name) -> list[Path]:
    """Backlogs and handovers a shell command may have written: at the work roots and any it names.

    Kept apart from `candidates` (the review-log reader) so the two rules can change separately.
    A path the command names is a word of its shell, so it is read the way that shell reads it
    before `_resolve` places it: on Windows Git Bash reads `/c/repo/...` as drive C and `/tmp/...`
    through its mount table, where pathlib alone would name a file the command never wrote.
    `os_name` is a parameter so tests reach the Windows reading on any host.
    """
    raw_cwd = event.get("cwd")
    cwd = Path(raw_cwd) if isinstance(raw_cwd, str) and raw_cwd else None
    found = [root / name for root in (_work_roots(cwd) if cwd else []) for name in _APPROVAL_NAMES]
    command = (event.get("tool_input") or {}).get("command")
    if isinstance(command, str) and any(n.lower() in command.lower() for n in _APPROVAL_NAMES):
        tool = event.get("tool_name") if isinstance(event.get("tool_name"), str) else "Bash"
        for m in _APPROVAL_PATH_IN_TEXT.finditer(command):
            word = shell_text.msys_drive_path_for_tool(m.group(0), tool, os_name)
            if word is not None:
                found.append(_resolve(word, raw_cwd))
    return list(dict.fromkeys(found))[:8]


def shell_candidates(event: dict) -> list[Path]:
    """Every watched file a shell command may have written: review logs, then approval files."""
    return list(dict.fromkeys(candidates(event) + approval_candidates(event)))


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
    for path in shell_candidates(event):
        signature = _signature(path)
        state = _load_state(path)
        if state is not None and state.get("sig") == signature:
            continue
        text = _read(path) if signature is not None else ""
        if text is not None:
            _save_state(path, signature, text)


def on_shell_post(event: dict) -> Outcome:
    """Judge the lines the command added to each candidate file; store the new state either way."""
    cwd = _event_cwd(event)
    messages, advice = [], []
    for path in shell_candidates(event):
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
        if _is_review(str(path)):
            messages += _judge_review(text, before, path, cwd)
            continue
        found = _judge_target(text, before, path, event)
        messages += [found.refusal] if found.refusal else []
        advice += [found.advice] if found.advice else []
    if not messages:
        return Outcome(advice="\n\n".join(advice) or None)
    return Outcome("\n\n".join(messages + advice) + (
        "\n\nThe file was already written by that command: fix the entry now (Edit the file), "
        "then go on."))


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:  # noqa: BLE001 - no or invalid stdin: nothing to judge
        return 0
    if not isinstance(event, dict):
        return 0
    tool, hook = event.get("tool_name"), event.get("hook_event_name")
    if hook == "PreToolUse" and tool in _WRITE_TOOLS:
        found = on_write(event)
    elif hook == "PreToolUse" and tool in _SHELL_TOOLS:
        on_shell_pre(event)
        found = on_commit(event)
    elif hook == "PostToolUse" and tool in _POST_TOOLS:
        found = on_shell_post(event)
        if found.refusal:
            # The command already ran, so the shared refusal footer ("NOTHING in this call ran")
            # would be false here: PostToolUse blocks through its own decision field instead.
            sys.stdout.write(json.dumps({"decision": "block", "reason": found.refusal}) + "\n")
            return 0
    else:
        return 0
    if found.refusal:
        return shell_text.refuse(found.refusal)
    if found.advice:
        sys.stdout.write(json.dumps({"hookSpecificOutput": {
            "hookEventName": hook, "additionalContext": found.advice}}) + "\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - a broken guard must never wedge a turn
        sys.exit(0)
