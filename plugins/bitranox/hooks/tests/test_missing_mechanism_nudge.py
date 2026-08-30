"""A memory hook that asserts a mechanism is MISSING must be checked against the init path first.

The fact `feedback-verify-a-missing-mechanism-premise-before-filing-or-documenting-it` sits at
recurrence 5 with no endpoint. The enshrining moment is the `memory_engine add` that writes the
claim into always-loaded context, and the claim is usually right there in the `--hook`, so that is
where the check belongs - not a broad scan of every markdown file.
"""
import importlib.util
import pathlib

import pytest

_HOOK = pathlib.Path(__file__).resolve().parent.parent / "missing-mechanism-nudge.py"
_spec = importlib.util.spec_from_file_location("missing_mechanism_nudge", _HOOK)
N = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(N)


CLAIMS = [
    'memory_engine.py add --hook "When X breaks, note the retry is missing entirely."',
    'memory_engine.py add --hook "The opt-in defaults off, so nobody gets it."',
    'memory_engine.py add --hook "When auditing, know the scrubber is not used anywhere."',
    'memory_engine.py add --hook "That branch is never called - it is dead code."',
    'memory_engine.py add --hook "The handler is not wired up at all."',
    'memory_engine.py add --hook "There is no caller for this path."',
]


@pytest.mark.parametrize("command", CLAIMS)
def test_a_missing_mechanism_claim_in_a_memory_hook_is_nudged(command):
    notice = N.notice(command)
    assert notice is not None
    assert "initialization" in notice.lower() or "init path" in notice.lower()


def test_an_ordinary_memory_add_is_untouched():
    """The negative must be reachable, or every capture nags."""
    assert N.notice('memory_engine.py add --hook "When a download times out, check the block table."') is None
    assert N.notice('memory_engine.py add --hook "When committing, use a pathspec."') is None


def test_the_same_words_outside_a_memory_add_are_not_this_hook_s_business():
    """Scoped to the enshrining moment on purpose - a grep or an echo is not filing a claim."""
    assert N.notice('grep -rn "is not used" src/') is None
    assert N.notice('echo "the retry is missing entirely"') is None


def test_a_claim_that_already_states_the_evidence_is_left_alone():
    """Naming the init path IS the check this asks for - nagging then is pure noise."""
    command = ('memory_engine.py add --hook "The opt-in defaults off: verified in '
               'composition/__init__.py line 40, nothing sets it."')
    assert N.notice(command) is None


def test_junk_is_ignored():
    assert N.notice("") is None
    assert N.notice(None) is None


def test_a_heredoc_body_is_not_a_memory_add():
    """A heredoc body is stdin DATA. Writing a doc that QUOTES a memory_engine add command is not
    running one, and firing there blocks the writing of the very guidance this nudge gives."""
    cmd = ('cat > note.md <<"EOF"\n'
           'Run: memory_engine.py add --hook "the retry is missing entirely"\n'
           'EOF')
    assert N.notice(cmd) is None


def test_a_real_memory_add_after_a_heredoc_is_still_noticed():
    """The direction where it must NOT apply: stripping the BODY must not swallow a real command
    standing after the terminator."""
    cmd = ('cat > note.md <<"EOF"\nprose\nEOF\n'
           'memory_engine.py add --hook "the retry is missing entirely"')
    assert N.notice(cmd) is not None
