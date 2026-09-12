"""Contracts the PreToolUse(Task|Agent) hooks and subagent-brief share, tested across them at once.

Two defects each had one shape across the siblings:

* A malformed `tool_name` (a list or a dict; Claude Code always sends a string) made each hook test
  set membership on an unhashable value, so `assess()` and `main()` raised and only the `__main__`
  catch-all kept the exit clean. A list is never Task or Agent, so no verdict was at stake; the
  defect is the exception escaping the pure functions.
* A NAMED dispatch of a probe type can neither stay clean nor, for an inert probe, deliver. Measured
  2026-09-11 on Claude Code 2.1.268: a named baseline-probe replied in its own transcript and
  nothing reached the caller, while an unnamed one's reply arrived in its completion notification
  within 6 s, and the inert probe has no SendMessage tool to close that gap. The same run showed
  SubagentStart receiving the NAME as `agent_type` (its hook record reads
  `SubagentStart:probe-named-k4q`), so the brief's clean-room exclusion never matched and the probe
  was briefed - as were both named RED/GREEN arms found in the recorded corpus, against 0 of 276
  unnamed probes. Every hook that decides "is this a probe" must therefore agree on what a probe is.
"""

import io
import json
import sys

import pytest

import subagent_backstop_nudge as backstop
import subagent_brief as brief
import subagent_model_gate as model_gate
import subagent_probe_capability_gate as probe_gate

MALFORMED = [["Task"], {"Agent": 1}, ("Task",), 7, None]
TEXT_ONLY = "Answer from this message alone."
PROBE_TYPES = ["bitranox:baseline-probe", "baseline-probe", "BITRANOX:Baseline-Probe",
               "bitranox:baseline-probe-strict", "probe-effort-low"]


# ---------------------------------------------------------------- a malformed tool_name

@pytest.mark.parametrize("tool_name", MALFORMED, ids=repr)
def test_backstop_nudge_ignores_a_malformed_tool_name(tool_name):
    assert backstop.assess(tool_name, {"name": "reviewer", "prompt": "do it"}) is None


@pytest.mark.parametrize("tool_name", MALFORMED, ids=repr)
def test_model_gate_ignores_a_malformed_tool_name(tool_name):
    assert model_gate.assess(tool_name, {"subagent_type": "general-purpose"}, plan_armed=True) == (None, "")


@pytest.mark.parametrize("tool_name", MALFORMED, ids=repr)
def test_probe_gate_ignores_a_malformed_tool_name(tool_name):
    tool_input = {"subagent_type": "general-purpose", "prompt": "Do not use any tools."}
    assert probe_gate.assess(tool_name, tool_input) == (None, "")


@pytest.mark.parametrize("module", [backstop, model_gate, probe_gate], ids=lambda m: m.__name__)
def test_main_does_not_raise_on_a_list_tool_name(module, monkeypatch, capsys):
    """main() itself must return, not raise and rely on the __main__ catch-all."""
    event = {"tool_name": ["Task"], "tool_input": {"subagent_type": "general-purpose",
                                                   "prompt": "Do not use any tools."}}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(event)))
    assert module.main() == 0
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("module", [backstop, model_gate, probe_gate], ids=lambda m: m.__name__)
def test_a_well_formed_dispatch_still_reaches_each_hook(module):
    """Control: the guard must not silence a real Agent dispatch along with the malformed ones."""
    tool_input = {"subagent_type": "general-purpose", "prompt": "Do not use any tools.", "name": "r"}
    if module is model_gate:
        assert module.assess("Agent", tool_input)[0] == "warn"
    elif module is probe_gate:
        assert module.assess("Agent", tool_input)[0] == "deny"
    else:
        assert module.assess("Agent", tool_input)


# ---------------------------------------------------------------- a named probe

@pytest.mark.parametrize("agent_type", PROBE_TYPES)
def test_the_probe_gate_refuses_a_named_probe(agent_type):
    action, message = probe_gate.assess("Agent", {"subagent_type": agent_type, "name": "red-arm",
                                                  "prompt": TEXT_ONLY})
    assert action == "deny"
    assert "unnamed" in message.lower()


def test_the_probe_gate_refuses_a_named_probe_whatever_its_prompt_says():
    """The failures are properties of the name and the type, not of the wording."""
    action, _ = probe_gate.assess("Agent", {"subagent_type": "bitranox:baseline-probe",
                                            "name": "green-arm", "prompt": "Review this diff."})
    assert action == "deny"


def test_an_unnamed_inert_probe_still_passes_the_gate():
    assert probe_gate.assess("Agent", {"subagent_type": "bitranox:baseline-probe",
                                       "prompt": TEXT_ONLY}) == (None, "")


@pytest.mark.parametrize("name", ["", None, "   "], ids=repr)
def test_a_blank_name_is_not_a_named_dispatch(name):
    assert probe_gate.assess("Agent", {"subagent_type": "bitranox:baseline-probe", "name": name,
                                       "prompt": TEXT_ONLY}) == (None, "")


@pytest.mark.parametrize("agent_type", PROBE_TYPES)
def test_a_named_probe_is_not_told_to_call_sendmessage(agent_type):
    """The gate's refusal is the message that applies; SendMessage advice next to it is noise, and
    for an inert probe asks for a tool it does not have."""
    msg = backstop.assess("Agent", {"subagent_type": agent_type, "name": "red-arm", "prompt": "answer"})
    assert "sendmessage" not in msg.lower()
    assert "backstop" in msg.lower()


def test_a_named_ordinary_dispatch_still_gets_the_delivery_warning():
    msg = backstop.assess("Agent", {"subagent_type": "general-purpose", "name": "reviewer",
                                    "prompt": "review the diff"})
    assert "sendmessage" in msg.lower()


def test_every_hook_that_recognises_a_probe_uses_the_same_markers():
    assert backstop.CLEAN_ROOM_MARKERS == probe_gate.CLEAN_ROOM_MARKERS == brief.CLEAN_ROOM_MARKERS
    assert all(brief.is_clean_room(t) for t in PROBE_TYPES)
