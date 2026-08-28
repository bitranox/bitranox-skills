"""Every shell-inspecting hook must treat `PowerShell` exactly like `Bash`.

Claude Code routes the model's shell commands through the `PowerShell` tool on Windows where it is
enabled, and registers no `Bash` tool at all on a Windows box without Git Bash. A guard that
compares `tool_name` against "Bash" alone therefore does nothing on those machines, while reading
- in hooks.json, in its docstring, and in its own previously-passing tests - exactly like a guard
that is switched on.

Two halves, and the first is what makes the second mean anything:

* the BASH arm must SPEAK. A hook that is silent on both arms passes an equality assertion
  vacuously, so a trigger that stops triggering would turn this file green while testing nothing.
  Each case asserts the Bash arm is non-silent before comparing the two.
* the POWERSHELL arm must produce the identical verdict - same exit code, same stdout, same stderr.

The matcher half of the same change lives in `test_hooks_json_matchers.py`: widening the script
without widening `hooks.json` leaves the hook switched off on the platform it was widened for, and
neither file can see that on its own.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

HOOKS_DIR = Path(__file__).resolve().parent.parent
SHIM = HOOKS_DIR / "run-python.sh"

# script -> a command that hook is KNOWN to have an opinion about. Taken from each hook's own tests
# where one existed, so a trigger going stale shows up as a vacuity failure here rather than silence.
TRIGGERS = {
    "arbitrary-sleep-nudge.py": "sleep 300",
    "block-pgrep-self-match.py": "pgrep -f myworker",
    "git-footgun-guard.py": "git rev-parse --short A B",
    "block-git-semicolon-chain.py": "git commit -m x ; git push",
    # The em dash is built from its code point, not typed: this repo's own tell sweep treats a
    # literal one as a defect, and a fixture that must CONTAIN the tell would otherwise make the
    # test file that proves the guard works into something the guard flags.
    "commit-tell-sweep.py": 'git commit -m "fix ' + chr(0x2014) + ' the thing"',
    "block-sed-structured-files.py": "sed -i s/a/b/ pkg.json",
    "shell-prefix-selfref-guard.py": 'VAR=hello echo "$VAR"',
    "sed-line1-range-nudge.py": "sed '1,/^---$/d' f.md",
    "git-revparse-nudge.py": "git rev-parse master",
    "gated-prep-nudge.py": "cat > /tmp/m <<'EOF'\nx\nEOF\ngit commit -F /tmp/m",
    "warn-inline-powershell.py": "ssh host 'powershell -Command Get-ChildItem | Select-Object'",
}


def _run(script: str, tool_name: str, command: str):
    """Drive one hook through the real shim, as Claude Code does. Returns (rc, stdout, stderr)."""
    event = {
        "session_id": "test-shell-tools",
        "transcript_path": "/nonexistent",
        "cwd": str(HOOKS_DIR),
        "hook_event_name": "PreToolUse",
        "tool_name": tool_name,
        "tool_input": {"command": command, "description": "probe"},
    }
    proc = subprocess.run(
        ["bash", str(SHIM), str(HOOKS_DIR / script)],
        input=json.dumps(event), capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


@pytest.mark.skipif(sys.platform == "win32", reason="drives the bash shim directly")
@pytest.mark.parametrize("script", sorted(TRIGGERS))
def test_powershell_gets_the_same_verdict_as_bash(script):
    command = TRIGGERS[script]
    bash = _run(script, "Bash", command)
    # Vacuity guard: an equality assertion between two silences proves nothing at all.
    assert bash != (0, "", ""), (
        f"{script} said nothing for its own trigger, so comparing the two arms would pass "
        f"vacuously. The trigger has gone stale - fix it, do not delete the case."
    )
    assert _run(script, "PowerShell", command) == bash


@pytest.mark.skipif(sys.platform == "win32", reason="drives the bash shim directly")
@pytest.mark.parametrize("script", sorted(TRIGGERS))
def test_a_non_shell_tool_event_is_ignored(script):
    """The widening must not turn these into hooks that fire on any tool.

    A real non-shell event carries no `command`, so that - not an invented Read event holding a
    shell string - is the shape to assert on. Several of these guards deliberately have no
    `tool_name` check and let the matcher be the filter; feeding them a command under another tool
    name tests a call Claude Code never makes.
    """
    event = {
        "session_id": "test-shell-tools",
        "transcript_path": "/nonexistent",
        "cwd": str(HOOKS_DIR),
        "hook_event_name": "PreToolUse",
        "tool_name": "Read",
        "tool_input": {"file_path": str(HOOKS_DIR / "shell_text.py")},
    }
    proc = subprocess.run(
        ["bash", str(SHIM), str(HOOKS_DIR / script)],
        input=json.dumps(event), capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    assert (proc.returncode, proc.stdout.strip(), proc.stderr.strip()) == (0, "", "")
