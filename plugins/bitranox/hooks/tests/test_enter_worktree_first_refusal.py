"""The first EnterWorktree of a session is refused once, with the 'finish main-checkout git first' note.

User decision 2026-10-12 ([200] bitranox-skills queue, OPEN-WORK [9](3)): once a session is isolated
in a worktree, every git aimed at another checkout is refused - a `!` command the user types
included - so git the session asked the user to run in the main checkout has to happen BEFORE the
switch. A note that arrives after the switch is too late, which is why this is a refusal.

Probe 2026-10-15, interactive CLI 2.1.300 in tmux with a throwaway --settings PreToolUse deny on
EnterWorktree: the hook fired, no worktree and no branch were created, the cwd stayed where it was,
and the model quoted the deny reason verbatim.

Must NOT (the decision's own words): refuse the re-call; refuse more than once per session.
"""
import importlib.util
import json
import os
import pathlib
import subprocess
import sys

_HOOK = pathlib.Path(__file__).resolve().parent.parent / "enter-worktree-first-refusal.py"
_spec = importlib.util.spec_from_file_location("enter_worktree_first_refusal", _HOOK)
N = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(N)


def _enter(home, session="sess-1", tool_input=None, tool_name="EnterWorktree"):
    event = {"hook_event_name": "PreToolUse", "tool_name": tool_name,
             "tool_input": tool_input or {"name": "topic"}}
    if session is not None:
        event["session_id"] = session
    env = {**os.environ, "HOME": str(home), "USERPROFILE": str(home)}
    return subprocess.run(
        [sys.executable, str(_HOOK)], input=json.dumps(event), capture_output=True, text=True,
        encoding="utf-8", errors="replace", check=False, env=env,
    )


def _refused(r):
    assert r.returncode == 0
    if not r.stdout.strip():
        return False
    out = json.loads(r.stdout)["hookSpecificOutput"]
    assert out["hookEventName"] == "PreToolUse"
    return out.get("permissionDecision") == "deny"


def test_the_first_entry_of_a_session_is_refused_with_the_note(tmp_path):
    r = _enter(tmp_path)
    assert _refused(r)
    reason = json.loads(r.stdout)["hookSpecificOutput"]["permissionDecisionReason"]
    assert reason == N.REFUSAL
    for clause in ("before the switch", "every git aimed at another checkout is refused",
                   "a `!` command the user types", "have them do it now",
                   "ExitWorktree with action keep", "EnterWorktree again"):
        assert clause in reason, clause


def test_the_re_call_passes_and_so_does_every_later_entry(tmp_path):
    """Once per SESSION, unlike the question refusal, which refuses every new question."""
    verdicts = [_refused(_enter(tmp_path)) for _ in range(4)]
    assert verdicts == [True, False, False, False]


def test_entering_an_existing_worktree_by_path_counts_as_the_first_entry(tmp_path):
    """`path` switches the session into a worktree just the same, so it gets the same note."""
    assert _refused(_enter(tmp_path, tool_input={"path": "/repo/.claude/worktrees/x"}))
    assert not _refused(_enter(tmp_path, tool_input={"name": "next"}))


def test_sessions_do_not_share_the_flag(tmp_path):
    assert _refused(_enter(tmp_path, session="sess-a"))
    assert _refused(_enter(tmp_path, session="sess-b"))
    assert not _refused(_enter(tmp_path, session="sess-a"))


def test_without_a_session_id_the_entry_passes(tmp_path):
    """No key, no flag: a refusal here could never be followed by a pass, so it must not refuse."""
    for _ in range(2):
        assert not _refused(_enter(tmp_path, session=None))


def test_an_unwritable_state_store_passes_instead_of_refusing_forever(tmp_path):
    home = tmp_path / "home-is-a-file"
    home.write_text("not a directory\n", encoding="utf-8")
    for _ in range(2):
        assert not _refused(_enter(home))


def test_another_tool_is_never_refused(tmp_path):
    """Control: the hook keys on EnterWorktree, so a mis-registration cannot refuse other tools."""
    assert not _refused(_enter(tmp_path, tool_name="ExitWorktree", tool_input={"action": "keep"}))
    assert _refused(_enter(tmp_path))


def test_junk_stdin_passes():
    proc = subprocess.run([sys.executable, str(_HOOK)], input="not json", capture_output=True,
                          text=True, encoding="utf-8", errors="replace", check=False)
    assert proc.returncode == 0
    assert proc.stdout.strip() == ""


def test_hooks_json_registers_it_on_enter_worktree():
    hooks = json.loads((_HOOK.parent / "hooks.json").read_text(encoding="utf-8"))["hooks"]
    groups = [g for g in hooks["PreToolUse"] if "EnterWorktree" in (g.get("matcher") or "").split("|")]
    commands = [h["command"] for g in groups for h in g["hooks"]]
    assert any(c.endswith('/hooks/enter-worktree-first-refusal.py"') and "--hook" in c for c in commands)
