"""abtrace: subagent overlap from transcripts, idea markers from the stream, the suite's outcome from its log."""
import json
from pathlib import Path

import abtrace as X
import pytest

FIXTURES = Path(__file__).resolve().parent / "fixtures"


# --- subagent overlap ----------------------------------------------------------------------------

def _transcript(path, *stamps, extra_lines=()):
    """A transcript whose records carry the given timestamps (None: a record without one)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [json.dumps({"type": "user", **({"timestamp": t} if t else {})}) for t in stamps]
    path.write_text("\n".join([*rows, *extra_lines]) + "\n", encoding="utf-8")
    return path


def _ts(minute, second=0):
    return f"2026-11-08T10:{minute:02d}:{second:02d}.000Z"


def _subagents_dir(tmp_path):
    return tmp_path / "transcripts" / "-ws" / "sess-1" / "subagents"


def test_overlap_counts_agent_files_and_the_most_running_at_once(tmp_path):
    sub = _subagents_dir(tmp_path)
    _transcript(sub / "agent-a.jsonl", _ts(0), _ts(3), _ts(5))
    _transcript(sub / "agent-b.jsonl", _ts(1), _ts(2))
    _transcript(sub / "agent-c.jsonl", _ts(6), _ts(7))
    # The main session and the per-agent metadata are not subagent transcripts.
    _transcript(tmp_path / "transcripts" / "-ws" / "sess-1.jsonl", _ts(0), _ts(9))
    (sub / "agent-a.meta.json").write_text("{}", encoding="utf-8")
    assert X.subagent_overlap(tmp_path / "transcripts") == {"transcripts": 3, "max_concurrent": 2, "untimed": 0}


def test_an_agent_starting_when_another_ends_does_not_overlap_it(tmp_path):
    sub = _subagents_dir(tmp_path)
    _transcript(sub / "agent-a.jsonl", _ts(0), _ts(5))
    _transcript(sub / "agent-b.jsonl", _ts(5), _ts(8))
    assert X.subagent_overlap(tmp_path / "transcripts")["max_concurrent"] == 1


def test_background_agents_launched_together_all_count_as_running_at_once(tmp_path):
    """run_in_background returns at once, so only the transcripts' own times show the overlap."""
    sub = _subagents_dir(tmp_path)
    for name, end in (("a", 9), ("b", 7), ("c", 8), ("d", 6)):
        _transcript(sub / f"agent-{name}.jsonl", _ts(0, 1), _ts(end))
    assert X.subagent_overlap(tmp_path / "transcripts") == {"transcripts": 4, "max_concurrent": 4, "untimed": 0}


def test_overlap_takes_the_earliest_and_latest_stamp_whatever_the_line_order(tmp_path):
    sub = _subagents_dir(tmp_path)
    _transcript(sub / "agent-a.jsonl", _ts(4), _ts(0), _ts(1))  # spans 0..4, not 4..1
    _transcript(sub / "agent-b.jsonl", _ts(2), _ts(3))
    assert X.subagent_overlap(tmp_path / "transcripts")["max_concurrent"] == 2


def test_a_transcript_without_timestamps_is_counted_but_untimed(tmp_path):
    sub = _subagents_dir(tmp_path)
    _transcript(sub / "agent-a.jsonl", _ts(0), _ts(5))
    _transcript(sub / "agent-b.jsonl", None, None, extra_lines=("{torn",))
    _transcript(sub / "agent-c.jsonl", "not a time", None)
    assert X.subagent_overlap(tmp_path / "transcripts") == {"transcripts": 3, "max_concurrent": 1, "untimed": 2}


def test_a_torn_line_does_not_hide_the_stamps_around_it(tmp_path):
    sub = _subagents_dir(tmp_path)
    _transcript(sub / "agent-a.jsonl", _ts(0), extra_lines=("{torn", json.dumps({"timestamp": _ts(5)})))
    _transcript(sub / "agent-b.jsonl", _ts(4), _ts(6))
    assert X.subagent_overlap(tmp_path / "transcripts")["max_concurrent"] == 2


def test_no_transcripts_dir_is_none_and_an_empty_one_is_zero(tmp_path):
    assert X.subagent_overlap(tmp_path / "transcripts") is None
    (tmp_path / "transcripts").mkdir()
    assert X.subagent_overlap(tmp_path / "transcripts") == {"transcripts": 0, "max_concurrent": 0, "untimed": 0}


# --- idea markers --------------------------------------------------------------------------------

def _tool_use(tid, name, **inp):
    return {"type": "tool_use", "id": tid, "name": name, "input": inp}


def _assistant(*blocks, mid="m"):
    return {"type": "assistant", "message": {"id": mid, "model": "claude-opus-5-5", "content": list(blocks)}}


def _stream(tmp_path, *records):
    path = tmp_path / "stream.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
    return path


PROGRESS = ".bitranox/sdd/progress.md"


def test_markers_written_by_bash_write_and_edit_are_collected(tmp_path):
    stream = _stream(
        tmp_path,
        _assistant(_tool_use("t1", "Bash", command=f'echo "[abx] idea=2 plan split in 3 tasks" >> {PROGRESS}')),
        _assistant(_tool_use("t2", "Write", file_path=PROGRESS, content="# progress\n[abx] idea=1 brief written\n")),
        _assistant(_tool_use("t3", "Edit", file_path=PROGRESS, old_string="[abx] idea=1 brief written\n",
                             new_string="[abx] idea=1 brief written\n[abx] idea=1 brief reused\n")),
        _assistant(_tool_use("t4", "Bash", command=f"cat >> {PROGRESS} <<'EOF'\n[abx] idea=2 review ran\nEOF")),
    )
    assert X.idea_markers(stream) == {
        "writes": 4,
        "ideas": {"1": {"count": 2, "first": "[abx] idea=1 brief written"},
                  "2": {"count": 2, "first": "[abx] idea=2 plan split in 3 tasks"}}}


def test_markers_in_prompts_reads_and_echoed_text_do_not_count(tmp_path):
    stream = _stream(
        tmp_path,
        {"type": "user", "message": {"role": "user", "content": "Write [abx] idea=1 <what> to progress.md"}},
        _assistant({"type": "text", "text": "I will write [abx] idea=1 when done."}),
        _assistant(_tool_use("t1", "Agent", prompt="When done append [abx] idea=3 <what> to progress.md")),
        _assistant(_tool_use("t2", "Bash", command=f'grep -c "[abx] idea=1" {PROGRESS} 2>/dev/null')),
        _assistant(_tool_use("t3", "Read", file_path=PROGRESS)),
        {"type": "user", "message": {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "t3", "content": "[abx] idea=1 brief written"}]}},
    )
    assert X.idea_markers(stream) == {"writes": 0, "ideas": {}}


def test_a_repeated_tool_use_and_a_rewritten_line_count_once(tmp_path):
    write = _tool_use("t1", "Write", file_path=PROGRESS, content="[abx] idea=4 done\n")
    rewrite = _tool_use("t2", "Write", file_path=PROGRESS, content="[abx] idea=4 done\n[abx] idea=5 x\n")
    stream = _stream(tmp_path, _assistant(write), _assistant(write), _assistant(rewrite))
    markers = X.idea_markers(stream)
    assert (markers["ideas"]["4"]["count"], markers["ideas"]["5"]["count"]) == (1, 1)
    assert markers["writes"] == 2, "the repeated record of t1 is one call, not two"


def test_ideas_are_ordered_by_number_not_by_text(tmp_path):
    stream = _stream(tmp_path, _assistant(_tool_use(
        "t1", "Write", file_path=PROGRESS, content="[abx] idea=10 a\n[abx] idea=9 b\n[abx] idea=2 c\n")))
    assert list(X.idea_markers(stream)["ideas"]) == ["2", "9", "10"]


def test_an_idea_named_by_word_counts_and_sorts_after_the_numbered_ones(tmp_path):
    """A preregistered idea may be named by word; a digits-only pattern reported writes=0 for it."""
    stream = _stream(tmp_path, _assistant(_tool_use(
        "t1", "Bash",
        command=f"cat >> {PROGRESS} <<'EOF'\n[abx] idea=final-design-review ran\n[abx] idea=3 ran\nEOF")))
    markers = X.idea_markers(stream)
    assert markers["writes"] == 1
    assert list(markers["ideas"]) == ["3", "final-design-review"]
    assert markers["ideas"]["final-design-review"]["first"] == "[abx] idea=final-design-review ran"


def test_a_placeholder_in_angle_brackets_is_not_an_idea(tmp_path):
    stream = _stream(tmp_path, _assistant(_tool_use(
        "t1", "Bash", command=f'echo "[abx] idea=<id> <what>" >> {PROGRESS}')))
    assert X.idea_markers(stream) == {"writes": 0, "ideas": {}}


def test_multiedit_and_tee_writes_count(tmp_path):
    stream = _stream(
        tmp_path,
        _assistant(_tool_use("t1", "MultiEdit", file_path=PROGRESS,
                             edits=[{"old_string": "a", "new_string": "[abx] idea=6 one"}])),
        _assistant(_tool_use("t2", "Bash", command=f"printf '[abx] idea=7 two\\n' | tee -a {PROGRESS}")),
    )
    ideas = X.idea_markers(stream)["ideas"]
    assert ideas["6"]["first"] == "[abx] idea=6 one" and ideas["7"]["first"] == "[abx] idea=7 two"


def test_a_marker_a_subagent_wrote_is_read_from_its_transcript_once(tmp_path):
    """A background subagent's calls may be missing from stream.jsonl; its own transcript has them."""
    stream = _stream(tmp_path, _assistant(_tool_use("t1", "Write", file_path=PROGRESS, content="[abx] idea=1 a\n")))
    sub = _subagents_dir(tmp_path)
    sub.mkdir(parents=True)
    rows = [_assistant(_tool_use("t1", "Write", file_path=PROGRESS, content="[abx] idea=1 a\n")),  # also in the stream
            _assistant(_tool_use("s1", "Bash", command=f'echo "[abx] idea=8 from a subagent" >> {PROGRESS}'))]
    (sub / "agent-x.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    # The main session's transcript repeats the stream and is not read a second time.
    (tmp_path / "transcripts" / "-ws" / "sess-1.jsonl").write_text(json.dumps(rows[1]) + "\n", encoding="utf-8")
    markers = X.idea_markers(stream, tmp_path / "transcripts")
    assert markers == {"writes": 2, "ideas": {"1": {"count": 1, "first": "[abx] idea=1 a"},
                                             "8": {"count": 1, "first": "[abx] idea=8 from a subagent"}}}


def test_markers_with_transcripts_but_no_stream_still_read(tmp_path):
    sub = _subagents_dir(tmp_path)
    sub.mkdir(parents=True)
    row = _assistant(_tool_use("s1", "Write", file_path=PROGRESS, content="[abx] idea=2 x\n"))
    (sub / "agent-x.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
    assert X.idea_markers(tmp_path / "stream.jsonl", tmp_path / "transcripts")["ideas"]["2"]["count"] == 1
    assert X.idea_markers(tmp_path / "missing.jsonl", tmp_path / "no-transcripts") is None


def test_no_stream_is_none_and_a_torn_stream_still_reads(tmp_path):
    assert X.idea_markers(tmp_path / "stream.jsonl") is None
    path = _stream(tmp_path, _assistant(_tool_use("t1", "Write", file_path=PROGRESS, content="[abx] idea=1 x\n")))
    with path.open("a", encoding="utf-8") as fh:
        fh.write('{"type": "assistant", "mess')
    assert X.idea_markers(path)["ideas"]["1"]["count"] == 1


# --- the suite's outcome -------------------------------------------------------------------------

def _suite(rc, error=None):
    return {"name": "suite", "rc": rc, "error": error}


def test_a_compile_failure_names_its_codes_and_the_missing_symbols():
    out = X.suite_outcome(_suite(101), FIXTURES / "cargo-compile-error.log")
    assert out["outcome"] == X.SUITE_NO_COMPILE == "does_not_compile"
    assert out["error_codes"] == {"E0308": 1, "E0425": 1, "E0432": 2}
    assert out["missing"] == ["sbx::policy::Policy", "run_sandboxed", "sbx::mount::Bind"]
    assert (out["rc"], out["tests_failed"], out["tests_total"]) == (101, None, None)


def test_a_run_time_failure_counts_failed_of_total():
    out = X.suite_outcome(_suite(101), FIXTURES / "cargo-test-failed.log")
    assert out["outcome"] == X.SUITE_TESTS_FAILED == "tests_failed"
    assert (out["tests_failed"], out["tests_total"]) == (2, 10)
    assert (out["error_codes"], out["missing"]) == ({}, [])


def test_the_same_rc_gives_two_different_outcomes():
    """Both fixtures exit 101 from cargo test; the score must not put them in one bucket."""
    compile_ = X.suite_outcome(_suite(101), FIXTURES / "cargo-compile-error.log")["outcome"]
    runtime = X.suite_outcome(_suite(101), FIXTURES / "cargo-test-failed.log")["outcome"]
    assert compile_ != runtime


def test_passed_unfinished_unclassified_and_absent(tmp_path):
    log = tmp_path / "floor-suite.log"
    log.write_text("all fine\n", encoding="utf-8")
    assert X.suite_outcome(_suite(0), log)["outcome"] == X.SUITE_PASSED
    assert X.suite_outcome(_suite(124, error="timed out after 5 s"), log)["outcome"] == X.SUITE_NOT_FINISHED
    assert X.suite_outcome(_suite(0, error="output held open"), log)["outcome"] == X.SUITE_NOT_FINISHED
    assert X.suite_outcome(_suite(2), log)["outcome"] == X.SUITE_FAILED
    assert X.suite_outcome(_suite(2), tmp_path / "missing.log")["outcome"] == X.SUITE_FAILED
    assert X.suite_outcome(None, log) is None


def test_a_passing_run_still_reports_its_test_count(tmp_path):
    log = tmp_path / "floor-suite.log"
    log.write_text("test result: ok. 7 passed; 0 failed; 1 ignored; 0 measured; 0 filtered out\n", encoding="utf-8")
    out = X.suite_outcome(_suite(0), log)
    assert (out["outcome"], out["tests_failed"], out["tests_total"]) == (X.SUITE_PASSED, 0, 7)


def test_the_missing_list_is_capped_but_every_code_is_counted(tmp_path):
    log = tmp_path / "floor-suite.log"
    lines = [f"error[E0425]: cannot find function `f{i}` in this scope" for i in range(X.MISSING_CAP + 5)]
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")
    out = X.suite_outcome(_suite(101), log)
    assert len(out["missing"]) == X.MISSING_CAP and out["error_codes"] == {"E0425": X.MISSING_CAP + 5}


# --- a build prerequisite the worktree lacks (protoc) --------------------------------------------

BUILD_SCRIPT_FAILED = "error: failed to run custom build command for `sbx-proto v0.1.0 (/work/sbx-proto)`"
# What prost-build before 0.12 printed, and what any build script prints when PROTOC names a path
# the arm's worktree does not have (a gitignored .packages dir).
OLD_PROST = ('  failed to invoke protoc (hint: https://docs.rs/prost-build/#sourcing-protoc): '
             'Os { code: 2, kind: NotFound, message: "No such file or directory" }')
PROTOC_PATH_GONE = '  Error: "/work/.packages/protoc/bin/protoc": No such file or directory (os error 2)'
# A protoc that is there but cannot be run (not executable in the worktree) fails the same step.
OLD_PROST_DENIED = ('  failed to invoke protoc (hint: https://docs.rs/prost-build/#sourcing-protoc): '
                    'Os { code: 13, kind: PermissionDenied, message: "Permission denied" }')


def _log(tmp_path, *lines):
    log = tmp_path / "floor.log"
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return log


def test_a_build_script_that_cannot_find_protoc_is_a_missing_prerequisite():
    out = X.suite_outcome(_suite(101), FIXTURES / "cargo-protoc-missing.log")
    assert out["outcome"] == X.SUITE_PREREQ_MISSING == "build_prerequisite_missing"
    assert out["prerequisite"] == "protoc" and out["error_codes"] == {}
    assert X.describe_suite(out) == "build_prerequisite_missing(protoc)"


@pytest.mark.parametrize("line", [OLD_PROST, OLD_PROST_DENIED, PROTOC_PATH_GONE],
                         ids=["failed-to-invoke", "failed-to-invoke-denied", "path-gone"])
def test_every_protoc_wording_after_a_build_script_failure_is_the_prerequisite(tmp_path, line):
    out = X.suite_outcome(_suite(101), _log(tmp_path, BUILD_SCRIPT_FAILED, "", "Caused by:", line))
    assert (out["outcome"], out["prerequisite"]) == (X.SUITE_PREREQ_MISSING, "protoc")


def test_a_build_script_failure_that_names_no_protoc_stays_failed(tmp_path):
    out = X.suite_outcome(_suite(101), _log(tmp_path, BUILD_SCRIPT_FAILED, "  thread 'main' panicked at build.rs:3:5:",
                                            "  bindgen could not find libclang"))
    assert (out["outcome"], out["prerequisite"]) == (X.SUITE_FAILED, None)


def test_a_real_compile_error_stays_does_not_compile_beside_a_protoc_line(tmp_path):
    compile_log = (FIXTURES / "cargo-compile-error.log").read_text(encoding="utf-8").splitlines()
    out = X.suite_outcome(_suite(101), _log(tmp_path, "note: protoc found at /usr/bin/protoc", *compile_log))
    assert (out["outcome"], out["prerequisite"]) == (X.SUITE_NO_COMPILE, None)


def test_a_test_that_prints_a_protoc_failure_is_a_test_failure_not_a_prerequisite(tmp_path):
    runtime = (FIXTURES / "cargo-test-failed.log").read_text(encoding="utf-8").splitlines()
    out = X.suite_outcome(_suite(101), _log(tmp_path, OLD_PROST, *runtime))
    assert (out["outcome"], out["prerequisite"]) == (X.SUITE_TESTS_FAILED, None)


def test_protoc_lines_in_a_passing_run_do_not_trigger(tmp_path):
    out = X.suite_outcome(_suite(0), _log(tmp_path, BUILD_SCRIPT_FAILED, OLD_PROST,
                                          "test result: ok. 3 passed; 0 failed; 0 ignored"))
    assert (out["outcome"], out["prerequisite"]) == (X.SUITE_PASSED, None)


def test_the_gate_step_is_classified_the_same_way():
    gate = {"name": "gate", "rc": 101, "error": None}
    out = X.step_outcome(gate, FIXTURES / "cargo-protoc-missing.log")
    assert (out["outcome"], out["prerequisite"]) == (X.SUITE_PREREQ_MISSING, "protoc")
    assert X.step_outcome(None, FIXTURES / "cargo-protoc-missing.log") is None


# --- the text line -------------------------------------------------------------------------------

@pytest.mark.parametrize(("subagents", "text"), [
    (None, "-"), ({"transcripts": 0, "max_concurrent": 0, "untimed": 0}, "0"),
    ({"transcripts": 5, "max_concurrent": 3, "untimed": 0}, "5(max 3 at once)"),
    ({"transcripts": 5, "max_concurrent": 3, "untimed": 1}, "5(max 3 at once, 1 untimed)")])
def test_describe_subagents(subagents, text):
    assert X.describe_subagents(subagents) == text


def test_describe_ideas_and_suite():
    assert X.describe_ideas(None) == "-" and X.describe_ideas({"writes": 0, "ideas": {}}) == "none"
    ideas = {"writes": 3, "ideas": {"1": {"count": 2, "first": "a"}, "3": {"count": 1, "first": "b"}}}
    assert X.describe_ideas(ideas) == "1x2,3x1"
    assert X.describe_suite(None) == "-"
    compile_ = X.suite_outcome(_suite(101), FIXTURES / "cargo-compile-error.log")
    assert X.describe_suite(compile_) == (
        "does_not_compile(E0308x1,E0425x1,E0432x2; missing sbx::policy::Policy,run_sandboxed,sbx::mount::Bind)")
    runtime = X.suite_outcome(_suite(101), FIXTURES / "cargo-test-failed.log")
    assert X.describe_suite(runtime) == "tests_failed(2 of 10)"
