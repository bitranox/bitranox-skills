"""forgotten-backstop-nudge: name the deadline shells whose guarded tasks have all reported.

Transcripts are built from the record shapes Claude Code writes: an assistant tool_use, the user
tool_result that answers it, and a queue-operation enqueue carrying a <task-notification>.
"""
import io
import json

import pytest

import forgotten_backstop_nudge as F


class Transcript:
    def __init__(self):
        self.lines = []
        self._n = 0

    def _id(self):
        self._n += 1
        return "toolu_%04d" % self._n

    def _use(self, name, tool_input, message_id=None):
        tid = self._id()
        self.lines.append(json.dumps({"type": "assistant", "message": {
            "id": message_id or ("msg_" + tid),
            "content": [{"type": "tool_use", "id": tid, "name": name, "input": tool_input}]}}))
        return tid

    def _result(self, tid, text):
        self.lines.append(json.dumps({"type": "user", "message": {
            "content": [{"type": "tool_result", "tool_use_id": tid,
                         "content": [{"type": "text", "text": text}]}]}}))

    def agent(self, message_id=None, answer=True, name=None):
        tool_input = {"prompt": "do it", "description": "x"}
        if name:
            tool_input["name"] = name
        tid = self._use("Agent", tool_input, message_id)
        if answer:
            self._result(tid, "Async agent launched successfully.\nagentId: a%s (internal ID - "
                              "Use SendMessage with to: 'a%s' to continue this agent" % (tid[-4:], tid[-4:]))
        return tid

    def send(self, to):
        tid = self._use("SendMessage", {"to": to, "summary": "s", "message": "go on"})
        self._result(tid, "message delivered")
        return tid

    def background(self, command, shell_id, message_id=None):
        tid = self._use("Bash", {"command": command, "run_in_background": True}, message_id)
        self._result(tid, "Command running in background with ID: %s. Output is being written to: "
                          "/tmp/x/%s.output" % (shell_id, shell_id))
        return tid

    def foreground_agent(self):
        tid = self._use("Agent", {"prompt": "do it", "description": "x"})
        self._result(tid, "the agent's full report")
        return tid

    def notify(self, task_id, tool_use_id, status="completed", summary="Agent \"x\" finished"):
        self.lines.append(json.dumps({"type": "queue-operation", "operation": "enqueue",
                                      "content": notification(task_id, tool_use_id, status, summary)}))

    def stop(self, shell_id, name="TaskStop"):
        tid = self._use(name, {"task_id": shell_id} if name == "TaskStop" else {"shell_id": shell_id})
        self._result(tid, "stopped")


def notification(task_id, tool_use_id, status="completed", summary="Agent \"x\" finished"):
    return ("<task-notification>\n<task-id>%s</task-id>\n<tool-use-id>%s</tool-use-id>\n"
            "<output-file>/tmp/x/%s.output</output-file>\n<status>%s</status>\n"
            "<summary>%s</summary>\n</task-notification>" % (task_id, tool_use_id, task_id, status,
                                                            summary))


DEADLINE = 'sleep 1800; echo "BACKSTOP: review agents due"'


def test_a_deadline_whose_agents_all_reported_is_forgotten():
    t = Transcript()
    a1, a2 = t.agent(), t.agent()
    t.background(DEADLINE, "bdead1")
    t.notify("x1", a1)
    t.notify("x2", a2)
    assert F.forgotten_backstops(t.lines) == [("bdead1", DEADLINE)]


def test_a_deadline_with_an_agent_still_out_is_doing_its_job():
    t = Transcript()
    a1, _a2 = t.agent(), t.agent()
    t.background(DEADLINE, "bdead1")
    t.notify("x1", a1)
    assert F.forgotten_backstops(t.lines) == []


def test_the_notification_being_delivered_now_counts_as_reported():
    # The hook runs on the notification's own prompt; the enqueue record may not be on disk yet.
    t = Transcript()
    a1 = t.agent()
    t.background(DEADLINE, "bdead1")
    assert F.forgotten_backstops(t.lines) == []
    assert F.forgotten_backstops(t.lines, notification("x1", a1)) == [("bdead1", DEADLINE)]


@pytest.mark.parametrize("by", ["agent id", "name"])
def test_an_agent_resumed_with_sendmessage_is_outstanding_again(by):
    t = Transcript()
    a1 = t.agent(name="reviewer")
    t.background(DEADLINE, "bdead1")
    t.notify("a" + a1[-4:], a1)
    resumed = t.send("a" + a1[-4:] if by == "agent id" else "reviewer")
    assert F.forgotten_backstops(t.lines) == []
    # A resumed agent reports under its agent id and the SendMessage call's tool-use id.
    t.notify("a" + a1[-4:], resumed)
    assert F.forgotten_backstops(t.lines) == [("bdead1", DEADLINE)]


def test_a_sendmessage_to_a_peer_session_resumes_nothing():
    t = Transcript()
    a1 = t.agent()
    t.background(DEADLINE, "bdead1")
    t.notify("x1", a1)
    t.send("uds:/run/user/1000/cc-socks/1.sock")
    assert F.forgotten_backstops(t.lines) == [("bdead1", DEADLINE)]


def test_a_deadline_armed_with_nothing_outstanding_is_never_judged():
    # It may guard a CI run or a remote job, which no record here shows.
    t = Transcript()
    t.background("sleep 900; echo release-run backstop", "bdead1")
    assert F.forgotten_backstops(t.lines) == []


def test_agents_dispatched_in_the_same_message_after_the_deadline_belong_to_it():
    t = Transcript()
    t.background(DEADLINE, "bdead1", message_id="msg_batch")
    a1 = t.agent(message_id="msg_batch")
    assert F.forgotten_backstops(t.lines) == []
    t.notify("x1", a1)
    assert F.forgotten_backstops(t.lines) == [("bdead1", DEADLINE)]


def test_an_agent_launched_after_the_deadline_in_a_later_message_is_not_its_task():
    t = Transcript()
    a1 = t.agent()
    t.background(DEADLINE, "bdead1")
    t.agent()                       # a new dispatch, not what the deadline was armed for
    t.notify("x1", a1)
    assert F.forgotten_backstops(t.lines) == [("bdead1", DEADLINE)]


def test_a_deadline_that_already_fired_or_was_stopped_is_not_listed():
    for end in ("fired", "TaskStop", "KillShell"):
        t = Transcript()
        a1 = t.agent()
        t.background(DEADLINE, "bdead1")
        t.notify("x1", a1)
        if end == "fired":
            t.notify("bdead1", "toolu_9999", summary="Background command \"sleep\" completed")
        else:
            t.stop("bdead1", end)
        assert F.forgotten_backstops(t.lines) == [], end


def test_a_background_job_outstanding_at_arming_is_guarded_too():
    t = Transcript()
    t.background("make test > /tmp/x/log 2>&1", "bjob1")
    t.background(DEADLINE, "bdead1")
    assert F.forgotten_backstops(t.lines) == []
    t.notify("bjob1", "toolu_0001", summary="Background command \"make test\" completed")
    assert F.forgotten_backstops(t.lines) == [("bdead1", DEADLINE)]


def test_a_foreground_agent_is_never_outstanding():
    t = Transcript()
    t.foreground_agent()
    t.background(DEADLINE, "bdead1")
    assert F.forgotten_backstops(t.lines) == []      # nothing was outstanding when it was armed


@pytest.mark.parametrize("command", [
    "sleep 600",
    "sleep 10m; echo DEADLINE",
    "sleep 720 && echo 'delta review backstop: 12 min passed'",
    "S=/tmp/x; sleep 900; echo done",
])
def test_pure_deadline_shapes(command):
    assert F.is_pure_deadline(command)


@pytest.mark.parametrize("command", [
    "until test -f /tmp/x/done; do sleep 10; done; echo ready",
    "sleep 5; make test",
    "tail -F /tmp/x/log | grep -m1 DONE",
    "sleep 600; rm -rf /tmp/x/scratch",
    "python3 backstop.py --deadline 600",
])
def test_not_pure_deadline_shapes(command):
    assert not F.is_pure_deadline(command)


def _run(monkeypatch, tmp_path, transcript, prompt, session="sid-1"):
    path = tmp_path / "t.jsonl"
    path.write_text("\n".join(transcript.lines) + "\n", encoding="utf-8")
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    event = {"hook_event_name": "UserPromptSubmit", "prompt": prompt, "session_id": session,
             "transcript_path": str(path), "cwd": str(tmp_path)}
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(event)))
    out = io.StringIO()
    monkeypatch.setattr("sys.stdout", out)
    assert F.main() == 0
    text = out.getvalue().strip()
    return json.loads(text)["hookSpecificOutput"]["additionalContext"] if text else ""


def test_main_names_the_shell_and_the_stop_call_once(monkeypatch, tmp_path):
    t = Transcript()
    a1 = t.agent()
    t.background(DEADLINE, "bdead1")
    note = notification("x1", a1)
    first = _run(monkeypatch, tmp_path, t, note)
    assert "bdead1" in first and 'TaskStop(task_id="bdead1")' in first and "sleep 1800" in first
    assert _run(monkeypatch, tmp_path, t, note) == ""          # said once per shell per session


def test_main_is_silent_on_a_typed_prompt(monkeypatch, tmp_path):
    t = Transcript()
    a1 = t.agent()
    t.background(DEADLINE, "bdead1")
    t.notify("x1", a1)
    assert _run(monkeypatch, tmp_path, t, "please continue") == ""


def test_main_fails_open_on_a_missing_transcript(monkeypatch, tmp_path):
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({
        "prompt": notification("x", "toolu_1"), "session_id": "s",
        "transcript_path": str(tmp_path / "missing.jsonl")})))
    out = io.StringIO()
    monkeypatch.setattr("sys.stdout", out)
    assert F.main() == 0 and out.getvalue() == ""
