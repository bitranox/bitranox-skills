"""Tests for transcript_tail.py. Fixtures mirror the real Claude Code JSONL shape. ASCII only."""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import transcript_tail as T


def _write(tmp_path, records):
    p = tmp_path / "t.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    return str(p)


def test_tail_returns_last_user_and_last_assistant_visible_text(tmp_path):
    recs = [
        {"type": "user", "message": {"role": "user", "content": "first user"}},
        {"type": "assistant", "message": {"role": "assistant", "content": [
            {"type": "thinking", "thinking": "hmm"}, {"type": "text", "text": "first assistant"}]}},
        {"type": "user", "message": {"role": "user", "content": "second user"}},
        {"type": "assistant", "message": {"role": "assistant", "content": [
            {"type": "text", "text": "final assistant"}, {"type": "tool_use", "name": "Bash", "input": {}}]}},
    ]
    out = T.tail_messages(_write(tmp_path, recs))
    assert out["user"] == "second user"
    assert out["assistant"] == "final assistant"   # thinking + tool_use excluded


def test_skips_sidechain_and_meta_by_default(tmp_path):
    recs = [
        {"type": "user", "message": {"role": "user", "content": "real user"}},
        {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "real asst"}]}},
        {"type": "user", "isSidechain": True, "message": {"role": "user", "content": "subagent prompt"}},
        {"type": "assistant", "isSidechain": True, "message": {"role": "assistant", "content": [{"type": "text", "text": "subagent reply"}]}},
        {"type": "user", "isMeta": True, "message": {"role": "user", "content": "meta note"}},
    ]
    out = T.tail_messages(_write(tmp_path, recs))
    assert out["user"] == "real user"
    assert out["assistant"] == "real asst"


def test_user_content_can_be_a_tool_result_list(tmp_path):
    recs = [{"type": "user", "message": {"role": "user", "content": [{"type": "tool_result", "content": "result text"}]}}]
    out = T.tail_messages(_write(tmp_path, recs))
    assert "result text" in out["user"]


def test_include_sidechain_flag_keeps_them(tmp_path):
    recs = [
        {"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "main"}]}},
        {"type": "assistant", "isSidechain": True, "message": {"role": "assistant", "content": [{"type": "text", "text": "sub"}]}},
    ]
    out = T.tail_messages(_write(tmp_path, recs), skip_sidechain=False)
    assert out["assistant"] == "sub"


# --- whole-transcript modes -------------------------------------------------------------

FOUR_TURNS = [
    {"type": "user", "message": {"role": "user", "content": "first user"}},
    {"type": "assistant", "message": {"role": "assistant", "content": [
        {"type": "thinking", "thinking": "hmm"}, {"type": "text", "text": "first assistant"}]}},
    {"type": "user", "message": {"role": "user", "content": "second user"}},
    {"type": "assistant", "message": {"role": "assistant", "content": [
        {"type": "text", "text": "final assistant"}, {"type": "tool_use", "name": "Bash", "input": {}}]}},
]


def test_all_messages_returns_every_turn_not_just_the_last(tmp_path):
    """The control: an empty or last-only return fails this, so a silent no-op cannot pass."""
    rows = T.all_messages(_write(tmp_path, FOUR_TURNS))
    assert rows == [
        {"line": 1, "role": "user", "kind": "prompt", "text": "first user"},
        {"line": 2, "role": "assistant", "kind": "text", "text": "first assistant"},
        {"line": 3, "role": "user", "kind": "prompt", "text": "second user"},
        {"line": 4, "role": "assistant", "kind": "text", "text": "final assistant"},
    ]
    # and it really is MORE than the tail returns, which is the whole point of the mode
    tail = T.tail_messages(_write(tmp_path, FOUR_TURNS))
    assert len(rows) > len([t for t in tail.values() if t])


def test_all_messages_role_filter_keeps_one_side(tmp_path):
    rows = T.all_messages(_write(tmp_path, FOUR_TURNS), role="user")
    assert [r["text"] for r in rows] == ["first user", "second user"]
    assert all(r["role"] == "user" for r in rows)


def test_all_messages_line_numbers_address_the_real_file_line(tmp_path):
    """Line numbers count blank and unparseable lines too, so `sed -n '<n>p'` finds the record."""
    p = tmp_path / "t.jsonl"
    p.write_text("\n".join([
        json.dumps({"type": "user", "message": {"role": "user", "content": "one"}}),
        "",
        "{not json at all",
        json.dumps({"type": "assistant", "message": {"role": "assistant",
                                                     "content": [{"type": "text", "text": "two"}]}}),
    ]) + "\n", encoding="utf-8")
    rows = T.all_messages(str(p))
    assert [(r["line"], r["text"]) for r in rows] == [(1, "one"), (4, "two")]
    physical = p.read_text(encoding="utf-8").splitlines()
    for row in rows:                                     # the number really indexes that line
        assert json.loads(physical[row["line"] - 1])["type"] == row["role"]


def test_all_messages_reports_unparseable_lines_instead_of_dropping_them(tmp_path):
    p = tmp_path / "t.jsonl"
    p.write_text('{"type": "user", "message": {"role": "user", "content": "ok"}}\n'
                 "{broken\n"
                 "[1, 2, 3]\n", encoding="utf-8")
    malformed = []
    rows = T.all_messages(str(p), malformed=malformed)
    assert [r["text"] for r in rows] == ["ok"]
    assert malformed == [2, 3]                           # a JSON non-object counts as malformed


def test_all_messages_skips_sidechain_and_meta_by_default(tmp_path):
    recs = [
        {"type": "user", "message": {"role": "user", "content": "real"}},
        {"type": "user", "isSidechain": True, "message": {"role": "user", "content": "sub"}},
        {"type": "user", "isMeta": True, "message": {"role": "user", "content": "meta"}},
    ]
    path = _write(tmp_path, recs)
    assert [r["text"] for r in T.all_messages(path)] == ["real"]
    assert [r["text"] for r in T.all_messages(path, skip_sidechain=False)] == ["real", "sub"]
    assert [r["text"] for r in T.all_messages(path, skip_meta=False)] == ["real", "meta"]


def test_tool_uses_lists_every_call_of_one_tool_with_its_input(tmp_path):
    recs = [
        {"type": "assistant", "message": {"role": "assistant", "content": [
            {"type": "text", "text": "dispatching"},
            {"type": "tool_use", "name": "Agent", "input": {"subagent_type": "Explore", "model": "sonnet"}},
            {"type": "tool_use", "name": "Agent", "input": {"subagent_type": "Plan", "model": "opus"}}]}},
        {"type": "assistant", "message": {"role": "assistant", "content": [
            {"type": "tool_use", "name": "Bash", "input": {"command": "ls"}}]}},
        {"type": "assistant", "message": {"role": "assistant", "content": [
            {"type": "tool_use", "name": "Agent", "input": {"subagent_type": "Plan", "model": "haiku"}}]}},
    ]
    rows = T.tool_uses(_write(tmp_path, recs), "Agent")
    assert rows == [
        {"line": 1, "name": "Agent", "input": {"subagent_type": "Explore", "model": "sonnet"}},
        {"line": 1, "name": "Agent", "input": {"subagent_type": "Plan", "model": "opus"}},
        {"line": 3, "name": "Agent", "input": {"subagent_type": "Plan", "model": "haiku"}},
    ]


def test_tool_uses_of_an_absent_tool_is_empty_while_a_present_one_is_not(tmp_path):
    """Paired so an always-empty implementation cannot pass the negative half alone."""
    recs = [{"type": "assistant", "message": {"role": "assistant", "content": [
        {"type": "tool_use", "name": "Bash", "input": {"command": "ls"}}]}}]
    path = _write(tmp_path, recs)
    assert T.tool_uses(path, "Agent") == []
    assert len(T.tool_uses(path, "Bash")) == 1


def test_tool_uses_skips_sidechain_by_default(tmp_path):
    recs = [
        {"type": "assistant", "message": {"role": "assistant", "content": [
            {"type": "tool_use", "name": "Bash", "input": {"command": "main"}}]}},
        {"type": "assistant", "isSidechain": True, "message": {"role": "assistant", "content": [
            {"type": "tool_use", "name": "Bash", "input": {"command": "sub"}}]}},
    ]
    path = _write(tmp_path, recs)
    assert [r["input"]["command"] for r in T.tool_uses(path, "Bash")] == ["main"]
    assert [r["input"]["command"] for r in T.tool_uses(path, "Bash", skip_sidechain=False)] == ["main", "sub"]


# --- CLI --------------------------------------------------------------------------------

def test_cli_default_output_is_unchanged_when_no_new_flag_is_passed(tmp_path, capsys):
    """Pins the pre-existing contract byte for byte: the new modes must be opt-in only."""
    rc = T.main([_write(tmp_path, FOUR_TURNS)])
    assert rc == 0
    assert capsys.readouterr().out == "== last user ==\nsecond user\n== last assistant ==\nfinal assistant\n"


def test_cli_all_prints_a_header_per_turn_and_exits_zero(tmp_path, capsys):
    rc = T.main([_write(tmp_path, FOUR_TURNS), "--all"])
    out = capsys.readouterr().out
    assert rc == 0
    assert out == ("== line 1 user ==\nfirst user\n"
                   "== line 2 assistant ==\nfirst assistant\n"
                   "== line 3 user ==\nsecond user\n"
                   "== line 4 assistant ==\nfinal assistant\n")


def test_cli_reports_no_match_with_exit_1_so_an_empty_result_is_never_silent(tmp_path, capsys):
    rc = T.main([_write(tmp_path, FOUR_TURNS), "--tool", "NoSuchTool"])
    assert rc == 1
    assert capsys.readouterr().out == ""


def test_cli_json_envelope_carries_the_rows_and_the_skipped_lines(tmp_path, capsys):
    p = tmp_path / "t.jsonl"
    p.write_text('{"type": "assistant", "message": {"role": "assistant", "content": '
                 '[{"type": "tool_use", "name": "Agent", "input": {"subagent_type": "Explore"}}]}}\n'
                 "{broken\n", encoding="utf-8")
    rc = T.main([str(p), "--tool", "Agent", "--json"])
    captured = capsys.readouterr()
    assert rc == 0
    envelope = json.loads(captured.out)
    assert envelope["ok"] is True
    assert envelope["command"] == "tool_uses"
    assert envelope["skipped"] == [2]
    assert envelope["data"] == [{"line": 1, "name": "Agent", "input": {"subagent_type": "Explore"}}]
    assert "unparseable" in captured.err            # the warning never pollutes the JSON stdout


def test_cli_refuses_both_modes_at_once(tmp_path, capsys):
    path = _write(tmp_path, FOUR_TURNS)
    assert T.main([path, "--all"]) == 0                  # each flag alone is accepted, so the
    assert T.main([path, "--tool", "Bash"]) == 0         # exit 2 below can only be the exclusion
    capsys.readouterr()
    with pytest.raises(SystemExit) as exc:
        T.main([path, "--all", "--tool", "Agent"])
    assert exc.value.code == 2


# --- robustness: malformed records, encodings, exit codes (subprocess, both JSON backends) ----

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "transcript_tail.py"

# Runs the real script with orjson either blocked (the stdlib fallback) or required.
_LAUNCH = ("import runpy, sys\n"
           "if sys.argv[1] == 'stdlib':\n"
           "    sys.modules['orjson'] = None\n"
           "else:\n"
           "    import orjson\n"
           "script = sys.argv[2]\n"
           "sys.argv = [script] + sys.argv[3:]\n"
           "runpy.run_path(script, run_name='__main__')\n")


@pytest.fixture(params=["stdlib", "orjson"])
def backend(request):
    if request.param == "orjson":
        pytest.importorskip("orjson")
    return request.param


def _cli(backend, *args, env_extra=None):
    env = {**os.environ, **(env_extra or {})}
    return subprocess.run([sys.executable, "-c", _LAUNCH, backend, str(SCRIPT), *args],
                          capture_output=True, env=env, check=False)


def test_a_non_dict_message_does_not_crash_any_mode(tmp_path, backend):
    p = tmp_path / "strmsg.jsonl"
    p.write_text(
        json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Agent", "input": {"x": 1}}]}}) + "\n"
        + json.dumps({"type": "system", "message": "compacted"}) + "\n"
        + json.dumps({"type": "user", "message": "hi"}) + "\n", encoding="utf-8")
    for args in (["--tool", "Agent"], ["--all"], []):
        r = _cli(backend, str(p), *args)
        assert b"Traceback" not in r.stderr, (args, r.stderr)
        assert r.returncode in (0, 1), (args, r.returncode)
    assert b"Agent" in _cli(backend, str(p), "--tool", "Agent").stdout


def test_invalid_utf8_line_is_skipped_not_fatal(tmp_path, backend):
    p = tmp_path / "badutf8.jsonl"
    p.write_bytes(b'{"type":"user","message":{"content":"ok"}}\n'
                  b'{"type":"user","message":{"content":"\xff\xfe"}}\n')
    r = _cli(backend, str(p), "--all")
    assert r.returncode == 0, r.stderr
    assert b"ok" in r.stdout
    assert b"skipped 1 unparseable line(s): 2" in r.stderr


def test_a_bom_does_not_drop_the_first_record(tmp_path, backend):
    p = tmp_path / "bom.jsonl"
    p.write_bytes(b"\xef\xbb\xbf"
                  + json.dumps({"type": "user", "message": {"content": "bom first"}}).encode() + b"\n")
    r = _cli(backend, str(p), "--all")
    assert r.returncode == 0, r.stderr
    assert b"bom first" in r.stdout
    assert b"unparseable" not in r.stderr


@pytest.mark.parametrize("extra", [[], ["--json"]])
def test_cp1252_stdout_does_not_crash(tmp_path, backend, extra):
    text = "done \\u2713 \\U0001f600".encode().decode("unicode_escape")
    p = tmp_path / "uni.jsonl"
    p.write_text(json.dumps({"type": "user", "message": {"content": text}}) + "\n", encoding="utf-8")
    r = _cli(backend, str(p), "--all", *extra,
             env_extra={"PYTHONIOENCODING": "cp1252", "PYTHONUTF8": "0"})
    assert r.returncode == 0, r.stderr
    if extra:
        assert json.loads(r.stdout)["data"][0]["text"] == text


@pytest.mark.parametrize("args", [["--tool", "Agent"], ["--all"], [], ["--json"], ["--all", "--json"]])
def test_a_missing_path_exits_2_not_the_no_match_code(tmp_path, args):
    r = _cli("stdlib", str(tmp_path / "nope.jsonl"), *args)
    assert r.returncode == 2
    assert b"Traceback" not in r.stderr
    assert b"nope.jsonl" in r.stderr
    if "--json" in args:
        doc = json.loads(r.stdout)
        assert doc["ok"] is False and "nope.jsonl" in doc["error"]


REAL = [
    {"type": "user", "message": {"role": "user", "content": "please list files"}},
    {"type": "assistant", "message": {"role": "assistant", "content": [
        {"type": "tool_use", "name": "Bash", "input": {"command": "ls"}}]}},
    {"type": "user", "message": {"role": "user", "content": [
        {"type": "tool_result", "content": "a.txt\nb.txt"}]}},
    {"type": "assistant", "message": {"role": "assistant", "content": [
        {"type": "text", "text": "Two files."}]}},
]


def _real_with_broken_line(tmp_path):
    p = tmp_path / "real.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in REAL) + "\n{broken\n", encoding="utf-8")
    return str(p)


def test_tail_json_reports_skipped_lines_and_honours_role(tmp_path, capsys):
    rc = T.main([_real_with_broken_line(tmp_path), "--json", "--role", "user"])
    captured = capsys.readouterr()
    assert rc == 0
    doc = json.loads(captured.out)
    assert doc["skipped"] == [5]
    assert doc["data"] == {"user": "a.txt\nb.txt"}
    assert "unparseable" in captured.err


def test_tail_plain_mode_warns_about_skipped_lines(tmp_path, capsys):
    T.main([_real_with_broken_line(tmp_path)])
    assert "skipped 1 unparseable line(s): 5" in capsys.readouterr().err


@pytest.mark.parametrize(("role", "shown", "hidden"), [
    ("user", "== last user ==", "== last assistant =="),
    ("assistant", "== last assistant ==", "== last user =="),
])
def test_tail_role_prints_only_that_side(tmp_path, capsys, role, shown, hidden):
    T.main([_write(tmp_path, FOUR_TURNS), "--role", role])
    out = capsys.readouterr().out
    assert shown in out
    assert hidden not in out


def test_all_rows_say_whether_a_user_row_is_a_prompt_or_a_tool_result(tmp_path):
    rows = T.all_messages(_real_with_broken_line(tmp_path), role="user")
    assert [(r["line"], r["kind"]) for r in rows] == [(1, "prompt"), (3, "tool_result")]


def test_prompts_only_answers_what_did_the_user_ask(tmp_path, capsys):
    rc = T.main([_real_with_broken_line(tmp_path), "--all", "--role", "user", "--prompts-only",
                 "--json"])
    doc = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert [r["text"] for r in doc["data"]] == ["please list files"]


def test_prompts_only_is_refused_without_all(tmp_path):
    with pytest.raises(SystemExit) as exc:
        T.main([_write(tmp_path, FOUR_TURNS), "--prompts-only"])
    assert exc.value.code == 2


def test_plain_all_output_labels_a_tool_result_row(tmp_path, capsys):
    T.main([_real_with_broken_line(tmp_path), "--all", "--role", "user"])
    out = capsys.readouterr().out
    assert "== line 1 user ==\nplease list files\n" in out
    assert "== line 3 user tool_result ==\na.txt\nb.txt\n" in out
