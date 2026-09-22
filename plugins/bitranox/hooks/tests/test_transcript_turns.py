"""Tests for transcript_turns.py - the last turn's prompt, reply and the reply before the prompt."""
import json

import transcript_turns as T


def _user(text, kind="human"):
    return {"type": "user", "message": {"content": text}, "origin": {"kind": kind}}


def _asst(text):
    return {"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}


def _tool_use():
    return {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "t", "name": "Bash",
                                                          "input": {}}]}}


def _tool_result():
    return {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t",
                                                     "content": "ok"}]}}


def _write(tmp_path, records):
    p = tmp_path / "t.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    return str(p)


def test_the_reply_before_the_prompt_is_the_one_the_person_answered(tmp_path):
    t = _write(tmp_path, [_user("fix it"), _asst("Shall I also bump the version?"),
                          _user("yes"), _tool_use(), _tool_result(), _asst("Bumped.")])
    turn = T.read_turn(t)
    assert turn.prompt == "yes"
    assert turn.reply == "Bumped."
    assert turn.reply_before_prompt == "Shall I also bump the version?"


def test_a_tool_only_record_never_blanks_the_reply_before_the_prompt(tmp_path):
    t = _write(tmp_path, [_asst("Proposal A or B?"), _tool_use(), _user("B")])
    assert T.read_turn(t).reply_before_prompt == "Proposal A or B?"


def _hook_feedback():
    return {"type": "user", "isMeta": True,
            "message": {"content": "Stop hook feedback:\nA learning signal was detected this turn."}}


def _skill_body():
    return {"type": "user", "isMeta": True,
            "message": {"content": "Base directory for this skill: /x\n# Skill"}}


def test_an_answer_to_stop_hook_feedback_does_not_displace_the_reply_the_person_answered(tmp_path):
    # The real shape: the Stop gate blocks, the assistant answers the hook in one line, and the
    # person then replies to the substantive message before it.
    t = _write(tmp_path, [_user("improve it"), _asst("Shall I change the recall input first?"),
                          _hook_feedback(), _asst("Nothing new to record."), _user("yes")])
    turn = T.read_turn(t)
    assert turn.reply_before_prompt == "Shall I change the recall input first?"
    t2 = _write(tmp_path, [_asst("Shall I change the recall input first?"), _hook_feedback(),
                           _asst("Nothing new to record.")])
    assert T.last_reply(t2) == "Shall I change the recall input first?"


def test_the_reply_after_an_invoked_skill_body_is_still_the_reply(tmp_path):
    t = _write(tmp_path, [_user("audit it"), _skill_body(), _asst("Audit done: 3 findings."),
                          _user("fix them")])
    assert T.read_turn(t).reply_before_prompt == "Audit done: 3 findings."


def test_the_first_prompt_of_a_session_has_no_reply_before_it(tmp_path):
    t = _write(tmp_path, [_user("hello")])
    turn = T.read_turn(t)
    assert turn.prompt == "hello" and turn.reply_before_prompt == ""


def test_an_injected_user_record_is_not_the_prompt(tmp_path):
    t = _write(tmp_path, [_asst("Ready."), _user("go"),
                          _user("<task-notification>done</task-notification>", kind="task")])
    turn = T.read_turn(t)
    assert turn.prompt == "go" and turn.reply_before_prompt == "Ready."


def test_last_reply_is_the_newest_assistant_text_whatever_follows_it(tmp_path):
    # At UserPromptSubmit the new prompt may or may not be on disk yet; either way the reply the
    # person is answering is the newest assistant text.
    t = _write(tmp_path, [_user("a"), _asst("First."), _user("b"), _asst("Second."), _tool_use()])
    assert T.last_reply(t) == "Second."
    t2 = _write(tmp_path, [_user("a"), _asst("First."), _user("b")])
    assert T.last_reply(t2) == "First."


def test_missing_transcript_reads_as_empty(tmp_path):
    turn = T.read_turn(str(tmp_path / "absent.jsonl"))
    assert (turn.prompt, turn.reply, turn.reply_before_prompt) == ("", "", "")
    assert T.last_reply(str(tmp_path / "absent.jsonl")) == ""
    assert T.last_reply("") == ""


def test_the_window_widens_past_a_huge_tool_output_to_find_the_prompt(tmp_path):
    big = {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t",
                                                    "content": "x" * 200_000}]}}
    t = _write(tmp_path, [_asst("Which one?"), _user("the second"), _tool_use(), big])
    turn = T.read_turn(t, tail_bytes=4096)
    assert turn.prompt == "the second" and turn.reply_before_prompt == "Which one?"


# ---- recent activity and skills in use -----------------------------------------------------

def _call(name, **inp):
    return {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": name,
                                                          "name": name, "input": inp}]}}


def test_recent_activity_labels_the_last_tool_calls_oldest_first(tmp_path):
    t = _write(tmp_path, [
        _call("Read", file_path="/a/b/old.py"),
        _call("Bash", command="ssh host 'secret stuff'", description="Run the shadow report"),
        _call("Edit", file_path="/repo/plugins/bitranox/hooks/recall-memory.py"),
        _call("Skill", skill="bitranox:meta-context-watcher"),
        _call("WebFetch", url="https://example.invalid/x")])
    assert T.recent_activity(t, n=4) == ("Bash: Run the shadow report; Edit: recall-memory.py; "
                                         "Skill: meta-context-watcher; WebFetch")


def test_recent_activity_never_sends_a_bash_command_line(tmp_path):
    # The command can carry hostnames and paths; the description the harness requires cannot
    # be relied on to exist, so a Bash call without one is only named.
    t = _write(tmp_path, [_call("Bash", command="ssh root@10.0.0.5 cat /etc/shadow")])
    assert T.recent_activity(t) == "Bash"


def test_recent_activity_is_capped(tmp_path):
    t = _write(tmp_path, [_call("Bash", description="x" * 200) for _ in range(6)])
    assert len(T.recent_activity(t, n=6, cap=300)) <= 300 + len(T.EXCERPT_MARK)


def test_skills_used_are_the_skills_invoked_this_session_without_their_plugin_prefix(tmp_path):
    t = _write(tmp_path, [_call("Skill", skill="bitranox:meta-context-watcher"),
                          _call("Skill", skill="toolbox"),
                          _call("Skill", skill="bitranox:meta-context-watcher")])
    assert T.skills_used(t) == ["meta-context-watcher", "toolbox"]


def test_activity_readers_on_a_missing_transcript_are_empty(tmp_path):
    assert T.recent_activity(str(tmp_path / "absent.jsonl")) == ""
    assert T.skills_used("") == []


# ---- excerpt -------------------------------------------------------------------------------

def test_excerpt_keeps_a_short_text_whole():
    assert T.excerpt("  short reply  ", 300) == "short reply"


def test_excerpt_keeps_both_ends_of_a_long_text():
    text = "HEADLINE " + "m" * 1000 + " Shall I do that?"
    out = T.excerpt(text, 100)
    assert out.startswith("HEADLINE ")
    assert out.endswith("Shall I do that?")
    assert " [...] " in out
    assert len(out) <= 100 + len(" [...] ")
