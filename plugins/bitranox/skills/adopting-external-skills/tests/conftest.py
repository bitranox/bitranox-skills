"""Pytest config: put the skill dir (parent of tests/) on sys.path.

This makes ``import adopt_skill`` work regardless of the cwd pytest is launched from.
"""
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
if str(SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR))
