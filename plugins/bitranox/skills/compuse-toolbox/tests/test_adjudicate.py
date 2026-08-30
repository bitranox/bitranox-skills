"""Tests for adjudicate.py. ASCII only.

The three-bucket verdict is the whole point of the tool, so it gets the most cases: a harness that
folds "the control did not discriminate" into "refuted" reports a clean sweep over broken controls,
which is what this replaces.
"""
import json
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
    assert "control" in err
