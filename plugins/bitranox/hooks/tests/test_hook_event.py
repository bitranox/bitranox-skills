"""Tests for hook_event.py - the typed, narrowed views of a hook's stdin event."""
import doctest
import json

import pytest

import hook_event as H


def test_doctests_pass():
    result = doctest.testmod(H)
    assert result.attempted > 0 and result.failed == 0


def test_a_real_pre_tool_use_event_keeps_every_read_field():
    raw = json.loads(json.dumps({
        "hook_event_name": "PreToolUse", "session_id": "s1", "transcript_path": "/tmp/t.jsonl",
        "cwd": "/opt/proj", "permission_mode": "default", "agent_id": "a1", "agent_type": "x",
        "tool_name": "Bash", "tool_use_id": "toolu_1",
        "tool_input": {"command": "ls", "description": "list", "run_in_background": True},
    }))
    assert H.parse_pre_tool_use(raw) == raw


def test_an_edit_input_keeps_its_strings_and_edits():
    tool_input = {"file_path": "/opt/a.py", "old_string": "a", "new_string": "b",
                  "replace_all": False, "content": "c", "notebook_path": "/opt/n.ipynb",
                  "new_source": "src", "prompt": "p", "name": "n", "to": "t", "task_id": "k",
                  "shell_id": "h", "edits": [{"old_string": "x", "new_string": "y",
                                              "replace_all": True}]}
    assert H.parse_tool_input(tool_input) == tool_input


@pytest.mark.parametrize("key", ["hook_event_name", "session_id", "transcript_path", "cwd",
                                 "permission_mode", "agent_id", "agent_type", "tool_name",
                                 "tool_use_id"])
@pytest.mark.parametrize("wrong", [7, None, ["a"], {"a": 1}, True])
def test_a_wrong_typed_event_field_reads_as_absent(key, wrong):
    assert key not in H.parse_pre_tool_use({key: wrong, "cwd": "/opt"} if key != "cwd" else {key: wrong})


@pytest.mark.parametrize("wrong", [7, "ls", ["ls"], None])
def test_a_tool_input_that_is_not_an_object_reads_as_absent(wrong):
    assert H.parse_pre_tool_use({"tool_name": "Bash", "tool_input": wrong}) == {"tool_name": "Bash"}


def test_a_wrong_typed_tool_input_field_reads_as_absent():
    parsed = H.parse_tool_input({"command": ["ls"], "run_in_background": "true",
                                 "file_path": 3, "edits": "not a list", "replace_all": 1})
    assert parsed == {}


def test_non_object_edit_elements_are_dropped_and_each_element_is_narrowed():
    parsed = H.parse_tool_input({"edits": [1, "x", None, {"old_string": 2, "new_string": "b"}]})
    assert parsed == {"edits": [{"new_string": "b"}]}


def test_undeclared_fields_are_not_copied():
    assert H.parse_pre_tool_use({"tool_name": "Bash", "surprise": "x"}) == {"tool_name": "Bash"}
    assert H.parse_tool_input({"command": "ls", "timeout": 5}) == {"command": "ls"}


@pytest.mark.parametrize("parse", [H.parse_pre_tool_use, H.parse_post_tool_use, H.parse_stop,
                                   H.parse_user_prompt_submit, H.parse_tool_input])
@pytest.mark.parametrize("raw", [None, 0, "text", [], ["a"], 1.5])
def test_a_payload_that_is_not_an_object_parses_to_none(parse, raw):
    assert parse(raw) is None


def test_post_tool_use_narrows_the_response():
    raw = {"tool_name": "Bash", "tool_input": {"command": "grep -r x ."},
           "tool_response": {"stdout": "", "stderr": "e", "interrupted": False,
                             "backgroundTaskId": "b1", "extra": 1}}
    assert H.parse_post_tool_use(raw) == {
        "tool_name": "Bash", "tool_input": {"command": "grep -r x ."},
        "tool_response": {"stdout": "", "stderr": "e", "interrupted": False,
                          "backgroundTaskId": "b1"}}


def test_a_plain_text_tool_response_reads_as_absent():
    assert "tool_response" not in H.parse_post_tool_use({"tool_response": "done"})
    assert H.parse_post_tool_use({"tool_response": {"stdout": 5}}) == {"tool_response": {}}


def test_stop_reads_its_flag_and_last_message():
    raw = {"session_id": "s", "stop_hook_active": False, "last_assistant_message": "bye"}
    assert H.parse_stop(raw) == raw
    assert H.parse_stop({"stop_hook_active": 1, "last_assistant_message": ["x"]}) == {}


def test_user_prompt_submit_reads_the_prompt():
    raw = {"session_id": "s", "transcript_path": "/tmp/t", "prompt": "hi"}
    assert H.parse_user_prompt_submit(raw) == raw
    assert H.parse_user_prompt_submit({"prompt": 3}) == {}


def test_the_parsed_event_is_a_new_dict_not_the_input():
    raw = {"tool_name": "Bash", "tool_input": {"command": "ls"}}
    parsed = H.parse_pre_tool_use(raw)
    assert parsed is not raw and parsed["tool_input"] is not raw["tool_input"]
