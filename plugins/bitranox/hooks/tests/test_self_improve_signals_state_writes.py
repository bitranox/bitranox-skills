"""State writes a caller reports as done must fail LOUDLY, and a capped transcript read must never
hand back an offset past text it did not return. All content ASCII.

The writers under test (the review watermark and the promotion-sighting store) used to swallow
every OSError, so a failed write returned exactly what a successful one returned. The only caller
that noticed was the one that happened to read the value back.
"""

import json
import os

import pytest

import self_improve_signals as S

NO_CHMOD = not hasattr(os, "geteuid") or os.geteuid() == 0


@pytest.fixture
def home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    (h / ".claude").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


def _block_with_a_dir(path):
    """Make `path` impossible to write as a file, on every platform: put a directory there."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.mkdir()


# ---- a failed write is raised, typed, and still an OSError --------------------------------------

def test_state_write_error_is_an_oserror():
    # every fail-open handler that already catches OSError keeps catching it
    assert issubclass(S.StateWriteError, OSError)


def test_set_watermark_raises_when_the_write_fails(home, tmp_path):
    _block_with_a_dir(S.watermark_file("/p/w"))
    with pytest.raises(S.StateWriteError):
        S.set_watermark("/p/w", str(tmp_path / "t.jsonl"), "dream", 5)
    assert S.get_watermark("/p/w", str(tmp_path / "t.jsonl"), "dream") == 0


def test_set_watermark_that_lands_returns_quietly(home, tmp_path):
    """Control: a writable store records the mark and raises nothing."""
    S.set_watermark("/p/w", str(tmp_path / "t.jsonl"), "dream", 5)
    assert S.get_watermark("/p/w", str(tmp_path / "t.jsonl"), "dream") == 5


def test_set_watermark_refuses_a_non_integer_offset(home, tmp_path):
    # it used to be swallowed, so the caller reported a mark that was never recorded
    with pytest.raises(ValueError):
        S.set_watermark("/p/w", str(tmp_path / "t.jsonl"), "dream", "not-a-number")


def test_note_promotion_candidate_raises_when_the_write_fails(home):
    _block_with_a_dir(S.promotion_file())
    with pytest.raises(S.StateWriteError):
        S.note_promotion_candidate("/p/a", "k")


def test_clear_promotion_candidate_raises_when_the_store_cannot_be_updated(home):
    f = S.promotion_file()
    _block_with_a_dir(f)
    (f / "keep").write_text("x", encoding="utf-8")        # a non-empty dir cannot be replaced
    with pytest.raises(S.StateWriteError):
        S.clear_promotion_candidate("/p/a", "k")


def test_clear_promotion_candidate_that_lands_forgets_the_key(home):
    """Control: a writable store is cleared and raises nothing."""
    S.note_promotion_candidate("/p/a", "k")
    S.clear_promotion_candidate("/p/a", "k")
    assert S.promotion_dwell("/p/a", "k") == 0


# ---- an existing store that cannot be READ is never overwritten --------------------------------

@pytest.mark.skipif(NO_CHMOD, reason="needs a non-root POSIX user for a write-only file")
def test_an_unreadable_watermark_store_is_not_clobbered(home, tmp_path):
    # Read failure used to read as "no marks", and the write then replaced every other reviewer's
    # mark with this one alone.
    S.set_watermark("/p/w", "/t/other.jsonl", "audit", 77)
    f = S.watermark_file("/p/w")
    before = f.read_bytes()
    f.chmod(0o200)                                        # writable, not readable
    try:
        with pytest.raises(S.StateWriteError):
            S.set_watermark("/p/w", str(tmp_path / "t.jsonl"), "dream", 5)
    finally:
        f.chmod(0o644)
    assert f.read_bytes() == before


@pytest.mark.skipif(NO_CHMOD, reason="needs a non-root POSIX user for a write-only file")
def test_an_unreadable_sighting_store_is_not_clobbered(home):
    S.note_promotion_candidate("/p/a", "other")
    S.note_promotion_candidate("/p/b", "other")
    f = S.promotion_file()
    before = f.read_bytes()
    f.chmod(0o200)
    try:
        with pytest.raises(S.StateWriteError):
            S.note_promotion_candidate("/p/a", "k")
    finally:
        f.chmod(0o644)
    assert f.read_bytes() == before
    assert S.promotion_dwell("/p/a", "other") == 2


@pytest.mark.skipif(NO_CHMOD, reason="needs a non-root POSIX user for a read-only dir")
def test_a_failed_write_leaves_the_previous_store_intact(home, tmp_path):
    # the write goes through a temp file and a replace, so a failure cannot leave a torn file
    S.set_watermark("/p/w", str(tmp_path / "t.jsonl"), "dream", 5)
    f = S.watermark_file("/p/w")
    before = f.read_bytes()
    f.parent.chmod(0o555)
    try:
        with pytest.raises(S.StateWriteError):
            S.set_watermark("/p/w", str(tmp_path / "t.jsonl"), "dream", 9)
    finally:
        f.parent.chmod(0o755)
    assert f.read_bytes() == before
    assert json.loads(before)["dream"][str(tmp_path / "t.jsonl")] == 5


@pytest.mark.skipif(NO_CHMOD, reason="root writes through a read-only mode")
def test_a_read_only_store_is_refused_not_renamed_over(home, tmp_path):
    # a replace-based write would succeed over a 0444 file on POSIX and fail on Windows
    S.set_watermark("/p/w", str(tmp_path / "t.jsonl"), "dream", 5)
    f = S.watermark_file("/p/w")
    f.chmod(0o444)
    try:
        with pytest.raises(S.StateWriteError):
            S.set_watermark("/p/w", str(tmp_path / "t.jsonl"), "dream", 9)
    finally:
        f.chmod(0o644)
    assert S.get_watermark("/p/w", str(tmp_path / "t.jsonl"), "dream") == 5


def test_a_corrupt_store_is_replaced_not_refused(home, tmp_path):
    """Control for the unreadable case: a store that reads but does not PARSE holds nothing to
    lose, and refusing there would wedge the watermark for good."""
    f = S.watermark_file("/p/w")
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("not json", encoding="utf-8")
    S.set_watermark("/p/w", str(tmp_path / "t.jsonl"), "dream", 5)
    assert S.get_watermark("/p/w", str(tmp_path / "t.jsonl"), "dream") == 5


# ---- a capped transcript read never returns an offset past what it returned ----------------------

def _abc(tmp_path):
    tp = tmp_path / "t.jsonl"
    tp.write_bytes(b"A" * 9 + b"\n" + b"B" * 9 + b"\n" + b"C" * 9 + b"\n")   # 30 bytes
    return tp


def _drain(proj, tp, max_bytes):
    """Read and mark until nothing is new; return what was read, in order."""
    parts = []
    for _ in range(100):                     # bound: a regression must fail, not hang the suite
        text, off = S.unreviewed_transcript_text(proj, "llm", str(tp), max_bytes=max_bytes)
        if not text:
            return parts
        parts.append(text)
        S.set_watermark(proj, str(tp), "llm", off)
    raise AssertionError("the reader never reached the end: %r" % parts[-3:])


def test_marking_the_returned_offset_never_skips_unread_text(home, tmp_path):
    # The cap used to return the NEWEST part with the offset of the file END, so a caller that
    # marked that offset discharged the older part unread (here: the A line).
    tp = _abc(tmp_path)
    parts = _drain("/p/x", tp, max_bytes=20)
    assert "".join(parts) == tp.read_text(encoding="utf-8")


def test_an_uncapped_read_returns_everything_at_once(home, tmp_path):
    """Control: under the cap there is one part and it is the whole file."""
    tp = _abc(tmp_path)
    assert _drain("/p/x", tp, max_bytes=1000) == [tp.read_text(encoding="utf-8")]


def test_a_capped_read_returns_the_oldest_whole_lines(home, tmp_path):
    tp = _abc(tmp_path)
    text, off = S.unreviewed_transcript_text("/p/x", "llm", str(tp), max_bytes=20)
    assert text == "A" * 9 + "\n" + "B" * 9 + "\n" and off == 20


def test_a_capped_read_cuts_after_the_last_newline_in_range(home, tmp_path):
    tp = _abc(tmp_path)
    text, off = S.unreviewed_transcript_text("/p/x", "llm", str(tp), max_bytes=19)
    assert text == "A" * 9 + "\n" and off == 10


def test_a_line_longer_than_the_cap_is_returned_in_pieces_never_as_nothing(home, tmp_path):
    # A single unreviewed line longer than the cap used to come back as "" - read as "nothing new"
    # while every byte of it was unreviewed.
    tp = tmp_path / "t.jsonl"
    tp.write_bytes(b"x" * 50 + b"\n")
    parts = _drain("/p/x", tp, max_bytes=20)
    assert parts and "".join(parts) == "x" * 50 + "\n"


def test_a_capped_read_resumes_at_the_mark(home, tmp_path):
    tp = _abc(tmp_path)
    S.set_watermark("/p/x", str(tp), "llm", 10)
    text, off = S.unreviewed_transcript_text("/p/x", "llm", str(tp), max_bytes=15)
    assert text == "B" * 9 + "\n" and off == 20
    text, off = S.unreviewed_transcript_text("/p/x", "llm", str(tp), max_bytes=25)
    assert text == "B" * 9 + "\n" + "C" * 9 + "\n" and off == 30   # the cap reaches the end
