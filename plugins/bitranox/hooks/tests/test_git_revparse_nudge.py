"""`git rev-parse <name>` without --verify ECHOES THE NAME BACK instead of failing on a bad ref.

From `feedback-wrong-repo-git-plus-a-plain-rev-parse-fabricates-a-confident-false-result`
(recurrence 2): comparing refs with a plain rev-parse produces a confident, plausible, wrong
answer - the string you passed in - so a comparison against it silently succeeds.
"""
import importlib.util
import pathlib

import pytest

_HOOK = pathlib.Path(__file__).resolve().parent.parent / "git-revparse-nudge.py"
_spec = importlib.util.spec_from_file_location("git_revparse_nudge", _HOOK)
N = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(N)


@pytest.mark.parametrize("command", [
    "git rev-parse origin/master",
    "cd /repo && git rev-parse HEAD~1",
    'A=$(git rev-parse mybranch); echo "$A"',
    "git rev-parse v1.2.3",
])
def test_a_bare_rev_parse_of_a_ref_is_nudged(command):
    notice = N.notice(command)
    assert notice is not None
    assert "--verify" in notice


@pytest.mark.parametrize("command", [
    "git rev-parse --verify -q origin/master",
    "git rev-parse --show-toplevel",
    "git rev-parse --abbrev-ref HEAD",
    "git rev-parse --git-dir",
    "git rev-parse --is-inside-work-tree",
])
def test_the_safe_and_informational_forms_are_untouched(command):
    """The negative must be reachable: these are the forms the rule asks for, or ask nothing."""
    assert N.notice(command) is None


def test_an_unrelated_git_command_is_untouched():
    assert N.notice("git status --porcelain") is None
    assert N.notice("git log --oneline -3") is None


def test_prose_mentioning_the_footgun_does_not_fire():
    """A guard that blocks its own documentation is the classic failure."""
    doc = "cat > note.md <<'EOF'\nnever use git rev-parse origin/master bare\nEOF"
    assert N.notice(doc) is None


def test_junk_is_ignored():
    assert N.notice("") is None
    assert N.notice(None) is None
