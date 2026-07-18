#!/usr/bin/env python3
"""PreToolUse(Bash) nudge: when a Bash command looks like a hand-rolled chore that the local
toolbox already has a tested tool for, inject a non-blocking additionalContext pointer ("use the
jig") - once per tool per session. Silent if the toolbox (or the specific tool) is not installed.

Why: the local toolbox only helps if the model remembers it BEFORE hand-rolling. This catches the
hand-roll at the moment it reaches for the raw materials (the Bash command) and points at the tool
- the closest thing Claude Code offers to "a supervisor noticing and saying: we have a tool for
that". additionalContext reaches the model as a system-reminder (probe-verified), never blocks.
"""
import json
import os
import re
import sys
from pathlib import Path

# (regex over the command, tool name, one-line "why"). First match wins. STRONG signatures only, to
# keep false positives + noise low; the per-session dedup then nudges each tool at most once.
_RULES = [
    (re.compile(r"<{7}|>{7}"), "conflict_scan", "scanning for git conflict markers"),
    (re.compile(r"\.jsonl\b.*(?:json\.loads|json\.load|for line in)"
                r"|(?:json\.loads|json\.load).*\.jsonl", re.S), "jsonl_grep",
     "parsing a JSONL transcript by hand"),
    (re.compile(r"\bssh\b[^|]*(?:StrictHostKeyChecking|anyhost_nopass|BatchMode=)"), "sshf",
     "building an ssh fleet one-liner"),
    (re.compile(r"(?:cargo (?:build|test|clippy)|gh run (?:view|watch))\b.*(?:\|\s*(?:grep|sed|awk)|2>&1)",
                re.S), "ci_triage", "hand-piping a build/CI log for errors"),
    (re.compile(r"for\b.*\bgit -C\b.*\bstatus\b|git rev-parse --abbrev-ref HEAD"), "git_state",
     "checking git branch/status across repo(s)"),
]


def match_tool(command):
    """(tool, why) for the first rule matching `command`, else None. PURE - unit-testable."""
    for rx, tool, why in _RULES:
        if rx.search(command or ""):
            return tool, why
    return None


def _toolbox_dir():
    """The local toolbox tools dir (resolved at call time so HOME can be overridden in tests)."""
    return Path(os.path.expanduser("~")) / ".claude" / "skills" / "toolbox" / "tools"


def _already_nudged(session, tool):
    """Per-session dedup: True if `tool` was already nudged this session; else record it. Best-effort."""
    if not session:
        return False
    try:
        from self_improve_signals import _audit_dir
        f = _audit_dir() / (str(session) + ".toolbox-nudged")
        seen = set(f.read_text(encoding="utf-8").split()) if f.exists() else set()
        if tool in seen:
            return True
        seen.add(tool)
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(" ".join(sorted(seen)) + "\n", encoding="utf-8")
        return False
    except Exception:                                    # noqa: BLE001 - dedup must never break the hook
        return False


def main():
    try:
        event = json.load(sys.stdin)
    except Exception:                                    # noqa: BLE001 - no/invalid stdin: do nothing
        return 0
    if not isinstance(event, dict) or event.get("tool_name") != "Bash":
        return 0
    command = (event.get("tool_input") or {}).get("command", "")
    hit = match_tool(command)
    if not hit:
        return 0
    tool, why = hit
    if not (_toolbox_dir() / (tool + ".py")).is_file():  # no toolbox / this tool -> stay silent
        return 0
    if _already_nudged(event.get("session_id") or "", tool):
        return 0
    msg = ("The local `toolbox` skill has a tested tool for this (%s): "
           "`uv run ~/.claude/skills/toolbox/tools/%s.py --help`. Prefer it over hand-rolling; if it "
           "falls short, ENHANCE it (propose-first, per bitranox:meta-self-improve) rather than "
           "working around it." % (why, tool))
    sys.stdout.write(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "additionalContext": msg}}) + "\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:                                    # noqa: BLE001 - a broken hook must never wedge a turn
        sys.exit(0)
