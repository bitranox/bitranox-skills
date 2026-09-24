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
    assert line["regex"]["roster"] == "shipped" and line["regex"]["roster_size"] == len(skills)


def test_skill_router_shadow_offers_the_sessions_installed_skills(env, tmp_path, monkeypatch,
                                                                  capsys):
    # A skill from another plugin and a built-in reach the options once the transcript lists them.
    listing = {"type": "attachment", "attachment": {
        "type": "skill_listing", "isInitial": True, "skillCount": 3,
        "names": ["bitranox:files-edit-xml", "typesafe:typesafe-ai", "update-config"],
        "content": "- bitranox:files-edit-xml: Use when editing XML.\n"
                   "- typesafe:typesafe-ai: Build AI-powered software with TypeSafe.\n"
                   "- update-config: Configure the Claude Code harness via settings.json."}}
    t = tmp_path / "transcript.jsonl"
    t.write_text(json.dumps(listing) + "\n", encoding="utf-8")
    _config(env["home"], classifier_backend="jev", classifier_skill_router="shadow")
    _run(SR, monkeypatch, capsys, {"prompt": "add a TypeSafe classifier to this app",
                                   "cwd": "/p/x", "session_id": "s-roster",
                                   "transcript_path": str(t)})
    line = _wait_for_log(env["home"])[-1]
    assert set(line["results"][0]["answers"]) == {"files-edit-xml", "typesafe:typesafe-ai",
                                                  "update-config", cl.NEW_TASK_ID}
    assert line["regex"]["roster"] == "transcript" and line["regex"]["roster_size"] == 3


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


def test_router_rows_record_which_keyword_matcher_judged_them(env, tmp_path, monkeypatch, capsys):
    # The keyword arm is half of every comparison, so when IT changes its rows must stop pooling
    # with the old ones. 7.6.0 changed what it scores while the input views stayed the same, which
    # left 15 notification rows judged by the old matcher in the same group as typed prompts.
    _config(env["home"], classifier_backend="jev", classifier_skill_router="shadow")
    _run(SR, monkeypatch, capsys, {"prompt": "git commit fails with a CRLF line ending",
                                   "cwd": str(tmp_path), "session_id": "s-matcher"})
    line = _wait_for_log(env["home"])[-1]
    assert line["regex"]["matcher_view"] == SR.MATCHER_VIEW


def test_router_questions_for_a_notification_name_its_fields_not_the_prompt():
    qs = cl.skill_router_questions({"x": "does x"}, NOTIFICATION_STATE,
                                   turn=cl.TURN_NOTIFICATION)
    assert [q.id for q in qs] == [cl.NEW_TASK_ID, "x"]
    for q in qs:
        assert "`user_prompt`" not in q.instructions
        assert "`task_status`" in q.instructions or "`task_summary`" in q.instructions


def test_router_questions_still_default_to_the_typed_prompt():
    qs = cl.skill_router_questions({"x": "does x"}, MID_SESSION)
    assert all("`user_prompt`" in q.instructions for q in qs)


def test_questions_name_the_previous_message_field():
    for questions in (cl.stop_signal_questions(), cl.recall_questions(),
                      cl.skill_router_questions({"x": "does x"}, MID_SESSION)):
        assert any("`previous_assistant_message`" in q.instructions for q in questions)


def test_the_gate_ignores_a_reasoning_field_even_when_one_is_sent():
    # Measured 2026-09-24 and rejected: naming the previous turn's reasoning made the gate LOWER
    # on 139 of 245 cells against higher on 61, so the router spoke LESS where missing a needed
    # skill is already the dominant failure. This pins the rejection - a caller that sends the
    # field must not silently change the question, which is how it would creep back in.
    state = dict(MID_SESSION, previous_assistant_reasoning="I was weighing two parser designs.")
    assert (cl.skill_router_questions({"x": "does x"}, state)[0].instructions
            == cl.skill_router_questions({"x": "does x"}, MID_SESSION)[0].instructions)


# ---- the choice-shaped router arm ------------------------------------------------------------
# One `choice` over the whole roster instead of one `noul` per skill. The gate is unchanged: it
# is measured as working here (bimodal, suppressing 29 of 43 rows), so the arm moves exactly one
# variable - the shape of the skill question - and nothing else.


def test_router_choice_offers_every_skill_and_a_no_match_option():
    qs = cl.skill_router_choice_questions({"a": "does a", "b": "does b"}, MID_SESSION)
    assert [q.id for q in qs] == [cl.NEW_TASK_ID, cl.PICK_ID]
    pick = qs[1]
    assert pick.type == "choice"
    assert set(pick.criteria) == {"a", "b", cl.NO_SKILL_KEY}
    assert pick.criteria["a"] == "does a"


def test_the_no_match_key_cannot_collide_with_a_skill_name():
    # Skill names are hyphenated by the taxonomy, so an underscore key is unreachable by one.
    assert "_" in cl.NO_SKILL_KEY and "-" not in cl.NO_SKILL_KEY
    assert cl.PICK_ID.startswith("_")


def test_router_choice_keeps_the_gate_exactly_as_the_noul_arm_asks_it():
    gate_choice = cl.skill_router_choice_questions({"a": "does a"}, MID_SESSION)[0]
    gate_noul = cl.skill_router_questions({"a": "does a"}, MID_SESSION)[0]
    assert gate_choice == gate_noul


def test_router_choice_for_a_notification_names_its_fields_not_the_prompt():
    qs = cl.skill_router_choice_questions({"x": "does x"}, NOTIFICATION_STATE,
                                          turn=cl.TURN_NOTIFICATION)
    for q in qs:
        assert "`user_prompt`" not in q.instructions
        assert "`task_status`" in q.instructions or "`task_summary`" in q.instructions


def test_short_description_drops_the_use_when_boilerplate():
    # 80 of 81 shipped descriptions open with "Use when" or another "Use <preposition>", so the
    # option list repeats it 80 times. The question frame says it once instead.
    assert cl.short_description("Use when parsing .gitignore files").startswith("parsing")
    assert cl.short_description("Use to convert documents").startswith("convert")
    assert cl.short_description("Use after finishing a refactor").startswith("finishing")


def test_short_description_cuts_on_a_word_boundary_within_the_cap():
    text = "Use when writing, reviewing, or debugging Bash scripts and shell constructs"
    short = cl.short_description(text, cap=30)
    assert len(short) <= 30
    assert not short.endswith("-")
    assert short.split()[-1] in text.split()


def test_short_description_leaves_a_description_that_is_already_short():
    assert cl.short_description("Use when x happens", cap=200) == "x happens"


def test_rerank_asks_one_choice_over_the_shortlist_and_one_noul_per_candidate():
    qs = cl.skill_router_rerank_questions({"a": "the whole body of a", "b": "the whole body of b"})
    assert [q.id for q in qs] == [cl.PICK_ID, "a", "b"]
    assert qs[0].type == "choice"
    assert set(qs[0].criteria) == {"a", "b", cl.NO_SKILL_KEY}
    assert all(q.type == "noul" for q in qs[1:])
    assert "'a'" in qs[1].instructions and "the whole body of a" in qs[1].instructions


# ---- no question may name a state field the caller did not supply ----------------------------
# Found 2026-09-23 by a planted control. `_router_fields` leaves out a field that is empty, and on
# the FIRST prompt of a session `previous_assistant_message` and `recent_activity` do not exist
# yet - but the gate named them anyway, so it was asked to contrast against nothing. Measured, it
# then HEDGED at 0.66-0.70 against a 0.7 threshold; with both fields present the same prompt
# scores 0.89-0.90 and its negative 0.05-0.06. The gate was a coin flip exactly where a session
# starts, and every arm is measured through that gate.

# The minimum a real caller produces: `_turn_fields` plus `_project_line`, which never returns
# empty. Everything else is absent until a session has a history.
FIRST_PROMPT = {"user_prompt": "write a parser for the log", "project": "p: a project"}
MID_SESSION = {"previous_assistant_message": "I rewrote the parser's error branch.",
               "user_prompt": "write a parser for the log", "project": "p: a project",
               "recent_activity": "Edit: parser.py; Bash: pytest",
               "skills_already_used": "compuse-bash"}
NOTIFICATION_STATE = {"task_status": "failed", "task_summary": "the build broke",
                      "project": "p: a project"}
OPTIONAL_FIELDS = ("previous_assistant_message", "recent_activity", "skills_already_used")


def _named_but_absent(questions, fields):
    """Every (question id, field) where the question names a field the caller did not send."""
    return [(q.id, f) for q in questions for f in OPTIONAL_FIELDS
            if "`%s`" % f in q.instructions and not fields.get(f)]


@pytest.mark.parametrize("build", [cl.skill_router_questions, cl.skill_router_choice_questions])
def test_no_router_question_names_a_field_the_first_prompt_of_a_session_lacks(build):
    assert _named_but_absent(build({"x": "does x"}, FIRST_PROMPT), FIRST_PROMPT) == []


@pytest.mark.parametrize("build", [cl.skill_router_questions, cl.skill_router_choice_questions])
def test_a_notification_question_names_no_absent_field_either(build):
    questions = build({"x": "does x"}, NOTIFICATION_STATE, turn=cl.TURN_NOTIFICATION)
    assert _named_but_absent(questions, NOTIFICATION_STATE) == []


@pytest.mark.parametrize("build", [cl.skill_router_questions, cl.skill_router_choice_questions])
def test_the_gate_still_names_both_fields_when_the_session_has_a_history(build):
    # The wording measured as working (bimodal, 0.89-0.90 against 0.05-0.06) must not move for a
    # caller that supplies the state, or this fix silently re-measures the arm it is fixing.
    gate = build({"x": "does x"}, MID_SESSION)[0]
    assert ("rather than continuing, approving or checking the work that "
            "`previous_assistant_message` and `recent_activity` describe?") in gate.instructions


def test_the_gate_names_only_the_one_context_field_that_is_there():
    fields = dict(FIRST_PROMPT, recent_activity="Edit: parser.py")
    gate = cl.skill_router_questions({"x": "does x"}, fields)[0]
    assert "`recent_activity` describes?" in gate.instructions
    assert "`previous_assistant_message`" not in gate.instructions


def test_a_skill_question_drops_the_already_used_clause_when_nothing_has_been_used():
    asked = cl.skill_router_questions({"x": "does x"}, FIRST_PROMPT)[1]
    used = cl.skill_router_questions({"x": "does x"}, MID_SESSION)[1]
    assert "skills_already_used" not in asked.instructions
    assert "`skills_already_used`" in used.instructions
    assert asked.instructions.endswith("Skill description: does x")


def test_the_choice_pick_drops_the_already_used_clause_too():
    pick = cl.skill_router_choice_questions({"x": "does x"}, FIRST_PROMPT)[1]
    assert "skills_already_used" not in pick.instructions
    assert cl.NO_SKILL_KEY in pick.criteria


def test_the_two_arms_still_ask_the_same_gate_for_the_same_state():
    for fields in (FIRST_PROMPT, MID_SESSION):
        assert (cl.skill_router_choice_questions({"a": "does a"}, fields)[0]
                == cl.skill_router_questions({"a": "does a"}, fields)[0])


# ---- option text written FOR the router ------------------------------------------------------
# The shipped descriptions are written for the KEYWORD matcher: paragraph-long trigger lists. The
# API's own guidance for an option catalogue is different - "Start with a one-line description per
# option. When two options are similar and the model keeps confusing them, describe each one with
# an object instead of a string. Give it fields for what the option covers, what belongs to a
# neighboring option instead, and a few example inputs." (docs.typesafe.ai/primitives/choice).
# `criteria` accepts string | object | array | null, so the structured form is a supported value
# and not a workaround. Measured motivation: 6 of 11 adjudicated misses wanted
# meta-context-watcher and lost to a neighbour, with the right skill ranked top at 0.58-0.73.


def test_router_criteria_fall_back_to_the_description_for_a_skill_with_no_entry(tmp_path):
    # The file is filled in incrementally, so a missing entry must degrade to the description
    # rather than empty the option - an option with no text is worse than a verbose one.
    path = tmp_path / "router_criteria.json"
    path.write_text(json.dumps({"a": "one discriminating line"}), encoding="utf-8")
    out = cl.load_router_criteria({"a": "Use when ...", "b": "Use when b happens"}, path=path)
    assert out["a"] == "one discriminating line"
    assert out["b"] == "Use when b happens"
    assert set(out) == {"a", "b"}


def test_a_structured_router_entry_stays_an_object_all_the_way_to_the_request(tmp_path):
    # `str(dict)` would be the same LENGTH as the dict in a size check and would reach the model as
    # a Python repr, so the only thing that catches it is asserting the type at the wire boundary.
    entry = {"what": "writes the handover", "not_for": "reviewing a decision",
             "examples": ["write handover", "what is still open"]}
    path = tmp_path / "router_criteria.json"
    path.write_text(json.dumps({"a": entry}), encoding="utf-8")
    roster = cl.load_router_criteria({"a": "Use when ..."}, path=path)
    assert roster["a"] == entry
    pick = cl.skill_router_choice_questions(roster, MID_SESSION)[1]
    assert pick.criteria["a"] == entry
    assert pick.to_api()["criteria"]["a"]["not_for"] == "reviewing a decision"
    json.dumps(pick.to_api())            # the request really serialises


def test_router_criteria_survive_a_missing_or_broken_file(tmp_path):
    # A hook must never wedge a prompt over its own data file.
    missing = tmp_path / "nope.json"
    assert cl.load_router_criteria({"a": "Use when a"}, path=missing) == {"a": "Use when a"}
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    assert cl.load_router_criteria({"a": "Use when a"}, path=broken) == {"a": "Use when a"}


def test_the_shipped_router_criteria_name_only_real_skills():
    # A typo'd key is silently inert: it never matches a skill, so its careful wording reaches
    # nobody and the option keeps the description it was written to replace.
    shipped = cl.load_router_criteria(cl.load_skill_descriptions())
    assert set(shipped) == set(cl.load_skill_descriptions())


def test_the_router_hook_asks_only_about_the_state_it_sends(env, tmp_path, monkeypatch, capsys):
    # End to end through the hook, which is where the defect lived: the questions are built from
    # one dict and the fields sent from another, so only a run that reads what reached the API can
    # prove they agree. No transcript, so this is the first prompt of a session.
    _config(env["home"], classifier_backend="jev", classifier_skill_router="shadow")
    _run(SR, monkeypatch, capsys, {"prompt": "write a parser for the log",
                                   "cwd": str(tmp_path), "session_id": "s-first"})
    _wait_for_log(env["home"])
    sent = env["fake"].requests[0]["json"]
    state = sent.get("state") or {}
    assert "user_prompt" in state  # the request really carried the turn, so absence means absence
    for qid, question in sent["questions"].items():
        for field in OPTIONAL_FIELDS:
            if not state.get(field):
                assert "`%s`" % field not in question["instructions"], qid
