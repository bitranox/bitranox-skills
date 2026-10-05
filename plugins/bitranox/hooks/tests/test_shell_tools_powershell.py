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
import os
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
    # Single-quoted on purpose: the PowerShell arm reads the hook text through the shared
    # splitter's single-quote handling, which is all that stands between it and `'the` + `entirely'`.
    "missing-mechanism-nudge.py":
        "python3 memory_engine.py add --title T --hook 'the retry is missing entirely'",
}


def _repo(root: Path, name: str) -> Path:
    """A directory that looks like a git work tree to the cwd-reading nudges."""
    (root / name / ".git").mkdir(parents=True)
    return root / name


def _wrong_repo(tmp: Path, _tool: str):
    """Two cds into two DIFFERENT repos, each followed by git: the shape that hook fires on."""
    here, one, two = _repo(tmp, "here"), _repo(tmp, "one"), _repo(tmp, "two")
    return [{"cwd": str(here), "command": f"cd {one} && git log && cd {two} && git log"}]


def _path_not_here(tmp: Path, _tool: str):
    """A path-status question asked from a sub-repo about a file that lives in the parent."""
    outer = _repo(tmp, "umbrella")
    (outer / "handover.md").write_text("x", encoding="utf-8")
    inner = _repo(outer, "planning")
    return [{"cwd": str(inner), "command": "git ls-files --error-unmatch handover.md"}]


def _retry_with_a_flag(_tmp: Path, _tool: str):
    """A recorded failure, then the same command with a flag added."""
    return [{"event": "PostToolUseFailure", "command": "rsync -a src dst"},
            {"command": "rsync -a -z src dst"}]


def _recovery_retry(_tmp: Path, _tool: str):
    """Destroy, undo, retry: each call is written to the transcript before the hook runs."""
    return [{"transcript": True, "command": "ssh admin@192.0.2.10 'robocopy C:\\empty C:\\Windows.old /MIR'"},
            {"transcript": True, "command": "ssh root@hv.example.com 'qm rollback 4242 presnap'"
                                            "  # 192.0.2.10 is guest 4242"},
            {"transcript": True, "command": "ssh admin@192.0.2.10 'robocopy C:\\empty C:\\Windows.old /MIR /XJ'"}]


# script -> a builder of the EVENT SEQUENCE that hook is known to speak on, for hooks whose verdict
# needs more than one command string: a cwd with repos in it, a failure recorded earlier, or a
# transcript holding the history. Each arm runs in its own tmp dir, HOME and session, so neither
# arm's state can reach the other, and the whole sequence's outputs are compared.
SCENARIOS = {
    "git-wrong-repo-nudge.py": _wrong_repo,
    "git-path-not-here-nudge.py": _path_not_here,
    "retry-with-a-flag-nudge.py": _retry_with_a_flag,
    "recovery-retry-gate.py": _recovery_retry,
}

# Every shell hook this file must cover. decision-review-nudge is deliberately absent: it is a Stop
# hook, so it never sees a tool_name at all.
ALL_SCRIPTS = sorted(set(TRIGGERS) | set(SCENARIOS))


def _run(script: str, tool_name: str, command: str, **overrides):
    """Drive one hook through the real shim, as Claude Code does. Returns (rc, stdout, stderr).

    `overrides` replaces event fields (cwd, session_id, transcript_path, hook_event_name); `env`
    among them is the child's environment, which is how HOME is isolated - a monkeypatch never
    reaches a subprocess.
    """
    env = overrides.pop("env", None)
    event = {
        "session_id": "test-shell-tools",
        "transcript_path": "/nonexistent",
        "cwd": str(HOOKS_DIR),
        "hook_event_name": "PreToolUse",
        "tool_name": tool_name,
        "tool_input": {"command": command, "description": "probe"},
    }
    event.update(overrides)
    proc = subprocess.run(
        ["bash", str(SHIM), str(HOOKS_DIR / script)],
        input=json.dumps(event), capture_output=True, text=True,
        encoding="utf-8", errors="replace", env=env,
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def _isolated_env(home: Path) -> dict:
    home.mkdir(parents=True, exist_ok=True)
    return dict(os.environ, HOME=str(home), USERPROFILE=str(home))


def _run_scenario(script: str, tool_name: str, tmp: Path):
    """Every step of `script`'s scenario under `tool_name`, in a fresh dir; one result per step."""
    tmp.mkdir(parents=True)
    env = _isolated_env(tmp / "home")
    transcript = tmp / "session.jsonl"
    transcript.write_bytes(b"")
    results = []
    for step in SCENARIOS[script](tmp, tool_name):
        if step.get("transcript"):
            record = {"message": {"content": [{"type": "tool_use", "name": tool_name,
                                               "input": {"command": step["command"]}}]}}
            with open(transcript, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(record) + "\n")
        results.append(_run(
            script, tool_name, step["command"], env=env, session_id="shell-tools-" + tmp.name,
            transcript_path=str(transcript), cwd=step.get("cwd", str(HOOKS_DIR)),
            hook_event_name=step.get("event", "PreToolUse"),
        ))
    return results


def _verdict(script: str, tool_name: str, tmp: Path):
    """The hook's whole verdict for its trigger under `tool_name`; the LAST result is the trigger."""
    if script in SCENARIOS:
        return _run_scenario(script, tool_name, tmp / tool_name)
    return [_run(script, tool_name, TRIGGERS[script], env=_isolated_env(tmp / tool_name / "home"))]


@pytest.mark.skipif(sys.platform == "win32", reason="drives the bash shim directly")
@pytest.mark.parametrize("script", ALL_SCRIPTS)
def test_powershell_gets_the_same_verdict_as_bash(script, tmp_path):
    bash = _verdict(script, "Bash", tmp_path)
    # Vacuity guard: an equality assertion between two silences proves nothing at all.
    assert bash[-1] != (0, "", ""), (
        f"{script} said nothing for its own trigger, so comparing the two arms would pass "
        f"vacuously. The trigger has gone stale - fix it, do not delete the case."
    )
    powershell = _verdict(script, "PowerShell", tmp_path)
    # A path a hook echoes back carries the arm's own tmp dir; that is the fixture, not a verdict.
    assert [tuple(part.replace("/PowerShell/", "/Bash/") if isinstance(part, str) else part
                  for part in result) for result in powershell] == bash


@pytest.mark.skipif(sys.platform == "win32", reason="drives the bash shim directly")
@pytest.mark.parametrize("script", ALL_SCRIPTS)
def test_a_non_shell_tool_event_is_ignored(script, tmp_path):
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
        encoding="utf-8", errors="replace", env=_isolated_env(tmp_path / "home"),
    )
    assert (proc.returncode, proc.stdout.strip(), proc.stderr.strip()) == (0, "", "")
