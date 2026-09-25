"""Full-text search over raw Claude Code transcripts."""
import json
import os
import pathlib
import sqlite3
import subprocess
import sys

import pytest

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


def test_a_stray_quote_is_literal_text_by_default(tmp_path):
    db = sqlite3.connect(":memory:")
    ti.ensure_schema(db)
    assert ti.search(db, '"unterminated') == []


def test_a_malformed_raw_fts_query_raises_a_query_error(tmp_path):
    """A syntax error answered nothing; it must not be indistinguishable from a real miss."""
    db = sqlite3.connect(":memory:")
    ti.ensure_schema(db)
    with pytest.raises(ti.QueryError, match="unterminated|syntax error"):
        ti.search(db, '"unterminated', raw=True)


FILENAME_TEXT = "fatal: not a git repository in anchor_edit.py, used ssh-keygen"


@pytest.fixture
def indexed(tmp_path):
    _write_transcript(tmp_path, "-proj-a", [
        {"type": "user", "message": {"content": FILENAME_TEXT}},
        {"type": "assistant", "message": {"content": "the zpool scrub was wedged"}},
    ])
    db = sqlite3.connect(":memory:")
    ti.ensure_schema(db)
    ti.index_dir(tmp_path, db)
    return db


@pytest.mark.parametrize("query", [
    "anchor_edit.py", "ssh-keygen", "fatal: not a git repository", "not", "OR",
])
def test_filenames_flags_and_error_text_are_found_literally(indexed, query):
    if query == "OR":
        assert ti.search(indexed, query) == []  # the word, not the operator: no crash
        return
    hits = ti.search(indexed, query)
    assert [h["text"] for h in hits] == [FILENAME_TEXT]


@pytest.mark.parametrize("query", ["anchor_edit", "repository", "zpool scrub", '"anchor_edit.py"'])
def test_control_queries_that_always_worked(indexed, query):
    assert ti.search(indexed, query)


def test_multi_word_query_keeps_and_semantics_not_adjacency(indexed):
    assert ti.search(indexed, "scrub zpool")
    assert ti.search(indexed, "zpool nothingelse") == []


def test_raw_fts_syntax_is_still_available(indexed):
    assert ti.search(indexed, "zpool OR nothingelse", raw=True)
    assert ti.search(indexed, "zpool OR nothingelse") == []


def test_empty_query_is_refused(indexed):
    with pytest.raises(ti.QueryError):
        ti.search(indexed, "   ")


def test_list_content_with_only_tool_parts_is_not_indexed(tmp_path):
    _write_transcript(tmp_path, "-proj-c", [
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Bash"}, {"type": "tool_use", "name": "Read"}]}},
        {"type": "assistant", "message": {"content": [
            {"type": "thinking", "thinking": "x"}, {"type": "text", "text": ""},
            {"type": "tool_use", "name": "Bash"}]}},
        {"type": "assistant", "message": {"content": [
            {"type": "text", "text": "alpha"}, {"type": "tool_use"}, {"type": "text", "text": "beta"}]}},
    ])
    db = sqlite3.connect(":memory:")
    ti.ensure_schema(db)
    assert ti.index_dir(tmp_path, db) == 1
    assert [h["text"] for h in ti.search(db, "alpha beta")] == ["alpha  beta"]


def test_a_string_message_is_indexed(tmp_path):
    _write_transcript(tmp_path, "-proj-d", [{"type": "system", "message": "compacted strmsgword"}])
    db = sqlite3.connect(":memory:")
    ti.ensure_schema(db)
    assert ti.index_dir(tmp_path, db) == 1
    assert ti.search(db, "strmsgword")[0]["role"] == "system"


def test_a_bom_on_the_first_line_does_not_drop_it(tmp_path):
    proj = tmp_path / "-proj-e"
    proj.mkdir()
    (proj / "s.jsonl").write_bytes(
        b"\xef\xbb\xbf" + json.dumps({"type": "user", "message": {"content": "bomword"}}).encode()
        + b"\n")
    db = sqlite3.connect(":memory:")
    ti.ensure_schema(db)
    assert ti.index_dir(tmp_path, db) == 1


@pytest.mark.skipif(sys.platform == "win32" or not hasattr(os, "geteuid") or os.geteuid() == 0,
                    reason="chmod 000 does not deny access on Windows or to root")
def test_an_unreadable_directory_is_reported_not_silently_skipped(tmp_path):
    _write_transcript(tmp_path, "-proj-ok", [{"type": "user", "message": {"content": "okword"}}])
    locked = tmp_path / "-proj-locked"
    _write_transcript(tmp_path, "-proj-locked", [{"type": "user", "message": {"content": "x"}}])
    locked.chmod(0)
    try:
        db = sqlite3.connect(":memory:")
        ti.ensure_schema(db)
        errors: list[str] = []
        assert ti.index_dir(tmp_path, db, errors=errors) == 1
        assert any("-proj-locked" in e for e in errors)
    finally:
        locked.chmod(0o755)


# ---- CLI: run the real script with HOME pointed into tmp_path, never the real ~/.claude ----

SCRIPT = pathlib.Path(__file__).resolve().parent.parent / "scripts" / "transcript_index.py"


def _cli(home, *args, env_extra=None):
    env = {**os.environ, "HOME": str(home), "USERPROFILE": str(home)}
    env.update(env_extra or {})
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True,
                          env=env, check=False)


@pytest.fixture
def home(tmp_path):
    projects = tmp_path / ".claude" / "projects"
    _write_transcript(projects, "-proj-a", [
        {"type": "user", "message": {"content": FILENAME_TEXT}},
        {"type": "assistant", "message": {"content": "fixed it \u2192 done"}},
    ])
    p = _cli(tmp_path, "index")
    assert p.returncode == 0, p.stderr
    assert b"indexed 2 new message(s)" in p.stdout
    return tmp_path


def test_cli_hit_exits_0(home):
    p = _cli(home, "search", "ssh-keygen")
    assert p.returncode == 0, p.stderr
    assert b"anchor_edit.py" in p.stdout


def test_cli_miss_exits_1_with_the_caveat(home):
    p = _cli(home, "search", "nonexistentword", "--json")
    assert p.returncode == 1
    doc = json.loads(p.stdout)
    assert doc["ok"] is True and doc["data"] == [] and "caveat" in doc


def test_cli_query_error_is_ok_false_exit_2_without_the_caveat(home):
    p = _cli(home, "search", "--fts", "anchor_edit.py", "--json")
    assert p.returncode == 2
    doc = json.loads(p.stdout)
    assert doc["ok"] is False
    assert "syntax error" in doc["error"]
    assert "caveat" not in doc


def test_cli_query_error_plain_goes_to_stderr(home):
    p = _cli(home, "search", "--fts", "anchor_edit.py")
    assert p.returncode == 2
    assert b"syntax error" in p.stderr
    assert b"not narrated" not in p.stderr


def test_cli_cp1252_stdout_does_not_crash(home):
    p = _cli(home, "search", "fixed", env_extra={"PYTHONIOENCODING": "cp1252", "PYTHONUTF8": "0"})
    assert p.returncode == 0, p.stderr
    assert b"fixed it" in p.stdout


def test_indexes_a_subagent_transcript_nested_below_the_session(tmp_path):
    """Subagent transcripts live at <project>/<session>/subagents/agent-*.jsonl.

    A `*/*.jsonl` walk reaches only the main-session files one level down, so it silently indexed
    878 of 2,090 transcripts on this machine and a search for work a subagent narrated came back
    empty - which reads exactly like "never happened", the one conclusion this tool warns against.
    """
    nested = tmp_path / "-proj-a" / "8ce95402" / "subagents"
    nested.mkdir(parents=True)
    (nested / "agent-abc.jsonl").write_text(
        json.dumps({"type": "assistant", "message": {"content": "the modulejail whitelist was it"}})
        + "\n", encoding="utf-8")
    db = sqlite3.connect(":memory:")
    ti.ensure_schema(db)
    assert ti.index_dir(tmp_path, db) == 1
    assert ti.search(db, "modulejail")


def test_the_project_label_survives_a_nested_transcript(tmp_path):
    """The label must stay the PROJECT, not the session dir a nested file happens to sit in."""
    nested = tmp_path / "-proj-b" / "sess1" / "subagents"
    nested.mkdir(parents=True)
    (nested / "agent-x.jsonl").write_text(
        json.dumps({"type": "user", "message": {"content": "xyzneedle"}}) + "\n",
        encoding="utf-8")
    db = sqlite3.connect(":memory:")
    ti.ensure_schema(db)
    ti.index_dir(tmp_path, db)
    hits = ti.search(db, "xyzneedle")
    assert hits and hits[0]["project"] == "-proj-b"


# --- only the message TEXT is searchable; the label columns are not ------------------------------

# The DDL every index built before the label columns became UNINDEXED carries. An old database on a
# user's machine keeps it until something rebuilds the table, so the migration is tested against it.
OLD_DDL = ("CREATE VIRTUAL TABLE messages "
           "USING fts5(project, path, role, text, tokenize='porter unicode61')")


def _labelled_corpus(root):
    """One message says 'animals'; NEITHER says 'zebraproject', which is only in their path."""
    return _write_transcript(root, "-media-zebraproject", [
        {"type": "user", "message": {"content": "nothing about animals here"}},
        {"type": "assistant", "message": {"content": "a reply that names no project"}},
    ])


def _fresh_index(root):
    _labelled_corpus(root)
    db = sqlite3.connect(":memory:")
    ti.ensure_schema(db)
    ti.index_dir(root, db)
    return db


def test_a_word_only_in_the_transcript_path_matches_nothing(tmp_path):
    """A path word matched EVERY message in that transcript, so a miss read as a hit."""
    db = _fresh_index(tmp_path)
    assert ti.search(db, "zebraproject") == []
    assert [h["text"] for h in ti.search(db, "animals")] == ["nothing about animals here"]


def test_a_word_only_in_the_role_matches_nothing(tmp_path):
    """'assistant' is a role label, not something the message said."""
    db = _fresh_index(tmp_path)
    assert ti.search(db, "assistant") == []
    assert [h["text"] for h in ti.search(db, "reply")] == ["a reply that names no project"]


def test_the_label_columns_are_still_returned_with_a_hit(tmp_path):
    db = _fresh_index(tmp_path)
    (hit,) = ti.search(db, "animals")
    path = tmp_path / "-media-zebraproject" / "session.jsonl"
    assert (hit["project"], hit["path"], hit["role"]) == ("-media-zebraproject", str(path), "user")


def _old_database(db_path, transcript):
    """A database exactly as the pre-fix tool left it: old DDL, two rows, their seen keys."""
    db = sqlite3.connect(db_path)
    db.execute(OLD_DDL)
    db.execute("CREATE TABLE seen (key TEXT PRIMARY KEY)")
    for lineno, (role, text) in enumerate([("user", "nothing about animals here"),
                                           ("assistant", "a reply that names no project")]):
        db.execute("INSERT INTO seen(key) VALUES (?)", (f"{transcript}:{lineno}",))
        db.execute("INSERT INTO messages(project, path, role, text) VALUES (?, ?, ?, ?)",
                   ("-media-zebraproject", str(transcript), role, text))
    db.commit()
    db.close()


def test_an_old_schema_database_is_migrated_not_left_matching_paths(tmp_path):
    """CREATE ... IF NOT EXISTS never touched an existing table, so an old index would have kept
    matching path words after the fix while the code claimed otherwise."""
    transcript = _labelled_corpus(tmp_path / "projects")
    db_path = tmp_path / "old.db"
    _old_database(db_path, transcript)
    db = sqlite3.connect(db_path)
    assert ti.search(db, "zebraproject")          # control: the old table DOES match the path
    ti.ensure_schema(db)
    assert ti.search(db, "zebraproject") == []
    assert ti.search(db, "assistant") == []
    # Nothing was lost: every row, its labels, its newest-first order and its seen key survive.
    assert [h["text"] for h in ti.search(db, "about OR reply", raw=True)] == [
        "a reply that names no project", "nothing about animals here"]
    assert ti.search(db, "animals")[0]["project"] == "-media-zebraproject"
    assert ti.index_dir(tmp_path / "projects", db) == 0


def test_migrating_twice_is_a_no_op(tmp_path):
    transcript = _labelled_corpus(tmp_path / "projects")
    db_path = tmp_path / "old.db"
    _old_database(db_path, transcript)
    db = sqlite3.connect(db_path)
    ti.ensure_schema(db)
    ti.ensure_schema(db)
    assert len(ti.search(db, "about OR reply", raw=True)) == 2
    assert ti.search(db, "zebraproject") == []


def test_a_migration_that_fails_part_way_keeps_the_old_index(tmp_path):
    """The sqlite3 module opens no implicit transaction before DDL, so without an explicit BEGIN
    the DROP committed on its own and a failed rebuild left no index at all."""
    transcript = _labelled_corpus(tmp_path / "projects")
    db_path = tmp_path / "old.db"
    _old_database(db_path, transcript)
    db = sqlite3.connect(db_path)
    with pytest.raises(sqlite3.OperationalError, match="nosuchmodule"):
        ti._migrate_messages(db, ddl="CREATE VIRTUAL TABLE messages USING nosuchmodule(x)")
    db.close()
    kept = sqlite3.connect(db_path).execute("SELECT text FROM messages ORDER BY rowid").fetchall()
    assert kept == [("nothing about animals here",), ("a reply that names no project",)]


def test_cli_search_on_an_old_database_does_not_match_path_words(tmp_path):
    """End to end: the database a previous version left in ~/.claude is what a user searches."""
    transcript = _labelled_corpus(tmp_path / ".claude" / "projects")
    _old_database(tmp_path / ".claude" / "transcript-index.db", transcript)
    p = _cli(tmp_path, "search", "zebraproject", "--json")
    assert p.returncode == 1, p.stdout
    assert json.loads(p.stdout)["data"] == []
    p = _cli(tmp_path, "search", "animals", "--json")
    assert p.returncode == 0, p.stderr
    assert [h["text"] for h in json.loads(p.stdout)["data"]] == ["nothing about animals here"]
