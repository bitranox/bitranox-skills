"""mod_bridge: driven as the mod drives it - a real subprocess, JSON on stdin. ASCII only."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

BRIDGE = Path(__file__).resolve().parents[1] / "mod_bridge.py"


@pytest.fixture
def env(tmp_path):
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    return {**{k: v for k, v in os.environ.items() if not k.startswith("GIT_")},
            "HOME": str(home), "USERPROFILE": str(home)}


@pytest.fixture
def repo(tmp_path, env):
    r = tmp_path / "repo"
    r.mkdir()
    subprocess.run(["git", "init", "-q", str(r)], check=True, env=env)
    return r


def run(cwd, env, data):
    return subprocess.run([sys.executable, str(BRIDGE)], input=data, capture_output=True,
                          cwd=cwd, env=env)


def call(cwd, env, tool, payload=None, raw=None):
    data = raw if raw is not None else json.dumps({"tool": tool, "input": payload or {}})
    p = run(cwd, env, data.encode("utf-8"))
    return p.returncode, json.loads(p.stdout.decode("ascii"))


ITEM = {"rank": 20, "origin": "USER", "what": "w", "size": "1", "open": "o", "next": "n"}
FACT = {"title": "T", "hook": "When x, y.", "body": "b"}


def test_backlog_add_then_list(repo, env):
    rc, out = call(repo, env, "backlog_add", ITEM)
    assert (rc, out["ok"], out["data"]["rank"]) == (0, True, 20)
    rc, out = call(repo, env, "backlog_list")
    assert rc == 0 and [it["rank"] for it in out["data"]["items"]] == [20]
    assert (repo / "OPEN-WORK.md").is_file()


def test_a_taken_rank_is_a_refusal_with_its_kind(repo, env):
    call(repo, env, "backlog_add", ITEM)
    rc, out = call(repo, env, "backlog_add", ITEM)
    assert (rc, out["ok"], out["error"]["kind"]) == (1, False, "RankTaken")


def test_backlog_close(repo, env):
    call(repo, env, "backlog_add", ITEM)
    rc, out = call(repo, env, "backlog_close", {"rank": 20, "reason": "done"})
    assert rc == 0 and out["data"]["line"].endswith("| closed: done")


def test_list_without_a_backlog_says_so(repo, env):
    rc, out = call(repo, env, "backlog_list")
    assert rc == 0 and out["data"]["items"] == [] and "no OPEN-WORK.md" in out["data"]["note"]


def test_memory_add_creates_then_updates_with_advice(tmp_path, env):
    level = tmp_path / "proj"
    level.mkdir()
    fact = {"title": "Rule", "hook": "Do y.", "body": "Because z.", "level": str(level)}
    rc, out = call(tmp_path, env, "memory_add", fact)
    assert rc == 0 and out["data"]["action"] == "created"
    assert any("no trigger phrase" in w for w in out["data"]["warnings"])
    rc, out = call(tmp_path, env, "memory_add", fact)
    assert rc == 0 and out["data"]["action"] == "updated"


def test_memory_add_over_cap_hook_is_refused(tmp_path, env):
    level = tmp_path / "proj"
    level.mkdir()
    rc, out = call(tmp_path, env, "memory_add",
                   {"title": "L", "hook": "When x, " + "y" * 600, "body": "b", "level": str(level)})
    assert (rc, out["error"]["kind"]) == (1, "HookTooLong")


def test_memory_add_bad_type_is_refused(tmp_path, env):
    rc, out = call(tmp_path, env, "memory_add", {**FACT, "type": "note"})
    assert (rc, out["error"]["kind"]) == (1, "BadInput")


def test_contrib_add_queues_once(tmp_path, env):
    req = {"what": "fix x", "target": "hook", "why": "seen twice"}
    rc, out = call(tmp_path, env, "contrib_add", req)
    assert (rc, out["data"]) == (0, {"queued": True})
    rc, out = call(tmp_path, env, "contrib_add", req)
    assert rc == 0 and out["data"] == {"queued": False, "reason": "already queued"}


def test_a_why_with_a_newline_is_refused(tmp_path, env):
    rc, out = call(tmp_path, env, "contrib_add", {"what": "fix x", "target": "hook", "why": "a\nb"})
    assert (rc, out["error"]["kind"]) == (1, "MalformedField")


def test_a_missing_required_field_is_a_refusal(repo, env):
    rc, out = call(repo, env, "backlog_add", {k: v for k, v in ITEM.items() if k != "what"})
    assert (rc, out["error"]["kind"]) == (1, "MalformedField")


@pytest.mark.parametrize("raw", ["not json", "[]", '{"tool": "nope", "input": {}}',
                                 '{"tool": "backlog_list", "input": []}',
                                 '{"tool": ["x"], "input": {}}', '{"tool": {"a": 1}, "input": {}}',
                                 pytest.param("[" * 200000, id="deep-nesting")])
def test_a_request_the_bridge_cannot_run_exits_2(tmp_path, env, raw):
    p = run(tmp_path, env, raw.encode("utf-8"))
    assert p.returncode == 2 and len(p.stdout.decode("ascii").splitlines()) == 1
    out = json.loads(p.stdout.decode("ascii"))
    assert (out["ok"], out["error"]["kind"]) == (False, "BadRequest")


def test_a_bad_request_still_names_a_known_tool(tmp_path, env):
    rc, out = call(tmp_path, env, None, raw='{"tool": "backlog_list", "input": null}')
    assert (rc, out["tool"], out["error"]["kind"]) == (2, "backlog_list", "BadRequest")


def test_stdin_that_is_not_utf8_exits_2_with_one_ascii_line(tmp_path, env):
    p = run(tmp_path, env, b"\xff\xfe{")
    assert p.returncode == 2 and len(p.stdout.decode("ascii").splitlines()) == 1
    assert json.loads(p.stdout.decode("ascii"))["error"]["kind"] == "BadRequest"


def test_non_ascii_text_in_an_envelope_is_escaped(tmp_path, env):
    request = json.dumps({"tool": "caf\u00e9", "input": {}}).encode("utf-8")
    p = run(tmp_path, env, request)
    text = p.stdout.decode("ascii")
    assert p.returncode == 2 and "\\u00e9" in text
    assert json.loads(text)["error"]["kind"] == "BadRequest"


def test_a_refusal_over_non_ascii_input_is_ascii_json(repo, env):
    request = json.dumps({"tool": "backlog_close",
                          "input": {"rank": 99, "reason": "caf\u00e9"}}).encode("utf-8")
    p = run(repo, env, request)
    out = json.loads(p.stdout.decode("ascii"))
    assert p.returncode == 1 and out["ok"] is False


def test_a_state_that_is_no_state_is_a_refusal(repo, env):
    rc, out = call(repo, env, "backlog_list", {"state": 5})
    assert (rc, out["ok"], out["error"]["kind"]) == (1, False, "MalformedField")


@pytest.mark.parametrize("level", [5, [1], {"a": 1}, 0, False, [], "", "   "])
def test_a_level_that_is_no_path_string_is_refused_and_writes_nothing(tmp_path, env, level):
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    rc, out = call(cwd, env, "memory_add", {**FACT, "level": level})
    assert (rc, out["error"]["kind"]) == (1, "BadInput")
    assert list(cwd.iterdir()) == []


def test_a_level_that_is_home_is_an_excluded_level_refusal(tmp_path, env):
    rc, out = call(tmp_path, env, "memory_add", {**FACT, "level": env["HOME"]})
    assert (rc, out["error"]["kind"]) == (1, "ExcludedLevel")


def test_a_session_in_home_without_a_level_is_refused_not_internal(env):
    rc, out = call(env["HOME"], env, "memory_add", FACT)
    assert (rc, out["error"]["kind"]) == (1, "ExcludedLevel")


def test_an_unexpected_exception_still_yields_an_envelope(tmp_path, env):
    level = tmp_path / "proj"
    level.mkdir()
    (level / "CLAUDE.local.md").write_bytes(b"\xff\xfe not utf-8")
    request = json.dumps({"tool": "memory_add", "input": {**FACT, "level": str(level)}})
    p = run(tmp_path, env, request.encode("utf-8"))
    assert p.returncode == 2 and len(p.stdout.decode("ascii").splitlines()) == 1
    out = json.loads(p.stdout.decode("ascii"))
    assert (out["ok"], out["error"]["kind"]) == (False, "Internal")
    assert out["error"]["message"].startswith("TreeWalkError: ")
    assert b"Traceback" in p.stderr
