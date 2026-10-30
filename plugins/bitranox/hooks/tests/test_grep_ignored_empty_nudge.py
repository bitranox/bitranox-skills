"""Tests for grep-ignored-empty-nudge.py: an EMPTY recursive grep under Claude Code's grep shim.

The payload shape is the one Claude Code 2.1.314 really delivers to a PostToolUse(Bash) hook,
captured with a probe hook: `tool_response` carries `stdout`, `stderr`, `interrupted`, `isImage`,
`noOutputExpected`, and for a grep that matched nothing (exit 1) also
`returnCodeInterpretation: "No matches found"`. A grep exiting 2 never reaches PostToolUse.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

import grep_ignored_empty_nudge as hook

HOOK_FILE = Path(__file__).resolve().parent.parent / "grep-ignored-empty-nudge.py"


def _payload(command, stdout="", *, tool_name="Bash", **response):
    tool_response = {"stdout": stdout, "stderr": "", "interrupted": False, "isImage": False,
                     "noOutputExpected": False}
    tool_response.update(response)
    return {"hook_event_name": "PostToolUse", "tool_name": tool_name,
            "tool_input": {"command": command, "description": "x"},
            "tool_response": tool_response}


def _run(payload, capsys):
    rc = hook.main(json.dumps(payload))
    return rc, capsys.readouterr().out


FIRES = [
    "grep -rn foo .",
    "grep -R foo /opt/data",
    "grep --recursive foo .",
    "grep --dereference-recursive foo .",
    "grep -rli foo .",
    "grep -nr foo",
    "grep -in -r foo /opt/a /opt/b",
    "grep -d recurse foo .",
    "grep --directories=recurse foo .",
    "grep --directories recurse foo .",
    "grep -rn -e foo .",
    "grep -rn --include='*.py' foo .",
    "cd /opt/data && grep -rn foo .",
    "grep -rn foo . | head -20",
    "grep -rn foo . | sort | uniq",
    "LC_ALL=C grep -rn foo .",
    "if grep -rn foo .; then echo y; fi",
    "\\grep -rn foo .",
    "'grep' -rn foo .",
    "( grep -rn foo . )",
    "(grep -rn foo .)",
    "! grep -rn foo .",
    "time grep -rn foo .",
    "grep -rn foo /opt/a; grep -rn bar /opt/b",
    "grep -rn 'two words' .",
    # the function runs inside a substitution too, and an empty call is the miss made silent
    "for f in $(grep -rl foo .); do echo $f; done",
    "if [ -n \"$(grep -rl foo .)\" ]; then echo found; fi",
    "x=$(grep -rl foo .)",
    "echo `grep -rl foo .`",
]


@pytest.mark.parametrize("command", FIRES)
def test_an_empty_recursive_grep_fires(command, capsys):
    rc, out = _run(_payload(command), capsys)
    assert rc == 0
    emitted = json.loads(out)["hookSpecificOutput"]
    assert emitted["hookEventName"] == "PostToolUse"
    assert "If grep is Claude Code's shim (check: declare -F grep)" in emitted["additionalContext"]
    assert "bash -c grep" in emitted["additionalContext"]
    assert "compuse-toolbox grep_all" in emitted["additionalContext"]


def test_the_message_is_the_decided_text_and_names_the_statement(capsys):
    _rc, out = _run(_payload("cd /opt/data && grep -rn foo ."), capsys)
    text = json.loads(out)["hookSpecificOutput"]["additionalContext"]
    assert text == ("`grep -rn foo .` returned no output. If grep is Claude Code's shim (check: "
                    "declare -F grep), it skips gitignored files; if this search must be complete, "
                    "re-run it with bash -c grep or compuse-toolbox grep_all (an empty result can "
                    "also be genuine).")


def test_the_message_does_not_assert_the_shim_is_active(capsys):
    """The payload cannot show whether grep is the shim, so the text must stay conditional."""
    _rc, out = _run(_payload("grep -rn foo ."), capsys)
    text = json.loads(out)["hookSpecificOutput"]["additionalContext"]
    assert "Claude Code's grep skips" not in text
    assert text.isascii()


def test_the_no_matches_interpretation_field_does_not_change_the_answer(capsys):
    _rc, out = _run(_payload("grep -rn foo .", returnCodeInterpretation="No matches found"), capsys)
    assert out


def test_whitespace_only_stdout_counts_as_empty(capsys):
    _rc, out = _run(_payload("grep -rn foo .", stdout="\n  \n"), capsys)
    assert out


def test_stderr_alone_does_not_count_as_output(capsys):
    _rc, out = _run(_payload("grep -rn foo .", stderr="grep: /opt/x: Permission denied"), capsys)
    assert out


SILENT = [
    # not recursive
    "grep foo file.txt",
    "grep -n foo a.txt b.txt",
    "grep -e -r file.txt",
    "grep -erfoo file.txt",
    "grep -- -r file.txt",
    "grep -d skip foo .",
    "grep -A 3 -B2 foo file.txt",
    # these run the real binary, which sees gitignored files
    "bash -c 'grep -rn foo .'",
    "sh -c \"grep -r foo .\"",
    "command grep -rn foo .",
    "/usr/bin/grep -rn foo .",
    "sudo grep -rn foo /etc",
    "timeout 5 grep -rn foo .",
    "env grep -rn foo .",
    "nice grep -rn foo .",
    "find . -name '*.py' | xargs grep -rn foo",
    "find . -exec grep -rn foo {} +",
    "uv run /opt/toolbox/scripts/grep_all.py foo .",
    # other programs
    "rg foo",
    "git grep -n foo",
    "egrep -r foo .",
    "fgrep -r foo .",
    # grep as data, not a program
    "echo \"grep -rn foo .\"",
    "printf '%s\\n' 'grep -rn foo .'",
    "cat <<'EOF'\ngrep -rn foo .\nEOF",
    # empty output says nothing about the hits
    "grep -rq foo .",
    "grep -r --quiet foo .",
    "grep -r --silent foo .",
    "grep -rL foo .",
    "grep -r --files-without-match foo .",
    # the shim hands these to the real grep itself
    "grep -rZ foo .",
    "grep -rnz foo .",
    "grep -rn --null foo .",
    "grep -rn --null-data foo .",
    "grep -rn --config=x foo .",
]


@pytest.mark.parametrize("command", SILENT)
def test_shapes_that_must_stay_silent(command, capsys):
    rc, out = _run(_payload(command), capsys)
    assert rc == 0
    assert out == ""


def test_a_recursive_grep_with_output_stays_silent(capsys):
    _rc, out = _run(_payload("grep -rn foo .", stdout="./a.py:1:foo"), capsys)
    assert out == ""


@pytest.mark.parametrize("extra", [
    {"interrupted": True},
    {"backgroundTaskId": "b1"},
])
def test_an_interrupted_or_backgrounded_call_stays_silent(extra, capsys):
    _rc, out = _run(_payload("grep -rn foo .", **extra), capsys)
    assert out == ""


def test_a_run_in_background_input_stays_silent(capsys):
    payload = _payload("grep -rn foo .")
    payload["tool_input"]["run_in_background"] = True
    _rc, out = _run(payload, capsys)
    assert out == ""


@pytest.mark.parametrize("tool_name", ["PowerShell", "Monitor", "Edit"])
def test_other_tools_stay_silent(tool_name, capsys):
    _rc, out = _run(_payload("grep -rn foo .", tool_name=tool_name), capsys)
    assert out == ""


@pytest.mark.parametrize("response", [None, "", "text", {"stderr": ""}, {"stdout": None}, []])
def test_a_response_without_a_stdout_string_stays_silent(response, capsys):
    payload = _payload("grep -rn foo .")
    payload["tool_response"] = response
    _rc, out = _run(payload, capsys)
    assert out == ""


@pytest.mark.parametrize("raw", ["", "not json", "[]", "null", json.dumps({"tool_name": "Bash"})])
def test_malformed_input_exits_zero_silently(raw, capsys):
    assert hook.main(raw) == 0
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("command", [None, 7, "", ["grep", "-r"]])
def test_a_command_that_is_not_text_stays_silent(command, capsys):
    _rc, out = _run(_payload(command), capsys)
    assert out == ""


def test_the_shipped_file_runs_end_to_end():
    """Through the real file and a real interpreter, as hooks.json launches it."""
    result = subprocess.run([sys.executable, str(HOOK_FILE)], input=json.dumps(_payload("grep -rn foo .")),
                            capture_output=True, text=True, encoding="utf-8", timeout=60, check=False)
    assert result.returncode == 0
    assert "compuse-toolbox grep_all" in json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]


def test_registered_in_hooks_json_under_post_tool_use_on_bash():
    config = json.loads((HOOK_FILE.parent / "hooks.json").read_text(encoding="utf-8"))["hooks"]
    groups = [g for g in config["PostToolUse"]
              if any("grep-ignored-empty-nudge.py" in h["command"] for h in g["hooks"])]
    assert len(groups) == 1
    assert "Bash" in groups[0]["matcher"].split("|")
