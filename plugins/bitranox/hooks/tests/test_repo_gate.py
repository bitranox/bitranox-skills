"""Tests for repo-gate.py (the pre-commit / CI gate).

The pure checks (tests-exist, json-valid, command detection, repo detection) are
exercised against synthetic trees in tmp_path. git-dependent checks (lf-endings,
version-bump) self-skip outside a git repo, which these synthetic trees rely on, so
they never produce spurious failures here. main() is driven with repo_root /
check_pytest patched so no real pytest run or real repo is needed.

All content is ASCII.
"""

import io
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import repo_gate as RG


# --------------------------------------------------------------------------
# Synthetic-tree helpers
# --------------------------------------------------------------------------


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def make_repo(root, *, version="1.6.0", good_skill=True, bad_skill=False,
              demo_only=False, changelog=True):
    write(root / "plugins/bitranox/.claude-plugin/plugin.json",
          json.dumps({"name": "bitranox", "version": version}))
    write(root / ".claude-plugin/marketplace.json", json.dumps({"name": "bitranox-skills"}))
    # A clean tree now includes an entry for the version the manifest names: the changelog check
    # is an invariant, so it fires on any tree whose version is undocumented, not only on a bump.
    # Callers that want the violation pass changelog=False.
    if changelog:
        write(root / "CHANGELOG.md", f"# Changelog\n\n## [{version}]\n\n- fixture\n")
    write(root / "plugins/bitranox/hooks/hooks.json", json.dumps({"hooks": {}}))
    # A hook package that ships a script + a test (always conforms).
    write(root / "plugins/bitranox/hooks/somehook.py", "x = 1\n")
    write(root / "plugins/bitranox/hooks/tests/test_somehook.py", "def test_ok():\n    assert True\n")
    if good_skill:
        write(root / "plugins/bitranox/skills/good/script.py", "y = 2\n")
        write(root / "plugins/bitranox/skills/good/tests/test_script.py", "def test_ok():\n    assert True\n")
    if bad_skill:
        write(root / "plugins/bitranox/skills/bad/script.py", "z = 3\n")  # ships a script, no tests/
    if demo_only:
        # A skill whose only .py live under demos/ -> exempt, must NOT be flagged.
        write(root / "plugins/bitranox/skills/demoskill/SKILL.md", "# doc\n")
        write(root / "plugins/bitranox/skills/demoskill/demos/client.py", "pass\n")
    return root


# --------------------------------------------------------------------------
# is_gated_command
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "cmd,expected",
    [
        ("git commit -m 'x'", True),
        ("git add -A && git commit -m 'x'", True),
        ("git -C /repo commit --amend", True),
        ("git --no-pager commit -m x", True),
        ("FOO=bar git commit -m x", True),          # env-assignment prefix
        ("(git commit -m x)", True),                # subshell
        ("gh pr create --fill", True),
        # push is gated too: it is the moment a change reaches CI
        ("git push", True),
        ("git push --force origin master", True),
        ("git -C /repo push", True),
        ("git add -A && git commit -m x && git push", True),
        ("git status", False),
        ("ls && echo commit done", False),
        ("git log --oneline", False),
        # the false-positive this fix targets: "git commit"/"git push" only INSIDE a string body
        ('echo "use git commit -m msg -- paths"', False),
        ('echo "remember to git push after"', False),
        ("python3 -c \"print('git commit -m x')\"", False),
        ("sed -i s/a/b/ f; echo 'commit only your paths: git commit -- f'", False),
        # A HEREDOC BODY is data too, and anchoring alone does not cover it: the body's own lines
        # are split on the same separators, so `... && git commit -m x` inside a quoted Python
        # literal yields a segment that begins with a real-looking command. Measured 2026-08-20 -
        # writing the tests for gated-prep-nudge was blocked by the gate, because the test data
        # named the very shapes under test.
        ("python3 - <<'PY'\nfor cmd in (\"git checkout -- f && git commit -m x\",):\n    pass\nPY\necho done", False),
        ("cat > doc.md <<'EOF'\nNever chain git checkout && git commit in one call.\nEOF\necho ok", False),
        ("cat > d.md <<'EOF'\nrun git push origin master afterwards\nEOF\nls", False),
        # ... while a real verb AFTER the body still gates, which is the whole point of keeping the
        # opener and dropping only the body.
        ("cat > m <<'EOF'\nsubject\nEOF\ngit commit -F m", True),
        ("cat > m <<'EOF'\ngit commit -m 'not this one'\nEOF\ngit push origin master", True),
        # The MISS direction, across terminator spellings. This predicate now decides whether a
        # BLOCKING gate runs, so over-stripping would swallow the trailing verb and the gate would
        # silently not fire on a real commit - the failure that looks exactly like a healthy guard.
        ("cat > m <<EOF\nsubject\nEOF\ngit commit -F m", True),                 # unquoted
        ('cat > m <<"EOF"\nsubject\nEOF\ngit commit -F m', True),               # double-quoted
        ("cat > m <<-EOF\n\tsubject\n\tEOF\ngit commit -F m", True),            # dash form, tabs
        ("cat > m <<'MSGEOF'\nsubject\nMSGEOF\ngit commit -F m", True),         # custom word
        ("cat > m <<'EOF'\nsay EOF here\nEOF\ngit commit -F m", True),          # word inline in body
        ("cat > a <<'EOF'\nx\nEOF\ncat > b <<'EOF'\ny\nEOF\ngit commit -F a", True),   # two bodies
        ("cat > m <<'EOF'\nx\nEOF\nls && git commit -F m", True),               # verb after a chain
        # An UNTERMINATED heredoc consumes the rest of the input, so the trailing line is data the
        # shell never runs. Not gating it is the guard agreeing with the shell, not a miss.
        ("cat > m <<'EOF'\ngit commit -F m", False),
    ],
)
def test_is_gated_command(cmd, expected):
    assert RG.is_gated_command(cmd) is expected


# --------------------------------------------------------------------------
# is_bitranox_skills
# --------------------------------------------------------------------------


def test_is_bitranox_skills_true(tmp_path):
    make_repo(tmp_path)
    assert RG.is_bitranox_skills(tmp_path) is True


def test_is_bitranox_skills_wrong_name(tmp_path):
    write(tmp_path / "plugins/bitranox/.claude-plugin/plugin.json", json.dumps({"name": "other"}))
    assert RG.is_bitranox_skills(tmp_path) is False


def test_is_bitranox_skills_absent(tmp_path):
    assert RG.is_bitranox_skills(tmp_path) is False


# --------------------------------------------------------------------------
# check_tests_exist
# --------------------------------------------------------------------------


def test_tests_exist_all_good(tmp_path):
    make_repo(tmp_path, good_skill=True)
    assert RG.check_tests_exist(tmp_path) == []


def test_tests_exist_flags_untested_package(tmp_path):
    make_repo(tmp_path, bad_skill=True)
    failures = RG.check_tests_exist(tmp_path)
    assert any("skills/bad" in line for line in failures)


def test_tests_exist_exempts_demo_only_package(tmp_path):
    make_repo(tmp_path, demo_only=True)
    failures = RG.check_tests_exist(tmp_path)
    assert not any("demoskill" in line for line in failures)


# --------------------------------------------------------------------------
# check_json_valid
# --------------------------------------------------------------------------


def test_json_valid_passes(tmp_path):
    make_repo(tmp_path)
    assert RG.check_json_valid(tmp_path) == []


def test_json_valid_flags_broken_plugin_json(tmp_path):
    make_repo(tmp_path)
    write(tmp_path / "plugins/bitranox/.claude-plugin/plugin.json", '{"name": "bitranox",}')  # trailing comma
    failures = RG.check_json_valid(tmp_path)
    assert any("plugin.json" in line for line in failures)


# --------------------------------------------------------------------------
# git-dependent checks self-skip outside a git repo
# --------------------------------------------------------------------------


def test_lf_and_version_skip_without_git(tmp_path):
    make_repo(tmp_path)
    assert RG.check_lf_endings(tmp_path) == []
    assert RG.check_version_bumped(tmp_path) == []


def test_version_bump_enforced_in_hook_mode_only(tmp_path, monkeypatch):
    # version-bump is a maintainer pre-commit concern, never a CI/PR gate.
    make_repo(tmp_path)
    monkeypatch.setattr(RG, "check_version_bumped", lambda root: ["VERSION_SENTINEL"])
    monkeypatch.setattr(RG, "check_pytest", lambda root, paths, **kw: [])
    assert "VERSION_SENTINEL" in RG.run_checks(tmp_path, ci=False)
    assert "VERSION_SENTINEL" not in RG.run_checks(tmp_path, ci=True)


# --------------------------------------------------------------------------
# main(): repo-guard, hook gating, block path
# --------------------------------------------------------------------------


def test_main_noop_in_other_repo(tmp_path, monkeypatch):
    # Hook mode in a repo that is NOT bitranox-skills must exit 0 and never block.
    monkeypatch.setattr(RG, "repo_root", lambda: tmp_path)  # tmp_path has no plugin.json
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"tool_input": {"command": "git commit -m x"}})))
    assert RG.main() == 0


def test_main_ci_errors_in_other_repo(tmp_path, monkeypatch):
    monkeypatch.setattr(RG, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(sys, "argv", ["repo-gate.py", "--ci"])
    assert RG.main() == 1


def test_main_hook_ignores_non_commit_command(tmp_path, monkeypatch):
    make_repo(tmp_path, bad_skill=True)  # would fail checks IF they ran
    monkeypatch.setattr(RG, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"tool_input": {"command": "git status"}})))
    assert RG.main() == 0  # not a commit -> checks never run


def test_main_hook_blocks_commit_on_violation(tmp_path, monkeypatch, capsys):
    make_repo(tmp_path, bad_skill=True)
    monkeypatch.setattr(RG, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(RG, "check_pytest", lambda root, paths, **kw: [])  # don't run real pytest
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"tool_input": {"command": "git commit -m x"}})))
    assert RG.main() == 2
    assert "blocked" in capsys.readouterr().err


def test_main_hook_allows_clean_commit(tmp_path, monkeypatch):
    make_repo(tmp_path, good_skill=True)
    monkeypatch.setattr(RG, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(RG, "check_pytest", lambda root, paths, **kw: [])
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"tool_input": {"command": "git commit -m x"}})))
    assert RG.main() == 0


def test_main_hook_blocks_push_on_violation(tmp_path, monkeypatch, capsys):
    # a push is gated too: it is the moment the change reaches CI, so a violation must block it
    make_repo(tmp_path, bad_skill=True)
    monkeypatch.setattr(RG, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(RG, "check_pytest", lambda root, paths, **kw: [])
    monkeypatch.setattr(sys, "stdin",
                        io.StringIO(json.dumps({"tool_input": {"command": "git push origin master"}})))
    assert RG.main() == 2
    assert "blocked" in capsys.readouterr().err


def test_pre_push_mode_needs_no_stdin_event(tmp_path, monkeypatch):
    # A real git pre-push hook is handed REF LINES on stdin, not a Claude Code event JSON. Reading
    # it as JSON fails and the old hook path returns 0, so the gate would pass by accident on the
    # one caller that fires outside Claude Code.
    make_repo(tmp_path, bad_skill=True)
    monkeypatch.setattr(RG, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(RG, "check_pytest", lambda root, paths, **kw: [])
    monkeypatch.setattr(sys, "argv", ["repo-gate.py", "--pre-push"])
    monkeypatch.setattr(sys, "stdin", io.StringIO("refs/heads/master abc refs/heads/master def\n"))
    assert RG.main() == 1                       # a hook exit code, not the PreToolUse 2


def test_pre_push_mode_passes_a_clean_tree(tmp_path, monkeypatch):
    make_repo(tmp_path, good_skill=True)
    monkeypatch.setattr(RG, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(RG, "check_pytest", lambda root, paths, **kw: [])
    monkeypatch.setattr(sys, "argv", ["repo-gate.py", "--pre-push"])
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))
    assert RG.main() == 0


def test_pre_push_blocks_a_tree_whose_version_has_no_entry(tmp_path, monkeypatch, capsys):
    """End to end through main(), not just the check in isolation.

    The sibling above proves a clean tree passes; without this one, nothing proves the changelog
    check is REACHED by the pre-push path rather than merely defined. It also gives make_repo's
    changelog=False a caller - an unused knob is a knob nobody has run.
    """
    make_repo(tmp_path, good_skill=True, changelog=False)
    monkeypatch.setattr(RG, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(RG, "check_pytest", lambda root, paths, **kw: [])
    monkeypatch.setattr(sys, "argv", ["repo-gate.py", "--pre-push"])
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))
    assert RG.main() != 0
    assert "1.6.0" in capsys.readouterr().err


def test_pre_push_runs_pytest_over_the_whole_repo(tmp_path, monkeypatch):
    # The stale-catalog test lives in hooks/tests, but a pre-push is the last gate before CI, so it
    # runs what CI runs. Recording the paths proves the widened scope rather than assuming it.
    make_repo(tmp_path, good_skill=True)
    seen = []
    monkeypatch.setattr(RG, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(RG, "check_pytest", lambda root, paths, **kw: seen.append(list(paths)) or [])
    monkeypatch.setattr(sys, "argv", ["repo-gate.py", "--pre-push"])
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))
    RG.main()
    assert seen == [[tmp_path]]                 # whole repo, not just hooks/tests


def test_pre_push_keeps_the_maintainer_only_checks(tmp_path, monkeypatch):
    # version-bump is skipped in CI (a contributor must not be forced to bump) but a pre-push IS
    # the maintainer, and a missing bump is exactly what makes a shipped change reach nobody.
    monkeypatch.setattr(RG, "check_version_bumped", lambda root: ["VERSION_SENTINEL"])
    monkeypatch.setattr(RG, "check_pytest", lambda root, paths, **kw: [])
    assert "VERSION_SENTINEL" in RG.run_checks(tmp_path, ci=False, full_pytest=True)


def test_the_tracked_pre_push_hook_is_executable_and_lf():
    # core.fileMode is false on this tree, so an exec bit set with chmod is NOT recorded and the
    # hook installs unrunnable - git silently skips a non-executable hook. The INDEX mode is the
    # only real answer, and a CRLF hook dies on its shebang.
    root = Path(RG.__file__).resolve().parents[3]
    hook = root / "githooks" / "pre-push"
    assert hook.is_file(), "githooks/pre-push is missing"
    # Assert on HEAD, not on the index. `git commit -- <pathspec>` re-stages the WORKING TREE
    # version, and with core.fileMode=false a newly added path is recorded 100644 whatever the
    # index held - measured here, where the index read 100755 and the commit still shipped 100644.
    # An index-only assertion passes while the clone gets a hook git silently skips.
    mode = subprocess.run(["git", "-C", str(root), "ls-tree", "HEAD", "githooks/pre-push"],
                          capture_output=True, text=True, encoding="utf-8").stdout
    assert mode.startswith("100755"), "githooks/pre-push is not executable in HEAD: " + mode
    assert b"\r\n" not in hook.read_bytes()


@pytest.mark.skipif(os.name == "nt", reason="a bash hook; bare `bash` on Windows is the WSL stub")
def test_the_pre_push_hook_hands_the_gate_no_git_environment(tmp_path):
    """A push FROM A LINKED WORKTREE hands the hook GIT_DIR, and this hook's gate runs the suite.

    Those tests build fixtures with `git init` / `git add` / `git commit` in a temp directory, and
    git reads GIT_DIR before it considers cwd - so each of them writes to THIS repository instead.
    Measured 2026-08-31: such a push put fixture commits titled "base" on the worktree's branch,
    moved refs/remotes/origin/master onto one, and set core.bare, after which `git status` refused
    to run in the main checkout. Every git call exited 0, so nothing announced it.

    The worktree is the trigger: on git 2.53.0 a push from an ordinary checkout exports no GIT_DIR,
    with or without core.hooksPath, while both worktree arms exported it. This test sets the
    variables itself instead of staging a worktree push, so it pins what the hook must GUARANTEE
    however the push was made.

    The gate is stubbed and `uv` hidden from PATH, which forces the python3 branch: this asserts
    the ENVIRONMENT handed over, not which interpreter runs.
    """
    root = Path(RG.__file__).resolve().parents[3]
    repo = tmp_path / "repo"
    (repo / "plugins/bitranox/hooks").mkdir(parents=True)
    shutil.copy(root / "githooks" / "pre-push", repo / "pre-push")
    seen = tmp_path / "seen.txt"
    (repo / "plugins/bitranox/hooks/repo-gate.py").write_text(
        "import os\n"
        f"open({str(seen)!r}, 'w', encoding='utf-8').write("
        "'\\n'.join(sorted(k for k in os.environ if k.startswith('GIT_'))))\n",
        encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)

    # PATH is replaced rather than prepended, because hiding uv is the point; git and python3 are
    # linked in so the hook can still resolve the root and run the stub.
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for tool in ("git", "python3"):
        os.symlink(shutil.which(tool), bin_dir / tool)
    env = {**os.environ, "PATH": str(bin_dir),
           "GIT_DIR": str(repo / ".git"), "GIT_INDEX_FILE": str(repo / ".git" / "index"),
           "GIT_PREFIX": "", "GIT_QUARANTINE_PATH": str(tmp_path / "quarantine")}
    subprocess.run([shutil.which("bash"), str(repo / "pre-push")], cwd=repo, env=env, check=True,
                   capture_output=True, text=True, encoding="utf-8", errors="replace")

    # Only the variables that POINT AT A REPOSITORY matter. An unrelated name merely starting with
    # GIT_ (a local guard's own config, say) is not a leak, and asserting on the prefix made this
    # test fail on one.
    repo_scoping = {"GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY",
                    "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_COMMON_DIR", "GIT_NAMESPACE",
                    "GIT_PREFIX", "GIT_QUARANTINE_PATH"}
    handed_over = set(seen.read_text(encoding="utf-8").split())
    leaked = sorted(handed_over & repo_scoping)
    assert leaked == [], "the gate was handed a repository: " + ", ".join(leaked)


def test_main_malformed_stdin_passes(tmp_path, monkeypatch):
    make_repo(tmp_path)
    monkeypatch.setattr(RG, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(sys, "stdin", io.StringIO("not json"))
    assert RG.main() == 0


# --------------------------------------------------------------------------
# check_skills_index (meta-using-bitranox-skills domains list <-> skill dirs)
# --------------------------------------------------------------------------

INDEX_TEMPLATE = """---
name: meta-using-bitranox-skills
---

## Skills Span Every Domain, Not Just Process

intro paragraph, not a bullet.

- **Process:** {names}

caveat paragraph mentioning `not-a-bullet-name` which must be ignored.

## Skill Types

other content
"""


def make_skills(root, names):
    for n in names:
        write(root / f"plugins/bitranox/skills/{n}/SKILL.md", f"---\nname: {n}\n---\n")


def make_index(root, listed):
    names = ", ".join(f"`{n}`" for n in listed)
    write(root / "plugins/bitranox/skills/meta-using-bitranox-skills/SKILL.md",
          INDEX_TEMPLATE.format(names=names))


def test_skills_index_in_sync(tmp_path):
    make_skills(tmp_path, ["alpha", "beta"])
    make_index(tmp_path, ["alpha", "beta"])
    assert RG.check_skills_index(tmp_path) == []


def test_skills_index_unlisted_skill_is_fine(tmp_path):
    # the roster is categories + exemplars; completeness comes from the available-skills list,
    # so an unlisted skill is deliberately NOT a failure (only stale names are)
    make_skills(tmp_path, ["alpha", "beta", "gamma"])
    make_index(tmp_path, ["alpha", "beta"])  # gamma not listed
    assert RG.check_skills_index(tmp_path) == []


def test_skills_index_flags_stale_entry(tmp_path):
    make_skills(tmp_path, ["alpha"])
    make_index(tmp_path, ["alpha", "ghost"])  # ghost has no dir
    fails = RG.check_skills_index(tmp_path)
    assert any("ghost" in f and "non-existent" in f for f in fails)


def test_skills_index_ignores_itself_and_non_bullet_names(tmp_path):
    # meta-using-bitranox-skills need not list itself; names outside the bullets (the caveat
    # paragraph's `not-a-bullet-name`) must not be treated as listed skills.
    make_skills(tmp_path, ["alpha"])
    make_index(tmp_path, ["alpha"])
    assert RG.check_skills_index(tmp_path) == []


# --------------------------------------------------------------------------
# check_attribution (credit line <-> THIRD_PARTY_NOTICES.md sync)
# --------------------------------------------------------------------------


def credited_skill(root, name):
    write(root / f"plugins/bitranox/skills/{name}/SKILL.md",
          f"---\nname: {name}\n---\n\n# {name}\n\n> Adapted from upstream x (MIT).\n")


def notices(root, names):
    body = "# Third-Party Notices\n" + "".join(f"\n---\n\n### {n}\n\n- License: MIT\n" for n in names)
    write(root / "plugins/bitranox/THIRD_PARTY_NOTICES.md", body)


def test_attribution_in_sync(tmp_path):
    credited_skill(tmp_path, "alpha")
    notices(tmp_path, ["alpha"])
    assert RG.check_attribution(tmp_path) == []


def test_attribution_credit_without_notice_blocks(tmp_path):
    credited_skill(tmp_path, "alpha")
    notices(tmp_path, [])  # notices file exists but has no entry
    fails = RG.check_attribution(tmp_path)
    assert any("alpha" in f and "no THIRD_PARTY_NOTICES" in f for f in fails)


def test_attribution_credit_with_no_notices_file_blocks(tmp_path):
    credited_skill(tmp_path, "alpha")  # no notices file at all
    fails = RG.check_attribution(tmp_path)
    assert any("alpha" in f for f in fails)


def test_attribution_orphan_notice_blocks(tmp_path):
    make_skills(tmp_path, ["alpha"])  # plain skill, no credit line
    notices(tmp_path, ["alpha"])
    fails = RG.check_attribution(tmp_path)
    assert any("alpha" in f and "no matching" in f for f in fails)


def test_attribution_no_credits_no_notices_passes(tmp_path):
    make_skills(tmp_path, ["alpha", "beta"])
    assert RG.check_attribution(tmp_path) == []


# --------------------------------------------------------------------------
# check_skill_naming (category-prefix scheme)
# --------------------------------------------------------------------------


def make_taxonomy(root, categories, legacy=()):
    write(root / "plugins/bitranox/skill-taxonomy.json",
          json.dumps({"categories": {c: {"subs": []} for c in categories}, "legacy": list(legacy)}))


def test_naming_accepts_valid_prefix(tmp_path):
    make_skills(tmp_path, ["coding-python-foo"])
    make_taxonomy(tmp_path, ["coding", "files"])
    assert RG.check_skill_naming(tmp_path) == []


def test_naming_rejects_unprefixed(tmp_path):
    make_skills(tmp_path, ["foobar"])
    make_taxonomy(tmp_path, ["coding"])
    assert any("foobar" in f for f in RG.check_skill_naming(tmp_path))


def test_naming_rejects_unknown_prefix(tmp_path):
    make_skills(tmp_path, ["zzz-foo"])
    make_taxonomy(tmp_path, ["coding"])
    assert any("zzz-foo" in f for f in RG.check_skill_naming(tmp_path))


def test_naming_grandfathers_legacy(tmp_path):
    make_skills(tmp_path, ["rory"])
    make_taxonomy(tmp_path, ["coding"], legacy=["rory"])
    assert RG.check_skill_naming(tmp_path) == []


def test_naming_skipped_when_no_taxonomy(tmp_path):
    make_skills(tmp_path, ["foobar"])  # no skill-taxonomy.json -> fail-open
    assert RG.check_skill_naming(tmp_path) == []


# --------------------------------------------------------------------------
# check_secrets (credentials / private keys / sensitive files / infra denylist)
# Tokens are built via concatenation so the literal patterns are NOT present in this
# test file (else the gate would flag this file when scanning the real repo).
# --------------------------------------------------------------------------

GH_TOKEN = "ghp_" + "A" * 36
# Long JWT-format installation token: ghs_ + three dot-separated base64url segments.
GHS_TOKEN = "ghs_" + ".".join(["A" * 40, "B" * 40, "C" * 40])
AWS_KEY = "AKIA" + "ABCDEFGHIJ123456"


def git_repo(tmp_path, files):
    for rel, content in files.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    return tmp_path


def test_secrets_clean_repo(tmp_path):
    git_repo(tmp_path, {"skills/x/SKILL.md": "just docs, host media.example.com, ip 192.0.2.10\n"})
    assert RG.check_secrets(tmp_path) == []


def test_secrets_detects_github_token(tmp_path):
    git_repo(tmp_path, {"a.md": f"token = {GH_TOKEN}\n"})
    assert any("GitHub token" in f for f in RG.check_secrets(tmp_path))


def test_secrets_detects_github_app_installation_token(tmp_path):
    git_repo(tmp_path, {"a.md": f"token = {GHS_TOKEN}\n"})
    assert any("GitHub App installation token" in f for f in RG.check_secrets(tmp_path))


def test_secrets_detects_aws_key(tmp_path):
    git_repo(tmp_path, {"a.md": f"key={AWS_KEY}\n"})
    assert any("AWS" in f for f in RG.check_secrets(tmp_path))


def test_secrets_detects_complete_private_key(tmp_path):
    body = "\n".join(["A" * 64] * 5)  # real-looking base64, no "..." truncation
    pem = f"-----BEGIN RSA PRIVATE KEY-----\n{body}\n-----END RSA PRIVATE KEY-----\n"
    git_repo(tmp_path, {"a.md": pem})
    assert any("private key" in f for f in RG.check_secrets(tmp_path))


def test_secrets_ignores_truncated_private_key(tmp_path):
    # Illustrative/elided key (like the rpyc tutorial) must NOT trip the gate.
    pem = "'-----BEGIN RSA PRIVATE KEY-----\\nMIIJKQ...XuVmz\\n-----END RSA PRIVATE KEY-----\\n'"
    git_repo(tmp_path, {"tutorial.md": pem})
    assert not any("private key" in f for f in RG.check_secrets(tmp_path))


def test_secrets_detects_sensitive_filename(tmp_path):
    git_repo(tmp_path, {".env": "X=1\n"})
    assert any(".env" in f and "sensitive filename" in f for f in RG.check_secrets(tmp_path))


def test_secrets_denylist_local_only(tmp_path):
    git_repo(tmp_path, {"a.md": "deploy to acmeinternal-host-host now\n"})
    # No denylist file present -> the term is not flagged.
    assert not any("denylisted" in f for f in RG.check_secrets(tmp_path))
    # An untracked local denylist file makes the gate catch it (file itself stays untracked).
    (tmp_path / ".security-denylist.local").write_text("acmeinternal-host\n", encoding="utf-8")
    assert any("denylisted" in f and "acmeinternal-host" in f for f in RG.check_secrets(tmp_path))


# --------------------------------------------------------------------------
# skill review artifact + CSO description lint (skill-usage enforcement)
# --------------------------------------------------------------------------

def _skill(root, name, desc, checklist=None, checked=True):
    write(root / f"plugins/bitranox/skills/{name}/SKILL.md",
          "---\nname: %s\ndescription: %s\n---\n\n# %s\n" % (name, desc, name))
    if checklist:
        box = "[x]" if checked else "[ ]"
        write(root / f"plugins/bitranox/skills/{name}/.skillwriter/{checklist}",
              "# checklist\n- %s RED baseline\n- %s pressure scenarios\n" % (box, box))


def test_skill_review_requires_cochanged_checklist(tmp_path):
    make_repo(tmp_path)
    _skill(tmp_path, "alpha", "Use when testing alpha widgets fail")
    changed = ["plugins/bitranox/skills/alpha/SKILL.md"]
    fails = RG.skill_review_failures(tmp_path, changed)
    assert fails and "checklist" in fails[0]
    # co-changed artifact with all boxes checked -> clean
    _skill(tmp_path, "alpha", "Use when testing alpha widgets fail",
           checklist="checklist-20260706.md")
    changed += ["plugins/bitranox/skills/alpha/.skillwriter/checklist-20260706.md"]
    assert RG.skill_review_failures(tmp_path, changed) == []


def test_skill_review_rejects_unchecked_boxes(tmp_path):
    make_repo(tmp_path)
    _skill(tmp_path, "beta", "Use when beta gadgets misbehave under load",
           checklist="checklist-20260706.md", checked=False)
    changed = ["plugins/bitranox/skills/beta/SKILL.md",
               "plugins/bitranox/skills/beta/.skillwriter/checklist-20260706.md"]
    fails = RG.skill_review_failures(tmp_path, changed)
    assert fails and "unchecked" in fails[0]


def test_frontmatter_gate_sweeps_skills_the_change_never_touched(tmp_path):
    """Changed-only would reproduce the blind spot this check exists to close: the defects that
    prompted it survived precisely because nothing ever swept the whole set."""
    make_repo(tmp_path)
    _skill(tmp_path, "iota", "Use when hitting a recurring chore: finding a process and paths")
    fails = RG.check_frontmatter(tmp_path)            # the real entry point, no changed-list
    assert any("iota" in f for f in fails)


def test_frontmatter_gate_blocks_a_colon_that_breaks_the_yaml(tmp_path):
    """The commit gate must see what `cso_failures` cannot: the CSO rules read a description
    the regex recovered, so an invalid block passes them while a parser rejects the file."""
    make_repo(tmp_path)
    _skill(tmp_path, "zeta", "Use when hitting a recurring chore: finding a process and paths")
    changed = ["plugins/bitranox/skills/zeta/SKILL.md"]
    assert RG.cso_failures(tmp_path, changed) == []          # the old gate is blind to it
    fails = RG.frontmatter_failures(tmp_path)
    # Both routes fire: the parser rejects the block, and the stdlib colon rule names the key.
    assert any("the YAML parser rejects" in f for f in fails)
    assert any("not valid YAML" in f for f in fails)


def test_frontmatter_gate_blocks_a_second_front_matter(tmp_path):
    make_repo(tmp_path)
    _skill(tmp_path, "eta", "Use when gadget builds fail with linker errors on windows runners")
    md = tmp_path / "plugins/bitranox/skills/eta/SKILL.md"
    md.write_text(md.read_text(encoding="utf-8")
                  + "\n---\nname: smuggled\ndescription: A divergent description.\n---\n",
                  encoding="utf-8")
    fails = RG.frontmatter_failures(tmp_path)
    assert fails and "second front matter" in fails[0]


def test_frontmatter_gate_is_quiet_for_a_good_skill(tmp_path):
    make_repo(tmp_path)
    _skill(tmp_path, "theta", "Use when gadget builds fail with linker errors on windows runners")
    assert RG.frontmatter_failures(tmp_path) == []


def test_frontmatter_gate_is_quiet_when_the_repo_ships_no_skills(tmp_path):
    make_repo(tmp_path)
    assert RG.frontmatter_failures(tmp_path) == []


def test_cso_lint_requires_trigger_first_description(tmp_path):
    make_repo(tmp_path)
    _skill(tmp_path, "gamma", "Consolidates the store and prunes entries nightly")
    fails = RG.cso_failures(tmp_path, ["plugins/bitranox/skills/gamma/SKILL.md"])
    assert fails and "Use when" in fails[0]
    _skill(tmp_path, "delta", "Use when gadget builds fail with linker errors on windows runners")
    assert RG.cso_failures(tmp_path, ["plugins/bitranox/skills/delta/SKILL.md"]) == []


def test_cso_lint_requires_derivable_keywords(tmp_path):
    make_repo(tmp_path)
    _skill(tmp_path, "epsilon", "Use when it is good to do so")   # no distinctive keywords
    fails = RG.cso_failures(tmp_path, ["plugins/bitranox/skills/epsilon/SKILL.md"])
    assert fails and "keyword" in fails[0]


def test_cso_lint_rejects_block_scalar_and_quoted_descriptions(tmp_path):
    # a `>-` block scalar and a quoted scalar both leak artifacts into the derived
    # catalog/router - the lint must name the scalar style, not misdiagnose trigger-first
    make_repo(tmp_path)
    d = tmp_path / "plugins/bitranox/skills/zeta"
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text(
        "---\nname: zeta\ndescription: >-\n  Use when zeta widgets explode under pressure loads\n---\n\n# z\n",
        encoding="utf-8")
    fails = RG.cso_failures(tmp_path, ["plugins/bitranox/skills/zeta/SKILL.md"])
    assert fails and "plain" in fails[0] and "scalar" in fails[0]

    _skill(tmp_path, "eta", '"Use when eta gadgets rust in coastal climates"')
    fails = RG.cso_failures(tmp_path, ["plugins/bitranox/skills/eta/SKILL.md"])
    assert fails and "plain" in fails[0] and "scalar" in fails[0]


# --------------------------------------------------------------------------
# Mirrored skills: a skill that also ships from its own tool repo
# --------------------------------------------------------------------------


MIRROR_BODY = """---
name: coding-python-thing
description: Use when doing the thing.
---

# Doing the thing (coding-python-thing)

One paragraph of content.
"""

TWIN_BODY = """---
name: python-thing
description: Use when doing the thing.
---

# Doing the thing (python-thing)

> The `thing` repo is itself a Claude Code plugin/marketplace. Install this skill
> anywhere with `/plugin marketplace add bitranox/thing` then `/plugin install thing`.
> It is also mirrored in the central bitranox marketplace as `coding-python-thing`.

One paragraph of content.
"""


def test_the_name_line_the_h1_and_the_self_install_note_are_not_drift():
    # Each copy uses its own repo's skill name in both places, and only the tool repo's
    # copy tells the reader to add that marketplace. Reporting those would make the
    # check cry wolf on every pair, every time.
    assert RG.normalise_mirror(MIRROR_BODY) == RG.normalise_mirror(TWIN_BODY)


def test_a_multi_line_self_install_blockquote_is_dropped_whole():
    # A line-at-a-time rule leaves the continuation lines behind and reports them as
    # drift; this is the shape that actually ships in igittigitt and btx_lib_mail.
    normalised = RG.normalise_mirror(TWIN_BODY)

    assert "marketplace add" not in normalised
    assert "mirrored in the central" not in normalised
    assert "One paragraph of content." in normalised


def test_a_blockquote_that_is_not_the_self_install_note_is_kept() -> None:
    quoted = TWIN_BODY.replace("> The `thing` repo", "> A quote worth keeping").replace(
        "> anywhere with `/plugin marketplace add bitranox/thing` then `/plugin install thing`.\n", ""
    ).replace("> It is also mirrored in the central bitranox marketplace as `coding-python-thing`.\n", "")

    assert "A quote worth keeping" in RG.normalise_mirror(quoted)


def test_changed_content_is_reported_as_drift(tmp_path, monkeypatch):
    public = tmp_path / "public"
    root = public / "KI" / "bitranox-skills"
    write(root / "plugins" / "bitranox" / "skills" / "coding-python-thing" / "SKILL.md", MIRROR_BODY)
    write(public / "libs" / "thing" / "skills" / "python-thing" / "SKILL.md", TWIN_BODY.replace("One paragraph", "A DIFFERENT paragraph"))
    monkeypatch.setitem(RG.MIRRORED_SKILLS, "coding-python-thing", "libs/thing/skills/python-thing")

    fails = RG.mirror_failures(root, {"coding-python-thing"})

    assert len(fails) == 1
    assert "libs/thing/skills/python-thing" in fails[0]
    assert "DIFFERENT" in fails[0]


def test_an_identical_pair_reports_nothing(tmp_path, monkeypatch):
    public = tmp_path / "public"
    root = public / "KI" / "bitranox-skills"
    write(root / "plugins" / "bitranox" / "skills" / "coding-python-thing" / "SKILL.md", MIRROR_BODY)
    write(public / "libs" / "thing" / "skills" / "python-thing" / "SKILL.md", TWIN_BODY)
    monkeypatch.setitem(RG.MIRRORED_SKILLS, "coding-python-thing", "libs/thing/skills/python-thing")

    assert RG.mirror_failures(root, {"coding-python-thing"}) == []


def test_a_drifted_reference_file_is_reported(tmp_path, monkeypatch):
    """A mirrored skill is a DIRECTORY, and several pairs ship references/ or scripts/.

    Comparing only SKILL.md let three changed files in one pair sit unreported while the gate
    printed "in sync" - the worst shape a check can have, because the answer is the one you wanted.
    """
    public = tmp_path / "public"
    root = public / "KI" / "bitranox-skills"
    write(root / "plugins" / "bitranox" / "skills" / "coding-python-thing" / "SKILL.md", MIRROR_BODY)
    write(root / "plugins" / "bitranox" / "skills" / "coding-python-thing" / "references" / "api.md", "one\n")
    write(public / "libs" / "thing" / "skills" / "python-thing" / "SKILL.md", TWIN_BODY)
    write(public / "libs" / "thing" / "skills" / "python-thing" / "references" / "api.md", "TWO\n")
    monkeypatch.setitem(RG.MIRRORED_SKILLS, "coding-python-thing", "libs/thing/skills/python-thing")

    fails = RG.mirror_failures(root, {"coding-python-thing"})

    assert len(fails) == 1
    assert "references/api.md" in fails[0]


def test_a_file_present_on_only_one_side_is_reported(tmp_path, monkeypatch):
    public = tmp_path / "public"
    root = public / "KI" / "bitranox-skills"
    write(root / "plugins" / "bitranox" / "skills" / "coding-python-thing" / "SKILL.md", MIRROR_BODY)
    write(root / "plugins" / "bitranox" / "skills" / "coding-python-thing" / "scripts" / "tool.py", "print(1)\n")
    write(public / "libs" / "thing" / "skills" / "python-thing" / "SKILL.md", TWIN_BODY)
    monkeypatch.setitem(RG.MIRRORED_SKILLS, "coding-python-thing", "libs/thing/skills/python-thing")

    fails = RG.mirror_failures(root, {"coding-python-thing"})

    assert len(fails) == 1
    assert "scripts/tool.py" in fails[0]


def test_the_skillwriter_artifact_and_pycache_are_not_compared(tmp_path, monkeypatch):
    """The review artifact is the marketplace's own commit receipt and never ships to the twin;
    __pycache__ is build output. Comparing either would fail every pair permanently."""
    public = tmp_path / "public"
    root = public / "KI" / "bitranox-skills"
    here = root / "plugins" / "bitranox" / "skills" / "coding-python-thing"
    write(here / "SKILL.md", MIRROR_BODY)
    write(here / ".skillwriter" / "checklist-20260101.md", "- [x] done\n")
    write(here / "scripts" / "__pycache__" / "tool.cpython-313.pyc", "bytes\n")
    write(here / ".pytest_cache" / "v" / "cache" / "lastfailed", "{}\n")
    write(here / ".ruff_cache" / "0.14.0" / "blob", "bytes\n")
    write(public / "libs" / "thing" / "skills" / "python-thing" / "SKILL.md", TWIN_BODY)
    monkeypatch.setitem(RG.MIRRORED_SKILLS, "coding-python-thing", "libs/thing/skills/python-thing")

    assert RG.mirror_failures(root, {"coding-python-thing"}) == []


def test_an_identical_directory_pair_reports_nothing(tmp_path, monkeypatch):
    public = tmp_path / "public"
    root = public / "KI" / "bitranox-skills"
    write(root / "plugins" / "bitranox" / "skills" / "coding-python-thing" / "SKILL.md", MIRROR_BODY)
    write(root / "plugins" / "bitranox" / "skills" / "coding-python-thing" / "references" / "api.md", "same\n")
    write(public / "libs" / "thing" / "skills" / "python-thing" / "SKILL.md", TWIN_BODY)
    write(public / "libs" / "thing" / "skills" / "python-thing" / "references" / "api.md", "same\n")
    monkeypatch.setitem(RG.MIRRORED_SKILLS, "coding-python-thing", "libs/thing/skills/python-thing")

    assert RG.mirror_failures(root, {"coding-python-thing"}) == []


def test_a_twin_that_is_not_checked_out_is_skipped_not_failed(tmp_path, monkeypatch):
    # Another machine has the marketplace without the tool repos. Failing there would
    # block every commit for a contributor who cannot possibly fix it.
    public = tmp_path / "public"
    root = public / "KI" / "bitranox-skills"
    write(root / "plugins" / "bitranox" / "skills" / "coding-python-thing" / "SKILL.md", MIRROR_BODY)
    monkeypatch.setitem(RG.MIRRORED_SKILLS, "coding-python-thing", "libs/absent/skills/python-thing")

    assert RG.mirror_failures(root, {"coding-python-thing"}) == []


def test_no_public_tree_means_no_comparison(tmp_path):
    root = tmp_path / "elsewhere" / "bitranox-skills"
    write(root / "plugins" / "bitranox" / "skills" / "coding-python-thing" / "SKILL.md", MIRROR_BODY)

    assert RG.mirror_failures(root, set(RG.MIRRORED_SKILLS)) == []


def test_every_mirrored_entry_names_a_real_marketplace_skill():
    # A manifest key that no longer matches a skill dir would silently stop checking that
    # pair - the exact rot this check exists to catch.
    here = Path(RG.__file__).resolve().parent.parent / "skills"
    missing = [name for name in RG.MIRRORED_SKILLS if not (here / name / "SKILL.md").is_file()]

    assert missing == [], "MIRRORED_SKILLS names a skill that does not exist: %s" % missing


def _mirror_tree(tmp_path, twin_body=TWIN_BODY):
    """A public/ tree with the marketplace and one tool repo that mirrors a skill."""
    public = tmp_path / "public"
    write(public / "KI" / "bitranox-skills" / "plugins" / "bitranox" / "skills" / "coding-python-thing" / "SKILL.md", MIRROR_BODY)
    write(public / "libs" / "thing" / "skills" / "python-thing" / "SKILL.md", twin_body)
    return public


def test_mirror_of_reports_in_sync_for_the_repo_it_is_run_in(tmp_path, monkeypatch, capsys):
    public = _mirror_tree(tmp_path)
    monkeypatch.setitem(RG.MIRRORED_SKILLS, "coding-python-thing", "libs/thing/skills/python-thing")

    rc = RG.audit_mirror_of(public / "libs" / "thing")

    assert rc == 0
    assert "in sync" in capsys.readouterr().out


def test_mirror_of_fails_on_drift_in_the_repo_it_is_run_in(tmp_path, monkeypatch, capsys):
    public = _mirror_tree(tmp_path, TWIN_BODY.replace("One paragraph", "A DIFFERENT paragraph"))
    monkeypatch.setitem(RG.MIRRORED_SKILLS, "coding-python-thing", "libs/thing/skills/python-thing")

    rc = RG.audit_mirror_of(public / "libs" / "thing")
    out = capsys.readouterr().out

    assert rc == 1
    assert "DRIFT" in out and "DIFFERENT" in out


def test_mirror_of_is_silent_and_green_where_there_is_nothing_to_compare(tmp_path, monkeypatch, capsys):
    # A release pipeline runs this in EVERY repo, so the three "not applicable" cases
    # must pass rather than block: no mirrored skill here, no marketplace checkout, no
    # public/ tree at all.
    public = _mirror_tree(tmp_path)
    monkeypatch.setitem(RG.MIRRORED_SKILLS, "coding-python-thing", "libs/thing/skills/python-thing")
    (public / "libs" / "other").mkdir(parents=True)

    assert RG.audit_mirror_of(public / "libs" / "other") == 0
    assert "ships no skill mirrored" in capsys.readouterr().out

    bare = tmp_path / "public" / "libs" / "thing"
    monkeypatch.setitem(RG.MIRRORED_SKILLS, "coding-python-thing", "libs/thing/skills/python-thing")
    import shutil

    shutil.rmtree(public / "KI")
    assert RG.audit_mirror_of(bare) == 0
    assert "no bitranox-skills checkout" in capsys.readouterr().out

    assert RG.audit_mirror_of(tmp_path / "nowhere") == 0
    assert "no public/ tree" in capsys.readouterr().out


def test_mirror_of_dispatches_from_the_command_line(tmp_path, monkeypatch):
    public = _mirror_tree(tmp_path)
    monkeypatch.setitem(RG.MIRRORED_SKILLS, "coding-python-thing", "libs/thing/skills/python-thing")
    monkeypatch.setattr(sys, "argv", ["repo-gate.py", "--mirror-of", str(public / "libs" / "thing")])

    assert RG.main() == 0


def test_a_twin_that_the_manifest_does_not_list_is_reported(tmp_path, monkeypatch):
    # The manifest is hand-maintained, and a missing entry is invisible: it simply stops
    # checking that pair. coding-python-layered-config went unchecked exactly that way.
    public = _mirror_tree(tmp_path)
    monkeypatch.setattr(RG, "MIRRORED_SKILLS", {})

    found = RG.unlisted_mirrors(public / "KI" / "bitranox-skills", public)

    assert found == [("coding-python-thing", "libs/thing/skills/python-thing")]


def test_a_listed_twin_is_not_reported_as_unlisted(tmp_path, monkeypatch):
    public = _mirror_tree(tmp_path)
    monkeypatch.setattr(RG, "MIRRORED_SKILLS", {"coding-python-thing": "libs/thing/skills/python-thing"})

    assert RG.unlisted_mirrors(public / "KI" / "bitranox-skills", public) == []


def test_a_repo_skill_with_its_own_description_is_not_a_mirror(tmp_path, monkeypatch):
    # Matching on the description is what makes this reliable; an unrelated skill that
    # merely lives in a tool repo must not be reported as somebody's twin.
    public = _mirror_tree(tmp_path)
    write(public / "libs" / "other" / "skills" / "unrelated" / "SKILL.md", "---\nname: unrelated\ndescription: Use when doing something else entirely.\n---\n")
    monkeypatch.setattr(RG, "MIRRORED_SKILLS", {"coding-python-thing": "libs/thing/skills/python-thing"})

    assert RG.unlisted_mirrors(public / "KI" / "bitranox-skills", public) == []


def test_every_manifest_entry_points_at_a_real_twin_on_this_machine():
    # Guards the other direction: an entry whose path no longer exists silently degrades
    # to "skipped forever". Only meaningful where the fleet is checked out.
    here = Path(RG.__file__).resolve()
    public = next((p for p in here.parents if p.name == "public"), None)
    if public is None:
        pytest.skip("not inside the shared public/ tree")
    missing = [rel for rel in RG.MIRRORED_SKILLS.values() if not (public / rel / "SKILL.md").is_file()]
    assert missing == [], "MIRRORED_SKILLS points at a twin that does not exist: %s" % missing


# --------------------------------------------------------------------------
# The tool-repo side of the gate: a mirrored skill edited in ITS OWN repo
# --------------------------------------------------------------------------


def _tool_repo_commit(monkeypatch, public, repo, command="git commit -m x"):
    """Drive hook mode as though the commit happened inside a tool repo."""
    monkeypatch.setattr(RG, "repo_root", lambda: repo)
    monkeypatch.setattr(RG, "_public_tree", lambda _start: public)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"tool_input": {"command": command}})))
    monkeypatch.setattr(sys, "argv", ["repo-gate.py"])


def test_a_commit_in_a_tool_repo_blocks_when_its_mirror_has_drifted(tmp_path, monkeypatch, capsys):
    # The asymmetry this closes: the gate already fires on every git commit, but used to
    # return 0 in any repo that is not the marketplace - so editing a mirrored skill in
    # its OWN repo was unguarded. Measured twice in practice: the network-probe mirror
    # described a subsystem as absent two releases after it shipped.
    public = _mirror_tree(tmp_path, twin_body=TWIN_BODY.replace("One paragraph of content.", "DRIFTED: a capability the mirror never heard of."))
    monkeypatch.setattr(RG, "MIRRORED_SKILLS", {"coding-python-thing": "libs/thing/skills/python-thing"})
    _tool_repo_commit(monkeypatch, public, public / "libs" / "thing")

    assert RG.main() == 2
    assert "DRIFT" in capsys.readouterr().out


def test_a_commit_in_a_tool_repo_passes_when_the_mirror_is_in_sync(tmp_path, monkeypatch):
    public = _mirror_tree(tmp_path)
    monkeypatch.setattr(RG, "MIRRORED_SKILLS", {"coding-python-thing": "libs/thing/skills/python-thing"})
    _tool_repo_commit(monkeypatch, public, public / "libs" / "thing")

    assert RG.main() == 0


def test_a_repo_that_ships_no_mirrored_skill_is_still_silent(tmp_path, monkeypatch, capsys):
    # The gate must not start narrating in every unrelated repo on the machine.
    public = _mirror_tree(tmp_path)
    monkeypatch.setattr(RG, "MIRRORED_SKILLS", {"coding-python-thing": "libs/thing/skills/python-thing"})
    _tool_repo_commit(monkeypatch, public, public / "libs" / "unrelated")

    assert RG.main() == 0
    assert capsys.readouterr().out == ""


def test_a_non_commit_command_in_a_tool_repo_is_not_checked(tmp_path, monkeypatch):
    public = _mirror_tree(tmp_path, twin_body=TWIN_BODY.replace("One paragraph of content.", "DRIFTED: a capability the mirror never heard of."))
    monkeypatch.setattr(RG, "MIRRORED_SKILLS", {"coding-python-thing": "libs/thing/skills/python-thing"})
    _tool_repo_commit(monkeypatch, public, public / "libs" / "thing", command="git status")

    assert RG.main() == 0


def test_a_missing_marketplace_checkout_says_so_instead_of_passing_silently(tmp_path, monkeypatch, capsys):
    # THE failure mode that would make this whole guard worthless: with no marketplace
    # on the machine there is nothing to compare, and a bare exit 0 is indistinguishable
    # from "in sync". It must pass - blocking would break anyone without the checkout -
    # but it has to SAY it could not check, on the channel the model actually reads.
    public = tmp_path / "public"
    write(public / "libs" / "thing" / "skills" / "python-thing" / "SKILL.md", TWIN_BODY)
    monkeypatch.setattr(RG, "MIRRORED_SKILLS", {"coding-python-thing": "libs/thing/skills/python-thing"})
    _tool_repo_commit(monkeypatch, public, public / "libs" / "thing")

    assert RG.main() == 0
    printed = capsys.readouterr().out
    assert "additionalContext" in printed, "an unverifiable mirror must reach the model, not exit 0 in silence"
    assert "could not" in printed.lower() or "nothing to compare" in printed.lower()


# ---- duplicate .py basenames ---------------------------------------------------------------------

def _repo_with(tmp_path, rel_paths):
    """A git repo whose tracked files are `rel_paths` (the check enumerates via git ls-files)."""
    for rel in rel_paths:
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x = 1\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    return tmp_path


def test_duplicate_basenames_are_reported(tmp_path):
    """Two modules with one name: whichever is collected FIRST wins for the whole pytest run, so
    the other directory's tests silently exercise a file nobody changed. Both suites stay green."""
    root = _repo_with(tmp_path, ["a/helper.py", "b/helper.py"])
    fails = RG.check_duplicate_basenames(root)
    assert fails, "a duplicate basename was not reported"
    assert any("helper.py" in f for f in fails)


def test_unique_basenames_pass(tmp_path):
    root = _repo_with(tmp_path, ["a/one.py", "b/two.py"])
    assert RG.check_duplicate_basenames(root) == []


def test_conftest_duplicates_are_benign(tmp_path):
    """pytest handles per-directory conftest.py specially; every test dir legitimately has one."""
    root = _repo_with(tmp_path, ["a/tests/conftest.py", "b/tests/conftest.py"])
    assert RG.check_duplicate_basenames(root) == []


def test_vendored_demos_and_examples_are_exempt(tmp_path):
    """Same exemption the pytest run already makes: those trees are documentation, not convention."""
    root = _repo_with(tmp_path, ["a/helper.py", "x/demos/helper.py", "y/examples/helper.py"])
    assert RG.check_duplicate_basenames(root) == []


def test_three_copies_are_all_named(tmp_path):
    root = _repo_with(tmp_path, ["a/dup.py", "b/dup.py", "c/dup.py"])
    joined = "\n".join(RG.check_duplicate_basenames(root))
    for d in ("a/dup.py", "b/dup.py", "c/dup.py"):
        assert d in joined, d


def test_the_real_repo_has_no_duplicate_basenames():
    """Guards the consolidation this check was written for: the plugin ships each module once."""
    root = Path(__file__).resolve().parents[3].parent
    assert (root / ".git").exists(), "expected to run inside the repo checkout"
    assert RG.check_duplicate_basenames(root) == []


# --------------------------------------------------------------------------
# Test-dependency preflight: a missing optional dep must name itself, not
# surface as an unrelated assertion failure inside somebody's test.
# --------------------------------------------------------------------------


def _workflow(tmp_path, install_line):
    wf = tmp_path / ".github" / "workflows"
    wf.mkdir(parents=True)
    (wf / "ci.yml").write_text(
        "jobs:\n"
        "  test:\n"
        "    steps:\n"
        "      - run: |\n"
        "          python -m pip install --upgrade pip\n"
        "          %s\n" % install_line,
        encoding="utf-8",
    )
    return tmp_path


def test_dependency_list_is_read_from_the_ci_workflow(tmp_path):
    """Reading the workflow is what stops the gate's idea of CI drifting from CI's."""
    root = _workflow(tmp_path, "pip install pytest PyYAML lxml")
    assert RG.ci_test_dependencies(root) == ["pytest", "PyYAML", "lxml"]


def test_the_pip_upgrade_line_is_not_read_as_a_dependency(tmp_path):
    root = _workflow(tmp_path, "pip install pytest lxml")
    names = RG.ci_test_dependencies(root)
    assert "--upgrade" not in names and names == ["pytest", "lxml"]


def test_a_missing_dependency_is_named_with_the_command_that_installs_it(tmp_path):
    root = _workflow(tmp_path, "pip install pytest lxml")
    msgs = RG.check_test_dependencies(root, is_installed=lambda mod: mod != "lxml")
    joined = "\n".join(msgs)
    assert msgs, "a missing dependency must be reported"
    assert "missing: lxml" in joined
    assert "pip install lxml" in joined


def test_an_installed_dependency_is_not_reported_as_missing(tmp_path):
    root = _workflow(tmp_path, "pip install pytest lxml")
    joined = "\n".join(RG.check_test_dependencies(root, is_installed=lambda mod: mod != "lxml"))
    assert "missing: lxml" in joined and "pytest" not in joined.split("missing:")[1].splitlines()[0]


def test_all_dependencies_present_reports_nothing(tmp_path):
    root = _workflow(tmp_path, "pip install pytest lxml")
    assert RG.check_test_dependencies(root, is_installed=lambda mod: True) == []


def test_pyyaml_is_probed_by_its_import_name(tmp_path):
    """PyYAML installs under one name and imports under another; probing the pip name always misses."""
    root = _workflow(tmp_path, "pip install PyYAML")
    probed = []

    def record(mod):
        probed.append(mod)
        return True

    RG.check_test_dependencies(root, is_installed=record)
    assert probed == ["yaml"]


def test_a_workflow_that_cannot_be_read_reports_nothing(tmp_path):
    """No workflow means no claim about CI parity to make - stay silent rather than guess."""
    assert RG.ci_test_dependencies(tmp_path) == []
    assert RG.check_test_dependencies(tmp_path, is_installed=lambda mod: False) == []


def test_the_default_probe_finds_a_module_that_is_installed():
    """The injected seam must agree with the real import system, or the tests prove nothing."""
    assert RG.module_installed("json") is True
    assert RG.module_installed("a_module_that_is_not_installed_anywhere") is False


def test_a_missing_dependency_does_not_also_report_a_pytest_failure(tmp_path, monkeypatch):
    """One cause, one message: running pytest anyway files the dep problem as a test defect."""
    root = _workflow(tmp_path, "pip install lxml")
    monkeypatch.setattr(RG, "module_installed", lambda mod: False)
    monkeypatch.setattr(RG, "check_pytest", lambda *a, **k: pytest.fail("pytest must not run"))
    joined = "\n".join(RG.run_checks(root, ci=True))
    assert "missing: lxml" in joined


def test_the_real_workflow_names_the_dependencies_this_gate_relies_on():
    root = Path(__file__).resolve().parents[3].parent
    names = RG.ci_test_dependencies(root)
    assert "pytest" in names and "lxml" in names


# --------------------------------------------------------------------------
# check_pytest: the run must be fail-CLOSED
#
# Every other test in this file patches check_pytest out, so its own behaviour
# was never exercised - which is how the zero-collection fail-open below shipped.
# These drive the real function against real pytest runs in tmp_path.
# --------------------------------------------------------------------------


def test_a_passing_suite_is_reported_as_no_failures(tmp_path):
    tests = tmp_path / "tests"
    write(tests / "test_ok.py", "def test_ok():\n    assert True\n")
    assert RG.check_pytest(tmp_path, [tests]) == []


def test_a_failing_suite_is_reported(tmp_path):
    tests = tmp_path / "tests"
    write(tests / "test_bad.py", "def test_bad():\n    assert False\n")
    problems = RG.check_pytest(tmp_path, [tests])
    assert problems and "pytest failed:" in problems[0]


def test_a_path_that_does_not_exist_is_not_an_empty_run(tmp_path):
    """The one legitimate empty case: hook mode points at a tests dir that is absent."""
    assert RG.check_pytest(tmp_path, [tmp_path / "nope"]) == []


def test_a_test_dir_that_collects_nothing_is_a_failure(tmp_path):
    """pytest exits 5 on zero collected. Treating that as success means a broken
    glob, a renamed dir or a conftest import error reads as 'all checks passed'
    while nothing ran at all."""
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "not_a_test.py").write_text("x = 1\n", encoding="utf-8")
    problems = RG.check_pytest(tmp_path, [tests])
    assert problems, "zero collected tests must be reported, not silently passed"
    assert any("no tests" in p.lower() for p in problems)


def test_collecting_under_the_floor_is_a_failure(tmp_path):
    """A partial collapse never reaches zero, so the rc-5 check alone cannot see it."""
    tests = tmp_path / "tests"
    write(tests / "test_one.py", "def test_one():\n    assert True\n")
    problems = RG.check_pytest(tmp_path, [tests], baseline=500)
    assert problems, "a collected count under the floor must be reported"
    assert any("floor" in p.lower() or "baseline" in p.lower() for p in problems)


# --------------------------------------------------------------------------
# --pytest-only: the CI test step. Streams pytest to the log (so a run is
# visible) and counts from the junit XML rather than from scraped stdout.
# --------------------------------------------------------------------------


def _junit(tmp_path, tests, failures=0, errors=0):
    xml = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<testsuites><testsuite name="pytest" errors="%d" failures="%d" tests="%d">'
        "</testsuite></testsuites>" % (errors, failures, tests)
    )
    path = tmp_path / "junit.xml"
    path.write_text(xml, encoding="utf-8")
    return path


def test_junit_total_reads_the_test_count(tmp_path):
    assert RG.junit_total(_junit(tmp_path, tests=3122)) == 3122


def test_junit_total_returns_none_when_the_report_is_missing(tmp_path):
    assert RG.junit_total(tmp_path / "absent.xml") is None


def test_junit_total_returns_none_on_a_corrupt_report(tmp_path):
    path = tmp_path / "junit.xml"
    path.write_text("<testsuites", encoding="utf-8")
    assert RG.junit_total(path) is None


def test_floor_problems_accepts_a_count_at_or_above_the_floor(tmp_path):
    assert RG.floor_problems(_junit(tmp_path, tests=3000), baseline=3000) == []


def test_floor_problems_rejects_a_count_under_the_floor(tmp_path):
    problems = RG.floor_problems(_junit(tmp_path, tests=12), baseline=3000)
    assert problems and "12" in problems[0]


def test_floor_problems_rejects_an_unreadable_report(tmp_path):
    """A missing report means the count is unknown - that must not read as 'above the floor'."""
    problems = RG.floor_problems(tmp_path / "absent.xml", baseline=3000)
    assert problems, "an unknown count must fail closed, not pass"


def test_the_real_ci_workflow_still_declares_the_dependency_set():
    """ci_test_dependencies() scrapes `pip install` lines out of the real ci.yml, and the
    pre-push hook builds its `uv run --with ...` line from the result. A workflow edit that
    leaves zero or duplicate `pip install` lines silently empties or doubles that list, and
    nothing else would notice: the preflight just stops preflighting."""
    root = Path(__file__).resolve().parents[4]
    assert (root / ".github" / "workflows" / "ci.yml").exists(), root
    deps = RG.ci_test_dependencies(root)
    assert deps == ["pytest", "PyYAML", "lxml", "defusedxml", "ruamel.yaml", "httpx2"], deps
    assert len(deps) == len(set(deps)), "duplicated pip install lines double the dependency set"


# --------------------------------------------------------------------------
# The floor is derived from a checked-in baseline, not a hardcoded constant,
# and it is measured on COLLECTED tests rather than passed ones: skips are
# platform-dependent (Windows and macOS legitimately skip POSIX-only tests),
# so a floor on "passed" would drift by platform rather than by real coverage.
# --------------------------------------------------------------------------


def test_baseline_is_checked_in_and_matches_the_real_suite():
    root = Path(__file__).resolve().parents[4]
    baseline = RG.expected_collected(root)
    assert baseline > 3000, baseline


def test_floor_from_baseline_allows_a_small_dip(tmp_path):
    """Marking a handful of tests POSIX-only must not trip the gate."""
    assert RG.floor_problems(_junit(tmp_path, tests=2980), baseline=3000) == []


def test_floor_from_baseline_rejects_a_real_collapse(tmp_path):
    problems = RG.floor_problems(_junit(tmp_path, tests=2000), baseline=3000)
    assert problems and "2000" in problems[0]


def test_floor_names_the_baseline_to_update(tmp_path):
    """A gate that blocks must say how to unblock it deliberately."""
    problems = RG.floor_problems(_junit(tmp_path, tests=10), baseline=3000)
    assert any("baseline" in p.lower() for p in problems)


def test_a_grown_suite_is_never_a_failure(tmp_path):
    assert RG.floor_problems(_junit(tmp_path, tests=9999), baseline=3000) == []


# --------------------------------------------------------------------------
# Non-ASCII tracked paths. Git C-quotes them (core.quotePath), so a scanner that
# opens the file by the name git printed opens nothing, and a fail-open turns
# that into a clean verdict on a file it never read.
# The name is built from an escape so this file itself stays ASCII.
# --------------------------------------------------------------------------

UMLAUT_NAME = "f\u00e4hig.py"


def test_git_paths_returns_names_that_open_a_real_file(tmp_path):
    """The seam every scanner enumerates through.

    Without -z, git prints the literal "f\\303\\244hig.py", quotes included, which names no file
    on disk. Both names must come back as paths that exist, or the caller skips one in silence.
    """
    git_repo(tmp_path, {"plain.py": "x = 1\n", UMLAUT_NAME: "x = 1\n"})
    rc, paths = RG._git_paths(tmp_path, "ls-files")
    assert rc == 0
    assert sorted(paths) == sorted(["plain.py", UMLAUT_NAME])
    assert all((tmp_path / p).exists() for p in paths)


@pytest.mark.parametrize("name", ["plain.py", UMLAUT_NAME])
def test_secrets_scans_a_file_whatever_its_name_encodes(tmp_path, name):
    """The ASCII twin is the control: it must pass for the same reason the other must.

    Proven 2026-08-28 with exactly this pair - the quoted path raised inside read_bytes, the
    `except OSError` swallowed it, and the file carrying the token was never scanned while the
    gate reported clean. This check is the automated enforcement of the no-secrets rule, and the
    tree it guards is SMB-exported and edited from Windows, so an umlaut in a filename is
    ordinary rather than exotic.
    """
    git_repo(tmp_path, {name: "token = " + GH_TOKEN + "\n"})
    assert any("GitHub token" in f for f in RG.check_secrets(tmp_path))


@pytest.mark.parametrize("name", ["plain.py", UMLAUT_NAME])
def test_lf_endings_flags_crlf_whatever_the_name_encodes(tmp_path, name):
    """Same defect, second scanner - and nothing previously proved this check FIRES at all."""
    (tmp_path / name).write_bytes(b"x = 1\r\ny = 2\r\n")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    assert any(name in f for f in RG.check_lf_endings(tmp_path))


def git_repo_with_origin(tmp_path, files):
    """A repo carrying an origin/master ref, so the origin-comparing checks actually run.

    Both checks below return [] the moment `rev-parse --verify origin/master` fails, so without
    this ref they pass while asserting nothing - which is how they came to have no test at all.
    """
    git_repo(tmp_path, files)
    subprocess.run(["git", "-c", "user.email=t@example.invalid", "-c", "user.name=t",
                    "commit", "-q", "--no-verify", "-m", "base"], cwd=tmp_path, check=True)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=tmp_path,
                          capture_output=True, text=True, check=True).stdout.strip()
    subprocess.run(["git", "update-ref", "refs/remotes/origin/master", head],
                   cwd=tmp_path, check=True)
    return tmp_path


def test_changed_vs_origin_returns_a_non_ascii_path_unquoted(tmp_path):
    """`git diff --name-only` quotes exactly like `ls-files` does.

    These paths feed a regex that decides whether a changed SKILL.md needs its skill-writer
    receipt, so a quoted name does not merely look wrong - it stops matching, and the receipt
    requirement silently lapses for that skill.
    """
    git_repo_with_origin(tmp_path, {UMLAUT_NAME: "x = 1\n", "plain.py": "x = 1\n"})
    (tmp_path / UMLAUT_NAME).write_text("x = 2\n", encoding="utf-8")
    (tmp_path / "plain.py").write_text("x = 2\n", encoding="utf-8")
    assert sorted(RG._changed_vs_origin(tmp_path)) == sorted(["plain.py", UMLAUT_NAME])


def test_version_bumped_fires_when_a_plugin_file_changes_without_a_bump(tmp_path):
    """Coverage for a check that had none, in both directions.

    Quoting cannot change THIS verdict - the function only tests the changed list for emptiness,
    and a quoted path is just as non-empty - so this is not a quoting regression test. It is here
    because the check now enumerates through a helper it did not use before, and nothing else
    proves it still fires, or still goes quiet once the version moves.
    """
    pj = "plugins/bitranox/.claude-plugin/plugin.json"
    git_repo_with_origin(tmp_path, {pj: '{"version": "1.0.0"}\n',
                                    "plugins/bitranox/hooks/x.py": "x = 1\n"})
    (tmp_path / "plugins" / "bitranox" / "hooks" / "x.py").write_text("x = 2\n", encoding="utf-8")
    assert any("still 1.0.0" in f for f in RG.check_version_bumped(tmp_path))
    (tmp_path / pj).write_text('{"version": "1.0.1"}\n', encoding="utf-8")
    assert RG.check_version_bumped(tmp_path) == []


PJ_REL = "plugins/bitranox/.claude-plugin/plugin.json"


def bumped_repo(tmp_path, changelog):
    """A repo whose plugin.json is bumped past origin/master, carrying `changelog` as its
    CHANGELOG.md. Pass None to ship no changelog at all."""
    files = {PJ_REL: '{"version": "1.0.0"}\n', "plugins/bitranox/hooks/x.py": "x = 1\n"}
    if changelog is not None:
        files["CHANGELOG.md"] = changelog
    git_repo_with_origin(tmp_path, files)
    (tmp_path / PJ_REL).write_text('{"version": "1.0.1"}\n', encoding="utf-8")
    return tmp_path


def test_changelog_fires_when_a_bump_ships_without_an_entry(tmp_path):
    """The motivating case: a version reaches installs with nothing recorded about it.

    This is the direction that actually happened - 153 shipped versions had no entry when the
    check was written - so it is the one that must stay covered.
    """
    bumped_repo(tmp_path, "# Changelog\n\n## [1.0.0]\n\n- the previous one\n")
    failures = RG.check_changelog_current_version(tmp_path)
    assert any("1.0.1" in f and "no `## [1.0.1]` heading" in f for f in failures)


def test_changelog_is_quiet_once_the_entry_exists(tmp_path):
    """The check must be able to report the other answer, or it asserts nothing above."""
    bumped_repo(tmp_path, "# Changelog\n\n## [1.0.1]\n\n- the new one\n\n## [1.0.0]\n")
    assert RG.check_changelog_current_version(tmp_path) == []


def test_changelog_accepts_the_older_dated_heading_shape(tmp_path):
    """Two heading shapes ship in the real file: `## [5.290.0]` and `## [5.207.0] - 2026-08-16`.

    264 of the historical headings carry the dated suffix. A matcher built only against the
    current shape passes every recent version and rejects every old one, so it would fire on a
    correct entry the day anyone wrote one in the older style.
    """
    bumped_repo(tmp_path, "# Changelog\n\n## [1.0.1] - 2026-08-31\n\n- dated shape\n")
    assert RG.check_changelog_current_version(tmp_path) == []


def test_version_sync_fires_when_pyproject_and_manifest_disagree(tmp_path):
    """The drift this check exists for, in the direction that actually happened.

    A wheel built at one version shipping a CLI that reports another: every test passed,
    because nothing compared the two files.
    """
    write(tmp_path / "plugins/bitranox/.claude-plugin/plugin.json",
          json.dumps({"name": "bitranox", "version": "1.0.0"}))
    write(tmp_path / "pyproject.toml", '[project]\nname = "x"\nversion = "1.1.0"\n')
    failures = RG.check_version_sync(tmp_path)
    assert any("1.1.0" in f and "1.0.0" in f for f in failures)


def test_version_sync_is_quiet_when_they_match(tmp_path):
    """It must be able to report the other answer, or the test above asserts nothing."""
    write(tmp_path / "plugins/bitranox/.claude-plugin/plugin.json",
          json.dumps({"name": "bitranox", "version": "2.3.4"}))
    write(tmp_path / "pyproject.toml", '[project]\nname = "x"\nversion = "2.3.4"\n')
    assert RG.check_version_sync(tmp_path) == []


def test_version_sync_skips_a_repo_with_no_pyproject(tmp_path):
    """Not every checkout is a Python distribution; absence is not a violation."""
    write(tmp_path / "plugins/bitranox/.claude-plugin/plugin.json",
          json.dumps({"name": "bitranox", "version": "2.3.4"}))
    assert RG.pyproject_version(tmp_path) is None
    assert RG.check_version_sync(tmp_path) == []


def test_version_sync_fires_when_pyproject_carries_no_readable_version(tmp_path):
    """A pyproject that is PRESENT but whose version cannot be read is a finding, not a pass.

    Absence of the file means "not a distribution" and is the legitimate skip tested above. A
    file that is there and unreadable is a different answer: reporting no failures asserts the
    two versions AGREE, which is the one thing this check cannot know when it never learned
    either of them.
    """
    write(tmp_path / "plugins/bitranox/.claude-plugin/plugin.json",
          json.dumps({"name": "bitranox", "version": "2.3.4"}))
    write(tmp_path / "pyproject.toml", '[project]\nname = "x"\n')
    failures = RG.check_version_sync(tmp_path)
    assert failures, "a present pyproject with no readable version must be reported"
    assert any("pyproject.toml" in f for f in failures)


def test_version_sync_fires_when_the_manifest_cannot_be_read(tmp_path):
    """The same argument from the manifest's side.

    plugin.json is what the installed CLI reports at runtime, so a malformed one is exactly the
    state that ships a tool misreporting its own version - the defect this check was written for.
    """
    write(tmp_path / "plugins/bitranox/.claude-plugin/plugin.json", "{ not json")
    write(tmp_path / "pyproject.toml", '[project]\nname = "x"\nversion = "2.3.4"\n')
    failures = RG.check_version_sync(tmp_path)
    assert failures, "an unreadable manifest must be reported, not skipped"
    assert any("plugin.json" in f for f in failures)


def test_version_sync_fires_when_the_manifest_is_missing_beside_a_pyproject(tmp_path):
    """run_checks only ever runs against the marketplace root, where the manifest is not optional.

    The --mirror-of entry point returns before run_checks, so no tool repo reaches this check
    and an absent manifest here means the marketplace checkout is incomplete.
    """
    write(tmp_path / "pyproject.toml", '[project]\nname = "x"\nversion = "2.3.4"\n')
    failures = RG.check_version_sync(tmp_path)
    assert failures, "a missing manifest must be reported, not skipped"


def test_version_sync_fires_on_a_pyproject_that_is_not_valid_toml(tmp_path):
    """Invalid TOML is a file to repair, and the message must say so rather than blaming a key.

    The version line here is perfectly readable to the eye, which is exactly why a line-scanning
    fallback would have answered "1.2.3" and passed while tomllib rejects the file.
    """
    write(tmp_path / "plugins/bitranox/.claude-plugin/plugin.json",
          json.dumps({"name": "bitranox", "version": "1.2.3"}))
    write(tmp_path / "pyproject.toml", '[project\nname = "x"\nversion = "1.2.3"\n')
    failures = RG.check_version_sync(tmp_path)
    assert failures, "a pyproject that cannot be parsed must be reported, not skipped"
    assert any("not valid TOML" in f for f in failures)


def test_version_sync_reports_rather_than_passing_without_tomllib(tmp_path, monkeypatch):
    """Below 3.11 the check says it could not verify, instead of answering that they agree.

    The two versions here MATCH, so a check able to read them would pass. It must still fire,
    which is what makes this test about verifiability rather than about drift.

    A hand-rolled TOML reader shipped in 5.294.2 to avoid this and was removed: its wrong
    answers would be silent and reachable only below 3.11, where nothing exercises them, and
    it left a malformed pyproject passing there while firing on 3.11+. The repo declares
    requires-python >=3.11, so an interpreter without tomllib cannot develop it anyway.
    """
    monkeypatch.setitem(sys.modules, "tomllib", None)
    write(tmp_path / "plugins/bitranox/.claude-plugin/plugin.json",
          json.dumps({"name": "bitranox", "version": "7.8.9"}))
    write(tmp_path / "pyproject.toml", '[project]\nname = "x"\nversion = "7.8.9"\n')
    failures = RG.check_version_sync(tmp_path)
    assert failures, "an interpreter that cannot parse TOML must report, not pass"
    assert any("tomllib" in f for f in failures)


def test_changelog_fires_on_an_undocumented_version_with_no_bump(tmp_path):
    """The discriminating case against the diff-shaped predecessor.

    Nothing changed here - the version on disk equals the one on origin/master - and the check
    must STILL fire, because the invariant is about what the manifest NAMES, not about what
    moved. The diff form went quiet on exactly this state, which is why it was inert in CI on a
    push to master: by then the commit that made the bump IS origin/master.
    """
    git_repo_with_origin(tmp_path, {PJ_REL: '{"version": "1.0.0"}\n',
                                    "CHANGELOG.md": "# Changelog\n\n## [0.9.0]\n"})
    assert RG._plugin_version_pair(tmp_path) == ("1.0.0", "1.0.0"), "fixture must show NO bump"
    assert any("1.0.0" in f for f in RG.check_changelog_current_version(tmp_path))


def test_changelog_reports_a_missing_changelog_file(tmp_path):
    """A tree with no CHANGELOG.md at all is a violation, not a skip - otherwise deleting the
    file is the way to silence the check."""
    bumped_repo(tmp_path, None)
    assert any("no CHANGELOG.md" in f for f in RG.check_changelog_current_version(tmp_path))


def test_changelog_needs_no_origin_master(tmp_path):
    """It must answer in a repo with no remote-tracking ref at all.

    A CI checkout need not have one, and dropping the diff is precisely what frees the check
    from depending on a ref being fetched. The predecessor returned [] here, which reads as a
    pass on a tree that is actually undocumented.
    """
    git_repo(tmp_path, {PJ_REL: '{"version": "2.0.0"}\n', "CHANGELOG.md": "# Changelog\n"})
    assert RG._plugin_version_pair(tmp_path) is None, "fixture must have no origin/master"
    assert any("2.0.0" in f for f in RG.check_changelog_current_version(tmp_path))


def test_changelog_heading_matcher_rejects_a_version_that_merely_appears(tmp_path):
    """A prose mention of the version is not an entry.

    `changelog_documents` anchors on a heading, so a body line naming 1.0.1 - which is what a
    "still missing" note looks like - must not satisfy the requirement it is complaining about.
    """
    body = "# Changelog\n\n## [1.0.0]\n\n- 1.0.1 is still missing and not covered here\n"
    bumped_repo(tmp_path, body)
    assert RG.changelog_documents(tmp_path, "1.0.1") is False
    assert RG.check_changelog_current_version(tmp_path) != []


# --------------------------------------------------------------------------
# check_ragged_tables - the repo opts itself into the tool's --strict behaviour
# --------------------------------------------------------------------------


def _repo_with_table(tmp_path, table_md):
    """A tree carrying the real reformat_tables.py, since the check imports it rather than
    re-implementing the fence walk."""
    make_repo(tmp_path)
    real = Path(RG.__file__).resolve().parents[1] / "skills" / "docs-md-table-formatting" \
        / "reformat_tables.py"
    dest = tmp_path / "plugins/bitranox/skills/docs-md-table-formatting/reformat_tables.py"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(real.read_text(encoding="utf-8"), encoding="utf-8")
    write(tmp_path / "docs/page.md", table_md)
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    return tmp_path


def test_ragged_tables_flags_a_long_row(tmp_path):
    root = _repo_with_table(tmp_path, "| a | b |\n|---|---|\n| 1 | 2 | 3 |\n")
    failures = RG.check_ragged_tables(root)
    assert failures, failures
    assert "docs/page.md:3:" in "\n".join(failures[1:]), failures


def test_ragged_tables_names_the_file_the_way_git_does(tmp_path):
    """The finding names a repo-relative POSIX path, on every platform.

    The tool echoes back whatever path it is handed, so handing it an absolute one put the
    runner's home directory into the message - and on Windows the native separator made the
    assertion above fail while the check itself was working (CI, windows-latest py3.13,
    2026-08-31). Asserting the RELATIVE form fails on POSIX too, so the platform bug is
    reproducible here rather than only on a runner.
    """
    root = _repo_with_table(tmp_path, "| a | b |\n|---|---|\n| 1 | 2 | 3 |\n")
    body = "\n".join(RG.check_ragged_tables(root)[1:])
    assert body.strip().startswith("docs/page.md:"), body
    assert str(root) not in body, body
    assert "\\" not in body, body


def test_ragged_tables_flags_a_short_row(tmp_path):
    root = _repo_with_table(tmp_path, "| a | b | c |\n|---|---|---|\n| 1 | 2 |\n")
    failures = RG.check_ragged_tables(root)
    assert failures, failures
    assert "docs/page.md:3:" in "\n".join(failures[1:]), failures


def test_ragged_tables_passes_a_clean_table(tmp_path):
    """The control: a well-formed table must NOT be reported, or the check blocks every push."""
    root = _repo_with_table(tmp_path, "| a | b |\n|---|---|\n| 1 | 2 |\n")
    assert RG.check_ragged_tables(root) == []


def test_ragged_tables_fails_open_without_the_tool(tmp_path):
    """Unable to enumerate is not evidence of a violation - same contract as the other checks."""
    make_repo(tmp_path)
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    assert RG.check_ragged_tables(tmp_path) == []
