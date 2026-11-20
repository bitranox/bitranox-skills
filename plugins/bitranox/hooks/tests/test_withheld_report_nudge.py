"""withheld-report-nudge: a withheld hand-back's report is read from the agent's transcript."""

import json
import subprocess
import sys
from pathlib import Path

import withheld_report_nudge as hook

HOOKS_DIR = Path(__file__).resolve().parent.parent
SCRIPT = HOOKS_DIR / "withheld-report-nudge.py"
AGENT = "a206186377e645d0b"
WITHHELD_TEXT = (
    "The subagent ended without delivering a report through SubagentHandback, so no report was "
    "delivered. Its unsent text is not shown. Send the agent a message (SendMessage) to ask it to "
    f"deliver its report.\n\nagentId: {AGENT} (use SendMessage with to: '{AGENT}')"
)


def _response(handback="withheld", text=WITHHELD_TEXT, agent_id=AGENT):
    response = {"status": "completed", "content": [{"type": "text", "text": text}]}
    if handback is not None:
        response["handback"] = handback
    if agent_id is not None:
        response["agentId"] = agent_id
    return response


def _assistant(*blocks):
    return {"type": "assistant", "message": {"content": list(blocks)}}


def _handback(message):
    return {"type": "tool_use", "name": "SubagentHandback", "id": "t", "input": {"message": message}}


def _session(tmp_path, records, agent_id=AGENT):
    """A session transcript plus the agent's own transcript under <session>/subagents/."""
    main = tmp_path / "session.jsonl"
    main.write_text("{}\n", encoding="utf-8")
    agents = tmp_path / "session" / "subagents"
    agents.mkdir(parents=True)
    agent = agents / (f"agent-{agent_id}.jsonl")
    agent.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
    return main, agent


def _event(main, response=None, tool_name="Agent"):
    return {"hook_event_name": "PostToolUse", "tool_name": tool_name, "transcript_path": str(main),
            "tool_response": _response() if response is None else response}


def test_withheld_result_shows_the_handback_message(tmp_path):
    main, agent = _session(tmp_path, [_assistant(_handback("REPORT: item 130 is other-repo"))])
    message = hook.assess(_event(main))
    assert "REPORT: item 130 is other-repo" in message
    assert str(agent) in message


def test_last_handback_message_wins(tmp_path):
    main, _ = _session(tmp_path, [_assistant(_handback("first draft")), _assistant(_handback("final word"))])
    message = hook.assess(_event(main))
    assert "final word" in message and "first draft" not in message


def test_falls_back_to_last_text(tmp_path):
    main, _ = _session(tmp_path, [_assistant({"type": "text", "text": "early"}),
                                  _assistant({"type": "text", "text": "the answer in text"})])
    message = hook.assess(_event(main))
    assert "the answer in text" in message and "early" not in message


def test_long_report_is_capped(tmp_path):
    main, _ = _session(tmp_path, [_assistant(_handback("x" * (hook.REPORT_CAP + 500)))])
    message = hook.assess(_event(main))
    assert "x" * hook.REPORT_CAP in message
    assert "x" * (hook.REPORT_CAP + 1) not in message
    assert f"cut at {hook.REPORT_CAP} characters" in message


def test_delivered_result_is_silent(tmp_path):
    main, _ = _session(tmp_path, [_assistant(_handback("REPORT"))])
    delivered = _response(handback="send", text="Final report text, delivered.")
    assert hook.assess(_event(main, delivered)) is None


def test_plain_result_without_handback_field_is_silent(tmp_path):
    main, _ = _session(tmp_path, [_assistant(_handback("REPORT"))])
    plain = _response(handback=None, text="All done, 3 files changed.")
    assert hook.assess(_event(main, plain)) is None


def test_handback_field_alone_is_recognised(tmp_path):
    """The `handback` field decides even when the harness rewords the text around it."""
    main, _ = _session(tmp_path, [_assistant(_handback("REPORT from the field"))])
    response = _response(text=f"Report held back.\n\nagentId: {AGENT}")
    assert "REPORT from the field" in hook.assess(_event(main, response))


def test_text_form_alone_is_recognised(tmp_path):
    """No handback or agentId field: the harness wording and `agentId: <id>` in the text suffice."""
    main, _ = _session(tmp_path, [_assistant(_handback("REPORT from text form"))])
    response = _response(handback=None, agent_id=None)
    assert "REPORT from text form" in hook.assess(_event(main, response))


def test_other_tools_are_ignored(tmp_path):
    main, _ = _session(tmp_path, [_assistant(_handback("REPORT"))])
    assert hook.assess(_event(main, tool_name="Bash")) is None


def test_missing_transcript_still_names_the_agent(tmp_path):
    main = tmp_path / "session.jsonl"
    main.write_text("{}\n", encoding="utf-8")
    message = hook.assess(_event(main))
    assert AGENT in message and "could not be recovered" in message


def test_transcript_beside_a_subagent_transcript_path(tmp_path):
    """A transcript_path that is itself a subagent's file: the agent sits beside it."""
    agents = tmp_path / "subagents"
    agents.mkdir()
    own = agents / "agent-ateam-1.jsonl"
    own.write_text("{}\n", encoding="utf-8")
    (agents / (f"agent-{AGENT}.jsonl")).write_text(
        json.dumps(_assistant(_handback("REPORT beside"))) + "\n", encoding="utf-8")
    assert "REPORT beside" in hook.assess(_event(own))


def test_unsafe_agent_id_is_ignored(tmp_path):
    main, _ = _session(tmp_path, [_assistant(_handback("REPORT"))])
    assert hook.assess(_event(main, _response(agent_id="../../etc"))) is None


def test_large_transcript_is_read_from_its_tail(tmp_path):
    """Only the last tail_bytes are parsed: the head is skipped, the cut first line is dropped."""
    early = _assistant({"type": "text", "text": "EARLY record " + "pad " * 100})
    filler = [_assistant({"type": "text", "text": "pad " * 100}) for _ in range(40)]
    _, agent = _session(tmp_path, [early, *filler, _assistant(_handback("REPORT at the end"))])
    records = list(hook.transcript_records(agent, tail_bytes=2048))
    texts = json.dumps(records)
    assert "REPORT at the end" in texts
    assert "EARLY record" not in texts
    assert 0 < len(records) < 42
    assert hook.report_from_records(records) == "REPORT at the end"


def test_small_transcript_is_read_whole(tmp_path):
    _, agent = _session(tmp_path, [_assistant({"type": "text", "text": "first"}),
                                   _assistant(_handback("REPORT"))])
    assert len(list(hook.transcript_records(agent))) == 2


def test_script_emits_post_tool_use_context(tmp_path):
    main, _ = _session(tmp_path, [_assistant(_handback("REPORT via stdin"))])
    done = subprocess.run([sys.executable, str(SCRIPT)], input=json.dumps(_event(main)),
                          capture_output=True, text=True, encoding="utf-8", check=False)
    assert done.returncode == 0
    out = json.loads(done.stdout)["hookSpecificOutput"]
    assert out["hookEventName"] == "PostToolUse"
    assert "REPORT via stdin" in out["additionalContext"]


def test_script_exits_zero_on_garbage_stdin():
    done = subprocess.run([sys.executable, str(SCRIPT)], input="not json", capture_output=True,
                          text=True, encoding="utf-8", check=False)
    assert done.returncode == 0 and done.stdout == ""


def test_registered_in_hooks_json_under_post_tool_use_on_agent():
    hooks = json.loads((HOOKS_DIR / "hooks.json").read_text(encoding="utf-8"))["hooks"]
    groups = [g for g in hooks["PostToolUse"]
              if any(h["command"].endswith('withheld-report-nudge.py"') for h in g["hooks"])]
    assert len(groups) == 1
    assert set(groups[0]["matcher"].split("|")) == {"Task", "Agent"}
