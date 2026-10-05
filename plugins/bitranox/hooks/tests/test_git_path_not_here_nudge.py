"""Tests for git-path-not-here-nudge.py - a path-status answer about a path that is not here. ASCII."""
import json
import os
import subprocess
import sys
from pathlib import Path

import git_path_not_here_nudge as G

_HOOK = Path(__file__).resolve().parent.parent / "git-path-not-here-nudge.py"


def _repo(tmp_path, name):
    """A directory that looks like a git work tree to the detector."""
    root = tmp_path / name
    (root / ".git").mkdir(parents=True)
    return root


def _sh(path):
    """`path` as a Bash command operand: double-quoted, forward slashes (bash eats an unquoted
    Windows path's backslashes)."""
    return '"%s"' % Path(path).as_posix()


# --- must fire -------------------------------------------------------------------------------

def test_error_unmatch_about_a_file_that_lives_in_the_parent_project_fires(tmp_path):
    # The measured incident: the shell was left in a sub-repo by an EARLIER call, so a later
    # `git ls-files --error-unmatch handover.md` answered from there. rc 1 reads as "untracked",
    # when it actually means "no such file in THIS repo".
    outer = _repo(tmp_path, "umbrella")
    (outer / "handover.md").write_text("x")
    inner = _repo(outer, "planning")
    msg = G.notice("git ls-files --error-unmatch handover.md >/dev/null 2>&1", str(inner))
    assert msg is not None
    assert "handover.md" in msg


def test_check_ignore_about_a_path_that_lives_in_the_parent_project_fires(tmp_path):
    outer = _repo(tmp_path, "project")
    (outer / ".claude").mkdir()
    inner = _repo(outer / ".claude" / "worktrees", "wt")
    assert G.notice("git check-ignore -v .claude 2>&1", str(inner)) is not None


# --- must NOT fire ---------------------------------------------------------------------------

def test_a_path_that_exists_under_the_cwd_is_silent(tmp_path):
    here = _repo(tmp_path, "here")
    (here / "README.md").write_text("x")
    assert G.notice("git ls-files --error-unmatch README.md", str(here)) is None


def test_a_path_present_in_BOTH_the_cwd_and_an_ancestor_is_silent(tmp_path):
    # The guard that actually earns its keep. A name like README.md or CLAUDE.md commonly exists in
    # a sub-repo AND in the project above it; without the "exists under the cwd" test this hook
    # would fire on every such call. Pinned because a mutation removing that test left the rest of
    # this suite green - the ancestor check absorbed it, so nothing else here can fail on it.
    outer = _repo(tmp_path, "outer")
    (outer / "README.md").write_text("outer")
    inner = _repo(outer, "inner")
    (inner / "README.md").write_text("inner")
    assert G.notice("git ls-files --error-unmatch README.md", str(inner)) is None


def test_a_call_that_cds_first_is_silent(tmp_path):
    # An explicit cd states the subject. The two-work-tree shape belongs to git-wrong-repo-nudge;
    # this hook only judges a call that relies on the cwd an earlier call left behind.
    outer = _repo(tmp_path, "outer")
    (outer / "f.md").write_text("x")
    inner = _repo(outer, "inner")
    assert G.notice(f"cd {_sh(outer)} && git ls-files --error-unmatch f.md", str(inner)) is None


def test_a_cd_in_a_loop_body_or_a_pushd_states_the_subject_too(tmp_path):
    # The private regex this hook carried knew `cd` only at statement start: `do cd X` and
    # `pushd X` both moved the shell while the hook judged the question as if nothing had.
    outer = _repo(tmp_path, "outer")
    (outer / "f.md").write_text("x")
    inner = _repo(outer, "inner")
    question = "git ls-files --error-unmatch f.md"
    assert G.notice(question, str(inner)) is not None                      # control: it fires
    assert G.notice(f"for i in 1; do cd {_sh(outer)} && {question}; done", str(inner)) is None
    assert G.notice(f"pushd {_sh(outer)} && {question}", str(inner)) is None


def test_an_absolute_path_is_silent(tmp_path):
    outer = _repo(tmp_path, "outer")
    (outer / "f.md").write_text("x")
    inner = _repo(outer, "inner")
    assert G.notice(f"git ls-files --error-unmatch {outer / 'f.md'}", str(inner)) is None


def test_an_unreadable_path_is_silent(tmp_path):
    # A destination no static read can resolve must not be attributed to a repo: a guessed
    # attribution is worse than a miss, because it is wrong with confidence.
    outer = _repo(tmp_path, "outer")
    (outer / "f.md").write_text("x")
    inner = _repo(outer, "inner")
    assert G.notice('git ls-files --error-unmatch "$FILE"', str(inner)) is None


def test_a_path_absent_everywhere_is_silent(tmp_path):
    # A typo is not this hook's business, and with no ancestor copy there is nothing to point at.
    inner = _repo(_repo(tmp_path, "outer"), "inner")
    assert G.notice("git ls-files --error-unmatch nowhere.md", str(inner)) is None


def test_a_bare_ls_files_listing_is_silent(tmp_path):
    # Without --error-unmatch, ls-files is a LISTING, not a question about one path.
    outer = _repo(tmp_path, "outer")
    (outer / "f.md").write_text("x")
    inner = _repo(outer, "inner")
    assert G.notice("git ls-files f.md", str(inner)) is None


def test_a_pathspec_on_another_verb_is_silent(tmp_path):
    # `git log -- <path>` about a DELETED file is routine and correct; only the path-status verbs
    # turn an absent path into a verdict-shaped answer.
    outer = _repo(tmp_path, "outer")
    (outer / "f.md").write_text("x")
    inner = _repo(outer, "inner")
    assert G.notice("git log --oneline -- f.md", str(inner)) is None


def test_prose_documenting_this_footgun_does_not_trip_it(tmp_path):
    # A guard that blocks writing its own documentation is the measured failure mode.
    outer = _repo(tmp_path, "outer")
    (outer / "handover.md").write_text("x")
    inner = _repo(outer, "inner")
    cmd = (
        "cat > note.md <<'EOF'\n"
        "Never run git ls-files --error-unmatch handover.md from the wrong repo.\n"
        "EOF"
    )
    assert G.notice(cmd, str(inner)) is None


def test_a_linked_worktree_is_silent(tmp_path):
    # Both false positives this hook produced were here. A linked worktree carries a `.git` FILE and
    # legitimately holds a different file set from the checkout it hangs off, so a path that is
    # absent in it and present above is its normal state, not a confused session. Measured: one such
    # session had just printed `pwd`; the other ran `ls` first and said out loud that the file lives
    # only in the shared checkout. Neither was misled.
    outer = _repo(tmp_path, "project")
    (outer / "EXECUTION-USER-REVIEW.md").write_text("x")
    wt = outer / ".claude" / "worktrees" / "docs"
    wt.mkdir(parents=True)
    (wt / ".git").write_text("gitdir: /elsewhere\n")      # a FILE: the linked-worktree marker
    assert G.notice("git ls-files --error-unmatch EXECUTION-USER-REVIEW.md", str(wt)) is None


def test_a_match_above_the_enclosing_project_is_silent(tmp_path):
    # The ceiling. With no work tree enclosing the cwd's own one there is no "project you think you
    # are in" to point at, so a same-named file further up must not be attributed to this call.
    stray = tmp_path / "unrelated"
    stray.mkdir()
    (stray / "README.md").write_text("x")
    here = _repo(stray, "here")                            # cwd's own repo; nothing above it is one
    assert G.notice("git ls-files --error-unmatch README.md", str(here)) is None


def test_missing_inputs_are_silent(tmp_path):
    assert G.notice("", str(tmp_path)) is None
    assert G.notice("git check-ignore x", "") is None
    assert G.notice(None, str(tmp_path)) is None


def _umbrella(tmp_path):
    """The measured incident's layout: handover.md in the outer project, the shell in a sub-repo."""
    outer = _repo(tmp_path, "umbrella")
    (outer / "handover.md").write_text("x")
    inner = _repo(outer, "planning")
    (inner / "local.txt").write_text("x")
    return outer, inner


# --- a heredoc BEFORE the statement must not move it ---------------------------------------------
# Offsets were read on heredoc-STRIPPED text and applied to the raw command, so a statement after a
# heredoc was sliced out of the body instead: the real nudge was lost, or a name that exists only in
# the body was reported as the path being asked about.

def test_the_nudge_survives_a_heredoc_before_it(tmp_path):
    _outer, inner = _umbrella(tmp_path)
    cmd = "cat > note.md <<'EOF'\nprose\nEOF\ngit ls-files --error-unmatch handover.md"
    msg = G.notice(cmd, str(inner))
    assert msg is not None and "'handover.md'" in msg


def test_a_name_only_the_heredoc_body_mentions_is_not_reported(tmp_path):
    _outer, inner = _umbrella(tmp_path)
    assert G.notice("git check-ignore -q local.txt", str(inner)) is None          # control
    cmd = "cat >n <<'EOF'\nxxxxxxxxxxxxxxxx handover.md\nEOF\ngit check-ignore -q local.txt"
    assert G.notice(cmd, str(inner)) is None


# --- check-attr operands -------------------------------------------------------------------------

def test_check_attr_with_a_named_attribute_skips_the_attribute(tmp_path):
    _outer, inner = _umbrella(tmp_path)
    assert G.notice("git check-attr text handover.md", str(inner)) is not None
    # `handover.md` in the ATTRIBUTE slot is an attribute name, not a path
    assert G.notice("git check-attr handover.md local.txt", str(inner)) is None


def test_check_attr_all_has_no_attribute_operand(tmp_path):
    # `-a`/`--all` replace the attribute list, so the first bare token is already a path. Skipping
    # it as an attribute made the hook permanently silent for this form.
    _outer, inner = _umbrella(tmp_path)
    assert G.notice("git check-attr -a handover.md", str(inner)) is not None
    assert G.notice("git check-attr --all handover.md", str(inner)) is not None


def test_check_attr_double_dash_separates_attributes_from_paths(tmp_path):
    _outer, inner = _umbrella(tmp_path)
    assert G.notice("git check-attr text eol -- handover.md", str(inner)) is not None
    assert G.notice("git check-attr text handover.md -- local.txt", str(inner)) is None


def test_check_attr_source_value_is_not_the_attribute(tmp_path):
    # `--source <tree-ish>` consumes its value; read as the attribute, it shifted the real
    # attribute into the path slot and fired on a name that was never a path.
    _outer, inner = _umbrella(tmp_path)
    assert G.notice("git check-attr --source HEAD handover.md local.txt", str(inner)) is None
    assert G.notice("git check-attr --source HEAD text handover.md", str(inner)) is not None


def test_an_operand_after_double_dash_is_a_path_even_with_a_leading_dash(tmp_path):
    outer, inner = _umbrella(tmp_path)
    (outer / "-odd.md").write_text("x")
    assert G.notice("git ls-files --error-unmatch -- -odd.md", str(inner)) is not None
    assert G.notice("git ls-files --error-unmatch -odd.md", str(inner)) is None     # an option


# --- a subshell is a statement boundary ----------------------------------------------------------
# Statements were cut on a regex that knows no parens, so `(git check-ignore ...)` read as the
# program `(git` - never a git verb - and `(cd X && ...)` as no cd at all.

def test_a_question_inside_a_subshell_still_fires(tmp_path):
    _outer, inner = _umbrella(tmp_path)
    assert G.notice("git check-ignore -q handover.md", str(inner)) is not None     # control
    assert G.notice("(git check-ignore -q handover.md)", str(inner)) is not None
    assert G.notice("echo start; (git ls-files --error-unmatch handover.md)", str(inner)) is not None


def test_a_cd_inside_a_subshell_states_the_subject(tmp_path):
    outer, inner = _umbrella(tmp_path)
    assert G.notice(f"(cd {_sh(outer)} && git check-ignore -q handover.md)", str(inner)) is None


def test_a_quoted_paren_label_is_not_a_subshell(tmp_path):
    _outer, inner = _umbrella(tmp_path)
    cmd = 'echo "=== (must PASS) ===" ; git check-ignore -q handover.md'
    assert G.notice(cmd, str(inner)) is not None


# --- the walks that reach the filesystem root ----------------------------------------------------

def test_no_work_tree_anywhere_is_silent(tmp_path):
    # Neither the cwd nor any ancestor is a work tree: there is no project to point at.
    plain = tmp_path / "plain"
    (plain / "sub").mkdir(parents=True)
    (plain / "f.md").write_text("x")
    assert G.notice("git ls-files --error-unmatch f.md", str(plain / "sub")) is None


# --- main(): the hook as the harness runs it -----------------------------------------------------

def _run(event, env_extra=None, cwd=None):
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
    env.update(env_extra or {})
    proc = subprocess.run([sys.executable, str(_HOOK)], input=json.dumps(event).encode("utf-8"),
                          capture_output=True, env=env, cwd=cwd, timeout=60)
    return proc.returncode, proc.stdout.decode("utf-8", "replace")


def test_main_emits_additional_context_json(tmp_path):
    _outer, inner = _umbrella(tmp_path)
    rc, out = _run({"tool_name": "Bash", "cwd": str(inner),
                    "tool_input": {"command": "git ls-files --error-unmatch handover.md"}})
    assert rc == 0
    payload = json.loads(out)["hookSpecificOutput"]
    assert payload["hookEventName"] == "PreToolUse"
    assert "PATH NOT IN THIS DIRECTORY" in payload["additionalContext"]


def test_main_is_silent_for_a_non_shell_tool(tmp_path):
    _outer, inner = _umbrella(tmp_path)
    rc, out = _run({"tool_name": "Read", "cwd": str(inner),
                    "tool_input": {"command": "git ls-files --error-unmatch handover.md"}})
    assert (rc, out) == (0, "")


def test_main_falls_back_to_the_project_dir_then_the_process_cwd(tmp_path):
    _outer, inner = _umbrella(tmp_path)
    event = {"tool_name": "Bash", "tool_input": {"command": "git check-ignore -q handover.md"}}
    rc, out = _run(event, env_extra={"CLAUDE_PROJECT_DIR": str(inner)})
    assert rc == 0 and "PATH NOT IN THIS DIRECTORY" in out
    rc, out = _run(event, cwd=str(inner))
    assert rc == 0 and "PATH NOT IN THIS DIRECTORY" in out
    rc, out = _run(event, cwd=str(tmp_path))       # the outer dir itself: nothing is missing
    assert (rc, out) == (0, "")


def test_main_fails_open_on_garbage_stdin():
    proc = subprocess.run([sys.executable, str(_HOOK)], input=b"{", capture_output=True, timeout=60)
    assert (proc.returncode, proc.stdout) == (0, b"")
