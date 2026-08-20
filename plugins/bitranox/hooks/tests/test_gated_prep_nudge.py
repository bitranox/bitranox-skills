"""Tests for gated-prep-nudge.py - warn when a gated verb shares a command with its own prep.

A PreToolUse gate judges the WHOLE command before any statement runs, so a block discards the
heredoc that wrote the commit message too. The retry then fails on a missing `-F` input and points
at the wrong cause. Recorded six times; this hook is the escalation from prose to a signal.
"""
import json

import gated_prep_nudge as N


def _ctx(command):
    """The additionalContext a PreToolUse run would emit, or None when it stays quiet."""
    return N.notice(command)


# --- it fires on the real shape -----------------------------------------------------------------

def test_heredoc_written_message_plus_git_commit_dash_f_is_flagged():
    """The exact shape that has cost six retries."""
    cmd = ("cat > /tmp/msg.txt <<'EOF'\nsubject line\n\nbody\nEOF\n"
           "git add -A && git commit -F /tmp/msg.txt")
    ctx = _ctx(cmd)
    assert ctx and "/tmp/msg.txt" in ctx and "commit" in ctx


def test_the_file_it_names_is_the_one_that_would_be_lost():
    cmd = "cat > notes/COMMIT_MSG <<EOF\nhi\nEOF\ngit commit -F notes/COMMIT_MSG"
    ctx = _ctx(cmd)
    assert "notes/COMMIT_MSG" in ctx


def test_git_push_counts_as_a_gated_verb():
    cmd = "cat > /tmp/m <<'EOF'\nx\nEOF\ngit push origin master"
    assert _ctx(cmd)


def test_printf_redirect_also_counts_as_prep():
    """Not every prep is a heredoc; a redirect that creates the input has the same failure."""
    cmd = "printf 'subject\\n' > /tmp/m.txt\ngit commit -F /tmp/m.txt"
    ctx = _ctx(cmd)
    assert ctx and "/tmp/m.txt" in ctx


def test_semicolon_separated_statements_are_seen():
    cmd = "cat > /tmp/m <<'EOF'\nx\nEOF\n; git commit -F /tmp/m"
    assert _ctx(cmd)


# --- it stays quiet otherwise -------------------------------------------------------------------

def test_a_commit_with_no_prep_in_the_same_command_is_quiet():
    """The correct shape must never be nagged, or the nudge trains itself out."""
    assert _ctx("git commit -F /tmp/msg.txt") is None


def test_writing_a_file_with_no_gated_verb_is_quiet():
    assert _ctx("cat > /tmp/notes.md <<'EOF'\nhello\nEOF") is None


def test_a_gated_verb_named_only_inside_the_heredoc_body_is_quiet():
    """The body is DATA. A guard that reads it fires on prose that documents the footgun."""
    cmd = ("cat > /tmp/doc.md <<'EOF'\n"
           "Never run `git commit -F msg` in the same command that writes msg.\n"
           "EOF\n"
           "echo done")
    assert _ctx(cmd) is None


def test_a_gated_verb_inside_a_heredoc_plus_an_unrelated_write_is_quiet():
    cmd = ("cat > /tmp/a.md <<'EOF'\ngit push origin master\nEOF\n"
           "cat > /tmp/b.md <<'EOF'\nmore prose\nEOF")
    assert _ctx(cmd) is None


def test_a_non_gated_git_verb_is_quiet():
    assert _ctx("cat > /tmp/m <<'EOF'\nx\nEOF\ngit status --porcelain") is None


def test_empty_and_garbage_input_never_raise():
    for cmd in ("", "   ", None, "cat > <<", "git commit -F"):
        N.notice(cmd)


# --- the hook contract --------------------------------------------------------------------------

def test_main_emits_additional_context_and_exits_zero(capsys):
    """Non-blocking: exit 0 with hookSpecificOutput, never a permissionDecision."""
    event = {"tool_name": "Bash",
             "tool_input": {"command": "cat > /tmp/m <<'EOF'\nx\nEOF\ngit commit -F /tmp/m"}}
    code = N.main(json.dumps(event))
    out = capsys.readouterr().out
    assert code == 0
    payload = json.loads(out)
    assert payload["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
    assert "additionalContext" in payload["hookSpecificOutput"]
    assert "permissionDecision" not in payload["hookSpecificOutput"]


def test_main_is_silent_for_a_clean_command(capsys):
    event = {"tool_name": "Bash", "tool_input": {"command": "git commit -F /tmp/m"}}
    assert N.main(json.dumps(event)) == 0
    assert capsys.readouterr().out.strip() == ""


def test_main_never_wedges_on_malformed_input(capsys):
    for raw in ("", "not json", "{}", '{"tool_name": "Bash"}'):
        assert N.main(raw) == 0


def test_a_non_bash_tool_is_ignored(capsys):
    event = {"tool_name": "Write", "tool_input": {"content": "git commit -F x"}}
    assert N.main(json.dumps(event)) == 0
    assert capsys.readouterr().out.strip() == ""


# ---- gaps found by probing the shipped hook, 2026-08-09 ----------------------------------------
# The fact this hook serves says a further hit is a hook gap, not a wording gap, and names the fix:
# widen the gated-verb set or the prep shapes, and add the command that slipped through as a
# regression test. These three slipped through.

def test_gh_pr_create_is_a_gated_verb_too():
    """repo-gate blocks `gh pr create`, so a body file written beside it is lost the same way."""
    assert N.notice('printf "body" > body.md; gh pr create --body-file body.md') is not None


def test_a_heredoc_body_that_writes_the_file_counts_as_prep():
    """`python3 - <<PY ... open(f, "w") ... PY` writes with no redirect, so no `>` to match on."""
    command = ('python3 - <<\'PY\'\n'
               'open("msg.txt", "w").write("subject")\n'
               'PY\n'
               'git commit -F msg.txt')
    assert N.notice(command) is not None


def test_an_inline_interpreter_write_counts_as_prep():
    assert N.notice('python3 -c \'open("msg.txt","w").write("x")\'; git commit -F msg.txt') is not None
    assert N.notice('python3 -c \'from pathlib import Path; Path("m").write_text("x")\'; git push') is not None


def test_the_write_scan_reads_bodies_while_the_verb_scan_does_not():
    """Asymmetric ON PURPOSE: the write lives IN the body, the verb must not be faked BY one."""
    prose_only = "cat > doc.md <<'EOF'\nnever run git commit here\nEOF"
    assert N.notice(prose_only) is None


def test_an_interpreter_that_only_reads_is_not_prep():
    """The negative must stay reachable, or every python heredoc before a commit nags."""
    assert N.notice('python3 -c \'print(open("f").read())\'; git commit -m "x"') is None
    assert N.notice("python3 - <<'PY'\nprint(1)\nPY\ngit commit -m 'x'") is None


# ---- gap found 2026-08-20: prep that changes the TREE and writes no file ------------------------
# Hit 7. The command was `git checkout -- <file> && git commit -F msg.txt`, run to discard churn in
# a file the gate was blocking on. It wrote nothing, so the write scan never matched - yet it is the
# same footgun, and a sharper one: the gate reads the tree BEFORE the restore, so this shape can
# never satisfy it in one command however many times it is retried.

def test_a_working_tree_restore_before_a_commit_is_flagged():
    """The exact command from hit 7."""
    cmd = "git checkout -- path/to/SKILL.md && git commit -F /tmp/msg.txt -- some/dir"
    ctx = N.notice(cmd)
    assert ctx is not None
    assert "checkout" in ctx


def test_other_tree_writing_verbs_are_flagged_too():
    for cmd in ("git stash && git commit -m x",
                "git reset --hard HEAD~1 && git push origin master",
                "git restore --staged f && git commit -m x",
                "git clean -fd; git commit -m x",
                "git switch master && git push"):
        assert N.notice(cmd) is not None, cmd


def test_the_message_says_the_gate_reads_the_tree_before_the_prep():
    ctx = N.notice("git checkout -- f && git commit -m x")
    assert "before" in ctx.lower()


# --- and the directions it must NOT fire ---------------------------------------------------------

def test_a_tree_writing_verb_AFTER_the_gated_verb_is_quiet():
    """Order is the whole point: a cleanup after a commit is not prep for it."""
    assert N.notice("git commit -m x && git checkout -- other/file") is None


def test_git_add_before_a_commit_is_not_flagged():
    """`add` is deliberately excluded.

    It touches the index, not the working tree, and losing it to a block produces no confusing
    missing-input error - the retry simply re-adds. It is also the single most common idiom before
    a commit, and another rule in this store actively prescribes it for a new file, so nudging on
    it would contradict guidance and train the reader to ignore the channel.
    """
    assert N.notice("git add -A && git commit -m x") is None
    assert N.notice("git add path/to/new.py && git commit path/to/new.py -m x") is None


def test_a_restore_named_only_inside_a_heredoc_body_is_quiet():
    """The body is DATA - this file's own documentation must not trip its guard."""
    cmd = ("cat > /tmp/doc.md <<'EOF'\n"
           "Never chain `git checkout -- f && git commit -m x`: the gate reads the tree first.\n"
           "EOF\n"
           "echo done")
    assert N.notice(cmd) is None


def test_a_tree_writing_verb_with_no_gated_verb_is_quiet():
    assert N.notice("git checkout -- f && git status --porcelain") is None
    assert N.notice("git stash") is None


def test_a_non_git_command_mentioning_checkout_is_quiet():
    assert N.notice("echo checkout && git commit -m x") is None


# ---- completing the verb set, 2026-08-20 --------------------------------------------------------
# The first pass shipped eight verbs, which was not a reasoned subset - it was the list that got
# typed. The gate reads `git diff --name-only origin/master` plus `git ls-files --others`, so its
# verdict moves with the WORKING TREE and with the `origin/master` REF. Both families qualify.

def test_history_rewriting_verbs_are_prep_too():
    for cmd in ("git merge feature && git commit -m x",
                "git rebase master && git push --force-with-lease",
                "git cherry-pick abc123 && git push",
                "git revert HEAD && git commit -m x",
                "git am < patch.eml && git push",
                "git apply fix.patch && git commit -m x",
                "git worktree add ../wt && git commit -m x",
                "git clone https://example.com/r.git sub && git commit -m x"):
        assert N.notice(cmd) is not None, cmd


def test_verbs_that_move_origin_master_are_prep_too():
    """`fetch` writes no file, but the gate compares against `origin/master`, which it moves.

    Verified against repo-gate: `_changed_vs_origin` runs `git diff --name-only origin/master`, so
    a fetch between the gate's read and the push changes the answer.
    """
    assert N.notice("git fetch origin && git push origin master") is not None
    assert N.notice("git pull --rebase && git push") is not None


def test_the_message_names_the_right_mechanism_for_each_family():
    tree = N.notice("git checkout -- f && git commit -m x")
    assert "working tree" in tree and "origin/master" not in tree
    fetch = N.notice("git fetch && git push")
    assert "origin/master" in fetch and "working tree" not in fetch
    pull = N.notice("git pull && git push")
    assert "working tree" in pull and "origin/master" in pull


def test_a_read_only_git_verb_is_still_not_prep():
    """The exemption direction: querying commands must stay quiet, or every sequence nags."""
    for cmd in ("git status --porcelain && git commit -m x",
                "git log --oneline -1 && git push",
                "git diff --stat && git commit -m x",
                "git rev-parse HEAD && git push"):
        assert N.notice(cmd) is None, cmd
