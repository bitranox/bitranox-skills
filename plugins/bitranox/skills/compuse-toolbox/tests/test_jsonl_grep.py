"""Tests for jsonl_grep.py - filter a JSONL stream by type/role, extract a field or regex. ASCII."""
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
