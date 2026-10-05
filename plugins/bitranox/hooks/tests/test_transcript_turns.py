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


def test_excerpt_with_a_tiny_cap_is_bounded_by_the_cap():
    # half = cap // 2 is 0 for a cap of 0 or 1, and text[-0:] is the WHOLE text.
    assert T.excerpt("abcdef", 1) == "a"
    assert T.excerpt("abcdef", 0) == ""
    assert T.excerpt("abcdefghij", 4) == "ab [...] ij"   # control: the normal path is unchanged


# ---- the reply before the prompt, when it sits outside the first window ---------------------

def _big_result(n):
    return {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t",
                                                     "content": "x" * n}]}}


def test_the_reply_before_the_prompt_is_found_past_a_huge_output_before_the_prompt(tmp_path):
    # The prompt fits in the first window but the reply it answers does not: a large tool output
    # sits between them. Finding the prompt is not enough to stop widening.
    t = _write(tmp_path, [_user("start"), _asst("Shall I go on?"), _tool_use(),
                          _big_result(10_000), _user("yes"), _asst("Done.")])
    turn = T.read_turn(t, tail_bytes=1024)
    assert turn.prompt == "yes"
    assert turn.reply_before_prompt == "Shall I go on?"
    assert T.last_reply(t, tail_bytes=1024) == "Done."


def test_a_previous_turn_with_no_text_is_final_once_its_prompt_is_in_the_window(tmp_path):
    # Control: the turn before had no assistant text at all. Once the previous PROMPT is in the
    # window there is nothing further back to find, so the empty answer is the right one - the
    # text before THAT prompt answered an older question.
    t = _write(tmp_path, [_asst("Ancient text that answers an older prompt."), _big_result(10_000),
                          _user("run it"), _tool_use(), _tool_result(), _user("again")])
    turn = T.read_turn(t, tail_bytes=256)
    assert turn.prompt == "again" and turn.reply_before_prompt == ""


def test_widening_stops_at_max_bytes(tmp_path):
    # The only prompt sits at the very start, behind ~40 KiB of tool output. A 4 KiB cap must
    # stop the widening before it gets there; the uncapped read is the control that it exists.
    t = _write(tmp_path, [_user("far back")] + [_tool_result() for _ in range(600)])
    assert T.read_turn(t, tail_bytes=1024, max_bytes=4096) == T.Turn("", "", "")
    assert T.read_turn(t, tail_bytes=1024).prompt == "far back"


# ---- records that are not what a reader expects ----------------------------------------------

def test_a_line_that_is_json_but_not_an_object_is_skipped(tmp_path):
    p = tmp_path / "t.jsonl"
    lines = [json.dumps(_asst("Ready?")), "[]", "42", '"text"', "null",
             json.dumps({"type": "user", "message": None}),
             json.dumps({"type": "assistant", "message": None}),
             json.dumps({"type": "assistant", "message": "a string"}),
             json.dumps(_user("go")), json.dumps(_call("Skill", skill="bitranox:x"))]
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    t = str(p)
    turn = T.read_turn(t)
    assert turn.prompt == "go" and turn.reply_before_prompt == "Ready?"
    assert T.recent_activity(t) == "Skill: x"
    assert T.skills_used(t) == ["x"]


def test_human_text_and_is_hook_feedback_reject_what_is_not_a_record():
    for obj in (None, [], "text", {"type": "user", "message": None},
                {"type": "user", "message": "not a dict"}):
        assert T.human_text(obj) == ""
        assert T.is_hook_feedback(obj) is False


def test_a_compact_summary_after_the_prompt_is_not_the_prompt(tmp_path):
    summary = {"type": "user", "isCompactSummary": True, "origin": {"kind": "human"},
               "message": {"content": "This session is being continued from a previous one."}}
    t = _write(tmp_path, [_asst("Ready."), _user("go on"), summary, _asst("Continuing.")])
    turn = T.read_turn(t)
    assert turn.prompt == "go on" and turn.reply_before_prompt == "Ready."


def test_human_text_uses_the_whole_not_typed_registry():
    # A pattern shape (no literal prefix to list) must be refused here too, not only by
    # looks_typed: read_turn would otherwise take the harness's notice as the person's prompt.
    assert T.human_text(_user("3 background agents were stopped by the user.")) == ""
    assert T.human_text(_user("<task-notification>x</task-notification>")) == ""
    assert T.human_text(_user("the 3 background agents were fine")) != ""   # control


# ---- prompts typed while the assistant was busy -------------------------------------------------
# Such a prompt is written ONLY as an `attachment` record of type `queued_command` (plus two
# `queue-operation` bookkeeping records), never as a `user` record. The shapes below are copied
# from real transcripts (CLI 2.1.282); the queue also carries task notifications, subagent
# hand-backs and coordinator messages, told apart by the same `origin.kind` a user record has.

def _queued(prompt, origin=None, **extra):
    attachment = dict({"type": "queued_command", "prompt": prompt,
                       "source_uuid": "55e23c39-7704-415f-b4a8-81cdba3ae6f3",
                       "timestamp": "2026-09-25T01:41:02.873Z"}, **extra)
    if origin is not None:
        attachment["origin"] = origin
    return {"type": "attachment", "attachment": attachment, "uuid": "4d91b542",
            "entrypoint": "cli"}


def _queued_human(prompt):
    return _queued(prompt, {"kind": "human"}, commandMode="prompt", humanTurn=True)


def _queue_op(op, content):
    return {"type": "queue-operation", "operation": op, "content": content,
            "timestamp": "2026-09-25T01:41:02.873Z"}


def test_a_prompt_typed_while_busy_is_human_text():
    assert T.human_text(_queued_human("use agent teams to keep main context free")) == \
        "use agent teams to keep main context free"


def test_a_queued_record_the_person_did_not_type_is_not_human_text():
    # Every non-human shape the queue was measured to carry.
    assert T.human_text(_queued("<task-notification>x</task-notification>", None,
                                commandMode="task-notification")) == ""
    assert T.human_text(_queued("<task-notification>y</task-notification>",
                                {"kind": "task-notification"},
                                commandMode="task-notification")) == ""
    assert T.human_text(_queued("<agent-message from=\"a1\">done</agent-message>",
                                {"kind": "peer", "from": "a1"}, commandMode="prompt")) == ""
    assert T.human_text(_queued("Your worktree was created at c77d0f1", {"kind": "coordinator"})) == ""
    # The bookkeeping records carry the same text and must never count a second time.
    assert T.human_text(_queue_op("enqueue", "go")) == ""
    assert T.human_text(_queue_op("remove", "go")) == ""


def test_a_queued_human_record_still_obeys_the_not_typed_registry():
    assert T.human_text(_queued_human("<bash-input>ls</bash-input>")) == ""


def test_a_queued_record_in_a_headless_sdk_run_is_not_human_text():
    record = _queued_human("summarise the repo")
    record["entrypoint"] = "sdk-py"
    assert T.human_text(record) == ""


def test_a_prompt_typed_while_busy_becomes_the_turns_prompt(tmp_path):
    # The real order: the prompt is queued mid-turn, after the assistant has already written.
    t = _write(tmp_path, [_user("fix the gate"), _asst("Running the suite now."),
                          _queue_op("enqueue", "no - stop, wrong repo"),
                          _queue_op("remove", "no - stop, wrong repo"),
                          _queued_human("no - stop, wrong repo"), _tool_use(), _tool_result(),
                          _asst("Stopped.")])
    turn = T.read_turn(t)
    assert turn.prompt == "no - stop, wrong repo"
    assert turn.reply_before_prompt == "Running the suite now."
    assert turn.reply == "Stopped."


def test_a_queued_notification_does_not_displace_the_typed_prompt(tmp_path):
    t = _write(tmp_path, [_asst("Ready."), _user("go"),
                          _queued("<task-notification>done</task-notification>",
                                  {"kind": "task-notification"}, commandMode="task-notification"),
                          _asst("Done.")])
    turn = T.read_turn(t)
    assert turn.prompt == "go" and turn.reply_before_prompt == "Ready."


# ---- scheduled prompts ------------------------------------------------------------------------
# A CronCreate or ScheduleWakeup fire reaches UserPromptSubmit as bare text, with the same payload
# keys as a typed prompt (probed on CLI 2.1.283), and its transcript record is written only AFTER
# the hook ran. The scheduling call is the one thing on disk in time: its `prompt` argument is the
# text that later arrives. The record shapes below are copied from that probe's transcript.

def _schedule(tool, prompt, **extra):
    return {"type": "assistant", "message": {"role": "assistant", "content": [
        {"type": "tool_use", "id": "toolu_01", "name": tool,
         "input": dict({"prompt": prompt}, **extra), "caller": {"type": "direct"}}]}}


def _fired(prompt):
    return {"type": "user", "message": {"content": prompt}, "isMeta": True,
            "promptSource": "system", "scheduledTaskId": "e4ce11db", "turnOrigin": "scheduled",
            "promptId": "2daa3028-7220-4fe1-ac39-2d8f3a323374", "entrypoint": "cli"}


CRON_TEXT = "probe95-cron-tick: reply with the single word OK"


def test_a_prompt_a_croncreate_call_scheduled_is_recognised(tmp_path):
    t = _write(tmp_path, [_user("schedule it"),
                          _schedule("CronCreate", CRON_TEXT, cron="43 13 28 09 *", recurring=False),
                          _asst("DONE")])
    assert T.scheduled_by_the_session(CRON_TEXT, t) is True


def test_a_prompt_a_schedulewakeup_call_scheduled_is_recognised(tmp_path):
    t = _write(tmp_path, [_schedule("ScheduleWakeup", "check the CI run", delaySeconds=600)])
    assert T.scheduled_by_the_session("check the CI run", t) is True


def test_surrounding_whitespace_does_not_hide_a_scheduled_prompt(tmp_path):
    t = _write(tmp_path, [_schedule("CronCreate", "  " + CRON_TEXT + "\n")])
    assert T.scheduled_by_the_session(CRON_TEXT + " ", t) is True


def test_a_typed_prompt_is_not_scheduled_even_when_it_quotes_the_scheduled_text(tmp_path):
    t = _write(tmp_path, [_schedule("CronCreate", CRON_TEXT)])
    assert T.scheduled_by_the_session("why did '%s' fire twice?" % CRON_TEXT, t) is False
    assert T.scheduled_by_the_session("schedule it", t) is False


def test_another_tools_prompt_argument_does_not_count(tmp_path):
    # Agent and Task carry a `prompt` too; a subagent brief is not a scheduled prompt.
    t = _write(tmp_path, [_schedule("Agent", CRON_TEXT)])
    assert T.scheduled_by_the_session(CRON_TEXT, t) is False


def test_no_transcript_or_no_scheduling_call_means_not_scheduled(tmp_path):
    assert T.scheduled_by_the_session(CRON_TEXT, str(tmp_path / "missing.jsonl")) is False
    assert T.scheduled_by_the_session(CRON_TEXT, "") is False
    assert T.scheduled_by_the_session(CRON_TEXT, None) is False
    t = _write(tmp_path, [_user("hello"), _asst("hi")])
    assert T.scheduled_by_the_session(CRON_TEXT, t) is False


def test_a_scheduling_call_early_in_a_long_transcript_is_still_found(tmp_path):
    # A cron fires long after it was created, so the call can sit far outside any turn tail.
    filler = [_asst("x" * 2000) for _ in range(200)]
    t = _write(tmp_path, [_schedule("CronCreate", CRON_TEXT)] + filler)
    assert T.scheduled_by_the_session(CRON_TEXT, t) is True


def test_is_scheduled_record_reads_the_record_the_harness_writes_afterwards():
    assert T.is_scheduled_record(_fired(CRON_TEXT)) is True
    assert T.is_scheduled_record(_user(CRON_TEXT)) is False
    meta = {"type": "user", "isMeta": True, "message": {"content": "Stop hook feedback: x"}}
    assert T.is_scheduled_record(meta) is False
    assert T.is_scheduled_record(None) is False


def test_scheduled_text_is_the_fired_prompt_and_empty_for_anything_else():
    assert T.scheduled_text(_fired(CRON_TEXT)) == CRON_TEXT
    assert T.scheduled_text(_user(CRON_TEXT)) == ""
    assert T.scheduled_text(None) == ""


# ---- slash commands -----------------------------------------------------------------------------
# A slash command is written as ONE user record holding three tags (CLI 2.1.283), with no `origin`
# key, and its output follows as a `<local-command-stdout>` record. The person typed the command
# and its arguments, and the prompt-time hooks receive them as `/name args`, so a command WITH
# arguments counts as typed, in exactly that form. A bare command carries no prose to judge.

def _command(name, args, legacy_order=False, **extra):
    tags = ["<command-name>/%s</command-name>" % name,
            "<command-message>%s</command-message>" % name]
    if legacy_order:
        tags.reverse()
    if args is not None:
        tags.append("<command-args>%s</command-args>" % args)
    record = {"type": "user", "entrypoint": "cli",
              "message": {"role": "user", "content": "\n            ".join(tags)}}
    record.update(extra)
    return record


def _stdout(text):
    return {"type": "user", "message": {"content": "<local-command-stdout>%s</local-command-stdout>"
                                                   % text}}


def test_a_slash_command_with_arguments_is_typed_as_the_hook_receives_it():
    assert T.human_text(_command("goal", "do A-F, use subagents")) == "/goal do A-F, use subagents"
    assert T.human_text(_command("plugin", "marketplace update bitranox-skills")) == \
        "/plugin marketplace update bitranox-skills"


def test_a_slash_command_keeps_its_arguments_verbatim_inside():
    text = T.human_text(_command("goal", ": fix  Still open\n  - [91] a b"))
    assert text == "/goal : fix  Still open\n  - [91] a b"


def test_a_slash_command_in_the_older_tag_order_is_read_the_same_way():
    assert T.human_text(_command("tfbpr", "patch", legacy_order=True)) == "/tfbpr patch"


def test_a_bare_slash_command_is_not_typed():
    assert T.human_text(_command("clear", "")) == ""
    assert T.human_text(_command("reload-plugins", "   ")) == ""
    assert T.human_text(_command("context", None)) == ""


def test_command_output_and_other_harness_command_records_stay_excluded():
    assert T.human_text(_stdout("Goal set: x")) == ""
    caveat = {"type": "user", "message": {"content": "<local-command-caveat>Caveat: x"
                                                     "</local-command-caveat>"}}
    assert T.human_text(caveat) == ""
    # A command record carrying anything besides its three tags is not this shape.
    odd = _command("goal", "x")
    odd["message"]["content"] += "\nmore text"
    assert T.human_text(odd) == ""


def test_a_slash_command_record_still_obeys_origin_meta_and_sdk():
    assert T.human_text(_command("goal", "x", isMeta=True)) == ""
    assert T.human_text(_command("goal", "x", origin={"kind": "task-notification"})) == ""
    assert T.human_text(_command("goal", "x", origin={"kind": "human"})) == "/goal x"
    assert T.human_text(_command("goal", "x", entrypoint="sdk-py")) == ""


def test_looks_typed_is_unchanged_for_the_raw_tag_form():
    # The prompt-time readers receive `/goal x`, never the tag form, and the tag form stays
    # not-typed there: only a transcript reader reconstructs the command.
    assert T.looks_typed(_command("goal", "x")["message"]["content"]) is False
    assert T.looks_typed("/goal x") is True


def test_a_slash_command_with_arguments_becomes_the_turns_prompt(tmp_path):
    t = _write(tmp_path, [_user("fix it"), _asst("Which part first?"),
                          _command("goal", "do 3-7"), _stdout("Goal set: do 3-7"),
                          _asst("Working on 3.")])
    turn = T.read_turn(t)
    assert turn.prompt == "/goal do 3-7"
    assert turn.reply_before_prompt == "Which part first?"
    assert turn.reply == "Working on 3."
