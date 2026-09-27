"""Tests for git-commit-branch-guard.py (warn-only PreToolUse commit-state guard). ASCII.

The hyphenated module is loaded + aliased as `git_commit_branch_guard` by conftest.py.
"""
import io
import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import git_commit_branch_guard as G

_HOOK = Path(__file__).resolve().parent.parent / "git-commit-branch-guard.py"


def _q(path):
    """``path`` as bash reads it: a bare Windows path loses its backslashes to bash's escapes."""
    return shlex.quote(str(path))


def test_is_git_commit():
    assert G._is_git_commit('git commit -m "x"')
    assert G._is_git_commit("git -C /repo commit -m x")
    assert G._is_git_commit("ls && git commit -F -")
    assert not G._is_git_commit("git status")
    assert not G._is_git_commit("git log --oneline -1")
    assert not G._is_git_commit("echo commit")


def test_is_git_commit_ignores_git_commit_appearing_as_data():
    """git+commit in a STRING, a COMMENT or a HEREDOC body is not a commit.

    The bag-of-tokens test this replaces split on separators and then asked only whether both
    words were present ANYWHERE in a segment, so a read-only `git log` carrying the word in a
    trailing comment spent 2-4 git subprocesses and warned about a commit that is not happening.
    The last assertion is the control: it must stay True, or this test would pass against a
    predicate that has simply stopped recognising commits at all.
    """
    assert not G._is_git_commit('echo "run git commit later"')
    assert not G._is_git_commit("git log -1 --pretty=%B  # inspect the commit message")
    assert not G._is_git_commit("cat > note.md <<'EOF'\ngit commit -m x\nEOF")
    assert G._is_git_commit('git commit -m "x"')  # control: a real commit still matches


def _fake_git(returns):
    def _f(cwd, *a):
        if a[0] == "rev-parse" and "--show-toplevel" in a:
            return returns.get("toplevel")
        if a[0] == "rev-list":
            return returns.get("ahead_behind")
        if a[0] == "symbolic-ref" and "refs/remotes/origin/HEAD" in a:
            return returns.get("origin_head")
        if a[0] == "symbolic-ref":
            return returns.get("branch")
        return None
    return _f


def _context(out):
    """The additionalContext the hook put on stdout, or "" when it stayed silent.

    Read from STDOUT on purpose: an exit-0 hook's stderr never reaches the model, so a warning
    written there is a warning nobody reads. These tests used to assert on stderr and so pinned
    the invisible channel.
    """
    if not out.strip():
        return ""
    payload = json.loads(out)["hookSpecificOutput"]
    assert payload["hookEventName"] == "PreToolUse"
    assert "permissionDecision" not in payload                     # warn only, never block
    return payload["additionalContext"]


def _run(monkeypatch, capsys, command, returns, strict_repos=None):
    monkeypatch.setattr(G, "_git", _fake_git(returns))
    if strict_repos is None:
        monkeypatch.delenv("GIT_GUARD_STRICT_REPOS", raising=False)
    else:
        monkeypatch.setenv("GIT_GUARD_STRICT_REPOS", strict_repos)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"tool_input": {"command": command}, "cwd": "/x"})))
    rc = G.main()
    captured = capsys.readouterr()
    assert captured.err == ""
    return rc, _context(captured.out)


# toplevel + on a feature branch + default 'main'
BASE = {"toplevel": "/p/myrepo", "branch": "feature", "origin_head": "origin/main"}


def test_silent_when_ahead_only(monkeypatch, capsys):
    rc, err = _run(monkeypatch, capsys, "git commit -m x", dict(BASE, ahead_behind="2\t0"))
    assert rc == 0 and err == ""


def test_silent_when_no_upstream(monkeypatch, capsys):
    rc, err = _run(monkeypatch, capsys, "git commit -m x", dict(BASE, ahead_behind=None))
    assert rc == 0 and err == ""


def test_warns_when_behind_any_repo(monkeypatch, capsys):
    # the always-on safe check: fires in any repo, no strict config needed
    rc, err = _run(monkeypatch, capsys, "git commit -m x", dict(BASE, ahead_behind="0\t3"))
    assert rc == 0 and "3 commit(s) behind/diverged" in err


def test_branch_check_off_by_default(monkeypatch, capsys):
    # on a feature branch, up to date: silent unless the repo is in GIT_GUARD_STRICT_REPOS
    rc, err = _run(monkeypatch, capsys, "git commit -m x", dict(BASE, ahead_behind="0\t0"))
    assert rc == 0 and err == ""


def test_branch_check_warns_for_strict_repo(monkeypatch, capsys):
    rc, err = _run(monkeypatch, capsys, "git commit -m x", dict(BASE, ahead_behind="0\t0"),
                   strict_repos="other,myrepo")
    assert rc == 0 and "not the default 'main'" in err and "feature" in err


def test_branch_check_detached_for_strict_repo(monkeypatch, capsys):
    rc, err = _run(monkeypatch, capsys, "git commit -m x", dict(BASE, branch=None, ahead_behind="0\t0"),
                   strict_repos="myrepo")
    assert rc == 0 and "DETACHED" in err


def test_strict_repo_not_matched_is_silent(monkeypatch, capsys):
    rc, err = _run(monkeypatch, capsys, "git commit -m x", dict(BASE, ahead_behind="0\t0"),
                   strict_repos="some-other-repo")
    assert rc == 0 and err == ""


def test_silent_not_a_git_repo(monkeypatch, capsys):
    rc, err = _run(monkeypatch, capsys, "git commit -m x", dict(BASE, toplevel=None, ahead_behind="0\t9"))
    assert rc == 0 and err == ""


def test_silent_non_commit(monkeypatch, capsys):
    rc, err = _run(monkeypatch, capsys, "git status", dict(BASE, ahead_behind="0\t9"))
    assert rc == 0 and err == ""


def test_bad_stdin_safe(monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO("not json"))
    assert G.main() == 0



# --- real repositories: nothing between the hook and git is faked ---------------------------------

_GIT_ENV_SCOPE = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY",
                  "GIT_COMMON_DIR", "GIT_PREFIX")


def _isolated_env():
    """An environment whose git reads no user or system config and no inherited repo scope.

    A push from a linked worktree exports GIT_DIR to its hooks, and git reads it before the cwd,
    so a fixture built without clearing it would write into the repository being pushed.
    """
    env = {k: v for k, v in os.environ.items() if k not in _GIT_ENV_SCOPE}
    env.update({"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1", "LC_ALL": "C",
                "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
                "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid"})
    env.pop("GIT_GUARD_STRICT_REPOS", None)
    return env


def _sh(env, cwd, *args):
    proc = subprocess.run(["git", *args], cwd=cwd, env=env, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=60)
    assert proc.returncode == 0, (args, proc.stderr)
    return proc.stdout.strip()


@pytest.fixture
def shared(tmp_path, monkeypatch):
    """`w` is one commit BEHIND its upstream; `o` is in sync. Both track `main` on a bare origin."""
    if shutil.which("git") is None:
        pytest.skip("needs a real git")
    env = _isolated_env()
    for key in _GIT_ENV_SCOPE + ("GIT_GUARD_STRICT_REPOS",):
        monkeypatch.delenv(key, raising=False)
    for key in ("GIT_CONFIG_GLOBAL", "GIT_CONFIG_NOSYSTEM", "LC_ALL"):
        monkeypatch.setenv(key, env[key])
    _sh(env, tmp_path, "-c", "init.defaultBranch=main", "init", "-q", "--bare", "up.git")
    _sh(env, tmp_path, "clone", "-q", "up.git", "w")
    w, o = tmp_path / "w", tmp_path / "o"
    _sh(env, w, "checkout", "-q", "-b", "main")
    _sh(env, w, "commit", "-q", "--allow-empty", "-m", "one")
    _sh(env, w, "push", "-q", "-u", "origin", "main")
    _sh(env, tmp_path, "clone", "-q", "up.git", "o")
    _sh(env, o, "commit", "-q", "--allow-empty", "-m", "two")
    _sh(env, o, "push", "-q")
    _sh(env, w, "fetch", "-q")
    assert _sh(env, w, "rev-list", "--left-right", "--count", "HEAD...@{upstream}").split() == ["0", "1"]
    assert _sh(env, o, "rev-list", "--left-right", "--count", "HEAD...@{upstream}").split() == ["0", "0"]
    return {"root": tmp_path, "w": w, "o": o, "env": env}


def _hook(shared, command, cwd, strict=None, tool_name="Bash"):
    env = dict(shared["env"])
    if strict is not None:
        env["GIT_GUARD_STRICT_REPOS"] = strict
    event = {"tool_name": tool_name, "cwd": str(cwd), "tool_input": {"command": command}}
    proc = subprocess.run([sys.executable, str(_HOOK)], input=json.dumps(event).encode("utf-8"),
                          capture_output=True, env=env, timeout=60)
    assert proc.returncode == 0 and proc.stderr == b"", proc.stderr
    return _context(proc.stdout.decode("utf-8"))


def test_a_behind_checkout_is_reported_on_stdout_where_the_model_reads_it(shared):
    ctx = _hook(shared, "git commit -m x", shared["w"])
    assert "1 commit(s) behind/diverged" in ctx


def test_an_in_sync_checkout_is_silent(shared):
    assert _hook(shared, "git commit -m x", shared["o"]) == ""


def test_git_dash_C_is_judged_by_the_repo_it_names_not_the_event_cwd(shared):
    # The guard used to ask git about the EVENT cwd, so it warned about an in-sync target and
    # missed a behind one, in both directions.
    assert _hook(shared, f"git -C {_q(shared['o'])} commit -m x", shared["w"]) == ""
    assert "behind" in _hook(shared, f"git -C {_q(shared['w'])} commit -m x", shared["o"])
    assert "behind" in _hook(shared, "git -C w commit -m x", shared["root"])      # relative


def test_a_leading_cd_is_judged_by_where_it_lands(shared):
    assert "behind" in _hook(shared, f"cd {_q(shared['w'])} && git commit -m x", shared["o"])
    assert _hook(shared, f"cd {_q(shared['o'])} && git add f; git commit -m x", shared["w"]) == ""
    assert "behind" in _hook(shared, "cd o && cd ../w && git commit -m x", shared["root"])


def test_an_unreadable_target_is_silent(shared):
    # The event cwd is behind, so a guard that fell back to it would warn - about a repo the
    # commit may not touch at all.
    for command in ('cd "$REPO" && git commit -m x', "git -C $REPO commit -m x",
                    "cd - && git commit -m x", "cd && git commit -m x", "cd ~ && git commit -m x",
                    "git --git-dir=/elsewhere/.git commit -m x",
                    "GIT_DIR=/elsewhere/.git git commit -m x"):
        assert _hook(shared, command, shared["w"]) == "", command


def test_a_target_that_is_not_a_repository_is_silent(shared):
    plain = shared["root"] / "plain"
    plain.mkdir()
    assert _hook(shared, f"git -C {plain} commit -m x", shared["w"]) == ""
    assert _hook(shared, f"git -C {_q(shared['root'] / 'missing')} commit -m x", shared["w"]) == ""


def test_strict_mode_is_silent_on_the_default_branch(shared):
    assert _hook(shared, "git commit -m x", shared["o"], strict="o") == ""


def test_strict_mode_warns_off_the_default_branch(shared):
    _sh(shared["env"], shared["o"], "checkout", "-q", "-b", "feature")
    ctx = _hook(shared, "git commit -m x", shared["o"], strict="o")
    assert "not the default 'main'" in ctx and "'feature'" in ctx


def test_strict_mode_is_silent_when_origin_HEAD_is_undetermined(shared):
    _sh(shared["env"], shared["o"], "checkout", "-q", "-b", "feature")
    _sh(shared["env"], shared["o"], "remote", "set-head", "origin", "-d")
    assert _hook(shared, "git commit -m x", shared["o"], strict="o") == ""


def test_strict_mode_warns_on_a_detached_head(shared):
    _sh(shared["env"], shared["o"], "checkout", "-q", "--detach")
    assert "DETACHED" in _hook(shared, "git commit -m x", shared["o"], strict="o")


def test_git_runs_real_git_and_fails_open(shared):
    top = G._git(str(shared["o"]), "rev-parse", "--show-toplevel")
    assert top is not None and os.path.samefile(top, shared["o"])
    assert G._git(str(shared["o"]), "rev-parse", "--verify", "-q", "nosuchref") is None   # rc 1
    assert G._git(str(shared["root"] / "missing"), "rev-parse", "--show-toplevel") is None
    assert G._git("bad\x00path", "rev-parse", "--show-toplevel") is None     # subprocess raises


def test_the_behind_count_parser_refuses_malformed_output():
    assert G._parse_behind("0\t3") == 3
    assert G._parse_behind("2 0") == 0
    for malformed in (None, "", "5", "a\tb", "garbage"):
        assert G._parse_behind(malformed) is None, malformed


def test_commit_target_follows_the_shell_and_git_the_way_they_run():
    base = os.path.join(os.sep, "base")
    # abspath gives a drive on Windows: a bare '\r' is drive-relative there, so after an unreadable
    # `cd "$X"` the drive is unknown too and the target rightly stays unreadable.
    top = os.path.abspath(os.path.join(os.sep, "r"))
    j = os.path.join
    assert G._commit_target("git commit -m x", base) == base
    assert G._commit_target(f"cd -P {_q(top)} && git commit -m x", base) == top
    assert G._commit_target(f"cd -- {_q(top)} && git commit -m x", base) == top
    assert G._commit_target("git -C a -C b commit -m x", base) == j(base, "a", "b")
    assert G._commit_target(f'git -c user.name="A B" -C {_q(top)} commit -m x', base) == top
    assert G._commit_target("cd a; pushd b && git commit -m x", base) == j(base, "a", "b")
    assert G._commit_target("Set-Location sub; git commit -m x", base, "PowerShell") == j(base, "sub")
    assert G._commit_target("cd a && popd && git commit -m x", base) is None
    assert G._commit_target(f'cd "$X" && cd {_q(top)} && git commit -m x', base) == top   # absolute recovers
    assert G._commit_target('cd "$X" && cd sub && git commit -m x', base) is None
    assert G._commit_target("git -C", base) is None                                     # no verb
    assert G._commit_target(f"git commit -m x && cd {_q(top)}", base) == base              # cd after
    assert G._commit_target("cd -P && git commit -m x", base) is None                  # no operand
    assert G._commit_target("; git commit -m x", base) == base                         # empty statement
