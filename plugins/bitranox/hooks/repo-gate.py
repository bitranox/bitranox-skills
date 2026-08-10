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
  6. skill-mirrors - HOOK MODE ONLY: a skill that also ships from its own tool repo must
                    match that twin apart from the documented divergences. Local only,
                    because the twins are sibling repos that a CI clone does not have.
                    Run `repo-gate.py --mirrors` to audit every pair, changed or not.

Pure standard library; shells out to git and pytest via subprocess.
"""

import difflib
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

import harness_checks as hc  # noqa: E402

# Re-exported: these predicates are shared with the local-harness audit, which applies the same
# rules to the skills and hooks no plugin ships. One definition, so the two cannot drift apart.
EXCLUDE_DIRS = hc.EXCLUDE_DIRS
EXCLUDE_FILES = hc.EXCLUDE_FILES

# git commit / gh pr create detection. Anchored at a COMMAND position (statement start, after a shell
# separator) so the literal text "git commit" inside a quoted string or heredoc body - e.g. a CHANGELOG
# line ABOUT committing - does NOT trip the gate. Over-matching is NOT harmless: it false-fires the
# version-bump BLOCK, since plugins/ is normally dirty-and-not-yet-bumped mid-work.
_SEP = re.compile(r"&&|\|\||[;\n|]")
_COMMIT_RE = re.compile(r"^(?:\w+=\S+\s+)*git\b(?:\s+-C\s+\S+|\s+--?\S+)*\s+commit\b")
_PR_RE = re.compile(r"^(?:\w+=\S+\s+)*gh\b.*\bpr\b.*\bcreate\b")
_PUSH_RE = re.compile(r"^(?:\w+=\S+\s+)*git\b(?:\s+-C\s+\S+|\s+--?\S+)*\s+push\b")


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


_ships_scripts = hc.ships_scripts
_has_tests = hc.has_tests


def check_tests_exist(root):
    missing = [str(p.relative_to(root)) for p in hc.packages_missing_tests(_packages(root))]
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


# pytest handles a per-directory conftest.py specially, so every test dir legitimately has one.
_BENIGN_DUPLICATE_BASENAMES = frozenset({"conftest.py"})
# Same exemption the pytest run makes: these trees are documentation, not convention.
_VENDORED_DIRNAMES = frozenset({"demos", "examples"})


def check_duplicate_basenames(root):
    """Two shipped .py files must not share a basename.

    Python resolves an import to the FIRST match on sys.path, so with two same-named modules the
    one collected first wins for an entire run and the other directory's tests silently exercise a
    file nobody changed. Nothing announces it: both suites stay green, the shadowed file's real
    coverage is zero, and a fix in it reads as absent in the full run while passing in isolation.

    The pytest invocation here passes --import-mode=importlib, which lets such a pair be IMPORTED
    side by side - that keeps the run working but hides the collision rather than surfacing it,
    and it does nothing for any other tool or for a consumer importing these modules. Two real
    duplications shipped in this plugin before this check existed.
    """
    rc, out, _ = _git(root, "ls-files", "*.py")
    if rc != 0:
        return []                                     # cannot enumerate -> do not block
    by_name = {}
    for rel in out.splitlines():
        rel = rel.strip()
        if not rel:
            continue
        parts = Path(rel).parts
        if _VENDORED_DIRNAMES.intersection(parts):
            continue
        name = Path(rel).name
        if name in _BENIGN_DUPLICATE_BASENAMES:
            continue
        by_name.setdefault(name, []).append(rel)
    duplicates = {n: paths for n, paths in by_name.items() if len(paths) > 1}
    if not duplicates:
        return []
    lines = ["Two or more .py files share a basename - a whole-repo pytest run imports only the "
             "first, so the other directory's tests exercise the wrong file while both suites "
             "stay green. Ship the module once and import it, or rename:"]
    for name in sorted(duplicates):
        lines.append("  %s:" % name)
        for path in sorted(duplicates[name]):
            lines.append("    %s" % path)
    return lines


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
    """Every skill NAME the meta-using-bitranox-skills orientation list mentions must be a real
    skill dir (a rename/removal cannot leave a dangling entry). The reverse direction is
    deliberately NOT enforced: the roster is category names + exemplars, and the injected
    available-skills list is the source of truth for completeness."""
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
    stale = sorted(listed - dirs)
    if stale:
        return ["meta-using-bitranox-skills lists non-existent skills (renamed/removed?): "
                + ", ".join(stale)]
    return []


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


# A test that exercises an optional backend fails on its ASSERTION when the backend is absent,
# not on the import - so a missing dependency reads as a code defect. Measured: no lxml in the
# interpreter running the gate turned a green tree into a convincing red one, and the reported
# failure named an XML entity assertion, pointing at code nobody had touched in months.
_PIP_TO_IMPORT = {"pyyaml": "yaml"}


def ci_test_dependencies(root):
    """The packages CI installs before pytest, read from the workflow so the two cannot drift."""
    try:
        text = (root / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    except OSError:
        return []  # no workflow, so no claim about CI parity to make
    names = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("pip install "):
            continue  # skips "python -m pip install --upgrade pip", which installs no test dep
        names += [tok for tok in stripped[len("pip install "):].split() if not tok.startswith("-")]
    return names


def module_installed(module):
    """True if `module` can be found by the interpreter that will run pytest."""
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError):
        return False  # a missing PARENT raises here rather than returning None (ruamel.yaml)


def check_test_dependencies(root, is_installed=None):
    """Name a missing test dependency, rather than letting it surface as somebody's failed assert."""
    probe = is_installed or module_installed
    declared = ci_test_dependencies(root)
    missing = [n for n in declared if not probe(_PIP_TO_IMPORT.get(n.lower(), n))]
    if not missing:
        return []
    return [
        "Test dependencies missing from %s - this gate cannot match CI without them:" % sys.executable,
        "  missing: " + " ".join(missing),
        "  install: pip install " + " ".join(missing),
        "  or run the gate with the full CI set:",
        "    uv run " + " ".join("--with " + n for n in declared)
        + " python plugins/bitranox/hooks/repo-gate.py --ci",
    ]


def check_pytest(root, paths):
    target = [str(p) for p in paths if p.exists()]
    if not target:
        return []
    # import-mode=importlib keys modules by full path rather than basename. check_duplicate_basenames
    # above is what actually FORBIDS a collision; this flag only stops a stray one from silently
    # substituting a module during the run, and it also covers the benign per-directory conftest.py.
    # examples/ and demos/ are documentation, not convention tests - exempt from tests-exist, so
    # exempt from the run too.
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
_CSO_STOP = hc.CSO_STOP


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


_frontmatter_description = hc.frontmatter_description


def cso_failures(root, changed):
    """A changed skill description must be a single-line plain YAML scalar, trigger-first
    ('Use when ...'), and yield distinctive keywords - that is what makes it router-derivable
    and findable (the CSO rules). Block scalars (`>-`/`|`) and quoted scalars leak their
    style markers into the derived catalog and trigger map."""
    fails = []
    for p in changed:
        m = _SKILL_MD_RX.match(p)
        if not m:
            continue
        desc = hc.frontmatter_description(root / p)
        if desc is None:
            continue
        fails.extend(hc.cso_failures_for("skills/%s" % m.group(1), desc))
    return fails


def check_cso(root):
    changed = _changed_vs_origin(root)
    if changed is None:
        return []
    return cso_failures(root, changed)



#: Skills that ship from BOTH this marketplace and their own tool repo, mapped to the
#: twin's path under the shared `public/` tree. The two copies must stay identical apart
#: from the divergences below, and both directions drift: a marketplace edit that is never
#: mirrored back leaves the tool repo's own installers a release behind, and a repo edit
#: that is never mirrored forward leaves this marketplace describing behaviour the tool
#: dropped. Measured 2026-07-30: the coding-python-network-probe mirror still told an agent
#: that a default sweep refuses to run, two ipscout releases after it stopped doing that.
MIRRORED_SKILLS = {
    "coding-python-gitignore": "libs/igittigitt/skills/python-gitignore",
    "coding-python-layered-config": "libs/lib_layered_config/skills/python-layered-config",
    "coding-python-network-probe": "libs/ipscout/skills/python-network-probe",
    "coding-python-new-public-library": "libs/bitranox_template_py_lib/skills/new-public-python-library",
    "coding-python-pwshpy": "apps/utils/pwshpy/skills/using-pwsh",
    "coding-python-send-mail": "libs/btx_lib_mail/skills/python-send-mail",
    # The REPO dir is underscored (vnc_remote_control) while the SKILL dir inside it is
    # hyphenated. Spelling both with hyphens pointed this entry at nothing, so the mirror
    # check skipped compuse-vnc silently - the exact "degrades to skipped forever" failure
    # the twin-exists test below guards against.
    "compuse-vnc": "apps/utils/vnc_remote_control/skills/vnc-remote-control",
    "devops-bmk": "apps/utils/bmk/skills/devops-bmk",
    "infra-proxmox-bindsnap": "apps/pve-bindsnap/skills/proxmox-bindsnap",
    "infra-storage-check-zpools": "apps/utils/check_zpools/skills/check-zpools",
}

#: The self-install note only the tool repo's copy carries: there it is true and useful,
#: here it would tell a reader to add a marketplace they are already inside. Matched
#: against a whole blockquote rather than one line, because it wraps over several and a
#: line-at-a-time rule leaves the continuation behind and reports it as drift.
_SELF_INSTALL_RX = re.compile(r"/plugin marketplace add|/plugin install", re.I)


def _public_tree(root):
    """Return the shared `public/` tree holding the tool repos, or None off this machine."""

    for parent in Path(root).resolve().parents:
        if parent.name == "public":
            return parent
    return None


def normalise_mirror(text):
    """Return the comparable body of a mirrored SKILL.md.

    Three divergences are by convention, not drift, so they are erased rather than
    reported: the `name:` field (each copy uses its own repo's skill name), the same name
    echoed in the H1, and the tool repo's self-install blockquote. Everything else is
    content, and content that differs between the copies is drift by definition.
    """

    source = text.splitlines()
    lines = []
    index = 0
    while index < len(source):
        line = source[index]
        if line.startswith("> "):
            end = index
            while end < len(source) and source[end].startswith(">"):
                end += 1
            block = source[index:end]
            index = end
            if not _SELF_INSTALL_RX.search("\n".join(block)):
                lines.extend(block)
            continue
        index += 1
        if line.startswith("name:"):
            lines.append("name: <per-repo>")
        elif line.startswith("# "):
            lines.append(re.sub(r"\s*\([^()]*\)\s*$", " (<per-repo>)", line))
        else:
            lines.append(line)
    # A dropped blockquote leaves a blank line behind on the side that carried it.
    joined = "\n".join(lines)
    while "\n\n\n" in joined:
        joined = joined.replace("\n\n\n", "\n\n")
    return joined.strip() + "\n"


def mirror_failures(root, names):
    """Return a failure per mirrored skill in ``names`` whose twin has drifted."""

    public = _public_tree(root)
    if public is None:
        return []
    fails = []
    for name in sorted(names):
        relative = MIRRORED_SKILLS.get(name)
        if relative is None:
            continue
        here = Path(root) / "plugins" / "bitranox" / "skills" / name / "SKILL.md"
        twin = public / relative / "SKILL.md"
        if not here.exists() or not twin.exists():
            # The tool repo is not checked out on this machine, so there is nothing to
            # compare against. Silence is right: the audit mode reports the skip.
            continue
        mine, theirs = normalise_mirror(here.read_text(encoding="utf-8")), normalise_mirror(twin.read_text(encoding="utf-8"))
        if mine == theirs:
            continue
        sample = [line for line in difflib.unified_diff(theirs.splitlines(), mine.splitlines(), "twin", "marketplace", lineterm="", n=0) if line[:1] in "+-" and line[:3] not in ("---", "+++")]
        fails.append(
            "skills/%s has drifted from its twin at %s (%d differing lines). Regenerate the "
            "stale side from the other, re-apply only the name/H1/self-install divergences, and "
            "bump that repo's plugin.json. First lines:\n      %s"
            % (name, relative, len(sample), "\n      ".join(sample[:6]))
        )
    return fails


def check_skill_mirrors(root):
    """Gate the mirrored twin of every skill this change touches.

    Scoped to what changed, like the review and description checks: pre-existing drift in
    a skill nobody is editing must not block an unrelated commit, and the maintainer has
    ``--mirrors`` for the full sweep.
    """

    changed = _changed_vs_origin(root)
    if changed is None:
        return []
    touched = {m.group(1) for m in (_SKILL_MD_RX.match(p) for p in changed) if m}
    return mirror_failures(root, touched & set(MIRRORED_SKILLS))


def audit_mirror_of(tool_repo):
    """Print the state of the mirrored pair belonging to one tool repo.

    The counterpart to ``--mirrors`` for the other side of the mirror: a release pipeline
    running inside a tool repo asks only about ITS pair, because another repo's drift is
    not a reason to block this release. Returns 1 if that pair has drifted, else 0, and
    says so and returns 0 when there is nothing to compare - the repo ships no mirrored
    skill, or this machine has no marketplace checkout - so it is safe to run everywhere.
    """

    tool = Path(tool_repo).resolve()
    public = _public_tree(tool / "x")  # _public_tree looks at parents, so descend one
    if public is None:
        print("mirror check: no public/ tree above %s - nothing to compare" % tool)
        return 0
    marketplace = public / "KI" / "bitranox-skills"
    if not (marketplace / "plugins" / "bitranox" / "skills").is_dir():
        print("mirror check: no bitranox-skills checkout at %s - nothing to compare" % marketplace)
        return 0
    mine = sorted(name for name, rel in MIRRORED_SKILLS.items() if (public / rel).resolve().is_relative_to(tool))
    if not mine:
        print("mirror check: %s ships no skill mirrored in bitranox-skills" % tool.name)
        return 0
    fails = mirror_failures(marketplace, set(mine))
    for name in mine:
        print("%-8s%-34s %s" % ("DRIFT" if any(name in f for f in fails) else "in sync", name, MIRRORED_SKILLS[name]))
    for failure in fails:
        print("\n" + failure)
    return 1 if fails else 0


def audit_mirrors(root):
    """Print the state of every mirrored pair. Returns the number that have drifted."""

    public = _public_tree(root)
    if public is None:
        print("no public/ tree above %s - nothing to compare" % root)
        return 0
    drifted = 0
    for name in sorted(MIRRORED_SKILLS):
        relative = MIRRORED_SKILLS[name]
        twin = public / relative / "SKILL.md"
        if not twin.exists():
            print("SKIP    %-34s twin not checked out: %s" % (name, relative))
            continue
        fails = mirror_failures(root, {name})
        if fails:
            drifted += 1
            print("DRIFT   %-34s %s" % (name, relative))
            print("        " + fails[0].split("First lines:\n")[-1].strip()[:400])
        else:
            print("in sync %-34s %s" % (name, relative))
    for unlisted in unlisted_mirrors(root, public):
        print("UNLISTED %-33s %s" % unlisted)
    print("\n%d of %d mirrored pairs have drifted." % (drifted, len(MIRRORED_SKILLS)))
    return drifted


def _description(path):
    """Return a SKILL.md's description line, collapsed to one line."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    match = re.search(r"^description:\s*(.+)$", text, re.M)
    return " ".join(match.group(1).split()) if match else ""


def unlisted_mirrors(root, public):
    """Return (marketplace skill, repo path) pairs that look mirrored but are not listed.

    A skill and its twin keep the same description by convention, so an exact match on
    that line is a reliable tell. The manifest is hand-maintained and a missing entry is
    invisible - it simply stops checking that pair - which is how
    coding-python-layered-config went unchecked until a scan found it.
    """
    listed = {(public / rel).resolve() for rel in MIRRORED_SKILLS.values()}
    catalog = {}
    for skill in sorted((Path(root) / "plugins" / "bitranox" / "skills").glob("*/SKILL.md")):
        description = _description(skill)
        if description:
            catalog.setdefault(description, skill.parent.name)

    found = []
    for pattern in ("*/*/skills/*/SKILL.md", "*/*/*/skills/*/SKILL.md"):
        for twin in sorted(public.glob(pattern)):
            if twin.parent.resolve() in listed or "bitranox-skills" in twin.parts:
                continue
            name = catalog.get(_description(twin))
            if name:
                found.append((name, str(twin.parent.relative_to(public))))
    return found


def run_checks(root, ci):
    failures = []
    failures += check_tests_exist(root)
    failures += check_json_valid(root)
    failures += check_lf_endings(root)
    failures += check_duplicate_basenames(root)
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
        failures += check_skill_mirrors(root)
    # Preflight the dependencies, and run pytest only when they are all there. Running it anyway
    # would report the SAME problem a second time as a failed assertion in an unrelated test,
    # and that second message is the one a reader acts on.
    missing_deps = check_test_dependencies(root)
    failures += missing_deps
    if not missing_deps:
        pytest_paths = [root] if ci else [root / "plugins" / "bitranox" / "hooks" / "tests"]
        failures += check_pytest(root, pytest_paths)
    return failures


def is_gated_command(command):
    # Match per statement, anchored at its start, so "git commit"/"git push" embedded in a quoted
    # string or heredoc body does not count - only an actual git commit / git push / gh pr create
    # command does. Push is gated too: the push is the moment a change reaches CI, and a commit made
    # where this hook did not fire (a cross-repo `git -C` from another project, or docs regenerated
    # between commit and push) would otherwise sail straight through to a red CI run.
    for seg in _SEP.split(command or ""):
        seg = seg.strip().lstrip("(").strip()
        if _COMMIT_RE.match(seg) or _PR_RE.match(seg) or _PUSH_RE.match(seg):
            return True
    return False


def gate_tool_repo_mirror(root):
    """Check the mirror of a skill edited in its OWN repo, before it is committed.

    The gate fires on every ``git commit``/``git push`` on the machine, but it used to
    return 0 in any repo that is not the marketplace. That left the tool-repo side of a
    mirrored pair unguarded, which is the side that actually drifted: measured twice on
    ``coding-python-network-probe``, which described a subsystem as absent two releases
    after it shipped.

    Returns 2 to block a drifted pair, 0 otherwise. Silent when this repo owns no
    mirrored skill, so it does not narrate in every unrelated repo.

    The "cannot compare" case is deliberately NOT a bare 0. With no marketplace checkout
    there is nothing to diff, and passing in silence is indistinguishable from passing
    because the pair is in sync - which would make this guard permanently green and
    worthless. It still passes, because blocking would break anyone without the
    checkout, but it says so through ``additionalContext``, the one exit-0 channel the
    model actually reads (plain stdout/stderr on exit 0 does not reach it).
    """

    if root is None:
        return 0
    try:
        event = json.load(sys.stdin)
    except Exception:  # noqa: BLE001
        return 0
    if not is_gated_command((event.get("tool_input") or {}).get("command") or ""):
        return 0

    public = _public_tree(root / "x")
    if public is None:
        return 0
    mine = sorted(name for name, rel in MIRRORED_SKILLS.items() if (public / rel).resolve().is_relative_to(root))
    if not mine:
        return 0

    marketplace = public / "KI" / "bitranox-skills"
    if not (marketplace / "plugins" / "bitranox" / "skills").is_dir():
        _say_unverifiable(mine, marketplace)
        return 0

    fails = mirror_failures(marketplace, set(mine))
    if not fails:
        return 0
    for name in mine:
        print("%-8s%-34s %s" % ("DRIFT" if any(name in f for f in fails) else "in sync", name, MIRRORED_SKILLS[name]))
    for failure in fails:
        print("\n" + failure)
    print("repo-gate: blocked - a skill this repo ships has drifted from its marketplace twin.", file=sys.stderr)
    return 2


def _say_unverifiable(names, marketplace):
    """Tell the model the mirror could not be checked, rather than exiting 0 in silence."""

    note = (
        "repo-gate: could not verify the marketplace mirror of %s - no bitranox-skills checkout at %s. "
        "The commit is allowed, but nothing confirmed the twin is in sync; run "
        "'repo-gate.py --mirror-of <this repo>' where the marketplace is checked out." % (", ".join(names), marketplace)
    )
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": note}}))



def main():
    args = sys.argv[1:]
    ci = "--ci" in args
    mirrors = "--mirrors" in args

    if "--mirror-of" in args:
        # Runs from INSIDE a tool repo, so it must not require the marketplace as cwd:
        # it locates the marketplace from the shared public/ tree itself.
        index = args.index("--mirror-of")
        target = args[index + 1] if len(args) > index + 1 else "."
        return audit_mirror_of(target)

    root = repo_root()
    if root is None or not is_bitranox_skills(root):
        if ci or mirrors:
            print("repo-gate: not inside the bitranox-skills repo", file=sys.stderr)
            return 1
        # Hook mode outside the marketplace. Not "never interfere" any more: if THIS repo
        # ships a skill mirrored into the marketplace, the pair is checked from this side
        # too. Everything else still passes untouched.
        return gate_tool_repo_mirror(root)

    if mirrors:
        # The full sweep the commit gate deliberately does not do: it reports every pair,
        # including the ones no current change touches.
        return 1 if audit_mirrors(root) else 0

    if not ci:
        try:
            event = json.load(sys.stdin)
        except Exception:  # noqa: BLE001
            return 0
        command = (event.get("tool_input") or {}).get("command") or ""
        if not is_gated_command(command):
            return 0

    failures = run_checks(root, ci)

    if not failures:
        if ci:
            print("repo-gate: all checks passed.")
        return 0

    header = "repo-gate: commit/push blocked - fix these first:" if not ci else "repo-gate: FAILED"
    print("\n".join([header, *failures]), file=sys.stderr)
    return 1 if ci else 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - a broken gate must never wedge a turn
        sys.exit(0)
