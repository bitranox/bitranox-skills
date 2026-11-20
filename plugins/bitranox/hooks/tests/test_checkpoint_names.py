"""The checkpoint-name rule both context hooks share.

`context-watcher.py` and `compact-resume.py` once kept a copy each, held equal by a test comparing
the two. Both now import `checkpoint_names`, so these tests pin the rule itself: every name the
comparison covered, with its expected answer written out, plus a random sweep against an
independent regular-expression statement of the same rule.
"""

import random
import re
import subprocess
import sys
from pathlib import Path

import pytest

import checkpoint_names
import compact_resume
import context_watcher

HOOKS_DIR = Path(__file__).resolve().parent.parent


@pytest.mark.parametrize(("name", "expected"), [
    # the canonical name
    ("handover.md", True),
    # `<anything>-handover.md`
    ("release-handover.md", True), ("wt-x-handover.md", True), ("-handover.md", False),
    ("a-handover.md.md", False), ("x-handover.md.bak", False), ("xhandover.md", False),
    ("myhandover.md", False),
    # `handover-<topic>.md`
    ("handover-latch.md", True), ("handover-crud-design.md", True),
    ("handover-a-handover.md", True), ("handover-.md", False), ("handover-x.md.bak", False),
    ("handover-x.txt", False),
    # neither form
    ("handover.prev.md", False), ("handover.txt", False), ("handovers.md", False),
    ("HANDOVER.md", False), ("notes.md", False), ("", False), ("handover", False),
])
def test_is_checkpoint_name(name, expected):
    assert checkpoint_names.is_checkpoint_name(name) is expected


# The same rule stated a second way: an exact `handover.md`, or one of the two improvised forms
# with at least one character in its open part.
_ORACLE = re.compile(r"handover\.md|.+-handover\.md|handover-.+\.md", re.DOTALL)


def test_a_random_name_sweep_matches_the_rule_stated_as_a_regex():
    rng = random.Random(100)
    parts = ["handover", "-", ".md", "x", "handover-", "-handover.md", ".", "md", "\n"]
    answers = set()
    for _ in range(5000):
        name = "".join(rng.choice(parts) for _ in range(rng.randint(0, 4)))
        expected = _ORACLE.fullmatch(name) is not None
        assert checkpoint_names.is_checkpoint_name(name) is expected, repr(name)
        answers.add(expected)
    assert answers == {True, False}       # the sweep reached both answers, not just one


def test_both_hooks_use_the_shared_rule():
    """Neither hook keeps a copy of its own any more."""
    for hook in (compact_resume, context_watcher):
        assert getattr(hook, "checkpoint_names", None) is checkpoint_names
        assert not hasattr(hook, "is_checkpoint_name")


@pytest.mark.parametrize("hook", ["context-watcher.py", "compact-resume.py"])
def test_each_hook_imports_it_when_run_from_another_directory(hook, tmp_path):
    """Run as a script, a hook finds the module beside it whatever the working directory."""
    done = subprocess.run([sys.executable, str(HOOKS_DIR / hook)], input="", cwd=tmp_path,
                          capture_output=True, text=True, encoding="utf-8", timeout=60,
                          check=False)
    assert "ModuleNotFoundError" not in done.stderr
    assert done.returncode == 0
