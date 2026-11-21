"""Judge a written claim that the USER approved something: is it the user's words, and is it safe?

A session that records "the user approved X" in a backlog line, a handover or a commit message
hands the next reader a permission. When the record paraphrases, the permission can grow: a plain
"yes" to "merge and push?" was written into a backlog as "(the user approved the release as is)"
(2026-11-19), and the next session would have released leftovers the question never named. Every
word the user typed is in the session transcript, and every AskUserQuestion answer is in
USER-DECISIONS.jsonl, so the claim can be checked.

Two duties, both computed here for decision-claim-guard.py and the backlog_add bridge:

1. Faithfulness (`judge`). An entry whose added text holds an approval phrase (`APPROVAL`) passes
   only when it carries either a quoted span that occurs in a message the person TYPED
   (transcript_turns.human_text: task notifications, teammate and peer messages are not the
   user's words) or in a chosen USER-DECISIONS.jsonl answer, or a `decision-check: "<term>"`
   marker that resolves there exactly as the review-log rule resolves it (decision_claims). A
   bare paraphrase is refused; a quote the user never typed is refused, naming the nearest
   message the user did type. With no transcript and no decision log readable, a quote passes
   unverified.
2. Critical review (`concerns`). An entry that passes but reaches past its own evidence - a
   widening phrase ("as is", "everything", "alles") the quote does not contain, or an iron-rule
   area (secrets, a public push or release, a force push, deleting data or history, AI
   attribution) the quote does not name - gets an advisory: raise it with the user, recommend the
   narrowest reading with its reason, before acting on the claim.

Pure standard library apart from the plugin's own decision_claims, transcript_turns and
claude_paths.
"""

from __future__ import annotations

import collections
import dataclasses
import json
import os
import re
from collections.abc import Iterator
from pathlib import Path

import claude_paths
import transcript_turns
from decision_claims import Entry, chosen_texts, find_hits, iter_records, marker_terms, MARKER

__all__ = ["APPROVAL", "TARGET_NAMES", "Verdict", "Word", "WordSource", "advice_text", "concerns",
           "explain", "is_target", "judge", "quoted_spans", "transcript_for_session"]

TARGET_NAMES = frozenset({"open-work.md", "handover.md"})

_WHO = r"(?:Benutzer|Nutzer|User|Anwender)(?:in)?"
_DE_VERB = r"(?:freigegeben|zugestimmt|genehmigt|abgenickt|akzeptiert|abgesegnet)"
APPROVAL = re.compile(
    # "the user (has) approved / agreed / accepted / okayed / said yes"; "as the user approved".
    # "(past) what the user approved" states a limit, not an approval, so it is no trigger.
    r"(?<!what\sthe\s)(?<!what\s)\buser\s+(?:has\s+|had\s+)?(?:approved|agreed|accepted|okayed|ok'?ed"
    r"|said\s+(?:yes|ok(?:ay)?|go))\b"
    r"|\buser-approved\b"
    # "der Benutzer hat (den Plan) freigegeben", up to six words between, none of them a negation
    r"|\b(?:der|die)\s+" + _WHO + r"\s+hat\s+(?:(?!nicht\b|kein)[^\s.;:!?]+\s+){0,6}?" + _DE_VERB + r"\b"
    r"|(?<!nicht\s)\bvom\s+" + _WHO + r"\s+(?:freigegeben|genehmigt|abgesegnet|akzeptiert|bestaetigt"
    r"|best\u00e4tigt)\b",
    re.IGNORECASE,
)

# A span counts as a quote between straight or typographic double quotes, German or French
# quotes, or single quotes that no word character touches from outside (so "user's" opens none).
_WRAP = r"|\n(?![ \t]*\n)"                 # a quote may wrap onto the next line, never past a blank one
_QUOTE = re.compile(
    r'"((?:[^"\n]' + _WRAP + r'){1,400})"'
    r"|\u201c((?:[^\u201d\n]" + _WRAP + r"){1,400})\u201d"
    r"|\u201e((?:[^\u201c\u201d\n]" + _WRAP + r"){1,400})[\u201c\u201d]"
    r"|\u00bb((?:[^\u00ab\n]" + _WRAP + r"){1,400})\u00ab"
    r"|\u00ab((?:[^\u00bb\n]" + _WRAP + r"){1,400})\u00bb"
    r"|(?<![\w'])'([^'\n]{1,400})'(?![\w'])"
)
_CODE_SPAN = re.compile(r"`[^`\n]*`")
_ELLIPSIS = re.compile(r"\s*(?:\[\.\.\.\]|\[\u2026\]|\.\.\.|\u2026)\s*")
_CANON = str.maketrans({"\u00e4": "ae", "\u00f6": "oe", "\u00fc": "ue", "\u00c4": "ae",
                        "\u00d6": "oe", "\u00dc": "ue", "\u00df": "ss", "\u2019": "'",
                        "\u2018": "'", "\u201c": '"', "\u201d": '"', "\u201e": '"'})
_SPACE = re.compile(r"\s+")
_EDGE = " \t.,;:!?-"
_WORD = re.compile(r"\w+")

# Typed text kept in memory for one judgement: the newest messages up to this many characters.
# A session's typed prompts are far smaller; the cap only bounds a pathological transcript.
_TYPED_CHARS = 4 * 1024 * 1024
# Earlier transcripts of the same project are searched on a miss, newest first, up to this many
# bytes in all: a handover often cites an approval given in the session before.
_SIBLING_BYTES = 64 * 1024 * 1024
_NEAREST_MAX = 300
_PLAN_CHARS = 64 * 1024                 # an approved plan's text kept as evidence
_MD_NAME = re.compile(r"[\w.-]+\.md\b", re.IGNORECASE)
_SESSION_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")

_WIDEN = re.compile(
    r"\bas[- ]is\b|\beverything\b|\ball\s+of\s+it\b|\ball\s+(?:the\s+)?(?:leftovers|remaining|rest)\b"
    r"|\bthe\s+rest\b|\bwhatever\b|\bwholesale\b|\bunconditional(?:ly)?\b|\bblanket\b|\bcarte\s+blanche\b"
    r"|\bwie\s+(?:es|sie|er)\s+ist\b|\balles\b|\bkomplett\b|\bsaemtliche\w*|\bs\u00e4mtliche\w*"
    r"|\bpauschal\b|\bden\s+rest\b",
    re.IGNORECASE,
)
_IRON = (
    ("secrets or credentials", re.compile(
        r"\bpassw(?:or|\u00f6)?\w*|\bsecrets?\b|\btokens?\b|\bcredentials?\b|\bapi[- ]?keys?\b"
        r"|\bprivate\s+keys?\b|(?<!\w)\.env\b", re.IGNORECASE)),
    ("a public push or release", re.compile(
        r"\breleas\w*|\bpublish\w*|\bpypi\b|\bpush(?:ed|es|ing)?\b|\btag(?:ged|ging|s)?\b"
        r"|\bveroeffentlich\w*|\bver\u00f6ffentlich\w*", re.IGNORECASE)),
    ("a force push", re.compile(
        r"\bforce[- ]push\w*|\bpush\s+(?:-f\b|--force)|--force(?:-with-lease)?\b", re.IGNORECASE)),
    ("deleting data or history", re.compile(
        r"\bdelet\w*|\brm\s+-\w*r|\bdrop\s+(?:table|database|the\s+data)|\bpurg\w*|\bwip(?:e|ed|ing)\b"
        r"|\bprun\w*|\bfilter-repo\b|\breset\s+--hard\b|\brewrit\w*\s+(?:the\s+)?history\b"
        r"|\bsquash\w*|\bl\u00f6sch\w*|\bloesch\w*", re.IGNORECASE)),
    ("AI attribution", re.compile(
        r"\bco-authored-by\b|\battribution\b|\bgenerated\s+with\s+claude\b", re.IGNORECASE)),
)


def is_target(path: str) -> bool:
    """True for a file whose approval claims are judged: OPEN-WORK.md or a handover.md."""
    return os.path.basename(path.replace("\\", "/")).lower() in TARGET_NAMES


def _canon(text: str) -> str:
    return _SPACE.sub(" ", text.translate(_CANON)).strip().lower()


def quoted_spans(text: str) -> list[str]:
    """The quoted spans of `text`, outside code spans and decision-check markers, in order."""
    bare = MARKER.sub(" ", _CODE_SPAN.sub(" ", text))
    out = []
    for match in _QUOTE.finditer(bare):
        span = next(group for group in match.groups() if group is not None)
        if _WORD.search(_canon(span)):                 # punctuation alone names nothing
            out.append(span)
    return out


def _fragments(quote: str) -> list[str]:
    return [f for f in (_canon(p).strip(_EDGE) for p in _ELLIPSIS.split(quote)) if f]


def _occurs(fragments: list[str], text: str) -> bool:
    """True when every fragment occurs in `text` (canonical), in order, at word boundaries."""
    canon, at = _canon(text), 0
    for fragment in fragments:
        match = re.compile(r"(?<!\w)" + re.escape(fragment) + r"(?!\w)").search(canon, at)
        if match is None:
            return False
        at = match.end()
    return True


@dataclasses.dataclass(frozen=True)
class Word:
    """One thing the user gave: typed text, a chosen answer, or a plan approved in plan mode."""

    text: str
    plan_file: str = ""                # basename of the approved plan's file, for a plan approval


def _answer_words(result: dict) -> Iterator[Word]:
    """The chosen label and description of each answer of an AskUserQuestion tool result."""
    answers = result.get("answers")
    if not isinstance(answers, dict):
        return
    options = {}
    for question in result.get("questions") or []:
        for option in question.get("options") or [] if isinstance(question, dict) else []:
            if isinstance(option, dict) and isinstance(option.get("label"), str):
                options[option["label"]] = str(option.get("description") or "")
    for answer in answers.values():
        if not isinstance(answer, str):
            continue
        for label in [a.strip() for a in answer.split(",")] if answer not in options else [answer]:
            yield Word(label)
            if options.get(label):
                yield Word(options[label])


def _record_words(record: dict) -> Iterator[Word]:
    text = transcript_turns.human_text(record)
    if text:
        yield Word(text)
        return
    result = record.get("toolUseResult") if record.get("type") == "user" else None
    if not isinstance(result, dict):
        return
    if "answers" in result:
        yield from _answer_words(result)
    elif isinstance(result.get("filePath"), str) and isinstance(result.get("plan"), str):
        # ExitPlanMode writes this shape only for an approved plan; a rejection is an error string
        yield Word(result["plan"][:_PLAN_CHARS], os.path.basename(result["filePath"].replace("\\", "/")))


def _user_words(path: Path) -> Iterator[Word]:
    """Each thing the user gave in the transcript at `path`, oldest first."""
    try:
        handle = open(path, encoding="utf-8", errors="replace")
    except OSError:
        return
    with handle:
        for line in handle:
            if '"user"' not in line and "queued_command" not in line:
                continue                               # cheap pre-filter: most lines are not the user's
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if isinstance(record, dict):
                yield from _record_words(record)


def _typed_texts(path: Path) -> Iterator[str]:
    """The user's words of the transcript at `path` that are text, not an approved plan."""
    return (w.text for w in _user_words(path) if not w.plan_file)


class WordSource:
    """The words the user gave: typed messages, chosen answers and plans approved in plan mode of
    a transcript, then the chosen answers of the decision logs.

    Read lazily, only when a claim must be checked; a miss also searches the project's earlier
    transcripts (newest first, `_SIBLING_BYTES` in all) without keeping them in memory.
    """

    def __init__(self, transcript: Path | None, logs: list[Path]):
        self.transcript = transcript if transcript is not None and transcript.is_file() else None
        self.logs = logs
        self._primary: list[str] | None = None
        self._plans: dict[str, str] = {}

    @property
    def readable(self) -> bool:
        return self.transcript is not None or bool(self.logs)

    def primary(self) -> list[str]:
        if self._primary is None:
            kept: collections.deque[str] = collections.deque()
            size = 0
            for word in _user_words(self.transcript) if self.transcript else ():
                if word.plan_file:
                    self._plans[word.plan_file] = word.text
                    continue
                kept.append(word.text)
                size += len(word.text)
                while size > _TYPED_CHARS and len(kept) > 1:
                    size -= len(kept.popleft())
            answers = [t for record in iter_records(self.logs) for _h, _l, t in chosen_texts(record) if t]
            self._primary = list(kept) + answers
        return self._primary

    def locate(self, quote: str) -> str | None:
        """The user message holding `quote`, or None."""
        fragments = _fragments(quote)
        if not fragments:
            return None
        for text in self.primary():
            if _occurs(fragments, text):
                return text
        for path in self._siblings():
            for text in _typed_texts(path):
                if _occurs(fragments, text):
                    return text
        return None

    def approved_plan(self, text: str) -> str | None:
        """The text of a plan approved in plan mode whose file `text` names, or None."""
        named = {m.group(0).lower() for m in _MD_NAME.finditer(text)}
        if not named:
            return None
        self.primary()
        for name, plan in self._plans.items():
            if name.lower() in named:
                return plan
        for path in self._siblings():
            for word in _user_words(path):
                if word.plan_file and word.plan_file.lower() in named:
                    return word.text
        return None

    def _siblings(self) -> list[Path]:
        if self.transcript is None:
            return []
        try:
            found = [(p.stat().st_mtime, p.stat().st_size, p) for p in self.transcript.parent.glob("*.jsonl")
                     if p != self.transcript]
        except OSError:
            return []
        out, budget = [], _SIBLING_BYTES
        for _mtime, size, path in sorted(found, reverse=True):
            if size > budget:
                break
            budget -= size
            out.append(path)
        return out

    def nearest(self, quote: str) -> str | None:
        """The typed message (or chosen answer) sharing the most words with `quote`, or None."""
        want = set(_WORD.findall(_canon(quote)))
        best, score = None, 0.0
        for text in self.primary():
            have = set(_WORD.findall(_canon(text)))
            overlap = len(want & have) / (len(want | have) or 1)
            if overlap > score:
                best, score = text, overlap
        return best


@dataclasses.dataclass(frozen=True)
class Verdict:
    """The judgement of one approval claim: `problem` refuses it, `evidence` is what passed it."""

    entry: Entry
    problem: str | None = None         # "paraphrase" | "unheard-quote" | "marker-miss" | "bad-term"
    detail: str = ""
    evidence: str = ""                 # the user's words that passed the claim


def judge(entry: Entry, logs: list[Path], words: WordSource) -> Verdict:
    """Duty 1 for one entry whose added text holds an approval phrase."""
    terms, bad = marker_terms(entry)
    if terms and bad is None:
        for term in terms:
            hits = find_hits(term, logs)
            if hits:
                return Verdict(entry, evidence=hits[-1].sentence)
    plan = words.approved_plan(entry.text) if words.readable else None
    if plan is not None:
        return Verdict(entry, evidence=plan)
    quotes = quoted_spans(entry.text)
    if quotes and not words.readable:
        return Verdict(entry, evidence=quotes[0])
    for quote in quotes:
        if words.locate(quote) is not None:
            return Verdict(entry, evidence=quote)
    if quotes:
        nearest = words.nearest(quotes[0]) or ""
        return Verdict(entry, "unheard-quote", json.dumps({"quotes": quotes[:3], "nearest": nearest}))
    if bad is not None:
        return Verdict(entry, "bad-term", bad)
    if terms:
        return Verdict(entry, "marker-miss", json.dumps({"terms": terms}))
    return Verdict(entry, "paraphrase")


def _claim_text(entry: Entry) -> str:
    """The entry without its quotes, code spans and markers: what the session itself asserts."""
    bare = MARKER.sub(" ", _CODE_SPAN.sub(" ", entry.text))
    return _canon(_QUOTE.sub(" ", bare))


def concerns(verdict: Verdict) -> list[str]:
    """Duty 2: how a passing claim reaches past its evidence, one sentence each."""
    claim, evidence = _claim_text(verdict.entry), _canon(verdict.evidence)
    out = []
    widened = sorted({m.group(0).lower() for m in _WIDEN.finditer(claim)
                      if not _WIDEN.search(evidence) or m.group(0).lower() not in evidence})
    if widened:
        out.append("reaches past the user's words: %s %s not in %r" % (
            ", ".join(repr(w) for w in widened), "is" if len(widened) == 1 else "are", verdict.evidence))
    for area, pattern in _IRON:
        if pattern.search(claim) and not pattern.search(evidence):
            out.append("touches an iron-rule area the user's words do not name: %s" % area)
    return out


def _lead(kind: str, entry: Entry, where: str, echo: bool) -> str:
    first = entry.lines[0].strip() if entry.lines else ""
    head = " %r" % (first[:100] + ("..." if len(first) > 100 else "")) if echo else ""
    return "%s (%s, entry at line %d%s): " % (kind, where, entry.start, head)


def explain(verdict: Verdict, logs: list[Path], where: str, echo: bool = True) -> str:
    """The refusal text for a refused verdict, written for the model to act on."""
    lead = _lead("APPROVAL CLAIM CHECK", verdict.entry, where, echo)
    remedy = (" Fix it: quote the user's own words in double quotes exactly as typed (e.g. the user "
              "approved the merge: \"yes, merge and push\"), or for an AskUserQuestion answer add "
              "decision-check: \"<term>\" naming a word of the chosen option that the entry also "
              "uses. If the user did not say it, drop the claim or ask the user.")
    if verdict.problem == "paraphrase":
        return lead + (
            "this entry says the user approved, agreed to or accepted something, but carries none "
            "of the user's words. A paraphrase widens a go unnoticed: a plain 'yes' to one question "
            "has been recorded as 'approved the release as is'." + remedy)
    if verdict.problem == "unheard-quote":
        found = json.loads(verdict.detail)
        nearest = found["nearest"][:_NEAREST_MAX]
        return lead + (
            "the user never typed the quoted words (%s): they are in no message the person typed in "
            "this session or an earlier one of this project, and in no chosen answer of %s. A "
            "teammate, subagent or task message is not the user's words. Nearest message the user "
            "did type: %r." % (", ".join(repr(q) for q in found["quotes"]),
                              " and ".join(str(p) for p in logs) or "USER-DECISIONS.jsonl",
                              nearest) + remedy)
    if verdict.problem == "marker-miss":
        terms = json.loads(verdict.detail)["terms"]
        return lead + (
            "the marker term%s %s occur%s in no option the user chose in %s, and the entry quotes "
            "none of the user's words." % ("" if len(terms) == 1 else "s", ", ".join(repr(t) for t in terms),
                                           "s" if len(terms) == 1 else "",
                                           " and ".join(str(p) for p in logs) or "USER-DECISIONS.jsonl (none found)")
            + remedy)
    return lead + verdict.detail + "." + remedy


def advice_text(verdict: Verdict, found: list[str], where: str, echo: bool = True) -> str:
    """The advisory for a passing claim with concerns: raise them with the user, with a recommendation."""
    return _lead("APPROVAL CLAIM REVIEW (advisory, nothing was blocked)", verdict.entry, where, echo) + (
        "the recorded approval %s. Before acting on it, raise this with the user: say plainly what the "
        "approval as written would cover beyond the words the user gave, recommend the narrowest "
        "reading those words support (for an iron-rule area, the safe alternative) and give the "
        "reason. Until the user answers, act only on what the quote names, and narrow the entry to "
        "that if it says more." % "; it ".join(found))


def transcript_for_session(session_id: str) -> Path | None:
    """The transcript of `session_id` under the Claude config dir's projects, or None."""
    if not _SESSION_ID.match(session_id or ""):
        return None
    for path in (claude_paths.config_dir() / "projects").glob("*/%s.jsonl" % session_id):
        if path.is_file():
            return path
    return None
