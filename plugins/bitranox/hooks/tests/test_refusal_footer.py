"""Every whole-call blocking Bash guard tells the model that NOTHING in the refused call ran.

A PreToolUse exit 2 refuses the WHOLE Bash call, not the one statement the guard objected to. An
edit, a write or a version bump bundled into the same command is lost with it, and a refusal that
names only the offending statement reads as if the rest went through. The sentence saying so lives
in one helper, `shell_text.refuse`, and this module pins that every such guard goes through it.

The guard list is DERIVED, never written down: every script hooks.json registers on a PreToolUse
matcher that covers Bash, whose source either exits 2 or calls the helper. A new guard that blocks
with a bare `return 2` therefore lands in the list and fails here until it uses the helper.
"""

import ast
import io
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

import shell_text

HOOKS_DIR = Path(__file__).resolve().parent.parent

# What a hook source looks like when it blocks: a literal exit status of 2, however spelled, or a
# call to the shared helper (which returns 2 itself).
_BLOCKS = re.compile(r"\breturn\s+2\b|\bexit\(\s*2\s*\)|SystemExit\(\s*2\s*\)|\brefuse\(")
_SCRIPT = re.compile(r"hooks/([\w.-]+\.py)")
# Claude Code reads a matcher made only of these characters as an exact name or a `|` list, and
# anything else as an unanchored regex (bitranox:meta-claude-hooks, configuration reference).
_PLAIN_MATCHER = re.compile(r"[A-Za-z0-9_| ,-]*")


def _matches_bash(matcher):
    if matcher in ("", "*"):
        return True
    if _PLAIN_MATCHER.fullmatch(matcher):
        return "Bash" in [part.strip() for part in re.split(r"[|,]", matcher)]
    return re.search(matcher, "Bash") is not None


def _bash_pretooluse_scripts():
    data = json.loads((HOOKS_DIR / "hooks.json").read_text(encoding="utf-8"))
    scripts = set()
    for group in data["hooks"].get("PreToolUse", []):
        if not _matches_bash(group.get("matcher") or ""):
            continue
        for handler in group.get("hooks", []):
            names = _SCRIPT.findall(handler.get("command") or "")
            if names:
                scripts.add(names[-1])
    return scripts


def blocking_guards():
    """The Bash PreToolUse scripts that can refuse a call, read from hooks.json and their source."""
    return sorted(name for name in _bash_pretooluse_scripts()
                  if _BLOCKS.search((HOOKS_DIR / name).read_text(encoding="utf-8")))


def _literal_exit_twos(tree):
    """Each place a module returns or exits with a literal 2 instead of going through the helper."""
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and isinstance(node.value, ast.Constant) \
                and node.value.value == 2:
            found.append(node.lineno)
        if isinstance(node, ast.Call) and node.args and isinstance(node.args[0], ast.Constant) \
                and node.args[0].value == 2:
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
            if name in ("exit", "SystemExit", "_exit"):
                found.append(node.lineno)
    return found


def test_the_enumeration_finds_the_known_guards():
    # A derived list that came back empty would pass every parametrized case below vacuously.
    guards = blocking_guards()
    assert "block-partial-typecheck.py" in guards
    assert "block-git-semicolon-chain.py" in guards
    assert "git-footgun-guard.py" in guards
    assert len(guards) >= 10, guards


def test_the_enumeration_skips_advisory_hooks():
    # A nudge that only adds context never refuses a call, so it owes no footer.
    assert "gated-prep-nudge.py" not in blocking_guards()


@pytest.mark.parametrize("guard", blocking_guards())
def test_every_blocking_guard_refuses_through_the_shared_helper(guard):
    source = (HOOKS_DIR / guard).read_text(encoding="utf-8")
    assert _literal_exit_twos(ast.parse(source)) == [], (
        f"{guard} blocks with a literal 2; use `return shell_text.refuse(message)` so the refusal "
        "says that nothing in the call ran")
    assert re.search(r"\brefuse\(", source), f"{guard} never calls shell_text.refuse"


def test_refuse_writes_the_message_then_the_footer_and_returns_two():
    stream = io.StringIO()
    assert shell_text.refuse("BLOCKED: reason", stream=stream) == 2
    assert stream.getvalue() == "BLOCKED: reason\n" + shell_text.WHOLE_CALL_REFUSED + "\n"
    assert "NOTHING" in shell_text.WHOLE_CALL_REFUSED


def test_refuse_does_not_double_the_newline_of_a_message_that_has_one():
    stream = io.StringIO()
    shell_text.refuse("line one\n", stream=stream)
    assert stream.getvalue() == "line one\n" + shell_text.WHOLE_CALL_REFUSED + "\n"


def test_refuse_defaults_to_the_real_stderr(capsys):
    shell_text.refuse("x")
    assert shell_text.WHOLE_CALL_REFUSED in capsys.readouterr().err


# End to end over the real scripts: the footer reaches the stderr Claude Code shows the model.
_TRIGGERS = {
    "git-footgun-guard.py": "git rev-parse --short HEAD HEAD~1",
    "block-git-semicolon-chain.py": "git commit -m x; git push",
    "block-pgrep-self-match.py": "pgrep -f nginx",
    "block-sed-structured-files.py": "sed -i 's/a/b/' config.json",
    "shell-prefix-selfref-guard.py": 'TOKEN=abc echo "$TOKEN"',
}


@pytest.mark.parametrize("guard", sorted(_TRIGGERS))
def test_a_real_refusal_ends_with_the_footer(guard, tmp_path):
    assert guard in blocking_guards()
    event = {"tool_name": "Bash", "hook_event_name": "PreToolUse", "cwd": str(tmp_path),
             "tool_input": {"command": _TRIGGERS[guard]}}
    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
    run = subprocess.run([sys.executable, str(HOOKS_DIR / guard)], input=json.dumps(event),
                         capture_output=True, text=True, encoding="utf-8", errors="replace",
                         cwd=str(tmp_path), env=env, timeout=60)
    assert run.returncode == 2, run.stderr
    assert shell_text.WHOLE_CALL_REFUSED in run.stderr
