"""Full-text search over raw Claude Code transcripts."""
import json
import pathlib
import sqlite3
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import transcript_index as ti


def _write_transcript(root, name, messages):
    proj = root / name
    proj.mkdir(parents=True, exist_ok=True)
    path = proj / "session.jsonl"
    with path.open("w", encoding="utf-8") as fh:
        for m in messages:
            fh.write(json.dumps(m) + "\n")
    return path


def test_indexes_and_finds_a_message(tmp_path):
    _write_transcript(tmp_path, "-proj-a", [
        {"type": "user", "message": {"content": "the zpool scrub was wedged"}},
        {"type": "assistant", "message": {"content": "ran zpool clear"}},
    ])
    db = sqlite3.connect(":memory:")
    ti.ensure_schema(db)
    assert ti.index_dir(tmp_path, db) == 2
    hits = ti.search(db, "wedged")
    assert len(hits) == 1
    assert "zpool scrub" in hits[0]["text"]


def test_reindex_is_idempotent(tmp_path):
    _write_transcript(tmp_path, "-proj-a", [
        {"type": "user", "message": {"content": "hello world"}},
    ])
    db = sqlite3.connect(":memory:")
    ti.ensure_schema(db)
    ti.index_dir(tmp_path, db)
    ti.index_dir(tmp_path, db)
    assert len(ti.search(db, "hello")) == 1


def test_malformed_line_does_not_abort_the_run(tmp_path):
    proj = tmp_path / "-proj-b"
    proj.mkdir()
    (proj / "session.jsonl").write_text(
        '{"type":"user","message":{"content":"good"}}\nNOT JSON\n',
        encoding="utf-8")
    db = sqlite3.connect(":memory:")
    ti.ensure_schema(db)
    assert ti.index_dir(tmp_path, db) == 1


def test_search_returns_empty_not_error_on_no_match(tmp_path):
    db = sqlite3.connect(":memory:")
    ti.ensure_schema(db)
    assert ti.search(db, "nothingmatchesthis") == []
