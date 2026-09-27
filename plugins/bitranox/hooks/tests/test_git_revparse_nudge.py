"""`git rev-parse <name>` without --verify ECHOES THE NAME BACK instead of failing on a bad ref.

From `feedback-wrong-repo-git-plus-a-plain-rev-parse-fabricates-a-confident-false-result`
(recurrence 2): comparing refs with a plain rev-parse produces a confident, plausible, wrong
answer - the string you passed in - so a comparison against it silently succeeds.
"""
import importlib.util
import os
import pathlib
import shutil
import subprocess

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


def test_a_redirection_target_is_not_a_revision():
    """`git rev-parse 2>/dev/null` is the standard am-I-in-a-repo idiom and names no ref at all.
    The redirection was left in the operand list, so it counted as a revision to resolve."""
    assert N.notice("git rev-parse 2>/dev/null") is None


def test_a_real_bare_rev_parse_is_still_nudged():
    """The direction where it must NOT apply."""
    assert N.notice("git rev-parse master") is not None


# --- the mechanism the notice states must be the one git has -------------------------------------

def _git(repo, *args):
    env = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
           "LC_ALL": "C"}
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=env, timeout=60)


@pytest.mark.skipif(shutil.which("git") is None, reason="needs a real git to measure")
def test_the_notice_states_the_exit_codes_real_git_gives(tmp_path):
    # Both halves measured against real git: an unresolvable name that is NOT a path still prints
    # the name on stdout but exits 128; it exits 0 only when the name is also a working-tree path.
    # The notice used to claim "exits 0" for every unresolvable ref, which is wrong for the common
    # case and invites the reader to disbelieve the rest of it.
    assert _git(tmp_path, "init", "-q").returncode == 0
    (tmp_path / "afile").write_text("x", encoding="utf-8")
    ref = _git(tmp_path, "rev-parse", "nosuchref")
    path = _git(tmp_path, "rev-parse", "afile")
    assert (ref.returncode, ref.stdout.strip()) == (128, "nosuchref")
    assert (path.returncode, path.stdout.strip()) == (0, "afile")
    for text in (N._NOTICE, N.__doc__):
        flat = " ".join(text.split())
        assert "128" in flat and "path" in flat, text
        assert "verbatim and exits 0" not in flat, text
