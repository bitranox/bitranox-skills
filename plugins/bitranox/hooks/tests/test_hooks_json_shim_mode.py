"""Every hooks.json registration launches the shim in HOOK mode.

run-python.sh is loud by default (exit 3 when it cannot run the script), which is right for a CLI
caller and wrong for a hook: a registration that forgets `--hook` turns a missing interpreter into
a non-blocking error notice on every event instead of a silent skip. Nothing else would report the
omission, so it is pinned here. This test reads JSON only, so it runs on every platform.
"""

import json
import re
from pathlib import Path

HOOKS_JSON = Path(__file__).resolve().parent.parent / "hooks.json"
CONFIG = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))["hooks"]
SHAPE = re.compile(
    r'^bash "\$\{CLAUDE_PLUGIN_ROOT\}/hooks/run-python\.sh" --hook '
    r'"\$\{CLAUDE_PLUGIN_ROOT\}/hooks/[\w.-]+\.py"$'
)


def _commands():
    return [(event, handler["command"]) for event, groups in CONFIG.items()
            for group in groups for handler in group["hooks"]]


def test_there_are_registrations_to_check():
    assert len(_commands()) > 0


def test_every_registration_launches_the_shim_in_hook_mode():
    bad = [(event, command) for event, command in _commands() if not SHAPE.match(command)]
    assert bad == []
