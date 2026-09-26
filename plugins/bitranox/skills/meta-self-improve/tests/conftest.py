"""Pytest config: put the skill dir (parent of tests/) on sys.path, and provide `short_root`.

Makes ``import reconcile_memory_index`` work regardless of the cwd pytest runs from.
"""
import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parent.parent
if str(SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR))


# Leaves ~90 characters of slug for the fixture's own components under the 200-character cap.
_TEMP_BASE_MAX = 100


def _short_bases():
    """Candidate parents for `short_root`, in order of preference.

    The platform temp dir comes first while it is short enough: the anchor resolver refuses to
    anchor AT that dir, so a stray CLAUDE.md left there cannot hijack a fixture tree. Only a temp
    dir too long for the slug cap falls back to /tmp (POSIX)."""
    temp = tempfile.gettempdir()
    bases = [temp]
    if os.name == "posix" and temp != "/tmp":
        bases.append("/tmp")
    if len(temp) > _TEMP_BASE_MAX:
        bases.sort(key=len)
    return bases


@pytest.fixture
def short_root():
    """A fresh, resolved directory whose path is as SHORT as this machine allows.

    A project path is encoded into a Claude project slug that is capped at 200 characters (past
    that the tail is a hash and cannot be decoded), and the migration's receipt filename is the
    whole path again. pytest's `tmp_path` adds the test's own name under $TMPDIR, so a long
    TMPDIR pushed fixture paths over both limits and the migration tests failed for a reason
    that has nothing to do with the code. This root is `<shortest base>/<~10 chars>`."""
    last = None
    for base in _short_bases():
        try:
            root = Path(tempfile.mkdtemp(prefix="mm", dir=base)).resolve()
        except OSError as exc:
            last = exc
            continue
        try:
            yield root
        finally:
            shutil.rmtree(root, ignore_errors=True)
        return
    raise RuntimeError("no writable temp base for short_root: %s" % last)
