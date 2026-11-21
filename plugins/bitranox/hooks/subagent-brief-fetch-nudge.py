#!/usr/bin/env python3
"""PreToolUse(Task|Agent) nudge: a brief that reads state across repos must say to fetch first.

A local checkout, and every ref in it, describes the LAST FETCH, not origin. A subagent briefed to
report or compare the state of several repositories (sibling clones, the templates and their
consumers, "for each repo") reads each working tree and returns a confident, precise, wrong answer:
nothing in a version floor or a file listing says how old the clone is. Measured 2026-11-18: a
report built from local checkouts said both bitranox templates still floored and locked
lib_cli_exit_tools 2.4.1; after a fetch origin had >=2.5.0 (the clones were 4 and 5 commits behind).
Memory fact `reference-ahead-behind-answers-against-the-last-fetch-so-a-stale-clone-reports-a-
confident-wrong-number`, recurrence 3.

WHY A BRIEF CHECK. The subagent follows the read it is told to do, and nothing at its own Bash
call can tell a stale clone from a fresh one; `git-footgun-guard` sees `@{u}` only once someone
types it. The fix belongs where the instruction is written, which is the dispatch.

WHAT COUNTS. The brief is prose, read as prose: the Agent `prompt`, plus up to three files it
points at whose NAME says "brief" (.md/.txt, each read up to 256 KiB), since "read your brief at
<path>" is a common shape. A hit in a file is reported by file and line, never quoted: the hook
reads it before the call is approved. Each paragraph (a hard-wrapped run of lines, or one list
item) is split into sentences, and a sentence fires on one of these arms:

* each / all / across / sibling: a sweep over repositories ("for each repo", "in each of the 3
  repos", "each template", "both templates", "clone both repos", "across the sibling repos", "grep
  the code in sibling repos") together with a READ word in the same sentence (read, list, grep,
  compare, diff, which, whether, still, clone, audit, ...).
* which: "which (of the) repos / templates / clones" - itself a question about their state.
* dependents: the other repos named by what they depend on ("CLIs built on lib_x", "apps that
  use lib_y", "the templates and their consumers") - the 2026-11-18 brief's own shape. It named no
  repo and no read verb ("That CLIs built on lib_cli_exit_tools run_cli get the broken-pipe fix on
  their next dependency resolve: state it"); its subagent grepped every pyproject.toml in the tree.

Anything in the brief that fetches or reads origin silences it: `git fetch`/`git pull`, any form of
"fetch", `@{u}`, `origin/`, "origin's", `ls-remote`, `gh api`, `--fetch`, or a `git clone` of a URL.

Decisions:
    - The read word must sit in the SAME SENTENCE as the sweep, not just the same paragraph. Why:
      write fan-outs ("put the file at X in each node repo") carry a read word elsewhere in the
      paragraph. Evidence: measured, replay 2026-11-19: paragraph scope fired 11, sentence scope 8;
      the 3 dropped were 2 false positives (a write fan-out, a repro copy) and 1 real read
      ("Each machine repo carries a copy of X; check how ..."). Reopen if: a replay shows real
      cross-sentence reads outnumbering the write fan-outs. Pinned by:
      tests/test_subagent_brief_fetch_nudge.py::test_the_read_word_must_share_the_sentence_with_the_scope
    - "consumer" is not a repo noun, and "template"/"clone" stop counting before a code noun
      (placeholder, string, URL, ...). Why: "every consumer of the model" and "every template
      placeholder" are code senses. Evidence: measured, a first draft with bare consumer, fleet
      and sibling arms and no read word fired on 122 dispatches (3.45 percent); a random 40 of
      them, read by hand, were mostly code-sense consumers, host-fleet mentions and layout notes.
      Reopen if: never; a downstream-repo sense has its own arm (dependents). Pinned by:
      tests/test_subagent_brief_fetch_nudge.py::test_prose_that_is_not_a_cross_repo_read_is_silent
    - The sibling arm needs a preposition before "sibling repos" (in, from, of, across). Why: the
      E2E suite's briefs say its "tests resolve sibling repos via parents[2]", a layout fact; a
      bare "sibling repos" arm fired 18 times on it. With the preposition an extra erasure of
      "resolve sibling repos" changed no firing (measured: 8 with it, the same 8 without), so
      there is none. Evidence: measured. Reopen if: never. Pinned by:
      test_prose_that_is_not_a_cross_repo_read_is_silent
    - The dependents arm needs no read word. Why: the incident brief has none. Evidence: measured
      (the brief above). Reopen if: the arm's share of false positives grows past its real ones.
      Pinned by: test_the_2026_11_18_incident_brief_fires_on_the_dependents_arm
    - Rejected: a bare "fleet", "consumers", "both repos", or "tree-wide" arm. Why: "fleet" is the
      host fleet, "consumers" the code sense, "both repos" a report of the agent's own two commits,
      and the one "tree-wide" firing was a sweep of untracked CLAUDE.md files, which have no origin
      to read. Evidence: measured, each arm's firings read by hand. Reopen if: a real incident
      brief uses one of them.
    - Task|Agent only, not SendMessage. Why: a follow-up message rarely re-scopes a task; the
      pyright nudge, the closest sibling, made the same call. Evidence: argued. Reopen if: an
      incident's cross-repo read was asked in a SendMessage. Pinned by:
      tests/test_subagent_brief_fetch_nudge.py::test_non_subagent_tools_are_silent

THE REPLAY (2026-11-19), over every Task/Agent tool_use under ~/.claude/projects (rglob, deduped by
tool_use id): 4827 dispatches, 3538 judged (the rest probe types or an empty prompt), brief files
read as they are now. 8 fire (0.23 percent). All 8 read by hand: 7 real (the 2026-11-18 incident
brief; "for each template: its CLAUDE.md section headings"; "in each of the 3 repos: where the
files live"; mirrored twins "in sibling repos" via repo-gate --mirrors, which reads refs as of the
last fetch and never fetches; "grep the code in sibling repos"; two "clone each/both repos with git
clone --no-local", which copies the local checkout) and 1 false positive (a fix round told to grep
each repo for a string it is itself fixing on its own branches). Re-run the replay with the
predicate `cross_repo_hit` before widening an arm.

Non-blocking by design: additionalContext only, never a permissionDecision. Fail-open: any error ->
print nothing, exit 0 (a broken hook must never wedge a dispatch). Memory is bounded: each brief
file is read up to a byte cap. Pure standard library; launched via run-python.sh so it works on
Windows too. ASCII only.
"""

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from hook_event import parse_pre_tool_use

SUBAGENT_TOOLS = {"Task", "Agent"}

# Kept character-identical to the copies in subagent-brief, subagent-probe-capability-gate,
# subagent-backstop-nudge and subagent-brief-must-not-nudge; tests/test_subagent_dispatch_hooks.py
# pins all of them together.
CLEAN_ROOM_MARKERS = ("baseline-probe", "probe-effort")

BRIEF_FILE_CAP = 256 * 1024
MAX_BRIEF_FILES = 3
EXCERPT = 70                         # characters of context on each side of an inline hit

BRIEF_PATH = re.compile(r"(?:[A-Za-z]:)?[/\\][^\s'\"`<>|]*brief[^\s'\"`<>|/\\]*\.(?:md|txt)",
                        re.IGNORECASE)

# Words that may stand between the sweep word and the repo noun ("each of the 3 node repos").
_QUAL = (r"(?:sibling|consumer|derived|downstream|bitranox|public|private|affected|other|template"
         r"|python|cli|local|node|machine|rotek|the)")
# A repository noun. "template" and "clone" stop counting before a code noun; "consumer" is never
# one (it is the code sense far more often, see the Decisions block).
_NOUN = (r"(?:repo(?:sitor(?:y|ies))?s?"
         r"|clones?(?!\s+(?:url|urls|command|step)\b)"
         r"|checkouts?"
         r"|templates?(?!\s+(?:placeholder|string|variable|var|literal|engine|file|text|key|field|tag"
         r"|parameter|argument|name|section|line)s?\b))")
_PLURAL = r"(?:repo(?:sitor(?:ies|y))?s|clones|checkouts|templates)"


@dataclass(frozen=True)
class Arm:
    """One way a sentence can ask for a cross-repo read; `needs_read` adds the READ-word test."""

    name: str
    pattern: re.Pattern[str]
    needs_read: bool


ARMS = (
    Arm("each", re.compile(
        r"\b(?:for\s+)?(?:each|every)\s+(?:one\s+)?(?:of\s+(?:the\s+)?)?"
        r"(?:\d+\s+|two\s+|three\s+|four\s+|five\s+)?(?:%s\s+){0,2}%s(?!['\u2019]s)" % (_QUAL, _NOUN),
        re.IGNORECASE), True),
    Arm("all", re.compile(
        r"\b(?:all\s+(?:(?:of\s+)?the\s+)?(?:\d+\s+)?(?:%s\s+){0,2}%s"
        r"|both\s+(?:of\s+)?(?:the\s+)?(?:%s\s+){0,2}templates"
        r"|clone\s+both\s+(?:the\s+)?repo(?:sitorie)?s)\b" % (_QUAL, _PLURAL, _QUAL),
        re.IGNORECASE), True),
    Arm("across", re.compile(
        r"\bacross\s+(?:the\s+|all\s+(?:the\s+)?|\d+\s+|several\s+|many\s+|multiple\s+)?"
        r"(?:%s\s+){0,2}%s\b" % (_QUAL, _PLURAL), re.IGNORECASE), True),
    Arm("sibling", re.compile(
        r"\b(?:in|from|of|across)\s+(?:the\s+)?sibling\s+(?:repo(?:sitor(?:ies|y))?s|clones|checkouts)\b",
        re.IGNORECASE), True),
    Arm("which", re.compile(
        r"\b(?:which|how\s+many)\s+(?:of\s+the\s+)?(?:%s\s+){0,2}%s\b" % (_QUAL, _PLURAL),
        re.IGNORECASE), False),
    Arm("dependents", re.compile(
        r"\b(?:CLIs|apps|applications|projects|repos|repositories|libraries|packages|tools|services)"
        r"\s+(?:that\s+are\s+)?(?:built\s+on|that\s+(?:use|depend\s+on|import|pin|floor)|depending\s+on)"
        r"\s+[`\"']?[A-Za-z][\w.-]*"
        r"|\btemplates?\s+and\s+(?:their|its)\s+(?:consumers|copies|descendants)\b",
        re.IGNORECASE), False),
)

READ = re.compile(
    r"\b(?:list|lists|listing|read(?!-only)|reads|reading|grep|greps|grepping|compare[sd]?|comparing"
    r"|diff(?:s|ing)?|inventor(?:y|ies)|survey|audit|count|collect|gather|which|whether|still|clone"
    r"|cloning|find|where\s+\w+\s+(?:live|lives|is|are))\b",
    re.IGNORECASE)

FETCH = re.compile(
    r"\bgit\s+(?:-C\s+\S+\s+)?(?:fetch|pull)\b|\bfetch(?:ed|es|ing)?\b|@\{u(?:pstream)?\}|\borigin/"
    r"|\borigin['\u2019]s\b|ls-remote|\bgh\s+api\b|--fetch\b"
    r"|\bgit\s+clone\s+(?:\S+\s+)*?(?:https?://|ssh://|git@)",
    re.IGNORECASE)

# Where a new paragraph starts in a hard-wrapped Markdown brief: a list item or a heading. Every
# other non-blank line continues the one above, so a sentence wrapped across lines is read whole.
_NEW_PARAGRAPH = re.compile(r"^\s*(?:[-*+]\s|\d+[.)]\s|#)")
_SENTENCE_END = re.compile(r"(?<=[.;:!?])\s+(?=[A-Z0-9(`])")

_ADVICE = (
    "Brief check (stale clone). This brief asks the subagent to read or compare state across "
    "several repositories{where} and nowhere says to fetch. A local checkout and its refs describe "
    "the last fetch, not origin, so a report built from them comes back confident and wrong (on "
    "2026-11-18 such a report named a version floor that origin had already raised; the clones were "
    "4 and 5 commits behind). The subagent reads what its brief tells it to read, so the line that "
    "prevents this belongs in the brief: git fetch each repo first and read origin's state "
    "(git show @{{u}}:<path>, origin/<branch>), never the working tree. This brief has already gone "
    "out; a correction would go by SendMessage."
)


@dataclass(frozen=True)
class Hit:
    """The arm that fired and where: an inline excerpt, or "<file> line N" for a brief file."""

    arm: str
    where: str


def paragraphs(text: str):
    """Yield (first line number, paragraph) for hard-wrapped Markdown text. PURE."""
    current: list[str] = []
    start = 0
    for number, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if not stripped or _NEW_PARAGRAPH.match(line):
            if current:
                yield start, " ".join(current)
            current, start = ([stripped], number) if stripped else ([], 0)
        elif current:
            current.append(stripped)
        else:
            current, start = [stripped], number
    if current:
        yield start, " ".join(current)


def _sentence_hit(sentence: str) -> tuple[str, re.Match[str]] | None:
    for arm in ARMS:
        match = arm.pattern.search(sentence)
        if match is None:
            continue
        if arm.needs_read and READ.search(sentence) is None:
            continue
        return arm.name, match
    return None


def _first_hit(text: str):
    """(arm, line number, sentence, match) of the first firing sentence in `text`, else None."""
    for number, para in paragraphs(text):
        for sentence in _SENTENCE_END.split(para):
            found = _sentence_hit(sentence)
            if found is not None:
                return found[0], number, sentence, found[1]
    return None


def _excerpt(sentence: str, match: re.Match[str]) -> str:
    start = max(0, match.start() - EXCERPT)
    return " ".join(sentence[start:match.end() + EXCERPT].split())


def brief_files(text: str) -> list[Path]:
    """Up to MAX_BRIEF_FILES existing files the brief points at whose name says "brief"."""
    found: list[Path] = []
    for raw in BRIEF_PATH.findall(text or ""):
        path = Path(raw.rstrip(".,:;)"))
        if path in found or not path.is_file():
            continue
        found.append(path)
        if len(found) == MAX_BRIEF_FILES:
            break
    return found


def _read_head(path: Path) -> str | None:
    try:
        with open(path, "rb") as handle:
            return handle.read(BRIEF_FILE_CAP).decode("utf-8", errors="replace")
    except OSError:
        return None


def cross_repo_hit(prompt, files=()) -> Hit | None:
    """The first cross-repo read in a brief that never says to fetch, else None.

    `files` are (name, text) pairs of brief files the prompt points at; a fetch line anywhere in the
    prompt or a file silences the whole brief. PURE. A non-string prompt answers None.
    """
    if not isinstance(prompt, str) or not prompt.strip():
        return None
    if FETCH.search(prompt) or any(FETCH.search(body) for _, body in files):
        return None
    found = _first_hit(prompt)
    if found is not None:
        arm, _, sentence, match = found
        return Hit(arm, repr(_excerpt(sentence, match)))
    for name, body in files:
        found = _first_hit(body)
        if found is not None:
            return Hit(found[0], f"{name} line {found[1]}")
    return None


def assess(tool_name, tool_input) -> str | None:
    """The advice for a dispatch whose brief reads across repos without a fetch, else None."""
    if not isinstance(tool_name, str) or tool_name not in SUBAGENT_TOOLS:
        return None
    if not isinstance(tool_input, dict):
        return None
    atype = str(tool_input.get("subagent_type") or "").lower()
    if any(marker in atype for marker in CLEAN_ROOM_MARKERS):
        return None
    prompt = tool_input.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        return None
    files = []
    for path in brief_files(prompt):
        body = _read_head(path)
        if body is not None:
            files.append((path.name, body))
    hit = cross_repo_hit(prompt, files)
    if hit is None:
        return None
    return _ADVICE.format(where=f" (near: {hit.where})")


def main() -> int:
    try:
        event = parse_pre_tool_use(json.load(sys.stdin))
    except Exception:  # noqa: BLE001 - no/invalid stdin: do nothing
        return 0
    if event is None:
        return 0
    message = assess(event.get("tool_name"), event.get("tool_input"))
    if message:
        sys.stdout.write(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": message,
        }}) + "\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - a broken hook must never wedge a turn
        sys.exit(0)
