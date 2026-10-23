#!/usr/bin/env python3
"""The shell calls already run in the CURRENT assistant message, recorded by hooks as they happen.

A PreToolUse guard that judges a call against its same-message siblings (an earlier `cd`, an
earlier gate nobody has read) cannot rely on the transcript: probed on Claude Code 2.1.309, a
later sibling's PreToolUse hook runs before the earlier siblings' records are written, so the
transcript shows none of them and the guard sees nothing. The hook events themselves are in step
(probed on the same CLI): sibling calls fire PreToolUse and PostToolUse strictly one call after
another, and PostToolBatch fires once when the message's calls have all resolved, listing them.
A subagent's events carry its `agent_id`, its PostToolBatch included.

So `sibling-ledger.py` appends each shell call to a per-session, per-agent file at PreToolUse,
and empties it at PostToolBatch (the message is over), and at UserPromptSubmit and Stop as
backstops for a batch that never resolved. `earlier()` then answers "which shell calls ran
before this one in this message" for any PreToolUse event.

The file lives in a per-user directory under the system temp dir, created 0700 and used only
while it is a real directory owned by this user with no group or world access; files are opened
without following a symlink and created 0600. The temp dir is shared on a POSIX host, and the
entries hold command text: another user must be able neither to redirect the appends through a
planted link nor to plant entries that refuse this user's commits. On Windows the temp dir is
already per user. Every failure answers None ("nothing known"), which a guard must read as
"allow". Entries older than MAX_AGE_SECONDS are ignored, so a ledger a crash left behind cannot
refuse a later message.
"""

import json
import os
import re
import stat
import sys
import tempfile
import time
from pathlib import Path

from shell_text import is_shell_tool

#: An entry this old belongs to a message whose PostToolBatch never came (a crash, a kill).
#: Generous, because one sibling can be a gate that runs for many minutes.
MAX_AGE_SECONDS = 6 * 3600

# Both ids become part of a file name; anything but a plain name could leave the temp dir.
_PLAIN = re.compile(r"[A-Za-z0-9_-]+")


# Not following a link where the platform can refuse one; Windows has no O_NOFOLLOW.
_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)


def _private_dir():
    """This user's ledger directory, or None when it is not safely ours."""
    root = Path(tempfile.gettempdir())
    if sys.platform == "win32":
        return root  # %TEMP% is per user there
    base = root / ("claude-siblings-%d" % os.getuid())
    try:
        base.mkdir(mode=0o700)
    except FileExistsError:
        pass
    info = os.lstat(base)
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
        return None
    return base


def ledger_path(event):
    """The ledger file of the session and agent `event` belongs to; None when unusable or unsafe."""
    session = event.get("session_id")
    agent = event.get("agent_id") or "main"
    if not isinstance(session, str) or not _PLAIN.fullmatch(session):
        return None
    if not isinstance(agent, str) or not _PLAIN.fullmatch(agent):
        return None
    base = _private_dir()
    return None if base is None else base / ("claude-siblings-%s-%s.jsonl" % (session, agent))


def record(event, now=None):
    """Append the shell call a PreToolUse `event` describes to its ledger; other tools are ignored."""
    tool_name = event.get("tool_name")
    path = ledger_path(event)
    if path is None or not is_shell_tool(tool_name):
        return
    entry = {
        "id": event.get("tool_use_id"),
        "tool": tool_name,
        "command": (event.get("tool_input") or {}).get("command") or "",
        "t": time.time() if now is None else now,
    }
    # One short line per append: concurrent hooks of one call never interleave inside it.
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | _NOFOLLOW, 0o600)
    with os.fdopen(fd, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry) + "\n")


def clear(event):
    """Forget the ledger of the session and agent `event` belongs to (its message is over)."""
    path = ledger_path(event)
    if path is not None:
        path.unlink(missing_ok=True)


def earlier(event, now=None):
    """Commands of the shell calls recorded before the one `event` describes, oldest first.

    The call's own entry is left out: its recorder runs beside the guard asking, in either order.
    None when there is no ledger or it cannot be read; then nothing is known about the siblings.
    """
    path = ledger_path(event)
    if path is None:
        return None
    try:
        fd = os.open(path, os.O_RDONLY | _NOFOLLOW)
    except OSError:
        return None  # absent, or a link this reader refuses to follow
    with os.fdopen(fd, encoding="utf-8", errors="replace") as handle:
        lines = handle.read().splitlines()
    cutoff = (time.time() if now is None else now) - MAX_AGE_SECONDS
    own = event.get("tool_use_id")
    commands = []
    for line in lines:
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if not isinstance(entry, dict) or entry.get("id") == own:
            continue
        if not isinstance(entry.get("t"), (int, float)) or entry["t"] < cutoff:
            continue
        commands.append(str(entry.get("command") or ""))
    return commands
