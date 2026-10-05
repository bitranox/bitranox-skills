"""Tests for git-wrong-repo-nudge.py - a git answer that is confidently about another repo. ASCII."""
import json
import os
import subprocess
import sys
from pathlib import Path

import git_wrong_repo_nudge as G


def _repo(tmp_path, name):
    """A directory that looks like a git work tree to the detector."""
    root = tmp_path / name
    (root / ".git").mkdir(parents=True)
    return root


def test_a_single_cd_into_another_repo_does_not_fire(tmp_path):
    # Measured over 60,517 real Bash commands: firing on "cd into a different work tree, then git"
    # fired 4,718 times - 7.8% of ALL commands. The dominant case is a session whose cwd is a parent
    # project working in a nested sub-repo, which is routine and correct. A nudge at that rate is
    # tuned out, so this shape is deliberately NOT guarded.
    here, other = _repo(tmp_path, "here"), _repo(tmp_path, "other")
    assert G.notice(f"cd {other} && git log --oneline -3", str(here)) is None


def test_a_cd_into_a_nested_sub_repo_does_not_fire(tmp_path):
    # The measured false-positive class itself: an inner repo below the session's own directory.
    here = _repo(tmp_path, "here")
    inner = _repo(here, "inner")
    assert G.notice(f"cd {inner} && git status --porcelain", str(here)) is None


def test_a_label_naming_another_repo_is_not_structurally_detectable(tmp_path):
    # The shape that motivated this hook: cd into one repo, echo the name of another, run git. It is
    # NOT distinguishable from the 4,718 benign commands above - the hazard is in the narrative, not
    # the structure - so the hook does not pretend to catch it. Kept as a test so nobody re-adds the
    # single-cd arm believing it covers this.
    here, other = _repo(tmp_path, "agentdag"), _repo(tmp_path, "RESEARCH")
    cmd = f"cd {other} && echo agentdag && git log --oneline -5 && git fetch origin"
    assert G.notice(cmd, str(here)) is None


def test_a_cd_within_the_same_repo_does_not_fire(tmp_path):
    here = _repo(tmp_path, "here")
    (here / "src").mkdir()
    assert G.notice(f"cd {here / 'src'} && git status", str(here)) is None


def test_the_recommended_cd_to_the_session_repo_does_not_fire(tmp_path):
    # The sibling rev-parse nudge tells you to add `cd /full/path &&`. Firing on its own advice
    # would make the two guards contradict each other.
    here = _repo(tmp_path, "here")
    assert G.notice(f"cd {here} && git rev-parse --verify -q HEAD", str(here)) is None


def test_git_with_no_cd_at_all_does_not_fire(tmp_path):
    here = _repo(tmp_path, "here")
    assert G.notice("git status --porcelain", str(here)) is None


def test_a_cd_with_no_git_does_not_fire(tmp_path):
    here, other = _repo(tmp_path, "here"), _repo(tmp_path, "other")
    assert G.notice(f"cd {other} && ls -la", str(here)) is None


def test_git_before_the_cd_does_not_fire(tmp_path):
    # A cd persists FORWARD, so a git that runs first is still answering from the session repo.
    here, other = _repo(tmp_path, "here"), _repo(tmp_path, "other")
    assert G.notice(f"git status && cd {other}", str(here)) is None


def test_two_cds_into_DIFFERENT_repos_fire(tmp_path):
    here, one, two = _repo(tmp_path, "here"), _repo(tmp_path, "one"), _repo(tmp_path, "two")
    assert G.notice(f"cd {one} && git log && cd {two} && git log", str(here)) is not None


def test_two_cds_inside_ONE_repo_do_not_fire(tmp_path):
    # Measured: 131 of 344 firings had every cd landing in the same work tree, where both gits
    # answer about the same repository and there is no wrong-repo hazard to warn about.
    here = _repo(tmp_path, "here")
    (here / "a").mkdir()
    (here / "b").mkdir()
    assert G.notice(f"cd {here / 'a'} && git log && cd {here / 'b'} && git log", str(here)) is None


def test_a_cd_to_a_shell_VARIABLE_does_not_fire(tmp_path):
    # Measured: 1,233 cd targets in the corpus are variables. The destination is not knowable
    # statically, so resolving the literal text produces a nonsense path and any verdict built on
    # it is invented. Silence is the only honest answer.
    here, other = _repo(tmp_path, "here"), _repo(tmp_path, "other")
    assert G.notice(f'cd {other} && git log && cd "$dir" && git log', str(here)) is None
    assert G.notice("cd $ONE && git log && cd $TWO && git log", str(here)) is None


def test_a_cd_to_a_directory_that_does_not_exist_does_not_fire(tmp_path):
    # A path that is not there cannot be attributed to a repo, so the comparison is unknowable.
    here, other = _repo(tmp_path, "here"), _repo(tmp_path, "other")
    assert G.notice(f"cd {other} && git log && cd {tmp_path / 'gone'} && git log", str(here)) is None


def test_a_cd_inside_a_heredoc_body_is_not_a_cd(tmp_path):
    here, other = _repo(tmp_path, "here"), _repo(tmp_path, "other")
    cmd = f"cd {here} && git log && cat <<'EOF'\ncd {other} && git log\nEOF"
    assert G.notice(cmd, str(here)) is None


def test_a_cd_inside_a_quoted_string_is_not_a_cd(tmp_path):
    here, other = _repo(tmp_path, "here"), _repo(tmp_path, "other")
    assert G.notice(f"cd {here} && git log && echo 'cd {other} && git log'", str(here)) is None


def test_the_notice_names_the_directory_the_last_git_answers_from(tmp_path):
    here, other = _repo(tmp_path, "here"), _repo(tmp_path, "other")
    msg = G.notice(f"cd {here} && git log && cd {other} && git log", str(here))
    assert msg is not None and str(other) in msg


def test_a_single_relative_cd_does_not_fire(tmp_path):
    here, other = _repo(tmp_path, "here"), _repo(tmp_path, "other")
    assert G.notice("cd ../other && git log", str(here)) is None


def test_a_missing_cwd_fails_open(tmp_path):
    assert G.notice("cd /nowhere-at-all && git log", None) is None


def test_garbage_input_fails_open():
    assert G.notice(None, "/x") is None and G.notice("", "/x") is None


# --- a heredoc BEFORE the cds must not move them -----------------------------------------------
# Statement offsets used to be read on heredoc-STRIPPED text and then used to slice the RAW
# command. Stripping deletes the body lines, so every statement after a heredoc was sliced from the
# wrong place: usually the guard went blind, and when a body happened to line up with the real
# tail it fired on a directory only the heredoc DATA named.

def test_two_repos_after_a_heredoc_still_fire(tmp_path):
    here, one, two = _repo(tmp_path, "here"), _repo(tmp_path, "one"), _repo(tmp_path, "two")
    cmd = f"cat <<'EOF' > n.txt\nnote\nline2\nEOF\ncd {one} && git log && cd {two} && git log"
    msg = G.notice(cmd, str(here))
    assert msg is not None and str(two) in msg


def test_a_heredoc_body_aligned_with_the_tail_is_not_read_as_the_tail(tmp_path):
    # The body names two repos; the real tail enters ONE repo twice. Same-length names make the
    # stripped-text offsets of the tail land exactly on the body in the raw command.
    here, aaa, bbb, ccc = (_repo(tmp_path, n) for n in ("here", "aaa", "bbb", "ccc"))
    body = f"cd {aaa} && git log && cd {bbb} && git log"
    tail = f"cd {ccc} && git log && cd {ccc} && git log"
    assert G.notice(tail, str(here)) is None                      # control: the tail alone
    assert G.notice(f"cat <<'EOF' > n.txt\n{body}\nEOF\n{tail}", str(here)) is None


def test_a_heredoc_after_the_cds_does_not_hide_them(tmp_path):
    here, one, two = _repo(tmp_path, "here"), _repo(tmp_path, "one"), _repo(tmp_path, "two")
    cmd = f"cd {one} && git log && cd {two} && git log\ncat <<'EOF' > n.txt\nx\nEOF"
    assert G.notice(cmd, str(here)) is not None


# --- destinations the hook cannot read -----------------------------------------------------------

def test_cd_dash_is_unknowable_not_a_directory_named_dash(tmp_path):
    # `cd -` goes back to $OLDPWD, which this hook does not track; it used to resolve to
    # "<previous>/-" and attribute that to the previous directory's repo.
    # Here `cd -` returns to `two`, so both gits answer about `two`; reading it as "<one>/-" put
    # the second git in `one` and fired on a single-repository call.
    here, one, two = _repo(tmp_path, "here"), _repo(tmp_path, "one"), _repo(tmp_path, "two")
    assert G.notice(f"cd {two} && git log && cd {one} && cd - && git log", str(here)) is None


def test_a_bare_cd_is_a_directory_change_with_an_unknowable_target(tmp_path):
    # A bare `cd` goes to $HOME. It used to be no cd at all, so the landing before it was still
    # treated as the directory the next git answered from.
    here, one, two = _repo(tmp_path, "here"), _repo(tmp_path, "one"), _repo(tmp_path, "two")
    assert G.notice(f"cd {one} && git log && cd && git log && cd {two} && git log",
                    str(here)) is None
    assert G.notice(f"cd {one} && git log && cd; git log", str(here)) is None


def test_cd_tilde_is_unknowable(tmp_path, monkeypatch):
    # Tilde expands against the HOME of the shell that runs the command, which this hook only
    # guesses at. HOME is pointed at a real work tree so a guess would visibly fire.
    here, one, two = _repo(tmp_path, "here"), _repo(tmp_path, "one"), _repo(tmp_path, "two")
    (two / "x").mkdir()
    monkeypatch.setenv("HOME", str(two))
    assert G.notice(f"cd {one} && git log && cd ~ && git log", str(here)) is None
    assert G.notice(f"cd {one} && git log && cd ~/x && git log", str(here)) is None


def test_two_readable_cds_still_fire_as_the_control_for_the_unknowable_ones(tmp_path):
    here, one = _repo(tmp_path, "here"), _repo(tmp_path, "one")
    (one / "sub").mkdir()
    assert G.notice(f"cd {one / 'sub'} && git log && cd {here} && git log", str(here)) is not None


# --- the gits must actually follow two different landings ----------------------------------------

def test_two_cds_but_only_ONE_git_does_not_fire(tmp_path):
    # Both cds run before the only git, so exactly one answer exists and it has one subject. The
    # message talks about two answers from two repositories, which would be false here.
    here, one, two = _repo(tmp_path, "here"), _repo(tmp_path, "one"), _repo(tmp_path, "two")
    assert G.notice(f"cd {one} && cd {two} && git log", str(here)) is None
    assert G.notice(f"cd {one} && cd {two} && git log && git status", str(here)) is None


def test_a_git_after_each_of_two_different_landings_fires(tmp_path):
    here, one, two = _repo(tmp_path, "here"), _repo(tmp_path, "one"), _repo(tmp_path, "two")
    assert G.notice(f"cd {one} && git log && cd {here} && cd {two} && git log",
                    str(here)) is not None


# --- main(): the hook as the harness runs it -----------------------------------------------------

_HOOK = Path(__file__).resolve().parent.parent / "git-wrong-repo-nudge.py"


def _run(event, env_extra=None, cwd=None):
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
    env.update(env_extra or {})
    proc = subprocess.run([sys.executable, str(_HOOK)], input=json.dumps(event).encode("utf-8"),
                          capture_output=True, env=env, cwd=cwd, timeout=60)
    return proc.returncode, proc.stdout.decode("utf-8", "replace")


def test_main_emits_additional_context_json_for_two_repos(tmp_path):
    here, one, two = _repo(tmp_path, "here"), _repo(tmp_path, "one"), _repo(tmp_path, "two")
    rc, out = _run({"tool_name": "Bash", "cwd": str(here),
                    "tool_input": {"command": f"cd {one} && git log && cd {two} && git log"}})
    assert rc == 0
    payload = json.loads(out)["hookSpecificOutput"]
    assert payload["hookEventName"] == "PreToolUse"
    assert "TWO DIRECTORY CHANGES" in payload["additionalContext"]


def test_main_is_silent_for_a_non_shell_tool(tmp_path):
    here, one, two = _repo(tmp_path, "here"), _repo(tmp_path, "one"), _repo(tmp_path, "two")
    rc, out = _run({"tool_name": "Read", "cwd": str(here),
                    "tool_input": {"command": f"cd {one} && git log && cd {two} && git log"}})
    assert (rc, out) == (0, "")


def test_main_falls_back_to_the_project_dir_when_the_event_has_no_cwd(tmp_path):
    # Relative cds are resolved against the fallback, so the fallback is what decides the verdict.
    _repo(tmp_path, "here")
    _repo(tmp_path / "here", "one")
    _repo(tmp_path / "here", "two")
    event = {"tool_name": "Bash", "tool_input": {"command": "cd one && git log && cd ../two && git log"}}
    rc, out = _run(event, env_extra={"CLAUDE_PROJECT_DIR": str(tmp_path / "here")})
    assert rc == 0 and "TWO DIRECTORY CHANGES" in out
    rc, out = _run(event, cwd=str(tmp_path))       # no project dir: the process cwd, where
    assert (rc, out) == (0, "")                   # neither `one` nor `../two` exists


def test_main_fails_open_on_garbage_stdin():
    proc = subprocess.run([sys.executable, str(_HOOK)], input=b"not json", capture_output=True,
                          timeout=60)
    assert (proc.returncode, proc.stdout) == (0, b"")


def test_a_cd_with_a_trailing_redirect_is_still_a_cd(tmp_path):
    # Control for the bare-cd reading: `cd <dir> 2>/dev/null` is a cd to <dir>, not a bare cd.
    here, one, two = _repo(tmp_path, "here"), _repo(tmp_path, "one"), _repo(tmp_path, "two")
    cmd = f"cd {one} 2>/dev/null && git log && cd {two} 2>/dev/null && git log"
    assert G.notice(cmd, str(here)) is not None


def test_cd_options_are_not_the_destination(tmp_path):
    # `cd -P <dir>` used to take `-P` as the target, resolve "<previous>/-P" and attribute it to the
    # previous landing's repo, so two different repos read as one and the call went unflagged.
    here, one, two = _repo(tmp_path, "here"), _repo(tmp_path, "one"), _repo(tmp_path, "two")
    assert G.notice(f"cd {one} && git log && cd -P {two} && git log", str(here)) is not None
    assert G.notice(f"cd {one} && git log && cd -- {two} && git log", str(here)) is not None
    assert G.notice(f"cd {one} && git log && cd -L && git log", str(here)) is None      # no operand


def test_a_quoted_destination_with_a_space_is_one_destination(tmp_path):
    here, one, two = _repo(tmp_path, "here"), _repo(tmp_path, "one"), _repo(tmp_path, "t w o")
    assert G.notice(f'cd {one} && git log && cd "{two}" && git log', str(here)) is not None
    assert G.notice(f'cd {one} && git log && cd -P "{two}" && git log', str(here)) is not None


# --- subshells: a statement boundary, and a cd that does not outlive its parens --------------------

def test_two_subshells_into_different_repos_fire(tmp_path):
    # A regex that knows no parens read `(cd X` as a program named `(cd`, so neither cd counted.
    here, one, two = _repo(tmp_path, "here"), _repo(tmp_path, "one"), _repo(tmp_path, "two")
    assert G.notice(f"cd {one} && git log ; cd {two} && git log", str(here)) is not None  # control
    assert G.notice(f"(cd {one} && git log) ; (cd {two} && git log)", str(here)) is not None
    assert G.notice(f"(cd {one}; git log); (cd {two}; git log)", str(here)) is not None


def test_a_cd_inside_a_subshell_ends_with_it(tmp_path):
    # Relative cds in sibling subshells both start from the call's own directory. Read flat, the
    # second resolved under the first (one/two, absent) and fell back to repo `one`, so two repos
    # read as one.
    base = tmp_path / "base"
    _repo(base, "one"), _repo(base, "two")
    assert G.notice("(cd one && git log) ; (cd two && git log)", str(base)) is not None
    assert G.notice("cd one && git log ; cd two && git log", str(base)) is None   # flat: one/two


def test_a_git_after_the_subshell_answers_from_the_calls_own_repo(tmp_path):
    here, one = _repo(tmp_path, "here"), _repo(tmp_path, "one")
    assert G.notice(f"(cd {one} && git log) ; git log", str(here)) is not None
    assert G.notice(f"(cd {here} && git log) ; git log", str(here)) is None       # one repo twice
