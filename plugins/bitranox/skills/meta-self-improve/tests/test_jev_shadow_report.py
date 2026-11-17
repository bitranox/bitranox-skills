"""Tests for jev_shadow_report.read_records: what it keeps, and what it holds while it reads.

The monthly shadow log is capped at 100 MiB per file and holds every site and every date, while a
report usually asks for one site or a recent window. Reading every record of every file and only
then filtering held the whole log in memory (measured 5.5x the bytes on disk) to report on a
fraction of it. These tests pin that peak memory follows the records KEPT, not the records read.
"""

import json
import tracemalloc
from pathlib import Path

import jev_shadow_report as rpt

# Built with chr(): a raw separator in this source would itself be the hazard under test.
LINE_SEPARATOR = chr(0x2028)
NEXT_LINE = chr(0x85)


def _record(n: int, site: str, day: str) -> str:
    return json.dumps({"site": site, "ts": f"{day}T10:00:00Z", "id": f"item-{n}",
                       "questions_sha": "x", "agent": {"q": True},
                       "jev": {"q": {"value": 0.9, "confidence": 0.9}},
                       "note": "padding " * 20})


def _log(path: Path, *, kept: int, other: int) -> Path:
    lines = [_record(n, "dream-prune", "2026-10-05") for n in range(kept)]
    lines += [_record(n, "other-site", "2026-10-05") for n in range(other)]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _peak_reading(path: Path) -> tuple[int, rpt.LogRead]:
    tracemalloc.start()
    try:
        log = rpt.read_records([path], site="dream-prune", since=None)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return peak, log


def test_peak_memory_follows_the_kept_records_not_the_file(tmp_path: Path):
    small_peak, small = _peak_reading(_log(tmp_path / "small.jsonl", kept=20, other=500))
    large_peak, large = _peak_reading(_log(tmp_path / "large.jsonl", kept=20, other=4000))
    assert len(small.records) == len(large.records) == 20
    assert large_peak < 2 * small_peak, \
        f"8x the filtered-out records raised the peak from {small_peak} to {large_peak} bytes"


def test_the_kept_records_and_their_order_are_those_of_a_full_read(tmp_path: Path):
    path = tmp_path / "log.jsonl"
    lines = [_record(0, "dream-prune", "2026-09-30"), _record(1, "other", "2026-10-05"),
             "not json", "", _record(2, "dream-prune", "2026-10-02"),
             _record(3, "dream-prune", "2026-10-09")]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log = rpt.read_records([path], site="dream-prune", since="2026-10-01")
    assert [r["id"] for r in log.records] == ["item-2", "item-3"]
    assert log.skipped == ["log.jsonl:3"]


def test_a_line_separator_inside_a_string_does_not_cut_the_record(tmp_path: Path):
    path = tmp_path / "log.jsonl"
    item = f"a{LINE_SEPARATOR}b{NEXT_LINE}c"
    rec = json.dumps({"site": "s", "ts": "2026-10-01", "id": item}, ensure_ascii=False)
    path.write_bytes((rec + "\r\n").encode("utf-8"))
    log = rpt.read_records([path], site="s", since=None)
    assert [r["id"] for r in log.records] == [item] and log.skipped == []


def test_an_undecodable_file_is_skipped_whole_and_keeps_none_of_its_records(tmp_path: Path):
    path = tmp_path / "bad.jsonl"
    path.write_bytes((_record(0, "s", "2026-10-01") + "\n").encode("utf-8") + b"\xff\xfe\n")
    good = tmp_path / "good.jsonl"
    good.write_text(_record(1, "s", "2026-10-01") + "\n", encoding="utf-8")
    log = rpt.read_records([path, good], site="s", since=None)
    assert [r["id"] for r in log.records] == ["item-1"]
    assert log.skipped == ["bad.jsonl"]
