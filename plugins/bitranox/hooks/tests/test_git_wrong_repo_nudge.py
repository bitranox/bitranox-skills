"""Tests for git-wrong-repo-nudge.py - a git answer that is confidently about another repo. ASCII."""
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


def test_two_cds_in_one_call_fire_even_when_both_are_the_session_repo(tmp_path):
    # One repo per call: after the second cd, every later git answers from there.
    here = _repo(tmp_path, "here")
    (here / "a").mkdir()
    (here / "b").mkdir()
    assert G.notice(f"cd {here / 'a'} && git log && cd {here / 'b'} && git log", str(here)) is not None


def test_a_cd_inside_a_heredoc_body_is_not_a_cd(tmp_path):
    here, other = _repo(tmp_path, "here"), _repo(tmp_path, "other")
    cmd = f"cd {here} && git log && cat <<'EOF'\ncd {other} && git log\nEOF"
    assert G.notice(cmd, str(here)) is None


def test_a_cd_inside_a_quoted_string_is_not_a_cd(tmp_path):
    here, other = _repo(tmp_path, "here"), _repo(tmp_path, "other")
    assert G.notice(f"cd {here} && git log && echo 'cd {other} && git log'", str(here)) is None


def test_two_cds_name_the_directory_the_last_git_answers_from(tmp_path):
    here = _repo(tmp_path, "here")
    other = _repo(tmp_path, "other")
    msg = G.notice(f"cd {here} && git log && cd {other} && git log", str(here))
    assert msg is not None and str(other) in msg


def test_a_single_relative_cd_does_not_fire(tmp_path):
    here, other = _repo(tmp_path, "here"), _repo(tmp_path, "other")
    assert G.notice("cd ../other && git log", str(here)) is None


def test_a_missing_cwd_fails_open(tmp_path):
    assert G.notice("cd /nowhere-at-all && git log", None) is None


def test_garbage_input_fails_open():
    assert G.notice(None, "/x") is None and G.notice("", "/x") is None
