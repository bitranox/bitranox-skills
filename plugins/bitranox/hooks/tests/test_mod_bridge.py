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


def call(cwd, env, tool, payload=None, raw=None):
    data = raw if raw is not None else json.dumps({"tool": tool, "input": payload or {}})
    p = subprocess.run([sys.executable, str(BRIDGE)], input=data.encode("utf-8"),
                       capture_output=True, cwd=cwd, env=env)
    return p.returncode, json.loads(p.stdout.decode("ascii"))


ITEM = {"rank": 20, "origin": "USER", "what": "w", "size": "1", "open": "o", "next": "n"}


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
    rc, out = call(tmp_path, env, "memory_add",
                   {"title": "T", "hook": "When x, y.", "body": "b", "type": "note"})
    assert (rc, out["error"]["kind"]) == (1, "BadInput")


def test_contrib_add_queues_once(tmp_path, env):
    req = {"what": "fix x", "target": "hook", "why": "seen twice"}
    rc, out = call(tmp_path, env, "contrib_add", req)
    assert (rc, out["data"]) == (0, {"queued": True})
    rc, out = call(tmp_path, env, "contrib_add", req)
    assert rc == 0 and out["data"] == {"queued": False, "reason": "already queued"}


def test_a_missing_required_field_is_a_refusal(repo, env):
    rc, out = call(repo, env, "backlog_add", {k: v for k, v in ITEM.items() if k != "what"})
    assert (rc, out["error"]["kind"]) == (1, "MalformedField")


@pytest.mark.parametrize("raw", ["not json", "[]", '{"tool": "nope", "input": {}}',
                                 '{"tool": "backlog_list", "input": []}'])
def test_a_request_the_bridge_cannot_run_exits_2(tmp_path, env, raw):
    rc, out = call(tmp_path, env, None, raw=raw)
    assert (rc, out["ok"], out["error"]["kind"]) == (2, False, "BadRequest")


def test_a_state_that_is_no_state_is_a_refusal(repo, env):
    rc, out = call(repo, env, "backlog_list", {"state": 5})
    assert (rc, out["ok"], out["error"]["kind"]) == (1, False, "MalformedField")


def test_an_unexpected_exception_still_yields_an_envelope(tmp_path, env):
    rc, out = call(tmp_path, env, "memory_add",
                   {"title": "T", "hook": "When x, y.", "body": "b", "level": 5})
    assert (rc, out["ok"], out["error"]["kind"]) == (2, False, "Internal")
    assert out["error"]["message"].startswith("TypeError: ")
