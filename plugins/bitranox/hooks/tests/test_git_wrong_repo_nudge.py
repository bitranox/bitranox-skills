"""Tests for git-wrong-repo-nudge.py - a git answer that is confidently about another repo. ASCII."""
import git_wrong_repo_nudge as G


def _repo(tmp_path, name):
    """A directory that looks like a git work tree to the detector."""
    root = tmp_path / name
    (root / ".git").mkdir(parents=True)
    return root


def test_git_after_a_cd_into_another_repo_fires(tmp_path):
    here, other = _repo(tmp_path, "here"), _repo(tmp_path, "other")
    assert G.notice(f"cd {other} && git log --oneline -3", str(here)) is not None


def test_the_notice_names_the_directory_the_git_actually_answers_from(tmp_path):
    here, other = _repo(tmp_path, "here"), _repo(tmp_path, "other")
    msg = G.notice(f"cd {other} && git log", str(here))
    assert str(other) in msg


def test_the_measured_shape_a_label_naming_a_different_repo(tmp_path):
    # cd into one repo, echo the name of another, then run git: the output reads as the echoed one.
    here, other = _repo(tmp_path, "agentdag"), _repo(tmp_path, "RESEARCH")
    cmd = f"cd {other} && echo agentdag && git log --oneline -5 && git fetch origin"
    assert G.notice(cmd, str(here)) is not None


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
    cmd = f"cat <<'EOF'\ncd {other} && git log\nEOF"
    assert G.notice(cmd, str(here)) is None


def test_a_cd_inside_a_quoted_string_is_not_a_cd(tmp_path):
    here, other = _repo(tmp_path, "here"), _repo(tmp_path, "other")
    assert G.notice(f"echo 'cd {other} && git log'", str(here)) is None


def test_a_relative_cd_into_a_sibling_repo_fires(tmp_path):
    here, other = _repo(tmp_path, "here"), _repo(tmp_path, "other")
    assert G.notice("cd ../other && git log", str(here)) is not None


def test_a_missing_cwd_fails_open(tmp_path):
    assert G.notice("cd /nowhere-at-all && git log", None) is None


def test_garbage_input_fails_open():
    assert G.notice(None, "/x") is None and G.notice("", "/x") is None
