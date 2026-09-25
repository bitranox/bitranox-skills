#!/usr/bin/env python3
"""Session receipts proving a procedure skill was actually ENTERED (not just listed).

`bitranox:meta-skill-writer`'s step 0 runs `skill_receipt.py start meta-skill-writer` - the command
is documented only inside that skill, so holding a fresh receipt implies the skill was loaded and
its procedure begun. The skill-edit-guard then allows SKILL.md edits only while a fresh receipt
exists (default TTL 8h), closing the "loaded but not executed" hole: the env bypass proved nothing
about procedure, a receipt at least proves entry.

    skill_receipt.py start <skill-name>       write/refresh this session's receipt (prints its path)
    skill_receipt.py check <skill-name>       exit 0 fresh / 1 stale-or-missing (prints age + session)
    skill_receipt.py end <skill-name>         remove this session's receipt (idempotent; disarms gates)

Receipts live under ~/.claude/self-improve-audit/skill-receipts/, one file per skill AND session
(`<skill>.<session>.json`; `<skill>.json` when the surface supplies no session id). The session
comes from CLAUDE_CODE_SESSION_ID. Keying by skill alone let one session's `start` overwrite and
its `end` delete another session's receipt - and let one session's plan execution arm a deny gate
in every other session on the machine. Machine-local; pure standard library.
"""
import json
import os
import sys
import time
from pathlib import Path

TTL_SECONDS = 8 * 3600
# Claude Code sets this in a Bash tool call, and its value is the session's own transcript name -
# the same id a PreToolUse event carries. That equality is what lets the writer (a Bash call) and
# the reader (the hook) agree on which session holds the receipt.
SESSION_ENV = "CLAUDE_CODE_SESSION_ID"


def current_session_id(env=None):
    """This session's id, or "" when the surface does not supply one."""
    return ((env if env is not None else os.environ).get(SESSION_ENV) or "").strip()


def _safe(text):
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in str(text))


def receipts_dir():
    return Path.home() / ".claude" / "self-improve-audit" / "skill-receipts"


def receipt_path(skill, session_id=""):
    """The receipt file for (`skill`, `session_id`); the id-less one when the id is empty.

    The id-less path is also where a receipt written before the per-session key lives, so a reader
    consults it as well and trusts it only when the session RECORDED inside matches."""
    sid = str(session_id or "").strip()
    name = _safe(skill) + ("." + _safe(sid) if sid else "")
    return receipts_dir() / (name + ".json")


def _read(path):
    """The receipt's data as a dict, or None when absent, unreadable or not a receipt's shape."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _age(data, now=None):
    """Seconds since the receipt was written, or None when its timestamp is not a number."""
    ts = data.get("ts")
    if isinstance(ts, bool) or not isinstance(ts, (int, float)):
        return None
    return (time.time() if now is None else now) - float(ts)


def _prune(skill, ttl=TTL_SECONDS):
    """Remove this skill's receipts that expired, whichever session wrote them.

    One file per session accumulates otherwise. mtime, not the recorded ts: a receipt whose body
    is unreadable must still age out."""
    base = _safe(skill)
    cutoff = time.time() - ttl
    try:
        entries = list(receipts_dir().iterdir())
    except OSError:
        return
    for p in entries:
        # A safe skill name holds no dot, so `<skill>.` cannot prefix another skill's receipts.
        if not (p.name == base + ".json" or (p.name.startswith(base + ".") and p.suffix == ".json")):
            continue
        try:
            if p.stat().st_mtime < cutoff:
                p.unlink()
        except OSError:
            pass


def start(skill, session_id=None):
    sid = session_id if session_id is not None else current_session_id()
    _prune(skill)
    p = receipt_path(skill, sid)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"skill": skill, "ts": time.time(), "session_id": sid}),
                 encoding="utf-8")
    return p


def _owned(skill, session_id):
    """(path, data) of the receipt this session owns, or (None, None).

    A candidate counts only when the session recorded INSIDE it equals `session_id`: that is what
    keeps the id-less file - which is also the pre-per-session location - from answering for
    another session."""
    sid = str(session_id or "").strip()
    for p in dict.fromkeys((receipt_path(skill, sid), receipt_path(skill))):
        data = _read(p)
        if data is not None and str(data.get("session_id") or "").strip() == sid:
            return p, data
    return None, None


def end(skill, session_id=None):
    """Remove THIS session's receipt (idempotent) - disarms this session's gates, no one else's."""
    sid = session_id if session_id is not None else current_session_id()
    removed = False
    while True:
        p, _ = _owned(skill, sid)
        if p is None:
            return removed
        try:
            p.unlink()
        except OSError:
            return removed
        removed = True


def is_fresh(skill, ttl=TTL_SECONDS, session_id=None):
    """Whether a receipt is armed FOR THIS SESSION.

    Session identity is the primary bound and the TTL is the secondary one. Asking without the id
    answered "somebody on this machine started the procedure recently", which is a different claim
    - and on a machine routinely running several sessions at once it is routinely true while this
    session never entered the skill at all.

    A caller with no id to offer (a surface that supplies none) is answered from the id-less
    receipt only, which is what the same surface's `start` writes. A receipt carrying no session id
    therefore fails CLOSED whenever an id is demanded, and a session-keyed one never answers an
    id-less caller."""
    _, data = _owned(skill, session_id)
    if data is None:
        return False
    age = _age(data)
    return age is not None and age < ttl


def main(argv=None):
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 2 or args[0] not in ("start", "check", "end"):
        print("usage: skill_receipt.py start|check|end <skill-name>")
        return 2
    cmd, skill = args
    if cmd == "start":
        print("receipt: %s" % start(skill))
        return 0
    if cmd == "end":
        print("receipt %s: %s" % (skill, "removed" if end(skill) else "absent"))
        return 0
    sid = current_session_id()
    who = "session %s" % (sid or "(none)")
    if not is_fresh(skill, session_id=sid):
        print("receipt %s: stale-or-missing (%s)" % (skill, who))
        return 1
    _, data = _owned(skill, sid)
    print("receipt %s: fresh (age %.1fh, %s)" % (skill, (_age(data) or 0.0) / 3600.0, who))
    return 0


if __name__ == "__main__":
    sys.exit(main())
