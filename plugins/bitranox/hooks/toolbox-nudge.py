#!/usr/bin/env python3
"""PreToolUse(Bash|Write|Edit|MultiEdit) nudge: when a tool call looks like a hand-rolled chore
that the local toolbox already has a tested tool for, inject a non-blocking additionalContext
pointer ("use the jig") - once per tool per session. Silent if the toolbox (or the specific tool)
is not installed.

Why: the local toolbox only helps if the model remembers it BEFORE hand-rolling. A chore hides in
one of two places - a Bash one-liner (the command line) or a script authored via Write/Edit (the
file CONTENT). Scanning only Bash left a blind spot: writing the same logic into a .py file and
running it slipped past. So we scan the new text of Write/Edit/MultiEdit too, against the same
signatures. This catches the hand-roll at the moment it reaches for the raw materials and points at
the tool - the closest thing Claude Code offers to "a supervisor noticing and saying: we have a
tool for that". additionalContext reaches the model as a system-reminder (probe-verified), never
blocks.
"""
import json
import os
import re
import sys
from pathlib import Path

# Shared with the other command-scanning guards: a heredoc body is DATA, and scanning it makes a
# guard fire on prose that merely mentions the chore it watches for. Re-exported so callers and
# tests can keep reaching it as `toolbox_nudge.strip_heredoc_bodies`.
from shell_text import is_shell_tool, strip_heredoc_bodies  # noqa: F401

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
    (re.compile(r"\b(?:pkill|pgrep)\s+[^\n]*-f\b"), "procsig",
     "hand-rolling pgrep/pkill -f (self-match risk)"),
    (re.compile(r"\bip\s+neigh\b|getent\s+hosts\s+OVM-|tcpdump[^\n]*\btap"), "guestip",
     "resolving a guest IP by hand"),
    (re.compile(r"/var/log/openvmm/"), "ovmlog", "reading an openvmm per-VM log by hand"),
    # LAST, so a more specific rule above keeps its own shape. A `grep` carrying -c/-l/-L is being
    # asked "is this THERE?", and its NEGATIVE answer is the one that cannot be trusted: `grep -c`
    # exits 1 on zero and prints file:count under -r, `-l` prints nothing for both "absent" and
    # "never looked". Each of those produced a confident false ABSENT in one session. The pipe and
    # semicolon exclusions keep the flag search inside this command, so `... | wc -l` is not read as
    # grep's own flag.
    (re.compile(r"\bgrep\b[^\n|;]*?\s-[A-Za-z]*[clL]"), "claim_check",
     "deciding whether text is PRESENT from a raw grep count/list, whose negative cannot be trusted"),
]


def match_tool(command):
    """(tool, why) for the first rule matching `command`, else None. PURE - unit-testable."""
    for rx, tool, why in _RULES:
        if rx.search(command or ""):
            return tool, why
    return None


# Tools whose call we scan, and WHERE each hides the chore. Bash puts it on the command line;
# Write/Edit/MultiEdit put it in the NEW text being written (never old_string - that is what is
# being removed, not authored). Anything else (Read, Grep, ...) is not a place a chore is authored.
_SCANNED_TOOLS = ("Bash", "PowerShell", "Write", "Edit", "MultiEdit")


def extract_text(tool_name, tool_input):
    """The text to scan for a hand-rolled chore, per tool. PURE - unit-testable.

    Returns None for a tool we do not scan, so `match_tool(None)` short-circuits to no nudge.
    """
    ti = tool_input or {}
    if is_shell_tool(tool_name):
        # Only the command LINES are a chore being hand-rolled. A heredoc body is content being
        # written, so scanning it nudges about prose that merely names the tool - which is how
        # documenting a footgun trips the guard that watches for it.
        return strip_heredoc_bodies(ti.get("command", ""))
    if tool_name == "Write":
        return ti.get("content", "")
    if tool_name == "Edit":
        return ti.get("new_string", "")
    if tool_name == "MultiEdit":
        return "\n".join(e.get("new_string", "") for e in ti.get("edits", []) if isinstance(e, dict))
    return None


def _toolbox_dir():
    """The local toolbox tools dir (resolved at call time so HOME can be overridden in tests)."""
    return Path(os.path.expanduser("~")) / ".claude" / "skills" / "toolbox" / "tools"


def _shipped_dir():
    """The compuse-toolbox scripts dir INSIDE THIS PLUGIN, resolved relative to this hook.

    Relative, so it names whichever plugin version is actually running - a path with a version in
    it would rot at the next update, and the installed cache dir for the old version is pruned."""
    return Path(__file__).resolve().parent.parent / "skills" / "compuse-toolbox" / "scripts"


def _tool_invocation(tool):
    """How to run `tool`: the local copy if there is one, else the shipped one, else None.

    A tool broadly useful enough to be contributed upstream gets DELETED locally (one source of
    truth), and those are precisely the ones most worth nudging about - so keying the nudge on the
    local file alone would turn every successful contribution into a silently lost guard."""
    if (_toolbox_dir() / (tool + ".py")).is_file():
        return "the local `toolbox` skill", "uv run ~/.claude/skills/toolbox/tools/%s.py --help" % tool
    if (_shipped_dir() / (tool + ".py")).is_file():
        return ("the shipped `bitranox:compuse-toolbox` skill",
                "uv run %s/%s.py --help" % (_shipped_dir(), tool))
    return None


def _nudge_flag(session):
    """Where this session's already-nudged tool list lives - a named helper so the path is testable
    rather than built inline, and so the id passes through the shared confinement on the way."""
    from self_improve_signals import session_state_path   # noqa: PLC0415 - shared, confines the id
    return session_state_path(session, ".toolbox-nudged")


def _already_nudged(session, tool):
    """Per-session dedup: True if `tool` was already nudged this session; else record it. Best-effort."""
    if not session:
        return False
    try:
        f = _nudge_flag(session)
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
    if not isinstance(event, dict) or event.get("tool_name") not in _SCANNED_TOOLS:
        return 0
    text = extract_text(event.get("tool_name"), event.get("tool_input") or {})
    hit = match_tool(text)
    if not hit:
        return 0
    tool, why = hit
    found = _tool_invocation(tool)
    if not found:                                        # nowhere local, nowhere shipped -> silent
        return 0
    home, invoke = found
    if _already_nudged(event.get("session_id") or "", tool):
        return 0
    msg = ("%s has a tested tool for this (%s): `%s`. Prefer it over hand-rolling; if it "
           "falls short, ENHANCE it (propose-first, per bitranox:meta-self-improve) rather than "
           "working around it." % (home.capitalize() if home.startswith("the") else home, why, invoke))
    sys.stdout.write(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "additionalContext": msg}}) + "\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:                                    # noqa: BLE001 - a broken hook must never wedge a turn
        sys.exit(0)
