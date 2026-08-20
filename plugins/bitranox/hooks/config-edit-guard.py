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

The bypass differs from theirs in one way that matters and is stated here rather than discovered
later. Their exempted writer is code in this plugin, which sets the variable itself. The sanctioned
writer here is the host `update-config` skill, which this plugin does not control and cannot make
set anything - so `BITRANOX_CONFIG_EDIT` has no automatic setter and a legitimate settings edit
will hit this block and have to export it. That is the accepted cost of enforcing the rule: the
block states the variable and why, so the exemption is a deliberate act rather than a silent one.
The deny message therefore has to be worth reading, because it is the only thing standing between
the reader and a habit of exporting the variable reflexively.

Windows paths arrive with BACKSLASH separators even under Git Bash, so the path is normalised
before any segment match; a `/`-anchored comparison would silently never fire there.

Pure standard library, ASCII only; launched via run-python.sh so it works on Windows too.
"""
from __future__ import annotations

import json
import os
import re
import sys

_TOOLS = {"Edit", "Write", "NotebookEdit", "MultiEdit"}
_BYPASS_ENV = "BITRANOX_CONFIG_EDIT"

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


def decide(event, env):
    """The block reason for this event, or None to allow silently. PURE in `event` and `env`."""
    if not isinstance(event, dict) or event.get("tool_name") not in _TOOLS:
        return None
    path = (event.get("tool_input") or {}).get("file_path")
    if not targets_config(path):
        return None
    if env.get(_BYPASS_ENV):
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
