#!/usr/bin/env python3
"""PreToolUse(Edit|Write|NotebookEdit) guard: Claude Code config JSON goes through update-config.

Hand-editing `settings.json` is the `no-hand-edit-config-json` footgun applied to the file that
decides how the harness itself behaves: a stray comma or a key at the wrong nesting level does not
fail loudly, it silently drops a hook, a permission rule or an env var, and the next symptom is a
guard that no longer fires. The host `update-config` skill knows the schema and the merge rules.

WHY HERE AND NOT ON `ConfigChange`, which looks like the obvious event. `ConfigChange` fires when a
configuration file changes during a session and its input carries `source` and `file_path` and NO
ACTOR. A user editing their own settings in an editor trips it exactly like the agent writing the
file, and its only verdict is `block` - so a guard there would block the user from editing their
own configuration, with no way to tell the two cases apart. A `PreToolUse` file-tool event is the
seam where the actor IS the agent by construction, which is the property this rule needs.

BLOCKS, with a bypass, matching its two siblings: `store-edit-guard` exempts the memory engine via
`BITRANOX_MEMORY_ENGINE` and `skill-edit-guard` exempts the skill-writer via
`BITRANOX_SKILL_WRITER`. An iron rule enforced by a reminder is enforced by goodwill.

Their exempted writer is code in this plugin, which sets the variable itself. The sanctioned writer
here is the host `update-config` skill, which this plugin does not control and cannot make set
anything - so the exemption is detected instead. MEASURED, not assumed: `update-config`'s own
workflow says "Edit file - Use Edit tool", and driving this guard with the event that step produces
returned exit 2. Without the detection below, enforcing the rule blocks the very skill the rule
tells you to use.

The detection reads the transcript for the skill BODY, which arrives as a user-role message when a
skill is invoked. It keys on the body's H1, never on the bare name `update-config`: that name
appears in ordinary prose about the rule - 57 times in the session that built this - so a name
match would disarm the guard for anyone who merely discussed it.

Scoped to a bounded TAIL of the transcript rather than the whole file, for two reasons. It runs on
every file-tool call, so it must not read a 34 MB transcript; and a skill invoked an hour ago should
not disarm the guard for the rest of the session.

Windows paths arrive with BACKSLASH separators even under Git Bash, so the path is normalised
before any segment match; a `/`-anchored comparison would silently never fire there.

Pure standard library, ASCII only; launched via run-python.sh so it works on Windows too.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

_TOOLS = {"Edit", "Write", "NotebookEdit", "MultiEdit"}
_BYPASS_ENV = "BITRANOX_CONFIG_EDIT"

# The H1 of the host update-config skill body. Distinctive enough that prose about the skill does
# not match it, which the bare name would.
_UPDATE_CONFIG_MARK = "# Update Config Skill"

# How much of the transcript tail to scan. Big enough to span a skill invocation and the Read that
# follows it before the Edit; small enough to stay a single cheap seek on a multi-megabyte file.
_TAIL_BYTES = 1_000_000

# The Claude Code configuration files this rule covers, matched on a path SEGMENT rather than
# anchored, because `file_path` is always absolute and its prefix varies per machine and per
# project. `.claude.json` is the user-level file that sits directly in the home directory.
_CONFIG_PATHS = re.compile(
    r"(?:^|/)(?:\.claude/settings(?:\.local)?\.json"
    r"|\.claude\.json"
    r"|managed-settings\.json)$",
    re.IGNORECASE,
)

_DENY = (
    "Refusing a direct edit of %s. Claude Code configuration JSON decides how the harness itself "
    "behaves, and a misplaced key or comma does not fail loudly - it silently drops a hook, a "
    "permission rule or an env var, and the next symptom is a guard that stopped firing. The host "
    "`update-config` skill owns this surface: it knows the schema, the settings precedence and the "
    "merge rules, and routing through it is what the no-hand-edit-config-json rule asks for. Use "
    "it for permissions, env vars and hook registration.\n\n"
    "If you are acting AS update-config, or this path is a fixture that merely looks like a "
    "settings file, set %s=1 for that one command. Setting it because the block is in the way is "
    "the habit this guard exists to prevent - the rule is an iron rule precisely because the "
    "damage it prevents is silent."
)


def targets_config(file_path) -> bool:
    """True when this path is Claude Code configuration JSON. PURE.

    Backslashes are normalised first: on Windows `file_path` arrives with `\\` separators even when
    the hook runs under Git Bash, so a forward-slash segment test would never match there and the
    edit would proceed exactly as if the hook had found nothing.
    """
    normalised = str(file_path or "").replace("\\", "/")
    return bool(_CONFIG_PATHS.search(normalised))


def _texts(record) -> list:
    """Every text block of a user-role message in this record. PURE."""
    message = record.get("message") or {}
    if message.get("role") != "user":
        return []
    content = message.get("content")
    if isinstance(content, str):
        return [content]
    if not isinstance(content, list):
        return []
    return [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"]


def _is_skill_body(line: str) -> bool:
    """True when this transcript line IS the update-config skill body. PURE.

    The marker must START the text, which is what separates the injected skill body from the ten
    other places the same string appears once anyone documents this guard.
    """
    try:
        record = json.loads(line)
    except (ValueError, TypeError):
        return False                                      # a tail read can start mid-line
    if not isinstance(record, dict) or record.get("type") != "user":
        return False
    return any(text.lstrip().startswith(_UPDATE_CONFIG_MARK) for text in _texts(record))


def update_config_active(transcript_path) -> bool:
    """True when the update-config skill body appears in the recent transcript. IMPURE (reads it).

    An ABSENT path is not an exemption. `transcript_path` is present on every real event, so a
    missing one means a malformed or synthetic event, and treating that as "update-config is
    running" would let any such event disarm the guard.

    A path that is present but UNREADABLE fails open, because that is a genuine IO problem on a real
    event and blocking the sanctioned path is the failure this detection exists to prevent.
    """
    if not transcript_path:
        return False
    try:
        path = Path(str(transcript_path))
        size = path.stat().st_size
        with path.open("rb") as handle:
            if size > _TAIL_BYTES:
                handle.seek(size - _TAIL_BYTES)
            tail = handle.read().decode("utf-8", errors="replace")
    except (OSError, ValueError):
        return True
    return any(_is_skill_body(line) for line in tail.splitlines())


def decide(event, env):
    """The block reason for this event, or None to allow silently. PURE in `event` and `env`."""
    if not isinstance(event, dict) or event.get("tool_name") not in _TOOLS:
        return None
    path = (event.get("tool_input") or {}).get("file_path")
    if not targets_config(path):
        return None
    if env.get(_BYPASS_ENV):
        return None
    if update_config_active(event.get("transcript_path")):
        return None
    return _DENY % (path, _BYPASS_ENV)


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:  # noqa: BLE001 - no/invalid stdin: do nothing
        return 0
    try:
        reason = decide(event, os.environ)
    except Exception:  # noqa: BLE001 - a broken guard must never wedge a turn
        return 0
    if reason is None:
        return 0
    sys.stderr.write("CONFIG-EDIT GUARD: " + reason + "\n")
    return 2  # PreToolUse: exit 2 blocks the tool call and feeds stderr back to the model


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - a broken hook must never wedge a turn
        sys.exit(0)
