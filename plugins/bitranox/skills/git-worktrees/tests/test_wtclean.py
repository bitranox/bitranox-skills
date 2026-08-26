"""Tests for wtclean.py - remove a worktree AND the build caches it leaves behind. ASCII only.

This tool calls shutil.rmtree on other people's machines, so every refusal below is asserted by
watching it actually refuse: a guard nobody has seen fire is not a guard.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import wtclean as W

GIT = shutil.which("git")
needs_git = pytest.mark.skipif(GIT is None, reason="git is not installed")
needs_symlinks = pytest.mark.skipif(
    not hasattr(os, "symlink"), reason="platform cannot create symlinks"
)

CLI = str(Path(__file__).resolve().parent.parent / "scripts" / "wtclean.py")
CLI_TIMEOUT = 60


def run_cli(*args, cwd=None, home=None):
    """Spawn the CLI the way a caller would, with an explicit timeout and encoding.

    sys.executable, never a bare "python3": the name does not resolve on every platform. An
    explicit encoding, because without one the capture decodes with the machine's locale codec
    and fails differently per platform (stdout can come back None on Windows).

    `cwd` and `home` are here because the tool resolves a bare name against both, and a test that
    let either default would be reading the machine the suite happens to run on. HOME and
    USERPROFILE are both set: Path.home() reads the first on POSIX and the second on Windows.
    """
    env = None
    if home is not None:
        env = {**os.environ, "HOME": str(home), "USERPROFILE": str(home)}
    return subprocess.run(
        [sys.executable, CLI, *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=CLI_TIMEOUT,
        check=False,
        cwd=None if cwd is None else str(cwd),
        env=env,
    )


def make_cache(base: Path, name: str, payload: bytes = b"0" * 4096) -> Path:
    directory = base / name
    directory.mkdir(parents=True)
    (directory / "blob").write_bytes(payload)
    return directory


def make_repo_with_worktree(root: Path, topic: str = "topic", worktree_path: Path | None = None):
    """A real git repo plus a real linked worktree - the thing the tool actually operates on."""
    main = root / "main"
    main.mkdir()
    env = {**os.environ, "GIT_CONFIG_GLOBAL": str(root / "gitconfig"), "GIT_CONFIG_SYSTEM": os.devnull}

    def git(*args, cwd=main):
        return subprocess.run(
            [GIT, *args],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=CLI_TIMEOUT,
            check=True,
            env=env,
        )

    git("init", "-q", "-b", "main")
    git("-c", "user.email=t@example.invalid", "-c", "user.name=t", "commit", "-q",
        "--allow-empty", "-m", "init")
    worktree = worktree_path if worktree_path is not None else root / f"wt-{topic}"
    git("worktree", "add", "-q", str(worktree), "-b", topic)
    return main, worktree, git


# ---------------------------------------------------------------------------------------------
# Name safety: every escape shape must be SEEN to refuse
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    [
        "..",
        "../..",
        "../../etc",
        "/absolute",
        "/",
        "a/b",
        "a\\b",
        "C:\\Windows",
        "C:topic",
        "",
        ".",
        "~",
    ],
)
def test_an_escaping_topic_name_is_refused_outright(value):
    """The name is pasted into a delete path, so a path shape is refused, never normalised."""
    assert W.unsafe_topic_reason(value) is not None, f"{value!r} was accepted as a bare name"
    assert W.cache_dirs(value, base="/anywhere") == []


@pytest.mark.parametrize("value", ["topic", "wt-topic", "my-feature", "feature_42", "a.b"])
def test_an_ordinary_topic_name_is_accepted(value):
    """The negative control: a guard that refuses everything would pass the tests above vacuously."""
    assert W.unsafe_topic_reason(value) is None
    assert W.cache_dirs(value, base="/anywhere") != []


def test_a_windows_shaped_escape_is_refused_on_every_platform():
    """Windows path rules are applied on Linux too, so a drive-relative form cannot slip past.

    PurePosixPath treats "C:topic" and "a\\b" as ordinary one-part names; only the Windows
    flavour sees the drive and the separator. Checking both is what makes the guard portable.
    """
    from pathlib import PurePosixPath

    assert PurePosixPath("C:topic").name == "C:topic"  # the platform-native check would pass it
    assert W.unsafe_topic_reason("C:topic") is not None  # the union check does not
    assert W.unsafe_topic_reason("a\\b") is not None


@pytest.mark.parametrize(
    "argument", ["..", "../..", "../../etc", "wt-a/../../etc", ".", "~", "a\\..\\..\\etc"]
)
def test_the_cli_refuses_a_traversal_instead_of_normalising_it(argument, tmp_path):
    """The regression this pins: taking the basename FIRST turns `../../etc` into the bare,
    apparently-safe topic `etc`, so a guard applied only to the derived name accepts the very
    shape the tool promises to refuse. The argument is checked before the topic is derived.
    """
    result = run_cli(argument, "--base", str(tmp_path), "--apply")
    assert result.returncode == 2, f"{argument!r} was not refused: {result.stdout}{result.stderr}"
    assert "refusing" in result.stderr
    assert result.stdout == ""


@pytest.mark.parametrize("argument", ["topic", "wt-topic"])
def test_the_cli_accepts_an_ordinary_argument(argument, tmp_path):
    """The control: a refusal that fires on everything would pass the test above vacuously."""
    result = run_cli(argument, "--base", str(tmp_path), "--skip-worktree")
    assert result.returncode == 0, result.stderr


def test_an_absolute_worktree_path_is_still_usable(tmp_path):
    """Refusing parent references must not also refuse naming a worktree outright."""
    assert W.unsafe_argument_reason(str(tmp_path / "wt-topic")) is None
    assert W.unsafe_argument_reason(".worktrees/my-feature") is None


# ---------------------------------------------------------------------------------------------
# Deriving names and cache paths
# ---------------------------------------------------------------------------------------------


def test_a_topic_is_taken_from_a_worktree_path_too():
    assert W.topic_name("/home/user/wt-nested-relay") == "nested-relay"
    assert W.topic_name("wt-nested-relay") == "nested-relay"
    assert W.topic_name("nested-relay") == "nested-relay"
    assert W.topic_name("/home/user/wt-nested-relay/") == "nested-relay"


def test_a_bare_name_is_not_read_as_a_relative_path():
    """`wt-foo` must resolve against --base, not against whatever directory the tool runs from."""
    assert not W.looks_like_a_path("wt-foo")
    assert W.looks_like_a_path(".worktrees/wt-foo")
    assert W.looks_like_a_path("~/wt-foo")


def test_the_cache_dirs_are_derived_from_the_worktree_name():
    """`git worktree remove` does not touch these - they are what piles up invisibly."""
    targets = [str(p) for p in W.cache_dirs("mytopic", base="/base")]
    assert str(Path("/base/wt-mytopic-target")) in targets
    assert str(Path("/base/wt-mytopic-clippy")) in targets


def test_the_layout_is_configurable_rather_than_baked_in():
    """The default prefix and suffixes are one project's convention, not a universal truth."""
    targets = [str(p) for p in W.cache_dirs("t", base="/b", prefix="feat/", suffixes=("build",))]
    assert targets == [str(Path("/b/feat/t-build"))]


# ---------------------------------------------------------------------------------------------
# The plan
# ---------------------------------------------------------------------------------------------


def test_plan_lists_only_what_actually_exists(tmp_path):
    """A plan naming absent paths reads as work to do and hides the real ones."""
    make_cache(tmp_path, "wt-topic-target")
    plan = W.build_plan("topic", base=tmp_path, status_probe=lambda _p: W.STATUS_CLEAN)
    paths = [str(t.path) for t in plan.caches]
    assert str(tmp_path / "wt-topic-target") in paths
    assert str(tmp_path / "wt-topic-clippy") not in paths


def test_plan_reports_sizes_so_the_reclaim_is_visible(tmp_path):
    make_cache(tmp_path, "wt-topic-target", b"0" * 4096)
    plan = W.build_plan("topic", base=tmp_path, status_probe=lambda _p: W.STATUS_CLEAN)
    assert plan.caches[0].size_bytes >= 4096
    assert plan.total_bytes >= 4096


def test_an_explicit_cache_dir_covers_a_layout_the_convention_misses(tmp_path):
    """A user whose caches live elsewhere must be able to name them, not be told there are none."""
    elsewhere = make_cache(tmp_path, "somewhere/else/mytopic-build")
    plan = W.build_plan(
        "topic", base=tmp_path, explicit_caches=[elsewhere],
        status_probe=lambda _p: W.STATUS_CLEAN,
    )
    assert [str(t.path) for t in plan.caches] == [str(elsewhere)]


def test_the_run_says_which_paths_it_checked_when_the_convention_matches_nothing(tmp_path):
    """Silence here would read as 'you have no caches' on a layout that simply differs."""
    result = run_cli("topic", "--base", str(tmp_path))
    assert "no cache directory matched the convention" in result.stderr
    assert str(tmp_path) in result.stderr
    assert "--cache-dir" in result.stderr


# ---------------------------------------------------------------------------------------------
# Symlinks
# ---------------------------------------------------------------------------------------------


@needs_symlinks
def test_a_symlinked_cache_target_is_refused_and_its_target_survives(tmp_path):
    """rmtree through a link can destroy data outside the directory that was named."""
    outside = tmp_path / "precious"
    outside.mkdir()
    (outside / "data.txt").write_text("keep me", encoding="utf-8")
    (tmp_path / "wt-topic-target").symlink_to(outside, target_is_directory=True)

    plan = W.build_plan("topic", base=tmp_path, status_probe=lambda _p: W.STATUS_ABSENT)
    assert plan.caches[0].refusal is not None
    assert "symlink" in plan.caches[0].refusal

    failures = W.apply_plan(plan, remove_worktree=False)
    assert failures and "symlink" in str(failures[0])
    assert (outside / "data.txt").read_text(encoding="utf-8") == "keep me"
    assert (tmp_path / "wt-topic-target").is_symlink(), "the link itself must be left alone too"


@needs_symlinks
def test_a_symlink_inside_the_tree_is_unlinked_not_followed(tmp_path):
    """Measured behaviour of shutil.rmtree, pinned: the link goes, what it points at does not."""
    outside = tmp_path / "precious"
    outside.mkdir()
    (outside / "data.txt").write_text("keep me", encoding="utf-8")
    cache = make_cache(tmp_path, "wt-topic-target")
    (cache / "inner").symlink_to(outside, target_is_directory=True)

    plan = W.build_plan("topic", base=tmp_path, status_probe=lambda _p: W.STATUS_ABSENT)
    assert W.apply_plan(plan, remove_worktree=False) == []
    assert not cache.exists()
    assert (outside / "data.txt").read_text(encoding="utf-8") == "keep me"


@needs_symlinks
def test_a_symlinked_worktree_is_refused_and_no_flag_overrides_it(tmp_path):
    """--discard-uncommitted overrides a dirty checkout, never a link pointing somewhere else."""
    real = tmp_path / "real-checkout"
    real.mkdir()
    (tmp_path / "wt-topic").symlink_to(real, target_is_directory=True)
    plan = W.build_plan("topic", base=tmp_path)
    assert plan.worktree_refusal is not None
    assert W.worktree_refusal(plan, discard_uncommitted=True) is not None
    assert real.exists()


def test_a_cache_resolving_outside_the_base_is_refused(tmp_path):
    """The backstop for a reparse point or bind mount, which is not reported as a symlink."""
    outside = tmp_path / "outside"
    outside.mkdir()
    base = tmp_path / "base"
    base.mkdir()
    assert W.refusal_for(outside, base=base) is not None
    assert W.refusal_for(base, base=base) is not None
    assert W.refusal_for(Path(tmp_path.anchor), base=None) is not None
    assert W.refusal_for(base / "wt-t-target", base=base) is None


# ---------------------------------------------------------------------------------------------
# Dry run is the default
# ---------------------------------------------------------------------------------------------


def test_nothing_is_removed_without_apply(tmp_path):
    """Default must be safe: this deletes directories and there is no undo."""
    cache = make_cache(tmp_path, "wt-topic-target")
    checkout = tmp_path / "wt-topic"
    checkout.mkdir()
    assert W.main(["topic", "--base", str(tmp_path)]) in (0, 1)
    assert cache.exists(), "a dry run must not delete anything"
    assert checkout.exists(), "a dry run must not remove the worktree either"


def test_the_dry_run_prints_what_would_go_with_its_size(tmp_path):
    make_cache(tmp_path, "wt-topic-target", b"0" * 2048)
    result = run_cli("topic", "--base", str(tmp_path))
    assert "would remove" in result.stdout
    assert str(tmp_path / "wt-topic-target") in result.stdout
    assert "--apply" in result.stdout


# ---------------------------------------------------------------------------------------------
# Plan equals apply
# ---------------------------------------------------------------------------------------------


def test_apply_removes_exactly_what_the_plan_listed_and_nothing_else(tmp_path):
    """No re-scan at apply time: a plan/apply mismatch is how a delete tool surprises someone."""
    planned = make_cache(tmp_path, "wt-topic-target")
    bystander = make_cache(tmp_path, "wt-other-target")
    plan = W.build_plan("topic", base=tmp_path, status_probe=lambda _p: W.STATUS_ABSENT)
    planned_paths = {str(t.path) for t in plan.caches}

    # created AFTER the plan was shown - it was never approved, so it must survive
    late = make_cache(tmp_path, "wt-topic-clippy")

    assert W.apply_plan(plan, remove_worktree=False) == []
    survivors = {p.name for p in tmp_path.iterdir()}
    assert planned_paths == {str(planned)}
    assert not planned.exists()
    assert late.exists(), "apply re-scanned instead of using the plan it showed"
    assert bystander.exists()
    assert survivors == {"wt-other-target", "wt-topic-clippy"}


def test_a_cache_that_vanished_between_plan_and_apply_is_reported_not_hidden(tmp_path):
    cache = make_cache(tmp_path, "wt-topic-target")
    plan = W.build_plan("topic", base=tmp_path, status_probe=lambda _p: W.STATUS_ABSENT)
    shutil.rmtree(cache)
    failures = W.apply_plan(plan, remove_worktree=False)
    assert len(failures) == 1 and failures[0].path == str(cache)


def test_an_applied_run_never_claims_it_removed_something_it_refused(tmp_path):
    """The regression this pins: the report listed the worktree as "removed" while refusing it.

    A delete tool whose output disagrees with what it did is the same failure as a plan that
    disagrees with the apply - the person reads the transcript, not the filesystem.
    """
    make_cache(tmp_path, "wt-topic-target")
    checkout = tmp_path / "wt-topic"
    checkout.mkdir()
    result = run_cli("topic", "--base", str(tmp_path), "--apply")
    assert result.returncode == 1, result.stdout
    assert checkout.exists(), "the dirty/unreadable worktree must survive"
    # Anchored on the rendered marker, not a bare substring: `wt-topic` is a PREFIX of
    # `wt-topic-target`, so a substring test here matches the cache line and never fails.
    assert f"{checkout}  (worktree" not in result.stdout, result.stdout
    assert str(checkout) in result.stderr
    assert not (tmp_path / "wt-topic-target").exists(), "the unblocked cache still goes"


def test_the_dry_run_reports_exactly_the_refusals_apply_will_hit(tmp_path):
    """One function answers this for both, so a dry run cannot promise what apply then refuses."""
    make_cache(tmp_path, "wt-topic-target")
    (tmp_path / "wt-topic").mkdir()
    plan = W.build_plan("topic", base=tmp_path, status_probe=lambda _p: W.STATUS_DIRTY)
    predicted = W.blocked_reasons(plan)
    actual = W.apply_plan(plan, git_remove=lambda *_a, **_k: pytest.fail("git must not be called"))
    assert predicted == actual
    assert (tmp_path / "wt-topic").exists()


# ---------------------------------------------------------------------------------------------
# Uncommitted work
# ---------------------------------------------------------------------------------------------


def test_a_dirty_worktree_is_refused_by_default(tmp_path):
    """Losing a person's uncommitted work is the worst outcome this tool can produce."""
    (tmp_path / "wt-topic").mkdir()
    plan = W.build_plan("topic", base=tmp_path, status_probe=lambda _p: W.STATUS_DIRTY)
    reason = W.worktree_refusal(plan)
    assert reason is not None and "uncommitted" in reason
    assert "--discard-uncommitted" in reason


def test_an_unreadable_worktree_state_is_treated_like_a_dirty_one(tmp_path):
    """'I could not check' must never be the permissive answer for a delete."""
    (tmp_path / "wt-topic").mkdir()
    plan = W.build_plan("topic", base=tmp_path, status_probe=lambda _p: W.STATUS_UNKNOWN)
    assert W.worktree_refusal(plan) is not None


def test_discard_uncommitted_is_required_before_git_is_asked_to_force(tmp_path):
    """--force is only ever forwarded on an explicit opt-in; it DISCARDS the work."""
    (tmp_path / "wt-topic").mkdir()
    plan = W.build_plan("topic", base=tmp_path, status_probe=lambda _p: W.STATUS_DIRTY)
    calls = []

    def fake_remove(path, *, force=False, **_kw):
        calls.append(force)
        return None

    assert W.apply_plan(plan, git_remove=fake_remove) != []
    assert calls == [], "git was called for a dirty worktree without the opt-in"

    assert W.apply_plan(plan, discard_uncommitted=True, git_remove=fake_remove) == []
    assert calls == [True]


def test_a_clean_worktree_is_removed_without_force(tmp_path):
    (tmp_path / "wt-topic").mkdir()
    plan = W.build_plan("topic", base=tmp_path, status_probe=lambda _p: W.STATUS_CLEAN)
    calls = []
    assert W.apply_plan(plan, git_remove=lambda p, *, force=False, **_k: calls.append(force)) == []
    assert calls == [False]


# ---------------------------------------------------------------------------------------------
# Real git
# ---------------------------------------------------------------------------------------------


@needs_git
def test_a_real_clean_worktree_reads_clean_and_a_dirty_one_reads_dirty(tmp_path):
    _main, worktree, _git = make_repo_with_worktree(tmp_path)
    assert W.git_worktree_status(worktree) == W.STATUS_CLEAN
    (worktree / "scratch.txt").write_text("untracked work", encoding="utf-8")
    assert W.git_worktree_status(worktree) == W.STATUS_DIRTY


@needs_git
def test_a_directory_that_is_not_a_worktree_reads_unknown(tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()
    assert W.git_worktree_status(plain) == W.STATUS_UNKNOWN


@needs_git
def test_a_real_worktree_is_removed_end_to_end(tmp_path):
    # Was skipped on Windows as an open-handle quirk of the platform. That diagnosis was wrong:
    # git removes a worktree there without complaint, and the permission error came from
    # git_worktree_remove running git with -C pointing INTO the directory being deleted, which
    # Windows locks. The skip was hiding a defect in shipped code, so it is gone.
    _main, worktree, _git = make_repo_with_worktree(tmp_path)
    cache = make_cache(tmp_path, "wt-topic-target")
    plan = W.build_plan("topic", base=tmp_path, worktree=worktree)
    assert plan.worktree_status == W.STATUS_CLEAN
    assert W.apply_plan(plan) == []
    assert not worktree.exists()
    assert not cache.exists()


@needs_git
def test_the_run_dir_is_the_main_checkout_and_carries_no_warning(tmp_path):
    """The whole point of the helper: git must not run from the directory being deleted, which
    Windows locks. A resolvable worktree returns the MAIN checkout and warns about nothing."""
    main, worktree, _git = make_repo_with_worktree(tmp_path)
    run_dir, warning = W._git_run_dir(worktree, 30)
    assert warning is None
    assert run_dir.resolve() == main.resolve()
    assert run_dir.resolve() != worktree.resolve()


def test_an_unresolvable_run_dir_falls_back_but_says_so(tmp_path):
    """The fallback keeps working where it always worked (POSIX), but must never be silent: on
    Windows it is exactly the bug this helper exists to avoid, and a check that quietly reverts
    to broken while still reading as working is the failure mode the whole change was about."""
    plain = tmp_path / "not-a-repo"
    plain.mkdir()
    run_dir, warning = W._git_run_dir(plain, 30)
    assert run_dir == plain
    assert warning and "main checkout" in warning


@needs_git
def test_a_removal_failure_names_the_degraded_run_dir(tmp_path):
    """The warning has to reach the caller, or reporting it changes nothing. It is attached on
    the FAILURE path only, where it separates "git refused" from "we asked git to delete the
    directory it was standing in"."""
    plain = tmp_path / "not-a-repo"
    plain.mkdir()
    error = W.git_worktree_remove(plain, force=False)
    assert error is not None
    assert "git ran from the worktree itself" in error


@needs_git
def test_a_successful_removal_carries_no_warning_text(tmp_path):
    """The direction it must NOT fire: a clean removal returns None, not a warning-decorated
    success."""
    _main, worktree, _git = make_repo_with_worktree(tmp_path, topic="quiet")
    assert W.git_worktree_remove(worktree, force=True) is None


@needs_git
def test_git_refuses_a_dirty_worktree_even_when_our_own_check_is_bypassed(tmp_path):
    """Defense in depth: git's own refusal is the second layer, keyed on the exit code."""
    _main, worktree, _git = make_repo_with_worktree(tmp_path)
    (worktree / "scratch.txt").write_text("work", encoding="utf-8")
    error = W.git_worktree_remove(worktree, force=False)
    assert error is not None
    assert worktree.exists()
    assert W.git_worktree_remove(worktree, force=True) is None
    assert not worktree.exists()


# ---------------------------------------------------------------------------------------------
# CLI contract
# ---------------------------------------------------------------------------------------------


def test_the_json_envelope_carries_the_repo_shape(tmp_path):
    make_cache(tmp_path, "wt-topic-target")
    result = run_cli("topic", "--base", str(tmp_path), "--json", "--skip-worktree")
    payload = json.loads(result.stdout)
    assert set(payload) == {"ok", "command", "skipped", "data"}
    assert payload["command"] == "wtclean"
    assert payload["ok"] is True
    assert payload["data"]["applied"] is False
    assert payload["data"]["convention"].endswith("{target,clippy}")


def test_warnings_go_to_stderr_and_never_into_the_parsed_stream(tmp_path):
    result = run_cli("topic", "--base", str(tmp_path), "--json", "--skip-worktree")
    payload = json.loads(result.stdout)
    assert "no cache directory matched" in result.stderr
    assert any("no cache directory matched" in item for item in payload["skipped"])


def test_a_blocked_plan_exits_one_and_a_clear_one_exits_zero(tmp_path):
    make_cache(tmp_path, "wt-topic-target")
    clear = run_cli("topic", "--base", str(tmp_path), "--skip-worktree")
    assert clear.returncode == 0, clear.stderr

    (tmp_path / "wt-topic").mkdir()  # a plain dir: git cannot read its state
    blocked = run_cli("topic", "--base", str(tmp_path), "--json")
    assert blocked.returncode == 1
    payload = json.loads(blocked.stdout)
    assert payload["ok"] is False
    assert payload["skipped"]


def test_apply_deletes_for_real_through_the_cli(tmp_path):
    cache = make_cache(tmp_path, "wt-topic-target")
    result = run_cli("topic", "--base", str(tmp_path), "--skip-worktree", "--apply")
    assert result.returncode == 0, result.stderr
    assert "removed" in result.stdout
    assert not cache.exists()


# ---------------------------------------------------------------------------------------------
# Finding the worktree: a bare name must reach the layouts that actually create one
# ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize("layout", [".worktrees", "worktrees", ".claude/worktrees"])
def test_a_bare_name_finds_a_project_local_worktree(tmp_path, layout):
    """The base convention is one project's habit; these three are how worktrees get created.

    Step 1b of the skill creates <LOCATION>/<branch> and the native worktree tool creates
    .claude/worktrees/<topic>. A bare name that only ever resolved against --base reported
    "nothing to remove" for a worktree sitting right there.
    """
    checkout = tmp_path / "project" / layout / "topic"
    checkout.mkdir(parents=True)
    plan = W.build_plan(
        "topic",
        base=tmp_path,
        project=tmp_path / "project",
        status_probe=lambda _p: W.STATUS_CLEAN,
    )
    assert str(plan.worktree) == str(checkout)
    assert plan.worktree_status == W.STATUS_CLEAN


def test_the_base_convention_still_wins_when_both_exist(tmp_path):
    """Changing which of two real worktrees gets deleted would be a regression, not a fix."""
    (tmp_path / "wt-topic").mkdir()
    (tmp_path / "project" / ".worktrees" / "topic").mkdir(parents=True)
    plan = W.build_plan(
        "topic",
        base=tmp_path,
        project=tmp_path / "project",
        status_probe=lambda _p: W.STATUS_CLEAN,
    )
    assert str(plan.worktree) == str(tmp_path / "wt-topic")


def test_no_project_means_no_project_local_candidates(tmp_path):
    """The library default stays base-only, so an existing caller's target cannot move."""
    (tmp_path / ".worktrees" / "topic").mkdir(parents=True)
    plan = W.build_plan("topic", base=tmp_path, status_probe=lambda _p: W.STATUS_CLEAN)
    assert str(plan.worktree) == str(tmp_path / "wt-topic")
    assert plan.worktree_status == W.STATUS_ABSENT
    assert [str(p) for p in plan.worktree_candidates] == [str(tmp_path / "wt-topic")]


def test_the_candidates_are_reported_even_when_one_matched(tmp_path):
    """The plan has to say where it looked, or a match cannot be told from a lucky guess."""
    (tmp_path / "wt-topic").mkdir()
    plan = W.build_plan(
        "topic", base=tmp_path, project=tmp_path, status_probe=lambda _p: W.STATUS_CLEAN
    )
    checked = [str(p) for p in plan.worktree_candidates]
    assert str(tmp_path / "wt-topic") in checked
    assert str(tmp_path / ".claude" / "worktrees" / "topic") in checked


def test_an_absent_worktree_still_reports_the_base_candidate(tmp_path):
    """With nothing on disk the reported path stays the convention, not the last candidate."""
    plan = W.build_plan(
        "topic", base=tmp_path, project=tmp_path, status_probe=lambda _p: W.STATUS_CLEAN
    )
    assert str(plan.worktree) == str(tmp_path / "wt-topic")
    assert plan.worktree_status == W.STATUS_ABSENT


def test_the_run_says_which_worktree_paths_it_checked_when_none_matched(tmp_path):
    """Silence about the worktree half is what made a 513 MB checkout read as nothing to remove."""
    project = tmp_path / "project"
    project.mkdir()
    result = run_cli("topic", cwd=project, home=tmp_path)
    assert "no worktree found at" in result.stderr
    assert str(tmp_path / "wt-topic") in result.stderr
    assert str(project / ".claude" / "worktrees" / "topic") in result.stderr


@needs_git
def test_a_real_project_local_worktree_is_planned_for_removal(tmp_path):
    """The end-to-end shape the fix exists for, on a real worktree rather than a stand-in.

    A plain directory would be refused here as unreadable-by-git, which is correct behaviour but
    would leave the found-and-planned path untested.
    """
    project = tmp_path / "project"
    checkout = project / ".worktrees" / "topic"
    _main, _worktree, _git = make_repo_with_worktree(tmp_path, worktree_path=checkout)
    result = run_cli("topic", cwd=project, home=tmp_path)
    assert "no worktree found at" not in result.stderr
    assert str(checkout) in result.stdout
    assert "would remove" in result.stdout
    assert result.returncode == 0, result.stderr
    assert checkout.exists(), "a dry run must not delete it"


def test_an_explicit_base_does_not_reach_into_the_project(tmp_path):
    """The direction the widening must NOT apply: a named --base is an instruction, not a hint.

    Explicit preference beats observed filesystem state, so a run told where to look must not
    delete something it found somewhere else.
    """
    project = tmp_path / "project"
    (project / ".claude" / "worktrees" / "topic").mkdir(parents=True)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    result = run_cli("topic", "--base", str(elsewhere), "--json", cwd=project, home=tmp_path)
    payload = json.loads(result.stdout)
    assert payload["data"]["worktree"] == str(elsewhere / "wt-topic")
    assert payload["data"]["worktree_status"] == W.STATUS_ABSENT
    assert payload["data"]["worktree_candidates"] == [str(elsewhere / "wt-topic")]


def test_the_json_envelope_carries_the_worktree_paths_checked(tmp_path):
    """A machine caller has to be able to see the search, not just its verdict."""
    project = tmp_path / "project"
    project.mkdir()
    result = run_cli("topic", "--json", cwd=project, home=tmp_path)
    payload = json.loads(result.stdout)
    checked = payload["data"]["worktree_candidates"]
    assert str(tmp_path / "wt-topic") in checked
    assert str(project / ".claude" / "worktrees" / "topic") in checked


def test_a_missing_explicit_path_is_not_told_to_pass_a_path(tmp_path):
    """The advice has to fit what was actually given, or it reads as not having been understood."""
    result = run_cli(str(tmp_path / "no" / "such" / "tree"), home=tmp_path)
    assert "no worktree found at" in result.stderr
    assert str(tmp_path / "no" / "such" / "tree") in result.stderr
    assert "instead of the bare name" not in result.stderr


def test_a_missing_bare_name_is_still_told_to_pass_a_path(tmp_path):
    """The control: the advice that fits a bare name must survive the branch above."""
    result = run_cli("topic", cwd=tmp_path, home=tmp_path)
    assert "no worktree found at" in result.stderr
    assert "instead of the bare name" in result.stderr


# ---------------------------------------------------------------------------------------------
# Ambiguity: two candidates is a question, not a silent pick
# ---------------------------------------------------------------------------------------------


def test_a_bare_name_matching_two_candidates_is_refused(tmp_path):
    """There is no undo, so a topic that names two real directories has to be a question.

    Base-first precedence is still what the plan reports, but silently deleting the base one when
    the caller meant the project-local one is the mistake this refuses to make for them.
    """
    (tmp_path / "wt-topic").mkdir()
    (tmp_path / "project" / ".claude" / "worktrees" / "topic").mkdir(parents=True)
    plan = W.build_plan(
        "topic",
        base=tmp_path,
        project=tmp_path / "project",
        status_probe=lambda _p: W.STATUS_CLEAN,
    )
    assert plan.worktree_refusal is not None
    assert "more than one" in plan.worktree_refusal


def test_one_candidate_is_not_ambiguous(tmp_path):
    """The control: a refusal that fires on a single match would make the tool useless."""
    (tmp_path / "project" / ".claude" / "worktrees" / "topic").mkdir(parents=True)
    plan = W.build_plan(
        "topic",
        base=tmp_path,
        project=tmp_path / "project",
        status_probe=lambda _p: W.STATUS_CLEAN,
    )
    assert plan.worktree_refusal is None
    assert plan.worktree_status == W.STATUS_CLEAN


def test_an_explicit_path_is_never_ambiguous(tmp_path):
    """Naming the worktree outright IS the disambiguation, so it must not be refused for it."""
    (tmp_path / "wt-topic").mkdir()
    checkout = tmp_path / "project" / ".claude" / "worktrees" / "topic"
    checkout.mkdir(parents=True)
    plan = W.build_plan(
        "topic",
        base=tmp_path,
        project=tmp_path / "project",
        worktree=checkout,
        status_probe=lambda _p: W.STATUS_CLEAN,
    )
    assert plan.worktree_refusal is None
    assert str(plan.worktree) == str(checkout)


def test_no_flag_overrides_an_ambiguous_topic(tmp_path):
    """--discard-uncommitted answers "delete it anyway", not "pick one for me"."""
    (tmp_path / "wt-topic").mkdir()
    (tmp_path / "project" / ".claude" / "worktrees" / "topic").mkdir(parents=True)
    plan = W.build_plan(
        "topic",
        base=tmp_path,
        project=tmp_path / "project",
        status_probe=lambda _p: W.STATUS_CLEAN,
    )
    assert W.worktree_refusal(plan, discard_uncommitted=True) is not None


def test_the_cli_names_both_candidates_and_removes_neither(tmp_path):
    """End to end: exit 1, both paths named, and both still on disk afterwards."""
    project = tmp_path / "project"
    base_wt = tmp_path / "wt-topic"
    base_wt.mkdir()
    local_wt = project / ".claude" / "worktrees" / "topic"
    local_wt.mkdir(parents=True)
    result = run_cli("topic", "--apply", cwd=project, home=tmp_path)
    assert result.returncode == 1, result.stdout + result.stderr
    assert str(base_wt) in result.stderr
    assert str(local_wt) in result.stderr
    assert base_wt.exists() and local_wt.exists()


def test_an_ambiguous_topic_blocks_the_caches_too(tmp_path):
    """The caches are derived from the SAME name the tool just said it could not resolve.

    Two checkouts sharing a topic share cache candidates, so removing them under an ambiguous
    topic destroys the other checkout's cache on the strength of a name that was refused.
    """
    (tmp_path / "wt-topic").mkdir()
    (tmp_path / "project" / ".claude" / "worktrees" / "topic").mkdir(parents=True)
    make_cache(tmp_path, "wt-topic-target")
    plan = W.build_plan(
        "topic",
        base=tmp_path,
        project=tmp_path / "project",
        status_probe=lambda _p: W.STATUS_CLEAN,
    )
    blocked = [str(item.path) for item in W.blocked_reasons(plan)]
    assert str(tmp_path / "wt-topic-target") in blocked


def test_a_dirty_worktree_still_lets_the_caches_go(tmp_path):
    """The control: only AMBIGUITY widens to the caches, not every worktree refusal.

    A dirty checkout is a resolved one, so its caches are unambiguously the right caches.
    """
    (tmp_path / "wt-topic").mkdir()
    make_cache(tmp_path, "wt-topic-target")
    plan = W.build_plan("topic", base=tmp_path, status_probe=lambda _p: W.STATUS_DIRTY)
    blocked = [str(item.path) for item in W.blocked_reasons(plan)]
    assert str(tmp_path / "wt-topic") in blocked
    assert str(tmp_path / "wt-topic-target") not in blocked


def test_the_cli_removes_no_cache_under_an_ambiguous_topic(tmp_path):
    """End to end: --apply leaves the cache on disk and exits 1."""
    project = tmp_path / "project"
    (tmp_path / "wt-topic").mkdir()
    (project / ".claude" / "worktrees" / "topic").mkdir(parents=True)
    cache = make_cache(tmp_path, "wt-topic-target")
    result = run_cli("topic", "--apply", cwd=project, home=tmp_path)
    assert result.returncode == 1, result.stdout + result.stderr
    assert cache.exists(), "an unresolvable name must not delete a cache derived from it"
