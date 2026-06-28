"""Pytest config: put the skill dir (parent of tests/) on sys.path so ``import dream_state`` works."""
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
if str(SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR))
