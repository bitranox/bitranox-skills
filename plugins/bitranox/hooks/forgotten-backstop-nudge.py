#!/usr/bin/env python3
"""UserPromptSubmit nudge: when a task notification arrives, name the deadline backstops it orphaned.

A backstop for subagents is a `run_in_background` shell that is nothing but a sleep (`sleep 1800;
echo DEADLINE`). Once every task it was armed for has reported it guards nothing, and if nobody
stops it, it fires much later as a "deadline reached" notification that reads like news. Measured
over a local transcript corpus: of 866 such shells, 440 were stopped and 399 ran to their deadline,
262 of those after every task outstanding when they were armed had already reported.

The moment that matters is the notification that collects the LAST of those tasks, and that
notification is delivered as a prompt, so this runs on UserPromptSubmit and only for a prompt that
is a `<task-notification>`. It replays the transcript in order:

- a pure deadline shell (`is_pure_deadline`) armed while tasks were outstanding records those
  tasks: every async Agent/Task/Workflow launch and every other background shell not yet reported,
  plus any launched in the same assistant message, which is how a batch and its backstop are
  usually dispatched together;
- a notification reports its task (matched by task id and by tool-use id), and the one being
  delivered now counts although its queue record may not be on disk yet;
- a shell is finished once its own notification arrives or a TaskStop/KillShell names it.

A shell armed with nothing outstanding is never judged: it may guard a CI run or a remote job no
record here shows. A SendMessage to an agent that already reported (by its agentId or its name)
makes it outstanding again, so a backstop still guarding the resumed run is not named; a resume
sent only after the nudge fired is outside what it could see, so the text says to keep one that
still guards something.

Each shell is named once per session. NON-BLOCKING: additionalContext only, exits 0, fail-open on
any error. ASCII only.
"""

import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass

from self_improve_signals import session_state_path

__all__ = ["forgotten_backstops", "is_pure_deadline", "main"]

_ASYNC_TOOLS = frozenset({"Agent", "Task", "Workflow"})
_STOP_TOOLS = frozenset({"TaskStop", "KillShell"})
_NOTIFICATION = "<task-notification"

# Leading literal assignments, one sleep, then at most an echo/printf of what fired.
_PURE_DEADLINE = re.compile(
    r"^\s*(?:[A-Za-z_][A-Za-z0-9_]*=\S*\s*;\s*)*sleep\s+\d+(?:\.\d+)?[smhd]?"
    r"\s*(?:(?:;|&&)\s*(?:echo|printf)\b[^;&|<>`$()]*)?\s*;?\s*$")
_SHELL_ID = re.compile(r"running in background with ID: ([A-Za-z0-9_-]+)")
_AGENT_ID = re.compile(r"agentId: ([A-Za-z0-9_-]+)")
_ELEMENT = re.compile(r"<(task-id|tool-use-id)>\s*([^<\s]+)\s*</\1>")
_BLOCK = re.compile(r"<task-notification>(.*?)</task-notification>", re.S)


def is_pure_deadline(command):
    """True when a background command does nothing but sleep and then say so."""
    return bool(command) and _PURE_DEADLINE.match(command) is not None


def _reported_ids(text):
    """Every task id and tool-use id the notifications in `text` report."""
    ids = set()
    for block in _BLOCK.findall(text or ""):
        ids |= {value for _name, value in _ELEMENT.findall(block)}
    return ids


def _result_text(block):
    content = block.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(str(part.get("text") or "") for part in content if isinstance(part, dict))
    return ""


class _Replay:
    """Outstanding tasks and live deadline shells, advanced one transcript record at a time."""

    def __init__(self):
        self.launches = {}       # tool_use_id -> (tool name, command, message id)
        self.outstanding = {}    # task key -> message id of its launch
        self.deadlines = {}      # shell id -> [command, {task keys it guards}]
        self.finished = set()    # every id reported or stopped
        self.aliases = {}        # agent id or name -> tool_use_id of its launch, for SendMessage

    def report(self, ids):
        # A resumed agent reports under its agent id and the SendMessage call's tool-use id, never
        # the launch's, so the agent id is mapped back to the launch it is outstanding under.
        ids = set(ids) | {self.aliases[key] for key in ids if key in self.aliases}
        self.finished |= ids
        for key in ids:
            self.outstanding.pop(key, None)

    def record(self, record):
        if record.get("type") == "queue-operation":
            if record.get("operation") == "enqueue":
                self.report(_reported_ids(str(record.get("content") or "")))
            return
        message = record.get("message") or {}
        content = message.get("content")
        if isinstance(content, str):
            self.report(_reported_ids(content))
            return
        for block in content if isinstance(content, list) else ():
            if isinstance(block, dict):
                self._block(block, str(message.get("id") or ""))

    def _block(self, block, message_id):
        if block.get("type") == "tool_use":
            name, tool_input = block.get("name"), block.get("input") or {}
            if name in _STOP_TOOLS:
                self.report({str(tool_input.get("task_id") or tool_input.get("shell_id") or "")})
            elif name == "SendMessage":
                self._resume(self.aliases.get(str(tool_input.get("to") or "")), message_id)
            elif name in _ASYNC_TOOLS or (name == "Bash" and tool_input.get("run_in_background")):
                self.launches[str(block.get("id"))] = (name, str(tool_input.get("command") or ""),
                                                       message_id)
                if tool_input.get("name"):
                    self.aliases[str(tool_input["name"])] = str(block.get("id"))
        elif block.get("type") == "tool_result":
            launch = self.launches.pop(str(block.get("tool_use_id")), None)
            if launch:
                self._launched(str(block.get("tool_use_id")), launch, _result_text(block))

    def _launched(self, tool_use_id, launch, text):
        name, command, message_id = launch
        if name != "Bash":
            if "launched" in text.lower():         # an async launch; a foreground one returned
                found = _AGENT_ID.search(text)
                if found:
                    self.aliases[found.group(1)] = tool_use_id
                self._resume(tool_use_id, message_id)
            return
        found = _SHELL_ID.search(text)
        if not found:
            return
        shell = found.group(1)
        if is_pure_deadline(command):
            self.deadlines[shell] = [command, set(self.outstanding), message_id]
        else:
            self.outstanding[shell] = message_id
            for guarded in self._armed_in(message_id):
                guarded.add(shell)

    def _resume(self, key, message_id):
        """Mark `key` running: launched now, or an agent SendMessage woke after it reported."""
        if not key:
            return
        self.outstanding[key] = message_id
        for guarded in self._armed_in(message_id):
            guarded.add(key)

    def _armed_in(self, message_id):
        return [entry[1] for entry in self.deadlines.values() if message_id and entry[2] == message_id]

    def forgotten(self):
        return [(shell, entry[0]) for shell, entry in self.deadlines.items()
                if shell not in self.finished and entry[1]
                and not any(key in self.outstanding for key in entry[1])]


def _feed(replay, line):
    """Advance `replay` by one transcript line; a line naming none of the record kinds is skipped."""
    if not any(mark in line for mark in ("tool_use", "tool_result", "task-notification")):
        return
    try:
        record = json.loads(line)
    except ValueError:
        return
    if isinstance(record, dict):
        replay.record(record)


def forgotten_backstops(lines, delivering=""):
    """[(shell id, command)] of live deadline shells whose guarded tasks have all reported.

    `lines` are transcript JSONL lines in file order; `delivering` is the notification prompt being
    delivered now, whose tasks count as reported."""
    replay = _Replay()
    for line in lines:
        _feed(replay, line)
    replay.report(_reported_ids(delivering))
    return replay.forgotten()


# ---- resuming the replay where the previous notification left it --------------------------------
#
# A notification arrives throughout a session while its transcript keeps growing, so replaying
# from byte 0 each time made the session's total cost notifications x transcript size: measured
# 367 ms per notification on a 147 MB transcript with 158 notifications in it. The replay state and
# the byte offset it reached are kept per session instead, and the next notification reads only
# what was appended. The offset is trusted only while the file still holds the same bytes in front
# of it (a digest of the last _TAIL bytes); a shorter file, another path or unreadable state means
# a full replay, which is always correct.

_RESUME_SUFFIX = ".forgotten-backstops-replay.json"
_TAIL = 64


def _string(value):
    if not isinstance(value, str):
        raise ValueError("not a string")
    return value


def _strings(value, length=None):
    if not isinstance(value, list) or (length is not None and len(value) != length):
        raise ValueError("not a list of the expected length")
    return [_string(x) for x in value]


def _object(raw, key):
    value = raw.get(key)
    if not isinstance(value, dict):
        raise ValueError(key + " is not an object")
    return {_string(k): v for k, v in value.items()}


def _replay_to_json(replay):
    return {"launches": {k: list(v) for k, v in replay.launches.items()},
            "outstanding": dict(replay.outstanding),
            "deadlines": {k: [v[0], sorted(v[1]), v[2]] for k, v in replay.deadlines.items()},
            "finished": sorted(replay.finished), "aliases": dict(replay.aliases)}


def _replay_from_json(raw):
    """The _Replay `_replay_to_json` wrote. Raises ValueError on any field of the wrong shape."""
    if not isinstance(raw, dict):
        raise ValueError("replay state is not an object")
    replay = _Replay()
    replay.launches = {k: tuple(_strings(v, 3)) for k, v in _object(raw, "launches").items()}
    replay.outstanding = {k: _string(v) for k, v in _object(raw, "outstanding").items()}
    for shell, entry in _object(raw, "deadlines").items():
        if not isinstance(entry, list) or len(entry) != 3:
            raise ValueError("a deadline is not [command, guarded, message id]")
        replay.deadlines[shell] = [_string(entry[0]), set(_strings(entry[1])), _string(entry[2])]
    replay.finished = set(_strings(raw.get("finished")))
    replay.aliases = {k: _string(v) for k, v in _object(raw, "aliases").items()}
    return replay


@dataclass(frozen=True)
class _ResumePoint:
    """Where the last replay of `path` stopped, and the replay state it had reached there."""

    path: str
    offset: int
    tail: str              # sha256 hex of the _TAIL bytes in front of `offset`
    replay: _Replay        # the state reached at `offset`


def _parse_resume(raw):
    """The _ResumePoint a decoded state file holds. Raises ValueError on any field of the wrong shape."""
    if not isinstance(raw, dict):
        raise ValueError("resume state is not an object")
    offset = raw.get("offset")
    if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
        raise ValueError("offset is not a byte count")
    return _ResumePoint(path=_string(raw.get("path")), offset=offset,
                        tail=_string(raw.get("tail")), replay=_replay_from_json(raw.get("replay")))


def _load_resume(session):
    try:
        with open(session_state_path(session, _RESUME_SUFFIX), encoding="utf-8") as fh:
            return _parse_resume(json.load(fh))
    except (OSError, ValueError):
        return None


def _save_resume(session, point):
    path = session_state_path(session, _RESUME_SUFFIX)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        staged = path.with_name(path.name + ".tmp")
        staged.write_text(json.dumps({"path": point.path, "offset": point.offset,
                                      "tail": point.tail, "replay": _replay_to_json(point.replay)}),
                          encoding="utf-8")
        os.replace(staged, path)                   # a reader never sees half a state file
    except OSError:
        pass


def _tail_digest(fh, offset):
    fh.seek(max(0, offset - _TAIL))
    return hashlib.sha256(fh.read(min(offset, _TAIL))).hexdigest()


def _replay_transcript(transcript, session):
    """The replay of `transcript` up to its last complete line, resumed from the saved point.

    Only complete lines are consumed: a transcript can be mid-write when this reads it, and a
    half-written last line is left for the next notification, which will see it whole.
    """
    point = _load_resume(session) if session else None
    with open(transcript, "rb") as fh:
        size = os.fstat(fh.fileno()).st_size
        replay, offset = _Replay(), 0
        if (point is not None and point.path == transcript and point.offset <= size
                and _tail_digest(fh, point.offset) == point.tail):
            replay, offset = point.replay, point.offset
        fh.seek(offset)
        for raw in fh:
            if not raw.endswith(b"\n"):
                break
            offset += len(raw)
            _feed(replay, raw.decode("utf-8", errors="replace"))
        tail = _tail_digest(fh, offset)
    if session:
        _save_resume(session, _ResumePoint(path=transcript, offset=offset, tail=tail, replay=replay))
    return replay


def _notice(shells):
    calls = "\n".join('    TaskStop(task_id="%s")   # %s' % (shell, command[:120])
                      for shell, command in shells)
    return ("FORGOTTEN BACKSTOP: every task these run_in_background deadline shells were armed for "
            "has now reported, yet they are still running. Each will fire later as a stale "
            "'deadline reached' notification that reads like news. Stop them now, unless one still "
            "guards something this transcript cannot show (a CI run, a remote job, an agent you "
            "resumed):\n" + calls)


def _already_named(session):
    try:
        with open(session_state_path(session, ".forgotten-backstops.json"), encoding="utf-8") as fh:
            named = json.load(fh)
        return set(named) if isinstance(named, list) else set()
    except (OSError, ValueError):
        return set()


def _remember(session, ids):
    path = session_state_path(session, ".forgotten-backstops.json")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(sorted(ids)), encoding="utf-8")
    except OSError:
        pass


def main():
    try:
        event = json.load(sys.stdin)
    except Exception:  # noqa: BLE001 - no/invalid stdin: do nothing
        return 0
    if not isinstance(event, dict):
        return 0
    prompt = str(event.get("prompt") or "")
    if not prompt.lstrip().startswith(_NOTIFICATION):
        return 0
    session = str(event.get("session_id") or "")
    try:
        replay = _replay_transcript(str(event.get("transcript_path") or ""), session)
    except OSError:
        return 0
    # Reported AFTER the state was saved: the notification being delivered may not be on disk yet,
    # and once it is, the next replay reads its record like any other.
    replay.report(_reported_ids(prompt))
    shells = replay.forgotten()
    named = _already_named(session)
    fresh = [(shell, command) for shell, command in shells if shell not in named]
    if not fresh:
        return 0
    _remember(session, named | {shell for shell, _command in fresh})
    sys.stdout.write(json.dumps({"hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit", "additionalContext": _notice(fresh)}}) + "\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - a broken hook must never wedge a turn
        sys.exit(0)
