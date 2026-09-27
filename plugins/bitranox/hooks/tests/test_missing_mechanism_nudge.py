"""A memory hook that asserts a mechanism is MISSING must be checked against the init path first.

The fact `feedback-verify-a-missing-mechanism-premise-before-filing-or-documenting-it` sits at
recurrence 5 with no endpoint. The enshrining moment is the `memory_engine add` that writes the
claim into always-loaded context, and the claim is usually right there in the `--hook`, so that is
where the check belongs - not a broad scan of every markdown file.
"""
import importlib.util
import json
import pathlib
import shlex
import subprocess
import sys

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


# --- every spelling of the hook argument ------------------------------------------------

_BASE = "python3 hooks/memory_engine.py add --proj . --title T {hook} --body-file /tmp/b"


@pytest.mark.parametrize(
    "hook",
    [
        "--hook 'the retry is missing entirely'",
        '--hook="the retry is missing entirely"',
        "--hook='the retry is missing entirely'",
        '--hook "the retry is missing entirely"',
    ],
)
def test_every_spelling_of_the_hook_argument_is_read(hook):
    """The single-quoted form is the one the docs prescribe, and `--hook=` is argparse's own; a
    regex that knew only `--hook "..."` let both through unread."""
    assert N.notice(_BASE.format(hook=hook)) is not None


@pytest.mark.parametrize(
    "hook",
    [
        "--hook 'the retry is missing entirely, verified in engine.py line 40'",
        "--hook='When committing, use a pathspec.'",
    ],
)
def test_single_quoted_and_equals_forms_still_respect_the_negatives(hook):
    assert N.notice(_BASE.format(hook=hook)) is None


def test_a_single_quoted_hook_is_read_on_powershell():
    """PowerShell strings are single-quoted too, and its argv splitter does not know that."""
    command = "python memory_engine.py add --title T --hook 'the retry is missing entirely'"
    assert N.notice(command, tool_name="PowerShell") is not None


def test_a_hook_argument_of_another_command_is_not_a_memory_add():
    """The flag belongs to the statement it sits in: an echo QUOTING a memory add is not one."""
    assert N.notice("echo 'memory_engine.py add --hook \"the retry is missing entirely\"'") is None


# --- --hook-file ------------------------------------------------------------------------


def _hook_file_command(path_arg, equals=False):
    flag = f"--hook-file={path_arg}" if equals else f"--hook-file {path_arg}"
    return f"python3 hooks/memory_engine.py add --proj . --title T {flag} --body-file b.txt"


@pytest.mark.parametrize("equals", [False, True])
def test_a_claim_in_a_hook_file_is_read(tmp_path, equals):
    """memory-backend.md prescribes --hook-file for long hooks, so a claim routed through the file
    was never checked at all."""
    (tmp_path / "h.txt").write_text("the retry is missing entirely\n", encoding="utf-8")
    assert N.notice(_hook_file_command("h.txt", equals), cwd=str(tmp_path)) is not None


def test_a_hook_file_naming_its_evidence_is_left_alone(tmp_path):
    (tmp_path / "h.txt").write_text("missing entirely, see engine.py line 40\n", encoding="utf-8")
    assert N.notice(_hook_file_command("h.txt"), cwd=str(tmp_path)) is None


def test_an_absolute_hook_file_is_read_whatever_the_cwd(tmp_path):
    hook = tmp_path / "h.txt"
    hook.write_text("the opt-in defaults off\n", encoding="utf-8")
    # Quoted as bash needs it: a bare Windows path loses its backslashes to bash's escapes.
    assert N.notice(_hook_file_command(shlex.quote(str(hook))), cwd="/") is not None


def test_a_hook_file_that_does_not_exist_yet_is_silent(tmp_path):
    """PreToolUse runs before the command, so a file the same command writes is not there yet."""
    assert N.notice(_hook_file_command("h.txt"), cwd=str(tmp_path)) is None


def test_an_oversized_hook_file_is_not_read(tmp_path):
    """A hook is capped at 500 chars by the engine; anything far larger is not a hook, and reading
    an arbitrary large file on every PreToolUse is not this nudge's business."""
    (tmp_path / "h.txt").write_text("the retry is missing entirely\n" + "x" * 20000, encoding="utf-8")
    assert N.notice(_hook_file_command("h.txt"), cwd=str(tmp_path)) is None


def test_a_directory_named_as_the_hook_file_is_silent(tmp_path):
    (tmp_path / "h.txt").mkdir()
    assert N.notice(_hook_file_command("h.txt"), cwd=str(tmp_path)) is None


# --- main(): the event envelope ---------------------------------------------------------

_CLAIM_COMMAND = 'memory_engine.py add --proj . --title T --hook "the retry is missing entirely"'


def _run(stdin):
    return subprocess.run(
        [sys.executable, str(_HOOK)], input=stdin, capture_output=True, text=True, check=False
    )


@pytest.mark.parametrize("tool", ["Bash", "PowerShell"])
def test_main_emits_the_notice_for_a_shell_tool(tool):
    r = _run(json.dumps({"tool_name": tool, "tool_input": {"command": _CLAIM_COMMAND}}))
    assert r.returncode == 0
    payload = json.loads(r.stdout)
    assert payload["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
    assert "MISSING-MECHANISM" in payload["hookSpecificOutput"]["additionalContext"]


def test_main_is_silent_for_a_non_shell_tool():
    r = _run(json.dumps({"tool_name": "Read", "tool_input": {"command": _CLAIM_COMMAND}}))
    assert r.returncode == 0 and r.stdout.strip() == ""


@pytest.mark.parametrize("stdin", ["", "not json", "[1, 2]", '{"tool_name": "Bash", "tool_input": null}'])
def test_main_exits_zero_and_says_nothing_on_junk(stdin):
    r = _run(stdin)
    assert r.returncode == 0 and r.stdout.strip() == ""


def test_main_resolves_a_hook_file_against_the_event_cwd(tmp_path):
    (tmp_path / "h.txt").write_text("the retry is missing entirely\n", encoding="utf-8")
    event = {"tool_name": "Bash", "cwd": str(tmp_path),
             "tool_input": {"command": _hook_file_command("h.txt")}}
    r = _run(json.dumps(event))
    assert r.returncode == 0
    assert "MISSING-MECHANISM" in json.loads(r.stdout)["hookSpecificOutput"]["additionalContext"]
