"""quotecheck: substring-check subagent quote-backs against the skill text they cite."""
from __future__ import annotations

import json
import re
import tracemalloc
from pathlib import Path

import pytest

import quotecheck

SKILL = (
    "# Skill\n\n"
    "Run the gate after **every** edit, never before the commit.\n"
    "Use `git ls-files -z` when a path may hold non-ASCII bytes.\n"
    "A second   line\nwraps across two lines here.\n"
)


@pytest.fixture()
def skill_dir(tmp_path: Path) -> Path:
    d = tmp_path / "skill"
    (d / "references").mkdir(parents=True)
    (d / "SKILL.md").write_text(SKILL, encoding="utf-8")
    (d / "references" / "more.md").write_text("A reference sentence lives here.\n", encoding="utf-8")
    (d / ".skillwriter").mkdir()
    (d / ".skillwriter" / "notes.md").write_text("A hidden working sentence.\n", encoding="utf-8")
    return d


def _check(quote: str, d: Path, min_part: int = 12) -> quotecheck.Verdict:
    return quotecheck.check_quote(quote, quotecheck.dir_text(d), min_part)


def test_markup_case_and_whitespace_are_ignored(skill_dir: Path) -> None:
    assert _check("run the gate after every edit, NEVER before the commit.", skill_dir).verdict == "OK"
    assert _check("Use git ls-files -z when a path", skill_dir).verdict == "OK"
    assert _check("A second line wraps across two lines", skill_dir).verdict == "OK"


def test_a_sentence_that_is_not_there_is_a_mismatch_naming_the_part(skill_dir: Path) -> None:
    v = _check("Run the gate before every commit, always.", skill_dir)
    assert v.verdict == "MISMATCH"
    assert v.missing == ["run the gate before every commit, always."]


def test_joined_quote_needs_every_part(skill_dir: Path) -> None:
    ok = "Run the gate after every edit ... A reference sentence lives here"
    assert _check(ok, skill_dir).verdict == "OK"
    for joiner in (" ... ", chr(0x2026), " / ", " | ", "\n"):
        bad = f"Run the gate after every edit{joiner}An invented second sentence"
        v = _check(bad, skill_dir)
        assert v.verdict == "MISMATCH", joiner
        assert v.missing == ["an invented second sentence"], joiner


def test_reference_files_count_and_skillwriter_does_not(skill_dir: Path) -> None:
    assert _check("A reference sentence lives here", skill_dir).verdict == "OK"
    assert _check("A hidden working sentence", skill_dir).verdict == "MISMATCH"


def test_none_answer_is_not_checked(skill_dir: Path) -> None:
    assert _check(" none ", skill_dir).verdict == "NONE"


def test_a_quote_too_short_to_check_is_never_ok(skill_dir: Path) -> None:
    assert _check("the gate", skill_dir).verdict == "TOO-SHORT"
    assert _check("the gate", skill_dir, min_part=3).verdict == "OK"


def test_a_single_file_can_be_the_text(skill_dir: Path) -> None:
    assert _check("A reference sentence lives here", skill_dir / "SKILL.md").verdict == "MISMATCH"


def _journal(path: Path, rows_by_label: dict[str, list[dict[str, str]]]) -> Path:
    lines = [{"type": "launched"}]
    for i, (label, rows) in enumerate(rows_by_label.items()):
        lines.append({"type": "started", "agentId": f"a{i}", "label": label})
        lines.append({"type": "result", "agentId": f"a{i}", "result": {"rows": rows}})
    path.write_text("\n".join(json.dumps(x) for x in lines) + "\n", encoding="utf-8")
    return path


def _rows_file(path: Path, mapping: dict[str, Path]) -> Path:
    path.write_text(json.dumps([{"slug": k, "pre": str(v)} for k, v in mapping.items()]), encoding="utf-8")
    return path


def test_journal_mode_checks_only_matching_labels_against_each_rows_dir(
        tmp_path: Path, skill_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
    journal = _journal(tmp_path / "j.jsonl", {
        "RED h1 opus": [
            {"slug": "s1", "quote": "Run the gate after every edit"},
            {"slug": "s2", "quote": "An invented sentence entirely"},
            {"slug": "s3", "quote": "NONE"},
        ],
        "GREEN h1 opus": [{"slug": "s1", "quote": "Not checked because label filtered out"}],
    })
    rows = _rows_file(tmp_path / "h1.json", {"s1": skill_dir, "s2": skill_dir, "s3": skill_dir})
    rc = quotecheck.main(["journal", str(journal), "--label", "^RED ", "--rows", str(rows),
                          "--dir-field", "pre", "--json"])
    out = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert out["ok"] is True
    assert out["data"]["tally"] == {"OK": 1, "MISMATCH": 1, "NONE": 1}
    assert [r["key"] for r in out["data"]["rows"]] == ["s1", "s2", "s3"]


def test_journal_all_ok_exits_0_and_unknown_key_fails(tmp_path: Path, skill_dir: Path) -> None:
    journal = _journal(tmp_path / "j.jsonl", {"RED x": [{"slug": "s1", "quote": "Run the gate after every edit"}]})
    rows = _rows_file(tmp_path / "h.json", {"s1": skill_dir})
    args = ["journal", str(journal), "--label", "RED", "--rows", str(rows), "--dir-field", "pre"]
    assert quotecheck.main(args) == 0
    other = _rows_file(tmp_path / "o.json", {"zz": skill_dir})
    assert quotecheck.main(["journal", str(journal), "--label", "RED", "--rows", str(other),
                            "--dir-field", "pre"]) == 1


def test_journal_with_one_dir_for_every_row(tmp_path: Path, skill_dir: Path) -> None:
    journal = _journal(tmp_path / "j.jsonl", {"probe": [{"slug": "a", "quote": "Run the gate after every edit"}]})
    assert quotecheck.main(["journal", str(journal), "--label", "probe", "--dir", str(skill_dir)]) == 0


def test_a_journal_run_that_examines_nothing_is_a_refusal(
        tmp_path: Path, skill_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
    journal = _journal(tmp_path / "j.jsonl", {"GREEN only": [{"slug": "a", "quote": "x" * 20}]})
    rc = quotecheck.main(["journal", str(journal), "--label", "^RED", "--dir", str(skill_dir), "--json"])
    assert rc == 2
    assert json.loads(capsys.readouterr().out)["ok"] is False


def test_missing_dir_and_missing_dir_source_exit_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert quotecheck.main(["text", "--dir", str(tmp_path / "gone"), "--quote", "q" * 20]) == 2
    journal = _journal(tmp_path / "j.jsonl", {"RED": [{"slug": "a", "quote": "q" * 20}]})
    assert quotecheck.main(["journal", str(journal), "--label", "RED"]) == 2
    assert "needs --dir" in capsys.readouterr().err


def test_a_usage_error_under_json_prints_an_envelope(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        quotecheck.main(["text", "--json"])
    assert exc.value.code == 2
    env = json.loads(capsys.readouterr().out)
    assert env["ok"] is False and env["command"] == "quotecheck"


def test_text_mode_text_report(skill_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = quotecheck.main(["text", "--dir", str(skill_dir), "--quote", "An invented sentence entirely"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "MISMATCH" in out and "missing: an invented sentence entirely" in out


def test_every_repeated_quote_is_checked_not_only_the_last(skill_dir: Path,
                                                         capsys: pytest.CaptureFixture[str]) -> None:
    # argparse's default store keeps only the last --quote, so an invented first quote passed.
    rc = quotecheck.main(["text", "--dir", str(skill_dir), "--json",
                          "--quote", "An invented sentence entirely",
                          "--quote", "Run the gate after every edit"])
    data = json.loads(capsys.readouterr().out)["data"]
    assert rc == 1
    assert data["tally"] == {"MISMATCH": 1, "OK": 1}
    assert [r["key"] for r in data["rows"]] == ["1", "2"]


def test_a_misspelt_verdict_is_refused_not_read_as_a_failure() -> None:
    # failed() tested `not in ("OK", "NONE")`, so a verdict string nobody defined counted as a
    # failed quote instead of being caught where it was made.
    with pytest.raises(ValueError, match="OKK"):
        quotecheck.Verdict("OKK")
    with pytest.raises(ValueError, match="OKK"):
        quotecheck.ReportRow("label", "key", "OKK")


def test_the_verdict_keeps_its_wire_string(skill_dir: Path) -> None:
    v = _check("the gate", skill_dir)
    assert v.verdict is quotecheck.QuoteVerdict.TOO_SHORT
    assert json.dumps({"verdict": v.verdict}) == '{"verdict": "TOO-SHORT"}'
    row = quotecheck.ReportRow("lab", "k", v.verdict)
    assert quotecheck.tally([row]) == {"TOO-SHORT": 1}
    assert quotecheck.render_text([row]).splitlines()[1] == "TOO-SHORT   lab  k"


def _traced_peak_loading(journal: Path) -> int:
    tracemalloc.start()
    try:
        quotecheck.labelled_results(quotecheck.load_journal(journal), re.compile("^RED"))
        return tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()


def test_reading_a_journal_does_not_hold_the_records_it_does_not_report(tmp_path: Path) -> None:
    # Results of agents whose label does not match are dropped as they are read, so the journal's
    # size alone must not move the peak.
    def write(path: Path, n: int) -> Path:
        with path.open("w", encoding="utf-8") as fh:
            fh.write(json.dumps({"type": "started", "agentId": "r", "label": "RED x"}) + "\n")
            fh.write(json.dumps({"type": "result", "agentId": "r",
                                 "result": {"rows": [{"slug": "s", "quote": "q" * 20}]}}) + "\n")
            for i in range(n):
                fh.write(json.dumps({"type": "started", "agentId": f"g{i}", "label": "GREEN"}) + "\n")
                fh.write(json.dumps({"type": "result", "agentId": f"g{i}",
                                     "result": {"rows": [{"slug": "s", "quote": "z" * 2000}]}}) + "\n")
        return path

    small = _traced_peak_loading(write(tmp_path / "small.jsonl", 500))
    big = _traced_peak_loading(write(tmp_path / "big.jsonl", 4000))
    assert big - small < 1_000_000, f"peak grew {(big - small) / 1e6:.1f} MB for 8x the journal"


def test_a_result_logged_before_its_started_line_is_still_reported(tmp_path: Path,
                                                                   skill_dir: Path) -> None:
    lines = [{"type": "result", "agentId": "a", "result": {"rows": [
        {"slug": "s", "quote": "Run the gate after every edit"}]}},
             {"type": "started", "agentId": "a", "label": "RED late"}]
    journal = tmp_path / "j.jsonl"
    journal.write_text("\n".join(json.dumps(x) for x in lines) + "\n", encoding="utf-8")
    assert quotecheck.main(["journal", str(journal), "--label", "RED", "--dir", str(skill_dir)]) == 0


def test_an_unreadable_journal_is_a_usage_error(tmp_path: Path,
                                                capsys: pytest.CaptureFixture[str]) -> None:
    rc = quotecheck.main(["journal", str(tmp_path / "gone.jsonl"), "--label", "RED",
                          "--dir", str(tmp_path)])
    assert rc == 2
    assert "cannot read journal" in capsys.readouterr().err
