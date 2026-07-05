"""Tests for subagent-model-gate.py (PreToolUse subagent-model gate).

Contract: WARN (stderr, exit 0) when a Task/Agent dispatch omits `model` and is not a fork;
DENY (PreToolUse deny JSON on stdout) for the same dispatch while a fresh `plan-execution`
receipt is armed. Every other path exits 0. All content is ASCII.
"""

import io
import json
import sys

import pytest

import skill_receipt
import subagent_model_gate as W


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    (h / ".claude").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


def run_main(monkeypatch, event):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(event)))
    return W.main()


def test_assess_warns_when_model_omitted():
    action, msg = W.assess("Task", {"subagent_type": "general-purpose", "prompt": "x"})
    assert action == "warn"
    assert "model" in msg


def test_assess_denies_when_plan_armed():
    action, msg = W.assess("Task", {"subagent_type": "general-purpose"}, plan_armed=True)
    assert action == "deny"
    assert "plan-execution" in msg and "model" in msg


def test_assess_pinned_passes_even_when_armed():
    assert W.assess("Task", {"subagent_type": "x", "model": "sonnet"}, plan_armed=True)[0] is None


def test_assess_fork_exempt_even_when_armed():
    assert W.assess("Agent", {"subagent_type": "fork"}, plan_armed=True)[0] is None


def test_assess_blank_model_warns():
    assert W.assess("Task", {"subagent_type": "x", "model": "   "})[0] == "warn"


def test_assess_ignores_non_subagent_tool():
    assert W.assess("Bash", {"command": "ls"}, plan_armed=True)[0] is None


def test_assess_non_dict_input_is_safe():
    assert W.assess("Task", None, plan_armed=True)[0] is None


def test_main_warns_exit0_when_not_armed(monkeypatch, capsys):
    rc = run_main(monkeypatch, {"tool_name": "Task", "tool_input": {"subagent_type": "x"}})
    assert rc == 0
    out = capsys.readouterr()
    assert "SUBAGENT-MODEL GATE" in out.err
    assert out.out == ""


def test_main_denies_with_json_when_armed(monkeypatch, capsys):
    skill_receipt.start("plan-execution")
    rc = run_main(monkeypatch, {"tool_name": "Task", "tool_input": {"subagent_type": "x"}})
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert "model" in payload["hookSpecificOutput"]["permissionDecisionReason"]


def test_main_disarmed_by_receipt_end(monkeypatch, capsys):
    skill_receipt.start("plan-execution")
    assert skill_receipt.end("plan-execution") is True
    rc = run_main(monkeypatch, {"tool_name": "Task", "tool_input": {"subagent_type": "x"}})
    assert rc == 0
    out = capsys.readouterr()
    assert out.out == "" and "warning" in out.err


def test_main_pinned_is_silent(monkeypatch, capsys):
    rc = run_main(monkeypatch, {"tool_name": "Task", "tool_input": {"subagent_type": "x", "model": "opus"}})
    assert rc == 0
    out = capsys.readouterr()
    assert out.err == "" and out.out == ""


def test_main_fail_open_on_bad_stdin(monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO("not json at all"))
    assert W.main() == 0


def test_receipt_end_is_idempotent():
    assert skill_receipt.end("plan-execution") is False   # absent -> False, no raise
    skill_receipt.start("plan-execution")
    assert skill_receipt.end("plan-execution") is True
    assert skill_receipt.end("plan-execution") is False
