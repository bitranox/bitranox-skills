"""Tests for the `<grep|diff|cmp> ... || echo <verdict>` refusal.

The positives are shapes that printed a verdict while the tool could not look (the first is the
real incident). The negatives are what a careless matcher would also refuse: honest labels,
counts, a different pipeline's status, negation, and the shape quoted as data.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

import block_or_echo_verdict as mod

_HOOK = Path(__file__).resolve().parent.parent / "block-or-echo-verdict.py"


@pytest.mark.parametrize(
    "command",
    [
        # the incident: -iE plus -P exits 2 ("conflicting matchers") and the label still printed
        "git log -1 --format=%B | grep -inE 'co-authored|claude' -P || echo \"no attribution\"",
        "diff -q a.conf b.conf 2>/dev/null || echo different",
        "cmp -s a b || echo DIFFERS",
        "grep -q X f && echo found || echo 'not found'",
        "rg -n foo src 2>&1 || echo 'no hits'",
        "LC_ALL=C grep -nP '[\\x{2014}]' f.md || echo no-tells",
        "timeout 5 grep -n x f || echo clean",
        "/usr/bin/grep -n x f || echo NONE",
        "git -C /r diff --quiet || echo 'not clean'",
        "git grep -n TODO || echo nothing",
        "if true; then grep x f || echo none; fi",
        "n=$(grep -l foo *.py || echo none); echo \"$n\"",
        "grep -q x f || { echo missing; exit 1; }",
        "for f in a b; do grep -q k \"$f\" || echo \"MISSING $f\"; done",
    ],
)
def test_a_verdict_on_any_nonzero_exit_is_refused(command: str) -> None:
    assert mod.refused_shape(command) is not None


@pytest.mark.parametrize(
    "command",
    [
        "grep x f || echo \"no match or error (rc=$?)\"",   # the label admits the doubt
        "grep x f || echo 'grep failed'",
        "grep -c x f || echo 0",                            # a count: the other hook's shape
        "grep x f || true",
        "grep x f || exit 1",
        "grep x f | head -3 || echo none",                  # head's status, not grep's
        "! grep -q x f || echo found",                      # negation inverts the meaning
        "which grep || echo missing",                       # grep is an argument
        "cat grep.txt || echo missing",
        "echo 'grep x f || echo clean'",                    # quoted data
        "printf '%s\\n' \"diff a b || echo same\"",
        "ssh h 'grep a b || echo clean'",                   # deliberate miss: another shell's text
        "cat <<'X'\ngrep a b || echo clean\nX",             # heredoc body
        "# grep x f || echo clean\ntrue",                   # comment
        "grep x f; echo none",                              # no ||
    ],
)
def test_honest_or_unrelated_shapes_pass(command: str) -> None:
    assert mod.refused_shape(command) is None


def test_powershell_calls_are_not_judged() -> None:
    assert mod.refused_shape("grep x f || echo none", tool_name="PowerShell") is None


@pytest.mark.parametrize(
    "command",
    ["grep -n x f || echo none", "diff -q a b || echo different", "cmp a b || echo differs"],
)
def test_the_refusal_offers_a_form_this_guard_passes(command: str) -> None:
    # A refusal that names no passing form is a dead end the agent routes around.
    shape = mod.refused_shape(command)
    assert shape is not None
    message = mod._message(shape)
    offered = re.search(r"\n    (.+)\n", message)
    assert offered is not None, message
    assert mod.refused_shape(offered.group(1)) is None
    # and the honest-label alternative it mentions passes too
    honest = re.search(r"\(`(\|\| echo .+?)`\)", message)
    assert honest is not None, message
    assert mod.refused_shape("grep x f " + honest.group(1).replace('\\"', '"')) is None


def test_diff_refusal_names_diff_codes_and_grep_refusal_names_grep_codes() -> None:
    assert "1 different" in mod._message(mod.refused_shape("diff a b || echo same") or "")
    assert "1 no match" in mod._message(mod.refused_shape("grep a b || echo none") or "")


def _run(event: object) -> subprocess.CompletedProcess[str]:
    payload = event if isinstance(event, str) else json.dumps(event)
    return subprocess.run(
        [sys.executable, str(_HOOK)], input=payload, capture_output=True, text=True,
        encoding="utf-8", errors="replace", cwd=_HOOK.parent, check=False,
    )


def test_cli_blocks_with_exit_2_and_explains_on_stderr() -> None:
    done = _run({"tool_name": "Bash", "tool_input": {"command": "grep x f || echo clean"}})
    assert done.returncode == 2
    assert "Refused" in done.stderr and "rc=$rc" in done.stderr
    assert done.stdout == ""


def test_cli_passes_a_clean_command_silently() -> None:
    done = _run({"tool_name": "Bash", "tool_input": {"command": "grep x f; rc=$?"}})
    assert (done.returncode, done.stdout, done.stderr) == (0, "", "")


def test_cli_never_wedges_on_garbage_input() -> None:
    assert _run("not json").returncode == 0
    assert _run({"tool_input": None}).returncode == 0
