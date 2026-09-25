"""Put the skill scripts/ dir on sys.path so tests can import each tool by module name."""
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


@pytest.fixture(autouse=True)
def _private_state(tmp_path, monkeypatch):
    """Keep every test out of the real per-user state and config.

    A snapshot verb that ignores its --snapshot-dir falls back to the XDG state dir, and a test for
    exactly that bug once wrote a fake config.xml into the operator's real snapshot directory. The
    named-target file is pointed into tmp_path for the same reason.
    """
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "xdg-state"))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("PFSENSE_JIG_CONFIG", str(tmp_path / "home" / "pfsense.ini"))
