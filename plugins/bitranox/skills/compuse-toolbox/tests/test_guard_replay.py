"""Tests for guard_replay.py - replay real Bash calls through a guard predicate. ASCII."""
import json

import guard_replay as G


def _mk(recs):
    return "\n".join(json.dumps(r) for r in recs) + "\n"


def _use(tid, command, cwd="/repo", tool="Bash"):
    return {"type": "assistant", "cwd": cwd,
            "message": {"content": [{"type": "tool_use", "id": tid, "name": tool,
                                     "input": {"command": command}}]}}


def _result(tid, text, is_error=True):
    return {"type": "user",
            "message": {"content": [{"type": "tool_result", "tool_use_id": tid,
                                     "is_error": is_error, "content": text}]}}


# --- extracting the calls ---------------------------------------------------------------------
# The cwd is not decoration: a guard judging paths answers differently per session directory, so a
# replay that drops it measures a different question than the one the guard is asked at runtime.

def test_extract_calls_carries_the_cwd_the_command_ran_under():
    calls = G.extract_calls(_mk([_use("t1", "git status", cwd="/srv/project")]))
    assert len(calls) == 1
    assert calls[0]["cwd"] == "/srv/project"


def test_extract_calls_joins_the_error_result_to_its_call():
    calls = G.extract_calls(_mk([_use("t1", "git commit"), _result("t1", "boom")]))
    assert calls[0]["error"] == "boom"


def test_extract_calls_leaves_a_successful_call_with_no_error():
    calls = G.extract_calls(_mk([_use("t1", "git status"), _result("t1", "fine", is_error=False)]))
    assert calls[0]["error"] is None


def test_extract_calls_ignores_other_tools():
    assert G.extract_calls(_mk([_use("t1", "x", tool="Read")])) == []


def test_malformed_line_is_skipped_not_fatal():
    text = json.dumps(_use("t1", "git status")) + "\nNOT JSON\n"
    assert len(G.extract_calls(text)) == 1


# --- the load-bearing distinction -------------------------------------------------------------
# Precision counts only the calls a GATE refused. An ordinary non-zero exit is a command that ran
# and failed, which a guard firing earlier would not have saved anybody from.

def test_a_gate_block_is_recognised():
    assert G.is_gate_block("PreToolUse:Bash hook error: repo-gate: commit/push blocked") is True


def test_an_ordinary_command_failure_is_not_a_gate_block():
    assert G.is_gate_block("bash: frobnicate: command not found") is False


def test_no_error_at_all_is_not_a_gate_block():
    assert G.is_gate_block(None) is False


# --- rate and precision are two questions -----------------------------------------------------
# The measured failure this jig exists for: a guard was shipped after checking only how OFTEN it
# spoke. 131 of its 344 firings turned out to have nothing to warn about.

def test_classify_reports_rate_and_precision_as_different_numbers():
    calls = [
        {"id": "a", "command": "fire", "cwd": "/r", "error": "PreToolUse:Bash hook error: nope"},
        {"id": "b", "command": "fire", "cwd": "/r", "error": None},
        {"id": "c", "command": "fire", "cwd": "/r", "error": None},
        {"id": "d", "command": "quiet", "cwd": "/r", "error": None},
    ]
    report = G.classify(calls, lambda cmd: "fire" in cmd)
    assert report["commands"] == 4
    assert report["fires"] == 3
    assert report["fire_rate_pct"] == 75.0
    assert report["blocked"] == 1
    assert report["precision_pct"] == 33.33


def test_a_predicate_that_never_fires_reports_precision_as_none():
    calls = [{"id": "a", "command": "x", "cwd": "/r", "error": None}]
    report = G.classify(calls, lambda cmd: False)
    assert report["fires"] == 0
    assert report["precision_pct"] is None


def test_a_two_argument_predicate_is_called_with_the_cwd():
    seen = []
    calls = [{"id": "a", "command": "git status", "cwd": "/srv/here", "error": None}]
    G.classify(calls, lambda cmd, cwd: seen.append(cwd) or False)
    assert seen == ["/srv/here"]


def test_a_predicate_that_raises_does_not_abort_the_replay():
    calls = [{"id": "a", "command": "boom", "cwd": "/r", "error": None},
             {"id": "b", "command": "fire", "cwd": "/r", "error": None}]

    def flaky(cmd):
        if cmd == "boom":
            raise ValueError("bad input")
        return True

    report = G.classify(calls, flaky)
    assert report["fires"] == 1
    assert report["predicate_errors"] == 1


def test_the_sample_is_spread_across_the_corpus_not_the_first_n():
    """A first-N sample clusters by walk order, which is by project, and reads as representative.

    Measured 2026-08-30: reading 40 of 557 firings this way put a residual at ~10 percent because
    the 40 came almost entirely from one project that scripts heavily; classifying all 557 put it
    at ~2 percent, and the full set held four shapes the 40 did not contain at all. The sample is
    what a reader judges the firings from, so drawing it from one end of the corpus is the half
    that turns a volume figure into a wrong conclusion.
    """
    calls = [{"id": str(i), "command": "fire %03d" % i, "cwd": "/r", "error": None}
             for i in range(100)]
    got = [s["command"] for s in G.classify(calls, lambda cmd: True, sample=5)["samples"]]

    assert got != ["fire %03d" % i for i in range(5)], "sample is still the first N"
    assert len(got) == 5
    assert got == sorted(got), "corpus order must be preserved within the sample"
    # It must actually REACH the far end - that is the whole point.
    assert int(got[-1].split()[1]) >= 80, "sample never reaches the end of the corpus: %s" % got
    assert len(set(got)) == 5, "sample repeats a firing"


def test_a_sample_larger_than_the_firings_returns_them_all():
    calls = [{"id": "a", "command": "fire one", "cwd": "/r", "error": None},
             {"id": "b", "command": "quiet", "cwd": "/r", "error": None}]
    report = G.classify(calls, lambda cmd: cmd.startswith("fire"), sample=5)
    assert [s["command"] for s in report["samples"]] == ["fire one"]


def test_samples_carry_the_firing_commands_for_eyeballing():
    calls = [{"id": "a", "command": "fire one", "cwd": "/r", "error": None},
             {"id": "b", "command": "quiet", "cwd": "/r", "error": None}]
    report = G.classify(calls, lambda cmd: cmd.startswith("fire"), sample=5)
    assert [s["command"] for s in report["samples"]] == ["fire one"]


# --- loading the predicate --------------------------------------------------------------------
# Hook modules are hyphenated and therefore not importable by name, which is exactly the shape
# this jig is pointed at most often.

def test_a_hyphenated_module_can_still_be_loaded(tmp_path):
    mod = tmp_path / "my-guard.py"
    mod.write_text("def notice(command):\n    return 'yes' if 'x' in command else None\n",
                   encoding="utf-8")
    fn = G.load_predicate(str(mod), "notice")
    assert fn("axb") == "yes"


def test_a_missing_function_is_named_rather_than_an_attribute_error(tmp_path):
    mod = tmp_path / "g.py"
    mod.write_text("def other(command):\n    return None\n", encoding="utf-8")
    try:
        G.load_predicate(str(mod), "notice")
    except G.UsageError as exc:
        assert "notice" in str(exc)
    else:
        raise AssertionError("expected UsageError")


# --- the empty-corpus trap --------------------------------------------------------------------
# "The guard never fires" and "I never looked" print the same, so an unread corpus must be loud.

def test_an_empty_corpus_is_reported_as_unread(tmp_path):
    report = G.replay(str(tmp_path), lambda cmd: True)
    assert report["files_read"] == 0
    assert report["commands"] == 0


def test_replay_reads_every_jsonl_below_the_root(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "one.jsonl").write_text(_mk([_use("t1", "fire")]), encoding="utf-8")
    (tmp_path / "two.jsonl").write_text(_mk([_use("t2", "quiet")]), encoding="utf-8")
    report = G.replay(str(tmp_path), lambda cmd: cmd == "fire")
    assert report["files_read"] == 2
    assert report["commands"] == 2
    assert report["fires"] == 1


def test_exit_code_separates_never_fired_from_empty_corpus(tmp_path):
    (tmp_path / "one.jsonl").write_text(_mk([_use("t1", "quiet")]), encoding="utf-8")
    assert G.exit_code(G.replay(str(tmp_path), lambda cmd: False)) == 1
    empty = tmp_path / "empty"
    empty.mkdir()
    assert G.exit_code(G.replay(str(empty), lambda cmd: False)) == 3


# --- the same call recorded twice --------------------------------------------------------------
# Resuming or forking a session copies the earlier transcript into a new file, so one real call
# can sit in two .jsonl files under the same tool_use id. Counting it twice inflates the
# denominator and deflates the rate, and it does so silently - the corpus just looks bigger.

def test_the_same_call_in_two_transcripts_counts_once(tmp_path):
    (tmp_path / "original.jsonl").write_text(_mk([_use("shared", "fire")]), encoding="utf-8")
    (tmp_path / "resumed.jsonl").write_text(_mk([_use("shared", "fire"), _use("new", "quiet")]),
                                            encoding="utf-8")
    report = G.replay(str(tmp_path), lambda cmd: cmd == "fire")
    assert report["commands"] == 2
    assert report["fires"] == 1
    assert report["duplicates_skipped"] == 1


def test_calls_with_no_id_are_not_collapsed_into_one(tmp_path):
    rec = {"type": "assistant", "cwd": "/r",
           "message": {"content": [{"type": "tool_use", "name": "Bash",
                                    "input": {"command": "a"}},
                                   {"type": "tool_use", "name": "Bash",
                                    "input": {"command": "b"}}]}}
    (tmp_path / "one.jsonl").write_text(_mk([rec]), encoding="utf-8")
    report = G.replay(str(tmp_path), lambda cmd: True)
    assert report["commands"] == 2


# ---- the second positional argument is chosen by NAME, not by arity ------------------------------
#
# Measured 2026-08-30. `_wants_cwd` asked only "does this take two positional parameters?", so a
# hook whose real signature is `notice(command, tool_name=None)` - the house shape across the
# bitranox hooks - was handed the CWD in its tool_name slot. It did not crash: an unrecognised tool
# takes the strict fallback, so the replay silently measured a code path production never runs, and
# reported a fire rate for it. Deciding by the parameter's NAME is what makes the forwarding mean
# what it says.

def test_a_tool_name_parameter_receives_the_tool_not_the_cwd():
    seen = []
    calls = [{"id": "a", "command": "git status", "cwd": "/srv/here", "error": None}]
    G.classify(calls, lambda command, tool_name: seen.append(tool_name) or False, tool="Bash")
    assert seen == ["Bash"], "a tool_name parameter must get the tool, never the cwd"


def test_the_tool_forwarded_is_the_one_being_replayed():
    seen = []
    calls = [{"id": "a", "command": "Get-Item x", "cwd": "/srv/here", "error": None}]
    G.classify(calls, lambda command, tool_name: seen.append(tool_name) or False, tool="PowerShell")
    assert seen == ["PowerShell"]


def test_a_cwd_parameter_still_receives_the_cwd():
    """The direction that must NOT change."""
    seen = []
    calls = [{"id": "a", "command": "git status", "cwd": "/srv/here", "error": None}]
    G.classify(calls, lambda cmd, cwd: seen.append(cwd) or False)
    assert seen == ["/srv/here"]


def test_an_unrecognised_second_parameter_is_not_filled_in():
    """`bracket_leaks(cmd, haystack=None)` is a real shape in this plugin, and a cwd in its
    haystack slot would quietly change what the guard searches. Only names we understand get
    forwarded; anything else is called with the command alone."""
    seen = []
    calls = [{"id": "a", "command": "git status", "cwd": "/srv/here", "error": None}]
    G.classify(calls, lambda cmd, haystack=None: seen.append(haystack) or False)
    assert seen == [None], "an unknown second parameter must be left at its default"


def test_the_report_names_which_second_argument_was_forwarded():
    """A silent choice here is what made the wrong number unnoticeable, so the run states it."""
    calls = [{"id": "a", "command": "git status", "cwd": "/srv/here", "error": None}]
    assert G.classify(calls, lambda command, tool_name: False)["forwarded_second_arg"] == "tool_name"
    assert G.classify(calls, lambda cmd, cwd: False)["forwarded_second_arg"] == "cwd"
    assert G.classify(calls, lambda cmd: False)["forwarded_second_arg"] is None


# ---- an unrecognised second parameter is announced, not silently dropped ------------------------
#
# Choosing by name means a predicate whose second parameter is `haystack` now gets ONE argument
# where it used to get the cwd. That is the right call and it changes results on upgrade, so it
# says so. The whole reason this fix exists is a wrong number that arrived quietly; shipping a
# second quiet change in the same commit would repeat the defect one level up.

def test_an_unrecognised_second_parameter_warns_on_stderr(capsys):
    calls = [{"id": "a", "command": "git status", "cwd": "/srv/here", "error": None}]
    G.classify(calls, lambda cmd, haystack=None: False)
    err = capsys.readouterr().err
    assert "haystack" in err, "the warning must NAME the parameter being dropped"


def test_the_warning_never_touches_stdout(capsys):
    """stdout carries the JSON envelope; a warning there would corrupt a parsed run."""
    calls = [{"id": "a", "command": "git status", "cwd": "/srv/here", "error": None}]
    G.classify(calls, lambda cmd, haystack=None: False)
    assert capsys.readouterr().out == ""


def test_a_recognised_second_parameter_is_not_warned_about(capsys):
    """The direction where it must NOT fire - twice, because both names are recognised."""
    calls = [{"id": "a", "command": "git status", "cwd": "/srv/here", "error": None}]
    G.classify(calls, lambda command, tool_name: False)
    G.classify(calls, lambda cmd, cwd: False)
    assert capsys.readouterr().err == ""


def test_a_single_argument_predicate_is_not_warned_about(capsys):
    """Nothing is being dropped, so there is nothing to say."""
    calls = [{"id": "a", "command": "git status", "cwd": "/srv/here", "error": None}]
    G.classify(calls, lambda cmd: False)
    assert capsys.readouterr().err == ""


def test_the_warning_is_emitted_once_not_per_call():
    """66,000 copies of one warning is the same as no warning."""
    calls = [{"id": str(n), "command": "git status", "cwd": "/x", "error": None}
             for n in range(50)]
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        G.classify(calls, lambda cmd, haystack=None: False)
    assert buf.getvalue().count("haystack") == 1


# --- payload per tool -------------------------------------------------------------------------
# `--tool` used to accept any name while the extractor only ever read `input.command`, which only
# Bash has. The run does not go quiet - it exits 3 saying "read 2332 file(s) and found no Write
# calls - nothing was replayed" - but that sentence blames the CORPUS for an emptiness the
# EXTRACTOR caused, so the reader concludes their history holds no writes rather than that the
# question could not be asked. Measured 2026-09-03: an always-true control over the same corpus
# fired 76649 times on Bash and 0 times on Write and on Edit.


def _use_write(tid, content, cwd="/repo"):
    return {"type": "assistant", "cwd": cwd,
            "message": {"content": [{"type": "tool_use", "id": tid, "name": "Write",
                                     "input": {"file_path": "/repo/x.md", "content": content}}]}}


def _use_edit(tid, new_string, cwd="/repo"):
    return {"type": "assistant", "cwd": cwd,
            "message": {"content": [{"type": "tool_use", "id": tid, "name": "Edit",
                                     "input": {"file_path": "/repo/x.md",
                                               "old_string": "before", "new_string": new_string}}]}}


def test_a_write_call_yields_the_text_it_would_write():
    calls = G.extract_calls(_mk([_use_write("t1", "39 of 40 candidates")]), tool="Write")
    assert [c["command"] for c in calls] == ["39 of 40 candidates"]


def test_an_edit_call_yields_the_replacement_text_not_the_replaced_text():
    calls = G.extract_calls(_mk([_use_edit("t1", "the new claim")]), tool="Edit")
    assert [c["command"] for c in calls] == ["the new claim"], \
        "a guard judges what is about to be written, so the payload is new_string"


def test_the_bash_path_is_unchanged():
    calls = G.extract_calls(_mk([_use("t1", "git status")]), tool="Bash")
    assert [c["command"] for c in calls] == ["git status"]


def test_a_write_still_carries_its_cwd_and_its_error():
    text = _mk([_use_write("t1", "body", cwd="/srv/p"), _result("t1", "denied by hook")])
    call = G.extract_calls(text, tool="Write")[0]
    assert call["cwd"] == "/srv/p" and call["error"] == "denied by hook"


def test_a_call_missing_its_payload_field_is_skipped_not_fatal():
    rec = {"type": "assistant", "cwd": "/repo",
           "message": {"content": [{"type": "tool_use", "id": "t1", "name": "Write",
                                    "input": {"file_path": "/repo/x.md"}}]}}
    assert G.extract_calls(_mk([rec, _use_write("t2", "kept")]), tool="Write") != []


def test_an_unsupported_tool_is_a_REFUSAL_not_an_empty_result():
    """The property that stops this defect recurring under a different tool name.

    Returning [] for a tool nobody taught the extractor about is indistinguishable from a corpus
    that genuinely contains none, and the caller reports the second. A name it cannot read must
    say so instead of answering zero.
    """
    try:
        G.extract_calls(_mk([_use("t1", "git status")]), tool="Glob")
    except G.UnsupportedTool as exc:
        assert "Glob" in str(exc) and "Bash" in str(exc), \
            "the refusal must name the tool asked for and the tools it does know"
    else:
        raise AssertionError("an unreadable tool name must refuse, never answer 0")


def test_every_supported_tool_actually_extracts_something():
    """A control: each entry in the payload map must be reachable, or the map documents a tool
    the extractor still cannot read - the same silent zero wearing a table."""
    builders = {"Bash": lambda: _use("t", "cmd"),
                "Write": lambda: _use_write("t", "text"),
                "Edit": lambda: _use_edit("t", "text")}
    for tool in G.TOOL_PAYLOAD:
        assert tool in builders, f"no fixture for supported tool {tool}"
        assert G.extract_calls(_mk([builders[tool]()]), tool=tool), \
            f"{tool} is listed as supported but extracted nothing"


def test_the_cli_refuses_an_unknown_tool_with_exit_2_not_a_traceback(tmp_path, capsys):
    """A library-level raise is only half the fix: uncaught, the CLI dies with a traceback, which
    is a worse answer than the wrong one it replaced. Exit 2 and a readable line on stderr."""
    mod = tmp_path / "p.py"
    mod.write_text("def notice(command):\n    return True\n", encoding="utf-8")
    corpus = tmp_path / "c.jsonl"
    corpus.write_text("", encoding="utf-8")
    rc = G.main(["--module", str(mod), "--tool", "Glob", "--root", str(corpus)])
    assert rc == 2, "an unreadable tool name is a usage refusal"
    err = capsys.readouterr().err
    assert "Glob" in err and "Bash" in err, err
