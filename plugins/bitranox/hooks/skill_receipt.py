#!/usr/bin/env python3
"""Session receipts proving a procedure skill was actually ENTERED (not just listed).

`bitranox:meta-skill-writer`'s step 0 runs `skill_receipt.py start meta-skill-writer` - the command
is documented only inside that skill, so holding a fresh receipt implies the skill was loaded and
its procedure begun. The skill-edit-guard then allows SKILL.md edits only while a fresh receipt
exists (default TTL 8h), closing the "loaded but not executed" hole: the env bypass proved nothing
about procedure, a receipt at least proves entry.

    skill_receipt.py start <skill-name>       write/refresh the receipt (prints its path)
    skill_receipt.py check <skill-name>       exit 0 fresh / 1 stale-or-missing (prints age)
    skill_receipt.py end <skill-name>         remove the receipt (idempotent; disarms gates)

Receipts live under ~/.claude/self-improve-audit/skill-receipts/, keyed by skill name only
(machine-local; a receipt is a session-scale token, not a per-repo ledger). Pure standard library.
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


def receipt_path(skill):
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in skill)
    return Path.home() / ".claude" / "self-improve-audit" / "skill-receipts" / (safe + ".json")


def start(skill, session_id=None):
    p = receipt_path(skill)
    p.parent.mkdir(parents=True, exist_ok=True)
    sid = session_id if session_id is not None else current_session_id()
    p.write_text(json.dumps({"skill": skill, "ts": time.time(), "session_id": sid}),
                 encoding="utf-8")
    return p


def end(skill):
    """Remove the receipt (idempotent) - disarms any gate keyed on it."""
    try:
        receipt_path(skill).unlink()
        return True
    except OSError:
        return False


def is_fresh(skill, ttl=TTL_SECONDS, session_id=None):
    """Whether a receipt is armed FOR THIS SESSION.

    Session identity is the primary bound and the TTL is the secondary one. Without the id, this
    answered "somebody on this machine started the procedure recently", which is a different
    claim - and on a machine routinely running several sessions at once it is routinely true
    while this session never entered the skill at all.

    A receipt carrying no session id fails CLOSED whenever an id is demanded: not being able to
    say which session wrote it is precisely the hole, so it is not grandfathered. Where the
    caller has no id to offer (a surface that does not supply one), the TTL-only contract stands
    rather than denying every edit there.
    """
    try:
        data = json.loads(receipt_path(skill).read_text(encoding="utf-8"))
        if (time.time() - float(data.get("ts", 0))) >= ttl:
            return False
        if session_id:
            return str(data.get("session_id") or "") == str(session_id)
        return True
    except (OSError, ValueError):
        return False


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
    fresh = is_fresh(skill)
    print("receipt %s: %s" % (skill, "fresh" if fresh else "stale-or-missing"))
    return 0 if fresh else 1


if __name__ == "__main__":
    sys.exit(main())
