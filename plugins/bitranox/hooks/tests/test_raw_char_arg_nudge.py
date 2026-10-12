"""Tests for raw-char-arg-nudge: a raw control or invisible character in a tool argument. ASCII only.

Every character under test is built with chr(): this file exists because an escape typed into a
tool argument arrives as the raw character, so writing one here would plant the very thing the
hook reports.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

import raw_char_arg_nudge as N

HOOK = Path(__file__).resolve().parents[1] / "raw-char-arg-nudge.py"

RLO = chr(0x202E)   # RIGHT-TO-LEFT OVERRIDE
ZWSP = chr(0x200B)  # ZERO WIDTH SPACE
CSI = chr(0x9B)     # a C1 control
LSEP = chr(0x2028)  # LINE SEPARATOR
ESC = chr(0x1B)
TAG = chr(0xE0041)  # TAG LATIN CAPITAL LETTER A, invisible
UMLAUT = chr(0xFC)


@pytest.mark.parametrize(("tool", "tool_input", "field"), [
    ("Write", {"file_path": "/x/t.py", "content": f'x = "a{RLO}b"\n'}, "content"),
    ("Edit", {"file_path": "/x/t.py", "old_string": "a", "new_string": f"a{CSI}"}, "new_string"),
    ("NotebookEdit", {"notebook_path": "/x/n.ipynb", "new_source": f"print('{ZWSP}')"}, "new_source"),
    ("Bash", {"command": f"printf 'a{LSEP}b' > f"}, "command"),
    ("PowerShell", {"command": f"Write-Output 'a{ESC}[31m'"}, "command"),
    ("Agent", {"prompt": f"write the digit {TAG} as an escape"}, "prompt"),
    ("Task", {"prompt": f"x{RLO}"}, "prompt"),
])
def test_a_raw_control_or_invisible_character_in_what_a_tool_writes_is_named(tool, tool_input, field):
    message = N.notice(tool, tool_input)
    assert message is not None
    assert field in message
    assert "chr(92)" in message


def test_the_notice_names_each_character_by_code_point_and_name():
    message = N.notice("Write", {"content": f"{RLO}{RLO}{CSI}"})
    assert "U+202E RIGHT-TO-LEFT OVERRIDE x2" in message
    assert "U+009B" in message


def test_a_multiedit_is_checked_in_every_edit():
    tool_input = {"file_path": "/x/a.py", "edits": [{"old_string": "a", "new_string": "b"},
                                                    {"old_string": "c", "new_string": f"d{ZWSP}"}]}
    message = N.notice("MultiEdit", tool_input)
    assert message is not None and "edits[1].new_string" in message


def test_a_character_only_in_old_string_is_left_alone():
    # Matching a raw character that is already in the file is how you REMOVE it.
    assert N.notice("Edit", {"old_string": f"a{RLO}b", "new_string": "ab"}) is None


@pytest.mark.parametrize("text", [
    "plain ascii\n", "tab\there\r\nand crlf", f"K{UMLAUT}che", "emoji " + chr(0x1F600),
    "an escape spelled as text: \\u202e and \\x1b", "",
])
def test_ordinary_text_including_non_ascii_letters_and_spelled_escapes_is_left_alone(text):
    assert N.notice("Write", {"content": text}) is None
    assert N.notice("Bash", {"command": text}) is None


def test_a_tool_that_writes_nothing_is_left_alone():
    assert N.notice("Read", {"file_path": f"/x/{RLO}"}) is None


@pytest.mark.parametrize("tool_input", [None, "not a dict", {"content": 5}, {"edits": "nope"},
                                        {"edits": [5, {"new_string": None}]}])
def test_malformed_input_never_raises(tool_input):
    assert N.notice("MultiEdit", tool_input) is None
    assert N.notice("Write", tool_input) is None


def _run(event: object) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(HOOK)], input=json.dumps(event), capture_output=True,
                          text=True, encoding="utf-8", check=False)


def test_the_hook_emits_pretooluse_context_and_exits_0():
    done = _run({"hook_event_name": "PreToolUse", "tool_name": "Write",
                 "tool_input": {"file_path": "/x/t.txt", "content": RLO}})
    assert done.returncode == 0
    output = json.loads(done.stdout)["hookSpecificOutput"]
    assert output["hookEventName"] == "PreToolUse"
    assert "U+202E" in output["additionalContext"]


def test_the_hook_is_silent_on_clean_input_and_on_junk_stdin():
    clean = _run({"tool_name": "Write", "tool_input": {"content": "ok"}})
    assert (clean.returncode, clean.stdout) == (0, "")
    junk = subprocess.run([sys.executable, str(HOOK)], input="not json", capture_output=True, text=True, check=False)
    assert (junk.returncode, junk.stdout) == (0, "")


# --- the blocking half: where a raw character is never wanted and the damage is lasting ---------

BOM = chr(0xFEFF)
DE_OPEN, DE_CLOSE = chr(0x201E), chr(0x201C)  # German quotation marks: visible, never a tell
GUILLEMETS = chr(0xBB) + "x" + chr(0xAB)


@pytest.mark.parametrize("command", [
    # The shape that shipped a RIGHT-TO-LEFT OVERRIDE: the heredoc writes the message file and the
    # same call commits it, so a check reading the -F file before the call finds nothing yet.
    f"cat > /tmp/m.txt <<'EOF'\nfix: the {RLO} thing\nEOF\ngit commit a.py -F /tmp/m.txt",
    f'git -C /repo commit -m "fix{ZWSP}"',
    f"git tag -a v1.0.0 -m 'release {LSEP}'",
    f"cd /repo && git -c user.name=x commit --amend -F m.txt  # {RLO}",
])
def test_a_shell_call_that_commits_or_tags_with_a_raw_character_is_blocked(command):
    reason = N.block_reason("Bash", {"command": command})
    assert reason is not None
    assert "U+" in reason and "chr(92)" in reason


@pytest.mark.parametrize("command", [
    f"printf 'a{LSEP}b' > f",
    f"echo 'git commit -m x' {RLO}",
    f"cat > run.sh <<'EOF'\ngit commit -m x{RLO}\nEOF",
    f"git log --format=%s{ZWSP}",
])
def test_a_shell_call_that_neither_commits_nor_tags_is_only_nudged(command):
    assert N.block_reason("Bash", {"command": command}) is None
    assert N.notice("Bash", {"command": command}) is not None


@pytest.mark.parametrize(("tool", "tool_input"), [
    ("Write", {"file_path": "/x/t.py", "content": f'x = "a{RLO}b"\n'}),
    ("Write", {"file_path": "/x/README.MD", "content": f"{BOM}# Title\n"}),
    ("Write", {"file_path": "/x/pyproject.toml", "content": f'name = "x{ZWSP}"\n'}),
    ("Edit", {"file_path": "/x/t.Py", "old_string": "a", "new_string": f"a{CSI}"}),
    ("MultiEdit", {"file_path": "/x/doc.md", "edits": [{"old_string": "a", "new_string": f"b{TAG}"}]}),
])
def test_a_write_or_edit_to_source_docs_or_toml_with_a_raw_character_is_blocked(tool, tool_input):
    assert N.block_reason(tool, tool_input) is not None


@pytest.mark.parametrize(("tool", "tool_input"), [
    ("Write", {"file_path": "/x/data.bin.txt", "content": f"{BOM}payload"}),
    ("NotebookEdit", {"notebook_path": "/x/n.ipynb", "new_source": f"print('{ZWSP}')"}),
    ("Agent", {"prompt": f"x{RLO}"}),
    ("Edit", {"file_path": "/x/t.py", "old_string": f"a{RLO}b", "new_string": "ab"}),
])
def test_other_targets_and_removals_are_not_blocked(tool, tool_input):
    assert N.block_reason(tool, tool_input) is None


@pytest.mark.parametrize("text", [f"K{UMLAUT}che", f"{DE_OPEN}Zitat{DE_CLOSE}", GUILLEMETS, "plain"])
def test_visible_non_ascii_is_never_blocked(text):
    assert N.block_reason("Write", {"file_path": "/x/a.md", "content": text}) is None
    assert N.block_reason("Bash", {"command": f"git commit -m '{text}'"}) is None


@pytest.mark.parametrize("tool_input", [None, "x", {"file_path": 5, "content": RLO},
                                        {"command": None}, {"file_path": "/a.py", "edits": "no"}])
def test_block_reason_never_raises_on_malformed_input(tool_input):
    for tool in ("Write", "Edit", "MultiEdit", "Bash"):
        assert N.block_reason(tool, tool_input) is None


def test_the_hook_blocks_with_exit_2_and_names_the_character_without_quoting_the_text():
    secretish = "do-not-echo-me"
    done = _run({"hook_event_name": "PreToolUse", "tool_name": "Bash",
                 "tool_input": {"command": f"git commit -m '{secretish}{RLO}'"}})
    assert done.returncode == 2
    assert "U+202E RIGHT-TO-LEFT OVERRIDE" in done.stderr
    assert secretish not in done.stderr
    assert done.stdout == ""


def test_the_hook_still_only_nudges_where_it_does_not_block():
    done = _run({"tool_name": "Write", "tool_input": {"file_path": "/x/notes.txt", "content": RLO}})
    assert done.returncode == 0
    assert "U+202E" in json.loads(done.stdout)["hookSpecificOutput"]["additionalContext"]
