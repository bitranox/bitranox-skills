"""Tests for toolbox-nudge.py (PreToolUse nudge on Bash, PowerShell, Edit, Write, MultiEdit and NotebookEdit toward a local toolbox tool). ASCII only."""
import ast
import io
import json
import os
import re
import sys
from pathlib import Path

import pytest

import shell_text
import toolbox_nudge as N


# ---- the pure matcher ---------------------------------------------------------------------------
def test_match_conflict_scan():
    assert N.match_tool("grep -rn '^<<<<<<<' .")[0] == "conflict_scan"


def test_match_jsonl_parse():
    assert N.match_tool('python3 -c "import json;[json.loads(l) for l in open(\'x.jsonl\')]"')[0] == "jsonl_grep"


def test_match_ssh_fleet():
    assert N.match_tool("ssh -o StrictHostKeyChecking=no -i k host uptime")[0] == "fleet_ssh"


def test_match_ci_triage():
    assert N.match_tool("cargo build 2>&1 | grep error")[0] == "ci_triage"


def test_match_git_state():
    assert N.match_tool("git rev-parse --abbrev-ref HEAD")[0] == "git_state"


def test_match_procsig_pkill():
    assert N.match_tool("pkill -f 'vm-79099-disk-0'")[0] == "procsig"


def test_match_procsig_pgrep():
    assert N.match_tool("pgrep -af openvmm -f")[0] == "procsig"


def test_match_guestip_ip_neigh():
    assert N.match_tool("ip neigh show dev vmbr0 | grep bc:24")[0] == "guestip"


def test_match_guestip_getent_ovm():
    assert N.match_tool("getent hosts OVM-64000")[0] == "guestip"


def test_match_ovmlog():
    assert N.match_tool("tail -100 /var/log/openvmm/79099.log")[0] == "ovmlog"


def test_no_match_on_plain_commands():
    assert N.match_tool("ls -la /tmp") is None
    assert N.match_tool("echo hello && cat file.py") is None


# ---- the pure text extractor (which field each tool hides the chore in) --------------------------
def test_extract_text_bash_is_the_command():
    assert N.extract_text("Bash", {"command": "ls -la"}) == "ls -la"


def test_extract_text_write_is_the_content():
    assert N.extract_text("Write", {"file_path": "/tmp/x.py", "content": "print(1)"}) == "print(1)"


def test_extract_text_edit_is_the_new_string():
    assert N.extract_text("Edit", {"old_string": "a", "new_string": "print(1)"}) == "print(1)"


def test_extract_text_multiedit_joins_new_strings():
    txt = N.extract_text("MultiEdit", {"edits": [{"new_string": "alpha"}, {"new_string": "beta"}]})
    assert "alpha" in txt and "beta" in txt


def test_extract_text_unscanned_tool_is_none():
    assert N.extract_text("Read", {"file_path": "x"}) is None


# ---- the main() hook behavior -------------------------------------------------------------------
@pytest.fixture
def home(tmp_path, monkeypatch):
    h = tmp_path / "home"
    (h / ".claude").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(h))
    monkeypatch.setenv("USERPROFILE", str(h))
    return h


def _feed(monkeypatch, ev):
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(ev)))


def _ev(cmd, session="s1"):
    return {"tool_name": "Bash", "session_id": session, "tool_input": {"command": cmd}}


def _no_shipped_tree(root):
    """A shipped-scripts dir that does not exist, inside a skills tree this test owns.

    The resolver also searches SIBLING skills, at `_shipped_dir().parent.parent`. A fake placed
    directly in `tmp_path` puts that search at pytest's shared temp root, where every other test's
    tmp_path sits - so a test that writes `<its tmp>/scripts/procsig.py` makes the tool "exist",
    and this test's verdict depends on which tests ran before it."""
    return root / "no-plugin" / "skills" / "compuse-toolbox" / "scripts"


def _with_tool(home, name="git_state"):
    tools = home / ".claude" / "skills" / "toolbox" / "tools"
    tools.mkdir(parents=True, exist_ok=True)
    (tools / (name + ".py")).write_text("x", encoding="utf-8")


def test_main_nudges_when_tool_present(home, monkeypatch, capsys):
    _with_tool(home)
    _feed(monkeypatch, _ev("git rev-parse --abbrev-ref HEAD"))
    assert N.main() == 0
    out = capsys.readouterr().out
    assert "git_state" in out and "additionalContext" in out


def test_main_falls_back_to_the_shipped_copy_when_the_local_one_is_absent(home, monkeypatch, capsys):
    """An empty local toolbox is no longer silence: git_state ships with the plugin.

    This test used to assert silence, which encoded the old local-only contract. Retiring a local
    tool after contributing it upstream is now the norm, so silence there would lose the guard for
    exactly the tools broadly useful enough to ship.
    """
    (home / ".claude" / "skills" / "toolbox" / "tools").mkdir(parents=True)   # empty, no git_state.py
    _feed(monkeypatch, _ev("git rev-parse --abbrev-ref HEAD", "s2"))
    N.main()
    out = capsys.readouterr().out.strip()
    assert "compuse-toolbox" in out and "git_state" in out


def test_main_silent_when_the_tool_exists_neither_locally_nor_shipped(home, monkeypatch, capsys):
    (home / ".claude" / "skills" / "toolbox" / "tools").mkdir(parents=True)
    monkeypatch.setattr(N, "_shipped_dir", lambda: _no_shipped_tree(home))
    _feed(monkeypatch, _ev("git rev-parse --abbrev-ref HEAD", "s2b"))
    N.main()
    assert capsys.readouterr().out.strip() == ""


def test_main_silent_on_plain_command(home, monkeypatch, capsys):
    _with_tool(home)
    _feed(monkeypatch, _ev("ls -la", "s3"))
    N.main()
    assert capsys.readouterr().out.strip() == ""


def test_main_dedup_second_time_is_silent(home, monkeypatch, capsys):
    _with_tool(home)
    _feed(monkeypatch, _ev("git rev-parse --abbrev-ref HEAD", "s4"))
    N.main()
    assert "git_state" in capsys.readouterr().out
    _feed(monkeypatch, _ev("git rev-parse --abbrev-ref HEAD", "s4"))
    N.main()
    assert capsys.readouterr().out.strip() == ""


def test_main_nudges_on_hand_rolled_write(home, monkeypatch, capsys):
    """The blind spot: a chore hand-rolled by WRITING a script file, not a Bash one-liner."""
    _with_tool(home, "jsonl_grep")
    _feed(monkeypatch, {"tool_name": "Write", "session_id": "w1",
                        "tool_input": {"file_path": "/tmp/scratch.py",
                                       "content": 'import json\n[json.loads(l) for l in open("t.jsonl")]'}})
    assert N.main() == 0
    out = capsys.readouterr().out
    assert "jsonl_grep" in out and "additionalContext" in out


def test_main_nudges_on_edit_new_string(home, monkeypatch, capsys):
    _with_tool(home, "fleet_ssh")
    _feed(monkeypatch, {"tool_name": "Edit", "session_id": "e1",
                        "tool_input": {"file_path": "/tmp/f.sh", "old_string": "x",
                                       "new_string": "ssh -o StrictHostKeyChecking=no -i k host uptime"}})
    assert N.main() == 0
    assert "fleet_ssh" in capsys.readouterr().out


def test_main_silent_on_write_without_matching_content(home, monkeypatch, capsys):
    _with_tool(home)
    _feed(monkeypatch, {"tool_name": "Write", "session_id": "w2",
                        "tool_input": {"file_path": "/tmp/x.py", "content": "print('hello world')"}})
    N.main()
    assert capsys.readouterr().out.strip() == ""


def test_main_ignores_unscanned_tool(home, monkeypatch, capsys):
    _with_tool(home)
    _feed(monkeypatch, {"tool_name": "Read", "session_id": "r1", "tool_input": {"file_path": "x"}})
    N.main()
    assert capsys.readouterr().out.strip() == ""


# ---- claim_check: a presence check whose NEGATIVE answer cannot be trusted ------------------------

def test_match_claim_check_on_grep_count():
    """`grep -c` decides "is it there?" - and returns file:count under -r, exits 1 on zero.

    Both shapes produced a confident false ABSENT in one session, twice.
    """
    assert N.match_tool('grep -c "LC_ALL=C" skill.md')[0] == "claim_check"
    assert N.match_tool('grep -ric "pattern" file.md')[0] == "claim_check"


def test_match_claim_check_on_file_listing():
    assert N.match_tool('grep -l "needle" *.md')[0] == "claim_check"
    assert N.match_tool('grep -rL "needle" src/')[0] == "claim_check"


def test_claim_check_does_not_hijack_an_ordinary_grep():
    """A plain search is not a presence CHECK; nudging on every grep would get the hook ignored."""
    for cmd in ('grep -rn "needle" src/', 'grep -i pattern file', "grep --color=auto x y"):
        matched = N.match_tool(cmd)
        assert matched is None or matched[0] != "claim_check", cmd


def test_conflict_scan_still_wins_its_own_shape():
    """conflict_scan's rule is listed first and uses -rn, so the new rule must not shadow it."""
    assert N.match_tool("grep -rn '^<<<<<<<' .")[0] == "conflict_scan"


# --- a heredoc body is DATA, not a command ------------------------------------------------------

def test_a_tool_name_inside_a_heredoc_body_does_not_nudge():
    """Writing prose that MENTIONS a chore must not fire the nudge for it.

    A fact body containing the word pgrep, written with `cat > f <<'EOF' ... EOF`, fired the
    procsig nudge: the heredoc body is data being written, not a command being run. Same family
    as the git-footgun and shell-prefix guards, which already strip heredoc bodies."""
    command = (
        "cat > /tmp/body.md <<'EOF'\n"
        "Same root as the pgrep -f \"X\" self-match trap, where a keyword that also appears in\n"
        "your own command line makes the check match itself.\n"
        "EOF\n"
        "echo done\n"
    )
    assert N.match_tool(N.extract_text("Bash", {"command": command})) is None


def test_a_real_invocation_outside_the_heredoc_still_nudges():
    """The control: stripping data must not disarm the guard for an actual command."""
    command = (
        "cat > /tmp/body.md <<'EOF'\n"
        "just some prose\n"
        "EOF\n"
        "pgrep -f openvmm\n"
    )
    matched = N.match_tool(N.extract_text("Bash", {"command": command}))
    assert matched is not None and matched[0] == "procsig"


# ---- a tool that moved upstream must still be nudged, pointing at the shipped copy ---------------

def _event(cmd, session="s1"):
    return {"tool_name": "Bash", "tool_input": {"command": cmd}, "session_id": session}


def _run(event, monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(event)))
    N.main()
    out = capsys.readouterr().out.strip()
    return json.loads(out)["hookSpecificOutput"]["additionalContext"] if out else None


def test_nudge_points_at_the_shipped_copy_when_there_is_no_local_one(tmp_path, monkeypatch, capsys):
    """Retiring a local tool after contributing it upstream must not silence its nudge.

    The tools most worth nudging about are exactly the ones broadly useful enough to ship, so
    keying the nudge on the LOCAL file alone turns a successful contribution into a lost guard.
    """
    monkeypatch.setenv("HOME", str(tmp_path))          # no local toolbox at all
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    msg = _run(_event("pkill -f myserver"), monkeypatch, capsys)
    assert msg is not None, "nudge went silent for a tool that ships with the plugin"
    assert "compuse-toolbox" in msg and "procsig" in msg


def test_a_local_tool_still_wins(tmp_path, monkeypatch, capsys):
    """Local-only tools (no shipped twin) keep working, and a local copy is preferred if present."""
    tools = tmp_path / ".claude" / "skills" / "toolbox" / "tools"
    tools.mkdir(parents=True)
    (tools / "procsig.py").write_text("# local\n", encoding="utf-8")
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    msg = _run(_event("pkill -f myserver", session="s2"), monkeypatch, capsys)
    assert msg is not None and "skills/toolbox/tools/procsig.py" in msg


def test_still_silent_for_a_tool_that_exists_nowhere(tmp_path, monkeypatch, capsys):
    """Must-not-break: a match for a tool neither local nor shipped stays silent."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setattr(N, "_shipped_dir", lambda: _no_shipped_tree(tmp_path))
    assert _run(_event("pkill -f myserver", session="s3"), monkeypatch, capsys) is None


def test_a_single_quoted_commit_message_is_not_a_tool_invocation():
    """A commit message DESCRIBING a trap is not an instance of it. The message is single-quoted,
    so nothing in it runs, and nudging there blocks the writing of the very guidance. The blanking
    lives in extract_text, which is what main() feeds match_tool - match_tool itself takes raw
    text, so driving it directly would bypass the fix and assert nothing."""
    text = N.extract_text("Bash", {"command":
        "git commit -m 'docs: warn about the p" + "grep -f self-match trap'"})
    assert N.match_tool(text) is None


def test_a_flag_from_a_later_statement_is_not_greps():
    """`grep -rn "needle" src/ && ls -la` - the `-l` is ls's. The pattern stopped at a pipe or a
    semicolon but not at an &&, so it read across into the next command."""
    assert N.match_tool('grep -rn "needle" src/ && ls -la') is None


def test_a_real_grep_count_flag_is_still_nudged():
    """The direction where it must NOT apply."""
    assert N.match_tool('grep -c "needle" src/') is not None


# ---- rules for the tools that shipped without one ------------------------------------------------
# Every pattern below was priced over a frozen corpus of 79,052 authored calls from 493 sessions
# and adjudicated against the calls it fires on, never against its own match count. The bar is the
# shipped claim_check rule, which already speaks in 57.6% of sessions: what disqualifies a rule
# here is precision, not volume.

def test_match_pushcheck_on_a_real_push():
    """The moment to ask "does this repo publish something private" is the push itself."""
    assert N.match_tool("git push origin main", "Bash")[0] == "pushcheck"
    assert N.match_tool("cd /repo && make push", "Bash")[0] == "pushcheck"


def test_pushcheck_is_shell_only_so_authoring_a_script_is_not_a_push():
    """A Write body containing `git push` is a script being AUTHORED, not a push being run.

    Measured: this shape dominated the rule's firings before it was scoped, so the nudge would
    have spoken while writing a release doc and stayed useful only by accident."""
    body = "#!/usr/bin/env bash\nset -e\ngit push origin main\n"
    matched = N.match_tool(N.extract_text("Write", {"content": body}), "Write")
    assert matched is None or matched[0] != "pushcheck"


def test_match_ci_wait_on_a_run_poll():
    assert N.match_tool("gh run list --limit 1", "Bash")[0] == "ci_wait"
    assert N.match_tool("gh pr checks 12", "Bash")[0] == "ci_wait"


def test_match_gate_when_a_pipe_hides_the_exit_status():
    """`pytest ... | tail` reports the FILTER's status; that is the whole point of `gate`."""
    assert N.match_tool("pytest tests/ -q 2>&1 | tail -15", "Bash")[0] == "gate"
    assert N.match_tool("make test && ./deploy.sh", "Bash")[0] == "gate"


def test_a_gated_push_routes_to_pushcheck_not_gate():
    """`make test && git push` carries both shapes. The push is the irreversible half - what it
    publishes cannot be unpublished - so pushcheck is listed first and wins."""
    assert N.match_tool("make test && git push", "Bash")[0] == "pushcheck"


def test_match_backstop_on_a_hand_rolled_wait_loop():
    assert N.match_tool("sleep 300; cat /tmp/job.log", "Bash")[0] == "backstop"
    assert N.match_tool("nohup ./long-job.sh &", "Bash")[0] == "backstop"


def test_a_ci_poll_loop_routes_to_ci_wait_not_backstop():
    """Both shapes sit in `for ...; do sleep 30; gh run list; done`, and the tool answering the
    actual question - did CI finish on MY commit - is the better nudge, so ci_wait is listed
    first. Ordering is behaviour here, not tidiness: the rules are first-match-wins."""
    loop = "for i in $(seq 1 8); do sleep 30; gh run list --json headSha; done"
    assert N.match_tool(loop, "Bash")[0] == "ci_wait"


# ---- recall: shapes the rules above went silent on ------------------------------------------------
# Found by replaying a wider, independent oracle over 79,213 recorded Bash calls and reading every
# silent hit: about 30 real pushes and about 66 hand-rolled waits went un-nudged. Each case below is
# one of those recorded shapes, reduced.

def _bash(command):
    """The verdict production gives a Bash call: the same text extraction, then the rules."""
    matched = N.match_tool(N.extract_text("Bash", {"command": command}), "Bash")
    return matched[0] if matched else None


def test_pushcheck_sees_a_push_on_a_later_line():
    """A multi-line command puts the push on its own line. Without multi-line matching the `^`
    alternative only ever meant the first character of the whole command."""
    assert _bash("cd /repo\ngit push origin main") == "pushcheck"
    assert _bash('tail -3 "$SP/c.txt"\ngit push origin master > "$SP/p.txt" 2>&1') == "pushcheck"


def test_pushcheck_sees_a_push_behind_an_environment_prefix():
    assert _bash("LC_ALL=C git push") == "pushcheck"
    assert _bash("env -u VIRTUAL_ENV git push origin HEAD:master") == "pushcheck"
    assert _bash("cd /r && env -u GIT_DIR -u GIT_INDEX_FILE git push origin master") == "pushcheck"


def test_pushcheck_sees_a_push_behind_git_global_options():
    """`git -C <repo> push` is how a loop over several repos pushes each one."""
    assert _bash('git -C "$r" push origin main') == "pushcheck"
    assert _bash("git -C $r -c credential.helper='!gh auth git-credential' push origin main") \
        == "pushcheck"


def test_pushcheck_still_ignores_prose_that_names_a_push():
    """Mid-sentence text is not a statement: the anchors stay line start or a separator."""
    assert _bash("echo we never git push here") is None
    assert _bash("grep -n 'git push' CLAUDE.md") != "pushcheck"


def test_backstop_sees_a_polling_loop_with_a_short_sleep():
    """The original rule knew only `sleep` of 10 or more; a poll sleeps 3-6 seconds a turn."""
    assert _bash("until grep -qE '^RC=' /tmp/s.log; do sleep 5; done; tail -4 /tmp/s.log") \
        == "backstop"
    assert _bash("i=0; until [ -s out.jsonl ] || [ $i -ge 60 ]; do sleep 3; i=$((i+1)); done") \
        == "backstop"
    assert _bash("until grep -q passed t.output\ndo\n  sleep 5\ndone") == "backstop"


def test_backstop_sees_process_absence_read_as_finished():
    """No process is not the same as success: a crash leaves the table just as empty."""
    assert _bash("ps -eo etimes,comm | grep -w pytest || echo FINISHED") == "backstop"
    assert _bash("ps -eo etime,args | grep '[b]ench' | head -1 || { echo FINISHED; tail -5 l; }") \
        == "backstop"


def test_backstop_ignores_a_sleep_after_a_loop_that_ended():
    """A `sleep 1` AFTER `done` is not inside the loop, so the loop is not a poll."""
    assert _bash("pgrep x | while read p; do kill $p; done; sleep 1; ls") is None
    assert _bash("while read -r f; do wc -l \"$f\"; done < list.txt") is None


def test_match_transcript_index_on_a_hand_walk_over_past_sessions():
    assert N.match_tool("grep -rn needle ~/.claude/projects/", "Bash")[0] == "transcript_index"


def test_match_anchor_edit_on_sed_in_place():
    assert N.match_tool("sed -i 's/a/b/' pyproject.toml", "Bash")[0] == "anchor_edit"


def test_match_srccount_on_find_piped_to_wc():
    assert N.match_tool("find src -name '*.py' | wc -l", "Bash")[0] == "srccount"


def test_match_newest_only_on_the_pick_the_latest_shape():
    """`ls | sort | tail -1` picks by NAME, so a longer name sharing the date prefix wins.

    A bare `ls dir/ | head` is a listing, not a latest-of question: measured, the unnarrowed
    rule fired 2,591 times and 0 of 8 sampled firings were about picking the latest."""
    assert N.match_tool("ls -d ~/.claude/plugins/cache/x/*/ | tail -1", "Bash")[0] == "newest"
    assert N.match_tool("ls backups/*.tgz | sort | tail -1", "Bash")[0] == "newest"
    for listing in ("ls tests/ | head -80", "ls -la | head -40"):
        matched = N.match_tool(listing, "Bash")
        assert matched is None or matched[0] != "newest", listing


def test_match_winlog_transfer_and_wtclean():
    assert N.match_tool("iconv -f UTF-16 -t UTF-8 cbs.log", "Bash")[0] == "winlog"
    assert N.match_tool("curl --limit-rate 8M -O http://h/f.iso", "Bash")[0] == "transfer"
    assert N.match_tool("git worktree remove ../wt-x", "Bash")[0] == "wtclean"


def test_plain_commands_still_nudge_about_nothing():
    """The rules added above must not turn ordinary work into a nudge."""
    for cmd in ("ls -la", "cd /repo && git status", "echo hello", "cat README.md",
                "python3 -m pytest -q", "git commit -F msg.txt"):
        assert N.match_tool(cmd, "Bash") is None, cmd


def test_a_tool_owned_by_a_sibling_skill_resolves_and_names_its_owner(home, monkeypatch, capsys):
    """compuse-toolbox's table documents tools that ship under a DIFFERENT skill.

    Resolving only against compuse-toolbox/scripts made those rules silent, which reads exactly
    like having no rule at all. The nudge must find the file and name the skill that owns it -
    pointing a reader at compuse-toolbox for a file that is not there is worse than silence.
    """
    (home / ".claude" / "skills" / "toolbox" / "tools").mkdir(parents=True)
    skills = home / "plugin" / "skills"
    (skills / "compuse-toolbox" / "scripts").mkdir(parents=True)
    (skills / "git-worktrees" / "scripts").mkdir(parents=True)
    (skills / "git-worktrees" / "scripts" / "wtclean.py").write_text("x", encoding="utf-8")
    monkeypatch.setattr(N, "_shipped_dir", lambda: skills / "compuse-toolbox" / "scripts")
    _feed(monkeypatch, _ev("git worktree remove ../wt-x", "s-sibling"))
    N.main()
    out = capsys.readouterr().out
    assert "wtclean" in out and "bitranox:git-worktrees" in out
    assert "compuse-toolbox" not in out


# ---- rules for LOCAL jigs -------------------------------------------------------------------------
# These ship here like `guestip` and `ovmlog` already do, even though the tools live only in a
# personal ~/.claude/skills/toolbox. The resolver falls back to silence for anyone without the
# file, and a rule kept only on the machine that has the tool is a rule nobody can review.

def test_match_statusrot_on_a_status_sweep_of_the_fact_store():
    """Hand-rolled twice in sessions where statusrot already existed and nothing named it."""
    assert N.match_tool(
        "grep -rn 'shipped' /media/srv-main-softdev/.claude-memory/facts/", "Bash")[0] == "statusrot"


def test_match_factedit_on_editing_a_fact_by_hand():
    assert N.match_tool(
        "vim /media/srv-main-softdev/.claude-memory/facts/no-em-dashes.md", "Bash")[0] == "factedit"


def test_match_mdwrap_on_reflowing_a_paragraph():
    assert N.match_tool("fold -s -w 100 TODO.md", "Bash")[0] == "mdwrap"


def test_an_identifier_rename_routes_to_renamescope_not_anchor_edit():
    """Both rules match `sed -i`, and the more specific one has to be listed first or it is dead:
    measured, all 23 firings of the rename shape were already claimed by anchor_edit."""
    assert N.match_tool("sed -i 's/old_name/new_name/g' src/mod.py", "Bash")[0] == "renamescope"
    assert N.match_tool("sed -i '3d' notes.md", "Bash")[0] == "anchor_edit"


def test_a_tool_kept_at_a_skill_root_resolves_and_names_that_skill(home, monkeypatch, capsys):
    """The catalogue uses BOTH layouts: compuse-toolbox keeps tools in scripts/, meta-dream-tree
    keeps them beside its SKILL.md. Globbing only the first made a root-level tool resolve
    nowhere, and the owner must come from the component under skills/ - `parent.parent` names
    the skill only in the scripts/ layout and yields `skills` itself for the other.
    """
    (home / ".claude" / "skills" / "toolbox" / "tools").mkdir(parents=True)
    skills = home / "plugin" / "skills"
    (skills / "compuse-toolbox" / "scripts").mkdir(parents=True)
    (skills / "meta-dream-tree").mkdir(parents=True)
    (skills / "meta-dream-tree" / "statusrot.py").write_text("x", encoding="utf-8")
    monkeypatch.setattr(N, "_shipped_dir", lambda: skills / "compuse-toolbox" / "scripts")
    _feed(monkeypatch, _ev("grep -rn shipped /srv/.claude-memory/facts/", "s-root"))
    N.main()
    out = capsys.readouterr().out
    assert "statusrot" in out and "bitranox:meta-dream-tree" in out

# ---- a chore authored INSIDE a heredoc body ----------------------------------------------------
# Measured 2026-09-23 with jig_probe over 60 recorded calls: the commonest real spelling of
# anchor_edit's chore is a Python heredoc doing an exact-text replace, and no rule could ever see
# it - extract_text blanks the whole body, so what survived was a trailing `pytest ... 2>&1 |
# tail` and `gate` matched that instead. A body is not only data; it is also a program being
# AUTHORED, which is the reading the hook already gives Write and Edit content. So the body gets
# the authored-text rules, and the command keeps getting the command rules.

_OPEN = "<<" + "'PY'"
_REPLACE_IN_A_HEREDOC = (
    "python3 - %s\n"
    "from pathlib import Path\n"
    "p = Path('src/app.py')\n"
    "s = p.read_text(encoding='utf-8')\n"
    "old = '''    self.findings = diagnose(self.inventory)'''\n"
    "p.write_text(s.replace(old, '    pass'), encoding='utf-8')\n"
    "PY\n" % _OPEN
)


def test_a_replace_authored_in_a_heredoc_is_routed_to_anchor_edit():
    body = shell_text.heredoc_bodies(_REPLACE_IN_A_HEREDOC)
    assert "write_text" in body                      # the body really reached the matcher
    assert N.match_authored(body)[0] == "anchor_edit"


def test_the_command_rules_see_nothing_of_the_chore_in_that_command():
    # the premise of the whole change: the visible text carries no sign of it
    text = N.extract_text("Bash", {"command": _REPLACE_IN_A_HEREDOC})
    assert N.match_tool(text, tool_name="Bash") is None


def test_prose_that_merely_names_the_chore_is_still_not_a_firing():
    # why bodies were blanked in the first place - documenting a footgun must not trip the guard
    doc = ("cat > notes.md %s\n"
           "Never hand-roll it: read_text then write_text with a replace is the trap\n"
           "EOF\n" % ("<<" + "'EOF'"))
    assert N.match_authored(shell_text.heredoc_bodies(doc)) is None


def test_the_authored_pass_does_not_use_the_shell_only_rules():
    # a shell-only rule must not fire on authored text, which is what the split is for
    assert N.match_authored("git push origin master") is None


def test_the_command_reading_keeps_precedence_over_the_authored_one():
    # the command rules are the shipped, measured behaviour; the authored pass only extends reach
    command = _REPLACE_IN_A_HEREDOC + "pgrep -f something\n"
    text = N.extract_text("Bash", {"command": command})
    assert N.match_tool(text, tool_name="Bash")[0] == "procsig"


# ---- how to LAUNCH the tool comes from the tool, not from the hook ------------------------------
#
# The nudge suggested `uv run <tool>.py --help` for every tool. mutation_arm runs its arm as
# `<its own interpreter> -m pytest`, so under `uv run` - an isolated interpreter with neither
# pytest nor the project - every arm reads INCONCLUSIVE. The tool DECLARES its launch
# (`LAUNCH_WITH`), read from its source without importing it, so the next tool with the same need
# states it once and cannot be forgotten by a special case in this hook.

def _nudge_for(cmd, session, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("HOME", str(tmp_path))          # no local toolbox: the shipped copy answers
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    return _run(_event(cmd, session=session), monkeypatch, capsys)


def test_mutation_arm_is_suggested_with_the_project_interpreter_not_uv_run(tmp_path, monkeypatch,
                                                                            capsys):
    msg = _nudge_for("git stash && pytest tests/t.py::test_y", "m1", tmp_path, monkeypatch, capsys)
    assert msg is not None and "mutation_arm" in msg
    assert "uv run" not in msg, msg
    assert ".venv" in msg and "mutation_arm.py --help" in msg


def test_a_tool_declaring_nothing_is_still_suggested_with_uv_run(tmp_path, monkeypatch, capsys):
    """Control: the default launch is unchanged for every tool that declares no requirement."""
    msg = _nudge_for("pkill -f myserver", "m2", tmp_path, monkeypatch, capsys)
    assert msg is not None and "uv run " in msg and "procsig.py --help" in msg


def test_the_declaration_is_read_without_executing_the_tool(tmp_path):
    tool = tmp_path / "t.py"
    tool.write_text('raise SystemExit("importing me is a bug")\nLAUNCH_WITH = "project-python"\n',
                    encoding="utf-8")
    assert N.declared_launch(tool) == "project-python"


def test_an_absent_or_unreadable_declaration_means_uv(tmp_path):
    plain = tmp_path / "plain.py"
    plain.write_text("x = 1\n", encoding="utf-8")
    broken = tmp_path / "broken.py"
    broken.write_text("def (:\n", encoding="utf-8")
    assert N.declared_launch(plain) == "uv"
    assert N.declared_launch(broken) == "uv"
    assert N.declared_launch(tmp_path / "missing.py") == "uv"


def test_an_unknown_declaration_never_falls_back_to_uv_run(tmp_path):
    """A value this hook does not know is a requirement it cannot honour - naming `uv run` anyway
    would be the defect this section exists to remove."""
    tool = tmp_path / "t.py"
    tool.write_text('LAUNCH_WITH = "conda-env"\n', encoding="utf-8")
    cmd, note = N.launch_command(tool)
    assert "uv run" not in cmd + note and str(tool) in cmd
    assert "conda-env" in note, "the reader is told why no launcher was given"


def _shipped_nudge_targets(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    targets = {}
    for tool in sorted(N.ruled_tools()):
        found = N._tool_invocation(tool)
        if found is not None:
            targets[tool] = found[1]
    return targets


def test_every_nudged_tool_declares_a_launch_this_hook_knows(tmp_path, monkeypatch):
    for tool, path in _shipped_nudge_targets(tmp_path, monkeypatch).items():
        assert N.declared_launch(path) in N.LAUNCHERS, tool
        # The docstring route too: an ambiguous or unknown launch would print no launcher at all.
        assert N.resolve_launch(path) in N.LAUNCHERS, tool


def test_a_nudged_tool_that_runs_pytest_on_its_own_interpreter_declares_the_project_python(
        tmp_path, monkeypatch):
    """The shape, not the instance: a tool whose work is `sys.executable -m pytest` is only as good
    as the interpreter it was launched with, so it must say so or the nudge sends it to uv."""
    runs_own_pytest = re.compile(r"sys\.executable\s*,\s*[\"']-m[\"']\s*,\s*[\"']pytest[\"']")
    checked = []
    for tool, path in _shipped_nudge_targets(tmp_path, monkeypatch).items():
        if runs_own_pytest.search(Path(path).read_text(encoding="utf-8")):
            checked.append(tool)
            assert N.declared_launch(path) == "project-python", tool
    assert "mutation_arm" in checked, "the detector must see the tool it was written for"


# ---- a tool that says how to launch it in its DOCSTRING is launched that way -------------------
#
# gate.py's docstring says "plain python3, NOT uv run" - under `uv run` the gates it runs inherit
# uv's isolated interpreter on PATH, so a `python3 -m pytest` gate dies with `No module named
# pytest` and reads as RED. It declared no LAUNCH_WITH, so the nudge (and the background-gate
# block) told agents `uv run gate.py`: the one launch the jig forbids. A launch documented for the
# tool itself is now a declaration too, so a tool that writes its launch down once is believed.

_PLAIN_PY = "python" if os.name == "nt" else "python3"
_EXPECTED_PREFIX = {
    "uv": "uv run ",
    "python3": _PLAIN_PY + " ",
    "project-python": (".venv\\Scripts\\python.exe " if os.name == "nt" else ".venv/bin/python "),
}


def _tool_file(tmp_path, doc, body="", name="t.py"):
    tool = tmp_path / name
    tool.write_text('"""' + doc + '"""\n' + body, encoding="utf-8")
    return tool


@pytest.mark.parametrize(
    ("label", "doc", "expected"),
    [
        ("plain python3", "Run:\n  python3 scripts/t.py --x 1\n", "python3"),
        ("the plugin shim", "Run:\n  `bash hooks/run-python.sh skills/s/t.py show`\n", "python3"),
        ("the project venv", "Run:\n  `.venv/bin/python scripts/t.py --mutate a`\n",
         "project-python"),
        ("a uv counter-example beside the real launch",
         "Run (plain python3, NOT uv run):\n  `uv run scripts/t.py` is wrong here\n"
         "  python3 scripts/t.py -- pytest -q\n", "python3"),
    ],
)
def test_a_launch_documented_for_the_tool_itself_is_the_one_suggested(tmp_path, label, doc,
                                                                       expected):
    cmd, _note = N.launch_command(_tool_file(tmp_path, doc))
    assert cmd.startswith(_EXPECTED_PREFIX[expected]), (label, cmd)


@pytest.mark.parametrize(
    ("label", "doc"),
    [
        ("uv run only", "Run: `uv run scripts/t.py --root .`\n"),
        ("no launch written at all", "Does a thing.\n"),
        ("python3 launching a DIFFERENT file",
         'Run: `uv run scripts/t.py --a "python3 old.py" --b "python3 new.py"`\n'),
        ("python3 on a file whose name only ENDS like this one", "Run: python3 scripts/not_t.py\n"),
    ],
)
def test_a_tool_that_documents_no_other_launch_is_still_suggested_with_uv_run(tmp_path, label,
                                                                              doc):
    """Controls: only a launch of THIS file counts, and uv stays the default."""
    cmd, _note = N.launch_command(_tool_file(tmp_path, doc))
    assert cmd.startswith("uv run "), (label, cmd)


def test_two_different_documented_launches_suggest_neither(tmp_path):
    """A docstring that shows the tool run two non-uv ways is ambiguous: guessing either one is
    the wrong-interpreter suggestion this section removes, so the reader is sent to the doc."""
    doc = "Run:\n  python3 scripts/t.py a\n  .venv/bin/python scripts/t.py b\n"
    tool = _tool_file(tmp_path, doc)
    cmd, note = N.launch_command(tool)
    assert cmd == "%s --help" % tool, cmd
    assert "docstring" in note and "uv run" not in cmd + note


def test_a_declaration_outranks_the_docstring(tmp_path):
    tool = _tool_file(tmp_path, "Run: python3 scripts/t.py\n", body='LAUNCH_WITH = "uv"\n')
    assert N.launch_command(tool)[0].startswith("uv run ")


def test_the_docstring_is_read_without_executing_the_tool(tmp_path):
    tool = _tool_file(tmp_path, "Run: python3 scripts/t.py\n",
                      body='raise SystemExit("importing me is a bug")\n')
    assert N.launch_command(tool)[0].startswith(_EXPECTED_PREFIX["python3"])


def test_the_plain_interpreter_note_says_why_uv_run_is_wrong(tmp_path):
    _cmd, note = N.launch_command(_tool_file(tmp_path, "Run: python3 scripts/t.py\n"))
    assert "uv run" in note and "RED" in note, note


def test_gate_is_suggested_with_a_plain_interpreter_not_uv_run(tmp_path, monkeypatch, capsys):
    """The reported instance, end to end through main()."""
    msg = _nudge_for("pytest -q | tail -3", "g1", tmp_path, monkeypatch, capsys)
    assert msg is not None and "gate.py --help" in msg, msg
    assert "uv run" not in msg.split("gate.py --help")[0], msg
    assert (_PLAIN_PY + " ") in msg, msg


# ---- the pin, per jig: what the nudge suggests is what the jig itself says --------------------

def _shipped_jigs():
    """{tool: shipped path} for every tool a rule can name, ignoring any local toolbox copy."""
    out = {}
    for tool in sorted(N.ruled_tools()):
        path = N._shipped_dir() / (tool + ".py")
        path = path if path.is_file() else N._sibling_skill_script(tool)
        if path is not None:
            out[tool] = path
    return out


_SHIPPED_JIGS = _shipped_jigs()


def _what_the_jig_says(path):
    """The launch the jig asks for, read INDEPENDENTLY of the hook's own parser: its
    `LAUNCH_WITH` line, else the word(s) in front of each whitespace token of its docstring that
    names this very file."""
    src = Path(path).read_text(encoding="utf-8")
    declared = re.search(r"^LAUNCH_WITH\s*(?::\s*str\s*)?=\s*[\"']([^\"']+)[\"']", src, re.M)
    if declared:
        return declared.group(1)
    said = set()
    for line in (ast.get_docstring(ast.parse(src)) or "").splitlines():
        words = [w.strip("`()'\"") for w in line.split()]
        for i, word in enumerate(words):
            if Path(word.replace("\\", "/")).name != Path(path).name or i == 0:
                continue
            before = words[i - 1]
            if before in ("python3", "python") or before.endswith("run-python.sh"):
                said.add("python3")
            elif ".venv" in before:
                said.add("project-python")
            elif before == "run" and i >= 2 and words[i - 2] == "uv":
                said.add("uv")
    non_uv = said - {"uv"}
    return non_uv.pop() if len(non_uv) == 1 else ("ambiguous" if non_uv else "uv")


def test_the_independent_reading_sees_the_jig_it_was_written_for():
    """Control: an oracle that answered "uv" for everything would pass the pin below vacuously."""
    assert _what_the_jig_says(_SHIPPED_JIGS["gate"]) == "python3"
    assert _what_the_jig_says(_SHIPPED_JIGS["mutation_arm"]) == "project-python"
    assert _what_the_jig_says(_SHIPPED_JIGS["procsig"]) == "uv"


@pytest.mark.parametrize("tool", sorted(_SHIPPED_JIGS))
def test_the_nudge_suggests_each_jig_the_way_the_jig_says_to_launch_it(tool):
    """The shape, not the instance: every jig a rule can name, against its own words. A new jig
    that documents a launch is covered the moment a rule names it, with no edit here."""
    path = _SHIPPED_JIGS[tool]
    expected = _what_the_jig_says(path)
    cmd, _note = N.launch_command(path)
    if expected == "ambiguous":
        assert cmd == "%s --help" % path, (tool, cmd)
    else:
        assert cmd.startswith(_EXPECTED_PREFIX[expected]), (tool, expected, cmd)


# ---- a jig that runs YOUR command must never be suggested under uv run ------------------------
#
# Measured 2026-09-26: under `uv run`, a child `python3` resolves to uv's ephemeral build env,
# which has no pytest. gate.py reported GATE RED rc=1 for a gate that passed under plain python3;
# ci_triage `--cmd "python3 -m pytest --version"` exited 1 with "No module named pytest" where
# python3 exited 0; transfer `check --cmd` read its sampler as unreadable (UNKNOWN, rc 2) where
# python3 read it (rc 1). A jig that only spawns a FIXED program (git, gh) is unaffected.

#: Nudged jigs that spawn a command the CALLER supplies, so its children inherit the launcher.
_RUNS_YOUR_COMMANDS = {
    "gate": "--gate / -- / --then",
    "ci_triage": "--cmd",
    "transfer": "check --cmd (a sampler)",
    "mutation_arm": "the arm's pytest, on its own interpreter",
}
#: Nudged jigs whose computed argv only ever names a fixed program, never the caller's command.
_SPAWNS_ONLY_FIXED_PROGRAMS = {
    "ci_wait": "gh run list",
    "pushcheck": "git",
    "wtclean": "git worktree remove",
    "factedit": "memory_engine.py, on the first NON-venv python3 on PATH (it skips uv's)",
}


def _spawns_a_computed_argv(path):
    """True when a subprocess call's argv is anything but a list literal led by a string - the
    only way a caller's command can reach a child. It sees `subprocess.<fn>(...)` calls only, so a
    runner injected as a parameter (fleet_ssh's `run=`) is not seen; ssh runs its command remotely,
    where the local PATH does not reach."""
    tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name) and node.func.value.id == "subprocess"
                and node.func.attr in ("run", "Popen", "call", "check_call", "check_output")):
            continue
        first = node.args[0] if node.args else None
        if not (isinstance(first, ast.List) and first.elts and isinstance(first.elts[0], ast.Constant)
                and isinstance(first.elts[0].value, str)):
            return True
    return False


def test_every_nudged_jig_that_spawns_a_computed_argv_is_classified():
    """The enumeration is pinned, not just its members: a new jig that runs a computed command
    fails here until someone decides which list it belongs in."""
    flagged = {tool for tool, path in _SHIPPED_JIGS.items() if _spawns_a_computed_argv(path)}
    assert "gate" in flagged, "the detector must see the jig it was written for"
    assert flagged == set(_RUNS_YOUR_COMMANDS) | set(_SPAWNS_ONLY_FIXED_PROGRAMS)


@pytest.mark.parametrize("tool", [
    "gate",
    "ci_triage",
    "transfer",
    "mutation_arm",
])
def test_a_nudged_jig_that_runs_your_commands_is_never_suggested_under_uv_run(tool):
    cmd, _note = N.launch_command(_SHIPPED_JIGS[tool])
    assert not cmd.startswith("uv run"), (tool, cmd)
