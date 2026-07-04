"""Tests for store-edit-guard.py: the live slug store (`.claude-memory/`) and the CLAUDE.local.md
pointer blocks are engine-written ONLY - hand edits via Edit/Write/MultiEdit are denied. ASCII."""
import json
from pathlib import Path

import pytest

import store_edit_guard as G
import uuid_store as us


def _event(tool, file_path, tool_input=None, cwd="/w"):
    inp = {"file_path": file_path}
    inp.update(tool_input or {})
    return {"tool_name": tool, "tool_input": inp, "cwd": cwd}


def _block(pointers=None, scope="sc"):
    return us.upsert_pointer_block("", scope, pointers or [us.Pointer(slug="a-fact", title="A", hook="h")])


# ---- store paths (live + legacy) -----------------------------------------------------------------

def test_denies_write_inside_claude_memory_store():
    ev = _event("Write", "/tree/.claude-memory/facts/some-fact.md", {"content": "x"})
    assert G.decide(ev, {}) is not None


def test_denies_edit_inside_claude_memory_archive():
    ev = _event("Edit", "/tree/.claude-memory/.archive/old.md",
                {"old_string": "a", "new_string": "b"})
    assert G.decide(ev, {}) is not None


def test_denies_legacy_store_path_too():
    ev = _event("Write", "/tree/.claude-bx-selflearning/index.md", {"content": "x"})
    assert G.decide(ev, {}) is not None


def test_allows_unrelated_paths():
    assert G.decide(_event("Write", "/tree/src/main.py", {"content": "x"}), {}) is None
    assert G.decide(_event("Edit", "/tree/README.md", {"old_string": "a", "new_string": "b"}), {}) is None


def test_deny_message_names_live_layout_and_engine_commands():
    msg = G.decide(_event("Write", "/tree/.claude-memory/facts/f.md", {"content": "x"}), {})
    assert "memory_engine" in msg and "add" in msg and "move" in msg


# ---- CLAUDE.local.md block-region checks ---------------------------------------------------------

@pytest.fixture
def local_file(tmp_path):
    p = tmp_path / "CLAUDE.local.md"
    p.write_text("# my notes\n\nkeep me\n\n" + _block(), encoding="utf-8")
    return p


def test_denies_edit_overlapping_pointer_block(local_file, tmp_path):
    ev = _event("Edit", str(local_file), {"old_string": "(mem:a-fact)", "new_string": "(mem:b)"},
                cwd=str(tmp_path))
    assert G.decide(ev, {}) is not None


def test_allows_edit_outside_the_block(local_file, tmp_path):
    ev = _event("Edit", str(local_file), {"old_string": "keep me", "new_string": "kept"},
                cwd=str(tmp_path))
    assert G.decide(ev, {}) is None


def test_denies_edit_injecting_fence_markers(local_file, tmp_path):
    ev = _event("Edit", str(local_file),
                {"old_string": "keep me", "new_string": "keep me\n" + us.INDEX_BEGIN},
                cwd=str(tmp_path))
    assert G.decide(ev, {}) is not None


def test_denies_write_that_alters_the_block(local_file, tmp_path):
    new = local_file.read_text(encoding="utf-8").replace("(mem:a-fact)", "(mem:tampered)")
    ev = _event("Write", str(local_file), {"content": new}, cwd=str(tmp_path))
    assert G.decide(ev, {}) is not None


def test_denies_write_that_deletes_the_block(local_file, tmp_path):
    ev = _event("Write", str(local_file), {"content": "# my notes\n\nkeep me\n"}, cwd=str(tmp_path))
    assert G.decide(ev, {}) is not None


def test_allows_write_preserving_block_bytes(local_file, tmp_path):
    cur = local_file.read_text(encoding="utf-8")
    ev = _event("Write", str(local_file), {"content": cur.replace("keep me", "kept, edited")},
                cwd=str(tmp_path))
    assert G.decide(ev, {}) is None


def test_allows_write_of_fresh_claude_local_md_without_block(tmp_path):
    p = tmp_path / "CLAUDE.local.md"                     # does not exist yet
    ev = _event("Write", str(p), {"content": "just user notes\n"}, cwd=str(tmp_path))
    assert G.decide(ev, {}) is None


def test_denies_write_introducing_a_block_by_hand(tmp_path):
    p = tmp_path / "CLAUDE.local.md"
    ev = _event("Write", str(p), {"content": _block()}, cwd=str(tmp_path))
    assert G.decide(ev, {}) is not None


def test_legacy_fence_block_is_guarded_too(tmp_path):
    p = tmp_path / "CLAUDE.local.md"
    inner = "- [T](uuid:11111111-0000-5000-8000-000000000000) - h <!-- bx:slug=t -->\n"
    p.write_text("%s\n%s%s\n" % (us.LEGACY_INDEX_BEGIN, inner, us.LEGACY_INDEX_END), encoding="utf-8")
    ev = _event("Edit", str(p), {"old_string": "uuid:11111111", "new_string": "uuid:22222222"},
                cwd=str(tmp_path))
    assert G.decide(ev, {}) is not None


def test_multiedit_any_overlapping_edit_denies(local_file, tmp_path):
    ev = {"tool_name": "MultiEdit", "cwd": str(tmp_path),
          "tool_input": {"file_path": str(local_file),
                         "edits": [{"old_string": "keep me", "new_string": "kept"},
                                   {"old_string": "(mem:a-fact)", "new_string": "(mem:x)"}]}}
    assert G.decide(ev, {}) is not None


def test_multiedit_all_outside_allows(local_file, tmp_path):
    ev = {"tool_name": "MultiEdit", "cwd": str(tmp_path),
          "tool_input": {"file_path": str(local_file),
                         "edits": [{"old_string": "keep me", "new_string": "kept"},
                                   {"old_string": "# my notes", "new_string": "# notes"}]}}
    assert G.decide(ev, {}) is None


# ---- bypass + fail-open + path handling ----------------------------------------------------------

def test_env_bypass_allows_everything(local_file, tmp_path):
    env = {"BITRANOX_MEMORY_ENGINE": "1"}
    assert G.decide(_event("Write", "/tree/.claude-memory/facts/f.md", {"content": "x"}), env) is None
    ev = _event("Edit", str(local_file), {"old_string": "(mem:a-fact)", "new_string": "x"},
                cwd=str(tmp_path))
    assert G.decide(ev, env) is None


def test_relative_path_resolved_against_cwd(tmp_path, local_file):
    ev = _event("Edit", "CLAUDE.local.md", {"old_string": "(mem:a-fact)", "new_string": "x"},
                cwd=str(tmp_path))
    assert G.decide(ev, {}) is not None


def test_fail_open_on_unreadable_current_file(tmp_path):
    ev = _event("Edit", str(tmp_path / "missing" / "CLAUDE.local.md"),
                {"old_string": "a", "new_string": "b"}, cwd=str(tmp_path))
    assert G.decide(ev, {}) is None                      # no file, no markers -> allow


def test_non_target_tools_allowed():
    assert G.decide({"tool_name": "Read", "tool_input": {"file_path": "/tree/.claude-memory/f.md"}},
                    {}) is None
    assert G.decide({"tool_name": "Bash", "tool_input": {"file_path": "/tree/.claude-memory/f.md"}},
                    {}) is None


def test_missing_tool_input_is_allowed():
    assert G.decide({"tool_name": "Edit"}, {}) is None


def test_main_blocks_with_exit_2_and_stderr(monkeypatch, capsys):
    import io
    ev = _event("Write", "/tree/.claude-memory/facts/f.md", {"content": "x"})
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(ev)))
    monkeypatch.delenv("BITRANOX_MEMORY_ENGINE", raising=False)
    assert G.main() == 2                                 # non-zero blocks the tool call
    assert "memory_engine" in capsys.readouterr().err


def test_main_allows_when_env_set(monkeypatch, capsys):
    import io
    ev = _event("Write", "/tree/.claude-memory/facts/f.md", {"content": "x"})
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(ev)))
    monkeypatch.setenv("BITRANOX_MEMORY_ENGINE", "1")
    assert G.main() == 0
    assert capsys.readouterr().err == ""


def test_main_fail_open_on_bad_stdin(monkeypatch, capsys):
    import io
    monkeypatch.setattr("sys.stdin", io.StringIO("not json"))
    assert G.main() == 0                                 # allow, never wedge
    assert capsys.readouterr().err == ""
