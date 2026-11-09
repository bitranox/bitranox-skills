#!/usr/bin/env python3
"""PreToolUse(Bash|PowerShell|Edit|Write|MultiEdit|NotebookEdit) nudge: a clock time written into a durable record should match the clock.

A session's sense of elapsed time is unreliable, and a stamp typed from it reads as evidence: a
later reader takes "17:55" in a handover or backlog as when something happened. Rewriting the rule
as prose has not stopped it, so a write to OPEN-WORK.md, a handover file or EXECUTION-USER-REVIEW.md
that adds a same-day HH:MM far from the clock, or ahead of it, gets one line naming both.

Scope of a NUDGE (additionalContext, exit 0, always): a time quoted from the past (when the user
said go, when a run ended) is legitimate and indistinguishable here, so nothing is refused, the
text says so, and only stamps within 90 minutes of the clock are judged at all: a replay over 19,221
recorded writes fired on 7 percent of them without that horizon, most of them plainly quoted times. Silent on a Bash command that reads the clock itself (`date`, `datetime.now`),
because a derived stamp is the thing being asked for. Fails open on any error.

Compared against the local clock, or UTC for a stamp written with Z or UTC. A date on the same
line other than today means the stamp is not about today and is skipped. Stamps already in the
replaced text (Edit) or on disk (Write, a Bash rewrite) are not new.
"""

import datetime
import json
import re
import sys
from pathlib import Path

import shell_text

__all__ = ["assess", "main", "new_stamp_problems"]

_DURABLE = re.compile(r"(?:^|/)(?:OPEN-WORK\.md|handover[^/]*\.md|EXECUTION-USER-REVIEW\.md)$", re.IGNORECASE)
_DURABLE_IN_TEXT = re.compile(r"OPEN-WORK\.md|handover[^\s'\"/]*\.md|EXECUTION-USER-REVIEW\.md", re.IGNORECASE)
_STAMP = re.compile(r"(?<![\d:/.-])(?P<hh>[01]\d|2[0-3]):(?P<mm>[0-5]\d)(?::[0-5]\d)?(?P<tz>\s?(?:Z|UTC)\b)?(?![\d:])")
_ANY_DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_CLOCK_READ = re.compile(r"\bdate\b|datetime\.|time\.strftime|utcnow")
_TOLERANCE_MINUTES = 5
# Further from the clock than this is a quoted past or planned time, not a stamp typed as "now".
_HORIZON_MINUTES = 90
_MESSAGE = ("CLOCK CHECK: this writes %s into %s, but the clock reads %s. Stamp a durable record "
            "from `date` in the same command, not from a sense of elapsed time. A time quoted from "
            "the past (when a run ended, when the user said go) is fine: leave it.")


def _bad_stamps(text, known, now_local, now_utc):
    """(stamp text, clock text) for each stamp in `text` far from the clock and not in `known`."""
    bad = []
    today = now_local.date().isoformat()
    for line in text.splitlines():
        dates = _ANY_DATE.findall(line)
        if dates and today not in dates:
            continue
        for match in _STAMP.finditer(line):
            value = "%s:%s" % (match.group("hh"), match.group("mm"))
            if value in known:
                continue
            clock = now_utc if match.group("tz") else now_local
            stamp_minutes = int(match.group("hh")) * 60 + int(match.group("mm"))
            now_minutes = clock.hour * 60 + clock.minute
            ahead = (stamp_minutes - now_minutes) % 1440
            behind = (now_minutes - stamp_minutes) % 1440
            if 1 < ahead <= _HORIZON_MINUTES or _TOLERANCE_MINUTES < behind <= _HORIZON_MINUTES:
                bad.append((match.group(0).strip(), clock.strftime("%H:%M")))
    return bad


def new_stamp_problems(text, old_text, now_local, now_utc):
    """(stamp, clock) pairs for times `text` adds that are far from the clock. PURE."""
    known = {"%s:%s" % (m.group("hh"), m.group("mm")) for m in _STAMP.finditer(old_text or "")}
    return _bad_stamps(text or "", known, now_local, now_utc)


def _read(path):
    try:
        return Path(path).read_text(encoding="utf-8", errors="ignore")
    except (OSError, ValueError):
        return ""


def _edit_tool_text(tool_input):
    """(added text, replaced text) of an Edit/MultiEdit/Write input."""
    if "new_string" in tool_input:
        return tool_input.get("new_string") or "", tool_input.get("old_string") or ""
    if "edits" in tool_input:
        edits = [e for e in tool_input.get("edits") or [] if isinstance(e, dict)]
        return ("\n".join(str(e.get("new_string") or "") for e in edits),
                "\n".join(str(e.get("old_string") or "") for e in edits))
    return str(tool_input.get("content") or ""), None


def _bash_writes(command, cwd):
    """(added text, on-disk text, durable file name) for a Bash command writing a durable record."""
    if _CLOCK_READ.search(command):
        return None
    named = _DURABLE_IN_TEXT.search(command)
    if not named:
        return None
    lines = command.split("\n")
    added = ["\n".join(lines[start:end]) for _line, _opener, (start, end) in shell_text.iter_heredocs(command)]
    # an `echo ... >> OPEN-WORK.md` carries the text on the statement itself
    for _at, segment in shell_text.iter_segments(shell_text.strip_heredoc_bodies(command), "Bash"):
        if _DURABLE_IN_TEXT.search(segment) and ">" in segment:
            added.append(segment)
    if not added:
        return None
    path = named.group(0)
    old = _read(Path(cwd or ".") / path)
    return "\n".join(added), old, path


def assess(event, now_local=None, now_utc=None):
    """The nudge text for this PreToolUse event, or None. PURE apart from reading the target."""
    now_local = now_local or datetime.datetime.now()
    now_utc = now_utc or datetime.datetime.now(datetime.timezone.utc)
    tool = event.get("tool_name")
    tool_input = event.get("tool_input") or {}
    if tool in ("Edit", "Write", "MultiEdit"):
        path = str(tool_input.get("file_path") or "").replace("\\", "/")
        if not _DURABLE.search(path):
            return None
        added, old = _edit_tool_text(tool_input)
        old = _read(path) if old is None else old
        name = path.rsplit("/", 1)[-1]
    elif tool == "Bash":
        command = tool_input.get("command")
        if not isinstance(command, str):
            return None
        found = _bash_writes(command, event.get("cwd"))
        if found is None:
            return None
        added, old, name = found
    else:
        return None
    problems = new_stamp_problems(added, old, now_local, now_utc)
    if not problems:
        return None
    stamp, clock = problems[0]
    return _MESSAGE % (stamp, name, clock)


def main(raw=None):
    try:
        event = json.loads(raw if raw is not None else sys.stdin.read() or "{}")
    except (ValueError, TypeError):
        return 0
    if not isinstance(event, dict):
        return 0
    text = assess(event)
    if text:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                                 "additionalContext": text}}))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:                                    # a nudge must never wedge a turn
        sys.exit(0)
