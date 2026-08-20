#!/usr/bin/env python3
"""PreToolUse(Edit|Write|NotebookEdit) nudge: Claude Code config JSON goes through update-config.

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

NON-BLOCKING, deliberately. The sanctioned path (`update-config`) edits these same files with these
same tools, and a hook cannot reliably tell that skill's write from a freehand one - a transcript
scan for a recent invocation would be a guess, and guessing wrong here means blocking the very fix
it is asking for. So it emits `additionalContext` and exits 0: the reminder arrives at the moment
of the edit, and a legitimate write proceeds untouched. If freehand edits are ever measured to slip
past this, the answer is to harden it into a block WITH a recognised bypass, not to reword it.

Windows paths arrive with BACKSLASH separators even under Git Bash, so the path is normalised
before any segment match; a `/`-anchored comparison would silently never fire there.

Pure standard library, ASCII only; launched via run-python.sh so it works on Windows too.
"""
from __future__ import annotations

import json
import re
import sys

_TOOLS = {"Edit", "Write", "NotebookEdit", "MultiEdit"}

# The Claude Code configuration files this rule covers, matched on a path SEGMENT rather than
# anchored, because `file_path` is always absolute and its prefix varies per machine and per
# project. `.claude.json` is the user-level file that sits directly in the home directory.
_CONFIG_PATHS = re.compile(
    r"(?:^|/)(?:\.claude/settings(?:\.local)?\.json"
    r"|\.claude\.json"
    r"|managed-settings\.json)$",
    re.IGNORECASE,
)

_MESSAGE = (
    "This edits Claude Code configuration JSON directly. That file decides how the harness itself "
    "behaves, and a misplaced key or comma does not fail loudly - it silently drops a hook, a "
    "permission rule or an env var, and the next symptom is a guard that stopped firing. The host "
    "`update-config` skill owns this surface: it knows the schema, the settings precedence and the "
    "merge rules, and it is the routing this project's no-hand-edit-config-json rule asks for. "
    "Use it for permissions, env vars and hook registration. If you are already acting as "
    "update-config, or this is a fixture or test file that merely looks like settings.json, carry "
    "on - this is a reminder, not a refusal."
)


def targets_config(file_path) -> bool:
    """True when this path is Claude Code configuration JSON. PURE.

    Backslashes are normalised first: on Windows `file_path` arrives with `\\` separators even when
    the hook runs under Git Bash, so a forward-slash segment test would never match there and the
    edit would proceed exactly as if the hook had found nothing.
    """
    normalised = str(file_path or "").replace("\\", "/")
    return bool(_CONFIG_PATHS.search(normalised))


def notice(event):
    """The reminder text for this event, or None to stay silent. PURE."""
    if not isinstance(event, dict) or event.get("tool_name") not in _TOOLS:
        return None
    path = (event.get("tool_input") or {}).get("file_path")
    return _MESSAGE if targets_config(path) else None


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except Exception:  # noqa: BLE001 - no/invalid stdin: do nothing
        return 0
    message = notice(event)
    if not message:
        return 0
    json.dump({"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                      "additionalContext": message}}, sys.stdout)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - a broken hook must never wedge a turn
        sys.exit(0)
