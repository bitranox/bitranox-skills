"""Tests for corpus_prompts: which records in a transcript are a person's typed prompt.

Every shape here was taken from the real corpus rather than imagined: over 300 transcripts,
14,884 user records split 13,790 tool_result / 890 plain string / 203 list-of-text, with
`entrypoint` on every record, `isSidechain` on 3,613, `isMeta` on 398 and `origin` on only 245.
That last number is why nothing here filters on `origin`.
"""
import json

import corpus_prompts as cp


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
