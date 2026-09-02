"""Tests for ci-watch-nudge - records a LANDED push and clears the record when CI is watched.

These drive a real git repository with a real remote rather than patching the git calls. The whole
subtlety of the hook is its landed-test (`HEAD` == `@{u}`), and a patched `_git` would assert the
shape of the mock instead of the behaviour that matters.
"""
from __future__ import annotations

import json
import subprocess

import ci_watch_nudge as hook
import ci_watch_state as state
import pytest


def _git(cwd, *args):
    subprocess.run(["git", *args], cwd=str(cwd), check=True,
                   capture_output=True, text=True, encoding="utf-8", errors="replace")


@pytest.fixture()
def repo(tmp_path):
    """A clone with an upstream and a CI workflow, one commit ahead of nothing."""
    remote = tmp_path / "remote.git"
    work = tmp_path / "work"
    subprocess.run(["git", "init", "--bare", "-b", "master", str(remote)],
                   check=True, capture_output=True)
    subprocess.run(["git", "clone", str(remote), str(work)], check=True, capture_output=True)
    _git(work, "config", "user.email", "t@example.invalid")
    _git(work, "config", "user.name", "T")
    flows = work / ".github" / "workflows"
    flows.mkdir(parents=True)
    (flows / "ci.yml").write_text("name: ci\n", encoding="utf-8")
    (work / "f.txt").write_text("one\n", encoding="utf-8")
    _git(work, "add", "-A")
    _git(work, "commit", "-m", "first")
    _git(work, "push", "-u", "origin", "master")
    return work


def _event(command, cwd, session="sess-1", tool="Bash"):
    return json.dumps({"tool_name": tool, "cwd": str(cwd), "session_id": session,
                       "tool_input": {"command": command}})


def test_a_landed_push_is_recorded_and_announced(repo, capsys):
    assert hook.main(_event("git push", repo)) == 0
    out = capsys.readouterr().out
    payload = json.loads(out)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(repo), capture_output=True,
                          text=True, check=True).stdout.strip()
    assert payload["hookSpecificOutput"]["hookEventName"] == "PostToolUse"
    assert head[:12] in payload["hookSpecificOutput"]["additionalContext"]
    assert "ci_wait.py" in payload["hookSpecificOutput"]["additionalContext"]
    assert [e["sha"] for e in state.pending_for(str(repo), "sess-1")] == [head]


def test_a_push_that_did_not_land_is_not_recorded(repo, capsys):
    """The usual shape is `git push 2>&1 | tail -3`, which exits 0 whatever git did."""
    (repo / "f.txt").write_text("two\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "second")          # committed but never pushed
    assert hook.main(_event("git push 2>&1 | tail -3", repo)) == 0
    assert capsys.readouterr().out == ""
    assert state.pending_for(str(repo), "sess-1") == []


def test_a_command_merely_quoting_git_push_does_not_fire(repo, capsys):
    """The guard must not fire on prose that mentions the pattern - it would block its own docs."""
    assert hook.main(_event('git commit --allow-empty -m "wip; git push later"', repo)) == 0
    assert capsys.readouterr().out == ""
    assert state.pending_for(str(repo), "sess-1") == []


def test_a_dry_run_push_does_not_fire(repo, capsys):
    assert hook.main(_event("git push --dry-run", repo)) == 0
    assert capsys.readouterr().out == ""


def test_a_branch_delete_does_not_fire(repo, capsys):
    assert hook.main(_event("git push origin --delete sidebranch", repo)) == 0
    assert capsys.readouterr().out == ""


def test_a_repo_without_workflows_does_not_fire(repo, capsys):
    """The applicability test the tree-top rule states for itself: is there CI to watch?"""
    for stale in (repo / ".github" / "workflows").glob("*.yml"):
        stale.unlink()
    assert hook.main(_event("git push", repo)) == 0
    assert capsys.readouterr().out == ""


def test_watching_ci_clears_the_record(repo, capsys):
    hook.main(_event("git push", repo))
    capsys.readouterr()
    assert state.pending_for(str(repo), "sess-1") != []
    assert hook.main(_event("uv run scripts/ci_wait.py --sha deadbeef", repo)) == 0
    assert capsys.readouterr().out == ""
    assert state.pending_for(str(repo), "sess-1") == []


@pytest.mark.parametrize("watcher", [
    "gh run watch 123",
    "gh run list --workflow ci.yml",
    "gh run view 42 --log-failed",
    "gh pr checks",
])
def test_every_documented_watch_form_clears_the_record(repo, capsys, watcher):
    hook.main(_event("git push", repo))
    capsys.readouterr()
    assert hook.main(_event(watcher, repo)) == 0
    assert state.pending_for(str(repo), "sess-1") == []


def test_the_bypass_env_silences_it(repo, capsys, monkeypatch):
    monkeypatch.setenv("BITRANOX_CI_WATCH", "1")
    assert hook.main(_event("git push", repo)) == 0
    assert capsys.readouterr().out == ""
    assert state.pending_for(str(repo), "sess-1") == []


def test_a_non_shell_tool_is_ignored(repo, capsys):
    assert hook.main(_event("git push", repo, tool="Edit")) == 0
    assert capsys.readouterr().out == ""


def test_malformed_input_never_raises(repo, capsys):
    for raw in ("", "{not json", json.dumps({"tool_name": "Bash"}), json.dumps([1, 2])):
        assert hook.main(raw) == 0
    assert capsys.readouterr().out == ""


# --- `git -C <dir> push`: the shape the transcript corpus is full of ------------------------
# The call's cwd is the PARENT, so resolving the repo from cwd asks the wrong repository and
# answers confidently. These pin the resolution rather than the happy path.

def _sibling_repo(tmp_path, name, with_workflows=True):
    """A second pushable clone beside the first, so -C has somewhere real to point."""
    remote = tmp_path / (name + ".git")
    work = tmp_path / name
    subprocess.run(["git", "init", "--bare", "-b", "master", str(remote)],
                   check=True, capture_output=True)
    subprocess.run(["git", "clone", str(remote), str(work)], check=True, capture_output=True)
    _git(work, "config", "user.email", "t@example.invalid")
    _git(work, "config", "user.name", "T")
    if with_workflows:
        flows = work / ".github" / "workflows"
        flows.mkdir(parents=True)
        (flows / "ci.yml").write_text("name: ci\n", encoding="utf-8")
    (work / "g.txt").write_text("one\n", encoding="utf-8")
    _git(work, "add", "-A")
    _git(work, "commit", "-m", "first")
    _git(work, "push", "-u", "origin", "master")
    return work


def test_dash_c_records_the_sha_of_the_targeted_repo_not_the_cwd(tmp_path, repo, capsys):
    """The defect the corpus surfaced: cwd is the parent, the push is to a sibling."""
    other = _sibling_repo(tmp_path, "other")
    assert hook.main(_event("git -C other push origin HEAD", tmp_path)) == 0
    text = json.loads(capsys.readouterr().out)["hookSpecificOutput"]["additionalContext"]
    other_head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(other), capture_output=True,
                                text=True, check=True).stdout.strip()
    repo_head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(repo), capture_output=True,
                               text=True, check=True).stdout.strip()
    assert other_head[:12] in text
    assert repo_head[:12] not in text
    assert [e["sha"] for e in state.pending_for(str(tmp_path), "sess-1")] == [other_head]


def test_dash_c_into_a_repo_without_workflows_does_not_fire(tmp_path, capsys):
    _sibling_repo(tmp_path, "plain", with_workflows=False)
    assert hook.main(_event("git -C plain push origin HEAD", tmp_path)) == 0
    assert capsys.readouterr().out == ""


def test_a_dash_c_path_from_an_expansion_is_not_guessed(tmp_path, capsys):
    """An unresolvable path must bail, not fall back to cwd and ask the wrong repo."""
    _sibling_repo(tmp_path, "other")
    assert hook.main(_event('git -C "$TARGET" push origin HEAD', tmp_path)) == 0
    assert capsys.readouterr().out == ""
    assert state.pending_for(str(tmp_path), "sess-1") == []


def test_watching_clears_a_record_made_by_a_dash_c_push(tmp_path, capsys):
    _sibling_repo(tmp_path, "other")
    hook.main(_event("git -C other push origin HEAD", tmp_path))
    capsys.readouterr()
    assert state.pending_for(str(tmp_path), "sess-1") != []
    assert hook.main(_event("gh run watch 5", tmp_path)) == 0
    assert state.pending_for(str(tmp_path), "sess-1") == []


# --- pushed-ref resolution: a tag builds a DIFFERENT run than its branch --------------------

def _tag(repo, name):
    _git(repo, "tag", "-a", name, "-m", name)
    return subprocess.run(["git", "rev-parse", name + "^{commit}"], cwd=str(repo),
                          capture_output=True, text=True, check=True).stdout.strip()


def test_an_explicit_tag_push_is_recorded_as_the_tag(repo, capsys):
    """At release time the tag's run is the one that matters, not its branch's."""
    tag_sha = _tag(repo, "v1.2.3")
    assert hook.main(_event("git push origin v1.2.3", repo)) == 0
    text = json.loads(capsys.readouterr().out)["hookSpecificOutput"]["additionalContext"]
    assert "tag v1.2.3" in text
    assert tag_sha[:12] in text


def test_a_bulk_tags_push_uses_the_newest_tag(repo, capsys):
    _tag(repo, "v1.0.0")
    newest = _tag(repo, "v2.0.0")
    assert hook.main(_event("git push --tags", repo)) == 0
    text = json.loads(capsys.readouterr().out)["hookSpecificOutput"]["additionalContext"]
    assert "tag v2.0.0" in text
    assert newest[:12] in text


def test_an_explicit_branch_push_still_resolves_the_branch(repo, capsys):
    assert hook.main(_event("git push origin master", repo)) == 0
    text = json.loads(capsys.readouterr().out)["hookSpecificOutput"]["additionalContext"]
    assert "branch master" in text


def test_a_plain_push_still_uses_the_landed_test(repo, capsys):
    """No refspec named, so the branch landed-test applies exactly as before."""
    assert hook.main(_event("git push", repo)) == 0
    text = json.loads(capsys.readouterr().out)["hookSpecificOutput"]["additionalContext"]
    assert "master" in text


def test_a_refspec_pair_resolves_by_its_source(repo, capsys):
    tag_sha = _tag(repo, "v3.0.0")
    assert hook.main(_event("git push origin v3.0.0:refs/tags/v3.0.0", repo)) == 0
    text = json.loads(capsys.readouterr().out)["hookSpecificOutput"]["additionalContext"]
    assert tag_sha[:12] in text


def test_a_refspec_that_does_not_resolve_falls_back_to_the_branch(repo, capsys):
    """An unknown ref must not silently record nothing - the ordinary push test still applies."""
    assert hook.main(_event("git push origin no-such-ref", repo)) == 0
    assert capsys.readouterr().out != ""


def test_bulk_tags_prefers_the_newest_by_time_not_the_highest_version(repo, capsys):
    """The discriminating case: an OLD high version beside a NEW low one.

    `for-each-ref` treats the LAST --sort key as primary, so the key order that reads naturally
    (creatordate first) actually sorts by version and would pick v10.0.0 here.
    """
    import os
    env = dict(os.environ)
    env["GIT_COMMITTER_DATE"] = env["GIT_AUTHOR_DATE"] = "2020-01-01T00:00:00"
    subprocess.run(["git", "tag", "-a", "v10.0.0", "-m", "old"], cwd=str(repo),
                   check=True, capture_output=True, env=env)
    env["GIT_COMMITTER_DATE"] = env["GIT_AUTHOR_DATE"] = "2026-01-01T00:00:00"
    subprocess.run(["git", "tag", "-a", "v2.0.0", "-m", "new"], cwd=str(repo),
                   check=True, capture_output=True, env=env)

    assert hook.main(_event("git push --tags", repo)) == 0
    text = json.loads(capsys.readouterr().out)["hookSpecificOutput"]["additionalContext"]
    assert "tag v2.0.0" in text, "picked the highest version instead of the newest tag"
    assert "v10.0.0" not in text



def _names(resolved, posix_path):
    """Does `resolved` name `posix_path`? `_repo_dir` returns an ABSOLUTE path, so on Windows
    `/real/repo` comes back as `D:\\real\\repo`. A bare `==` fails there - and a bare `!=`
    passes VACUOUSLY there even with the defect present, which is the worse half of the same
    mistake. Compare on the normalised tail instead."""
    if resolved is None:
        return False
    return resolved.replace("\\", "/").endswith(posix_path)


def test_a_dash_c_inside_a_heredoc_body_is_not_the_repo():
    """A heredoc body is stdin DATA. Reading `git -C <path>` out of one makes the nudge watch CI
    in a repository the command never touched - it would report on the wrong repo, confidently.
    `mask_data_regions` alone cannot catch this: a heredoc body is not quoted, so masking leaves
    it looking like a statement. The canonical idiom pairs it with `strip_heredoc_bodies`, which
    `git-wrong-repo-nudge` and `git-path-not-here-nudge` both use and this hook does not."""
    cmd = "cat > r.md <<EOF\ngit -C /fake/repo push\nEOF\ngit push origin master"
    assert not _names(hook._repo_dir(cmd, "/cwd"), "/fake/repo")


def test_a_real_dash_c_is_still_the_repo():
    """The direction where it must NOT apply."""
    assert _names(hook._repo_dir("git -C /real/repo push origin master", "/cwd"), "/real/repo")


def test_a_neighbouring_statements_flag_is_not_read_as_this_ones():
    """`--dry-run` was matched against the WHOLE command, so a dry run in one statement silenced
    the nudge for a genuine push in another. `_statement_around` is the scoping that fixes it;
    `notice` itself needs a real repo, so the pure helper is what can actually be asserted here."""
    cmd = "git push --dry-run origin master && git push origin master"
    real_push = cmd.rindex("git push")
    assert "--dry-run" not in hook._statement_around(cmd, real_push)


def test_the_statement_around_a_lone_dry_run_still_contains_it():
    """The direction where it must NOT apply."""
    cmd = "git push --dry-run origin master"
    assert "--dry-run" in hook._statement_around(cmd, cmd.index("git push"))


# --- which FORGE the push landed on -------------------------------------------------------
# `_has_workflows` asks whether the repo has CI files. A fork that vendors upstream's
# `.github/workflows` passes that while its own pushes go to a forge running no Actions, so the
# nudge points `gh` at a repository that has never seen the sha and the watch cannot terminate.


def test_a_push_to_a_non_github_forge_is_not_recorded(repo, capsys):
    """Measured on a fork whose pushes go to a private Gitea while `gh` resolves the checkout to
    the upstream repository, whose API answers 422 'No commit found for SHA'."""
    _git(repo, "remote", "add", "forge", "ssh://git.example.invalid/team/thing.git")
    assert hook.main(_event("git push forge master", repo)) == 0
    assert capsys.readouterr().out == ""
    assert state.pending_for(str(repo), "sess-1") == []


def test_a_push_to_github_is_still_recorded(repo, capsys):
    """The control. Without it, a skip-everything bug would pass the test above."""
    _git(repo, "remote", "add", "gh", "https://github.com/owner/thing.git")
    assert hook.main(_event("git push gh master", repo)) == 0
    assert "ci_wait.py" in capsys.readouterr().out
    assert len(state.pending_for(str(repo), "sess-1")) == 1


def test_an_scp_style_github_remote_is_still_recorded(repo, capsys):
    """`git@github.com:owner/thing.git` names no scheme, so a URL parser that only splits on
    `://` reads it as a path and would skip a real GitHub push."""
    _git(repo, "remote", "add", "gh", "git@github.com:owner/thing.git")
    assert hook.main(_event("git push gh master", repo)) == 0
    assert "ci_wait.py" in capsys.readouterr().out


def test_an_enterprise_host_gh_holds_auth_for_is_recorded(repo, capsys, tmp_path, monkeypatch):
    """GitHub Enterprise has an arbitrary hostname, so github.com alone is not the whole set."""
    cfg = tmp_path / "ghcfg"
    cfg.mkdir()
    (cfg / "hosts.yml").write_text("github.example.invalid:\n    user: someone\n", encoding="utf-8")
    monkeypatch.setenv("GH_CONFIG_DIR", str(cfg))
    _git(repo, "remote", "add", "ent", "https://github.example.invalid/owner/thing.git")
    assert hook.main(_event("git push ent master", repo)) == 0
    assert "ci_wait.py" in capsys.readouterr().out


def test_a_local_path_remote_keeps_the_nudge(repo, capsys):
    """A remote naming no host is what every fixture here uses to stand in for a real one, so
    reading it as 'no CI' would decide semantics from a test's convenience."""
    assert hook.main(_event("git push", repo)) == 0
    assert "ci_wait.py" in capsys.readouterr().out
