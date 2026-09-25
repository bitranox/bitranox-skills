"""Tests for diffbehave.py - do two implementations BEHAVE the same on the same inputs?"""
import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import diffbehave as D

TOOL = Path(__file__).resolve().parents[1] / "scripts" / "diffbehave.py"


def _res(rc=0, out="", err=""):
    return D.Run(returncode=rc, stdout=out, stderr=err)


def _py(code: str) -> str:
    """A shell-quoted `<this interpreter> -c <code>` command for --a/--b.

    Uses sys.executable rather than a bare "python3" - on Windows that name is often the Store
    stub, and it is never guaranteed to be the interpreter running the tests.
    """
    return f'{sys.executable} -c "{code}"'


# --- pure comparison logic ------------------------------------------------------------------

def test_identical_runs_agree():
    assert D.verdict(_res(0, "x"), _res(0, "x")) == "AGREE"


def test_a_different_exit_code_is_a_difference():
    assert D.verdict(_res(0, "x"), _res(1, "x")) == "DIFFER"


def test_a_different_stdout_is_a_difference():
    assert D.verdict(_res(0, "yes"), _res(0, "no")) == "DIFFER"


def test_stderr_is_compared_too_because_a_guard_speaks_on_stderr():
    assert D.verdict(_res(2, "", "blocked: reason A"), _res(2, "", "blocked: reason B")) == "DIFFER"


def test_trailing_whitespace_alone_is_not_a_behaviour_difference():
    """Otherwise every comparison differs and the tool reports noise."""
    assert D.verdict(_res(0, "x\n"), _res(0, "x")) == "AGREE"


def test_summary_counts_and_flags_whether_anything_differed():
    results = [
        D.CaseResult(name="c1", verdict="AGREE", a=_res(), b=_res()),
        D.CaseResult(name="c2", verdict="DIFFER", a=_res(0, "x"), b=_res(1, "y")),
    ]
    s = D.summarize(results)
    assert s["total"] == 2 and s["agree"] == 1 and s["differ"] == 1
    assert s["any_differ"] is True
    assert s["differing"] == ["c2"]


def test_summary_of_all_agreeing_says_so():
    s = D.summarize([D.CaseResult(name="c1", verdict="AGREE", a=_res(), b=_res())])
    assert s["any_differ"] is False and s["differing"] == []


def test_expect_differ_is_the_known_negative_check():
    """The rule this tool exists for: a detector that cannot say DIFFER proves nothing."""
    all_agree = D.summarize([D.CaseResult(name="c", verdict="AGREE", a=_res(), b=_res())])
    assert D.meets_expectation(all_agree, expect_differ=1) is False
    assert D.meets_expectation(all_agree, expect_differ=0) is True
    one_differs = D.summarize([D.CaseResult(name="c", verdict="DIFFER", a=_res(), b=_res(1))])
    assert D.meets_expectation(one_differs, expect_differ=1) is True


# --- real processes, not mocks: what the tool is actually for --------------------------------

def test_real_end_to_end_against_two_actual_commands():
    """Not a mock: run two real interpreter processes and compare what they actually did."""
    hello = _py("import sys;sys.stdout.write('hello')")
    same = D.compare(hello, hello, [D.Case(name="c1", stdin="")])
    assert [r.verdict for r in same] == ["AGREE"]

    goodbye = _py("import sys;sys.stdout.write('goodbye')")
    differs = D.compare(hello, goodbye, [D.Case(name="c1", stdin="")])
    assert [r.verdict for r in differs] == ["DIFFER"]


def test_stdin_is_delivered_to_both_sides():
    cat = _py("import sys;sys.stdout.write(sys.stdin.read())")
    results = D.compare(cat, cat, [D.Case(name="payload", stdin="abc")])
    assert results[0].verdict == "AGREE"
    assert results[0].a.stdout.strip() == "abc"


def test_a_command_that_fails_to_start_is_a_result_not_a_crash():
    noop = _py("pass")
    results = D.compare("definitely-not-a-real-command-xyz", noop, [D.Case(name="c", stdin="")])
    assert results[0].verdict == "DIFFER"
    assert results[0].a.returncode != 0


def test_non_ascii_output_round_trips_through_utf8_capture():
    """A locale-default decode fails differently per platform; utf-8 capture must be explicit."""
    # Write BYTES: a bare sys.stdout.write encodes with the child's stdout encoding, which is
    # cp1252 on Windows, so the test would be measuring the child's locale rather than whether
    # diffbehave decodes its capture as utf-8 - which is what it claims to check.
    accented = _py("import sys;sys.stdout.buffer.write('caf\\u00e9'.encode('utf-8'))")
    results = D.compare(accented, accented, [D.Case(name="c", stdin="")])
    assert results[0].verdict == "AGREE"
    assert results[0].a.stdout.strip() == "caf\u00e9"


# --- CLI contract: exit codes, JSON envelope, stderr-only diagnostics ------------------------

def _run(args):
    return subprocess.run([sys.executable, str(TOOL), *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def test_no_cases_is_a_usage_error_not_a_traceback():
    r = _run(["--a", "true", "--b", "true"])
    assert r.returncode == 2
    assert "no cases" in r.stderr
    assert "Traceback" not in r.stderr


def test_missing_case_file_is_a_typed_error_not_a_traceback():
    r = _run(["--a", "true", "--b", "true", "--case-file", "/no/such/file.jsonl"])
    assert r.returncode == 2
    assert "cannot read --case-file" in r.stderr
    assert "Traceback" not in r.stderr


def test_exit_codes_reflect_whether_the_expectation_was_met():
    hello = _py("import sys;sys.stdout.write('hello')")
    goodbye = _py("import sys;sys.stdout.write('goodbye')")
    assert _run(["--a", hello, "--b", hello, "--case", "x"]).returncode == 0
    assert _run(["--a", hello, "--b", goodbye, "--case", "x", "--expect-differ", "1"]).returncode == 0
    assert _run(["--a", hello, "--b", hello, "--case", "x", "--expect-differ", "1"]).returncode == 1


def test_json_envelope_is_the_documented_shape():
    hello = _py("import sys;sys.stdout.write('hello')")
    r = _run(["--a", hello, "--b", hello, "--case", "x", "--json"])
    assert r.returncode == 0
    payload = json.loads(r.stdout)
    assert payload["ok"] is True
    assert payload["command"] == "diffbehave"
    assert payload["data"]["summary"]["total"] == 1


def test_warnings_go_to_stderr_not_the_parsed_stream():
    """The FAILED-expectation diagnostic must not corrupt --json stdout, even on failure."""
    hello = _py("import sys;sys.stdout.write('hello')")
    r = _run(["--a", hello, "--b", hello, "--case", "x", "--expect-differ", "1", "--json"])
    assert r.returncode == 1
    payload = json.loads(r.stdout)  # must still parse even though a diagnostic was emitted
    assert payload["ok"] is False
    assert "FAILED" in r.stderr


def test_case_file_jsonl_row_carries_name_stdin_and_args(tmp_path):
    """--case-file rows can carry a name, stdin, and per-case args - not just raw lines."""
    echo_argv = _py("import sys;sys.stdout.write(' '.join(sys.argv[1:]))")
    case_file = tmp_path / "cases.jsonl"
    case_file.write_text(
        json.dumps({"name": "greet", "stdin": "", "args": ["hi", "there"]}) + "\n",
        encoding="utf-8",
    )
    r = _run(["--a", echo_argv, "--b", echo_argv, "--case-file", str(case_file), "--json"])
    payload = json.loads(r.stdout)
    assert payload["data"]["results"][0]["name"] == "greet"
    assert payload["data"]["results"][0]["verdict"] == "AGREE"


# --- whitespace: only TRAILING whitespace is formatting --------------------------------------

def test_leading_whitespace_is_a_behaviour_difference():
    assert D.verdict(_res(0, "  x"), _res(0, "x")) == "DIFFER"


def test_a_leading_blank_line_is_a_behaviour_difference():
    assert D.verdict(_res(0, "\nx"), _res(0, "x")) == "DIFFER"


def test_a_form_feed_is_not_read_as_a_line_break():
    """splitlines() treated \\f as a newline, so 'a<FF>b' and 'a<LF>b' compared equal."""
    assert D.verdict(_res(0, "a\x0cb"), _res(0, "a\nb")) == "DIFFER"


def test_trailing_blank_lines_and_crlf_are_still_formatting():
    assert D.verdict(_res(0, "a\r\nb\r\n\n"), _res(0, "a\nb")) == "AGREE"


# --- a case neither side could run is an ERROR, never AGREE -----------------------------------

def test_both_sides_failing_to_launch_is_an_error_not_agreement():
    """A typo copied into both commands used to read as 'behave the same'."""
    results = D.compare("definitely-not-a-real-command-xyz", "definitely-not-a-real-command-xyz",
                        [D.Case(name="c", stdin="")])
    assert results[0].verdict == "ERROR"
    assert results[0].a.returncode == 127 and results[0].a.launched is False


def test_both_sides_timing_out_is_an_error_not_agreement():
    sleeper = _py("import time;time.sleep(5)")
    results = D.compare(sleeper, sleeper, [D.Case(name="c", stdin="")], timeout=0.5)
    assert results[0].verdict == "ERROR"
    assert results[0].a.returncode == 124 and results[0].b.returncode == 124


def test_one_side_timing_out_is_a_difference():
    sleeper = _py("import time;time.sleep(5)")
    results = D.compare(sleeper, _py("pass"), [D.Case(name="c", stdin="")], timeout=0.5)
    assert results[0].verdict == "DIFFER"
    assert "timeout" in results[0].a.stderr


def test_cli_both_sides_unlaunchable_exits_2_and_says_why():
    r = _run(["--a", "pyhton3-typo old.py", "--b", "pyhton3-typo new.py", "--case", "x"])
    assert r.returncode == 2
    assert "ERROR" in r.stdout
    assert "could not run" in r.stderr


def test_cli_json_reports_the_error_count():
    r = _run(["--a", "pyhton3-typo", "--b", "pyhton3-typo", "--case", "x", "--json"])
    assert r.returncode == 2
    payload = json.loads(r.stdout)
    assert payload["ok"] is False
    assert payload["data"]["summary"]["error"] == 1
    assert payload["data"]["summary"]["erroring"] == ["case1"]


# --- human output ---------------------------------------------------------------------------

def test_cli_human_output_shows_what_each_side_did_on_a_difference():
    hello = _py("import sys;sys.stdout.write('hello')")
    goodbye = _py("import sys;sys.stdout.write('goodbye')")
    r = _run(["--a", hello, "--b", goodbye, "--case", "x"])
    assert r.returncode == 0
    assert "DIFFER  case1" in r.stdout
    assert "a: rc=0 out='hello'" in r.stdout
    assert "b: rc=0 out='goodbye'" in r.stdout
    assert "0/1 agree, 1 differ" in r.stdout


def test_cli_output_the_console_cannot_encode_is_printed_not_a_crash():
    arrow = _py("import sys;sys.stdout.buffer.write('\\u2192'.encode('utf-8'))")
    plain = _py("import sys;sys.stdout.write('x')")
    env = dict(os.environ, PYTHONIOENCODING="cp1252")
    r = subprocess.run([sys.executable, str(TOOL), "--a", arrow, "--b", plain, "--case", "x"],
                       capture_output=True, env=env, check=False)
    assert r.returncode == 0, r.stderr
    assert b"DIFFER" in r.stdout


class _FailingStdout(io.StringIO):
    """A stdout whose device fails, the way a redirect to a full disk does."""

    def write(self, s):
        raise OSError(28, "No space left on device")


def test_an_unexpected_error_exits_2_not_the_expectation_code(monkeypatch, capsys):
    hello = _py("import sys;sys.stdout.write('hello')")
    monkeypatch.setattr(sys, "stdout", _FailingStdout())
    assert D.main(["--a", hello, "--b", hello, "--case", "x"]) == 2
    assert "No space left" in capsys.readouterr().err


# --- command strings and case rows are validated, not crashed on ---------------------------

@pytest.mark.parametrize("command", ["", "   "] + ([] if os.name == "nt" else ["python3 -c 'print(1)"]))
def test_cli_an_unusable_command_string_is_a_usage_error(command):
    r = _run(["--a", command, "--b", _py("pass"), "--case", "x"])
    assert r.returncode == 2
    assert "Traceback" not in r.stderr
    assert "--a" in r.stderr


def _case_file(tmp_path, *rows):
    f = tmp_path / "cases.jsonl"
    f.write_text("".join(r + "\n" for r in rows), encoding="utf-8")
    return str(f)


@pytest.mark.parametrize("row", [
    '{"args": "hi there"}',
    '{"args": [1]}',
    '{"stdin": 5}',
    '{"stdin": "", "args": {"a": 1}}',
])
def test_cli_a_malformed_case_row_is_a_usage_error(tmp_path, row):
    echo = _py("import sys;sys.stdout.write(repr(sys.argv[1:]))")
    r = _run(["--a", echo, "--b", echo, "--case-file", _case_file(tmp_path, row)])
    assert r.returncode == 2
    assert "Traceback" not in r.stderr
    assert "line1" in r.stderr


def test_cli_a_null_stdin_is_empty_input_not_the_parent_stdin(tmp_path):
    """A null stdin used to inherit the parent's stdin: the first side drained it, fake DIFFER."""
    cat = _py("import sys;sys.stdout.write(sys.stdin.read())")
    r = subprocess.run(
        [sys.executable, str(TOOL), "--a", cat, "--b", cat, "--json",
         "--case-file", _case_file(tmp_path, '{"stdin": null}')],
        input="PARENTSTDIN", capture_output=True, text=True, encoding="utf-8", check=False)
    payload = json.loads(r.stdout)
    result = payload["data"]["results"][0]
    assert result["verdict"] == "AGREE"
    assert result["a"]["stdout"] == ""


def test_cli_raw_lines_and_argless_objects_are_fed_as_stdin(tmp_path):
    cat = _py("import sys;sys.stdout.write(sys.stdin.read())")
    r = _run(["--a", cat, "--b", cat, "--json",
              "--case-file", _case_file(tmp_path, "raw text line", '{"x":1}')])
    assert r.returncode == 0, r.stderr
    results = json.loads(r.stdout)["data"]["results"]
    assert [(x["name"], x["a"]["stdout"]) for x in results] == [
        ("line1", "raw text line"), ("line2", '{"x":1}')]


def test_cli_a_utf16_case_file_is_decoded(tmp_path):
    """PowerShell 5.1's > writes UTF-16LE with a BOM."""
    cat = _py("import sys;sys.stdout.write(sys.stdin.read())")
    f = tmp_path / "cases.jsonl"
    f.write_bytes('{"name": "w", "stdin": "abc"}\n'.encode("utf-16"))
    r = _run(["--a", cat, "--b", cat, "--case-file", str(f), "--json"])
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["data"]["results"][0]["a"]["stdout"] == "abc"


def test_cli_a_utf8_bom_case_file_keeps_its_first_row(tmp_path):
    cat = _py("import sys;sys.stdout.write(sys.stdin.read())")
    f = tmp_path / "cases.jsonl"
    f.write_bytes(b'\xef\xbb\xbf{"name": "first", "stdin": "abc"}\n')
    r = _run(["--a", cat, "--b", cat, "--case-file", str(f), "--json"])
    assert json.loads(r.stdout)["data"]["results"][0]["name"] == "first"


def test_cli_a_case_file_that_is_not_text_is_a_typed_error(tmp_path):
    f = tmp_path / "cases.jsonl"
    f.write_bytes(b"\xc3\x28 not utf-8\n")
    r = _run(["--a", "true", "--b", "true", "--case-file", str(f)])
    assert r.returncode == 2
    assert "Traceback" not in r.stderr
    assert "cannot read --case-file" in r.stderr


# --------------------------------------------------------------------------
# Command splitting is platform-sensitive. shlex.split defaults to POSIX mode,
# where a backslash ESCAPES the next character - so a Windows program path is
# silently stripped of its separators and the command cannot start.
# --------------------------------------------------------------------------


@pytest.mark.skipif(os.name != "nt",
                    reason="the split is CommandLineToArgvW, a real Windows API - it cannot be "
                           "asked for Windows behaviour from POSIX")
def test_split_command_keeps_backslashes_on_windows():
    argv = D._split_command(r'C:\tools\py.exe -c "import sys"')
    assert argv[0] == r"C:\tools\py.exe", argv
    assert argv[1] == "-c"
    assert argv[2] == "import sys", "surrounding quotes must not survive into argv"


@pytest.mark.skipif(os.name == "nt",
                    reason="asserts the POSIX escape semantics callers rely on there, which the "
                           "Windows command-line parser deliberately does not share")
def test_split_command_treats_backslash_as_an_escape_on_posix():
    """The POSIX behaviour must be preserved, not traded away for the Windows fix."""
    argv = D._split_command(r"echo a\ b")
    assert argv == ["echo", "a b"], argv


@pytest.mark.skipif(os.name != "nt",
                    reason="the split is CommandLineToArgvW, a real Windows API - it cannot be "
                           "asked for Windows behaviour from POSIX")
def test_split_command_keeps_an_embedded_quoted_value_in_one_token_on_windows():
    r"""The earlier non-POSIX fix stripped quotes only when they WRAPPED the whole token, so
    `--opt="a b"` came apart into '--opt="a' + 'b"' and the option reached the child broken.
    Escape-off reads the quoting properly while still leaving backslashes alone."""
    argv = D._split_command(r'py.exe --opt="a b" tail')
    assert argv == ["py.exe", "--opt=a b", "tail"]


@pytest.mark.skipif(os.name != "nt",
                    reason="the split is CommandLineToArgvW, a real Windows API - it cannot be "
                           "asked for Windows behaviour from POSIX")
def test_split_command_survives_the_c_runtime_quote_escape_on_windows():
    r"""The shape neither shlex mode could read: escape-off saw unbalanced quotes and RAISED,
    non-POSIX mode left the quotes attached. CommandLineToArgvW is the parser that defines this
    convention, so it reconstructs the argument exactly rather than degrading."""
    assert D._split_command(r'cmd "a\"b" x') == ["cmd", 'a"b', "x"]


@pytest.mark.skipif(os.name != "nt",
                    reason="the split is CommandLineToArgvW, a real Windows API - it cannot be "
                           "asked for Windows behaviour from POSIX")
def test_split_command_handles_a_quoted_path_with_spaces_on_windows():
    argv = D._split_command(r'"C:\Program Files\py.exe" --version')
    assert argv == [r"C:\Program Files\py.exe", "--version"], argv
