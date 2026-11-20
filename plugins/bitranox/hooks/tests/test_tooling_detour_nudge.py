"""Tests for tooling-detour-nudge.py (the PreToolUse nudge that catches a work session fixing the
plugin source in place instead of queueing the symptom for a dream).

The core is pure and takes the room test as a seam (`is_root`), so the marketplace shape is built
in tmp_path rather than assumed from the developer's tree. The wiring is tested end to end through
main() with HOME redirected, so the once-per-session flag is the real file.

`Path.home()` reads USERPROFILE on Windows and HOME on POSIX, so both are set. All content is ASCII.
"""

import io
import json
import os
import sys

import pytest

import tooling_detour_nudge as TDN


@pytest.fixture
def scratch_home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    (tmp_path / "home").mkdir()
    return tmp_path / "home"


def _marketplace(root, name):
    (root / ".claude-plugin").mkdir(parents=True)
    (root / ".claude-plugin" / "marketplace.json").write_text(json.dumps({"name": name}),
                                                             encoding="utf-8")
    return root


@pytest.fixture
def rooms(tmp_path, monkeypatch):
    """The marketplace that ships the running plugin, beside a work project - real directories.

    The running plugin is identified the way the harness identifies it: CLAUDE_PLUGIN_ROOT is the
    versioned cache dir `<cache>/<marketplace>/<plugin>/<version>`, so the marketplace's NAME is
    two levels up, and only a marketplace.json carrying that name is the plugin's source.
    """
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(tmp_path / "cache" / "mkt-under-test" / "plug" / "1.0.0"))
    mkt = _marketplace(tmp_path / "mkt", "mkt-under-test")
    (mkt / "plugins" / "x" / "hooks").mkdir(parents=True)
    (mkt / "plugins" / "x" / "hooks" / "a.py").write_text("", encoding="utf-8")
    work = tmp_path / "work"
    (work / "src").mkdir(parents=True)
    return mkt, work


def _hook_file(rooms):
    return str(rooms[0] / "plugins" / "x" / "hooks" / "a.py")


# --------------------------------------------------------------------------
# A path write
# --------------------------------------------------------------------------


def test_an_edit_into_a_marketplace_from_a_work_project_is_noticed(rooms):
    mkt, work = rooms
    text = TDN.notice_path(_hook_file(rooms), str(work))
    assert text and "contrib_queue" in text and str(mkt) in text


def test_the_same_edit_from_inside_the_marketplace_is_silent(rooms):
    mkt, _ = rooms
    assert TDN.notice_path(_hook_file(rooms), str(mkt)) is None
    assert TDN.notice_path(_hook_file(rooms), str(mkt / "plugins" / "x")) is None


def test_a_linked_worktree_of_the_marketplace_is_its_own_room(tmp_path, rooms):
    """A worktree carries its own marketplace.json, so a session inside it is inside a marketplace."""
    mkt, _ = rooms
    wt = _marketplace(mkt / ".claude" / "worktrees" / "topic", "mkt-under-test")
    assert TDN.notice_path(str(wt / "plugins" / "x" / "hooks" / "a.py"), str(wt)) is None


def test_a_tool_repo_that_ships_its_own_usage_skill_is_ordinary_work(tmp_path, rooms):
    """A repo is a marketplace the moment it ships a skill; only the one that ships THIS plugin is
    the plugin's source. Editing such a tool repo from elsewhere is project work, not a detour."""
    _, work = rooms
    tool = _marketplace(tmp_path / "some-tool", "some-tool")
    (tool / "skills" / "s").mkdir(parents=True)
    assert TDN.notice_path(str(tool / "skills" / "s" / "SKILL.md"), str(work)) is None
    assert TDN.notice_bash("cd \"%s\" && git commit -F m" % tool, str(work)) is None


def test_without_a_plugin_root_the_hook_is_silent(rooms, monkeypatch):
    """No running plugin to name the source repo: fail open, never guess by directory name."""
    monkeypatch.delenv("CLAUDE_PLUGIN_ROOT")
    _, work = rooms
    assert TDN.notice_path(_hook_file(rooms), str(work)) is None


@pytest.mark.skipif(sys.platform == "win32", reason="creating a symlink needs a privilege there")
def test_the_plugin_root_is_resolved_once_per_value(tmp_path, monkeypatch):
    """CLAUDE_PLUGIN_ROOT is constant for the process, yet it was resolved again for every
    ancestor of every path token checked. Re-pointing a symlinked root after the first read shows
    whether it is read again: a resolution per call would follow the link to the new name."""
    first = tmp_path / "cache" / "first-mkt" / "plug" / "1.0.0"
    second = tmp_path / "cache" / "second-mkt" / "plug" / "1.0.0"
    first.mkdir(parents=True)
    second.mkdir(parents=True)
    link = tmp_path / "link"
    link.mkdir()
    (link / "root").symlink_to(first)
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(link / "root"))
    assert TDN.own_marketplace_name() == "first-mkt"
    (link / "root").unlink()
    (link / "root").symlink_to(second)
    assert TDN.own_marketplace_name() == "first-mkt"
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(second))   # a new value is read afresh
    assert TDN.own_marketplace_name() == "second-mkt"


def test_a_write_outside_any_marketplace_is_silent(rooms):
    _, work = rooms
    assert TDN.notice_path(str(work / "src" / "a.py"), str(work)) is None


def test_a_write_from_the_memory_store_is_silent(tmp_path, rooms):
    store = tmp_path / ".claude-memory"
    store.mkdir()
    assert TDN.notice_path(_hook_file(rooms), str(store)) is None


def test_a_relative_target_resolves_against_the_cwd(rooms):
    _, work = rooms
    assert TDN.notice_path("src/a.py", str(work)) is None


# --------------------------------------------------------------------------
# A shell write
# --------------------------------------------------------------------------


def test_a_commit_in_the_marketplace_from_a_work_project_is_noticed(rooms):
    mkt, work = rooms
    assert TDN.notice_bash("cd \"%s\" && git commit -F m -- plugins/x" % mkt, str(work))


def test_a_cd_the_shared_reader_follows_moves_the_commit_too(rooms):
    """The private regex knew `cd` only at statement start and cut a quoted path at its first
    space; the shared `shell_text.directory_change` reads a loop body, a pushd and a quoted path."""
    mkt, work = rooms
    assert TDN.notice_bash("for i in 1; do cd \"%s\" && git commit -F m; done" % mkt, str(work))
    assert TDN.notice_bash("pushd \"%s\" && git commit -F m" % mkt, str(work))
    spaced = mkt.parent / "m k t"
    mkt.rename(spaced)
    assert TDN.notice_bash("cd \"%s\" && git commit -F m" % spaced, str(work))
    # control: a cd the reader cannot follow attributes nothing
    assert TDN.notice_bash("cd \"$X\" && git commit -F m", str(work)) is None


def test_a_cd_into_the_marketplace_through_the_home_tilde_is_noticed(rooms, scratch_home):
    """The hook runs as the user whose shell runs the command, so `~` is that user's home."""
    mkt, work = rooms
    moved = scratch_home / "mkt"
    mkt.rename(moved)
    assert TDN.notice_bash("cd ~/mkt && git commit -F m", str(work))


def test_a_git_dash_c_push_is_noticed(rooms):
    mkt, work = rooms
    assert TDN.notice_bash("git -C %s push origin master" % mkt, str(work))


def test_an_in_place_sed_on_a_hook_is_noticed(rooms):
    _, work = rooms
    assert TDN.notice_bash("sed -i 's/a/b/' %s" % _hook_file(rooms), str(work))


def _git_bash_spelling(path):
    """`C:\\x\\y` as Git Bash prints it, `/c/x/y`."""
    return "/" + path.drive[0].lower() + path.as_posix()[len(path.drive):]


@pytest.mark.skipif(os.name != "nt", reason="Git Bash drive paths exist on Windows only")
@pytest.mark.parametrize("template", ["echo x > {}", "sed -i 's/a/b/' {}"])
def test_a_write_through_a_git_bash_drive_path_is_noticed(rooms, template):
    """Git Bash reads `/c/...` as drive C; pathlib called it relative and joined it onto the cwd,
    so a write into the marketplace spelled the way Git Bash prints paths went unnoticed."""
    mkt, work = rooms
    target = _git_bash_spelling(mkt / "plugins" / "x" / "hooks" / "a.py")
    assert TDN.notice_bash(template.format(target), str(work))


@pytest.mark.parametrize("template", ["echo x > {}", "sed -i 's/a/b/' {}"])
def test_a_write_through_a_git_bash_mount_names_no_marketplace_on_windows(rooms, monkeypatch,
                                                                         template):
    """A rooted path that is not a drive reaches Git Bash's mount table, so on Windows the hook
    cannot say where the write lands and stays silent; elsewhere it is the marketplace file. The
    cwd is moved onto the file's drive so the current-drive reading would find it."""
    mkt, work = rooms
    monkeypatch.chdir(work)
    hook = mkt / "plugins" / "x" / "hooks" / "a.py"
    fired = bool(TDN.notice_bash(template.format(hook.as_posix()[len(hook.drive):]), str(work)))
    assert fired is (os.name != "nt")


def test_a_redirect_into_the_marketplace_is_noticed(rooms):
    _, work = rooms
    assert TDN.notice_bash("printf x > %s" % _hook_file(rooms), str(work))


def test_a_redirect_to_a_log_while_running_a_marketplace_script_is_silent(rooms, tmp_path):
    """35 of 549 corpus firings: the command names a shipped script and sends its OUTPUT to a
    scratch log. The write lands in the log; only a redirect whose target is in the repo counts."""
    _, work = rooms
    log = tmp_path / "scratch" / "run.log"
    assert TDN.notice_bash("python3 %s --check > %s 2>&1" % (_hook_file(rooms), log), str(work)) is None
    mkt = rooms[0]
    assert TDN.notice_bash("cd \"%s\" && python3 -m pytest -q > %s" % (mkt, log), str(work)) is None


def test_an_arrow_in_prose_and_a_variable_target_are_not_redirects_into_the_repo(rooms):
    """Measured: `echo 'a -> b'` after a `cd` into the repo read as a redirect to `b` under it, and
    a `$LOG` target resolved as a relative path there. Neither can be shown to land in the repo."""
    mkt, work = rooms
    assert TDN.notice_bash("cd \"%s\" && echo '=== a -> b ===' && python3 -m pytest -q" % mkt, str(work)) is None
    assert TDN.notice_bash("cd \"%s\" && python3 -m pytest -q > $LOG 2>&1" % mkt, str(work)) is None
    assert TDN.notice_bash("cd \"%s\" && printf x > plugins/x/hooks/a.py" % mkt, str(work))


def test_a_comparison_inside_a_quoted_one_liner_is_not_a_redirect(rooms):
    """Measured 56 of 596 corpus firings: `python3 -c "... if n > 126"` after a cd into the repo
    read as a redirect to `126` under it. A `>` inside quotes is data."""
    mkt, work = rooms
    cmd = 'cd \"%s\" && python3 -c "import sys; sys.exit(0 if len(sys.argv) > 126 else 1)"' % mkt
    assert TDN.notice_bash(cmd, str(work)) is None
    assert TDN.notice_bash("cd \"%s\" && awk '$1 > 100' data.txt" % mkt, str(work)) is None
    assert TDN.notice_bash('cd \"%s\" && printf x > "plugins/x/hooks/a.py"' % mkt, str(work))


def test_a_python_heredoc_that_writes_a_hook_is_noticed(rooms):
    _, work = rooms
    cmd = ("python3 - <<'PY'\nfrom pathlib import Path\np = Path(%r)\n"
           "p.write_text(p.read_text() + 'x')\nPY" % _hook_file(rooms))
    assert TDN.notice_bash(cmd, str(work))


def test_reading_and_running_a_marketplace_file_is_silent(rooms):
    """Reading the tool is not fixing it; running a shipped script is what the tool is for."""
    _, work = rooms
    assert TDN.notice_bash("cat %s" % _hook_file(rooms), str(work)) is None
    assert TDN.notice_bash("grep -n foo %s" % _hook_file(rooms), str(work)) is None
    assert TDN.notice_bash("python3 %s --check" % _hook_file(rooms), str(work)) is None
    assert TDN.notice_bash("uv run %s list" % _hook_file(rooms), str(work)) is None


def test_a_read_only_git_question_in_the_marketplace_is_silent(rooms):
    """Measured firing on the corpus: `merge-base` read as `merge`, and a `2>/dev/null` read as a
    write. Neither lands a byte in the repo."""
    mkt, work = rooms
    assert TDN.notice_bash("cd \"%s\" && git status --porcelain && git log -3" % mkt, str(work)) is None
    assert TDN.notice_bash("cd \"%s\" && git merge-base --is-ancestor a b" % mkt, str(work)) is None
    assert TDN.notice_bash("grep -n x %s 2>/dev/null" % _hook_file(rooms), str(work)) is None


def test_a_heredoc_that_merely_names_the_path_is_silent(rooms):
    """A note ABOUT the tool is data: the write lands in the work project, and the path is prose."""
    _, work = rooms
    cmd = "cat > %s <<'EOF'\nsee %s for the guard\nEOF" % (work / "notes.md", _hook_file(rooms))
    assert TDN.notice_bash(cmd, str(work)) is None


def test_a_windows_drive_path_is_a_path_token():
    """Git Bash on Windows hands the hook `C:\\...` paths; a scanner that knows only `/` never sees
    the marketplace there. Measured: three tests green on POSIX and red on the windows-latest cell."""
    found = [m.group(1) for m in TDN._PATH_TOKEN.finditer("sed -i 's/a/b/' C:\\Users\\me\\mkt\\plugins\\a.py")]
    assert found == ["C:\\Users\\me\\mkt\\plugins\\a.py"]
    found = [m.group(1) for m in TDN._PATH_TOKEN.finditer("p = Path('C:\\\\Users\\\\me\\\\mkt\\\\plugins\\\\a.py')")]
    assert found == ["C:\\\\Users\\\\me\\\\mkt\\\\plugins\\\\a.py"]
    assert [m.group(1) for m in TDN._PATH_TOKEN.finditer("git -C D:/work/mkt push")] == ["D:/work/mkt"]


def test_a_commit_in_the_work_project_is_silent(rooms):
    _, work = rooms
    assert TDN.notice_bash("git commit -F m -- src/", str(work)) is None
    assert TDN.notice_bash("cd \"%s\" && git push" % work, str(work)) is None


def test_bash_from_inside_the_marketplace_is_silent(rooms):
    mkt, _ = rooms
    assert TDN.notice_bash("sed -i 's/a/b/' plugins/x/hooks/a.py", str(mkt)) is None
    assert TDN.notice_bash("git commit -F m -- plugins/x", str(mkt)) is None


# --------------------------------------------------------------------------
# The wiring: once per session, and a dream session is exempt
# --------------------------------------------------------------------------


def run_main(event, monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(event)))
    rc = TDN.main()
    return rc, capsys.readouterr().out


def test_an_edit_event_carries_the_notice_as_additional_context(scratch_home, rooms, monkeypatch, capsys):
    _, work = rooms
    rc, out = run_main({"session_id": "s1", "cwd": str(work), "tool_name": "Edit",
                        "tool_input": {"file_path": _hook_file(rooms), "old_string": "a",
                                       "new_string": "b"}}, monkeypatch, capsys)
    assert rc == 0
    ctx = json.loads(out)["hookSpecificOutput"]["additionalContext"]
    assert "contrib_queue" in ctx


def test_it_speaks_once_per_session(scratch_home, rooms, monkeypatch, capsys):
    _, work = rooms
    event = {"session_id": "s2", "cwd": str(work), "tool_name": "Write",
             "tool_input": {"file_path": _hook_file(rooms), "content": "x"}}
    _, first = run_main(event, monkeypatch, capsys)
    _, second = run_main(event, monkeypatch, capsys)
    assert first and second == "", "a nudge that repeats on every call is one that gets ignored"


def test_a_dream_session_is_exempt(scratch_home, rooms, monkeypatch, capsys):
    """A dream is the session whose job the maintenance IS - its edits are the point."""
    _, work = rooms
    run_main({"session_id": "s3", "cwd": str(work), "tool_name": "Skill",
              "tool_input": {"skill": "bitranox:meta-dream-tree"}}, monkeypatch, capsys)
    _, out = run_main({"session_id": "s3", "cwd": str(work), "tool_name": "Edit",
                       "tool_input": {"file_path": _hook_file(rooms), "new_string": "b"}},
                      monkeypatch, capsys)
    assert out == ""


def test_another_sessions_dream_does_not_exempt_this_one(scratch_home, rooms, monkeypatch, capsys):
    _, work = rooms
    run_main({"session_id": "s4-dream", "cwd": str(work), "tool_name": "Skill",
              "tool_input": {"skill": "bitranox:meta-dream-nap"}}, monkeypatch, capsys)
    _, out = run_main({"session_id": "s4-work", "cwd": str(work), "tool_name": "Edit",
                       "tool_input": {"file_path": _hook_file(rooms), "new_string": "b"}},
                      monkeypatch, capsys)
    assert out and "contrib_queue" in out


def test_garbage_on_stdin_never_wedges_the_turn(monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO("not json"))
    assert TDN.main() == 0
    assert capsys.readouterr().out == ""


def test_an_unrelated_tool_is_ignored(scratch_home, rooms, monkeypatch, capsys):
    _, work = rooms
    _, out = run_main({"session_id": "s5", "cwd": str(work), "tool_name": "Read",
                       "tool_input": {"file_path": _hook_file(rooms)}}, monkeypatch, capsys)
    assert out == ""


def test_a_notebookedit_target_is_read_from_notebook_path(scratch_home, rooms, monkeypatch, capsys):
    """NotebookEdit names its target `notebook_path`, not `file_path` - `decide()` must read it
    too, the way every sibling path-reading guard in this plugin does (store-edit-guard.py,
    skill-edit-guard.py, config-edit-guard.py, touched-paths.py, validate-structured-files.py)."""
    _, work = rooms
    rc, out = run_main({"session_id": "s6", "cwd": str(work), "tool_name": "NotebookEdit",
                        "tool_input": {"notebook_path": _hook_file(rooms), "cell_id": "c1",
                                       "new_source": "print(1)"}}, monkeypatch, capsys)
    assert rc == 0
    assert out and "contrib_queue" in out
