"""Tests for block-index-splice.py: refuse a Bash call that RUNS a Python program splicing a file
between two found anchors (`s[:a] + new + s[b:]`). ASCII only."""

import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

import block_index_splice as G
import shell_text

HOOK = Path(__file__).resolve().parent.parent / "block-index-splice.py"

SPLICE_CMD = (
    "cd /opt/repo && python3 - <<'PY'\n"
    "from pathlib import Path\n"
    "p = Path('src/layout.py')\n"
    "s = p.read_text(encoding='utf-8')\n"
    "a = s.index('def natural_widths(')\n"
    "b = s.index('    return widths')\n"
    "p.write_text(s[:a] + NEW + s[b:], encoding='utf-8')\n"
    "PY\n"
)


def run_main(event):
    stdin, stderr = io.StringIO(json.dumps(event)), io.StringIO()
    old_in, old_err = sys.stdin, sys.stderr
    sys.stdin, sys.stderr = stdin, stderr
    try:
        rc = G.main()
    finally:
        sys.stdin, sys.stderr = old_in, old_err
    return rc, stderr.getvalue()


def bash(command, tool="Bash"):
    return {"tool_name": tool, "tool_input": {"command": command}, "session_id": "s1"}


# ---- the decision ------------------------------------------------------------------------------
def test_a_run_splice_is_refused():
    assert G.assess(SPLICE_CMD) is not None


def test_the_refusal_names_replace_span_with_a_usable_example():
    message = G.assess(SPLICE_CMD)
    assert "anchor_edit.py replace-span" in message
    for flag in ("--start-file", "--end-file", "--new-file", "--expect-removed-lines",
                 "--must-keep"):
        assert flag in message, flag


def test_the_refusal_points_at_a_script_that_exists():
    message = G.assess(SPLICE_CMD)
    assert str(G.anchor_edit_path()) in message
    assert G.anchor_edit_path().is_file()


def test_the_refusal_names_the_insert_and_batch_forms_too():
    message = G.assess(SPLICE_CMD)
    assert "insert" in message and "batch" in message


@pytest.mark.parametrize("command", [
    # authoring the same program into a file is the Write tool's case: the nudge speaks there
    SPLICE_CMD.replace("cd /opt/repo && python3 - <<'PY'", "cat > /tmp/edit.py <<'PY'"),
    # a commit message describing the trap
    SPLICE_CMD.replace("cd /opt/repo && python3 - <<'PY'", "git commit -F - <<'PY'"),
    # the same text on a command line, inside quotes, is prose
    "echo 's[:a] + new + s[b:] after s.index(x) and s.index(y), then p.write_text(...)'",
    "ls -la",
    "",
])
def test_calls_that_do_not_run_a_splice_pass(command):
    assert G.assess(command) is None


def test_powershell_is_not_judged():
    assert G.assess(SPLICE_CMD, "PowerShell") is None


# ---- the hook contract -------------------------------------------------------------------------
def test_main_blocks_with_exit_2_and_the_shared_footer():
    rc, err = run_main(bash(SPLICE_CMD))
    assert rc == 2
    assert shell_text.WHOLE_CALL_REFUSED in err
    assert "replace-span" in err


def test_main_passes_a_harmless_call():
    assert run_main(bash("git status")) == (0, "")


def test_main_ignores_other_tools():
    event = {"tool_name": "Write", "tool_input": {"content": SPLICE_CMD}}
    assert run_main(event) == (0, "")


@pytest.mark.parametrize("stdin", ["", "not json", "[1, 2]", '{"tool_input": null}'])
def test_bad_input_passes(stdin):
    proc = subprocess.run([sys.executable, str(HOOK)], input=stdin, capture_output=True,
                          text=True, encoding="utf-8", timeout=60)
    assert proc.returncode == 0, proc.stderr


def test_the_script_blocks_end_to_end():
    proc = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(bash(SPLICE_CMD)),
                          capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert proc.returncode == 2
    assert "replace-span" in proc.stderr


def test_the_refusal_does_not_point_at_a_way_around_it():
    # naming an unjudged route (author the script with Write instead) invites the bypass
    assert "Write" not in G.assess(SPLICE_CMD)


_HUNK_CMD = (
    "python3 - <<'PY'\n"
    "s = p.read_text()\n"
    "a = s.index('<' * 7 + ' ours\\n')\n"
    "b = s.index('>>>>>>> theirs\\n') + len('>>>>>>> theirs\\n')\n"
    "p.write_text(s[:a] + KEEP + s[b:])\n"
    "PY\n"
)


def test_a_conflict_hunk_splice_is_pointed_at_conflict_resolve():
    message = G.assess(_HUNK_CMD)
    assert message is not None and "conflict_resolve.py" in message


def test_an_ordinary_splice_does_not_mention_conflict_resolve():
    assert "conflict_resolve" not in G.assess(SPLICE_CMD)


# ---- the exemption (user decision 2026-10-30): every anchor asserted unique --------------------
_CHECKED_CMD = SPLICE_CMD.replace(
    "a = s.index('def natural_widths(')\n",
    "assert s.count('def natural_widths(') == 1\n"
    "assert s.count('    return widths') == 1\n"
    "a = s.index('def natural_widths(')\n")


def test_a_splice_checking_every_anchor_unique_is_let_through():
    assert G.assess(_CHECKED_CMD) is None


def test_a_splice_checking_only_the_start_anchor_is_still_refused():
    # the recorded recurrence was an END marker matching inside a deeper-indented line
    start_only = _CHECKED_CMD.replace("assert s.count('    return widths') == 1\n", "")
    assert G.assess(start_only) is not None


def test_the_refusal_names_the_count_check_as_the_alternative():
    message = G.assess(SPLICE_CMD)
    assert "count(" in message and "== 1" in message
