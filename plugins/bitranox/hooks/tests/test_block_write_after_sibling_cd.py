"""Tests for block-write-after-sibling-cd.py.

The two incident shapes are copied from real transcripts with the paths made generic: a writing
Bash call with no directory of its own ran right after a sibling call of the SAME assistant message
had cd'd elsewhere, and it inherited that directory.
"""
import io
import json
import sys

import pytest

import block_write_after_sibling_cd as guard
import transcript_siblings

PLANNING_COMMIT = "cd /work/umbrella/planning && git commit notes.md -F /tmp/msg-a.txt -q"
UMBRELLA_COMMIT = "git commit scripts/refresh.sh -F /tmp/msg-b.txt -q && git push -q origin HEAD"
OPEN_WORK_EDIT = "cd /work/bmk && python3 - <<'EOF'\nprint('edit OPEN-WORK.md')\nEOF"
GATE_RUN = 'timeout 900 python3 /tools/gate.py --log /tmp/l.log --gate "env -u VIRTUAL_ENV make test"'


def _record(message_id, tool_use_id, command, name="Bash"):
    return {"type": "assistant", "message": {"id": message_id, "content": [
        {"type": "tool_use", "id": tool_use_id, "name": name, "input": {"command": command}}]}}


def _result(tool_use_id):
    return {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": tool_use_id}]}}


# --- the incidents ---------------------------------------------------------------------------------

def test_incident_one_a_bare_commit_after_a_sibling_cd_is_refused():
    assert guard.verdict(UMBRELLA_COMMIT, [PLANNING_COMMIT]) is not None


def test_incident_two_a_gate_without_its_cwd_after_a_sibling_cd_is_refused():
    assert guard.verdict(GATE_RUN, [OPEN_WORK_EDIT]) is not None


# --- what must stay free ---------------------------------------------------------------------------

def test_a_lone_bare_commit_with_no_siblings_is_allowed():
    assert guard.verdict(UMBRELLA_COMMIT, []) is None


def test_a_bare_commit_whose_siblings_never_cd_is_allowed():
    assert guard.verdict(UMBRELLA_COMMIT, ["git status --porcelain", "ls -la"]) is None


@pytest.mark.parametrize("command", [
    "cd /work/umbrella && git commit x -F m",
    "git -C /work/umbrella commit x -F m",
    "make -C /work/bmk test",
    "python3 /tools/gate.py --gate-cwd /work/bmk --gate 'make test'",
    "python3 /tools/gate.py --gate-cwd=/work/bmk --gate 'make test'",
    # gate.py --cwd runs every gate there; the reported false refusal was the `-- cmd` form.
    "env -u VIRTUAL_ENV python3 /tools/gate.py --cwd /work/bmk -- make test",
    "python3 /tools/gate.py --cwd=/work/bmk --gate 'make test'",
    "python3 /tools/gate.py --cwd /work/bmk 'make test'",
    # The options, --gate-cwd included, are inside the expansion: not readable, so not judged.
    'python3 /tools/gate.py "${args[@]}"',
])
def test_an_explicit_target_is_allowed_even_beside_a_cd_ing_sibling(command):
    assert guard.verdict(command, [PLANNING_COMMIT]) is None


@pytest.mark.parametrize("command", [
    "git status --porcelain",
    "git log --oneline -1",
    "git diff --stat",
    "ls && cat README.md",
    "bmk --version",                                # measured in the corpus replay: read-only
    "/home/u/.local/bin/bmk --help",
    "bmk install --help 2>&1",
])
def test_a_read_only_command_is_allowed_beside_a_cd_ing_sibling(command):
    assert guard.verdict(command, [PLANNING_COMMIT]) is None


@pytest.mark.parametrize("sibling", [
    "python3 - <<'EOF'\ncd /elsewhere && git commit\nEOF",
    "echo 'cd /elsewhere'",
    "git commit -m 'cd /elsewhere'",
])
def test_a_cd_that_is_only_data_in_a_sibling_does_not_count(sibling):
    assert guard.verdict(UMBRELLA_COMMIT, [sibling]) is None


# --- what still counts as no target -----------------------------------------------------------------

@pytest.mark.parametrize("command", [
    "cd sub && git commit x -F m",                  # relative: lands under the INHERITED directory
    "git -C sub commit x -F m",
    "make test",
    "env -u VIRTUAL_ENV make push",
    "bmk test",
    "git add -A",
    "git push origin HEAD:master",
    "git checkout -- file.txt",
    "git reset --hard HEAD~1",
    "python3 /tools/gate.py -- make test",
    "python3 /tools/gate.py --cwd sub -- make test",
])
def test_a_write_without_an_absolute_target_is_refused_beside_a_cd_ing_sibling(command):
    assert guard.verdict(command, [PLANNING_COMMIT]) is not None


def test_a_write_after_the_commands_own_absolute_cd_is_judged_from_there():
    # The statement before the cd is target-less; the one after it is not.
    assert guard.verdict("git add -A && cd /work/x && git commit -m m", [PLANNING_COMMIT]) is not None
    assert guard.verdict("cd /work/x && git add -A && git commit -m m", [PLANNING_COMMIT]) is None


def test_a_sibling_cd_with_an_unreadable_target_still_counts():
    # Where it lands is unknown, which is exactly why the next call cannot rely on its own cwd.
    assert guard.verdict(UMBRELLA_COMMIT, ['cd "$REPO" && git status']) is not None


# --- finding the siblings in the transcript ---------------------------------------------------------

def test_earlier_siblings_are_the_bash_calls_of_the_same_message_before_this_one():
    records = [
        _record("msg_old", "t0", "cd /old && true"),
        _result("t0"),
        _record("msg_now", "t1", PLANNING_COMMIT),
        _record("msg_now", "t2", "echo not bash", name="Read"),
        _record("msg_now", "t3", UMBRELLA_COMMIT),
        _record("msg_now", "t4", "cd /later && true"),
    ]
    assert transcript_siblings.earlier_siblings(records, "t3") == [PLANNING_COMMIT]


def test_a_call_from_an_earlier_message_is_not_a_sibling():
    records = [_record("msg_old", "t0", PLANNING_COMMIT), _result("t0"), _record("msg_now", "t1", UMBRELLA_COMMIT)]
    assert transcript_siblings.earlier_siblings(records, "t1") == []


def test_a_call_missing_from_the_transcript_has_no_known_siblings():
    assert transcript_siblings.earlier_siblings([_record("m", "t1", PLANNING_COMMIT)], "t9") is None


# --- the hook end to end ------------------------------------------------------------------------------

def _run(monkeypatch, capsys, tmp_path, records, tool_use_id, command):
    transcript = tmp_path / "session.jsonl"
    transcript.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
    event = {"tool_name": "Bash", "tool_use_id": tool_use_id, "transcript_path": str(transcript),
             "tool_input": {"command": command}}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(event)))
    code = guard.main()
    return code, capsys.readouterr().err


def test_the_hook_refuses_incident_one_and_says_how_to_fix_it(monkeypatch, capsys, tmp_path):
    records = [_record("m", "t1", PLANNING_COMMIT), _record("m", "t2", UMBRELLA_COMMIT)]
    code, err = _run(monkeypatch, capsys, tmp_path, records, "t2", UMBRELLA_COMMIT)
    assert code == 2
    assert "git -C" in err and "/work/umbrella/planning" in err
    assert "nothing in this call ran" in err.lower()
    assert err.lower().count("nothing in this call ran") == 1


def test_the_advice_leads_with_git_c_and_warns_a_session_root_cd_is_stripped():
    # Measured 2026-10-26 and 2026-10-29: Claude Code strips a leading `cd <session root> &&`
    # before a hook sees the command, so advising that cd sends the reader into the same refusal.
    text = guard.refusal("git commit x -F m", "cd /work/planning")
    advice = text[text.index("Name the repository"):]
    assert advice.index("git -C /abs/repo") < advice.index("cd /abs/repo")
    assert "strips that cd" in advice


def test_the_powershell_tool_is_read_the_same_way(monkeypatch, capsys, tmp_path):
    records = [_record("m", "t1", "Set-Location C:/work/planning; git commit notes.md -F m1", name="PowerShell"),
               _record("m", "t2", "git commit scripts/refresh.ps1 -F m2", name="PowerShell")]
    transcript = tmp_path / "session.jsonl"
    transcript.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
    event = {"tool_name": "PowerShell", "tool_use_id": "t2", "transcript_path": str(transcript),
             "tool_input": {"command": "git commit scripts/refresh.ps1 -F m2"}}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(event)))
    assert guard.main() == 2
    # A POSIX absolute target: what counts as absolute follows the host OS, and the hook runs on the
    # same machine as the shell it guards (pwsh runs on Linux too).
    assert guard.verdict("git -C /work/umbrella commit x -F m", ["Set-Location /work/planning"],
                         "PowerShell") is None


def test_the_hook_allows_a_lone_bare_commit(monkeypatch, capsys, tmp_path):
    records = [_record("m", "t2", UMBRELLA_COMMIT)]
    code, err = _run(monkeypatch, capsys, tmp_path, records, "t2", UMBRELLA_COMMIT)
    assert (code, err) == (0, "")


def test_the_hook_fails_open_without_a_transcript(monkeypatch, capsys):
    event = {"tool_name": "Bash", "tool_use_id": "t2", "transcript_path": "/nonexistent/x.jsonl",
             "tool_input": {"command": UMBRELLA_COMMIT}}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(event)))
    assert guard.main() == 0


def test_the_hook_reads_only_the_tail_of_a_long_transcript(monkeypatch, capsys, tmp_path):
    filler = [_record("old%d" % i, "f%d" % i, "echo " + "x" * 200) for i in range(5000)]
    records = filler + [_record("m", "t1", PLANNING_COMMIT), _record("m", "t2", UMBRELLA_COMMIT)]
    code, _err = _run(monkeypatch, capsys, tmp_path, records, "t2", UMBRELLA_COMMIT)
    assert code == 2


def test_a_call_inside_a_subagent_is_judged_against_the_subagent_s_own_siblings(monkeypatch, capsys, tmp_path):
    # A subagent's event carries the PARENT's transcript_path plus agent_id; its records sit in
    # <parent minus .jsonl>/subagents/agent-<agent_id>.jsonl. Reading the parent never found the call.
    main = tmp_path / "session.jsonl"
    main.write_text(json.dumps(_record("p", "p1", "echo parent")) + "\n", encoding="utf-8")
    sub = tmp_path / "session" / "subagents"
    sub.mkdir(parents=True)
    (sub / "agent-a1.jsonl").write_text(
        json.dumps(_record("m", "t1", PLANNING_COMMIT)) + "\n" + json.dumps(_record("m", "t2", UMBRELLA_COMMIT)) + "\n",
        encoding="utf-8")
    event = {"tool_name": "Bash", "tool_input": {"command": UMBRELLA_COMMIT}, "transcript_path": str(main),
             "tool_use_id": "t2", "agent_id": "a1"}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(event)))

    assert guard.main() == 2
