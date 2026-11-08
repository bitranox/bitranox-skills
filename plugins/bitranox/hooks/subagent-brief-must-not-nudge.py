#!/usr/bin/env python3
"""PreToolUse(Task|Agent|SendMessage) nudge: a Must-NOT line in a brief must be the user's words.

A subagent cannot see the question the user answered, so the controller's relay IS the requirement.
Five times a controller wrote a "Must NOT" line into a brief that paraphrased, widened or invented a
constraint the user never stated, and the subagent built and green-tested the paraphrase (memory
fact `feedback-relay-a-user-decision-verbatim-with-its-negative-case-never-a-paraphrase`). The
capture half exists: `user-decision-log` keeps every AskUserQuestion answer in USER-DECISIONS.jsonl.
This hook covers the RELAY half, the lines the controller writes into a brief.

WHAT IT READS. The brief is the Agent `prompt` or the SendMessage `message` (a string; a structured
message is a protocol reply, not a brief). A SendMessage to `main` is a subagent reporting back, not
a brief, and is skipped; a dispatch to a probe type (`baseline-probe`, `probe-effort`) is skipped,
with the same markers the other subagent hooks use. A brief that only says "read your brief at
<path>" is the common shape, so a referenced file whose NAME contains "brief" (.md/.txt, at most
three, each capped) is read too; a hit there is reported by file and line number, never quoted,
because the hook reads it before the call is approved.

THE SOURCES, at the root of the MAIN checkout of the event cwd's repository (the same resolution as
`user-decision-log`, falling back to its audit-dir file outside a repository):

* USER-DECISIONS.jsonl: each record's question, every option's label and description (a Must NOT is
  most often "do the option the user rejected", so rejected options count) and the user's notes.
* EXECUTION-USER-REVIEW.md: decisions the user typed in CHAT are in no jsonl; the controller is
  told to quote them in this file, so without it every chat decision would read as invented. Every
  "(my reading)" span in it is cut out before matching, since a brief line that matches the
  controller's own inference is exactly the defect. The cost, accepted: this file also holds the
  controller's autonomous decisions, so a Must-NOT copied from one of those passes silently.

THREE FINDINGS, each on one paragraph of the brief (a brief is hard-wrapped Markdown, so a list
item or a run of lines up to a blank line is one unit, cited by the line it starts on):

* my-reading: a must-not paragraph labelled as the controller's reading ("(my reading)", "My
  reading:", "Coordinator's reading:"; a label inside double quotes is a mention, not a label).
  The controller's inference is not a user constraint: ask it as a question, or drop it.
* relayed-reading: a NEGATIVE "(my reading)" note from EXECUTION-USER-REVIEW.md ("(my reading) no new
  dependency") appears in the brief, as whole words, outside double quotes and WITHOUT its label.
  This is the 2026-11-03 datamax-dpl incident exactly: the note was logged correctly and the brief
  file said "No size cap as the fix, no new dependency." - no must-not word at all, so a
  marker-keyed check alone cannot see it.
* untraced: a must-not LABEL paragraph ("Must NOT: ...", "- MUST NOT TOUCH (from ...): ...") with no
  reading label whose text is not found in either source.

THE MATCHING RULE for untraced. Text is normalized (case folded, curly quotes straightened, markdown
emphasis and backticks dropped, whitespace collapsed). The paragraph after its label traces when
every clause (split on the ";" outside double quotes) passes one of: a double-quoted span of 3+
words found verbatim in a source; the clause itself found verbatim; or 75 percent of its content
words present in ONE decision record or review paragraph (per record, so a large log cannot answer
yes from scattered common words; 75 rather than 80 lets a four-word relay drop its prohibition verb,
"change the port 9100 default", and the replay's firing set was identical at both). A clause of
under two content words is never judged. Only a LABEL counts, the marker first ("Behaviour must not
change:" is the controller's own engineering rule).

THE REPLAY (2026-11-04), over every Agent/SendMessage tool_use under ~/.claude/projects (rglob,
deduped by tool_use id): 6285 dispatches, 4868 judged (the rest: probes, reports to `main`,
structured messages), 540 carrying a must-not marker, 729 pointing at a brief file. Each was judged
against its repository's USER-DECISIONS.jsonl cut to records older than the dispatch, and against
EXECUTION-USER-REVIEW.md twice: as it is now (what a live dispatch sees) and cut to paragraphs
dated no later than the dispatch day; both arms give the same firing set. Judging every marker paragraph, as first drafted, fired on
428 briefs (8.8 percent of judged, 79 percent of marker briefs); a seeded sample of 10 was 10 false
alarms, each the controller's own engineering rule or a reviewer's question. The shipped rule
fires on 4 briefs (0.08 percent), all four adjudicated real against their sources:

* datamax-dpl 2026-11-02, SendMessage `fix6`: "Must NOT change: a batch ... is refused BEFORE ANY
  BYTE ..., so the check pass runs over all records first" - the review log later records that the
  two passes were "my shortcut to 'refuse before any byte', not a requirement" after the user asked
  "why ? I dont see any reason ?".
* datamax-dpl 2026-11-03, Agent `perf020-impl`, brief-020-impl.md: the "(my reading) no new
  dependency" relay above (relayed-reading).
* soundtouch-zonemaster 2026-10-12, task-10-fix8-brief.md: "MUST NOT TOUCH: a box that ANSWERS and
  is not clearly awake ... still ends 130" - recurrence 3 of the memory fact, the added qualifier
  that widened the user's "a Ctrl-C ... that leaves an asleep box".
* soundtouch-zonemaster 2026-10-12, task-11-build-brief.md: a verbatim quote of the user's option
  followed, in the same Must-NOT, by cases the option does not state ("a repeating alarm saved
  DISABLED is not refused (it is checked when enabled)").

The tuning steps, each removing a class seen in the firings: no leading word before the marker
(two allowed fired on "Behaviour must not change:" and "The Must NOT lines:"), paragraphs instead
of physical lines (a wrapped sentence whose second line opened "must not break:" read as a label,
and a Must-NOT the log held, split at its wrap, read as untraced), a quote-aware ";" split, a
length cap on a quoted span (a lone quote from an escaped `\"` swallowed the line), whole-word
note matches outside quotes ("no code change" inside "no code changes", a brief quoting the log),
the broader reading label ("Coordinator's reading:" read as unlabelled), and the topic overlap a
relayed note needs (see `relayed_reading`: a short note is a common phrase). What the replay cannot see: a brief file rewritten since its
dispatch is judged as it is now, and the my-reading arm fired on nothing in the corpus (its only
pre-tuning firing was a brief describing this rule, which the quoted-label rule now passes).
Re-run the replay with the predicate `findings` before widening any arm.

WHEN THE CONTROLLER SEES IT. Probed on CLI 2.1.318 with a nonce per tool: PreToolUse
additionalContext on Agent and on SendMessage reaches the controller (it wrote both nonces to a file
it was told to fill with what it saw), and the transcript records it as a `hook_additional_context`
attachment before the tool_result, read on the next model request - so the brief has already gone
out, and the advice says a correction goes by SendMessage.

Non-blocking by design: additionalContext only, never a permissionDecision. Fail-open: any error ->
print nothing, exit 0 (a broken hook must never wedge a dispatch). Memory is bounded: each source
is read up to a byte cap (newest part), each brief file too. Pure standard library; launched via
run-python.sh so it works on Windows too. ASCII only.
"""

import json
import re
import sys
from pathlib import Path

import claude_paths
from self_improve_signals import main_checkout_root, project_slug

SUBAGENT_TOOLS = {"Task", "Agent"}
MESSAGE_TOOL = "SendMessage"

# Kept character-identical to the copies in subagent-brief, subagent-probe-capability-gate and
# subagent-backstop-nudge; tests/test_subagent_dispatch_hooks.py pins all of them together.
CLEAN_ROOM_MARKERS = ("baseline-probe", "probe-effort")

DECISIONS_NAME = "USER-DECISIONS.jsonl"
REVIEW_NAME = "EXECUTION-USER-REVIEW.md"
SOURCE_CAP = 2 * 1024 * 1024        # bytes read from each source: the newest part
BRIEF_FILE_CAP = 256 * 1024
MAX_BRIEF_FILES = 3
MAX_REPORTED = 3                     # findings named in the advice; the rest are counted
LINE_EXCERPT = 100
COVERAGE = 0.75
MIN_QUOTE_WORDS = 3
TOPIC_OVERLAP = 6                    # see relayed_reading

MARKER = re.compile(r"\bmust[\s-]*not\b|\bmustn['\u2019]?t\b", re.IGNORECASE)
# The label that marks the controller's own inference. The house spelling is "(my reading)", but
# a brief also writes "My reading:" or "Coordinator's reading:" (the replay found a relay labelled
# that way and flagged as unlabelled), so any of those counts.
_READING = r"\b(?:my|(?:the\s+)?(?:coordinator|controller)'?s)\s+reading\b"
MY_READING = re.compile(_READING, re.IGNORECASE)
# The label inside double quotes is a MENTION of it (a brief about this very rule says
# 'labelled "(my reading)"'), not a line that carries it.
_QUOTED_MY_READING = re.compile(r'"[^"\n]{0,240}' + _READING + r'[^"\n]{0,240}"', re.IGNORECASE)

# A must-not LABEL: the marker OPENS the line (after a bullet, a number or emphasis), takes up to
# two more words ("MUST NOT TOUCH") and an optional parenthetical, and ends in a colon:
# "- Must NOT (my reading): x", "MUST-NOT-TOUCH: x". No word may come first: with up to two
# allowed, "Behaviour must not change:" and "The Must NOT lines:" (a reviewer's question) read as
# relays, and both are the controller's own wording by construction. A wrapped sentence whose
# second line happens to open with "must not break:" is no label either; the paragraph reader joins
# it to the line above, so the marker no longer opens anything.
LABEL = re.compile(
    r"^\s*(?:[-*+]\s+|\d+[.)]\s+)?[*_`]*\s*"
    r"(?:must[\s-]*not|mustn['\u2019]?t)(?:[\s-]+\w+){0,2}[*_`]*\s*(?:\([^)]*\))?\s*[*_`]*\s*:",
    re.IGNORECASE)

# Where a new paragraph starts in a hard-wrapped Markdown file: a list item or a heading. Every
# other non-blank line continues the one above, so a sentence wrapped across two lines is read
# whole (a line-by-line read failed to find a Must-NOT the log held, split at its wrap).
_NEW_PARAGRAPH = re.compile(r"^\s*(?:[-*+]\s|\d+[.)]\s|#)")

# A negative note: what a "(my reading)" span must say for its unlabelled relay to matter.
NEGATIVE = re.compile(r"^(?:must[\s-]*not\b|no\b|never\b|not\b|do not\b|don't\b|without\b)",
                      re.IGNORECASE)

BRIEF_PATH = re.compile(r"(?:[A-Za-z]:)?[/\\][^\s'\"`<>|]*brief[^\s'\"`<>|/\\]*\.(?:md|txt)",
                        re.IGNORECASE)

_TRANSLATE = {ord(c): r for c, r in (
    ("\u2018", "'"), ("\u2019", "'"), ("\u201c", '"'), ("\u201d", '"'),
    ("\u2013", "-"), ("\u2014", "-"), ("*", None), ("`", None))}
_SPACE = re.compile(r"\s+")
_WORD = re.compile(r"[a-z0-9][a-z0-9_.-]*[a-z0-9]|[a-z0-9]")
# A double-quoted span, capped in length: a lone quote (an escaped `\"` in a code span, its
# backticks already dropped) would otherwise pair with a quote lines later and swallow the text
# between them, and the cap lets the scan move on to the next real pair instead.
_QUOTED = re.compile(r'"([^"\n]{1,240})"')
# In the review file a note is spelled the house way, "(my reading)" or "(my reading, ...)".
_PAREN_READING = re.compile(r"\(\s*my\s+reading\b[^)]*\)", re.IGNORECASE)
_MY_READING_SPAN = re.compile(_PAREN_READING.pattern + r"[^.;\n]*", re.IGNORECASE)

STOPWORDS = frozenset("""
a an the and or but nor so yet of to in on at by for with from into onto over under as is are was
were be been being it its this that these those there here than then when where which who whom
whose what why how not no must never do does did done any all each every some such only also just
very can could may might should would will shall you your we our us they their them he she his her
i me my mine if else because while about after before again same other own both either neither
""".split())


def norm(text) -> str:
    """Case-folded, quote-straightened, emphasis-free, whitespace-collapsed text. PURE."""
    return _SPACE.sub(" ", str(text).translate(_TRANSLATE).casefold()).strip()


def content_words(text) -> set:
    """The words of `text` that carry meaning: 3+ characters, not a stopword. PURE."""
    return {w for w in _WORD.findall(norm(text)) if len(w) >= 3 and w not in STOPWORDS}


class Sources:
    """The decision text a brief line may be traced to, normalized once.

    `docs` holds one entry per decision record and per review line, each as (normalized text, its
    content words); `blob` is all of them joined, for the verbatim tests; `readings` holds the
    negative "(my reading)" notes as (review line number, normalized clause).
    """

    def __init__(self, docs=(), readings=()):
        self.docs = [(norm(d), content_words(d)) for d in docs if d and str(d).strip()]
        self.blob = "\n".join(d for d, _ in self.docs)
        self.readings = list(readings)

    def __bool__(self):
        return bool(self.docs or self.readings)

    def has_verbatim(self, text) -> bool:
        needle = norm(text)
        return bool(needle) and needle in self.blob

    def covers(self, words) -> bool:
        """True when one record or line holds COVERAGE of `words`."""
        if not words:
            return False
        need = COVERAGE * len(words)
        return any(len(words & have) >= need for _, have in self.docs)


def record_text(record) -> str:
    """Everything a USER-DECISIONS record says: question, every option, chosen label, notes. PURE."""
    if not isinstance(record, dict):
        return ""
    parts = [record.get("question"), record.get("header"), record.get("chosen")]
    for option in record.get("options") or []:
        if isinstance(option, dict):
            parts += [option.get("label"), option.get("description")]
    note = record.get("annotation")
    if isinstance(note, dict):
        parts += [v for v in note.values() if isinstance(v, str)]
    elif isinstance(note, str):
        parts.append(note)
    return "\n".join(p for p in parts if isinstance(p, str))


def paragraphs(text):
    """[(first line number, the paragraph's lines joined by spaces)] of a Markdown text. PURE."""
    out, start, held = [], 0, []
    for n, line in enumerate(text.splitlines(), 1):
        if held and (not line.strip() or _NEW_PARAGRAPH.match(line)):
            out.append((start, " ".join(held)))
            held = []
        if line.strip():
            if not held:
                start = n
            held.append(line.strip() if held else line)
    if held:
        out.append((start, " ".join(held)))
    return out


def review_docs(paras):
    """Each review paragraph with every "(my reading)" span cut out: what a brief may quote. PURE."""
    return [_MY_READING_SPAN.sub(" ", text) for _, text in paras]


def negative_readings(paras):
    """[(line number, clause, topic words)] for every negative "(my reading)" note. PURE.

    The note runs from the label to the end of its sentence; it is split into clauses on ";" and
    ",", and a clause counts when it reads as a prohibition (NEGATIVE) and holds 3+ words with at
    least two content words - "no new dependency" yes, "no." no - and no quote mark (a clause that
    crosses a quote boundary is a fragment of quoted text, not a note). The topic words are the
    content words of the whole paragraph the note sits in, which `relayed_reading` needs.
    """
    out = []
    for n, line in paras:
        topic = content_words(line)
        quoted = [m.span() for m in _QUOTED.finditer(line)]
        for hit in _PAREN_READING.finditer(line):
            if any(a < hit.start() < b for a, b in quoted):
                continue                # a quoted mention of someone else's note, not a note
            rest = line[hit.end():]
            sentence = re.split(r"(?<=[.!?])\s", rest.lstrip(" :"), maxsplit=1)[0]
            sentence = re.sub(r"^chosen\s*:\s*", "", sentence.strip(), flags=re.IGNORECASE)
            sentence = re.sub(r"^must[\s-]*not\s*(?:\([^)]*\))?\s*:\s*", "must not ", sentence,
                              flags=re.IGNORECASE)
            for clause in re.split(r"[;,]", sentence):
                clause = norm(clause).strip(" .:")
                if (NEGATIVE.match(clause) and len(clause.split()) >= 3 and '"' not in clause
                        and len(content_words(clause)) >= 2):
                    out.append((n, clause, topic))
    return out


def _read_head(path, cap):
    with open(path, "rb") as handle:
        return handle.read(cap).decode("utf-8", errors="replace")


def _read_tail(path, cap):
    with open(path, "rb") as handle:
        handle.seek(0, 2)
        size = handle.tell()
        handle.seek(max(0, size - cap))
        data = handle.read()
    text = data.decode("utf-8", errors="replace")
    return text.split("\n", 1)[1] if size > cap and "\n" in text else text


def source_paths(cwd):
    """(USER-DECISIONS path, review path or None) for an event cwd, as user-decision-log writes."""
    root = main_checkout_root(cwd) if cwd else None
    if root is not None:
        return root / DECISIONS_NAME, root / REVIEW_NAME
    audit = claude_paths.audit_dir()
    return audit / (project_slug(str(cwd or "unknown")) + "." + DECISIONS_NAME), None


def load_sources(decisions_path, review_path, before=None) -> Sources:
    """The Sources at these paths; `before` (an ISO timestamp) drops decisions logged later."""
    docs, readings = [], []
    if decisions_path is not None and decisions_path.is_file():
        for line in _read_tail(decisions_path, SOURCE_CAP).splitlines():
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if before is not None and str(record.get("ts") or "") > before:
                continue
            docs.append(record_text(record))
    if review_path is not None and review_path.is_file():
        paras = paragraphs(_read_head(review_path, SOURCE_CAP))   # newest first by convention
        docs += review_docs(paras)
        readings = negative_readings(paras)
    return Sources(docs, readings)


def brief_text(tool_name, tool_input):
    """The brief a dispatch carries, or None when this call is not a brief to judge. PURE."""
    if not isinstance(tool_name, str) or not isinstance(tool_input, dict):
        return None
    if tool_name in SUBAGENT_TOOLS:
        atype = str(tool_input.get("subagent_type") or "").lower()
        if any(marker in atype for marker in CLEAN_ROOM_MARKERS):
            return None
        text = tool_input.get("prompt")
    elif tool_name == MESSAGE_TOOL:
        if str(tool_input.get("to") or "").strip().lower() == "main":
            return None
        text = tool_input.get("message")
    else:
        return None
    return text if isinstance(text, str) and text.strip() else None


def brief_files(text):
    """Up to MAX_BRIEF_FILES existing files the brief points at whose name says "brief"."""
    found = []
    for raw in BRIEF_PATH.findall(text or ""):
        path = Path(raw.rstrip(".,:;)"))
        if path in found or not path.is_file():
            continue
        found.append(path)
        if len(found) == MAX_BRIEF_FILES:
            break
    return found


def _clause_traced(clause, sources) -> bool:
    words = content_words(clause)
    if len(words) < 2:
        return True                 # too little to judge: never an alarm on a fragment
    if any(len(q.split()) >= MIN_QUOTE_WORDS and sources.has_verbatim(q)
           for q in _QUOTED.findall(norm(clause))):
        return True
    return sources.has_verbatim(clause.strip(" .:")) or sources.covers(words)


def clauses(text):
    """`text` split on the semicolons that lie OUTSIDE double quotes. PURE.

    A verbatim quote of an option often holds its own ";", and cutting there leaves two halves
    with one quote mark each, so neither half is found as a quote.
    """
    quoted = [m.span() for m in _QUOTED.finditer(text)]
    out, start = [], 0
    for at, char in enumerate(text):
        if char == ";" and not any(a < at < b for a, b in quoted):
            out.append(text[start:at])
            start = at + 1
    out.append(text[start:])
    return [c for c in out if c.strip()]


def traced(line, sources) -> bool:
    """True when every clause of a must-not label line is found in the sources. PURE."""
    label = LABEL.match(line)
    body = norm(line[label.end():] if label else line)
    return all(_clause_traced(c, sources) for c in clauses(body))


def relayed_reading(line, readings):
    """The review line number of a negative note this brief line repeats unlabelled, else None. PURE.

    The note must stand as whole words ("no code change" is not in "no code changes") and outside
    double quotes, where a brief is quoting the log rather than stating a rule. And the brief must
    be about the same thing: TOPIC_OVERLAP content words shared with the note's own paragraph,
    beyond the note's words. A short note is a common phrase - "(my reading) ... no code change"
    under a timing decision matched two unrelated briefs saying "No code change." (2 and 2 shared
    words), while the real relay shared 43 with its note's paragraph.
    """
    bare = _QUOTED.sub(" ", norm(line))
    words = content_words(line)
    for n, clause, topic in readings:
        if not re.search(r"(?<![\w-])" + re.escape(clause) + r"(?![\w-])", bare):
            continue
        own = content_words(clause)
        if len((words - own) & (topic - own)) >= TOPIC_OVERLAP:
            return n
    return None


def findings(lines, sources):
    """[(kind, where, text)] for one brief, given [(where, line)] and the Sources. PURE.

    kind is "my-reading", "relayed-reading" (text names the review line the note came from) or
    "untraced". `where` is what the advice may cite: "line N" for inline text, "<file> line N" for
    a brief file.
    """
    out = []
    for where, line in lines:
        labelled = MY_READING.search(_QUOTED_MY_READING.sub(" ", norm(line))) is not None
        if MARKER.search(line) and labelled:
            out.append(("my-reading", where, line))
            continue
        if not labelled and sources.readings:
            hit = relayed_reading(line, sources.readings)
            if hit is not None:
                out.append(("relayed-reading", where, f"{REVIEW_NAME} line {hit}"))
                continue
        if sources and not labelled and LABEL.match(line) and not traced(line, sources):
            out.append(("untraced", where, line))
    return out


def brief_lines(text, files):
    """[(where, paragraph)] for the inline brief and each brief file it points at.

    A brief is hard-wrapped Markdown, so each unit is a paragraph (see `paragraphs`), cited by the
    line it starts on.
    """
    lines = [(f"line {n}", para) for n, para in paragraphs(text)]
    for path in files:
        try:
            body = _read_head(path, BRIEF_FILE_CAP)
        except OSError:
            continue
        lines += [(f"{path.name} line {n}", para) for n, para in paragraphs(body)]
    return lines


# Factual statements, not system-style commands: additionalContext framed as an out-of-band order
# can trip the model's prompt-injection defence, which surfaces it instead of using it.
_HEAD = {
    "my-reading": "is a Must-NOT labelled as your own reading. An inference is not a user "
                  "constraint; the subagent will build it as one unless it is asked as a question "
                  "or dropped",
    "relayed-reading": "repeats a (my reading) note from {text} without its label, so the subagent "
                       "reads your inference as a rule",
    "untraced": "is a Must-NOT found in neither USER-DECISIONS.jsonl nor EXECUTION-USER-REVIEW.md. "
                "A relay that quotes the chosen option's own words, or carries a (my reading) "
                "label, is what the decision-relay rule asks for",
}


def advice(found) -> str | None:
    """The additionalContext for these findings, or None. PURE. Kept well under the 2000-char cap."""
    if not found:
        return None
    parts = ["Brief check (decision relay). This brief has already gone out; a correction to it "
             "would go by SendMessage."]
    for kind, where, text in found[:MAX_REPORTED]:
        quote = ""
        if kind != "relayed-reading" and where.startswith("line "):
            quote = f' ("{" ".join(text.split())[:LINE_EXCERPT]}")'
        parts.append(f"- {where}{quote} {_HEAD[kind].format(text=text)}.")
    if len(found) > MAX_REPORTED:
        parts.append(f"- and {len(found) - MAX_REPORTED} more such lines.")
    return "\n".join(parts)


def assess(event):
    """The advice for one PreToolUse event, or None."""
    if not isinstance(event, dict):
        return None
    text = brief_text(event.get("tool_name"), event.get("tool_input"))
    if text is None:
        return None
    cwd = event.get("cwd") if isinstance(event.get("cwd"), str) else None
    decisions, review = source_paths(cwd)
    sources = load_sources(decisions, review)
    return advice(findings(brief_lines(text, brief_files(text)), sources))


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:  # noqa: BLE001 - no/invalid stdin: do nothing
        return 0
    message = assess(event)
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
