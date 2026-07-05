"""Pytest config: put the skill dir (parent of tests/) on sys.path so ``import dream_state`` works."""
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
if str(SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR))

# fixture harness scripts live IN tests/; make them importable as modules too
TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))
HOOKS_DIR = SKILL_DIR.parent.parent / "hooks"
if str(HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(HOOKS_DIR))
