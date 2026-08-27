"""Tests for git-path-not-here-nudge.py - a path-status answer about a path that is not here. ASCII."""
import git_path_not_here_nudge as G


def _repo(tmp_path, name):
    """A directory that looks like a git work tree to the detector."""
    root = tmp_path / name
    (root / ".git").mkdir(parents=True)
    return root


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
    assert G.notice(f"cd {outer} && git ls-files --error-unmatch f.md", str(inner)) is None


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


def test_missing_inputs_are_silent(tmp_path):
    assert G.notice("", str(tmp_path)) is None
    assert G.notice("git check-ignore x", "") is None
    assert G.notice(None, str(tmp_path)) is None
