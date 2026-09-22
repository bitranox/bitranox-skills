"""End-to-end tests for the three first-wave classifier sites in SHADOW mode.

Each hook runs in-process exactly as Claude Code drives it (event JSON on stdin), with a real
config file, a real API key env var and the loopback base-URL override pointing at a local fake
TypeSafe server. The detached child is a real process. Two properties are asserted per site:

* the hook's own output is byte-identical with shadow on and off - shadow never decides;
* the child reaches the fake API and appends one log line carrying the regex verdict beside
  Jev's answers, with the state already redacted.
"""

import io
import json
import sys
import time

import pytest

import classifier as cl
import recall_memory as RM
import self_improve_gate as G
import self_improve_signals as sig
import skill_router as SR

GHP = "ghp_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8"


@pytest.fixture
def env(tmp_path, monkeypatch, fake_jev):
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    state = tmp_path / "state"
    state.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setattr("tempfile.gettempdir", lambda: str(state))
    fake = fake_jev()
    monkeypatch.setenv("TYPESAFE_API_KEY", "k" * 20)
    monkeypatch.setenv(cl.BASE_URL_ENV, fake.url)
    return {"home": home, "state": state, "fake": fake}


def _config(home, **knobs):
    (home / ".claude" / ".bitranox-memory.json").write_text(json.dumps(knobs), encoding="utf-8")


def _log(home):
    return home / ".claude" / "self-improve-audit" / cl.SHADOW_LOG


def _wait_for_log(home, timeout=20.0):
    """The child is detached, so the only completion signal is the line it appends."""
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        p = _log(home)
        if p.exists() and p.read_text(encoding="utf-8").strip():
            return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
        time.sleep(0.1)
    raise AssertionError("no shadow log line within %.0fs" % timeout)


def _run(module, monkeypatch, capsys, event):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(event)))
    assert module.main() == 0
    return capsys.readouterr().out


# ---- Stop gate ---------------------------------------------------------------------------

def _stop_event(tmp_path, user, asst):
    t = tmp_path / "transcript.jsonl"
    t.write_text("\n".join([json.dumps({"type": "user", "message": {"content": user}}),
                            json.dumps({"type": "assistant", "message": {"content": asst}})])
                 + "\n", encoding="utf-8")
    return {"transcript_path": str(t), "cwd": str(tmp_path), "session_id": "s-stop"}


@pytest.mark.parametrize("user", ["No, that is wrong - always use uv. token %s" % GHP,
                                  "Please list the files in the repo."])
def test_stop_gate_shadow_logs_and_decides_exactly_as_before(env, tmp_path, monkeypatch, capsys,
                                                              user):
    ev = _stop_event(tmp_path, user, "Listed them.")
    _config(env["home"])
    off = _run(G, monkeypatch, capsys, ev)
    for f in env["state"].iterdir():  # forget "already blocked for this message"
        f.unlink()
    _config(env["home"], classifier_backend="jev", classifier_stop_signal="shadow")
    on = _run(G, monkeypatch, capsys, ev)
    assert on == off
    line = _wait_for_log(env["home"])[-1]
    assert line["site"] == "stop_signal" and line["session_id"] == "s-stop"
    assert line["regex"]["fires"] is bool(off)
    answers = line["results"][0]["answers"]
    assert set(answers) == {q.id for q in cl.stop_signal_questions()}
    assert set(line["states"][0]) == {"user_message", "assistant_reply"}
    assert GHP not in _log(env["home"]).read_text(encoding="utf-8")
    assert GHP not in json.dumps(env["fake"].requests)


def test_stop_gate_spawns_nothing_while_the_site_is_off(env, tmp_path, monkeypatch, capsys):
    _config(env["home"], classifier_backend="jev")  # backend on, site knob left at off
    _run(G, monkeypatch, capsys, _stop_event(tmp_path, "No, wrong.", "ok"))
    time.sleep(1.0)
    assert not _log(env["home"]).exists() and env["fake"].requests == []


# ---- skill router -------------------------------------------------------------------------

def test_skill_router_shadow_asks_one_noul_per_skill_and_keeps_its_output(env, monkeypatch,
                                                                          capsys):
    prompt = "git commit fails with a CRLF line ending and the hook is not executable"
    ev = {"prompt": prompt, "cwd": "/p/x", "session_id": "s-router"}
    _config(env["home"])
    off = _run(SR, monkeypatch, capsys, ev)
    for f in (env["home"] / ".claude" / "self-improve-audit").glob("*.skillrouter-*"):
        f.unlink()  # forget "already nudged this session"
    _config(env["home"], classifier_backend="jev", classifier_skill_router="shadow")
    on = _run(SR, monkeypatch, capsys, dict(ev))
    assert on == off
    line = _wait_for_log(env["home"])[-1]
    assert line["site"] == "skill_router"
    skills = cl.load_skill_descriptions()
    assert len(skills) >= 20
    assert set(line["results"][0]["answers"]) == set(skills) | {cl.NEW_TASK_ID}
    assert line["regex"]["selected"] == [s for s, _n in SR.match(prompt, SR.load_triggers())]
    assert line["states"][0] == {"user_prompt": prompt, "project": "x"}


# ---- recall -------------------------------------------------------------------------------

def _mem(proj, name, text):
    d = sig.memory_dir(proj)
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(text, encoding="utf-8")


def test_recall_shadow_reranks_the_shortlist_pairwise_and_keeps_its_output(env, monkeypatch,
                                                                           capsys):
    _mem("/p/other", "make-test.md", "Run make test with VIRTUAL_ENV=$PWD/.venv before committing")
    _mem("/p/other2", "frob.md", "The frobnicator needs make test too, password: hunter2")
    ev = {"prompt": "run make test", "cwd": "/p/cur", "session_id": "s-recall"}
    _config(env["home"])
    off = _run(RM, monkeypatch, capsys, ev)
    for f in (env["home"] / ".claude" / "self-improve-audit").glob("*.recall-*"):
        f.unlink()
    _config(env["home"], classifier_backend="jev", classifier_recall_rerank="shadow")
    on = _run(RM, monkeypatch, capsys, dict(ev))
    assert json.loads(on)["hookSpecificOutput"] == json.loads(off)["hookSpecificOutput"]
    line = _wait_for_log(env["home"])[-1]
    assert line["site"] == "recall_rerank"
    shortlist = line["regex"]["shortlist"]
    assert len(shortlist) == len(line["results"]) == len(line["states"]) == 2
    assert all(set(s) == {"user_prompt", "memory_note"} for s in line["states"])
    assert set(line["regex"]["selected"]) <= set(shortlist)
    assert "hunter2" not in _log(env["home"]).read_text(encoding="utf-8")
    assert len(env["fake"].requests) == 2  # one pair request per candidate


def test_stop_gate_shadow_sends_the_human_prompt_and_the_event_reply_in_a_tool_turn(
        env, tmp_path, monkeypatch, capsys):
    # The real shape: prompt, tool call, tool_result, and the final reply only in the event.
    t = tmp_path / "transcript.jsonl"
    t.write_text("\n".join([
        json.dumps({"type": "user", "message": {"content": "no, that is wrong - use uv"},
                    "origin": {"kind": "human"}}),
        json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": "t1", "name": "Bash", "input": {}}]}}),
        json.dumps({"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": "t1", "content": "ok"}]}}),
    ]) + "\n", encoding="utf-8")
    _config(env["home"], classifier_backend="jev", classifier_stop_signal="shadow")
    _run(G, monkeypatch, capsys, {"transcript_path": str(t), "cwd": str(tmp_path),
                                  "session_id": "s-tool", "last_assistant_message": "Switched."})
    line = _wait_for_log(env["home"])[-1]
    assert line["states"][0] == {"user_message": "no, that is wrong - use uv",
                                 "assistant_reply": "Switched."}
    assert line["regex"]["fires"] is True


def test_recall_shadow_shows_each_note_by_its_description_and_tags_the_view(env, monkeypatch,
                                                                            capsys):
    _mem("/p/other", "make-test.md",
         "---\nname: make-test-venv\ndescription: When running make test, set VIRTUAL_ENV.\n---\n\n"
         + "unrelated padding\n" * 60 + "run make test here\n")
    _config(env["home"], classifier_backend="jev", classifier_recall_rerank="shadow")
    _run(RM, monkeypatch, capsys, {"prompt": "run make test", "cwd": "/p/cur",
                                   "session_id": "s-view"})
    line = _wait_for_log(env["home"])[-1]
    assert line["regex"]["note_view"] == "summary-v1"
    assert line["states"][0]["memory_note"] == (
        "make-test-venv: When running make test, set VIRTUAL_ENV.")


# ---- the reply the person answered --------------------------------------------------------
# "yes", "go" or "check it again" cannot be judged without the message they answer.

def _transcript(tmp_path, *records):
    t = tmp_path / "transcript.jsonl"
    t.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    return str(t)


def _typed(text):
    return {"type": "user", "message": {"content": text}, "origin": {"kind": "human"}}


def _said(text):
    return {"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}


def test_stop_gate_shadow_sends_the_reply_the_prompt_answered(env, tmp_path, monkeypatch, capsys):
    t = _transcript(tmp_path, _typed("fix it"), _said("Fixed. Shall I bump the version too?"),
                    _typed("yes"))
    _config(env["home"], classifier_backend="jev", classifier_stop_signal="shadow")
    _run(G, monkeypatch, capsys, {"transcript_path": t, "cwd": str(tmp_path), "session_id": "s-p",
                                  "last_assistant_message": "Bumped to 1.2.0."})
    line = _wait_for_log(env["home"])[-1]
    assert line["states"][0] == {"previous_assistant_message": "Fixed. Shall I bump the version too?",
                                 "user_message": "yes", "assistant_reply": "Bumped to 1.2.0."}
    assert line["regex"]["context_view"] == "prev-reply-v1"


def test_skill_router_shadow_sends_the_reply_the_prompt_answers(env, tmp_path, monkeypatch,
                                                                capsys):
    t = _transcript(tmp_path, _typed("look at the log"), _said("The shadow log has 19 rows."))
    _config(env["home"], classifier_backend="jev", classifier_skill_router="shadow")
    _run(SR, monkeypatch, capsys, {"prompt": "check it again", "cwd": "/p/x", "session_id": "s-r",
                                   "transcript_path": t})
    line = _wait_for_log(env["home"])[-1]
    assert line["states"][0] == {"user_prompt": "check it again", "project": "x",
                                 "previous_assistant_message": "The shadow log has 19 rows."}
    assert line["regex"]["context_view"] == "prev-reply-v1"


def test_recall_shadow_sends_the_reply_the_prompt_answers(env, tmp_path, monkeypatch, capsys):
    _mem("/p/other", "make-test.md", "Run make test with VIRTUAL_ENV=$PWD/.venv before committing")
    t = _transcript(tmp_path, _typed("status?"), _said("The make test gate is red."))
    _config(env["home"], classifier_backend="jev", classifier_recall_rerank="shadow")
    _run(RM, monkeypatch, capsys, {"prompt": "run make test", "cwd": "/p/cur", "session_id": "s-c",
                                   "transcript_path": t})
    line = _wait_for_log(env["home"])[-1]
    assert all(s["previous_assistant_message"] == "The make test gate is red."
               for s in line["states"])
    assert line["regex"]["context_view"] == "prev-reply-v1"


def test_skill_router_shadow_sends_project_activity_and_skills_in_use(env, tmp_path, monkeypatch,
                                                                     capsys):
    proj = tmp_path / "shop"
    (proj / "sub").mkdir(parents=True)
    (proj / "CLAUDE.local.md").write_text("<!-- x -->\nWHAT: An online shop backend.\n",
                                          encoding="utf-8")
    t = _transcript(tmp_path, _typed("run it"),
                    {"type": "assistant", "message": {"content": [
                        {"type": "tool_use", "id": "a", "name": "Skill",
                         "input": {"skill": "bitranox:process-test-driven-development"}},
                        {"type": "tool_use", "id": "b", "name": "Bash",
                         "input": {"command": "pytest", "description": "Run the tests"}}]}},
                    _said("All 12 tests pass."))
    already = SR._state_file(str(proj / "sub"), "s-ctx")
    already.parent.mkdir(parents=True, exist_ok=True)
    already.write_text("compuse-git\n", encoding="utf-8")
    _config(env["home"], classifier_backend="jev", classifier_skill_router="shadow")
    _run(SR, monkeypatch, capsys, {"prompt": "check it again", "cwd": str(proj / "sub"),
                                   "session_id": "s-ctx", "transcript_path": t})
    line = _wait_for_log(env["home"])[-1]
    state = line["states"][0]
    assert state["project"] == "shop: An online shop backend."
    assert state["recent_activity"] == "Skill: process-test-driven-development; Bash: Run the tests"
    assert state["skills_already_used"] == "compuse-git, process-test-driven-development"
    assert line["regex"]["router_view"] == "ctx-v1"
    assert "_new_task" in line["results"][0]["answers"]


def test_skill_router_shadow_sends_a_notification_s_own_fields(env, tmp_path, monkeypatch,
                                                               capsys):
    # A machine turn scores no keywords, but a background task that FAILED can still need a
    # skill - so the shadow judges the envelope's own fields instead of the envelope as a
    # pretend prompt, and the row is tagged so it never pools with typed-prompt rows.
    notification = ("<task-notification>\n<task-id>b6bgpwg53</task-id>\n"
                    "<tool-use-id>toolu_01ABC</tool-use-id>\n"
                    "<output-file>/tmp/claude-1000/-media-srv-main-softdev/tasks/b6bgpwg53.output"
                    "</output-file>\n<status>failed</status>\n"
                    "<summary>Background command \"Run the repo CI-parity gate\" failed with exit "
                    "code 1</summary>\n</task-notification>")
    _config(env["home"], classifier_backend="jev", classifier_skill_router="shadow")
    out = _run(SR, monkeypatch, capsys, {"prompt": notification, "cwd": str(tmp_path),
                                         "session_id": "s-notify"})
    assert out == ""                                    # and it still nudges nothing
    line = _wait_for_log(env["home"])[-1]
    state = line["states"][0]
    assert "user_prompt" not in state
    assert state["task_status"] == "failed"
    assert "CI-parity gate" in state["task_summary"]
    assert "b6bgpwg53" not in json.dumps(state) and "toolu" not in json.dumps(state)
    assert line["regex"]["selected"] == []              # the keyword arm says nothing now
    assert line["regex"]["notify_view"] == cl.NOTIFY_VIEW
    gate = line["results"][0]["answers"][cl.NEW_TASK_ID]
    assert gate["type"] == "noul"


def test_router_questions_for_a_notification_name_its_fields_not_the_prompt():
    qs = cl.skill_router_questions({"x": "does x"}, turn=cl.TURN_NOTIFICATION)
    assert [q.id for q in qs] == [cl.NEW_TASK_ID, "x"]
    for q in qs:
        assert "`user_prompt`" not in q.instructions
        assert "`task_status`" in q.instructions or "`task_summary`" in q.instructions


def test_router_questions_still_default_to_the_typed_prompt():
    qs = cl.skill_router_questions({"x": "does x"})
    assert all("`user_prompt`" in q.instructions for q in qs)


def test_questions_name_the_previous_message_field():
    for questions in (cl.stop_signal_questions(), cl.recall_questions(),
                      cl.skill_router_questions({"x": "does x"})):
        assert any("`previous_assistant_message`" in q.instructions for q in questions)
