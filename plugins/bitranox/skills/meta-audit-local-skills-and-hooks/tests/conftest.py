"""Put the skill's scripts dir and the plugin's hooks dir on sys.path for the tests."""

import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
HOOKS_DIR = SKILL_DIR.parent.parent / "hooks"

for _path in (SKILL_DIR / "scripts", HOOKS_DIR):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))
