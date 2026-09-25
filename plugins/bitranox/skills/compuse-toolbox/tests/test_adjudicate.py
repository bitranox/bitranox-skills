"""Tests for adjudicate.py. ASCII only.

The three-bucket verdict is the whole point of the tool, so it gets the most cases: a harness that
folds "the control did not discriminate" into "refuted" reports a clean sweep over broken controls,
which is what this replaces.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import adjudicate as A

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "adjudicate.py"


# ---- the three buckets -------------------------------------------------------------------------

def test_probe_fires_and_control_does_not_is_confirmed():
    assert A.verdict_for(probe_fired=True, control_fired=False) == "CONFIRMED"


def test_probe_does_not_fire_is_refuted():
    assert A.verdict_for(probe_fired=False, control_fired=False) == "REFUTED"


def test_both_fire_is_unusable_not_refuted():
    """The distinction the harness exists to keep. Folding this into REFUTED reported 10 refuted
    where the truth was 7 refuted plus 3 unusable."""
    assert A.verdict_for(probe_fired=True, control_fired=True) == "UNUSABLE"


def test_a_control_that_fires_while_the_probe_does_not_is_still_refuted():
    """The claim said the probe fires. It did not, so the claim is wrong whatever the control did."""
    assert A.verdict_for(probe_fired=False, control_fired=True) == "REFUTED"


# ---- what counts as FIRED ----------------------------------------------------------------------

def test_output_mode_counts_any_stream():
    assert A.fired(A.Run(0, "something", ""), "output", None) is True
    assert A.fired(A.Run(0, "", "something"), "output", None) is True
    assert A.fired(A.Run(0, "", ""), "output", None) is False


def test_output_mode_ignores_whitespace_only_output():
    assert A.fired(A.Run(0, "  \n ", ""), "output", None) is False


def test_nonzero_mode_reads_the_exit_code_only():
    assert A.fired(A.Run(2, "", ""), "nonzero", None) is True
    assert A.fired(A.Run(0, "loud but allowed", ""), "nonzero", None) is False


def test_match_mode_searches_both_streams():
    assert A.fired(A.Run(0, "BLOCKED: nope", ""), "match", "BLOCKED") is True
    assert A.fired(A.Run(2, "", "BLOCKED: nope"), "match", "BLOCKED") is True
    assert A.fired(A.Run(2, "other text", ""), "match", "BLOCKED") is False


# ---- driving a real subject --------------------------------------------------------------------

def _fake_hook(tmp_path, body):
    p = tmp_path / "fake_hook.py"
    p.write_text("import sys\n" + body, encoding="utf-8")
    return p


def test_a_discriminating_subject_confirms(tmp_path):
    hook = _fake_hook(tmp_path, 'data = sys.stdin.read()\nif "TRAP" in data: print("fired")\n')
    claim = A.Claim(name="c1", probe="has TRAP here", control="has nothing here")
    result = A.adjudicate(A.subject_for_hook(hook), [claim], "output", None)[0]
    assert result.verdict == "CONFIRMED"


def test_a_subject_that_never_fires_refutes(tmp_path):
    hook = _fake_hook(tmp_path, "sys.stdin.read()\n")
    claim = A.Claim(name="c1", probe="has TRAP here", control="has nothing here")
    assert A.adjudicate(A.subject_for_hook(hook), [claim], "output", None)[0].verdict == "REFUTED"


def test_a_subject_that_always_fires_is_unusable_not_refuted(tmp_path):
    """A guard that fires on everything looks CONFIRMED to a two-bucket harness."""
    hook = _fake_hook(tmp_path, 'sys.stdin.read()\nprint("fired")\n')
    claim = A.Claim(name="c1", probe="has TRAP here", control="has nothing here")
    assert A.adjudicate(A.subject_for_hook(hook), [claim], "output", None)[0].verdict == "UNUSABLE"


def test_per_claim_args_reach_the_subject(tmp_path):
    hook = _fake_hook(tmp_path, 'if "TRAP" in " ".join(sys.argv[1:]): print("fired")\n')
    claim = A.Claim(name="c1", probe="", control="", probe_args=["TRAP"], control_args=["clean"])
    assert A.adjudicate(A.subject_for_hook(hook), [claim], "output", None)[0].verdict == "CONFIRMED"


# ---- summary and exit codes --------------------------------------------------------------------

def test_summary_counts_each_bucket_separately():
    results = [
        A.Adjudication("a", "CONFIRMED", A.Run(0), A.Run(0), True, False),
        A.Adjudication("b", "REFUTED", A.Run(0), A.Run(0), False, False),
        A.Adjudication("c", "UNUSABLE", A.Run(0), A.Run(0), True, True),
    ]
    s = A.summarize(results)
    assert (s["confirmed"], s["refuted"], s["unusable"], s["total"]) == (1, 1, 1, 3)
    assert s["unusable_names"] == ["c"]


def test_an_unusable_claim_makes_the_run_not_ok():
    results = [A.Adjudication("c", "UNUSABLE", A.Run(0), A.Run(0), True, True)]
    assert A.summarize(results)["ok"] is False


def test_all_refuted_is_still_ok_because_the_instrument_worked():
    results = [A.Adjudication("b", "REFUTED", A.Run(0), A.Run(0), False, False)]
    assert A.summarize(results)["ok"] is True


def test_cli_exits_1_when_a_control_did_not_discriminate(tmp_path):
    hook = _fake_hook(tmp_path, 'sys.stdin.read()\nprint("always")\n')
    rc = A.main(["--hook", str(hook), "--name", "c1", "--probe", "TRAP", "--control", "clean"])
    assert rc == 1


def test_cli_exits_0_when_every_claim_was_adjudicable(tmp_path):
    hook = _fake_hook(tmp_path, 'data = sys.stdin.read()\nif "TRAP" in data: print("fired")\n')
    rc = A.main(["--hook", str(hook), "--name", "c1", "--probe", "TRAP", "--control", "clean"])
    assert rc == 0


def test_cli_exits_2_without_a_subject():
    assert A.main(["--name", "c1", "--probe", "x", "--control", "y"]) == 2


def test_cli_exits_2_on_an_unreadable_claim_file(tmp_path):
    hook = _fake_hook(tmp_path, "sys.stdin.read()\n")
    assert A.main(["--hook", str(hook), "--claim-file", str(tmp_path / "nope.jsonl")]) == 2


def test_cli_exits_2_when_no_claims_were_given(tmp_path):
    hook = _fake_hook(tmp_path, "sys.stdin.read()\n")
    assert A.main(["--hook", str(hook)]) == 2


def test_match_mode_requires_a_pattern(tmp_path):
    hook = _fake_hook(tmp_path, "sys.stdin.read()\n")
    rc = A.main(["--hook", str(hook), "--name", "c", "--probe", "a", "--control", "b",
                 "--fired-when", "match"])
    assert rc == 2


# ---- claim files -------------------------------------------------------------------------------

def test_a_claim_file_is_read_as_jsonl(tmp_path):
    f = tmp_path / "claims.jsonl"
    f.write_text('{"name":"one","probe":"TRAP","control":"clean"}\n'
                 '\n'
                 '{"name":"two","probe":"TRAP2","control":"clean"}\n', encoding="utf-8")
    claims = A.load_claims(str(f), None, None, None)
    assert [c.name for c in claims] == ["one", "two"]


def test_a_claim_file_line_missing_control_is_rejected(tmp_path):
    f = tmp_path / "claims.jsonl"
    f.write_text('{"name":"one","probe":"TRAP"}\n', encoding="utf-8")
    with pytest.raises(ValueError):
        A.load_claims(str(f), None, None, None)


# ---- the machine-readable envelope ---------------------------------------------------------------

def test_json_envelope_shape(tmp_path, capsys):
    hook = _fake_hook(tmp_path, 'data = sys.stdin.read()\nif "TRAP" in data: print("fired")\n')
    A.main(["--hook", str(hook), "--name", "c1", "--probe", "TRAP", "--control", "clean", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert payload["command"] == "adjudicate"
    assert payload["ok"] is True
    assert payload["data"]["summary"]["confirmed"] == 1
    assert payload["data"]["results"][0]["verdict"] == "CONFIRMED"


def test_json_still_emitted_on_failure(tmp_path, capsys):
    hook = _fake_hook(tmp_path, 'sys.stdin.read()\nprint("always")\n')
    rc = A.main(["--hook", str(hook), "--name", "c1", "--probe", "TRAP", "--control", "clean",
                 "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 1 and payload["ok"] is False


def test_the_unusable_warning_goes_to_stderr_not_stdout(tmp_path, capsys):
    hook = _fake_hook(tmp_path, 'sys.stdin.read()\nprint("always")\n')
    A.main(["--hook", str(hook), "--name", "c1", "--probe", "TRAP", "--control", "clean", "--json"])
    captured = capsys.readouterr()
    json.loads(captured.out)                      # stdout stays a clean envelope
    assert "UNUSABLE" in captured.err


# ---- runs as a program -------------------------------------------------------------------------

def test_runs_as_a_subprocess(tmp_path):
    hook = _fake_hook(tmp_path, 'data = sys.stdin.read()\nif "TRAP" in data: print("fired")\n')
    res = subprocess.run([sys.executable, str(SCRIPT), "--hook", str(hook), "--name", "c",
                          "--probe", "TRAP", "--control", "clean"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert res.returncode == 0
    assert "CONFIRMED" in res.stdout


# ---- telling a broken control from a chatty subject ---------------------------------------------
#
# Both produce UNUSABLE, and the original message named only the first, which would send a reader to
# fix a control that was never wrong. The distinguishing signal is already in hand: one broken
# control is a control problem, EVERY claim unusable is the subject firing on everything.

def test_one_unusable_among_several_blames_the_control():
    results = [
        A.Adjudication("a", "CONFIRMED", A.Run(0), A.Run(0), True, False),
        A.Adjudication("b", "UNUSABLE", A.Run(0), A.Run(0), True, True),
    ]
    assert A.unusable_cause(A.summarize(results)) == "control"


def test_every_claim_unusable_blames_the_subject():
    results = [
        A.Adjudication("a", "UNUSABLE", A.Run(0), A.Run(0), True, True),
        A.Adjudication("b", "UNUSABLE", A.Run(0), A.Run(0), True, True),
    ]
    assert A.unusable_cause(A.summarize(results)) == "subject"


def test_a_single_claim_that_is_unusable_blames_the_control_not_the_subject():
    """One claim is not evidence of a pattern - with n=1 there is nothing to distinguish."""
    results = [A.Adjudication("a", "UNUSABLE", A.Run(0), A.Run(0), True, True)]
    assert A.unusable_cause(A.summarize(results)) == "control"


def test_no_unusable_has_no_cause():
    results = [A.Adjudication("a", "CONFIRMED", A.Run(0), A.Run(0), True, False)]
    assert A.unusable_cause(A.summarize(results)) is None


def test_the_all_unusable_warning_names_the_subject_and_the_fired_when_flag(tmp_path, capsys):
    hook = _fake_hook(tmp_path, 'sys.stdin.read()\nprint("banner on every run")\n')
    f = tmp_path / "claims.jsonl"
    f.write_text('{"name":"one","probe":"TRAP","control":"clean"}\n'
                 '{"name":"two","probe":"TRAP2","control":"clean"}\n', encoding="utf-8")
    A.main(["--hook", str(hook), "--claim-file", str(f)])
    err = capsys.readouterr().err
    assert "subject" in err
    assert "--fired-when" in err


def test_the_partial_unusable_warning_still_points_at_the_control(tmp_path, capsys):
    hook = _fake_hook(tmp_path, 'data = sys.stdin.read()\nif "TRAP" in data or "BOTH" in data: print("f")\n')
    f = tmp_path / "claims.jsonl"
    f.write_text('{"name":"good","probe":"TRAP","control":"clean"}\n'
                 '{"name":"bad","probe":"TRAP","control":"BOTH"}\n', encoding="utf-8")
    A.main(["--hook", str(hook), "--claim-file", str(f)])
    err = capsys.readouterr().err
    # The control-branch wording, and the claim it names: a bare "control" also appears in the
    # subject-branch message ("including every control"), so it could not tell the two apart.
    assert "the control fired too" in err
    assert "bad" in err
    assert "the subject fired on every input" not in err


# ---- a harness failure is its own bucket, never "fired" ----------------------------------------

def _hanging_hook(tmp_path):
    return _fake_hook(tmp_path, 'import time\ndata = sys.stdin.read()\n'
                                'if "HANG" in data: time.sleep(30)\n')


def test_a_timed_out_probe_is_error_not_confirmed(tmp_path):
    claim = A.Claim(name="c", probe="HANG", control="clean")
    result = A.adjudicate(A.subject_for_hook(_hanging_hook(tmp_path)), [claim], "output", None,
                          timeout=1)[0]
    assert result.verdict == "ERROR"
    assert result.probe_fired is False


@pytest.mark.parametrize("mode", ["output", "nonzero"])
def test_cli_exits_2_when_the_probe_times_out(tmp_path, capsys, mode):
    rc = A.main(["--hook", str(_hanging_hook(tmp_path)), "--name", "c", "--probe", "HANG",
                 "--control", "clean", "--timeout", "1", "--fired-when", mode])
    cap = capsys.readouterr()
    assert rc == 2
    assert "CONFIRMED" not in cap.out
    assert "ERROR" in cap.out and "timed out" in cap.err


def test_a_timed_out_control_is_error_too(tmp_path):
    hook = _fake_hook(tmp_path, 'import time\ndata = sys.stdin.read()\n'
                                'if "TRAP" in data: print("f")\nif "HANG" in data: time.sleep(30)\n')
    claim = A.Claim(name="c", probe="TRAP", control="HANG")
    result = A.adjudicate(A.subject_for_hook(hook), [claim], "output", None, timeout=1)[0]
    assert result.verdict == "ERROR"


def test_a_subject_that_cannot_be_launched_is_error(tmp_path):
    claim = A.Claim(name="c", probe="x", control="y")
    result = A.adjudicate([str(tmp_path / "no-such-interpreter")], [claim], "nonzero", None)[0]
    assert result.verdict == "ERROR"
    assert "cannot run subject" in result.probe_run.harness_error


def test_a_subject_that_itself_exits_124_is_still_scored(tmp_path):
    """Only the HARNESS failing is an error; a subject's own exit code is data."""
    hook = _fake_hook(tmp_path, 'data = sys.stdin.read()\nif "TRAP" in data: sys.exit(124)\n')
    claim = A.Claim(name="c", probe="TRAP", control="clean")
    assert A.adjudicate(A.subject_for_hook(hook), [claim], "nonzero", None)[0].verdict == "CONFIRMED"


def test_summary_counts_errors_and_is_not_ok():
    results = [A.Adjudication("e", "ERROR", A.Run(124, harness_error="timed out"), A.Run(0),
                              False, False)]
    s = A.summarize(results)
    assert (s["error"], s["error_names"], s["ok"]) == (1, ["e"], False)


# ---- claim-file validation ---------------------------------------------------------------------

def test_an_object_valued_probe_is_serialised_as_json(tmp_path):
    f = tmp_path / "claims.jsonl"
    f.write_text('{"name":"o","probe":{"tool_input":{"command":"TRAP"}},"control":"clean"}\n',
                 encoding="utf-8")
    claim = A.load_claims(str(f), None, None, None)[0]
    assert json.loads(claim.probe) == {"tool_input": {"command": "TRAP"}}


def test_an_object_valued_probe_runs_end_to_end(tmp_path, capsys):
    hook = _fake_hook(tmp_path, 'data = sys.stdin.read()\nif "TRAP" in data: print("fired")\n')
    f = tmp_path / "claims.jsonl"
    f.write_text('{"name":"o","probe":{"tool_input":{"command":"TRAP"}},'
                 '"control":{"tool_input":{"command":"x"}}}\n', encoding="utf-8")
    assert A.main(["--hook", str(hook), "--claim-file", str(f)]) == 0
    assert "CONFIRMED" in capsys.readouterr().out


@pytest.mark.parametrize("bad", ["42", "null", "true", "[1]"])
def test_a_non_string_non_object_probe_is_rejected(tmp_path, bad):
    f = tmp_path / "claims.jsonl"
    f.write_text('{"name":"o","probe":' + bad + ',"control":"clean"}\n', encoding="utf-8")
    with pytest.raises(ValueError):
        A.load_claims(str(f), None, None, None)


@pytest.mark.parametrize("bad", ['"--flag"', '["--flag", 3]', '{"a": 1}'])
def test_probe_args_must_be_a_list_of_strings(tmp_path, bad):
    f = tmp_path / "claims.jsonl"
    f.write_text('{"name":"s","probe":"","control":"","probe_args":' + bad + '}\n',
                 encoding="utf-8")
    with pytest.raises(ValueError):
        A.load_claims(str(f), None, None, None)


def test_a_string_probe_args_exits_2_not_a_silent_refuted(tmp_path):
    hook = _fake_hook(tmp_path, 'if "--flag" in sys.argv: print("fired")\n')
    f = tmp_path / "claims.jsonl"
    f.write_text('{"name":"s","probe":"","control":"","probe_args":"--flag"}\n', encoding="utf-8")
    assert A.main(["--hook", str(hook), "--claim-file", str(f)]) == 2


def test_a_claim_file_with_a_utf8_bom_is_read(tmp_path):
    f = tmp_path / "claims.jsonl"
    f.write_bytes(b"\xef\xbb\xbf" + b'{"name":"b","probe":"TRAP","control":"clean"}\n')
    assert [c.name for c in A.load_claims(str(f), None, None, None)] == ["b"]


def test_a_malformed_claim_file_exits_2(tmp_path):
    hook = _fake_hook(tmp_path, "sys.stdin.read()\n")
    f = tmp_path / "claims.jsonl"
    f.write_text('{"name": not json}\n', encoding="utf-8")
    assert A.main(["--hook", str(hook), "--claim-file", str(f)]) == 2


def test_probe_without_control_exits_2(tmp_path):
    hook = _fake_hook(tmp_path, "sys.stdin.read()\n")
    assert A.main(["--hook", str(hook), "--name", "c", "--probe", "x"]) == 2


# ---- argument validation happens BEFORE any subject runs ---------------------------------------

def test_an_invalid_fired_pattern_exits_2_before_running_the_subject(tmp_path):
    marker = tmp_path / "ran"
    hook = _fake_hook(tmp_path, f"open({str(marker)!r}, 'w').close()\n")
    rc = A.main(["--hook", str(hook), "--name", "c", "--probe", "a", "--control", "b",
                 "--fired-when", "match", "--fired-pattern", "("])
    assert rc == 2
    assert not marker.exists()


@pytest.mark.parametrize("mode", [["--fired-when", "match", "--fired-pattern", "BLOCKED"], []])
def test_a_missing_hook_path_exits_2(tmp_path, mode):
    rc = A.main(["--hook", str(tmp_path / "typo.py"), "--name", "c", "--probe", "a",
                 "--control", "b", *mode])
    assert rc == 2


# ---- --json emits the envelope on every exit-2 path -------------------------------------------

@pytest.mark.parametrize("argv", [
    ["--name", "c", "--probe", "x", "--control", "y"],                    # no --hook
    ["--hook", "does-not-exist.py", "--name", "c", "--probe", "x", "--control", "y"],
])
def test_json_envelope_on_usage_errors(argv, capsys):
    assert A.main([*argv, "--json"]) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False and payload["command"] == "adjudicate"
    assert payload["data"]["reason"]


def test_json_envelope_on_an_argparse_error(capsys):
    with pytest.raises(SystemExit) as exc:
        A.main(["--hook", "x.py", "--fired-when", "bogus", "--json"])
    assert exc.value.code == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False and "bogus" in payload["data"]["reason"]


def test_json_envelope_when_a_subject_times_out(tmp_path, capsys):
    rc = A.main(["--hook", str(_hanging_hook(tmp_path)), "--name", "c", "--probe", "HANG",
                 "--control", "clean", "--timeout", "1", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert rc == 2 and payload["ok"] is False
    assert payload["data"]["summary"]["error"] == 1


def test_a_non_cp1252_claim_name_does_not_crash_a_cp1252_stdout(tmp_path):
    hook = _fake_hook(tmp_path, 'data = sys.stdin.read()\nif "TRAP" in data: print("fired")\n')
    res = subprocess.run([sys.executable, str(SCRIPT), "--hook", str(hook), "--name", "c \u2717",
                          "--probe", "TRAP", "--control", "clean"], capture_output=True,
                         env={**os.environ, "PYTHONIOENCODING": "cp1252"}, timeout=60)
    assert res.returncode == 0, res.stderr
    assert b"CONFIRMED" in res.stdout
