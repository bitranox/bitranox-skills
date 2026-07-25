"""Tests for conflict_scan.py - find git merge-conflict markers. ASCII only."""
import conflict_scan as C


def test_scan_text_finds_all_three_markers():
    text = (
        "line one\n"
        "<<<<<<< HEAD\n"
        "ours\n"
        "=======\n"
        "theirs\n"
        ">>>>>>> branch\n"
        "line last\n"
    )
    hits = C.scan_text(text)
    assert [ln for ln, _ in hits] == [2, 4, 6]
    assert hits[0][1].startswith("<<<<<<<")


def test_scan_text_clean_is_empty():
    assert C.scan_text("no markers here\njust code\n") == []


def test_marker_must_be_at_line_start():
    # a marker in the middle of a line (e.g. in a string/doc) is NOT a conflict marker
    text = 'print("<<<<<<< not a conflict")\n=======\n'
    hits = C.scan_text(text)
    assert [ln for ln, _ in hits] == [2]   # only the real line-start ======= counts


def test_scan_paths_reports_per_file(tmp_path):
    good = tmp_path / "clean.py"; good.write_text("ok\n", encoding="utf-8")
    bad = tmp_path / "conflict.py"; bad.write_text("<<<<<<< HEAD\nx\n=======\ny\n>>>>>>> b\n", encoding="utf-8")
    res = C.scan_paths([str(good), str(bad)])
    assert str(good) not in res
    assert res[str(bad)] == [1, 3, 5]
