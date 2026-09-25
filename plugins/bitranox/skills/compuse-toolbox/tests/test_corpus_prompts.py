"""Tests for corpus_prompts: which records in a transcript are a person's typed prompt.

Every shape here was taken from the real corpus rather than imagined: over 300 transcripts,
14,884 user records split 13,790 tool_result / 890 plain string / 203 list-of-text, with
`entrypoint` on every record, `isSidechain` on 3,613, `isMeta` on 398 and `origin` on only 245.
That last number is why nothing here filters on `origin`.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import corpus_prompts as cp

TOOL = Path(__file__).resolve().parents[1] / "scripts" / "corpus_prompts.py"


def rec(**over):
    """A typed prompt record, with the fields the real corpus carries."""
    base = {"type": "user", "uuid": "u1", "cwd": "/repo", "sessionId": "s1",
            "entrypoint": "cli", "isSidechain": False, "gitBranch": "master",
            "message": {"role": "user", "content": "fix the CRLF handling"}}
    base.update(over)
    return base


def lines(*records):
    return "\n".join(json.dumps(r) for r in records)


def test_a_typed_prompt_is_extracted_with_the_context_a_replay_needs():
    got = cp.extract_prompts(lines(rec()), source="/t/a.jsonl")
    assert len(got) == 1
    p = got[0]
    assert p["prompt"] == "fix the CRLF handling"
    assert p["cwd"] == "/repo" and p["session_id"] == "s1" and p["uuid"] == "u1"
    assert p["source"] == "/t/a.jsonl" and p["line"] == 1
    assert p["git_branch"] == "master"


def test_a_tool_result_record_is_not_a_prompt():
    # 13,790 of 14,884 user records in the corpus are these. Counting them as prompts would
    # swamp the sample with the assistant's own tool traffic.
    tool_result = rec(message={"role": "user", "content": [{"type": "tool_result",
                                                            "content": "ok"}]},
                      toolUseResult={"stdout": "ok"})
    assert cp.extract_prompts(lines(tool_result)) == []


def test_a_meta_record_is_not_a_prompt():
    assert cp.extract_prompts(lines(rec(isMeta=True))) == []


def test_a_subagent_prompt_is_excluded_by_default_and_available_on_request():
    sidechain = rec(uuid="u2", isSidechain=True)
    assert cp.extract_prompts(lines(sidechain)) == []
    assert len(cp.extract_prompts(lines(sidechain), sidechain=True)) == 1


def test_a_headless_sdk_prompt_is_not_a_person_at_a_terminal():
    # `entrypoint` separates a person typing from an SDK node being driven. Both are `type: user`.
    assert cp.extract_prompts(lines(rec(entrypoint="sdk-cli"))) == []


def test_list_of_text_content_is_joined_rather_than_dropped():
    blocks = rec(message={"role": "user", "content": [{"type": "text", "text": "first"},
                                                      {"type": "text", "text": "second"}]})
    assert cp.extract_prompts(lines(blocks))[0]["prompt"] == "first\nsecond"


def test_a_malformed_line_is_skipped_rather_than_fatal():
    # A transcript being written while it is read routinely ends mid-line; aborting there would
    # truncate the corpus silently.
    text = lines(rec()) + "\n{not json\n" + json.dumps(rec(uuid="u3"))
    assert [p["uuid"] for p in cp.extract_prompts(text)] == ["u1", "u3"]


def test_the_same_prompt_in_a_resumed_session_is_counted_once(tmp_path):
    # Resuming or forking copies the earlier transcript into a new file under the same uuid.
    (tmp_path / "a.jsonl").write_text(lines(rec()), encoding="utf-8")
    (tmp_path / "b.jsonl").write_text(lines(rec(), rec(uuid="u9")), encoding="utf-8")
    got = cp.collect_prompts(str(tmp_path))
    assert sorted(p["uuid"] for p in got["prompts"]) == ["u1", "u9"]
    assert got["duplicates_skipped"] == 1
    assert got["files_read"] == 2


def test_a_subagent_transcript_two_levels_down_is_still_walked(tmp_path):
    # Subagent transcripts sit at <project>/<session>/subagents/agent-*.jsonl, so a shallow
    # glob reads a fraction of the corpus.
    deep = tmp_path / "proj" / "sess" / "subagents"
    deep.mkdir(parents=True)
    (deep / "agent-1.jsonl").write_text(lines(rec()), encoding="utf-8")
    assert len(cp.collect_prompts(str(tmp_path))["prompts"]) == 1


def test_reading_nothing_is_reported_rather_than_returned_as_a_clean_empty(tmp_path):
    got = cp.collect_prompts(str(tmp_path / "does-not-exist"))
    assert got["files_read"] == 0 and got["prompts"] == []


def test_two_predicates_are_compared_by_their_firing_SETS_not_their_counts():
    # Equal counts can cover different prompts. A count diff of zero is the shape that hides a
    # change, so the report carries the sets.
    prompts = [{"uuid": "a", "prompt": "run the gate"}, {"uuid": "b", "prompt": "write a note"}]
    report = cp.diff_predicates(prompts, lambda p: "gate" in p, lambda p: "note" in p)
    assert report["a_only"] == ["a"] and report["b_only"] == ["b"]
    assert report["both"] == [] and report["a_fired"] == 1 and report["b_fired"] == 1


def test_a_predicate_that_never_fires_is_reported_as_such():
    report = cp.diff_predicates([{"uuid": "a", "prompt": "x"}], lambda p: False, lambda p: True)
    assert report["a_fired"] == 0 and report["b_only"] == ["a"]


# --- records are split the way a JSONL writer wrote them ------------------------------------------

def test_a_raw_line_separator_inside_a_prompt_neither_drops_it_nor_shifts_line_numbers():
    """JSON may carry U+2028 unescaped; splitlines() broke the record in two there."""
    text = "\n".join(json.dumps(r, ensure_ascii=False) for r in (
        rec(uuid="u1"),
        rec(uuid="u2", message={"role": "user", "content": "first\u2028second"}),
        rec(uuid="u3"),
    ))
    got = cp.extract_prompts(text)
    assert [(p["uuid"], p["line"]) for p in got] == [("u1", 1), ("u2", 2), ("u3", 3)]
    assert got[1]["prompt"] == "first\u2028second"


def test_a_utf8_bom_does_not_lose_the_first_record(tmp_path):
    (tmp_path / "a.jsonl").write_bytes(b"\xef\xbb\xbf" + lines(rec(), rec(uuid="u2")).encode())
    got = cp.collect_prompts(str(tmp_path))
    assert [p["uuid"] for p in got["prompts"]] == ["u1", "u2"]


def test_a_tool_result_block_without_a_tool_use_result_field_is_not_a_prompt():
    """The content-level check, not the record-level toolUseResult shortcut, must refuse it."""
    mixed = rec(message={"role": "user", "content": [{"type": "text", "text": "note"},
                                                     {"type": "tool_result", "content": "ok"}]})
    assert "toolUseResult" not in mixed
    assert cp.extract_prompts(lines(mixed)) == []


# --- a diff of prompts without a uuid must not collapse them ------------------------------------

def test_prompts_without_a_uuid_are_keyed_by_where_they_came_from():
    prompts = [{"uuid": None, "prompt": "gate one", "source": "/t/a.jsonl", "line": 1},
               {"uuid": None, "prompt": "gate two", "source": "/t/a.jsonl", "line": 2},
               {"uuid": None, "prompt": "note", "source": "/t/a.jsonl", "line": 3}]
    report = cp.diff_predicates(prompts, lambda p: "gate" in p, lambda p: "note" in p)
    assert report["both"] == []
    assert report["a_only"] == ["/t/a.jsonl:1", "/t/a.jsonl:2"]
    assert report["b_only"] == ["/t/a.jsonl:3"]


def test_prompts_with_neither_uuid_nor_source_are_keyed_by_position():
    prompts = [{"prompt": "gate one"}, {"prompt": "gate two"}]
    report = cp.diff_predicates(prompts, lambda p: "gate" in p, lambda p: False)
    assert len(report["a_only"]) == 2


# --- the CLI: exit codes 0 found / 1 no prompt / 2 usage or IO error -----------------------------

def _corpus(tmp_path):
    root = tmp_path / "corpus"
    root.mkdir()
    (root / "s.jsonl").write_text(lines(
        rec(uuid="u1", message={"role": "user", "content": "alpha"}),
        rec(uuid="u2", message={"role": "user", "content": "beta"}),
        rec(uuid="u3", message={"role": "user", "content": "the gate fires here"}),
        rec(uuid="u4", message={"role": "user", "content": "delta"}),
    ), encoding="utf-8")
    pred = tmp_path / "pred.py"
    pred.write_text("def b(text):\n    return 'gate' in text\n\n"
                    "def a(text):\n    return 'eta' in text\n", encoding="utf-8")
    return root, pred


def test_cli_counts_and_exits_0(tmp_path, capsys):
    root, _ = _corpus(tmp_path)
    assert cp.main(["--root", str(root), "--count"]) == 0
    assert "prompts: 4" in capsys.readouterr().out


def test_cli_an_existing_empty_root_exits_1(tmp_path, capsys):
    assert cp.main(["--root", str(tmp_path), "--count"]) == 1


def test_cli_a_root_that_does_not_exist_is_a_usage_error(tmp_path, capsys):
    """A typo'd --root printed 'prompts: 0' and exited 1, identical to an empty corpus."""
    assert cp.main(["--root", str(tmp_path / "nope"), "--count"]) == 2
    assert "nope" in capsys.readouterr().err


def test_cli_sample_prints_firings_not_the_first_prompts(tmp_path, capsys):
    root, pred = _corpus(tmp_path)
    assert cp.main(["--root", str(root), "--module", str(pred), "--func", "b",
                    "--sample", "5"]) == 0
    out = capsys.readouterr().out
    assert "u3 | the gate fires here" in out
    assert "u1 |" not in out and "u2 |" not in out and "u4 |" not in out


def test_cli_json_sample_holds_n_firings(tmp_path, capsys):
    root, pred = _corpus(tmp_path)
    assert cp.main(["--root", str(root), "--module", str(pred), "--func", "b",
                    "--sample", "1", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert [p["uuid"] for p in payload["prompts"]] == ["u3"]


def test_cli_json_sample_without_a_predicate_holds_the_first_n_prompts(tmp_path, capsys):
    root, _ = _corpus(tmp_path)
    assert cp.main(["--root", str(root), "--sample", "2", "--json"]) == 0
    assert [p["uuid"] for p in json.loads(capsys.readouterr().out)["prompts"]] == ["u1", "u2"]


def test_cli_sample_with_two_predicates_covers_both_firing_sets(tmp_path, capsys):
    root, pred = _corpus(tmp_path)
    assert cp.main(["--root", str(root), "--module", str(pred), "--func", "b",
                    "--module-b", str(pred), "--func-b", "a", "--sample", "9", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    # the first predicate (b) fires on u3 only, the second (a) on 'beta' (u2) only
    assert sorted(p["uuid"] for p in payload["prompts"]) == ["u2", "u3"]


@pytest.mark.parametrize("argv", [
    ["--module-b", "pred.py", "--func-b", "b"],
    ["--func", "b"],
    ["--module", "pred.py", "--func", "b", "--func-b", "b"],
])
def test_cli_a_predicate_option_without_its_module_is_a_usage_error(tmp_path, capsys, argv):
    """--module-b with no --module was silently ignored, exit 0."""
    root, pred = _corpus(tmp_path)
    argv = [str(pred) if a == "pred.py" else a for a in argv]
    assert cp.main(["--root", str(root), *argv]) == 2
    assert "corpus_prompts:" in capsys.readouterr().err


@pytest.mark.skipif(sys.platform == "win32" or (hasattr(os, "geteuid") and os.geteuid() == 0),
                    reason="needs POSIX permissions that bind the running user (root reads anyway)")
def test_cli_an_unreadable_transcript_exits_2_and_says_so_on_stderr(tmp_path, capsys):
    root, _ = _corpus(tmp_path)
    locked = root / "b.jsonl"
    locked.write_text(lines(rec(uuid="u9")), encoding="utf-8")
    locked.chmod(0)
    try:
        rc = cp.main(["--root", str(root), "--count"])
    finally:
        locked.chmod(0o644)
    captured = capsys.readouterr()
    assert rc == 2
    assert "skipped:" in captured.err and "b.jsonl" in captured.err
    assert "b.jsonl" not in captured.out


@pytest.mark.skipif(sys.platform == "win32" or (hasattr(os, "geteuid") and os.geteuid() == 0),
                    reason="needs POSIX permissions that bind the running user (root reads anyway)")
def test_cli_an_unreadable_subdirectory_exits_2_rather_than_undercounting(tmp_path, capsys):
    root, _ = _corpus(tmp_path)
    sub = root / "proj"
    sub.mkdir()
    (sub / "x.jsonl").write_text(lines(rec(uuid="u9")), encoding="utf-8")
    sub.chmod(0)
    try:
        rc = cp.main(["--root", str(root), "--count"])
    finally:
        sub.chmod(0o755)
    assert rc == 2
    assert "proj" in capsys.readouterr().err


def test_cli_a_prompt_the_console_cannot_encode_is_printed_not_a_crash(tmp_path):
    root = tmp_path / "corpus"
    root.mkdir()
    (root / "s.jsonl").write_text(
        lines(rec(message={"role": "user", "content": "smile \U0001f600 please"})),
        encoding="utf-8")
    env = dict(os.environ, PYTHONIOENCODING="cp1252")
    r = subprocess.run([sys.executable, str(TOOL), "--root", str(root), "--sample", "5"],
                       capture_output=True, env=env, check=False)
    assert r.returncode == 0, r.stderr
    assert b"u1 | smile" in r.stdout
