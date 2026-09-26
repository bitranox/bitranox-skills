"""Tests for jsonl_grep.py - filter a JSONL stream by type/role, extract a field or regex. ASCII."""
import sys
import threading
import pytest
import json

import jsonl_grep as J


def _mk(recs):
    return "\n".join(json.dumps(r) for r in recs) + "\n"


def test_filter_by_type():
    text = _mk([{"type": "user", "message": {"role": "user", "content": "hi"}},
                {"type": "assistant", "message": {"role": "assistant", "content": "yo"}}])
    out = J.filter_records(text, type_="assistant")
    assert len(out) == 1 and out[0]["type"] == "assistant"


def test_filter_by_role():
    text = _mk([{"type": "user", "message": {"role": "user"}},
                {"type": "x", "message": {"role": "assistant"}}])
    out = J.filter_records(text, role="assistant")
    assert len(out) == 1 and out[0]["message"]["role"] == "assistant"


def test_extract_dotted_field():
    text = _mk([{"type": "x", "message": {"role": "r", "model": "opus"}}])
    assert J.filter_records(text, field="message.model") == ["opus"]


def test_regex_over_raw_line():
    text = _mk([{"type": "assistant", "message": {"content": [{"input": {"command": "cargo build"}}]}},
                {"type": "assistant", "message": {"content": "nope"}}])
    assert len(J.filter_records(text, pattern="cargo")) == 1


def test_malformed_line_skipped():
    out = J.filter_records('{"type":"user"}\nNOT JSON\n{"type":"assistant"}\n')
    assert len(out) == 2


# --- corpus scan: many files, counted values -------------------------------------------------
# The motivating failure: answering "what values does message.model hold across the whole
# transcript corpus?" by hand-rolling a loop over ~1485 files, because the tool took one file
# and had no counting. A negative here is the dangerous answer, so the scan reports how many
# files it actually read - "I never looked" must not read as "the field holds nothing".


def _write(dirpath, name, recs):
    p = dirpath / name
    p.write_text(_mk(recs), encoding="utf-8")
    return p


def test_scan_counts_field_values_across_several_files(tmp_path):
    _write(tmp_path, "a.jsonl", [{"type": "assistant", "message": {"model": "opus"}},
                                 {"type": "assistant", "message": {"model": "haiku"}}])
    _write(tmp_path, "b.jsonl", [{"type": "assistant", "message": {"model": "opus"}}])
    res = J.scan_corpus([tmp_path], field="message.model")
    assert res.counts == {"opus": 2, "haiku": 1}


def test_scan_reports_how_many_files_it_read(tmp_path):
    _write(tmp_path, "a.jsonl", [{"type": "assistant", "message": {"model": "opus"}}])
    _write(tmp_path, "b.jsonl", [{"type": "assistant", "message": {"model": "opus"}}])
    res = J.scan_corpus([tmp_path], field="message.model")
    assert res.files_read == 2


def test_scan_of_an_empty_corpus_reads_nothing_rather_than_answering_absent(tmp_path):
    res = J.scan_corpus([tmp_path / "nothing-here"], field="message.model")
    assert res.files_read == 0 and res.counts == {}


def test_scan_finds_jsonl_below_a_directory(tmp_path):
    nested = tmp_path / "proj" / "sess"
    nested.mkdir(parents=True)
    _write(nested, "deep.jsonl", [{"type": "assistant", "message": {"model": "fable"}}])
    res = J.scan_corpus([tmp_path], field="message.model")
    assert res.counts == {"fable": 1} and res.files_read == 1


def test_scan_takes_an_explicit_file_whatever_its_extension(tmp_path):
    p = _write(tmp_path, "transcript.log", [{"type": "assistant", "message": {"model": "sonnet"}}])
    res = J.scan_corpus([p], field="message.model")
    assert res.counts == {"sonnet": 1}


def test_scan_applies_the_same_filters_as_a_single_file_read(tmp_path):
    _write(tmp_path, "a.jsonl", [{"type": "assistant", "message": {"role": "assistant", "model": "opus"}},
                                 {"type": "user", "message": {"role": "user", "model": "opus"}}])
    res = J.scan_corpus([tmp_path], field="message.model", role="assistant")
    assert res.counts == {"opus": 1}


@pytest.mark.skipif(sys.platform == "win32",
                    reason='Windows has no POSIX mode bits: chmod(0o000) leaves the file readable, so an unreadable candidate cannot be created')
def test_scan_counts_an_unreadable_file_as_skipped(tmp_path):
    _write(tmp_path, "good.jsonl", [{"type": "assistant", "message": {"model": "opus"}}])
    bad = tmp_path / "bad.jsonl"
    bad.write_bytes(b'{"type":"assistant"}\n')
    bad.chmod(0o000)
    try:
        res = J.scan_corpus([tmp_path], field="message.model")
    finally:
        bad.chmod(0o644)
    assert res.files_read == 1 and [p.name for p in map(__import__("pathlib").Path, res.files_skipped)] == ["bad.jsonl"]


def test_cli_count_prints_values_with_counts(tmp_path, capsys):
    _write(tmp_path, "a.jsonl", [{"type": "assistant", "message": {"model": "opus"}},
                                 {"type": "assistant", "message": {"model": "opus"}}])
    rc = J.main(["--field", "message.model", "--count", str(tmp_path)])
    out = capsys.readouterr().out
    assert rc == 0 and "opus" in out and "2" in out


def test_cli_reports_the_file_count_on_stderr_not_in_the_parsed_stream(tmp_path, capsys):
    _write(tmp_path, "a.jsonl", [{"type": "assistant", "message": {"model": "opus"}}])
    J.main(["--field", "message.model", "--count", str(tmp_path)])
    cap = capsys.readouterr()
    assert "1" in cap.err and "file" in cap.err.lower()
    assert "file" not in cap.out.lower()


def test_cli_exits_3_when_the_corpus_is_empty(tmp_path, capsys):
    rc = J.main(["--field", "message.model", "--count", str(tmp_path / "missing")])
    capsys.readouterr()
    assert rc == 3


def test_cli_count_without_a_field_is_a_usage_error(tmp_path, capsys):
    rc = J.main(["--count", str(tmp_path)])
    capsys.readouterr()
    assert rc == 2


def test_cli_still_reads_a_single_file_without_count(tmp_path, capsys):
    p = _write(tmp_path, "a.jsonl", [{"type": "assistant", "message": {"model": "opus"}}])
    rc = J.main(["--field", "message.model", str(p)])
    out = capsys.readouterr().out
    assert rc == 0 and out.strip() == "opus"


def test_cli_reads_every_path_given_not_just_the_first(tmp_path, capsys):
    a = _write(tmp_path, "a.jsonl", [{"type": "assistant", "message": {"model": "opus"}}])
    b = _write(tmp_path, "b.jsonl", [{"type": "assistant", "message": {"model": "haiku"}}])
    J.main(["--field", "message.model", str(a), str(b)])
    assert capsys.readouterr().out.split() == ["opus", "haiku"]


def test_scan_counts_unparseable_lines_rather_than_dropping_them(tmp_path):
    p = tmp_path / "a.jsonl"
    p.write_text('{"type":"assistant","message":{"model":"opus"}}\nNOT JSON\n{"broken\n',
                 encoding="utf-8")
    res = J.scan_corpus([tmp_path], field="message.model")
    assert res.counts == {"opus": 1} and res.lines_skipped == 2


def test_cli_reports_skipped_lines_on_stderr(tmp_path, capsys):
    p = tmp_path / "a.jsonl"
    p.write_text('{"type":"assistant","message":{"model":"opus"}}\nNOT JSON\n', encoding="utf-8")
    J.main(["--field", "message.model", "--count", str(tmp_path)])
    assert "1 unparseable line" in capsys.readouterr().err


def test_scan_survives_a_json_line_that_is_not_an_object(tmp_path):
    # A bare array parses fine, then `obj.get(...)` raises - which would abort a 1500-file scan.
    p = tmp_path / "a.jsonl"
    p.write_text('[1,2,3]\n{"type":"assistant","message":{"model":"opus"}}\n', encoding="utf-8")
    res = J.scan_corpus([tmp_path], field="message.model")
    assert res.counts == {"opus": 1} and res.lines_skipped == 1


# ==== rank-10 skill-script audit: nothing read may vanish, nothing absent may pass as read ======

import os
import subprocess
from pathlib import Path

SCRIPT = Path(J.__file__).resolve()
TYPES = [{"v": "1"}, {"v": 1}, {"v": "true"}, {"v": True}, {"v": None}, {"other": 1}]


def _run(args, stdin=b"", env_extra=None):
    """The script as a real process: real stdin bytes, real stream encoding, real exit code."""
    env = dict(os.environ)
    env.pop("PYTHONIOENCODING", None)
    env.pop("PYTHONUTF8", None)
    env.update(env_extra or {})
    return subprocess.run([sys.executable, str(SCRIPT), *args], input=stdin,
                          capture_output=True, env=env)


# --- a named path that does not exist is reported and fails the run ------------------------------

def test_count_reports_a_missing_path_beside_a_good_one(tmp_path, capsys):
    good = _write(tmp_path, "ab.jsonl", [{"v": "a"}, {"v": "b"}])
    rc = J.main([str(good), str(tmp_path / "typo.jsonl"), "--field", "v", "--count"])
    cap = capsys.readouterr()
    assert rc == 2
    assert "typo.jsonl" in cap.err and "1 skipped" in cap.err
    assert "a" in cap.out and "b" in cap.out


def test_list_reports_a_missing_path_beside_a_good_one(tmp_path, capsys):
    good = _write(tmp_path, "ab.jsonl", [{"v": "a"}, {"v": "b"}])
    rc = J.main([str(good), str(tmp_path / "typo.jsonl"), "--field", "v"])
    cap = capsys.readouterr()
    assert rc == 2 and cap.out.split() == ["a", "b"]
    assert "typo.jsonl" in cap.err


def test_list_mode_on_only_a_missing_path_exits_3(tmp_path, capsys):
    assert J.main([str(tmp_path / "nope.jsonl"), "--field", "v"]) == 3
    assert "nope.jsonl" in capsys.readouterr().err


# --- unparseable lines are counted in list mode and on stdin too ---------------------------------

PRETTY = '{\n  "message": {\n    "model": "opus"\n  }\n}\n'


def test_list_mode_reports_unparseable_lines(tmp_path, capsys):
    p = tmp_path / "pretty.json"
    p.write_text(PRETTY, encoding="utf-8")
    rc = J.main([str(p), "--field", "message.model"])
    cap = capsys.readouterr()
    assert rc == 0 and cap.out == ""
    assert "5 unparseable line(s)" in cap.err


def test_stdin_list_mode_reports_unparseable_lines():
    proc = _run(["--field", "message.model"], stdin=PRETTY.encode("utf-8"))
    assert proc.returncode == 0 and proc.stdout == b""
    assert b"5 unparseable line(s)" in proc.stderr


def test_stdin_list_mode_reads_records():
    proc = _run(["--field", "message.model"],
                stdin=_mk([{"message": {"model": "opus"}}]).encode("utf-8"))
    assert proc.returncode == 0 and proc.stdout.decode().split() == ["opus"]


# --- an unreadable directory is a skip, never a silent undercount --------------------------------

@pytest.mark.skipif(sys.platform == "win32" or getattr(os, "geteuid", lambda: 1)() == 0,
                    reason="needs POSIX mode bits and a non-root user to make a directory unreadable")
def test_an_unreadable_subdirectory_is_listed_as_skipped(tmp_path):
    _write(tmp_path, "a.jsonl", [{"m": "opus"}])
    locked = tmp_path / "locked"
    locked.mkdir()
    _write(locked, "b.jsonl", [{"m": "haiku"}])
    locked.chmod(0)
    try:
        res = J.scan_corpus([tmp_path], field="m")
    finally:
        locked.chmod(0o755)
    assert res.counts == {"opus": 1}
    assert [Path(p).name for p in res.files_skipped] == ["locked"]


@pytest.mark.skipif(sys.platform == "win32" or getattr(os, "geteuid", lambda: 1)() == 0,
                    reason="needs POSIX mode bits and a non-root user to make a file unreadable")
def test_list_mode_skips_an_unreadable_file_instead_of_crashing(tmp_path, capsys):
    _write(tmp_path, "a.jsonl", [{"m": "opus"}])
    bad = _write(tmp_path, "b.jsonl", [{"m": "haiku"}])
    bad.chmod(0)
    try:
        rc = J.main([str(tmp_path), "--field", "m"])
    finally:
        bad.chmod(0o644)
    cap = capsys.readouterr()
    assert rc == 0 and cap.out.split() == ["opus"] and "b.jsonl" in cap.err


# --- values keep their JSON type, and null is a value --------------------------------------------

def test_count_keeps_strings_and_scalars_apart(tmp_path):
    _write(tmp_path, "t.jsonl", TYPES)
    res = J.scan_corpus([tmp_path], field="v")
    assert res.counts == {'"1"': 1, "1": 1, '"true"': 1, "true": 1, "null": 1}


def test_an_ordinary_string_is_still_printed_bare(tmp_path):
    _write(tmp_path, "t.jsonl", [{"v": "opus"}])
    assert J.scan_corpus([tmp_path], field="v").counts == {"opus": 1}


def test_json_null_is_tallied_and_a_missing_key_is_not(tmp_path, capsys):
    _write(tmp_path, "t.jsonl", [{"stop": None}, {"stop": None}, {"stop": "end_turn"}, {}])
    rc = J.main([str(tmp_path), "--field", "stop", "--count"])
    out = capsys.readouterr().out
    assert rc == 0
    assert out.splitlines() == ["2\tnull", "1\tend_turn"]


def test_list_mode_without_a_field_prints_each_record_as_json(tmp_path, capsys):
    p = _write(tmp_path, "t.jsonl", [{"type": "user", "n": 1}])
    J.main([str(p), "--type", "user"])
    assert json.loads(capsys.readouterr().out) == {"type": "user", "n": 1}


def test_list_mode_prints_a_null_value(tmp_path, capsys):
    p = _write(tmp_path, "t.jsonl", [{"stop": None}, {}])
    J.main([str(p), "--field", "stop"])
    assert capsys.readouterr().out.splitlines() == ["null"]


# --- encoding: cp1252 stdout, undecodable stdin, BOM, line separators -----------------------------

def test_non_ascii_values_survive_a_cp1252_stdout(tmp_path):
    p = _write(tmp_path, "u.jsonl", [{"m": "caf\u00e9 \u2014 \U0001f600"}])
    for args in (["--count"], []):
        proc = _run([str(p), "--field", "m", *args], env_extra={"PYTHONIOENCODING": "cp1252"})
        assert proc.returncode == 0, proc.stderr
        assert "caf\u00e9 \u2014 \U0001f600" in proc.stdout.decode("utf-8")


def test_undecodable_stdin_bytes_do_not_crash_the_read():
    proc = _run(["--field", "m"], stdin=b'{"m": "a\x81b"}\n{"m": "ok"}\n',
                env_extra={"PYTHONIOENCODING": "cp1252"})
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.decode("utf-8").split()[-1] == "ok"


def test_a_bom_does_not_cost_the_first_record(tmp_path, capsys):
    p = tmp_path / "bom.jsonl"
    p.write_bytes(b"\xef\xbb\xbf" + _mk([{"message": {"model": "opus"}}]).encode("utf-8"))
    rc = J.main([str(p), "--field", "message.model"])
    cap = capsys.readouterr()
    assert rc == 0 and cap.out.split() == ["opus"] and "unparseable" not in cap.err


def test_a_bom_on_stdin_does_not_cost_the_first_record():
    proc = _run(["--field", "m"], stdin=b"\xef\xbb\xbf" + _mk([{"m": "opus"}]).encode("utf-8"))
    assert proc.stdout.decode().split() == ["opus"]


def test_a_line_separator_inside_a_value_does_not_split_the_record():
    text = json.dumps({"m": "a\u2028b\fc"}, ensure_ascii=False) + "\n"
    assert J.filter_records(text, field="m") == ["a\u2028b\fc"]


# --- --count reads stdin like every other mode ----------------------------------------------------

def test_count_tallies_stdin_when_no_path_is_given():
    proc = _run(["--field", "v", "--count"], stdin=_mk(TYPES).encode("utf-8"))
    assert proc.returncode == 0, proc.stderr
    assert sorted(proc.stdout.decode().splitlines()) == ['1\t"1"', '1\t"true"', "1\t1",
                                                          "1\tnull", "1\ttrue"]


# --- an invalid --pattern is a usage error ---------------------------------------------------------

@pytest.mark.parametrize("extra", [[], ["--count", "--field", "v"]])
def test_an_invalid_pattern_is_a_usage_error(tmp_path, capsys, extra):
    p = _write(tmp_path, "t.jsonl", TYPES)
    rc = J.main([str(p), "--pattern", "(", *extra])
    assert rc == 2
    assert "--pattern" in capsys.readouterr().err


# --- both JSON backends read and print the same records ----------------------------------------

# Runs the script with orjson unimportable, so the stdlib fallback is the reader - the arm CI takes,
# since CI does not install orjson. Blocking the import is the one seam: the script picks its
# backend at import time.
_STDLIB_SHIM = ("import runpy, sys; sys.modules['orjson'] = None; script = sys.argv[1]; "
                "sys.argv = sys.argv[1:]; runpy.run_path(script, run_name='__main__')")


def _run_backend(backend, args, stdin=b""):
    if backend == "orjson":
        pytest.importorskip("orjson", reason="the orjson arm needs orjson installed")
        cmd = [sys.executable, str(SCRIPT), *args]
    else:
        cmd = [sys.executable, "-c", _STDLIB_SHIM, str(SCRIPT), *args]
    return subprocess.run(cmd, input=stdin, capture_output=True,
                          env={**os.environ, "PYTHONUTF8": "1"})


@pytest.mark.parametrize("backend", ["stdlib", "orjson"])
def test_a_non_standard_constant_is_unparseable_and_its_string_prints_bare(tmp_path, backend):
    # NaN and Infinity are not JSON. orjson refuses them; the stdlib accepted them, so the same
    # line parsed or not depending on what was installed, and the string "NaN" printed quoted on
    # one backend and bare on the other.
    p = tmp_path / "c.jsonl"
    p.write_text('{"x":NaN}\n{"x":"NaN"}\n{"x":-Infinity}\n{"x":"Infinity"}\n',
                 encoding="utf-8")
    proc = _run_backend(backend, [str(p), "--field", "x"])
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.decode("utf-8").splitlines() == ["NaN", "Infinity"]
    assert b"2 unparseable line(s)" in proc.stderr


@pytest.mark.parametrize("backend", ["stdlib", "orjson"])
def test_absurdly_deep_nesting_is_an_unparseable_line_not_a_traceback(tmp_path, backend):
    p = tmp_path / "deep.jsonl"
    p.write_text('{"x":' + "[" * 100000 + "]" * 100000 + '}\n{"x":"ok"}\n', encoding="utf-8")
    for extra in ([], ["--count"]):
        proc = _run_backend(backend, [str(p), "--field", "x", *extra])
        assert proc.returncode == 0, proc.stderr
        assert b"Traceback" not in proc.stderr
        assert proc.stdout.decode("utf-8").split()[-1] == "ok"
        assert b"1 unparseable line(s)" in proc.stderr


# --- a path that exists but is not a regular file (a pipe from <(...)) is read -------------------

@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="named pipes need os.mkfifo (POSIX)")
@pytest.mark.parametrize("extra", [[], ["--count"]])
def test_a_named_pipe_is_read_not_reported_missing(tmp_path, capsys, extra):
    fifo = tmp_path / "pipe"
    os.mkfifo(fifo)

    def feed():
        with open(fifo, "w", encoding="utf-8") as handle:
            handle.write(_mk([{"v": "a"}, {"v": "b"}]))

    writer = threading.Thread(target=feed, daemon=True)
    writer.start()
    rc = J.main([str(fifo), "--field", "v", *extra])
    if writer.is_alive():                                # nothing opened the pipe: release the writer
        os.close(os.open(fifo, os.O_RDONLY | os.O_NONBLOCK))
    writer.join(timeout=10)
    cap = capsys.readouterr()
    assert rc == 0, cap.err
    assert "no such file" not in cap.err
    assert sorted(cap.out.split()) == (["1", "1", "a", "b"] if extra else ["a", "b"])
