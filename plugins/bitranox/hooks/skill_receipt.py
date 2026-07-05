#!/usr/bin/env python3
"""Session receipts proving a procedure skill was actually ENTERED (not just listed).

`bitranox:meta-skill-writer`'s step 0 runs `skill_receipt.py start meta-skill-writer` - the command
is documented only inside that skill, so holding a fresh receipt implies the skill was loaded and
its procedure begun. The skill-edit-guard then allows SKILL.md edits only while a fresh receipt
exists (default TTL 8h), closing the "loaded but not executed" hole: the env bypass proved nothing
about procedure, a receipt at least proves entry.

    skill_receipt.py start <skill-name>       write/refresh the receipt (prints its path)
    skill_receipt.py check <skill-name>       exit 0 fresh / 1 stale-or-missing (prints age)

Receipts live under ~/.claude/self-improve-audit/skill-receipts/, keyed by skill name only
(machine-local; a receipt is a session-scale token, not a per-repo ledger). Pure standard library.
"""
import json
import sys
import time
from pathlib import Path

TTL_SECONDS = 8 * 3600


def receipt_path(skill):
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in skill)
    return Path.home() / ".claude" / "self-improve-audit" / "skill-receipts" / (safe + ".json")


def start(skill):
    p = receipt_path(skill)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"skill": skill, "ts": time.time()}), encoding="utf-8")
    return p


def is_fresh(skill, ttl=TTL_SECONDS):
    try:
        data = json.loads(receipt_path(skill).read_text(encoding="utf-8"))
        return (time.time() - float(data.get("ts", 0))) < ttl
    except (OSError, ValueError):
        return False


def main(argv=None):
    args = argv if argv is not None else sys.argv[1:]
    if len(args) != 2 or args[0] not in ("start", "check"):
        print("usage: skill_receipt.py start|check <skill-name>")
        return 2
    cmd, skill = args
    if cmd == "start":
        print("receipt: %s" % start(skill))
        return 0
    fresh = is_fresh(skill)
    print("receipt %s: %s" % (skill, "fresh" if fresh else "stale-or-missing"))
    return 0 if fresh else 1


if __name__ == "__main__":
    sys.exit(main())
