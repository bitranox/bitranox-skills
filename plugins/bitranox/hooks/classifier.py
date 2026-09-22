#!/usr/bin/env python3
"""Opt-in text classifier port for the hooks: TypeSafe's Jev (a "System One" model), in SHADOW mode.

Several hooks classify prose with regexes - is this turn a learning signal, which skill does this
prompt need, is this memory note relevant. Jev answers exactly that kind of question: text goes in
as a named-field `state`, typed questions go with it (`noul` = probability of yes, `choice` = one of
N keys, `score` = position on described levels), and typed answers with probabilities come back.

Shadow mode never changes a hook's behaviour. The hook keeps deciding with its regex, spawns a
DETACHED child (`python3 classifier.py --shadow <payload-file>`) and returns at once; the child
redacts the text, asks Jev, and appends both verdicts to `~/.claude/self-improve-audit/
classifier-shadow.jsonl` so a later replay can compare them. Off unless the user sets
`classifier_backend = jev` and the site's own knob to `shadow` (meta-memory-settings).

Egress: only the named fields a site passes are sent, each capped, every one through
`secret_patterns.redact` plus the API key itself as a literal - a secret is replaced, never a
reason to skip the call.

Pure standard library (urllib), so it runs on the bare interpreter run-python.sh finds. Every
failure - no key, HTTP error, timeout, malformed answer - yields None plus a reason, never an
exception into a hook.
"""

import json
import os
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

import secret_patterns  # noqa: E402
import transcript_turns  # noqa: E402

__all__ = [
    "Answer", "CAP_MARK", "CONTEXT_VIEW", "DEFAULT_BASE_URL", "JevClassifier", "NullClassifier",
    "PREVIOUS_FIELD", "Question", "Result", "SHADOW_LOG", "SITES", "detect_language",
    "get_classifier", "load_key", "load_skill_descriptions", "prepare_state", "recall_questions",
    "shadow_enabled", "skill_router_questions", "spawn_shadow", "stop_signal_questions",
    "with_previous",
]

DEFAULT_BASE_URL = "https://api.typesafe.ai"
ENDPOINT = "/v1/systemone"
KEY_ENV = "TYPESAFE_API_KEY"
BASE_URL_ENV = "BITRANOX_CLASSIFIER_BASE_URL"
SHADOW_LOG = "classifier-shadow.jsonl"
# A hook budget. The measured cold call (TLS handshake included) was 860 ms.
DEFAULT_DEADLINE = 1.5
# The detached child blocks nobody, so it can wait for a slow answer rather than lose it.
SHADOW_DEADLINE = 15.0
FIELD_CAP = 4000
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


def skill_router_questions(skills):
    """One noul per skill over {user_prompt}; the id is the skill name."""
    return [Question(name, "noul",
                     "Would the assistant need the skill described here to handle `user_prompt` "
                     "well? `user_prompt` is a reply to `previous_assistant_message` when that is "
                     "given. Skill description: " + desc)
            for name, desc in skills.items()]


def recall_questions():
    """One noul per (prompt, note) pair, asked in its own request (TypeSafe's rerank pattern)."""
    return [Question("relevant", "noul",
                     "Would `memory_note` be useful context for carrying out `user_prompt`, read "
                     "as a reply to `previous_assistant_message` when that is given? Only if it is "
                     "about the same task, tool or problem, not merely sharing some words.")]


# ---- shadow: the hook side -----------------------------------------------------------------

def _audit_dir():
    return Path.home() / ".claude" / "self-improve-audit"


def spawn_shadow(site, session_id, regex, requests):
    """Hand one shadow comparison to a detached child and return immediately.

    `requests` is a list of {"fields": {name: text}, "questions": [Question, ...]}. The payload
    goes through a mode-600 temp file, not a pipe: a large payload would block on a full pipe
    buffer until the child starts reading, which is latency on the user's prompt. Never raises.
    """
    try:
        payload = {"site": site, "session_id": session_id, "regex": regex,
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
    return {
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
    }


def _append_log(record):
    d = _audit_dir()
    d.mkdir(parents=True, exist_ok=True)
    with open(d / SHADOW_LOG, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def _shadow_main(argv):
    import self_improve_signals as sig  # noqa: PLC0415 - only the child needs the config reader
    try:
        payload = _read_payload(argv)
        _append_log(run_shadow(payload, sig.load_config()))
    except Exception:  # noqa: BLE001 - a detached child has nobody to report to
        return 0
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--shadow":
        sys.exit(_shadow_main(sys.argv[1:]))
    print("usage: classifier.py --shadow [payload.json]", file=sys.stderr)
    sys.exit(2)
