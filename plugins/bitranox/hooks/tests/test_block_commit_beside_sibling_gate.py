"""Tests for block-commit-beside-sibling-gate.py.

The incident: a test run and a `git add -A && git commit` were sent as two calls of ONE assistant
message. A guard refused the test call; the commit, its sibling, ran anyway - sibling calls run
regardless of each other, so nobody had read the verdict the commit depended on.
"""
import io
import json
import sys

import pytest

import block_commit_beside_sibling_gate as guard

COMMIT = "git add -A && git commit -q -m 'wip: docs'"
PYTEST = ".venv/bin/python -m pytest -q -p no:cacheprovider tests/test_x.py 2>&1 | tail -1"


def _record(message_id, tool_use_id, command, name="Bash"):
    return {"type": "assistant", "message": {"id": message_id, "content": [
        {"type": "tool_use", "id": tool_use_id, "name": name, "input": {"command": command}}]}}


# --- the verdict -----------------------------------------------------------------------------------


def test_the_incident_a_commit_after_a_sibling_test_run_is_refused():
    assert guard.verdict(COMMIT, [PYTEST]) == PYTEST


@pytest.mark.parametrize("gate", [
    "make test",
    "cd /w/repo && env -u VIRTUAL_ENV make test-all",
    'python3 /tools/gate.py --gate "make test" --log /tmp/g.log',
    "uv run pyright src",
    "ruff check src tests",
    "cargo test --workspace",
    "npm test",
    "timeout 900 python3 /tools/gate.py --log /tmp/g.log --gate 'make test'",
    "nice -n 19 pytest -x",
    "env -u VIRTUAL_ENV BMK_PYTHON_CMD=/w/.venv/bin/python make test",
    "env -u VIRTUAL_ENV uv run -q --with pytest --with httpx2 python -m pytest tests/ -q",
    "A=1 B=2 pytest",
])
def test_every_recognised_gate_counts_as_a_sibling_verdict(gate):
    assert guard.verdict(COMMIT, [gate]) == gate


@pytest.mark.parametrize("action", [
    "git push origin HEAD",
    "cd /w/repo && git commit -F /tmp/msg.txt",
    "gh pr create --title t --body-file /tmp/b.md",
])
def test_every_publishing_action_is_judged(action):
    assert guard.verdict(action, ["pytest -q"]) == "pytest -q"


def test_a_commit_whose_siblings_run_no_gate_is_allowed():
    assert guard.verdict(COMMIT, ["git status --porcelain", "git diff --stat"]) is None


def test_a_lone_commit_is_allowed():
    assert guard.verdict(COMMIT, []) is None


def test_a_call_that_does_not_publish_is_allowed_beside_a_gate():
    assert guard.verdict("git status && git log --oneline -3", ["pytest -q"]) is None


def test_a_gate_chained_into_the_commit_in_the_same_call_is_allowed():
    # The fix the refusal prescribes: one call, the gate gating the commit with &&.
    assert guard.verdict("make test && git commit -F /tmp/m.txt", []) is None


@pytest.mark.parametrize("sibling", [
    "cat > /tmp/notes.md <<'EOF'\nrun pytest before you commit\nEOF",
    "echo 'run make test first'",
    "grep -rn pytest docs/",
    "cat pytest.ini",
    "git log --oneline --grep pytest",
    "python3 -c 'import pytest'",
    "ls tests/ && rg -l 'make test' docs",
])
def test_a_gate_that_is_only_text_in_a_sibling_does_not_count(sibling):
    assert guard.verdict(COMMIT, [sibling]) is None


def test_a_commit_that_is_only_text_does_not_count():
    note = "cat > /tmp/m.md <<'EOF'\ngit commit after the gate\nEOF"
    assert guard.verdict(note, ["pytest -q"]) is None


# --- the hook --------------------------------------------------------------------------------------


def _run(monkeypatch, capsys, event):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(event)))
    code = guard.main()
    return code, capsys.readouterr().err


def _transcript(tmp_path, records):
    path = tmp_path / "session.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
    return str(path)


def test_the_hook_refuses_the_incident_and_says_how_to_fix_it(monkeypatch, capsys, tmp_path):
    path = _transcript(tmp_path, [_record("m", "t1", PYTEST), _record("m", "t2", COMMIT)])
    event = {"tool_name": "Bash", "tool_input": {"command": COMMIT}, "transcript_path": path, "tool_use_id": "t2"}

    code, err = _run(monkeypatch, capsys, event)

    assert code == 2
    assert "BLOCKED" in err
    assert "pytest" in err
    assert "&&" in err  # names the chained form
    assert "next message" in err


def test_the_hook_allows_a_gate_from_an_earlier_message(monkeypatch, capsys, tmp_path):
    path = _transcript(tmp_path, [_record("m1", "t1", PYTEST), _record("m2", "t2", COMMIT)])
    event = {"tool_name": "Bash", "tool_input": {"command": COMMIT}, "transcript_path": path, "tool_use_id": "t2"}

    assert _run(monkeypatch, capsys, event) == (0, "")


def test_the_hook_reads_a_subagent_s_own_transcript(monkeypatch, capsys, tmp_path):
    main = _transcript(tmp_path, [_record("p", "p1", "echo parent")])
    sub = tmp_path / "session" / "subagents"
    sub.mkdir(parents=True)
    (sub / "agent-a1.jsonl").write_text(
        json.dumps(_record("n", "c1", "make test")) + "\n" + json.dumps(_record("n", "c2", COMMIT)) + "\n",
        encoding="utf-8")
    event = {"tool_name": "Bash", "tool_input": {"command": COMMIT}, "transcript_path": main,
             "tool_use_id": "c2", "agent_id": "a1"}

    code, _err = _run(monkeypatch, capsys, event)

    assert code == 2


def test_the_powershell_tool_is_read_the_same_way(monkeypatch, capsys, tmp_path):
    path = _transcript(tmp_path, [_record("m", "t1", "pytest -q", name="PowerShell"),
                                  _record("m", "t2", "git push", name="PowerShell")])
    event = {"tool_name": "PowerShell", "tool_input": {"command": "git push"}, "transcript_path": path,
             "tool_use_id": "t2"}

    code, _err = _run(monkeypatch, capsys, event)

    assert code == 2


def test_the_hook_fails_open_without_a_transcript(monkeypatch, capsys):
    event = {"tool_name": "Bash", "tool_input": {"command": COMMIT}, "tool_use_id": "t2"}

    assert _run(monkeypatch, capsys, event) == (0, "")


def test_the_hook_ignores_other_tools_and_bad_input(monkeypatch, capsys):
    assert _run(monkeypatch, capsys, {"tool_name": "Read", "tool_input": {"file_path": "x"}}) == (0, "")
    monkeypatch.setattr(sys, "stdin", io.StringIO("not json"))
    assert guard.main() == 0
