"""Pytest fixtures for proxy_pool tests.

Puts the scripts/ dir on sys.path so ``import proxy_pool`` works. The script
imports httpx2 at module load, so the test runner must provide it; run via:

    uv run --with pytest --with httpx2 python -m pytest tests/ -q
"""
import os
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS = os.path.join(os.path.dirname(_HERE), "scripts")
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)


@pytest.fixture
def store(tmp_path):
    """An empty proxy store directory."""
    return str(tmp_path)
