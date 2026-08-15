"""Run the mutation harness as part of the suite.

A checker nobody runs is the same defect as a test that does not collect, so this wires
`mutation_check.py` into `pytest tests/`. It costs a few seconds: it applies each mutant in an
isolated copy and runs the srccount tests against it.

No recursion risk - mutation_check copies conftest.py and test_srccount.py explicitly, never
this file, so the sub-run cannot re-enter the harness.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HARNESS = Path(__file__).resolve().parent / "mutation_check.py"


def test_every_safety_test_notices_its_mutant() -> None:
    """Exit 0 means each mutant killed exactly the tests that claim to cover it.

    Proven to discriminate: with `test_a_pyvenv_cfg_without_the_home_key_does_not_exclude`
    weakened to `assert True`, the ordinary suite still reported 62 passed while this reported
    VACUOUS and exited 1.
    """
    done = subprocess.run(
        [sys.executable, str(HARNESS)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    assert done.returncode == 0, f"mutation check failed:\n{done.stdout}\n{done.stderr}"
