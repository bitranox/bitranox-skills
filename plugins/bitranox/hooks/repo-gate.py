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
  7. changelog    - BOTH MODES: the version plugin.json names must have a `## [version]`
                    CHANGELOG.md heading. Stated as an invariant rather than a diff, because a
                    diff against origin/master is inert in CI on a push (by then the bump IS
                    origin/master). Pairs with version-bump: that one makes a shipped change
                    carry a version, this one makes a version carry its entry.

Pure standard library; shells out to git and pytest via subprocess.
"""

import difflib
import importlib.util
import json
import os
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

import harness_checks as hc  # noqa: E402
import shell_text  # noqa: E402

# Re-exported: these predicates are shared with the local-harness audit, which applies the same
# rules to the skills and hooks no plugin ships. One definition, so the two cannot drift apart.
EXCLUDE_DIRS = hc.EXCLUDE_DIRS
EXCLUDE_FILES = hc.EXCLUDE_FILES

# git commit / git push / gh pr create detection lives in `shell_text` now: a second hook asks the
# same question for its own reason (a commit is when work concludes, which is when the
# decision-review nudge fires), and two copies of this regex set would drift silently in both
# directions. Re-exported here because this module's own tests and callers name it.
is_gated_command = shell_text.is_gated_command


def _git(root, *args):
    try:
        out = subprocess.run(["git", *args], cwd=str(root), capture_output=True, text=True)
        return out.returncode, out.stdout, out.stderr
    except Exception:  # noqa: BLE001
        return 1, "", ""


def _git_paths(root, subcommand, *args):
    """Enumerate paths from git NUL-separated, so no path is ever C-quoted.

    Without `-z`, git renders any non-ASCII path through `core.quotePath`: the caller receives the
    literal `"f\\303\\244hig.py"`, quotes included, which names no file on disk. Every read of it
    then raises, a fail-open skips that file, and the scan reports clean on a file it never read -
    the failure mode a scanner cannot notice about itself. `os.fsdecode` round-trips a name in any
    encoding the filesystem allows, which plain text-mode decoding does not.

    Returns (returncode, paths); a non-zero rc yields an empty list, and callers fail open on it
    exactly as before - being unable to enumerate is not evidence of a violation.
    """
    try:
        out = subprocess.run(["git", subcommand, "-z", *args], cwd=str(root), capture_output=True)
    except Exception:  # noqa: BLE001
        return 1, []
    if out.returncode != 0:
        return out.returncode, []
    return 0, [os.fsdecode(p) for p in out.stdout.split(b"\0") if p]


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
    missing = [p.relative_to(root).as_posix() for p in hc.packages_missing_tests(_packages(root))]
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
            bad.append(f"  {t.relative_to(root).as_posix()}: {exc}")
    return ["Invalid JSON:"] + bad if bad else []


def check_lf_endings(root):
    rc, paths = _git_paths(root, "ls-files", "*.py", "*.sh", "*.json")
    if rc != 0:
        return []  # cannot enumerate -> do not block
    crlf = []
    for rel in paths:
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


def _table_checker(root):
    """The skill's own ragged-row detector, imported rather than re-implemented.

    A second copy of the fence-walking would drift from the one that ships, and then the gate would
    be enforcing a rule the tool does not apply.
    """
    tool = root / _SKILLS_DIR / "docs-md-table-formatting" / "reformat_tables.py"
    if not tool.is_file():
        return None
    spec = importlib.util.spec_from_file_location("_gate_reformat_tables", tool)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_ragged_tables(root):
    """No shipped markdown may hold a table row whose cell count differs from its header.

    Maintainer-only, and enforced HERE rather than by changing the tool's default: making
    `reformat_tables.py` exit non-zero by default would turn every install's CI red on a document
    the tool was only ever asked to align. This repo opts in for itself, which is where the
    findings were - three on the first sweep, one of them a routing row that named no file.

    A row with MORE cells than its header loses the surplus when GFM renders it; a row with FEWER
    renders an empty cell. Both are reported, because both mean the table does not say what it
    reads as saying.
    """
    module = _table_checker(root)
    if module is None:
        return []  # tool missing -> cannot enumerate, do not block
    rc, paths = _git_paths(root, "ls-files", "*.md")
    if rc != 0:
        return []
    findings = []
    for rel in paths:
        warnings = []
        try:
            module.reformat_file(root / rel, check_only=True, warnings=warnings)
        except (OSError, UnicodeDecodeError):
            continue
        findings.extend(f"  {line}" for line in warnings)
    return ["Ragged markdown table rows (cell count differs from the header):"] + findings \
        if findings else []


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
    rc, paths = _git_paths(root, "ls-files", "*.py")
    if rc != 0:
        return []                                     # cannot enumerate -> do not block
    by_name = {}
    for rel in paths:
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


CHANGELOG_NAME = "CHANGELOG.md"


def _plugin_version_pair(root):
    """`(old, new)` plugin.json version across origin/master, or None when undecidable.

    None means "cannot answer" - no origin/master to compare against, or a manifest that will
    not parse on either side - and every caller treats that as skip-do-not-block, which is the
    gate's standing rule: being unable to read something is not evidence of a violation.
    """
    rc, _, _ = _git(root, "rev-parse", "--verify", "origin/master")
    if rc != 0:
        return None
    pj_rel = "plugins/bitranox/.claude-plugin/plugin.json"
    try:
        new_v = json.loads((root / pj_rel).read_text(encoding="utf-8")).get("version")
    except Exception:  # noqa: BLE001
        return None
    rc, old_blob, _ = _git(root, "show", f"origin/master:{pj_rel}")
    if rc != 0:
        return None
    try:
        old_v = json.loads(old_blob).get("version")
    except Exception:  # noqa: BLE001
        return None
    return old_v, new_v


def check_version_bumped(root):
    pair = _plugin_version_pair(root)
    if pair is None:
        return []  # no origin/master reference available -> skip, do not block
    old_v, new_v = pair
    _, changed = _git_paths(root, "diff", "--name-only", "origin/master", "--", "plugins/bitranox")
    _, untracked = _git_paths(root, "ls-files", "--others", "--exclude-standard", "plugins/bitranox")
    plugin_changed = bool(changed) or bool(untracked)
    if not plugin_changed:
        return []
    if new_v == old_v:
        return [
            f"plugins/ changed but plugin.json version is still {new_v} (== origin/master).",
            "Bump the version (the marketplace is append-only; updates ship via a version bump).",
        ]
    return []


def changelog_documents(root, version):
    """Whether CHANGELOG.md carries a heading for `version`; None when there is no changelog.

    Two heading shapes ship in this file - the current `## [5.290.0]` and the older
    `## [5.207.0] - 2026-08-16` - so match the version INSIDE the brackets and allow a dated
    suffix. Looking for one literal string would pass every recent version and fail every
    historical one, which is the kind of check that reads as working because the cases you
    happen to test are all one shape.
    """
    try:
        text = (root / CHANGELOG_NAME).read_text(encoding="utf-8")
    except OSError:
        return None
    return bool(re.search(r"^## \[" + re.escape(version) + r"\]\s*(?:-.*)?$", text, re.M))


class VersionUnreadable(Exception):
    """pyproject.toml is present but its version could not be read, carrying the reason why.

    A reason rather than a bare None because the three causes send a reader to different places:
    a missing key is an edit to make, invalid TOML is a file to repair, and an interpreter with
    no tomllib is a toolchain to change. Reporting "no version could be read" for all three sent
    someone looking for a missing key that was sitting right there.
    """


def pyproject_version(root):
    """The version declared in pyproject.toml.

    Returns None ONLY when there is no pyproject.toml at all, which means this checkout is not a
    Python distribution. Every other way of not getting a version raises VersionUnreadable,
    because "there is nothing to check" and "I could not check" are different answers and
    collapsing them into one None is what let this check pass on unreadable input.

    There is deliberately no fallback parser for interpreters below 3.11. One shipped in 5.294.2
    and was removed: a hand-rolled TOML reader answers wrongly in silence, and only below 3.11
    where nothing exercises it, which trades a silent skip for a silent wrong answer. The repo
    declares requires-python >=3.11, so reporting is both honest and the same verdict everywhere.
    """
    pp = root / "pyproject.toml"
    if not pp.is_file():
        return None
    try:
        text = pp.read_text(encoding="utf-8")
    except OSError as exc:
        raise VersionUnreadable("pyproject.toml could not be read: %s" % exc)
    try:
        import tomllib  # noqa: PLC0415 - stdlib only from 3.11; absence is reported, not skipped
    except ImportError:
        raise VersionUnreadable(
            "this interpreter has no tomllib, which is stdlib from 3.11, and the repo declares "
            "requires-python >=3.11"
        )
    try:
        data = tomllib.loads(text)
    except Exception as exc:  # noqa: BLE001
        raise VersionUnreadable("pyproject.toml is not valid TOML: %s" % exc)
    version = data.get("project", {}).get("version")
    if version is None:
        raise VersionUnreadable("its [project] table declares no version key")
    return version


def check_version_sync(root):
    """pyproject.toml and plugin.json must name the SAME version.

    They are two copies because the build backend cannot read the plugin manifest, and the
    manifest is what the CLI reports at runtime. Left ungated they drift silently and the
    failure is invisible until a user runs it: measured the day this was written, a wheel
    built at 5.293.0 shipped a CLI whose --version answered 5.292.0, and every test passed,
    because nothing compared the two.

    Stated as an INVARIANT, for the reason check_changelog_current_version above is: every way
    of failing to learn a version is reported, because returning no failures is what this check
    says when the two versions AGREE, and a reader cannot tell that apart from never having
    read either file. The one legitimate skip is a checkout with no pyproject.toml, which is
    not a distribution and has no second version to disagree with.
    """
    if not (root / "pyproject.toml").is_file():
        return []  # not a Python distribution; there is no second version to disagree with
    try:
        declared = pyproject_version(root)
    except VersionUnreadable as exc:
        return [
            "pyproject.toml is present but its version could not be read: %s." % exc,
            "The wheel takes its version from that key, so passing here would report that",
            "the two versions agree having learned neither of them.",
        ]
    pj = root / "plugins" / "bitranox" / ".claude-plugin" / "plugin.json"
    try:
        manifest = json.loads(pj.read_text(encoding="utf-8")).get("version")
    except Exception:  # noqa: BLE001
        manifest = None
    if manifest is None:
        return [
            "plugin.json could not be read, or names no version: %s" % pj,
            "It is what the installed CLI reports at runtime, so an unreadable manifest is",
            "exactly the state that ships a tool misreporting its own version.",
        ]
    if declared == manifest:
        return []
    return [
        f"version drift: pyproject.toml says {declared}, plugin.json says {manifest}.",
        "They ship as one artifact - the wheel takes pyproject, the CLI reports the",
        "manifest - so a mismatch means the installed tool misreports its own version.",
    ]


def check_changelog_current_version(root):
    """The version plugin.json NAMES must have a CHANGELOG entry - whatever put it there.

    Deliberately not a diff: it asks nothing about what changed, so it cannot go quiet for want
    of something to compare against. The first form of this check did compare the working tree
    to origin/master, and measured 2026-08-31 with a control arm, that form is INERT in CI on a
    push to master - by the time CI runs, the commit that made the bump IS origin/master, the
    pair reads ('1.1.0', '1.1.0'), and a check that cannot see the bump reads exactly like one
    that looked and found nothing wrong.

    Stating the invariant instead makes it true everywhere the gate runs: the local pre-commit
    and pre-push hooks, CI on a push, and CI on a pull request, with no fetch-depth requirement.
    It also subsumes the diff form - a bump to an undocumented version fails this too - which is
    why there is one check here and not two reporting the same defect twice.
    """
    pj = root / "plugins" / "bitranox" / ".claude-plugin" / "plugin.json"
    try:
        version = json.loads(pj.read_text(encoding="utf-8")).get("version")
    except Exception:  # noqa: BLE001
        return []  # a manifest that will not parse is check_json_valid's verdict, not ours
    if not version:
        return []
    documented = changelog_documents(root, version)
    if documented is None:
        return [f"plugin.json names {version} but there is no {CHANGELOG_NAME} to record it."]
    if documented:
        return []
    return [
        f"plugin.json names {version}, which has no `## [{version}]` heading in {CHANGELOG_NAME}.",
        "Add the entry in THIS commit. A version reaches installs the moment it is pushed, and",
        "an entry deferred to later is reconstructed from a diff by whoever notices it missing.",
    ]


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
    rc, paths = _git_paths(root, "ls-files")
    if rc != 0:
        return []
    deny = [(t, t.lower()) for t in _denylist_terms(root)]
    findings = []
    for rel in paths:
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


# A run that collects nothing exits 5 and used to be treated as success, so a broken glob, a
# renamed directory or a conftest import error reported "all checks passed" having run no tests
# at all. The count floor catches the partial version of the same failure, which never reaches
# zero and so is invisible to the exit code alone.
# How far the collected count may fall below the recorded baseline before the gate objects.
# Marking a few tests POSIX-only is normal and must not block; losing a whole skill's tests is
# not. Measured on COLLECTED tests, never on "passed": Windows and macOS legitimately skip the
# POSIX-only ones, so a floor on passed would move with the platform instead of with coverage.
PYTEST_SLACK = 0.02
BASELINE_FILE = "pytest_baseline.json"

_PYTEST_SUMMARY_RX = re.compile(r"^\d+ (passed|failed).*", re.MULTILINE)


def expected_collected(root):
    """The recorded size of the suite, or 0 when there is no baseline to compare against."""
    try:
        raw = (Path(root) / "plugins" / "bitranox" / "hooks" / BASELINE_FILE).read_text(encoding="utf-8")
        return int(json.loads(raw)["collected"])
    except (OSError, ValueError, KeyError, TypeError):
        return 0


def pytest_argv(root, paths):
    """The exact pytest command the gate runs, so CI can invoke it without duplicating flags.

    import-mode=importlib keys modules by full path rather than basename. check_duplicate_basenames
    is what actually FORBIDS a collision; this flag only stops a stray one from silently
    substituting a module during the run, and it also covers the benign per-directory conftest.py.
    examples/ and demos/ are documentation, not convention tests - exempt from tests-exist, so
    exempt from the run too.
    """
    return [
        sys.executable, "-m", "pytest", "-q",
        "--import-mode=importlib", "-p", "no:cacheprovider",
        "--ignore-glob=*/examples/*", "--ignore-glob=*/demos/*",
        *[str(p) for p in paths],
    ]


def junit_total(path):
    """Total tests recorded in a pytest junit report, or None if it cannot be read.

    The count comes from the report rather than from scraped stdout because --pytest-only
    streams pytest straight to the CI log (that is the point of it), so there is no captured
    text to parse.
    """
    try:
        root = ET.parse(str(path)).getroot()
    except (OSError, ET.ParseError):
        return None
    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    total = 0
    for suite in suites:
        try:
            total += int(suite.get("tests", 0))
        except (TypeError, ValueError):
            return None
    return total


def floor_problems(report, baseline):
    """Fail closed: an unknown count is not evidence the suite ran."""
    if not baseline:
        return []  # no baseline recorded yet, so there is nothing to compare against
    total = junit_total(report)
    if total is None:
        return ["Could not read the pytest junit report at %s - test count unverified." % report,
                "  An unknown count fails closed; it is not evidence the suite ran."]
    floor = int(baseline * (1.0 - PYTEST_SLACK))
    if total < floor:
        return ["pytest collected only %d tests; the recorded baseline is %d (floor %d)."
                % (total, baseline, floor),
                "  A partial collection never reaches zero, so the exit code cannot see it.",
                "  If the suite legitimately shrank, update 'collected' in plugins/bitranox/hooks/%s"
                " in the same change." % BASELINE_FILE]
    return []


def check_pytest(root, paths, baseline=0):
    target = [p for p in paths if p.exists()]
    if not target:
        return []  # hook mode pointed at a tests dir that is absent: the one legitimate empty case
    with tempfile.TemporaryDirectory() as tmp:
        report = Path(tmp) / "junit.xml"
        return _check_pytest_run(root, target, report, baseline)


def _check_pytest_run(root, target, report, baseline):
    cmd = pytest_argv(root, target) + ["--junitxml=" + str(report)]
    try:
        # encoding is explicit because text=True alone decodes with the machine locale codec,
        # which is cp1252 on a German Windows and corrupts any non-ASCII test output.
        out = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True,
                             encoding="utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001
        return [f"Could not run pytest: {exc}"]
    text = out.stdout or out.stderr or ""
    if out.returncode == 5:
        return ["pytest collected no tests - the suite did not run.",
                "  An empty run is a defect, not a pass: check the target paths and conftest imports."]
    if out.returncode != 0:
        tail = text.strip().splitlines()[-15:]
        return ["pytest failed:"] + [f"  {ln}" for ln in tail]
    problems = floor_problems(report, baseline)
    if problems:
        return problems
    summary = _PYTEST_SUMMARY_RX.search(text)
    if summary:  # the gate used to discard this, leaving CI with no evidence any test ran
        print("  pytest: " + summary.group(0).strip())
    return []


# ---- skill review artifact + CSO description lint (skill-usage enforcement) ---------------------

#: Where this plugin keeps its skills, relative to the repo root. Derived from once, so a
#: relocation cannot leave one check looking in the old place.
_SKILLS_DIR = "plugins/bitranox/skills"
_SKILL_MD_RX = re.compile(r"^%s/([^/]+)/SKILL\.md$" % re.escape(_SKILLS_DIR))
_CSO_STOP = hc.CSO_STOP


def _changed_vs_origin(root):
    """Worktree+index+untracked paths changed vs origin/master (the maintainer pre-commit view)."""
    rc, _, _ = _git(root, "rev-parse", "--verify", "origin/master")
    if rc != 0:
        return None
    _, changed = _git_paths(root, "diff", "--name-only", "origin/master")
    _, untracked = _git_paths(root, "ls-files", "--others", "--exclude-standard")
    return changed + untracked


def skill_review_failures(root, changed):
    """A changed SKILL.md needs a co-changed, fully-checked .skillwriter/checklist-*.md - the
    skill-writer procedure's committed receipt. Prose discipline gets cherry-picked; a required
    artifact does not."""
    fails = []
    names = sorted({m.group(1) for p in changed for m in [_SKILL_MD_RX.match(p)] if m})
    for name in names:
        prefix = "%s/%s/.skillwriter/" % (_SKILLS_DIR, name)
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


def frontmatter_failures(root):
    """EVERY shipped SKILL.md must have front matter a parser accepts, and only ONE of them.

    `cso_failures` above cannot reach this: it lints the description that `frontmatter_description`
    already recovered, and that reader is a regex over the first `---` split, so it recovers a
    value from a block no YAML parser would accept and from a file carrying a second block. Those
    checks lived only in `frontmatter_problems`, whose sole caller audits LOCAL unshipped skills -
    so the marketplace's own commits were never gated by them.

    Unlike its neighbours this sweeps the WHOLE skills dir rather than the changed paths. Changed-
    only would rebuild the blind spot the check exists to close: the descriptions that prompted it
    survived because nothing ever swept the full set, and a defect can arrive in an untouched file
    through a merge, a mirror sync, or an edit made outside the hook. The sweep costs milliseconds
    over 81 files."""
    return hc.frontmatter_problems(root / _SKILLS_DIR)


def check_frontmatter(root):
    return frontmatter_failures(root)


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
    "infra-soundtouch-decloud": "apps/utils/soundtouch-decloud/skills/soundtouch-decloud",
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


# Neither side ships these to the other: `.skillwriter` is the marketplace's own commit receipt and
# the rest are build or tool output. One of these appearing in a twin would otherwise block every
# commit touching that skill, for a file no reader ever sees.
MIRROR_IGNORED_DIRS = {".skillwriter", "__pycache__", ".pytest_cache", ".git", ".ruff_cache"}


def mirror_files(skill_dir):
    """Map every comparable file in a mirrored skill dir to its path, keyed by relative posix path."""

    found = {}
    for path in sorted(Path(skill_dir).rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(skill_dir)
        if MIRROR_IGNORED_DIRS & set(rel.parts):
            continue
        found[rel.as_posix()] = path
    return found


def mirror_failures(root, names):
    """Return a failure per mirrored skill in ``names`` whose twin has drifted.

    A mirrored skill is a DIRECTORY. Several pairs ship `references/` and `scripts/` beside their
    `SKILL.md`, and comparing only `SKILL.md` let three changed reference and script files sit
    unreported while this check printed "in sync" - an absence claim that is wrong is worse than
    no check, because it is the answer the reader hoped for.

    `SKILL.md` is compared through `normalise_mirror`, which erases the three by-convention
    divergences. Every other file must match byte for byte: nothing about them is per-repo.
    """

    public = _public_tree(root)
    if public is None:
        return []
    fails = []
    for name in sorted(names):
        relative = MIRRORED_SKILLS.get(name)
        if relative is None:
            continue
        here_dir = Path(root) / "plugins" / "bitranox" / "skills" / name
        twin_dir = public / relative
        if not (here_dir / "SKILL.md").exists() or not (twin_dir / "SKILL.md").exists():
            # The tool repo is not checked out on this machine, so there is nothing to
            # compare against. Silence is right: the audit mode reports the skip.
            continue
        mine_files, their_files = mirror_files(here_dir), mirror_files(twin_dir)
        differing, sample = [], []
        for rel in sorted(set(mine_files) | set(their_files)):
            mine, theirs = mine_files.get(rel), their_files.get(rel)
            if mine is None:
                differing.append("%s (only in the twin)" % rel)
            elif theirs is None:
                differing.append("%s (only in the marketplace)" % rel)
            elif rel == "SKILL.md":
                a = normalise_mirror(theirs.read_text(encoding="utf-8"))
                b = normalise_mirror(mine.read_text(encoding="utf-8"))
                if a != b:
                    differing.append(rel)
                    sample = [line for line in difflib.unified_diff(a.splitlines(), b.splitlines(), "twin", "marketplace", lineterm="", n=0) if line[:1] in "+-" and line[:3] not in ("---", "+++")]
            elif mine.read_bytes() != theirs.read_bytes():
                differing.append(rel)
        if not differing:
            continue
        detail = "\n      ".join(sample[:6]) if sample else "\n      ".join(differing[:6])
        fails.append(
            "skills/%s has drifted from its twin at %s (%d differing file(s): %s). Regenerate the "
            "stale side from the other, re-apply only the name/H1/self-install divergences, and "
            "bump that repo's plugin.json. First lines:\n      %s"
            % (name, relative, len(differing), ", ".join(differing[:6]), detail)
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
                found.append((name, twin.parent.relative_to(public).as_posix()))
    return found


def run_checks(root, ci, full_pytest=None, run_pytest=True, baseline=0):
    """`ci` picks the CHECK SET (CI omits the maintainer-only ones); `full_pytest` picks the pytest
    SCOPE and defaults to `ci`. They are separate axes because a pre-push is BOTH: the maintainer
    (so version-bump, skill-review and mirrors apply) and the last gate before CI (so it runs the
    whole suite CI runs, not just hooks/tests)."""
    if full_pytest is None:
        full_pytest = ci
    failures = []
    failures += check_tests_exist(root)
    failures += check_json_valid(root)
    failures += check_lf_endings(root)
    failures += check_duplicate_basenames(root)
    failures += check_skills_index(root)
    failures += check_attribution(root)
    failures += check_skill_naming(root)
    failures += check_cso(root)
    failures += check_frontmatter(root)
    failures += check_secrets(root)
    # Runs in BOTH modes, unlike version-bump below. It compares nothing across refs, so CI can
    # answer it on a push - which is the case the maintainer-only placement cannot cover, and the
    # one that lets a version ship undocumented from a clone with no hooks enabled.
    failures += check_changelog_current_version(root)
    failures += check_version_sync(root)
    # Version-bump is a release/merge concern owned by the maintainer, not a per-PR
    # gate: forcing contributors to bump causes plugin.json conflicts and takes the
    # version decision away from the merge. So enforce it ONLY in the local pre-commit
    # hook (compares the maintainer's working tree to origin/master right before a
    # push), never in CI on a contributor's PR.
    if not ci:
        failures += check_version_bumped(root)
        failures += check_ragged_tables(root)
        failures += check_skill_review(root)
        failures += check_skill_mirrors(root)
    # Preflight the dependencies, and run pytest only when they are all there. Running it anyway
    # would report the SAME problem a second time as a failed assertion in an unrelated test,
    # and that second message is the one a reader acts on.
    if not run_pytest:
        return failures  # CI runs the suite as its own step so GitHub renders the results
    missing_deps = check_test_dependencies(root)
    failures += missing_deps
    if not missing_deps:
        pytest_paths = [root] if full_pytest else [root / "plugins" / "bitranox" / "hooks" / "tests"]
        failures += check_pytest(root, pytest_paths, baseline=baseline if full_pytest else 0)
    return failures


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
    if not is_gated_command((event.get("tool_input") or {}).get("command") or "", event.get("tool_name")):
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
    pre_push = "--pre-push" in args
    run_pytest = "--no-pytest" not in args

    if "--print-test-deps" in args:
        # The pre-push hook builds its `uv run --with ...` line from this, so the dependency set
        # stays declared in exactly one place (the CI workflow) instead of being copied into a
        # shell script that would drift the first time CI gains a package.
        root = repo_root()
        if root is None:
            return 1
        print("\n".join(ci_test_dependencies(root)))
        return 0

    if "--pytest-only" in args:
        # The CI test step. It runs the suite WITHOUT capturing, so pytest's own output lands in
        # the CI log live - the gate used to swallow it, leaving a green run with no evidence any
        # test had run. The count is then read from the junit report and held to the floor.
        root = repo_root()
        if root is None:
            return 1
        # The report goes to a temp dir, never the repo root: a stray junit.xml there would
        # dirty the working tree and could be committed by a pathspec-less `git add`.
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "junit.xml"
            cmd = pytest_argv(root, [root]) + ["--junitxml=" + str(report)]
            rc = subprocess.run(cmd, cwd=str(root)).returncode
            problems = floor_problems(report, expected_collected(root)) if rc == 0 else []
        if rc == 5:
            print("repo-gate: pytest collected no tests - the suite did not run.", file=sys.stderr)
            return 1
        if rc != 0:
            return rc
        if problems:
            for line in problems:
                print(line, file=sys.stderr)
            return 1
        return 0

    if "--mirror-of" in args:
        # Runs from INSIDE a tool repo, so it must not require the marketplace as cwd:
        # it locates the marketplace from the shared public/ tree itself.
        index = args.index("--mirror-of")
        target = args[index + 1] if len(args) > index + 1 else "."
        return audit_mirror_of(target)

    root = repo_root()
    if root is None or not is_bitranox_skills(root):
        if pre_push:
            # Someone pointed core.hooksPath here from another repo. Say so rather than blocking
            # a push this gate knows nothing about.
            print("repo-gate: not inside the bitranox-skills repo - pre-push checks skipped",
                  file=sys.stderr)
            return 0
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

    if not (ci or pre_push):
        try:
            event = json.load(sys.stdin)
        except Exception:  # noqa: BLE001
            return 0
        command = (event.get("tool_input") or {}).get("command") or ""
        if not is_gated_command(command, event.get("tool_name")):
            return 0

    # A real git pre-push hook receives REF LINES on stdin, never a Claude Code event, so it must
    # not go through the parse above - that read fails and returns 0, passing the gate by accident
    # on the one caller that fires when git runs OUTSIDE Claude Code (a terminal, an IDE, a
    # script). That blind spot is how a stale generated catalog shipped twice.
    failures = run_checks(root, ci, full_pytest=ci or pre_push,
                          run_pytest=run_pytest, baseline=expected_collected(root))

    if not failures:
        if ci or pre_push:
            print("repo-gate: all checks passed.")
        return 0

    header = ("repo-gate: FAILED" if ci else
              "repo-gate: push blocked - fix these first:" if pre_push else
              "repo-gate: commit/push blocked - fix these first:")
    print("\n".join([header, *failures]), file=sys.stderr)
    return 2 if not (ci or pre_push) else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001 - a broken gate must never wedge a turn
        sys.exit(0)
