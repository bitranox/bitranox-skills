"""Tests for store-edit-guard.py: the live slug store (`.claude-memory/`) and the CLAUDE.local.md
pointer blocks are engine-written ONLY - hand edits via Edit/Write/MultiEdit/NotebookEdit are denied. ASCII."""
import io
import json

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


# ---- the store's own backlog: <store>/OPEN-WORK.md is not a fact and no engine verb writes it ----

def test_allows_edit_and_write_of_the_store_backlog():
    edit = _event("Edit", "/tree/.claude-memory/OPEN-WORK.md", {"old_string": "a", "new_string": "b"})
    write = _event("Write", "/tree/.claude-memory/OPEN-WORK.md", {"content": "# backlog\n"})
    assert G.decide(edit, {}) is None
    assert G.decide(write, {}) is None


def test_allows_the_store_backlog_through_a_relative_path():
    ev = _event("Edit", "OPEN-WORK.md", {"old_string": "a", "new_string": "b"}, cwd="/tree/.claude-memory")
    assert G.decide(ev, {}) is None


def test_a_fact_edit_beside_the_backlog_is_still_denied():
    ev = _event("Edit", "/tree/.claude-memory/facts/some-fact.md", {"old_string": "a", "new_string": "b"})
    assert G.decide(ev, {}) is not None


@pytest.mark.parametrize("path", [
    "/tree/.claude-memory/facts/OPEN-WORK.md",          # nested one level deeper
    "/tree/.claude-memory/.archive/OPEN-WORK.md",
    "/tree/.claude-memory/x/.claude-memory/OPEN-WORK.md",  # a store inside a store
    "/tree/.claude-bx-selflearning/OPEN-WORK.md",       # the legacy store has no backlog
    "/tree/.claude-memory/open-work.md",                 # the exact name only
    "/tree/.claude-memory/OPEN-WORK.md.bak",
])
def test_other_backlog_shaped_paths_in_a_store_stay_denied(path):
    assert G.decide(_event("Write", path, {"content": "x"}), {}) is not None


def test_a_dotdot_that_lands_on_a_fact_is_judged_by_where_it_lands():
    ev = _event("Write", "/tree/.claude-memory/OPEN-WORK.md/../facts/f.md", {"content": "x"})
    assert G.decide(ev, {}) is not None


def test_a_backlog_symlink_escaping_the_store_is_denied(tmp_path):
    store = tmp_path / ".claude-memory"
    (store / "facts").mkdir(parents=True)
    fact = store / "facts" / "a-fact.md"
    fact.write_text("body\n", encoding="utf-8")
    link = store / "OPEN-WORK.md"
    try:
        link.symlink_to(fact)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks need privileges on this platform")
    ev = _event("Write", str(link), {"content": "x"})
    assert G.decide(ev, {}) is not None


def test_a_real_backlog_file_in_a_real_store_is_allowed(tmp_path):
    store = tmp_path / ".claude-memory"
    store.mkdir()
    (store / "OPEN-WORK.md").write_text("# backlog\n", encoding="utf-8")
    ev = _event("Edit", str(store / "OPEN-WORK.md"), {"old_string": "backlog", "new_string": "b"})
    assert G.decide(ev, {}) is None


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


# ---- driven through main(), as PreToolUse runs it --------------------------------------------------
# main() swallows any exception from decide() and exits 0, so a bare decide() call would report a
# crash where production silently ALLOWS; these assert on main()'s exit code instead.

@pytest.fixture
def run(monkeypatch):
    monkeypatch.delenv("BITRANOX_MEMORY_ENGINE", raising=False)

    def _run(event):
        monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(event)))
        return G.main()
    return _run


def test_notebookedit_into_the_store_is_denied(run):
    nb = "/tree/.claude-memory/facts/forged.ipynb"
    ev = {"tool_name": "NotebookEdit", "cwd": "/tree",
          "tool_input": {"notebook_path": nb, "new_source": "x", "edit_mode": "insert",
                         "cell_type": "code"}}
    assert run(ev) == 2
    # control: the same NotebookEdit outside any store stays allowed
    ev["tool_input"]["notebook_path"] = "/tree/notebooks/ok.ipynb"
    assert run(ev) == 0


def test_non_utf8_claude_local_md_keeps_the_write_deny(tmp_path, run):
    p = tmp_path / "CLAUDE.local.md"
    p.write_bytes(b"# Notizen f\xfcr mich\n")                # latin-1, not valid UTF-8
    ev = _event("Write", str(p), {"content": "# Notizen\n" + _block()}, cwd=str(tmp_path))
    assert run(ev) == 2
    # control: a Write that adds no block to the same undecodable file stays allowed
    ev = _event("Write", str(p), {"content": "# Notizen fuer mich, neu\n"}, cwd=str(tmp_path))
    assert run(ev) == 0


def test_non_utf8_claude_local_md_keeps_the_edit_deny(tmp_path, run):
    p = tmp_path / "CLAUDE.local.md"
    p.write_bytes(b"# Notizen f\xfcr mich\n" + _block().encode("utf-8") + b"\n")
    ev = _event("Edit", str(p), {"old_string": "(mem:a-fact)", "new_string": "(mem:x)"},
                cwd=str(tmp_path))
    assert run(ev) == 2
    # control: an edit of the user's own ASCII text outside the block stays allowed
    ev = _event("Edit", str(p), {"old_string": "# Notizen", "new_string": "# Notes"},
                cwd=str(tmp_path))
    assert run(ev) == 0


def test_non_utf8_edit_whose_target_cannot_be_located_is_denied(tmp_path, run):
    # The needle carries the character the guard could not decode, so the guard cannot place it;
    # it spans into the block, and allowing it would let the tool rewrite the block unseen.
    p = tmp_path / "CLAUDE.local.md"
    blk = _block()
    p.write_bytes(b"f\xfcr mich\n" + blk.encode("utf-8") + b"\n")
    ev = _event("Edit", str(p), {"old_string": "für mich\n" + blk, "new_string": ""},
                cwd=str(tmp_path))
    assert run(ev) == 2


def test_cwd_relative_path_into_the_store_is_denied(run):
    ev = {"tool_name": "Edit", "cwd": "/tree/.claude-memory",
          "tool_input": {"file_path": "facts/f.md", "old_string": "a", "new_string": "b"}}
    assert run(ev) == 2
    # control: a relative path from a cwd outside the store stays allowed
    ev["cwd"] = "/tree/src"
    assert run(ev) == 0


def test_path_that_only_passes_through_a_store_segment_is_judged_by_where_it_lands(run):
    ev = _event("Write", "/tree/.claude-memory/../src/main.py", {"content": "x"})
    assert run(ev) == 0
    ev = _event("Write", "/tree/src/../.claude-memory/facts/f.md", {"content": "x"})
    assert run(ev) == 2


def test_multiedit_chained_pair_that_deletes_the_block_is_denied(tmp_path, run):
    p = tmp_path / "CLAUDE.local.md"
    blk = _block()
    p.write_text("user line\n" + blk + "\n", encoding="utf-8")
    # Edit 1 ends exactly where the block starts, so it touches no block byte; edit 2's needle
    # exists only AFTER edit 1 is applied, and it removes the whole block.
    ev = {"tool_name": "MultiEdit", "cwd": str(tmp_path),
          "tool_input": {"file_path": str(p),
                         "edits": [{"old_string": "user line\n", "new_string": "ZZZ"},
                                   {"old_string": "ZZZ" + blk, "new_string": ""}]}}
    assert run(ev) == 2
    # control: the same first edit on its own, and a chained pair that stays outside the block
    ev["tool_input"]["edits"] = [{"old_string": "user line\n", "new_string": "ZZZ\n"},
                                 {"old_string": "ZZZ\n", "new_string": "user line, edited\n"}]
    assert run(ev) == 0


def test_a_crlf_claude_local_md_is_judged_with_lf_line_ends(tmp_path, run):
    # Written as bytes so the file is CRLF on every platform: write_text only produces it on
    # Windows, which is how this regression first showed up - as a Windows-only CI failure.
    p = tmp_path / "CLAUDE.local.md"
    blk = _block()
    p.write_bytes(("user line\n" + blk + "\n").replace("\n", "\r\n").encode("utf-8"))
    # The Edit and Write tools hand the hook LF text, so a Write that keeps the block and a
    # chained MultiEdit that deletes it must both be judged against the LF form of the file.
    ev = _event("Write", str(p), {"content": "user line, edited\n" + blk + "\n"},
                cwd=str(tmp_path))
    assert run(ev) == 0
    ev = {"tool_name": "MultiEdit", "cwd": str(tmp_path),
          "tool_input": {"file_path": str(p),
                         "edits": [{"old_string": "user line\n", "new_string": "ZZZ"},
                                   {"old_string": "ZZZ" + blk, "new_string": ""}]}}
    assert run(ev) == 2
    # control: an edit inside the block of the CRLF file is still denied
    ev = _event("Edit", str(p), {"old_string": "(mem:a-fact)", "new_string": "(mem:x)"},
                cwd=str(tmp_path))
    assert run(ev) == 2


def test_begin_without_end_protects_the_whole_tail(tmp_path, run):
    p = tmp_path / "CLAUDE.local.md"
    p.write_text("user line\n" + us.INDEX_BEGIN + "\n- [F](mem:f) - hook text\n", encoding="utf-8")
    ev = _event("Edit", str(p), {"old_string": "hook text", "new_string": "forged"},
                cwd=str(tmp_path))
    assert run(ev) == 2
    # control: the user's line before the unterminated BEGIN stays editable
    ev = _event("Edit", str(p), {"old_string": "user line", "new_string": "mine"},
                cwd=str(tmp_path))
    assert run(ev) == 0


def test_empty_old_string_on_a_block_at_offset_zero_is_allowed(tmp_path, run):
    p = tmp_path / "CLAUDE.local.md"
    p.write_text(_block() + "\nuser line\n", encoding="utf-8")
    ev = _event("Edit", str(p), {"old_string": "", "new_string": "x"}, cwd=str(tmp_path))
    assert run(ev) == 0
    # control: a real needle inside that block is still denied
    ev = _event("Edit", str(p), {"old_string": "(mem:a-fact)", "new_string": "x"},
                cwd=str(tmp_path))
    assert run(ev) == 2


def test_edit_that_assembles_a_fence_marker_from_split_pieces_is_denied(tmp_path, run):
    # Neither needle nor replacement carries a whole marker stem and no block exists yet, so only
    # comparing the block region before and after the edits can see a block appear.
    p = tmp_path / "CLAUDE.local.md"
    begin, end = us.INDEX_BEGIN, us.INDEX_END
    cut = begin.index("MEMORY-INDEX:")
    p.write_text("user line\nXX" + begin[cut:] + "\n- [F](mem:f) - h\n" + end + "\n",
                 encoding="utf-8")
    ev = _event("Edit", str(p), {"old_string": "XX", "new_string": begin[:cut]}, cwd=str(tmp_path))
    assert run(ev) == 2
    # control: an edit of the user line in that same file stays allowed
    ev = _event("Edit", str(p), {"old_string": "user line", "new_string": "mine"}, cwd=str(tmp_path))
    assert run(ev) == 0


def test_utf16_claude_local_md_keeps_the_edit_deny(tmp_path, run):
    p = tmp_path / "CLAUDE.local.md"
    p.write_bytes(("# notes\n" + _block() + "\n").encode("utf-16"))   # utf-16 writes a BOM
    ev = _event("Edit", str(p), {"old_string": "(mem:a-fact)", "new_string": "(mem:x)"},
                cwd=str(tmp_path))
    assert run(ev) == 2
    # control: the user's own line in the same file stays editable
    ev = _event("Edit", str(p), {"old_string": "# notes", "new_string": "# mine"}, cwd=str(tmp_path))
    assert run(ev) == 0


# ---- the Edit tool's matching is not literal --------------------------------------------------------
#
# Probed on Claude Code 2.1.289 and read from its validateInput: when old_string is not found
# verbatim, Edit retries with curly quotes folded to straight ones on BOTH sides, then with
# `\uXXXX` escapes swapped for their characters. A guard that only looks for the verbatim string
# allowed an edit the tool then applied inside the block.

LQ, RQ, LS, RS = chr(0x201C), chr(0x201D), chr(0x2018), chr(0x2019)


@pytest.fixture
def curly_block_file(tmp_path):
    p = tmp_path / "CLAUDE.local.md"
    hook = "say %shi%s and %sit%ss" % (LQ, RQ, LS, RS)
    block = _block([us.Pointer(slug="a-fact", title="A", hook=hook)])
    assert hook in block
    p.write_text("# notes\nuser %sline%s\n\n" % (LQ, RQ) + block, encoding="utf-8")
    return p


def test_a_straight_quote_old_string_matching_curly_block_text_is_denied(curly_block_file, tmp_path):
    ev = _event("Edit", str(curly_block_file),
                {"old_string": 'say "hi" and', "new_string": "tampered"}, cwd=str(tmp_path))
    assert G.decide(ev, {}) is not None


def test_a_curly_old_string_matching_straight_block_text_is_denied(tmp_path):
    p = tmp_path / "CLAUDE.local.md"
    p.write_text("# notes\n\n" + _block([us.Pointer(slug="a-fact", title="A", hook="it's here")]),
                 encoding="utf-8")
    ev = _event("Edit", str(p), {"old_string": "it%ss here" % RS, "new_string": "x"},
                cwd=str(tmp_path))
    assert G.decide(ev, {}) is not None


def test_a_single_quote_fold_reaches_the_block_too(curly_block_file, tmp_path):
    ev = _event("Edit", str(curly_block_file),
                {"old_string": "'it's", "new_string": "x"}, cwd=str(tmp_path))
    assert G.decide(ev, {}) is not None


def test_a_quote_folded_edit_outside_the_block_stays_allowed(curly_block_file, tmp_path):
    ev = _event("Edit", str(curly_block_file),
                {"old_string": 'user "line"', "new_string": "user text"}, cwd=str(tmp_path))
    assert G.decide(ev, {}) is None


def test_a_quote_folded_replace_all_that_reaches_the_block_is_denied(curly_block_file, tmp_path):
    """The folded match is judged at every occurrence the tool would replace, not only the
    first: here the first sits outside the block and a later one inside it."""
    p = curly_block_file
    p.write_text(p.read_text(encoding="utf-8").replace("user %sline%s" % (LQ, RQ),
                                                        "say %shi%s" % (LQ, RQ)), encoding="utf-8")
    ev = _event("Edit", str(p), {"old_string": 'say "hi"', "new_string": "x", "replace_all": True},
                cwd=str(tmp_path))
    assert G.decide(ev, {}) is not None


def test_an_escaped_old_string_matching_block_text_is_denied(tmp_path):
    p = tmp_path / "CLAUDE.local.md"
    hook = "a %s b" % chr(0x00E9)
    p.write_text("# notes\n\n" + _block([us.Pointer(slug="a-fact", title="A", hook=hook)]),
                 encoding="utf-8")
    ev = _event("Edit", str(p), {"old_string": "a \\u00e9 b", "new_string": "x"}, cwd=str(tmp_path))
    assert G.decide(ev, {}) is not None


def test_a_non_ascii_old_string_matching_escaped_block_text_is_denied(tmp_path):
    p = tmp_path / "CLAUDE.local.md"
    p.write_text("# notes\n\n" + _block([us.Pointer(slug="a-fact", title="A",
                                                     hook="a \\u00E9 b")]), encoding="utf-8")
    ev = _event("Edit", str(p), {"old_string": "a %s b" % chr(0x00E9), "new_string": "x"},
                cwd=str(tmp_path))
    assert G.decide(ev, {}) is not None


def test_an_escape_spelled_fence_marker_in_new_string_is_denied(local_file, tmp_path):
    """When the tool matched through an escape swap it unescapes new_string as well, so a marker
    spelled with an escape lands as a real one."""
    new = "keep me\n<!-- \\u0042ITRANOX-MEMORY-INDEX:BEGIN -->"
    ev = _event("Edit", str(local_file), {"old_string": "keep me", "new_string": new},
                cwd=str(tmp_path))
    assert G.decide(ev, {}) is not None


def test_an_old_string_absent_in_every_form_is_still_allowed(curly_block_file, tmp_path):
    """The tool refuses a target it cannot find in any form, so there is nothing to judge."""
    ev = _event("Edit", str(curly_block_file),
                {"old_string": "nowhere at all", "new_string": "x"}, cwd=str(tmp_path))
    assert G.decide(ev, {}) is None
