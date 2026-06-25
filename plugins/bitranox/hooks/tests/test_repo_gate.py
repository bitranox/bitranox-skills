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


def make_repo(root, *, version="1.6.0", good_skill=True, bad_skill=False, demo_only=False):
    write(root / "plugins/bitranox/.claude-plugin/plugin.json",
          json.dumps({"name": "bitranox", "version": version}))
    write(root / ".claude-plugin/marketplace.json", json.dumps({"name": "bitranox-skills"}))
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
# is_commit_or_pr
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "cmd,expected",
    [
        ("git commit -m 'x'", True),
        ("git add -A && git commit -m 'x'", True),
        ("git -C /repo commit --amend", True),
        ("gh pr create --fill", True),
        ("git status", False),
        ("git push", False),
        ("ls && echo commit done", False),
        ("git log --oneline", False),
    ],
)
def test_is_commit_or_pr(cmd, expected):
    assert RG.is_commit_or_pr(cmd) is expected


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
    monkeypatch.setattr(RG, "check_pytest", lambda root, paths: [])
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
    monkeypatch.setattr(RG, "check_pytest", lambda root, paths: [])  # don't run real pytest
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"tool_input": {"command": "git commit -m x"}})))
    assert RG.main() == 2
    assert "commit blocked" in capsys.readouterr().err


def test_main_hook_allows_clean_commit(tmp_path, monkeypatch):
    make_repo(tmp_path, good_skill=True)
    monkeypatch.setattr(RG, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(RG, "check_pytest", lambda root, paths: [])
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"tool_input": {"command": "git commit -m x"}})))
    assert RG.main() == 0


def test_main_malformed_stdin_passes(tmp_path, monkeypatch):
    make_repo(tmp_path)
    monkeypatch.setattr(RG, "repo_root", lambda: tmp_path)
    monkeypatch.setattr(sys, "stdin", io.StringIO("not json"))
    assert RG.main() == 0


# --------------------------------------------------------------------------
# check_skills_index (using-bitranox-skills domains list <-> skill dirs)
# --------------------------------------------------------------------------

INDEX_TEMPLATE = """---
name: using-bitranox-skills
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
    write(root / "plugins/bitranox/skills/using-bitranox-skills/SKILL.md",
          INDEX_TEMPLATE.format(names=names))


def test_skills_index_in_sync(tmp_path):
    make_skills(tmp_path, ["alpha", "beta"])
    make_index(tmp_path, ["alpha", "beta"])
    assert RG.check_skills_index(tmp_path) == []


def test_skills_index_flags_unlisted_skill(tmp_path):
    make_skills(tmp_path, ["alpha", "beta", "gamma"])
    make_index(tmp_path, ["alpha", "beta"])  # gamma not listed
    fails = RG.check_skills_index(tmp_path)
    assert any("gamma" in f and "omits" in f for f in fails)


def test_skills_index_flags_stale_entry(tmp_path):
    make_skills(tmp_path, ["alpha"])
    make_index(tmp_path, ["alpha", "ghost"])  # ghost has no dir
    fails = RG.check_skills_index(tmp_path)
    assert any("ghost" in f and "non-existent" in f for f in fails)


def test_skills_index_ignores_itself_and_non_bullet_names(tmp_path):
    # using-bitranox-skills need not list itself; names outside the bullets (the caveat
    # paragraph's `not-a-bullet-name`) must not be treated as listed skills.
    make_skills(tmp_path, ["alpha"])
    make_index(tmp_path, ["alpha"])
    assert RG.check_skills_index(tmp_path) == []


# --------------------------------------------------------------------------
# check_secrets (credentials / private keys / sensitive files / infra denylist)
# Tokens are built via concatenation so the literal patterns are NOT present in this
# test file (else the gate would flag this file when scanning the real repo).
# --------------------------------------------------------------------------

GH_TOKEN = "ghp_" + "A" * 36
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
