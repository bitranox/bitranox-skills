"""Tests for subagent-model-gate.py (PreToolUse subagent-model gate).

Contract: WARN (additionalContext JSON on stdout, exit 0) when a Task/Agent dispatch omits
`model`, is not a fork, and its agent type's own definition pins no model; DENY (PreToolUse deny
JSON on stdout) for the same dispatch while a fresh `plan-execution` receipt is armed. Every other
path exits 0 and writes nothing to stderr. All content is ASCII.
"""

import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import skill_receipt
import subagent_model_gate as W


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    (h / ".claude").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    # A run inside a Claude Code session inherits that session's id, which would key every
    # id-less `start` here to it; the tests name their sessions explicitly instead.
    monkeypatch.delenv("CLAUDE_CODE_SESSION_ID", raising=False)
    # A hook run inside Claude Code sees the real project's .claude/agents through this; the tests
    # name their project dirs explicitly instead.
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
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
    hso = json.loads(out.out)["hookSpecificOutput"]
    assert hso["hookEventName"] == "PreToolUse"
    assert "model" in hso["additionalContext"]
    assert "permissionDecision" not in hso   # a warn must not block the dispatch
    assert out.err == ""


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
    hso = json.loads(capsys.readouterr().out)["hookSpecificOutput"]
    assert "additionalContext" in hso and "permissionDecision" not in hso


def test_main_pinned_is_silent(monkeypatch, capsys):
    rc = run_main(monkeypatch, {"tool_name": "Task", "tool_input": {"subagent_type": "x", "model": "opus"}})
    assert rc == 0
    out = capsys.readouterr()
    assert out.err == "" and out.out == ""


def test_main_fail_open_on_bad_stdin(monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO("not json at all"))
    assert W.main() == 0


SESSION_A = "aaaaaaaa-0000-0000-0000-000000000001"
SESSION_B = "bbbbbbbb-0000-0000-0000-000000000002"


def _dispatch(session):
    return {"tool_name": "Agent", "session_id": session, "tool_input": {"subagent_type": "x"}}


def _decision(capsys):
    return json.loads(capsys.readouterr().out)["hookSpecificOutput"].get("permissionDecision")


def test_one_sessions_plan_does_not_arm_the_gate_in_another(monkeypatch, capsys):
    """The gate asked "is a plan armed anywhere on this machine", so session A's plan execution
    denied every unpinned dispatch in session B for eight hours."""
    skill_receipt.start("plan-execution", session_id=SESSION_A)
    run_main(monkeypatch, _dispatch(SESSION_B))
    assert _decision(capsys) is None                      # B only gets the warning


def test_a_sessions_own_plan_still_arms_its_gate(monkeypatch, capsys):
    """Control for the test above: the session that armed the plan is still denied."""
    skill_receipt.start("plan-execution", session_id=SESSION_A)
    run_main(monkeypatch, _dispatch(SESSION_A))
    assert _decision(capsys) == "deny"


def test_another_sessions_end_does_not_disarm_this_sessions_plan(monkeypatch, capsys):
    """Keyed by skill alone, B's `end` deleted A's receipt and silently opened A's gate."""
    skill_receipt.start("plan-execution", session_id=SESSION_A)
    skill_receipt.start("plan-execution", session_id=SESSION_B)
    skill_receipt.end("plan-execution", session_id=SESSION_B)
    run_main(monkeypatch, _dispatch(SESSION_A))
    assert _decision(capsys) == "deny"


def test_receipt_end_is_idempotent():
    assert skill_receipt.end("plan-execution") is False   # absent -> False, no raise
    skill_receipt.start("plan-execution")
    assert skill_receipt.end("plan-execution") is True
    assert skill_receipt.end("plan-execution") is False



# --- agent types that pin their own model in their definition --------------------------------

SCRIPT = Path(W.__file__).resolve()


def _agent_md(directory, filename, name, model=None):
    directory.mkdir(parents=True, exist_ok=True)
    lines = ["---", "name: %s" % name, "description: test agent"]
    if model is not None:
        lines.append("model: %s" % model)
    lines += ["---", "", "body"]
    (directory / filename).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _armed_dispatch(subagent_type, **extra):
    skill_receipt.start("plan-execution", session_id=SESSION_A)
    event = {"tool_name": "Agent", "session_id": SESSION_A,
             "tool_input": {"subagent_type": subagent_type, "prompt": "x"}}
    event.update(extra)
    return event


def test_the_plugins_own_self_pinned_agent_is_not_denied_when_armed(monkeypatch, capsys):
    """bitranox:baseline-probe pins `model: sonnet` in plugins/bitranox/agents/baseline-probe.md,
    and the Agent tool uses that when the dispatch omits one - so it is pinned, not unpinned."""
    assert W.agent_definition_model("bitranox:baseline-probe") == "sonnet"
    assert run_main(monkeypatch, _armed_dispatch("bitranox:baseline-probe")) == 0
    out = capsys.readouterr()
    assert out.out == "" and out.err == ""


def test_the_plugins_own_self_pinned_agent_is_not_warned_when_unarmed(monkeypatch, capsys):
    run_main(monkeypatch, {"tool_name": "Agent",
                           "tool_input": {"subagent_type": "bitranox:baseline-probe"}})
    assert capsys.readouterr().out == ""


def test_general_purpose_with_no_model_is_still_denied_when_armed(monkeypatch, capsys):
    """Control: a type with no definition anywhere keeps the old answer."""
    run_main(monkeypatch, _armed_dispatch("general-purpose"))
    assert _decision(capsys) == "deny"


def test_another_plugins_agent_type_is_not_resolved_and_keeps_the_old_answer(monkeypatch, capsys):
    run_main(monkeypatch, _armed_dispatch("otherplugin:baseline-probe"))
    assert _decision(capsys) == "deny"


def test_a_user_agent_pinned_in_frontmatter_is_not_denied(home, monkeypatch, capsys):
    """Matched by the frontmatter `name`, which is what the Agent tool dispatches on - the file
    name may differ."""
    _agent_md(home / ".claude" / "agents", "some-file.md", "my-scout", model="haiku")
    run_main(monkeypatch, _armed_dispatch("my-scout"))
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("model", ["inherit", "", None])
def test_a_user_agent_that_inherits_or_names_no_model_is_still_denied(home, monkeypatch, capsys,
                                                                      model):
    _agent_md(home / ".claude" / "agents", "scout.md", "my-scout", model=model)
    run_main(monkeypatch, _armed_dispatch("my-scout"))
    assert _decision(capsys) == "deny"


def test_a_project_agent_is_found_from_the_event_cwd(tmp_path, monkeypatch, capsys):
    proj = tmp_path / "proj"
    _agent_md(proj / ".claude" / "agents", "p.md", "proj-agent", model="opus")
    run_main(monkeypatch, _armed_dispatch("proj-agent", cwd=str(proj)))
    assert capsys.readouterr().out == ""


def test_claude_project_dir_is_preferred_over_the_event_cwd(tmp_path, monkeypatch, capsys):
    proj = tmp_path / "proj"
    _agent_md(proj / ".claude" / "agents", "p.md", "proj-agent", model="opus")
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(proj))
    run_main(monkeypatch, _armed_dispatch("proj-agent", cwd=str(tmp_path / "elsewhere")))
    assert capsys.readouterr().out == ""


def test_a_project_agent_shadows_a_user_agent_of_the_same_name(tmp_path, home, monkeypatch,
                                                               capsys):
    """Project-level definitions take precedence over user-level ones, so an unpinned project
    agent is unpinned even when a user agent of that name pins a model."""
    proj = tmp_path / "proj"
    _agent_md(home / ".claude" / "agents", "u.md", "dup", model="haiku")
    _agent_md(proj / ".claude" / "agents", "p.md", "dup")
    run_main(monkeypatch, _armed_dispatch("dup", cwd=str(proj)))
    assert _decision(capsys) == "deny"


def test_a_file_with_unclosed_frontmatter_is_not_a_definition(home, monkeypatch, capsys):
    d = home / ".claude" / "agents"
    d.mkdir(parents=True)
    (d / "broken.md").write_text("---\nname: my-scout\nmodel: haiku\nbody, never closed\n",
                                 encoding="utf-8")
    run_main(monkeypatch, _armed_dispatch("my-scout"))
    assert _decision(capsys) == "deny"


def test_the_warning_does_not_claim_an_omitted_model_always_inherits():
    """The Agent tool falls back to the agent definition's model before the session model, so
    the bare "an omitted model inherits the session model" premise was false for self-pinned
    types."""
    _, msg = W.assess("Task", {"subagent_type": "general-purpose"})
    assert "inherits the session model" not in msg
    assert "definition" in msg


# --- main()'s degrade paths and the entry point ------------------------------------------------

@pytest.mark.parametrize("body", ["[]", "3", '"text"', "null"])
def test_main_ignores_a_json_event_that_is_not_an_object(monkeypatch, capsys, body):
    monkeypatch.setattr(sys, "stdin", io.StringIO(body))
    assert W.main() == 0
    out = capsys.readouterr()
    assert out.out == "" and out.err == ""


def test_a_receipt_store_that_raises_fails_open_to_the_warning(monkeypatch, capsys):
    """skill_receipt is a separate module; if it raises for any reason the gate must neither
    crash nor deny - it degrades to the unarmed answer (the warning)."""
    def boom(*_a, **_k):
        raise RuntimeError("receipt store broken")

    monkeypatch.setattr(skill_receipt, "is_fresh", boom)
    assert run_main(monkeypatch, _dispatch(SESSION_A)) == 0
    hso = json.loads(capsys.readouterr().out)["hookSpecificOutput"]
    assert "additionalContext" in hso and "permissionDecision" not in hso


def _script_env(home):
    env = {k: v for k, v in os.environ.items()
           if k not in ("CLAUDE_CODE_SESSION_ID", "CLAUDE_PROJECT_DIR", "VIRTUAL_ENV")}
    env.update(HOME=str(home), USERPROFILE=str(home), PYTHONPATH=str(SCRIPT.parent))
    return env


def test_the_script_entry_point_warns_as_a_process(home):
    event = json.dumps({"tool_name": "Task", "tool_input": {"subagent_type": "x"}})
    r = subprocess.run([sys.executable, str(SCRIPT)], input=event, capture_output=True,
                       text=True, encoding="utf-8", errors="replace", env=_script_env(home),
                       timeout=60)
    assert r.returncode == 0 and r.stderr == ""
    assert "additionalContext" in json.loads(r.stdout)["hookSpecificOutput"]


def test_the_script_entry_point_exits_zero_when_main_raises(home):
    """The __main__ guard is the last fail-open: a stdout that cannot be written makes main()
    raise, and the process must still exit 0 rather than wedge the turn with a traceback."""
    driver = (
        "import io, runpy, sys\n"
        "class Unwritable(io.StringIO):\n"
        "    def write(self, s):\n"
        "        raise RuntimeError('stdout gone')\n"
        "sys.stdin = io.StringIO(sys.argv[2])\n"
        "sys.stdout = Unwritable()\n"
        "runpy.run_path(sys.argv[1], run_name='__main__')\n"
    )
    event = json.dumps({"tool_name": "Task", "tool_input": {"subagent_type": "x"}})
    r = subprocess.run([sys.executable, "-c", driver, str(SCRIPT), event], capture_output=True,
                       text=True, encoding="utf-8", errors="replace", env=_script_env(home),
                       timeout=60)
    assert r.returncode == 0, r.stderr
    assert "Traceback" not in r.stderr
