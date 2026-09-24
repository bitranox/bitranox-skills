#!/usr/bin/env python3
"""Opt-in text classifier port for the hooks: TypeSafe's Jev (a "System One" model), in SHADOW mode.

Several hooks classify prose with regexes - is this turn a learning signal, which skill does this
prompt need, is this memory note relevant. Jev answers exactly that kind of question: text goes in
as a named-field `state`, typed questions go with it (`noul` = probability of yes, `choice` = one of
N keys, `score` = position on described levels), and typed answers with probabilities come back.

Shadow mode never changes a hook's behaviour. The hook keeps deciding with its regex, spawns a
DETACHED child (`python3 classifier.py --shadow <payload-file>`) and returns at once; the child
redacts the text, asks Jev, and appends both verdicts to `~/.claude/self-improve-audit/
classifier-shadow-<UTC date>.jsonl` so a later replay can compare them; each append drops whole
days older than SHADOW_KEEP_DAYS, then the oldest days past SHADOW_MAX_BYTES. Off unless the user sets
`classifier_backend = jev` and the site's own knob to `shadow` (meta-memory-settings).

Egress: only the named fields a site passes are sent, each capped, every one through
`secret_patterns.redact` plus the API key itself as a literal - a secret is replaced, never a
reason to skip the call.

Pure standard library (urllib), so it runs on the bare interpreter run-python.sh finds. Every
failure - no key, HTTP error, timeout, malformed answer - yields None plus a reason, never an
exception into a hook.
"""

import contextlib
import json
import os
import re
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

import secret_patterns  # noqa: E402
import transcript_turns  # noqa: E402

__all__ = [
    "Answer", "CAP_MARK", "CONTEXT_VIEW", "DEFAULT_BASE_URL", "JevClassifier", "NOTIFY_VIEW",
    "NO_SKILL_KEY", "NullClassifier", "PICK_ID", "PREVIOUS_FIELD", "Question", "Result",
    "SHADOW_DAY_PREFIX", "SHADOW_KEEP_DAYS", "SHADOW_LOG", "SHADOW_MAX_BYTES", "SHORT_DESC_CAP",
    "SITES", "TURN_NOTIFICATION", "TURN_PROMPT",
    "detect_language", "get_classifier", "load_key", "load_router_criteria",
    "load_skill_descriptions", "prepare_state", "prune_shadow_logs",
    "recall_questions", "shadow_enabled", "shadow_log_files", "shadow_log_path",
    "short_description", "skill_router_choice_questions",
    "shadow_guard", "skill_router_questions", "skill_router_rerank_questions", "spawn_shadow",
    "stop_signal_questions", "with_previous",
]

DEFAULT_BASE_URL = "https://api.typesafe.ai"
ENDPOINT = "/v1/systemone"
KEY_ENV = "TYPESAFE_API_KEY"
BASE_URL_ENV = "BITRANOX_CLASSIFIER_BASE_URL"
# The single undated log that releases before 7.22.0 appended to. It is still READ, as the oldest
# rows, and it ages out by its last write like any day file; nothing appends to it any more.
SHADOW_LOG = "classifier-shadow.jsonl"
# One file per UTC day. Writers are concurrent detached children, and a day file is never renamed,
# so no two of them can race a rotation; retiring one is a delete, which a race cannot corrupt.
SHADOW_DAY_PREFIX = "classifier-shadow-"
_SHADOW_DAY_RE = re.compile(r"^classifier-shadow-(\d{4}-\d{2}-\d{2})\.jsonl$")
# Retention (user's choice, 2026-09-25): the choice-v1 accumulation, its blind labelling and the two
# later site reviews each need rows from the weeks before, and a busy day logs about 11 MB.
SHADOW_KEEP_DAYS = 30
SHADOW_MAX_BYTES = 200 * 1024 * 1024
# A hook budget. The measured cold call (TLS handshake included) was 860 ms.
DEFAULT_DEADLINE = 1.5
# The detached child blocks nobody, so it can wait for a slow answer rather than lose it.
SHADOW_DEADLINE = 15.0
FIELD_CAP = 4000
# An error row carries the message, not a traceback: enough to group failures by cause.
ERROR_CAP = 200
CAP_MARK = "\n[... truncated ...]\n"
# The first-wave sites. Each has its own config knob `classifier_<site>` (off | shadow).
SITES = ("stop_signal", "skill_router", "recall_rerank")
_LOOPBACK = {"127.0.0.1", "localhost", "::1"}


@dataclass(frozen=True)
class Question:
    """One typed question. `id` is for code only - the API never shows it to the model, so
    `instructions` must carry the whole meaning, naming state fields as backticked paths."""

    id: str
    type: str  # noul | choice | score
    instructions: str
    criteria: object = None

    def to_json(self):
        d = {"id": self.id, "type": self.type, "instructions": self.instructions}
        if self.criteria is not None:
            d["criteria"] = self.criteria
        return d

    @classmethod
    def from_json(cls, d):
        return cls(id=d["id"], type=d["type"], instructions=d["instructions"],
                   criteria=d.get("criteria"))

    def to_api(self):
        d = {"type": self.type, "instructions": self.instructions}
        if self.criteria is not None:
            d["criteria"] = self.criteria
        return d


@dataclass(frozen=True)
class Answer:
    type: str
    value: object  # float for noul/score, the chosen key for choice
    probabilities: object = None
    confidence: object = None


@dataclass(frozen=True)
class Result:
    answers: dict
    latency_ms: int
    input_tokens: int
    model: str

    def to_json(self):
        return {"answers": {k: {"type": a.type, "value": a.value, "probabilities": a.probabilities,
                                "confidence": a.confidence} for k, a in self.answers.items()},
                "latency_ms": self.latency_ms, "input_tokens": self.input_tokens,
                "model": self.model}


class _BadResponse(ValueError):
    pass


class NullClassifier:
    """The off switch: answers nothing, so every caller keeps its regex verdict."""

    def __init__(self, reason):
        self.last_reason = reason

    def ask(self, state, questions):
        return None

    def ask_many(self, items, workers=8):
        return [None for _ in items]


@dataclass
class JevClassifier:
    key: str
    model: str = "jev-latest"
    base_url: str = DEFAULT_BASE_URL
    deadline: float = DEFAULT_DEADLINE
    last_reason: object = field(default=None)

    def ask(self, state, questions):
        """One request; a Result, or None with `last_reason` set. Never raises."""
        return self.ask_many([(state, questions)], workers=1)[0]

    def ask_many(self, items, workers=8):
        """Concurrent requests under ONE overall deadline; results keep the input order.

        `urlopen(timeout=)` bounds each socket operation, not the whole exchange, so a server
        trickling bytes could outlive any hook budget. Each request runs on a DAEMON thread and
        the caller waits only until the deadline; a late thread is abandoned, and being a daemon
        it cannot keep the process alive at exit (a ThreadPoolExecutor worker would).
        """
        results = [None] * len(items)
        reasons = ["deadline"] * len(items)
        gate = threading.Semaphore(max(1, workers))
        end = time.monotonic() + self.deadline

        def _run(i, state, questions):
            with gate:
                if time.monotonic() >= end:
                    return
                try:
                    results[i] = self._post(state, questions, end)
                    reasons[i] = None
                except _BadResponse as exc:
                    reasons[i] = "bad response: %s" % exc
                except urllib.error.HTTPError as exc:
                    reasons[i] = "http %d" % exc.code
                except Exception as exc:  # noqa: BLE001 - network, TLS, anything: fail open
                    reasons[i] = "error: %s" % type(exc).__name__

        threads = [threading.Thread(target=_run, args=(i, s, q), daemon=True)
                   for i, (s, q) in enumerate(items)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(max(0.0, end - time.monotonic()))
        out = [results[i] if not threads[i].is_alive() else None for i in range(len(items))]
        failed = [reasons[i] for i in range(len(items)) if out[i] is None]
        self.last_reason = failed[0] if failed else None
        return out

    def _post(self, state, questions, end):
        body = json.dumps({"model": self.model, "state": state,
                           "questions": {q.id: q.to_api() for q in questions}}).encode("utf-8")
        req = urllib.request.Request(
            self.base_url.rstrip("/") + ENDPOINT, data=body, method="POST",
            headers={"Authorization": "Bearer " + self.key, "Content-Type": "application/json",
                     "User-Agent": "bitranox-skills-classifier"})
        t0 = time.monotonic()
        timeout = max(0.05, end - t0)
        with urllib.request.urlopen(req, timeout=timeout,  # noqa: S310 - fixed https or loopback
                                    context=ssl.create_default_context()) as resp:
            raw = resp.read()
        latency = int((time.monotonic() - t0) * 1000)
        return _parse(raw, questions, latency)


def _parse(raw, questions, latency):
    try:
        data = json.loads(raw)
    except ValueError as exc:
        raise _BadResponse("not json") from exc
    answers_in = data.get("answers") if isinstance(data, dict) else None
    if not isinstance(answers_in, dict):
        raise _BadResponse("no answers")
    answers = {}
    for q in questions:
        a = answers_in.get(q.id)
        if not isinstance(a, dict) or a.get("type") != q.type or q.type not in a:
            raise _BadResponse("missing or mistyped answer %r" % q.id)
        value = a[q.type]
        if q.type == "choice" and isinstance(q.criteria, dict) and value not in q.criteria:
            raise _BadResponse("choice %r not among the options" % value)
        answers[q.id] = Answer(type=q.type, value=value, probabilities=a.get("probabilities"),
                               confidence=a.get("confidence"))
    usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
    return Result(answers=answers, latency_ms=latency,
                  input_tokens=int(usage.get("input_tokens") or 0), model=str(data.get("model", "")))


# ---- configuration -------------------------------------------------------------------------

def load_key(env, home):
    """(key, None) or (None, reason). The env var wins, then `~/.credentials/typesafe.key`.

    A keyfile any other user could read is refused: the key is billing authority, and a
    permissive mode usually means it was created by accident rather than by `install -m 600`.
    """
    key = (env.get(KEY_ENV) or "").strip()
    if key:
        return key, None
    path = Path(home) / ".credentials" / "typesafe.key"
    try:
        if os.name != "nt" and path.stat().st_mode & 0o077:
            return None, "keyfile permissions"
        key = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None, "no api key"
    return (key, None) if key else (None, "no api key")


def shadow_enabled(cfg, site):
    return cfg.get("classifier_backend") == "jev" and cfg.get("classifier_" + site) == "shadow"


def _base_url(env):
    """The API base. The env override exists for tests and is honoured ONLY for a loopback
    host - honouring any host would let one environment variable send the key elsewhere."""
    override = (env.get(BASE_URL_ENV) or "").strip()
    if override and urlparse(override).hostname in _LOOPBACK:
        return override
    return DEFAULT_BASE_URL


def get_classifier(cfg, site, env=None, home=None, deadline=DEFAULT_DEADLINE):
    env = os.environ if env is None else env
    home = Path.home() if home is None else Path(home)
    if cfg.get("classifier_backend") != "jev":
        return NullClassifier("classifier_backend is off")
    if cfg.get("classifier_" + site) not in ("shadow",):
        return NullClassifier("classifier_%s is off" % site)
    key, reason = load_key(env, home)
    if key is None:
        return NullClassifier(reason)
    return JevClassifier(key=key, model=str(cfg.get("classifier_model") or "jev-latest"),
                         base_url=_base_url(env), deadline=deadline)


# ---- egress preparation --------------------------------------------------------------------

def prepare_state(fields, key=None, cap=FIELD_CAP):
    """Redact and cap each named field; return (state, redaction_count).

    A long field keeps its head and its tail: a message's intent sits at the start, a tool
    output's verdict at the end.
    """
    state, total = {}, 0
    literals = [key] if key else []
    for name, text in fields.items():
        text, n = secret_patterns.redact(str(text or ""), extra_literals=literals)
        total += n
        if len(text) > cap:
            half = cap // 2
            text = text[:half] + CAP_MARK + text[-(cap - half):]
        state[name] = text
    return state, total


_DE = {"der", "die", "das", "und", "nicht", "ist", "ich", "du", "bitte", "wir", "mit", "auf", "ein",
       "eine", "noch", "nein", "doch", "immer", "nie", "habe", "hast", "kannst", "mach", "nimm",
       "falsch", "richtig", "warum", "wie", "was", "aber", "oder", "auch", "sehr", "gut", "jetzt"}
_EN = {"the", "and", "not", "is", "you", "please", "we", "with", "on", "a", "an", "no", "yes",
       "always", "never", "have", "can", "make", "use", "wrong", "right", "why", "how", "what",
       "but", "or", "also", "very", "good", "now", "that", "this", "it"}


def detect_language(text):
    """en | de | unknown - a stopword count, enough to split the eval per language (Jev is
    documented as English-primary, and the Stop gate's regexes cover German too)."""
    words = [w.strip(".,;:!?\"'()[]") for w in (text or "").lower().split()]
    de = sum(w in _DE for w in words) + sum(ch in "äöüß" for ch in (text or "").lower())
    en = sum(w in _EN for w in words)
    if de == en == 0:
        return "unknown"
    return "de" if de > en else "en"


# ---- the question sets, one per site ---------------------------------------------------------
# One `noul` per label wherever several labels can hold at once (TypeSafe's guidance): a turn can
# be a correction AND state a rule, a prompt can need two skills.

# The reply a prompt answers, as a state field. "yes", "go" or "check it again" cannot be judged
# without it. Trimmed, keeping both ends: its opening says what it is about, its end usually holds
# the question the short answer refers to. Every log line records this view.
CONTEXT_VIEW = "prev-reply-v1"
PREVIOUS_CAP = 300
PREVIOUS_FIELD = "previous_assistant_message"


def with_previous(fields, previous):
    """`fields` plus the trimmed previous reply, first; unchanged when there is none (the first
    prompt of a session), so no question is asked about an empty field."""
    text = transcript_turns.excerpt(previous, PREVIOUS_CAP)
    return {PREVIOUS_FIELD: text, **fields} if text else dict(fields)


def stop_signal_questions():
    """The Stop gate's learning-signal families, over {previous_assistant_message, user_message,
    assistant_reply}."""
    return [
        Question("correction", "noul",
                 "Does `user_message` correct, reject or push back on something the assistant did "
                 "or said, for example in `previous_assistant_message`?"),
        Question("remember_rule", "noul",
                 "Does `user_message` state a lasting rule, preference or instruction for future "
                 "work, such as 'always', 'never', 'from now on' or 'remember this'?"),
        Question("self_admission", "noul",
                 "Does `assistant_reply` admit that the assistant made a mistake, missed something, "
                 "or was wrong?"),
        Question("realization", "noul",
                 "Does `assistant_reply` state a newly understood root cause or a reusable lesson, "
                 "beyond just reporting that a fix was made?"),
        Question("endorsement", "noul",
                 "Does `user_message` approve an approach the assistant proposed in "
                 "`previous_assistant_message`, or does `assistant_reply` agree to adopt an idea "
                 "the user suggested?"),
    ]


def load_skill_descriptions(skills_dir=None):
    """{skill name: description} from each shipped SKILL.md front matter (one-line descriptions)."""
    skills_dir = Path(skills_dir) if skills_dir else _HOOKS_DIR.parent / "skills"
    out = {}
    for md in sorted(skills_dir.glob("*/SKILL.md")):
        try:
            head = md.read_text(encoding="utf-8").split("---", 2)[1]
        except (OSError, IndexError):
            continue
        for line in head.splitlines():
            if line.startswith("description:"):
                desc = line[len("description:"):].strip().strip("\"'")
                if desc:
                    out[md.parent.name] = desc
                break
    return out


# Option text written FOR the router, which is a different consumer from the keyword matcher the
# shipped descriptions were written for. The API's guidance for an option catalogue is "Start with
# a one-line description per option. When two options are similar and the model keeps confusing
# them, describe each one with an object instead of a string. Give it fields for what the option
# covers, what belongs to a neighboring option instead, and a few example inputs."
# (docs.typesafe.ai/primitives/choice; `criteria` accepts string | object | array | null.)
#
# The file is partial on purpose: an entry is worth writing where the adjudication showed a skill
# losing to a neighbour, and everywhere else the skill's own description is already the best text
# anyone has. A missing entry therefore falls back rather than emptying the option.
ROUTER_CRITERIA_FILE = _HOOKS_DIR / "router_criteria.json"


def load_router_criteria(skills, path=None):
    """{skill name: option text}, preferring a router-authored entry over the description.

    Never raises: a hook may not wedge a prompt over its own data file, and a missing or malformed
    file degrades to the descriptions, which is the behaviour before this file existed.
    """
    try:
        raw = json.loads(Path(path or ROUTER_CRITERIA_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raw = {}
    if not isinstance(raw, dict):
        raw = {}
    return {name: raw.get(name) or desc for name, desc in skills.items()}


# The router's gate question. Its id starts with "_" so it can never collide with a skill name;
# the eval reads a low score as "a continuation, suggest nothing".
NEW_TASK_ID = "_new_task"

# Which kind of turn the router is judging. A typed prompt is one thing; a task notification is
# not a prompt at all, so sending its envelope as `user_prompt` asks the model to read a status
# line as if somebody had said it. Each kind names its own state fields, and a notification row
# records NOTIFY_VIEW so the eval never pools the two.
TURN_PROMPT = "prompt"
TURN_NOTIFICATION = "notification"
NOTIFY_VIEW = "fields-v1"

# A question names a context field only when the caller sent that field. `_router_fields` leaves
# out a field that is empty, so on the FIRST prompt of a session there is no
# `previous_assistant_message` and no `recent_activity` - and a question naming one anyway asks
# the model to contrast against nothing, which it answers by HEDGING rather than erroring, so
# there is no failure to notice. Measured 2026-09-23 by a planted control: the gate scored
# 0.66-0.70 there against its own 0.7 threshold, and 0.89-0.90 (negative 0.05-0.06) with the
# fields present. That is a coin flip exactly where a session starts, and every arm is judged
# through this gate. The wording for a caller that DOES send them is unchanged.
_CONTEXT_FIELDS = ("previous_assistant_message", "recent_activity", "skills_already_used")


def _have(fields, name):
    """Did the caller send this field with something in it?"""
    return bool(str((fields or {}).get(name) or "").strip())


def _and_list(names):
    """'`a`', '`a` and `b`', '`a`, `b` and `c`' - the fields one sentence may name."""
    ticked = ["`%s`" % n for n in names]
    if len(ticked) < 2:
        return ticked[0] if ticked else ""
    return "%s and %s" % (", ".join(ticked[:-1]), ticked[-1])


def _joined(*parts):
    """The sentences that have something to say, one space apart."""
    return " ".join(p for p in parts if p)


def _describing(fields):
    """The fields that say what work is already under way.

    The previous turn's REASONING is deliberately not among them. It was implemented and A/B'd on
    2026-09-24 over 49 interleaved pairs drawn only from prompts that HAVE it, and it made the gate
    LOWER on 139 of 245 cells against higher on 61 (mean and median -0.010), so the arms spoke less
    rather than more - the wrong direction, since missing a needed skill is the dominant failure.
    It is also absent from about 88% of prompts even in sessions that record thinking at all.
    Do not re-add it without a result that beats those numbers.
    """
    return [n for n in (PREVIOUS_FIELD, "recent_activity") if _have(fields, n)]


def _context_sentence(fields, subject):
    """What the state fields are, for the reader of a skill question - naming only those sent."""
    parts = []
    if _have(fields, PREVIOUS_FIELD) and subject:
        parts.append("%s is a reply to `%s`" % (subject, PREVIOUS_FIELD))
    naming = [n for n in ("project", "recent_activity") if _have(fields, n)]
    if naming:
        parts.append("%s say%s what is being worked on"
                     % (_and_list(naming), "" if len(naming) > 1 else "s"))
    return ", and ".join(parts) + "." if parts else ""


def _router_turn_text(turn, fields):
    """(gate instructions, what the skill question is about, the context sentence) for `turn`."""
    under_way = _describing(fields)
    if turn == TURN_NOTIFICATION:
        carry_on = ("the work in %s can carry on" % _and_list(under_way) if under_way
                    else "the work under way can carry on")
        return (
            "A background task has just finished, described by `task_status` and `task_summary`. "
            "Does handling it need specialised know-how - for example because it failed - rather "
            "than simply being noted so %s?" % carry_on,
            "the finished background task in `task_status` and `task_summary`",
            _context_sentence(fields, ""),
        )
    checking = ("the work that %s describe%s" % (_and_list(under_way),
                                                 "" if len(under_way) > 1 else "s")
                if under_way else "work already under way")
    return (
        "Does `user_prompt` start a new task, or change direction in a way that needs specialised "
        "know-how, rather than continuing, approving or checking %s?" % checking,
        "`user_prompt`",
        _context_sentence(fields, "`user_prompt`"),
    )


def skill_router_questions(skills, fields, turn=TURN_PROMPT):
    """The gate question, then one noul per skill; each skill's id is its name.

    `fields` is the state this same request will carry, because the questions may only name what
    it holds. For `TURN_PROMPT` that is user_prompt, and when known previous_assistant_message,
    project, recent_activity and skills_already_used; for `TURN_NOTIFICATION`, task_status and
    task_summary in place of user_prompt.
    """
    gate_instructions, subject, context = _router_turn_text(turn, fields)
    skip_used = ("Answer no if the skill is listed in `skills_already_used`."
                 if _have(fields, "skills_already_used") else "")
    return [Question(NEW_TASK_ID, "noul", gate_instructions)] + [
        Question(name, "noul",
                 _joined("Would the assistant need the skill described here to handle %s well?"
                         % subject, context, skip_used, "Skill description: %s" % desc))
        for name, desc in skills.items()]


# The choice-shaped arm of the same question. One `choice` over the whole roster replaces the one
# noul per skill: the roster is sent ONCE as option descriptions instead of once per skill wrapped
# in its own question frame, and the answer carries a probability for every option plus a
# confidence, so nothing is lost by asking once. `PICK_ID` starts with "_" for the same reason
# `NEW_TASK_ID` does, and `NO_SKILL_KEY` holds an underscore, which a taxonomy-conformant skill
# name (hyphens only) cannot.
PICK_ID = "_pick"
NO_SKILL_KEY = "none_needed"
# A choice winner at least this sure passes a failed gate. The gate vetoed confident picks: "yes,
# write the handover" chose meta-context-watcher at 0.96 while the gate read the turn as approving
# work under way (0.37), and 8 of 14 such winners on a 30-prompt handover/backlog stratum were lost
# that way. Swept offline over three recorded runs: at 0.7 the stratum's context-watcher picks go
# 6 -> 12 of 30 with no added pick on a no-skill prompt in either labelled set; at 0.6 the
# held-out set gains 2 noise picks. The value is on the CHOICE's own probability scale, chosen from
# its own sweep - not borrowed from a noul threshold, since the API promises no comparability.
CHOICE_BYPASS = 0.7


def choice_pick(gate, winner, probabilities, *, threshold, bypass=CHOICE_BYPASS):
    """The skill a gate-plus-choice answer suggests, or None.

    The winner is taken when the gate passes (an unanswered gate does not suppress), or when the
    winner's own probability reaches `bypass`. A missing probability reads as unsure, and the
    no-match option is never a pick however confident. `bypass=None` restores gate-only.
    """
    if winner in (None, NO_SKILL_KEY):
        return None
    if not isinstance(gate, (int, float)) or gate >= threshold:
        return winner
    sure = (probabilities or {}).get(winner)
    if bypass is not None and isinstance(sure, (int, float)) and sure >= bypass:
        return winner
    return None


# The cookbook's roster is the truncated index its agent sees, averaging 54 characters. Ours are
# whole paragraphs, so they are cut to the opening clause; the frame states once what every one
# of them otherwise repeats.
SHORT_DESC_CAP = 120
_USE_PREFIX = re.compile(r"^use\s+(?:when|to|for|on|at|after|before|if|while|during)\s+", re.I)


def short_description(desc, cap=SHORT_DESC_CAP):
    """The opening clause of a skill description, without the `Use when` boilerplate.

    80 of the 81 shipped descriptions open with "Use when" or another "Use <preposition>", so an
    option list repeats it 80 times for nothing. Cuts on a word boundary, and adds no ellipsis -
    a marker costs tokens and tells the model nothing it can act on.
    """
    text = " ".join(str(desc or "").split())
    text = _USE_PREFIX.sub("", text)
    if len(text) <= cap:
        return text
    cut = text[:cap]
    head, sep, _tail = cut.rpartition(" ")
    return (head if sep else cut).rstrip(" ,;:-")


def _pick_question(skills, subject, context, no_match, fields=None):
    wrong = ("one that merely sounds related is wrong, as is one already listed in "
             "`skills_already_used`" if _have(fields, "skills_already_used")
             else "one that merely sounds related is wrong")
    return Question(
        PICK_ID, "choice",
        _joined("Which ONE of these skills would the assistant need to handle %s well? Each "
                "option describes when that skill applies." % subject, context,
                "Choose a skill only when it does the specific thing being asked; %s. Otherwise "
                "choose %r." % (wrong, NO_SKILL_KEY)),
        criteria={**skills, NO_SKILL_KEY: no_match})


def skill_router_choice_questions(skills, fields, turn=TURN_PROMPT):
    """The same gate, then ONE choice over the whole roster.

    The gate is byte-identical to the noul arm's on purpose: this arm moves the shape of the
    skill question and nothing else, so a comparison between the two can attribute what it sees.
    That holds per state, since both arms build the gate from the same `fields`.
    """
    gate_instructions, subject, context = _router_turn_text(turn, fields)
    return [Question(NEW_TASK_ID, "noul", gate_instructions),
            _pick_question(skills, subject, context,
                           "No listed skill does this. Ordinary work the assistant handles from "
                           "general understanding, or a task none of these cover.", fields)]


def skill_router_rerank_questions(shortlist):
    """Second request: the same choice over a handful of candidates shown in FULL, plus one noul
    per candidate asking whether it does the specific thing asked.

    The wide pass ranks the roster on one clause each; this one re-reads the survivors at length,
    which is where a skill that merely sounds related loses. The per-candidate noul is the floor:
    a choice must return something, so without it a shortlist of three wrong skills still names a
    winner.
    """
    return [_pick_question(shortlist, "the request", "",
                           "None of these does the specific thing being asked.")] + [
        Question(name, "noul",
                 "Does the skill %r do the specific thing the request asks for, rather than "
                 "something merely related? Skill: %s" % (name, body))
        for name, body in shortlist.items()]


def recall_questions():
    """One noul per (prompt, note) pair, asked in its own request (TypeSafe's rerank pattern)."""
    return [Question("relevant", "noul",
                     "Would `memory_note` be useful context for carrying out `user_prompt`, read "
                     "as a reply to `previous_assistant_message` when that is given? Only if it is "
                     "about the same task, tool or problem, not merely sharing some words.")]


# ---- shadow: the hook side -----------------------------------------------------------------

def _audit_dir():
    return Path.home() / ".claude" / "self-improve-audit"


def _transcript_location(transcript):
    """{"path", "offset"} of the transcript as it stood when the hook ran, both None without one.

    The offset is the file size at that moment, which places the prompt a row was asked about
    even when the same text was typed many times in one session.
    """
    if not transcript:
        return {"path": None, "offset": None}
    try:
        return {"path": str(transcript), "offset": os.path.getsize(transcript)}
    except OSError:
        return {"path": str(transcript), "offset": None}


def spawn_shadow(site, session_id, regex, requests, transcript=""):
    """Hand one shadow comparison to a detached child and return immediately.

    `requests` is a list of {"fields": {name: text}, "questions": [Question, ...]}. The payload
    goes through a mode-600 temp file, not a pipe: a large payload would block on a full pipe
    buffer until the child starts reading, which is latency on the user's prompt. Never raises.
    """
    try:
        payload = {"site": site, "session_id": session_id, "regex": regex,
                   "transcript": _transcript_location(transcript),
                   "requests": [{"fields": r["fields"],
                                 "questions": [q.to_json() for q in r["questions"]]}
                                for r in requests]}
        d = _audit_dir()
        d.mkdir(parents=True, exist_ok=True)
        fd, path = tempfile.mkstemp(prefix="classifier-", suffix=".json", dir=str(d))
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh)
        kwargs = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL,
                  "stderr": subprocess.DEVNULL, "close_fds": True}
        if os.name == "nt":
            kwargs["creationflags"] = (getattr(subprocess, "DETACHED_PROCESS", 0)
                                       | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))
        else:
            kwargs["start_new_session"] = True
        subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--shadow", path],
                         **kwargs)
    except Exception:  # noqa: BLE001 - shadow mode must never cost the hook anything
        pass


# ---- shadow: the child side ----------------------------------------------------------------

def _read_payload(argv):
    """The payload file named on the command line (deleted once read), else stdin."""
    if len(argv) > 1:
        path = Path(argv[1])
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        finally:
            try:
                path.unlink()
            except OSError:
                pass
    return json.loads(sys.stdin.read())


def _plugin_version():
    """The version of the plugin this file shipped in, so each row names the release that wrote
    it: sessions on different releases append to the same log."""
    try:
        manifest = _HOOKS_DIR.parent / ".claude-plugin" / "plugin.json"
        return str(json.loads(manifest.read_text(encoding="utf-8")).get("version") or "")
    except (OSError, ValueError, AttributeError):
        return ""


def _stamp(record, payload):
    """Add the release and the transcript location every row carries, success or failure."""
    where = payload.get("transcript") if isinstance(payload.get("transcript"), dict) else {}
    record["plugin_version"] = _plugin_version()
    record["transcript_path"] = where.get("path")
    record["transcript_offset"] = where.get("offset")
    return record


def _error_record(payload, exc):
    """The row for a comparison that failed: no answers, and the cause as its `reason`."""
    message, _n = prepare_state({"e": "%s: %s" % (type(exc).__name__, exc)}, cap=ERROR_CAP)
    return _stamp({
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "site": str(payload.get("site") or ""),
        "session_id": payload.get("session_id"),
        "regex": payload.get("regex"),
        "reason": "error: " + message["e"],
        "results": [],
    }, payload)


@contextlib.contextmanager
def shadow_guard(site, session_id):
    """Run a site's shadow hand-off, swallowing any exception but logging it as an error row.

    Shadow mode must never cost a hook anything, and it must not fail silently either: a site
    that raises and writes nothing looks exactly like a site that is switched off.
    """
    try:
        yield
    except Exception as exc:  # noqa: BLE001 - shadow mode must never wedge a hook
        try:
            _append_log(_error_record({"site": site, "session_id": session_id}, exc))
        except Exception:  # noqa: BLE001 - nothing left to report to
            pass


def run_shadow(payload, cfg, env=None, home=None):
    """Ask Jev for one site's comparison and return the log record (the caller appends it)."""
    site = str(payload.get("site") or "")
    requests = payload.get("requests") or []
    clf = get_classifier(cfg, site, env=env, home=home, deadline=SHADOW_DEADLINE)
    key = getattr(clf, "key", None)
    states, redactions = [], 0
    for r in requests:
        state, n = prepare_state(r.get("fields") or {}, key=key)
        states.append(state)
        redactions += n
    items = [(s, [Question.from_json(q) for q in r.get("questions") or []])
             for s, r in zip(states, requests)]
    results = clf.ask_many(items)
    first_text = " ".join(str(v) for v in (requests[0].get("fields") or {}).values()) if requests else ""
    return _stamp({
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "site": site,
        "session_id": payload.get("session_id"),
        "lang": detect_language(first_text),
        "regex": payload.get("regex"),
        "reason": clf.last_reason,
        "redactions": redactions,
        "input_tokens": sum(r.input_tokens for r in results if r),
        "latency_ms": max([r.latency_ms for r in results if r] or [0]),
        "results": [r.to_json() if r else None for r in results],
        "states": states,
    }, payload)


def shadow_log_path(audit, now):
    """The day file a row logged at `now` (an aware UTC datetime) is appended to."""
    return Path(audit) / ("%s%s.jsonl" % (SHADOW_DAY_PREFIX, now.strftime("%Y-%m-%d")))


def shadow_log_files(audit):
    """Every shadow log in `audit`, oldest rows first: the undated SHADOW_LOG, then the day files.

    Day files sort by name because the date in it is fixed-width. A missing dir lists nothing.
    """
    try:
        names = os.listdir(audit)
    except OSError:
        return []
    legacy = [SHADOW_LOG] if SHADOW_LOG in names else []
    return [Path(audit) / n for n in legacy + sorted(n for n in names if _SHADOW_DAY_RE.match(n))]


def _log_day(path):
    """The UTC date a log's newest row was written on: from the name, or the undated file's mtime."""
    m = _SHADOW_DAY_RE.match(path.name)
    if m:
        return datetime.strptime(m.group(1), "%Y-%m-%d").date()
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).date()


def _unlink(path):
    """True when `path` is gone afterwards. A concurrent prune may have removed it first, and on
    Windows a file another process holds open refuses; the next append retries that one."""
    try:
        path.unlink()
    except FileNotFoundError:
        return True
    except OSError:
        return False
    return True


def prune_shadow_logs(audit, now, keep_days=SHADOW_KEEP_DAYS, max_bytes=SHADOW_MAX_BYTES):
    """Delete whole logs older than `keep_days` UTC days, then the oldest until the rest fit in
    `max_bytes`. The current day's file is never deleted, even when it alone is over the cap.
    Returns the paths it removed. Never raises for a file that vanished or will not go."""
    today = shadow_log_path(audit, now)
    oldest_kept = (now - timedelta(days=keep_days - 1)).date()
    removed, sized = [], []
    for path in shadow_log_files(audit):
        try:
            day, size = _log_day(path), path.stat().st_size
        except OSError:                    # removed by a concurrent prune between list and stat
            continue
        if path != today and day < oldest_kept:
            if _unlink(path):
                removed.append(path)
            continue
        sized.append((path, size))
    total = sum(size for _p, size in sized)
    for path, size in sized:
        if total <= max_bytes:
            break
        if path != today and _unlink(path):
            removed.append(path)
            total -= size
    return removed


def _append_log(record, audit=None, now=None):
    d = Path(audit) if audit is not None else _audit_dir()
    now = now or datetime.now(timezone.utc)
    d.mkdir(parents=True, exist_ok=True)
    with open(shadow_log_path(d, now), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    prune_shadow_logs(d, now)


def _shadow_main(argv):
    import self_improve_signals as sig  # noqa: PLC0415 - only the child needs the config reader
    payload = {}
    try:
        payload = _read_payload(argv)
        _append_log(run_shadow(payload, sig.load_config()))
    except Exception as exc:  # noqa: BLE001 - its only reader is the log, so the failure goes there
        try:
            _append_log(_error_record(payload if isinstance(payload, dict) else {}, exc))
        except Exception:  # noqa: BLE001 - nothing left to report to
            pass
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--shadow":
        sys.exit(_shadow_main(sys.argv[1:]))
    print("usage: classifier.py --shadow [payload.json]", file=sys.stderr)
    sys.exit(2)
