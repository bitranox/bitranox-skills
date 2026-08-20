"""Tests for subagent-brief.py (SubagentStart: the two delivery facts, never to a clean-room probe).

The exclusion is the part worth testing hardest. `bitranox:baseline-probe` measures RED baselines,
and its inertness bounds TOOLS, not CONTEXT - so a hook that briefed it would contaminate the one
agent whose value is an uncontaminated context, and the only symptom would be RED baselines quietly
starting to pass. So there are tests in BOTH directions: the brief reaches an ordinary agent, and
it never reaches a probe.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

import subagent_brief as B

HOOKS_DIR = Path(__file__).resolve().parent.parent
SCRIPT = HOOKS_DIR / "subagent-brief.py"
SHIM = HOOKS_DIR / "run-python.sh"


# ---------------------------------------------------------------- the clean-room exclusion

@pytest.mark.parametrize("agent_type", [
    "bitranox:baseline-probe",
    "baseline-probe",
    "BITRANOX:BASELINE-PROBE",
    "probe-effort-low",
    "probe-effort-max",
    "bitranox:baseline-probe-strict",     # an unknown probe-shaped name must fail CLOSED
])
def test_a_clean_room_agent_is_never_briefed(agent_type):
    assert B.is_clean_room(agent_type) is True
    assert B.brief_for(agent_type) is None


@pytest.mark.parametrize("agent_type", [
    "general-purpose", "Explore", "Plan", "claude", "code-reviewer",
    "bitranox:something-else", "", None,
])
def test_an_ordinary_agent_is_briefed(agent_type):
    assert B.is_clean_room(agent_type) is False
    assert B.brief_for(agent_type) == B.BRIEF


def test_the_brief_names_both_delivery_facts():
    """Either fact alone leaves a subagent's work undelivered, so both must survive an edit."""
    assert "Write is refused by FILENAME" in B.BRIEF
    assert "SendMessage" in B.BRIEF


# ---------------------------------------------------------------- end to end through the shim

def _run(payload):
    proc = subprocess.run(
        ["bash", str(SHIM), str(SCRIPT)],
        input=json.dumps(payload), capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def _event(agent_type):
    return {"session_id": "t", "transcript_path": "/nonexistent", "cwd": str(HOOKS_DIR),
            "hook_event_name": "SubagentStart", "agent_id": "a1", "agent_type": agent_type}


@pytest.mark.skipif(sys.platform == "win32", reason="drives the bash shim directly")
def test_end_to_end_emits_additional_context_for_an_ordinary_agent():
    rc, out, _err = _run(_event("general-purpose"))
    assert rc == 0
    payload = json.loads(out)
    assert payload["hookSpecificOutput"]["hookEventName"] == "SubagentStart"
    assert payload["hookSpecificOutput"]["additionalContext"] == B.BRIEF


@pytest.mark.skipif(sys.platform == "win32", reason="drives the bash shim directly")
def test_end_to_end_is_silent_for_a_baseline_probe():
    assert _run(_event("bitranox:baseline-probe")) == (0, "", "")


@pytest.mark.skipif(sys.platform == "win32", reason="drives the bash shim directly")
@pytest.mark.parametrize("payload", ["", "not json", "[]", "null"])
def test_malformed_input_fails_open_silently(payload):
    """SubagentStart ignores the exit code, so the only safe failure is silence."""
    proc = subprocess.run(
        ["bash", str(SHIM), str(SCRIPT)],
        input=payload, capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    assert (proc.returncode, proc.stdout.strip()) == (0, "")
