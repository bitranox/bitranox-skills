#!/usr/bin/env python3
"""Pre-commit / CI gate for the bitranox-skills marketplace repo.

Enforces the repo's mandatory invariants in two interchangeable modes that share one
set of checks:

  * Hook mode (default): PreToolUse(Bash). Reads the event JSON on stdin and acts ONLY
    when the command is a `git commit` or `gh pr create`. On a violation it exits 2 to
    block the commit and prints what to fix; otherwise exits 0. Every error path exits 0
    so a broken gate never wedges a turn.
  * CI mode (`--ci`): runs the same checks against the working tree, prints a summary,
    and exits 1 on any violation (0 otherwise). Meant for GitHub Actions as a reporting
    check.

CRITICAL: this plugin is installed globally, so the Bash hook fires in EVERY repo the
user commits in. The gate first verifies it is actually inside the bitranox-skills repo
(plugins/bitranox/.claude-plugin/plugin.json with name "bitranox"); in any other repo it
no-ops (exit 0) so it never blocks unrelated commits.

Checks:
  1. tests-exist  - every skill/hook package that ships non-demo .py has a tests/ dir
                    with at least one test_*.py (demos/ and examples/ are exempt).
  2. pytest       - the test suite passes (hook mode: the fast hooks/tests; CI: all).
  3. json-valid   - plugin.json, marketplace.json, hooks.json all parse.
  4. lf-endings   - no tracked *.py/*.sh/*.json contains a CRLF.
  5. version-bump - HOOK MODE ONLY (maintainer pre-commit): if anything under plugins/
                    changed vs origin/master, plugin.json version must differ. Skipped in
                    CI: bumping is a merge/release decision, not a contributor's PR gate.

Pure standard library; shells out to git and pytest via subprocess.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

EXCLUDE_DIRS = {"tests", "demos", "examples", "__pycache__", "scripts_examples"}
EXCLUDE_FILES = {"conftest.py", "__init__.py"}

# git commit / gh pr create detection (loose: over-matching only runs a passing gate).
_COMMIT_RE = re.compile(r"\bgit\b(?:\s+-\S+|\s+--\S+|\s+-C\s+\S+)*\s+commit\b")
_PR_RE = re.compile(r"\bgh\b.*\bpr\b.*\bcreate\b")


def _git(root, *args):
    try:
        out = subprocess.run(["git", *args], cwd=str(root), capture_output=True, text=True)
        return out.returncode, out.stdout, out.stderr
    except Exception:  # noqa: BLE001
        return 1, "", ""


def repo_root():
    rc, out, _ = _git(Path.cwd(), "rev-parse", "--show-toplevel")
    if rc == 0 and out.strip():
        return Path(out.strip())
    return None


def is_bitranox_skills(root):
    pj = root / "plugins" / "bitranox" / ".claude-plugin" / "plugin.json"
    if not pj.is_file():
        return False
    try:
        return json.loads(pj.read_text(encoding="utf-8")).get("name") == "bitranox"
    except Exception:  # noqa: BLE001
        return False


def _packages(root):
    """The hooks dir plus each skill dir - the units that must carry tests."""
    base = root / "plugins" / "bitranox"
    pkgs = [base / "hooks"]
    skills = base / "skills"
    if skills.is_dir():
        pkgs += [d for d in sorted(skills.iterdir()) if d.is_dir()]
    return [p for p in pkgs if p.is_dir()]


def _ships_scripts(pkg):
    for p in pkg.rglob("*.py"):
        rel_parts = set(p.relative_to(pkg).parts[:-1])
        if rel_parts & EXCLUDE_DIRS or p.name in EXCLUDE_FILES:
            continue
        return True
    return False


def _has_tests(pkg):
    for t in pkg.rglob("test_*.py"):
        if "examples" not in t.relative_to(pkg).parts and "demos" not in t.relative_to(pkg).parts:
            return True
    return False


def check_tests_exist(root):
    missing = [str(p.relative_to(root)) for p in _packages(root) if _ships_scripts(p) and not _has_tests(p)]
    if missing:
        return ["These packages ship .py but have no tests/test_*.py:"] + [f"  {m}" for m in missing]
    return []


def check_json_valid(root):
    targets = [
        root / "plugins" / "bitranox" / ".claude-plugin" / "plugin.json",
        root / ".claude-plugin" / "marketplace.json",
        root / "plugins" / "bitranox" / "hooks" / "hooks.json",
    ]
    bad = []
    for t in targets:
        if not t.is_file():
            continue
        try:
            json.loads(t.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            bad.append(f"  {t.relative_to(root)}: {exc}")
    return ["Invalid JSON:"] + bad if bad else []


def check_lf_endings(root):
    rc, out, _ = _git(root, "ls-files", "*.py", "*.sh", "*.json")
    if rc != 0:
        return []  # cannot enumerate -> do not block
    crlf = []
    for rel in out.splitlines():
        rel = rel.strip()
        if not rel:
            continue
        fp = root / rel
        try:
            if b"\r\n" in fp.read_bytes():
                crlf.append(f"  {rel}")
        except OSError:
            continue
    return ["Files contain CRLF (must be LF):"] + crlf if crlf else []


def check_version_bumped(root):
    rc, _, _ = _git(root, "rev-parse", "--verify", "origin/master")
    if rc != 0:
        return []  # no origin/master reference available -> skip, do not block
    rc, changed, _ = _git(root, "diff", "--name-only", "origin/master", "--", "plugins/bitranox")
    rc2, untracked, _ = _git(root, "ls-files", "--others", "--exclude-standard", "plugins/bitranox")
    plugin_changed = bool(changed.strip()) or bool(untracked.strip())
    if not plugin_changed:
        return []
    pj_rel = "plugins/bitranox/.claude-plugin/plugin.json"
    try:
        new_v = json.loads((root / pj_rel).read_text(encoding="utf-8")).get("version")
    except Exception:  # noqa: BLE001
        return []
    rc, old_blob, _ = _git(root, "show", f"origin/master:{pj_rel}")
    if rc != 0:
        return []
    try:
        old_v = json.loads(old_blob).get("version")
    except Exception:  # noqa: BLE001
        return []
    if new_v == old_v:
        return [
            f"plugins/ changed but plugin.json version is still {new_v} (== origin/master).",
            "Bump the version (the marketplace is append-only; updates ship via a version bump).",
        ]
    return []


def check_pytest(root, paths):
    target = [str(p) for p in paths if p.exists()]
    if not target:
        return []
    # import-mode=importlib: skill test files share basenames (e.g. two
    # test_strip_typographic_tells.py), which the default prepend mode cannot import
    # side by side. examples/ and demos/ are documentation, not convention tests -
    # exempt from tests-exist, so exempt from the run too.
    cmd = [
        sys.executable, "-m", "pytest", "-q",
        "--import-mode=importlib", "-p", "no:cacheprovider",
        "--ignore-glob=*/examples/*", "--ignore-glob=*/demos/*",
        *target,
    ]
    try:
        out = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True)
    except Exception as exc:  # noqa: BLE001
        return [f"Could not run pytest: {exc}"]
    if out.returncode == 5:  # no tests collected
        return []
    if out.returncode != 0:
        tail = (out.stdout or out.stderr).strip().splitlines()[-15:]
        return ["pytest failed:"] + [f"  {ln}" for ln in tail]
    return []


def run_checks(root, ci):
    failures = []
    failures += check_tests_exist(root)
    failures += check_json_valid(root)
    failures += check_lf_endings(root)
    # Version-bump is a release/merge concern owned by the maintainer, not a per-PR
    # gate: forcing contributors to bump causes plugin.json conflicts and takes the
    # version decision away from the merge. So enforce it ONLY in the local pre-commit
    # hook (compares the maintainer's working tree to origin/master right before a
    # push), never in CI on a contributor's PR.
    if not ci:
        failures += check_version_bumped(root)
    pytest_paths = [root] if ci else [root / "plugins" / "bitranox" / "hooks" / "tests"]
    failures += check_pytest(root, pytest_paths)
    return failures


def is_commit_or_pr(command):
    return bool(_COMMIT_RE.search(command) or _PR_RE.search(command))


def main():
    ci = "--ci" in sys.argv[1:]

    root = repo_root()
    if root is None or not is_bitranox_skills(root):
        if ci:
            print("repo-gate: not inside the bitranox-skills repo", file=sys.stderr)
            return 1
        return 0  # hook mode in some other repo: never interfere

    if not ci:
        try:
            event = json.load(sys.stdin)
        except Exception:  # noqa: BLE001
            return 0
        command = (event.get("tool_input") or {}).get("command") or ""
        if not is_commit_or_pr(command):
            return 0

    failures = run_checks(root, ci)

    if not failures:
        if ci:
            print("repo-gate: all checks passed.")
        return 0

    header = "repo-gate: commit blocked - fix these first:" if not ci else "repo-gate: FAILED"
    print("\n".join([header, *failures]), file=sys.stderr)
    return 1 if ci else 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - a broken gate must never wedge a turn
        sys.exit(0)
