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

# git commit / gh pr create detection. Anchored at a COMMAND position (statement start, after a shell
# separator) so the literal text "git commit" inside a quoted string or heredoc body - e.g. a CHANGELOG
# line ABOUT committing - does NOT trip the gate. Over-matching is NOT harmless: it false-fires the
# version-bump BLOCK, since plugins/ is normally dirty-and-not-yet-bumped mid-work.
_SEP = re.compile(r"&&|\|\||[;\n|]")
_COMMIT_RE = re.compile(r"^(?:\w+=\S+\s+)*git\b(?:\s+-C\s+\S+|\s+--?\S+)*\s+commit\b")
_PR_RE = re.compile(r"^(?:\w+=\S+\s+)*gh\b.*\bpr\b.*\bcreate\b")


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


def check_skills_index(root):
    """Keep the meta-using-bitranox-skills domains list in sync with the skill dirs.

    Every shipped skill must be listed there (so the orientation list stays complete),
    and every name listed must be a real skill dir (so a rename/removal cannot leave a
    dangling entry). This is the deterministic guard for "update the index when you add
    or rename a skill" - the rule prose alone kept silently breaking.
    """
    skills_dir = root / "plugins" / "bitranox" / "skills"
    index = skills_dir / "meta-using-bitranox-skills" / "SKILL.md"
    if not skills_dir.is_dir() or not index.is_file():
        return []
    try:
        text = index.read_text(encoding="utf-8")
    except OSError:
        return []
    # Collect backtick-quoted skill names from the bullet lines of the domains section.
    listed = set()
    in_section = False
    for line in text.splitlines():
        if line.startswith("## "):
            in_section = line.startswith("## Skills Span Every Domain")
            continue
        if in_section and line.lstrip().startswith("- "):
            listed.update(re.findall(r"`([a-z][a-z0-9-]+)`", line))
    dirs = {d.name for d in skills_dir.iterdir() if d.is_dir() and (d / "SKILL.md").is_file()}
    dirs.discard("meta-using-bitranox-skills")
    missing = sorted(dirs - listed)
    stale = sorted(listed - dirs)
    msgs = []
    if missing:
        msgs.append("meta-using-bitranox-skills omits these skills (add to its domains list): " + ", ".join(missing))
    if stale:
        msgs.append("meta-using-bitranox-skills lists non-existent skills (renamed/removed?): " + ", ".join(stale))
    return msgs


_CREDIT_RX = re.compile(r"(?m)^>\s*Adapted from .+\(.+\)\.")
_NOTICE_HEADING_RX = re.compile(r"(?m)^###\s+([a-z][a-z0-9-]+)\s*$")


def check_attribution(root):
    """Keep license-attribution credit lines and THIRD_PARTY_NOTICES.md entries in sync.

    A skill adapted from a third-party source carries a `> Adapted from <src> (<LICENSE>).`
    credit line at the top of its SKILL.md; the permissive licenses we accept require the
    notice to ship, so each such skill must also have a `### <name>` entry in
    plugins/bitranox/THIRD_PARTY_NOTICES.md - and no notice may dangle without a credit line.
    Deterministic guard for the attribution rule (CONTRIBUTING.md), so it cannot silently rot.
    """
    skills_dir = root / "plugins" / "bitranox" / "skills"
    notices = root / "plugins" / "bitranox" / "THIRD_PARTY_NOTICES.md"
    if not skills_dir.is_dir():
        return []
    credited = set()
    for sk in sorted(skills_dir.iterdir()):
        md = sk / "SKILL.md"
        if sk.is_dir() and md.is_file():
            try:
                if _CREDIT_RX.search(md.read_text(encoding="utf-8")):
                    credited.add(sk.name)
            except OSError:
                continue
    noticed = set()
    if notices.is_file():
        try:
            noticed = set(_NOTICE_HEADING_RX.findall(notices.read_text(encoding="utf-8")))
        except OSError:
            noticed = set()
    if not credited and not noticed:
        return []
    msgs = []
    missing = sorted(credited - noticed)
    orphan = sorted(noticed - credited)
    if missing:
        msgs.append("Skills credit an upstream but have no THIRD_PARTY_NOTICES.md entry: "
                    + ", ".join(missing))
    if orphan:
        msgs.append("THIRD_PARTY_NOTICES.md entries with no matching '> Adapted from' credit line: "
                    + ", ".join(orphan))
    return msgs


def _load_taxonomy(root):
    tax = root / "plugins" / "bitranox" / "skill-taxonomy.json"
    try:
        return json.loads(tax.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 - missing/invalid registry: caller fail-opens
        return None


def check_skill_naming(root):
    """Every skill dir must use an approved category prefix from skill-taxonomy.json.

    Names are <category>-[<sub>-]<name>; the top-level <category> must be a key in the registry's
    'categories' (sub-prefixes stay free-form). Existing flat names in 'legacy' are grandfathered
    until a future retrofit. Fail-open if the registry is absent/invalid so a missing file never
    blocks commits. This is what forces the scheme on every NEW skill and makes opening a category a
    deliberate registry edit.
    """
    skills_dir = root / "plugins" / "bitranox" / "skills"
    tax = _load_taxonomy(root)
    if not skills_dir.is_dir() or not tax:
        return []
    cats = set((tax.get("categories") or {}).keys())
    legacy = set(tax.get("legacy") or [])
    if not cats:
        return []
    bad = []
    for d in sorted(skills_dir.iterdir()):
        if not (d.is_dir() and (d / "SKILL.md").is_file()):
            continue
        if d.name in legacy or d.name.split("-", 1)[0] in cats:
            continue
        bad.append(d.name)
    if bad:
        return [
            "Skills must use an approved category prefix (<category>-...) per skill-taxonomy.json, "
            "or be grandfathered in its 'legacy' list - these do not: " + ", ".join(bad),
            "  approved categories: " + ", ".join(sorted(cats)),
            "  to open a new category, add it to skill-taxonomy.json (see CONTRIBUTING.md).",
        ]
    return []


# High-signal credential formats that are never legitimate in a shipped skill. Standard
# secret-scanner patterns (gitleaks/trufflehog family); low false-positive by construction.
_SECRET_RX = [
    (re.compile(r"ghp_[A-Za-z0-9]{36,}"), "GitHub token"),
    # Installation tokens (ghs_) are now long JWT-format strings (~520 chars) carrying
    # dots/dashes/underscores, so the body allows ".-_" and is open-ended on length.
    (re.compile(r"ghs_[A-Za-z0-9._-]{36,}"), "GitHub App installation token"),
    (re.compile(r"github_pat_[A-Za-z0-9_]{60,}"), "GitHub fine-grained PAT"),
    (re.compile(r"\bsk-ant-[A-Za-z0-9_-]{24,}"), "Anthropic API key"),
    (re.compile(r"\bsk-[A-Za-z0-9]{40,}\b"), "OpenAI-style key"),
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AWS access key id"),
    (re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"), "Google API key"),
    (re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}"), "Slack token"),
    (re.compile(r"\bglpat-[A-Za-z0-9_-]{20}\b"), "GitLab token"),
]
# A complete private key block. The body must lack a "..." truncation marker and carry real
# base64, so an illustrative/elided example (e.g. the rpyc tutorial's key) does not trip it.
_PRIVKEY_RX = re.compile(
    r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----([\s\S]{20,8000}?)-----END [A-Z0-9 ]*PRIVATE KEY-----"
)
_SENSITIVE_NAME_RX = re.compile(
    r"(^|/)(\.env(\.[^/]*)?|id_rsa|id_dsa|id_ecdsa|id_ed25519|.*\.pem|.*\.p12|.*\.pfx|"
    r"\.netrc|\.htpasswd|.*\.kdbx)$|credentials?\.(json|ya?ml|toml|txt)$",
    re.IGNORECASE,
)


def _denylist_terms(root):
    """Maintainer's private-infra terms, loaded from a LOCAL (gitignored / out-of-repo) file so
    the terms themselves are never published in this shipped hook. Absent on contributor/CI
    machines -> that part of the scan is simply skipped (the maintainer's pre-commit catches it)."""
    candidates = [root / ".security-denylist.local",
                  Path.home() / ".config" / "bitranox" / "security-denylist.txt"]
    for cand in candidates:
        try:
            if cand.is_file():
                return [ln.strip() for ln in cand.read_text(encoding="utf-8").splitlines()
                        if ln.strip() and not ln.lstrip().startswith("#")]
        except OSError:
            pass
    return []


def check_secrets(root):
    """Block credentials, private keys, sensitive files, and (locally) denylisted infra terms.
    Runs on every commit and PR, so the credential class of leak can never land. The judgment
    class (generic vs real IPs/domains) is left to the documented human/agent security review."""
    rc, listing, _ = _git(root, "ls-files")
    if rc != 0:
        return []
    deny = [(t, t.lower()) for t in _denylist_terms(root)]
    findings = []
    for rel in listing.splitlines():
        rel = rel.strip()
        if not rel:
            continue
        if _SENSITIVE_NAME_RX.search(rel):
            findings.append(f"  {rel}: sensitive filename")
        fp = root / rel
        try:
            raw = fp.read_bytes()
        except OSError:
            continue
        if b"\x00" in raw[:4096] or len(raw) > 2_000_000:
            continue  # binary or oversized
        text = raw.decode("utf-8", "replace")
        for rx, label in _SECRET_RX:
            if rx.search(text):
                findings.append(f"  {rel}: possible {label}")
        for m in _PRIVKEY_RX.finditer(text):
            body = m.group(1)
            if "..." not in body and len(re.sub(r"[^A-Za-z0-9+/=]", "", body)) > 64:
                findings.append(f"  {rel}: embedded private key")
                break
        low = text.lower()
        for orig, term in deny:
            if term in low:
                findings.append(f"  {rel}: denylisted infra term '{orig}'")
    if findings:
        return ["Potential secrets / private data (security gate) - remove or genericize:"] + sorted(set(findings))
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


# ---- skill review artifact + CSO description lint (skill-usage enforcement) ---------------------

_SKILL_MD_RX = re.compile(r"^plugins/bitranox/skills/([^/]+)/SKILL\.md$")
_CSO_STOP = {
    "use", "when", "the", "and", "for", "with", "that", "this", "from", "into", "your", "you",
    "are", "was", "has", "have", "not", "but", "its", "any", "all", "one", "how", "what", "why",
    "where", "which", "should", "must", "can", "will", "also", "such", "them", "then", "than",
    "good", "need", "want", "like", "just",
}


def _changed_vs_origin(root):
    """Worktree+index+untracked paths changed vs origin/master (the maintainer pre-commit view)."""
    rc, _, _ = _git(root, "rev-parse", "--verify", "origin/master")
    if rc != 0:
        return None
    rc, changed, _ = _git(root, "diff", "--name-only", "origin/master")
    rc2, untracked, _ = _git(root, "ls-files", "--others", "--exclude-standard")
    return [p for p in (changed.splitlines() + untracked.splitlines()) if p.strip()]


def skill_review_failures(root, changed):
    """A changed SKILL.md needs a co-changed, fully-checked .skillwriter/checklist-*.md - the
    skill-writer procedure's committed receipt. Prose discipline gets cherry-picked; a required
    artifact does not."""
    fails = []
    names = sorted({m.group(1) for p in changed for m in [_SKILL_MD_RX.match(p)] if m})
    for name in names:
        prefix = "plugins/bitranox/skills/%s/.skillwriter/" % name
        arts = [p for p in changed if p.startswith(prefix) and p.endswith(".md")]
        if not arts:
            fails.append("skills/%s/SKILL.md changed without an updated .skillwriter/checklist-*.md "
                         "in the same change - run bitranox:meta-skill-writer and commit its "
                         "checklist artifact." % name)
            continue
        for a in arts:
            try:
                text = (root / a).read_text(encoding="utf-8")
            except OSError:
                continue
            if "[ ]" in text:
                fails.append("%s has unchecked boxes - finish the skill-writer checklist before "
                             "committing." % a)
    return fails


def check_skill_review(root):
    changed = _changed_vs_origin(root)
    if changed is None:
        return []
    return skill_review_failures(root, changed)


def _frontmatter_description(path):
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    if not text.startswith("---"):
        return None
    fm = text.split("---", 2)[1]
    m = re.search(r"^description:\s*(.+(?:\n(?![a-zA-Z_-]+:).*)*)", fm, re.M)
    return " ".join(m.group(1).split()) if m else None


def cso_failures(root, changed):
    """A changed skill description must be trigger-first ('Use when ...') and yield distinctive
    keywords - that is what makes it router-derivable and findable (the CSO rules)."""
    fails = []
    for p in changed:
        m = _SKILL_MD_RX.match(p)
        if not m:
            continue
        desc = _frontmatter_description(root / p)
        if desc is None:
            continue
        if not desc.lower().startswith("use "):
            fails.append("skills/%s: description must be trigger-first ('Use when <situations>...'), "
                         "never a summary of what the skill does (CSO rule)." % m.group(1))
            continue
        kws = {t for t in re.findall(r"[a-z0-9][a-z0-9_-]{3,}", desc.lower())
               if t not in _CSO_STOP}
        if len(kws) < 3:
            fails.append("skills/%s: description yields fewer than 3 distinctive keywords - the "
                         "skill router cannot derive triggers from it; name concrete situations, "
                         "tools, and symptoms." % m.group(1))
    return fails


def check_cso(root):
    changed = _changed_vs_origin(root)
    if changed is None:
        return []
    return cso_failures(root, changed)



def run_checks(root, ci):
    failures = []
    failures += check_tests_exist(root)
    failures += check_json_valid(root)
    failures += check_lf_endings(root)
    failures += check_skills_index(root)
    failures += check_attribution(root)
    failures += check_skill_naming(root)
    failures += check_cso(root)
    failures += check_secrets(root)
    # Version-bump is a release/merge concern owned by the maintainer, not a per-PR
    # gate: forcing contributors to bump causes plugin.json conflicts and takes the
    # version decision away from the merge. So enforce it ONLY in the local pre-commit
    # hook (compares the maintainer's working tree to origin/master right before a
    # push), never in CI on a contributor's PR.
    if not ci:
        failures += check_version_bumped(root)
        failures += check_skill_review(root)
    pytest_paths = [root] if ci else [root / "plugins" / "bitranox" / "hooks" / "tests"]
    failures += check_pytest(root, pytest_paths)
    return failures


def is_commit_or_pr(command):
    # Match per statement, anchored at its start, so "git commit" embedded in a quoted string or
    # heredoc body does not count - only an actual `git commit` / `gh pr create` command does.
    for seg in _SEP.split(command or ""):
        seg = seg.strip().lstrip("(").strip()
        if _COMMIT_RE.match(seg) or _PR_RE.match(seg):
            return True
    return False


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
