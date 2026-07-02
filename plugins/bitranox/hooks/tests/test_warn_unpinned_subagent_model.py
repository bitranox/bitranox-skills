"""Tests for warn-unpinned-subagent-model.py (PreToolUse subagent-model guard).

Contract: WARN (stderr, exit 0) when a Task/Agent dispatch omits `model` and is not a fork.
Every other path exits 0. All content is ASCII.
"""

import io
import json
import sys

import warn_unpinned_subagent_model as W


def run_main(monkeypatch, event):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(event)))
    return W.main()


def test_assess_warns_when_model_omitted():
    action, msg = W.assess("Task", {"subagent_type": "general-purpose", "prompt": "x"})
    assert action == "warn"
    assert "model" in msg


def test_assess_no_warn_when_model_pinned():
    assert W.assess("Task", {"subagent_type": "general-purpose", "model": "sonnet"})[0] is None


def test_assess_no_warn_for_fork():
    assert W.assess("Agent", {"subagent_type": "fork"})[0] is None


def test_assess_blank_model_warns():
    assert W.assess("Task", {"subagent_type": "x", "model": "   "})[0] == "warn"


def test_assess_ignores_non_subagent_tool():
    assert W.assess("Bash", {"command": "ls"})[0] is None


def test_assess_handles_agent_tool_name():
    assert W.assess("Agent", {"subagent_type": "general-purpose"})[0] == "warn"


def test_assess_non_dict_input_is_safe():
    assert W.assess("Task", None)[0] is None


def test_main_warns_exit0(monkeypatch, capsys):
    rc = run_main(monkeypatch, {"tool_name": "Task", "tool_input": {"subagent_type": "x"}})
    assert rc == 0
    assert "SUBAGENT-MODEL GUARD" in capsys.readouterr().err


def test_main_pinned_is_silent(monkeypatch, capsys):
    rc = run_main(monkeypatch, {"tool_name": "Task", "tool_input": {"subagent_type": "x", "model": "opus"}})
    assert rc == 0
    assert capsys.readouterr().err == ""


def test_main_fail_open_on_bad_stdin(monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO("not json at all"))
    assert W.main() == 0
