"""Tests for subagent-backstop-nudge.py (PreToolUse subagent backstop nudge).

Contract: on every Task/Agent dispatch, emit hookSpecificOutput.additionalContext (exit 0,
NO permissionDecision) reminding the main agent to estimate the subagent's duration and arm
its OWN bounded backstop re-check instead of passively waiting on the completion signal.
Every non-subagent tool and every bad-stdin path exits 0 silently. All content is ASCII.
"""

import io
import json
import sys

import subagent_backstop_nudge as W


def run_main(monkeypatch, event):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(event)))
    return W.main()


def test_assess_returns_reminder_for_task():
    msg = W.assess("Task", {"subagent_type": "general-purpose"})
    assert msg and "backstop" in msg.lower()


def test_assess_returns_reminder_for_agent():
    assert W.assess("Agent", {"subagent_type": "x"})


def test_assess_fires_for_fork_too():
    # a fork can hang in a wait-loop too, so it is NOT exempt here (unlike the model gate)
    assert W.assess("Agent", {"subagent_type": "fork"})


def test_assess_reminder_mentions_estimate_and_no_passive_wait():
    msg = W.assess("Task", {}).lower()
    assert "estimate" in msg
    assert "notification" in msg or "passive" in msg


def test_assess_ignores_non_subagent_tool():
    assert W.assess("Bash", {"command": "ls"}) is None
    assert W.assess("Edit", {"file_path": "x"}) is None


def test_assess_missing_input_is_safe():
    assert W.assess("Task") and W.assess("Task", None)


def test_main_emits_additionalcontext_for_subagent(monkeypatch, capsys):
    rc = run_main(monkeypatch, {"tool_name": "Task", "tool_input": {"subagent_type": "x"}})
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    hso = payload["hookSpecificOutput"]
    assert hso["hookEventName"] == "PreToolUse"
    assert "backstop" in hso["additionalContext"].lower()
    # non-blocking: must NOT carry a permission decision (that would interfere with dispatch)
    assert "permissionDecision" not in hso


def test_main_silent_for_non_subagent(monkeypatch, capsys):
    rc = run_main(monkeypatch, {"tool_name": "Bash", "tool_input": {"command": "ls"}})
    assert rc == 0
    out = capsys.readouterr()
    assert out.out == "" and out.err == ""


def test_main_fail_open_on_bad_stdin(monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO("not json at all"))
    assert W.main() == 0


def test_main_non_dict_event_is_safe(monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO("[1, 2, 3]"))
    assert W.main() == 0


def test_reminder_is_ascii():
    W.assess("Task").encode("ascii")  # raises if any non-ASCII char slipped in


# --- the SendMessage delivery warning (named == background == mailbox) -------------------
#
# A NAMED dispatch runs in the background: its final text is never returned as the tool
# result, only an idle/completion notification arrives. Without an explicit "SendMessage"
# instruction in its prompt, the report sits unread in the agent's transcript. Observed
# twice (2026-07 roster review: 9 of 9 silent; 2026-07-15 bmk review: 8 of 9 silent), which
# is why the prose rule was escalated to this guard.


def test_named_dispatch_without_sendmessage_gets_the_delivery_warning():
    msg = W.assess("Agent", {"name": "reviewer", "prompt": "Return ONLY: SCORE and EVIDENCE."})
    assert "sendmessage" in msg.lower()


def test_named_dispatch_that_already_says_sendmessage_is_not_warned():
    # The instruction is already there - warning again would be noise on every good dispatch.
    msg = W.assess("Agent", {"name": "reviewer", "prompt": "Report via SendMessage to main."})
    assert "backstop" in msg.lower()
    assert msg.lower().count("sendmessage") == 0 or "does not mention" not in msg.lower()


def test_unnamed_dispatch_is_not_warned():
    # An unnamed dispatch blocks and returns its final message as the tool result, so the
    # delivery trap does not apply - warning would be a false positive.
    msg = W.assess("Agent", {"prompt": "Return ONLY: SCORE."})
    assert "does not mention" not in msg.lower()


def test_delivery_warning_names_the_fix_and_the_idle_trap():
    msg = W.assess("Agent", {"name": "r", "prompt": "do the thing"}).lower()
    assert "main" in msg  # names the SendMessage target
    assert "idle" in msg  # an idle notification is NOT a report


def test_delivery_warning_still_carries_the_backstop_reminder():
    # The two nudges must compose, not replace each other.
    msg = W.assess("Agent", {"name": "r", "prompt": "do the thing"}).lower()
    assert "backstop" in msg
    assert "sendmessage" in msg


def test_named_dispatch_with_missing_prompt_is_safe():
    assert W.assess("Agent", {"name": "r"})
    assert W.assess("Agent", {"name": None, "prompt": None})


def test_delivery_warning_is_ascii():
    W.assess("Agent", {"name": "r", "prompt": "x"}).encode("ascii")
