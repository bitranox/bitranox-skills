#!/usr/bin/env python3
"""PreToolUse(Bash|PowerShell) nudge: a hand-typed PATH inside `pct exec` that drops a standard dir.

`pct exec` hands a Proxmox container a minimal PATH (`/sbin:/bin:/usr/sbin:/usr/bin`), and a login
shell inside it does not add `/usr/local/bin`. So a tool installed there (uv, most hand-installed
binaries) dies with 127, and a `command -v` probe reports it missing. The fix is to set PATH - and
the miss that keeps coming back is setting a SHORTER one typed from memory:
`/usr/local/bin:/usr/bin:/bin` runs uv and then fails on runuser, postfix and postmap, which live
in /usr/sbin. Measured three times, the last as a handover line that a later session reused for a
deploy whose postfix steps then failed. Prose had already failed twice, which is why this is a hook.

NUDGE, not a block: the user chose warn-only. It emits `additionalContext` and exits 0.

What it flags: a `PATH=<value>` (as `env PATH=`, `export PATH=` or a prefix assignment) on the same
line after `pct exec`, where the value omits any of the six standard dirs and does not extend the
inherited `$PATH`. Order does not matter; a trailing slash does not matter.

What it deliberately leaves alone: a bare `pct exec` with no PATH (most calls run a /usr/bin tool
and are fine, so flagging them would teach the reader to ignore the channel), and a heredoc body
piped into `pct exec ... bash` - heredoc bodies are stripped because they are usually DATA (a doc,
a commit message), and a guard that reads them fires on the prose documenting its own footgun.

The scan runs with heredoc bodies AND data-sink statements stripped, the same way
sed-line1-range-nudge does: `echo` and `git commit -m` print their argument, `ssh` and `bash -c`
run it, so a real call inside an ssh argument is still seen.
"""

import json
import re
import sys

from shell_text import is_shell_tool, strip_data_sink_statements, strip_heredoc_bodies

FULL_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
_REQUIRED = tuple(FULL_PATH.split(":"))

# `pct exec <vmid> [--keep-env X] --` at a command position: not preceded by a word character or a
# hyphen, so `cmpct` and `--pct` are excluded while `/usr/sbin/pct` and `'pct` (inside an ssh
# argument) match - the same anchor as sed-line1-range-nudge, for the reason given there. Requiring
# the vmid and the `--` is what keeps a SENTENCE about the trap quiet ("a pct exec line with env
# PATH=..." in some tool's --what argument fired on the first replay over real transcripts), while
# every real call has both: pct needs `--` before a command that takes options.
_PCT_EXEC = re.compile(r"(?<![\w-])pct\s+exec\s+\S+(?:\s+--keep-env(?:=\S+|\s+\S+))?\s+--(?=\s)")

# A PATH assignment: `PATH=` not preceded by a word character, so LD_LIBRARY_PATH= and MYPATH= are
# not it. The value runs to the first character that ends a shell word.
_PATH_ASSIGN = re.compile(r"""(?<![\w$])PATH=["']?(?P<val>[^\s'";&|)`]*)""")


def _missing_dirs(value):
    """The standard dirs a typed PATH value omits, or () when it is complete or extends $PATH."""
    if not value or "$" in value:
        return ()
    entries = {entry.rstrip("/") or "/" for entry in value.split(":")}
    return tuple(d for d in _REQUIRED if d not in entries)


def _short_paths(text):
    """Yield the missing-dir tuple for each short PATH set on a line after `pct exec`."""
    for match in _PCT_EXEC.finditer(text):
        end = text.find("\n", match.end())
        tail = text[match.end(): end if end != -1 else len(text)]
        for assign in _PATH_ASSIGN.finditer(tail):
            missing = _missing_dirs(assign.group("val"))
            if missing:
                yield missing


def notice(command, tool_name=None):
    """The warning text when this command sets a short PATH inside `pct exec`, else None."""
    if not command or not isinstance(command, str):
        return None
    try:
        text = strip_data_sink_statements(strip_heredoc_bodies(command), tool_name)
        found = next(_short_paths(text), None)
    except Exception:  # noqa: BLE001 - a nudge must never wedge a turn
        return None
    if not found:
        return None
    return (
        "`pct exec` with a hand-typed PATH that is missing: %s. Tools in those dirs will fail with "
        "127 'command not found' inside the container (runuser, useradd, postfix and postmap live "
        "in /usr/sbin; uv usually in /usr/local/bin), and a `command -v` probe will call an "
        "installed tool missing. Copy the full PATH rather than retyping a shorter one: "
        "`env PATH=%s`. Measured three times; the last was a short line reused from a handover "
        "that broke a deploy's postfix steps." % (" ".join(found), FULL_PATH)
    )


def main(raw=None) -> int:
    """Read the hook event, emit additionalContext when the shape matches. Always exits 0."""
    try:
        payload = json.loads(raw if raw is not None else sys.stdin.read() or "{}")
    except (ValueError, TypeError):
        return 0
    if not isinstance(payload, dict) or not is_shell_tool(payload.get("tool_name")):
        return 0
    tool_input = payload.get("tool_input")
    command = tool_input.get("command") if isinstance(tool_input, dict) else None
    try:
        text = notice(command, payload.get("tool_name"))
    except Exception:  # noqa: BLE001
        return 0
    if not text:
        return 0
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                             "additionalContext": text}}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
