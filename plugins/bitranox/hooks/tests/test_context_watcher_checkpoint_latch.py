"""The context watcher's ask latch against the two records that broke it, end to end.

Two real misses share one outcome: the session saved its checkpoint, and after the compaction the
resume reported that no checkpoint was saved, because `checkpoint_asked_at` was stamped AFTER the
file's mtime and compact-resume rejects a checkpoint older than the request.

1. An API error. The harness logs a rate-limit or overload reply as an assistant record with
   model `<synthetic>`, `isApiErrorMessage` set and every usage field 0. Read as a measurement it
   says the session carries 0 tokens, which reads like a compaction, so the latch re-armed and the
   checkpoint's own Write asked again.
2. A first ask landing on the checkpoint's own Write. After a real compaction re-arms the latch,
   the first tool call past the save point can be the session writing handover.md on its own; the
   request then stamps the moment just after that write.

These tests drive the real hook scripts as subprocesses with the event shapes the harness sends
and a transcript built from the record shapes it writes; no internals are patched.
"""

import datetime
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path

import pytest

import context_watcher as W

HOOKS_DIR = Path(__file__).resolve().parent.parent
WATCHER = HOOKS_DIR / "context-watcher.py"
RESUME = HOOKS_DIR / "compact-resume.py"

OPUS = "claude-opus-5"
# Defaults on a 1M window: limit min(70%, 400,000) = 400,000, the harness aligned at that limit
# compacts 33,000 below it at 367,000, the save point sits 40,000 lower at 327,000, and a repeat
# request waits a tenth of the window, 100,000 more.
ASKED = 425_006
LATER = 427_710


@pytest.fixture
def env(tmp_path):
    """A subprocess environment whose state, config and project live under tmp_path."""
    cfg = tmp_path / "claude-config"
    cfg.mkdir()
    out = {k: v for k, v in os.environ.items()
           if not k.startswith("GIT_") and k not in ("CLAUDE_PROJECT_DIR", "VIRTUAL_ENV")}
    out.update({"CLAUDE_CONFIG_DIR": str(cfg), "HOME": str(tmp_path / "home"),
                "USERPROFILE": str(tmp_path / "home"),
                "CLAUDE_CODE_AUTO_COMPACT_WINDOW": "400000", "PYTHONUTF8": "1"})
    (tmp_path / "home").mkdir()
    return out


@pytest.fixture
def proj(tmp_path):
    p = tmp_path / "proj"
    p.mkdir()
    return p


def _now_iso():
    return datetime.datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z")


def _assistant(tokens, tool_id, tool, tool_input, model=OPUS):
    return {"type": "assistant", "timestamp": _now_iso(), "message": {
        "role": "assistant", "model": model,
        "content": [{"type": "tool_use", "id": tool_id, "name": tool, "input": tool_input}],
        "usage": {"input_tokens": 3, "cache_creation_input_tokens": 1000,
                  "cache_read_input_tokens": tokens - 1003, "output_tokens": 50}}}


def _result(tool_id):
    return {"type": "user", "timestamp": _now_iso(), "message": {"role": "user", "content": [
        {"type": "tool_result", "tool_use_id": tool_id, "content": "ok"}]}}


def _api_error():
    """The record shape the harness writes for a 429 reply (values invented, fields as logged)."""
    zero = {"input_tokens": 0, "output_tokens": 0, "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0}
    return {"type": "assistant", "timestamp": _now_iso(), "isApiErrorMessage": True,
            "apiErrorStatus": 429, "error": "rate_limit",
            "message": {"id": "msg-x", "role": "assistant", "model": "<synthetic>",
                        "type": "message", "stop_reason": "stop_sequence",
                        "content": [{"type": "text", "text": "API Error: rate limited"}],
                        "usage": zero}}


def _append(transcript, *records):
    with open(transcript, "a", encoding="utf-8") as fh:
        fh.writelines(json.dumps(record) + "\n" for record in records)


def _run(script, event, env):
    done = subprocess.run([sys.executable, str(script)], input=json.dumps(event), env=env,
                          capture_output=True, text=True, encoding="utf-8", timeout=60,
                          check=False)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout) if done.stdout.strip() else None


def _post_tool(session, transcript, proj, tool, tool_input, **extra):
    return dict({"hook_event_name": "PostToolUse", "session_id": session,
                 "transcript_path": str(transcript), "cwd": str(proj),
                 "tool_name": tool, "tool_input": tool_input}, **extra)


def _resume(session, transcript, proj, env):
    payload = _run(RESUME, {"hook_event_name": "SessionStart", "source": "compact",
                            "session_id": session, "transcript_path": str(transcript),
                            "cwd": str(proj)}, env)
    assert payload is not None
    return payload["hookSpecificOutput"]["additionalContext"]


def _asked_epoch(env, session):
    """checkpoint_asked_at as the hook wrote it, read from the isolated config dir."""
    script = (f"import sys; sys.path.insert(0, {str(HOOKS_DIR)!r}); "
              f"import self_improve_signals as s; print(s.checkpoint_asked_at({session!r}))")
    done = subprocess.run([sys.executable, "-c", script], env=env, capture_output=True,
                          text=True, encoding="utf-8", timeout=60, check=True)
    return float(done.stdout.strip())


def _write_checkpoint(path):
    path.write_text("# Handover\n\nIn flight: the latch fix.\n", encoding="utf-8")


def test_an_api_error_record_does_not_re_arm_the_request(tmp_path, env, proj):
    """Steps 1-6 of the measured miss: ask, API error, the checkpoint's Write, compaction."""
    session = "s-" + uuid.uuid4().hex[:8]
    transcript = tmp_path / "t.jsonl"
    _append(transcript, _assistant(ASKED, "t1", "Bash", {"command": "ls"}), _result("t1"))
    first = _run(WATCHER, _post_tool(session, transcript, proj, "Bash", {"command": "ls"}), env)
    assert first is not None and "425,006" in first["hookSpecificOutput"]["additionalContext"]

    # The error record is the newest usage record when the next tool call's hook runs: the
    # hook reads before the harness flushes that call's own assistant record.
    _append(transcript, _api_error())
    assert _run(WATCHER, _post_tool(session, transcript, proj, "Bash", {"command": "ls"}),
                env) is None
    # The latch still holds the first ask, so an ordinary call a little later stays quiet too.
    _append(transcript, _assistant(LATER, "t2", "Bash", {"command": "ls"}), _result("t2"))
    assert _run(WATCHER, _post_tool(session, transcript, proj, "Bash", {"command": "ls"}),
                env) is None, "a 0-token error record re-armed the request"

    handover = proj / "handover.md"
    write_input = {"file_path": str(handover), "content": "..."}
    _append(transcript, _assistant(LATER, "t3", "Write", write_input))
    _write_checkpoint(handover)
    time.sleep(0.01)
    _append(transcript, _result("t3"))
    second = _run(WATCHER, _post_tool(session, transcript, proj, "Write", write_input), env)
    context = _resume(session, transcript, proj, env)

    assert "no checkpoint was saved" not in context
    assert str(handover) in context
    assert second is None, "a 0-token error record re-armed the request"
    assert _asked_epoch(env, session) <= os.path.getmtime(handover)


def test_a_first_ask_landing_on_the_checkpoint_write_is_answered_by_it(tmp_path, env, proj):
    """The latch is clear (a compaction re-armed it) and the crossing call IS the handover Write."""
    session = "s-" + uuid.uuid4().hex[:8]
    transcript = tmp_path / "t.jsonl"
    handover = proj / "handover.md"
    write_input = {"file_path": str(handover), "content": "..."}
    _append(transcript, _assistant(ASKED, "t1", "Write", write_input))
    _write_checkpoint(handover)
    time.sleep(0.01)
    _append(transcript, _result("t1"))

    answer = _run(WATCHER, _post_tool(session, transcript, proj, "Write", write_input), env)
    context = _resume(session, transcript, proj, env)
    assert "no checkpoint was saved" not in context
    assert str(handover) in context
    assert answer is None
    assert 0 < _asked_epoch(env, session) <= os.path.getmtime(handover)

    # The write answered this crossing, so the next call at the same level stays quiet...
    _append(transcript, _assistant(ASKED + 500, "t2", "Bash", {"command": "ls"}), _result("t2"))
    assert _run(WATCHER, _post_tool(session, transcript, proj, "Bash", {"command": "ls"}),
                env) is None
    # ...and a tenth of the window later the request comes as usual.
    _append(transcript, _assistant(ASKED + 100_000, "t4", "Bash", {"command": "ls"}),
            _result("t4"))
    assert _run(WATCHER, _post_tool(session, transcript, proj, "Bash", {"command": "ls"}),
                env) is not None


@pytest.mark.parametrize("name", ["notes.md", "handover.txt", "handovers.md"])
def test_a_write_to_another_file_at_the_save_point_still_asks(tmp_path, env, proj, name):
    """Control: only a checkpoint-named write answers the request."""
    session = "s-" + uuid.uuid4().hex[:8]
    transcript = tmp_path / "t.jsonl"
    target = proj / name
    write_input = {"file_path": str(target), "content": "..."}
    _append(transcript, _assistant(ASKED, "t1", "Write", write_input), _result("t1"))
    target.write_text("x\n", encoding="utf-8")
    assert _run(WATCHER, _post_tool(session, transcript, proj, "Write", write_input),
                env) is not None


@pytest.mark.parametrize("name", ["handover.md", "release-handover.md", "handover-latch.md"])
def test_every_checkpoint_name_answers_the_request(tmp_path, env, proj, name):
    session = "s-" + uuid.uuid4().hex[:8]
    transcript = tmp_path / "t.jsonl"
    target = proj / name
    edit_input = {"file_path": str(target), "old_string": "a", "new_string": "b"}
    _append(transcript, _assistant(ASKED, "t1", "Edit", edit_input), _result("t1"))
    _write_checkpoint(target)
    assert _run(WATCHER, _post_tool(session, transcript, proj, "Edit", edit_input), env) is None
    assert 0 < _asked_epoch(env, session) <= os.path.getmtime(target)


def test_a_plan_mode_write_answers_the_request(tmp_path, env, proj):
    """In plan mode the plan file is the only writable file, and the request sends it there."""
    session = "s-" + uuid.uuid4().hex[:8]
    transcript = tmp_path / "t.jsonl"
    plan = tmp_path / "plans" / "a-plan.md"
    plan.parent.mkdir()
    write_input = {"file_path": str(plan), "content": "..."}
    _append(transcript, _assistant(ASKED, "t1", "Write", write_input), _result("t1"))
    plan.write_text("# Plan\n\n## Checkpoint\n", encoding="utf-8")
    event = _post_tool(session, transcript, proj, "Write", write_input, permission_mode="plan")
    assert _run(WATCHER, event, env) is None
    assert 0 < _asked_epoch(env, session) <= os.path.getmtime(plan)


def test_a_checkpoint_write_that_cannot_be_read_back_still_gets_the_request(tmp_path, env, proj):
    """No mtime means nothing to stamp against, so the ordinary request goes out."""
    session = "s-" + uuid.uuid4().hex[:8]
    transcript = tmp_path / "t.jsonl"
    write_input = {"file_path": str(proj / "gone" / "handover.md"), "content": "..."}
    _append(transcript, _assistant(ASKED, "t1", "Write", write_input), _result("t1"))
    assert _run(WATCHER, _post_tool(session, transcript, proj, "Write", write_input),
                env) is not None


@pytest.mark.parametrize(("event", "plan_mode", "expected"), [
    ({"hook_event_name": "Stop"}, False, None),
    ({"hook_event_name": "PostToolUse", "tool_name": "Bash",
      "tool_input": {"command": "cat > handover.md"}}, False, None),
    ({"hook_event_name": "PostToolUse", "tool_name": "Read",
      "tool_input": {"file_path": "/opt/p/handover.md"}}, False, None),
    ({"hook_event_name": "PostToolUse", "tool_name": "Write",
      "tool_input": {"file_path": "/opt/p/handover.md"}}, False, "/opt/p/handover.md"),
    ({"hook_event_name": "PostToolUse", "tool_name": "MultiEdit",
      "tool_input": {"file_path": "/opt/p/x-handover.md"}}, False, "/opt/p/x-handover.md"),
    ({"hook_event_name": "PostToolUse", "tool_name": "Write",
      "tool_input": {"file_path": "/opt/p/notes.md"}}, False, None),
    ({"hook_event_name": "PostToolUse", "tool_name": "Write",
      "tool_input": {"file_path": "/opt/plans/p.md"}}, True, "/opt/plans/p.md"),
    ({"hook_event_name": "PostToolUse", "tool_name": "Write", "tool_input": "junk"}, True, None),
    ({"hook_event_name": "PostToolUse", "tool_name": "Write",
      "tool_input": {"file_path": 7}}, True, None),
])
def test_checkpoint_write(event, plan_mode, expected):
    assert W.checkpoint_write(event, plan_mode=plan_mode) == expected


# ------------------------------------------------------------- the reading itself, PURE-ish


def _line(record):
    return json.dumps(record)


def _transcript(tmp_path, *records):
    f = tmp_path / f"t-{uuid.uuid4().hex[:8]}.jsonl"
    f.write_text("".join(_line(r) + "\n" for r in records), encoding="utf-8")
    return str(f)


def test_an_api_error_record_is_not_a_reading(tmp_path):
    t = _transcript(tmp_path, _assistant(ASKED, "t1", "Bash", {}), _api_error())
    assert W.read_session(t) == (ASKED, OPUS)
    assert W.context_tokens(t) == ASKED


def test_a_synthetic_record_with_usage_is_not_a_reading_and_not_the_model(tmp_path):
    """Neither flag is required alone: a `<synthetic>` model never names the window."""
    synthetic = _assistant(5_000, "t2", "Bash", {}, model="<synthetic>")
    t = _transcript(tmp_path, _assistant(ASKED, "t1", "Bash", {}), synthetic)
    assert W.read_session(t) == (ASKED, OPUS)
    assert W.context_tokens(t) == ASKED


def test_an_error_flagged_record_with_a_real_model_is_not_a_reading(tmp_path):
    flagged = dict(_assistant(5_000, "t2", "Bash", {}), isApiErrorMessage=True)
    t = _transcript(tmp_path, _assistant(ASKED, "t1", "Bash", {}), flagged)
    assert W.read_session(t) == (ASKED, OPUS)
    assert W.context_tokens(t) == ASKED


def test_a_zero_usage_record_is_not_a_reading(tmp_path):
    """A request always carries its system prompt, so a 0 total is no measurement (real ids too)."""
    zero = _assistant(ASKED, "t2", "Bash", {}, model="claude-opus-5-5")
    zero["message"]["usage"] = {"input_tokens": 0, "cache_creation_input_tokens": 0,
                                "cache_read_input_tokens": 0, "output_tokens": 0}
    t = _transcript(tmp_path, _assistant(ASKED, "t1", "Bash", {}), zero)
    assert W.read_session(t) == (ASKED, OPUS)
    assert W.context_tokens(t) == ASKED


def test_only_error_records_read_as_unknown_not_zero(tmp_path):
    t = _transcript(tmp_path, _api_error(), _api_error())
    assert W.read_session(t) == (None, None)
    assert W.context_tokens(t) is None


def test_a_real_compaction_still_re_arms_the_request(tmp_path, env, proj):
    """A low real reading after an ask is the compaction the latch exists to notice."""
    session = "s-" + uuid.uuid4().hex[:8]
    transcript = tmp_path / "t.jsonl"
    _append(transcript, _assistant(ASKED, "t1", "Bash", {}), _result("t1"))
    assert _run(WATCHER, _post_tool(session, transcript, proj, "Bash", {}), env) is not None
    _append(transcript, _assistant(40_000, "t2", "Bash", {}), _result("t2"))
    assert _run(WATCHER, _post_tool(session, transcript, proj, "Bash", {}), env) is None
    _append(transcript, _assistant(ASKED + 1_000, "t3", "Bash", {}), _result("t3"))
    assert _run(WATCHER, _post_tool(session, transcript, proj, "Bash", {}), env) is not None
