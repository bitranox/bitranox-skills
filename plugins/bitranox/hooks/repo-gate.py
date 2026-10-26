#!/usr/bin/env python3
"""Pre-commit / CI gate for the bitranox-skills marketplace repo.

Enforces the repo's mandatory invariants in two interchangeable modes that share one
set of checks:

  * Hook mode (default): PreToolUse(Bash|PowerShell). Reads the event JSON on stdin and acts ONLY
    when the command is a `git commit` or `gh pr create`. On a violation it exits 2 to
    block the commit and prints what to fix; otherwise exits 0. Every error path exits 0
    so a broken gate never wedges a turn.
  * CI mode (`--ci`): runs the same checks against the working tree, prints a summary,
    and exits 1 on any violation (0 otherwise). Meant for GitHub Actions as a reporting
    check.

Exit codes of the CLI modes (--ci, --pre-push, --mirrors, --mirror-of, --pytest-only,
--print-test-deps): 0 clean, 1 a finding, 2 the gate could not run - it crashed, ran outside the
repo, lacked CI's test dependencies, or pytest did not produce a test result (could not start,
collected nothing, a collection/usage/internal error). 2 wins over 1: a run that could not finish
is not a complete list of findings. Only hook mode keeps the never-wedge rule that a crash exits 0.

CRITICAL: this plugin is installed globally, so the Bash|PowerShell hook fires in EVERY repo the
user commits in. The gate first verifies it is actually inside the bitranox-skills repo
(plugins/bitranox/.claude-plugin/plugin.json with name "bitranox"). In any other repo it runs
none of the checks below; the one thing it does there is `gate_tool_repo_mirror`: if that repo
ships a skill mirrored into the marketplace and the pair has drifted, a commit is blocked (exit
2). A repo that ships no mirrored skill passes silently (exit 0); one whose twin cannot be
compared (no marketplace checkout) passes and says so through additionalContext.

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
                    The side being committed is read at its index (commit) or HEAD (push),
                    except that a commit taking files from disk itself (`-a`, `-i <paths>`,
                    `<paths>`) is read as git will build it (`CommitSelection`);
                    the other side at its published ref plus what it committed since, so
                    another session's half-done edit never blocks a commit. A commit that
                    matches the other side's uncommitted text EXACTLY passes with a notice to
                    commit that side next (a change made to both copies at once); a push
                    never does. Never fetches. In a tool repo, a push that sends only tags
                    is not checked (`pushes_only_tags`): a tag ships no SKILL.md, and the
                    release order pushes the tag before the twin may name its version. The
                    tag must already exist when the push is judged, so create it in an
                    earlier command; a name that resolves to nothing stays gated.
                    Run `repo-gate.py --mirrors` to audit every pair, changed or not, at the
                    newest text of both sides, with any ref last fetched over 7 days ago named.
  7. changelog    - BOTH MODES: the version plugin.json names must have a `## [version]`
                    CHANGELOG.md heading. Stated as an invariant rather than a diff, because a
                    diff against origin/master is inert in CI on a push (by then the bump IS
                    origin/master). Pairs with version-bump: that one makes a shipped change
                    carry a version, this one makes a version carry its entry.

Pure standard library; shells out to git and pytest via subprocess.
"""

import contextlib
import difflib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import tomllib
import traceback
import xml.etree.ElementTree as ET
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

import harness_checks as hc  # noqa: E402
import shell_text  # noqa: E402
import secret_patterns  # noqa: E402

# git commit / git push / gh pr create detection lives in `shell_text` now: a second hook asks the
# same question for its own reason (a commit is when work concludes, which is when the
# decision-review nudge fires), and two copies of this regex set would drift silently in both
# directions. Re-exported here because this module's own tests and callers name it.
is_gated_command = shell_text.is_gated_command


def _git(root, *args, env=None):
    try:
        out = subprocess.run(["git", *args], cwd=str(root), capture_output=True, text=True,
                             encoding="utf-8", errors="replace", env=env)
        return out.returncode, out.stdout, out.stderr
    except Exception:  # noqa: BLE001
        return 1, "", ""


def _git_paths(root, subcommand, *args, env=None):
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
        out = subprocess.run(["git", subcommand, "-z", *args], cwd=str(root), capture_output=True, env=env)
    except Exception:  # noqa: BLE001
        return 1, []
    if out.returncode != 0:
        return out.returncode, []
    return 0, [os.fsdecode(p) for p in out.stdout.split(b"\0") if p]


def repo_root(start=None):
    rc, out, _ = _git(Path(start) if start else Path.cwd(), "rev-parse", "--show-toplevel")
    if rc == 0 and out.strip():
        return Path(out.strip())
    return None


def hook_root(event):
    """The repository a gated hook command lands in, or None; see `hook_landing`."""
    return hook_landing(event)[0]


def hook_landing(event):
    """(the repository a gated hook command lands in or None, whether that was a FALLBACK guess).

    A hook runs where the SESSION sits, not where `cd <repo> && git commit` or `git -C <repo> push`
    lands. Measured 2026-09-27: commits made that way from a session parked in a stale main
    checkout were judged against that checkout, so five unbumped plugins/ commits passed and two
    later ones were blocked for a version they did not carry.

    Falls back to the session's own repository when the command does not move, or moves somewhere
    the text cannot name (`cd "$X"` with an `X` the command did not assign a literal) or that does
    not exist (a Windows path whose backslashes the tokenizer ate) - that is the old behaviour, so
    an unreadable command is no worse than before.
    A readable target outside any repository gives None: the git command fails there by itself,
    and there is nothing to judge.

    The second value is True exactly when the command moved somewhere the text could not name and
    the session's repository was judged instead, so a block can say so: measured 2026-10-19, such a
    fallback blocked a commit for a repository it was not touching, and the message gave no hint.
    """
    command = (event.get("tool_input") or {}).get("command") or ""
    base = os.path.normpath(event.get("cwd") or os.getcwd())
    target = shell_text.git_verb_dir(command, base, shell_text.GATED_GIT_VERBS, event.get("tool_name"))
    if target and os.path.normcase(target) == os.path.normcase(base):
        return repo_root(), False
    if not target or not os.path.isdir(target):
        return repo_root(), True
    return repo_root(target), False


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


#: The file kinds `.gitattributes` pins to `eol=lf`, and so the ones the LF check reads.
_LF_SUFFIXES = (".py", ".sh", ".json")
#: Index and tree modes of a regular file; a symlink's blob is its target and a gitlink has none.
_REGULAR_MODES = frozenset({"100644", "100755"})


def _listed_blobs(root, args, env=None):
    """(rc, [(sha, path)]) of the LF-checked regular files `ls-files -s` or `ls-tree -r` lists."""
    rc, rows = _git_paths(root, *args, env=env)
    found = []
    for row in rows:
        meta, _, rel = row.partition("\t")
        fields = meta.split()
        if len(fields) == 3 and fields[0] in _REGULAR_MODES and rel.endswith(_LF_SUFFIXES):
            found.append((fields[2] if args[0] == "ls-tree" else fields[1], rel))
    return rc, list(dict.fromkeys(found))     # an unmerged path is listed once per stage


def _shipped_blobs(root, stage):
    """(rc, [(sha, path)]) of the blobs a commit or push at ``stage`` ships: HEAD's on a push, the
    index's on a commit, and the selection's on a commit that takes files from disk itself
    (`CommitSelection`; the index when git cannot build it, as `shipped_files` does)."""
    if not _is_commit(stage):
        return _listed_blobs(root, ("ls-tree", "-r", "HEAD"))
    if isinstance(stage, CommitSelection):
        with _selection_index(root, stage) as env:
            if env is not None:
                return _listed_blobs(root, ("ls-files", "-s"), env=env)
    return _listed_blobs(root, ("ls-files", "-s"))


def _blobs_with_crlf(root, blobs):
    """The paths among ``blobs`` whose blob holds a CRLF, read in ONE `git cat-file --batch`; None
    when git cannot read them."""
    if not blobs:
        return []
    try:
        out = subprocess.run(["git", "cat-file", "--batch"], cwd=str(root), capture_output=True,
                             input="".join(sha + "\n" for sha, _ in blobs).encode("ascii"))
    except OSError:                          # no git to run
        return None
    if out.returncode != 0:
        return None
    data, at, crlf = out.stdout, 0, []
    for _sha, rel in blobs:
        end = data.find(b"\n", at)
        header = data[at:end].split()
        if end < 0 or len(header) != 3:
            return None                      # `<sha> missing`, or output this reader cannot follow
        size = int(header[2])
        if b"\r\n" in data[end + 1:end + 1 + size]:
            crlf.append(rel)
        at = end + 1 + size + 1
    return crlf


def check_lf_endings(root, stage=None):
    """Refuse CRLF in a .py/.sh/.json BLOB the commit or push ships (``stage``, default the index).

    The blob, never the checkout ([620]): under Git for Windows' default core.autocrlf=true an LF
    blob is checked out with CRLF, so reading the working tree blocked every correct commit there,
    and it passed a staged CRLF blob whose checkout had been put back to LF."""
    rc, blobs = _shipped_blobs(root, STAGE_INDEX if stage is None else stage)
    crlf = _blobs_with_crlf(root, blobs) if rc == 0 else None
    if not crlf:
        return []  # clean, or cannot enumerate or read -> do not block
    return ["Files contain CRLF (must be LF):"] + [f"  {rel}" for rel in crlf]


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
        absolute = root / rel
        try:
            module.reformat_file(absolute, check_only=True, warnings=warnings)
        except (OSError, UnicodeDecodeError):
            continue
        # The tool echoes back the path it was handed, so report it the way git names it:
        # repo-relative, forward slashes. An absolute path drags the runner's home into the
        # message, and its separator is native - which is what made the Windows cell red while
        # the check itself was working.
        prefix = str(absolute)
        findings.extend(
            f"  {rel}{line[len(prefix):]}" if line.startswith(prefix) else f"  {line}"
            for line in warnings
        )
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

    A reason rather than a bare None because the causes send a reader to different places: a
    missing key is an edit to make, and an unreadable file or invalid TOML is a file to repair.
    Reporting "no version could be read" for all of them sent someone looking for a missing key
    that was sitting right there.
    """


def pyproject_version(root):
    """The version declared in pyproject.toml.

    Returns None ONLY when there is no pyproject.toml at all, which means this checkout is not a
    Python distribution. Every other way of not getting a version raises VersionUnreadable,
    because "there is nothing to check" and "I could not check" are different answers and
    collapsing them into one None is what let this check pass on unreadable input.
    """
    pp = root / "pyproject.toml"
    if not pp.is_file():
        return None
    try:
        text = pp.read_text(encoding="utf-8")
    except OSError as exc:
        raise VersionUnreadable("pyproject.toml could not be read: %s" % exc)
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
        data = json.loads(tax.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 - missing/invalid registry: caller fail-opens
        return None
    # Valid JSON of the wrong shape (a list) is as invalid as a parse error; read as a dict it
    # crashed the whole gate on `.get`.
    return data if isinstance(data, dict) else None


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
        # The credential formats and the real-key-block rule live in secret_patterns, shared
        # with recall and the classifier's egress redaction.
        for label in secret_patterns.find_secret_labels(text):
            findings.append(f"  {rel}: possible {label}")
        if next(secret_patterns.real_private_key_blocks(text), None):
            findings.append(f"  {rel}: embedded private key")
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


class _CouldNotRun(str):
    """A failure line that means the check could not run, not that it found something.

    Every check returns plain message lines, and the CLI modes have to tell the two kinds apart:
    a gate that could not run exits 2, one that found a violation exits 1. Tagging the line keeps
    the one list every check already returns, so the hook-mode printer needs no change."""


def could_not_run(lines):
    """Mark `lines` as a could-not-run failure (the first line carries the tag)."""
    if not lines:
        return []
    return [_CouldNotRun(lines[0]), *lines[1:]]


def is_could_not_run(lines):
    """True when any line in `lines` was marked by `could_not_run`."""
    return any(isinstance(line, _CouldNotRun) for line in lines)


def check_test_dependencies(root, is_installed=None):
    """Name a missing test dependency, rather than letting it surface as somebody's failed assert."""
    probe = is_installed or module_installed
    declared = ci_test_dependencies(root)
    missing = [n for n in declared if not probe(_PIP_TO_IMPORT.get(n.lower(), n))]
    if not missing:
        return []
    return could_not_run([
        "Test dependencies missing from %s - this gate cannot match CI without them:" % sys.executable,
        "  missing: " + " ".join(missing),
        "  install: pip install " + " ".join(missing),
        "  or run the gate with the full CI set:",
        "    uv run " + " ".join("--with " + n for n in declared)
        + " python plugins/bitranox/hooks/repo-gate.py --ci",
    ])


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
        return could_not_run([
            "Could not read the pytest junit report at %s - test count unverified." % report,
            "  An unknown count fails closed; it is not evidence the suite ran."])
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
        return could_not_run([f"Could not run pytest: {exc}"])
    text = out.stdout or out.stderr or ""
    if out.returncode == 5:
        return could_not_run([
            "pytest collected no tests - the suite did not run.",
            "  An empty run is a defect, not a pass: check the target paths and conftest imports."])
    if out.returncode != 0:
        tail = [f"  {ln}" for ln in text.strip().splitlines()[-15:]]
        if out.returncode == 1:
            return ["pytest failed:"] + tail  # tests ran and some failed: a finding
        # 2 interrupted (a module that cannot be imported lands here), 3 internal error, 4 usage
        # error, negative a signal: pytest produced no test result to judge.
        return could_not_run(["pytest did not complete (exit %d):" % out.returncode] + tail)
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


def _changed_vs_origin(root):
    """Worktree+index+untracked paths changed vs origin/master (the maintainer pre-commit view)."""
    rc, _, _ = _git(root, "rev-parse", "--verify", "origin/master")
    if rc != 0:
        return None
    # `diff origin/master` compares the WORKING TREE, so a staged change whose working copy was
    # reverted afterwards was missing - yet that staged text is exactly what the commit carries.
    _, changed = _git_paths(root, "diff", "--name-only", "origin/master")
    _, staged = _git_paths(root, "diff", "--cached", "--name-only", "origin/master")
    _, untracked = _git_paths(root, "ls-files", "--others", "--exclude-standard")
    return list(dict.fromkeys(changed + staged + untracked))


def _table_rows(lines, tool):
    """Per line: (leading whitespace, blockquote prefix, row) for a markdown table row, else None.

    Decided the way the formatter decides it (`_reformat_lines`), with its own fence scanner, so a
    pipe line inside a non-markdown fence or an indented code block is literal text, not a row.
    The front matter is never a table: it is YAML the router reads, so a row-shaped line there is
    content whatever its padding.
    """
    front_end = -1
    if lines and lines[0].strip() == "---":
        front_end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), len(lines))
    rows = []
    in_table = False
    for index, (line, cls) in enumerate(zip(lines, tool.classify_lines(lines))):
        found = None
        if index > front_end and cls.kind == tool.TEXT:
            bq_prefix, content = tool.strip_blockquote(line.strip())
            is_row = content.startswith("|") and "|" in content[1:]
            if is_row and not in_table:
                is_row = not tool.is_indented_code(lines, index, cls.floor, cls.base)
            if is_row:
                found = (line[: len(line) - len(line.lstrip(" \t"))], bq_prefix, content)
        in_table = found is not None
        rows.append(found)
    return rows


def _row_problem(number, old_row, new_row, is_separator, tool):
    """Why the changed line `number` is more than padding, or None when it is padding only."""
    if old_row is None or new_row is None:
        return "line %d is not a table row" % number
    if old_row[:2] != new_row[:2]:
        return "line %d: the row's indentation or blockquote prefix changed" % number
    old_cells, new_cells = tool.split_table_row(old_row[2]), tool.split_table_row(new_row[2])
    if not is_separator:
        return None if old_cells == new_cells else "line %d: a table cell changed" % number
    marks = [[tool.parse_separator_cell(c) for c in cells] for cells in (old_cells, new_cells)]
    if marks[0] == marks[1] and all(valid for _, _, valid in marks[0]):
        return None
    return "line %d: the alignment of a column changed" % number


def table_padding_problem(old, new, tool):
    """Return why `new` differs from `old` by more than table padding, or None when it does not.

    Table padding only means: the same line count, every changed line a table row on both sides
    with the same indentation and blockquote prefix, every cell equal after stripping, and every
    separator cell keeping its alignment markers. Whether `new` is canonical is the caller's
    question: it needs the file the formatter would rewrite, not two strings.
    """
    old_lines = [line.rstrip("\r") for line in old.split("\n")]
    new_lines = [line.rstrip("\r") for line in new.split("\n")]
    if len(old_lines) != len(new_lines):
        return "the line count changed (%d -> %d)" % (len(old_lines), len(new_lines))
    old_rows, new_rows = _table_rows(old_lines, tool), _table_rows(new_lines, tool)
    for index, (before, after) in enumerate(zip(old.split("\n"), new.split("\n"))):
        if before == after:
            continue
        # The second row of a table is its separator; any other row's cells are text a reader sees.
        is_separator = index > 0 and new_rows[index - 1] is not None and (
            index < 2 or new_rows[index - 2] is None)
        problem = _row_problem(index + 1, old_rows[index], new_rows[index], is_separator, tool)
        if problem:
            return problem
    return None


def _origin_text(root, rel):
    """The origin/master text of `rel` as a checkout here would write it, or None."""
    data = _checked_out_bytes(root, "origin/master", rel)
    return None if data is None else data.decode("utf-8", errors="replace")


def table_repad_problem(root, rel, read_original=None):
    """Why the changed SKILL.md `rel` is NOT a waivable table re-pad, or None when it is.

    The waiver exists because the reformat-md-tables hook rewrites a non-canonical table in every
    fresh worktree, and the checklist requirement then fires for a skill nobody edited. It is
    granted on a proof, never on a judgement: padding only against origin/master (see
    `table_padding_problem`), and canonical per the shipped formatter, so the hook will not
    rewrite it again.
    """
    tool = _table_checker(root)
    if tool is None:
        return "the table formatter is not shipped here, so a re-pad cannot be proven"
    old = (read_original or (lambda path: _origin_text(root, path)))(rel)
    if old is None:
        return "it has no origin/master version to compare against"
    try:
        with open(root / rel, encoding="utf-8", newline="") as handle:
            new = handle.read()
    except (OSError, UnicodeDecodeError):
        return "it cannot be read"
    problem = table_padding_problem(old, new, tool)
    if problem:
        return problem
    if tool.reformat_file(root / rel, check_only=True):
        return "its tables are not in the canonical form reformat_tables writes"
    return None


def skill_review_failures(root, changed, read_original=None):
    """A changed SKILL.md needs a co-changed, fully-checked .skillwriter/checklist-*.md - the
    skill-writer procedure's committed receipt. Prose discipline gets cherry-picked; a required
    artifact does not.

    One mechanical exception, waived only on proof: a change that re-pads tables and nothing else
    (`table_repad_problem`). `read_original(rel)` returns the origin/master text, or None; it
    defaults to reading git and is a parameter so tests need no remote."""
    fails = []
    names = sorted({m.group(1) for p in changed for m in [_SKILL_MD_RX.match(p)] if m})
    for name in names:
        prefix = "%s/%s/.skillwriter/" % (_SKILLS_DIR, name)
        arts = [p for p in changed if p.startswith(prefix) and p.endswith(".md")]
        if not arts:
            not_a_repad = table_repad_problem(root, "%s/%s/SKILL.md" % (_SKILLS_DIR, name),
                                              read_original)
            if not_a_repad is None:
                continue
            fails.append("skills/%s/SKILL.md changed without an updated .skillwriter/checklist-*.md "
                         "in the same change - run bitranox:meta-skill-writer and commit its "
                         "checklist artifact. (Not a table re-pad, which needs none: %s.)"
                         % (name, not_a_repad))
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


def _toolbox_nudge_module(root):
    """The shipped `toolbox-nudge.py`, loaded from its path (the filename is hyphenated).

    Loaded rather than restated: the rules and the exemptions are the hook's own data, so the gate
    cannot drift from the thing it checks. Returns None on a tree with no such hook, so the check
    degrades to silence rather than to a false failure."""
    hook = root / "plugins" / "bitranox" / "hooks" / "toolbox-nudge.py"
    if not hook.is_file():
        return None
    spec = importlib.util.spec_from_file_location("_gate_toolbox_nudge", hook)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def toolbox_rule_coverage_failures(root):
    """Every shipped toolbox tool must have a nudge rule, or a RECORDED reason it has none.

    Like `frontmatter_failures` this sweeps the WHOLE scripts dir rather than the changed paths,
    and for the same reason: `check_cso` next door lints changed files only, so a tool added in one
    commit is never looked at again. That is exactly how five tools shipped with no trigger while
    every gate stayed green - and the PreToolUse nudge, not the prompt router, is the channel that
    does the work here (measured over 2,090 transcripts: 917 firings against the router's 3).

    A STALE exemption fails too: it names a tool nobody ships any more, so it quietly stops meaning
    anything, which is the same silent rot one level up.
    """
    nudge = _toolbox_nudge_module(root)
    if nudge is None:
        return []
    scripts_dir = root / _SKILLS_DIR / "compuse-toolbox" / "scripts"
    shipped = {p.stem for p in sorted(scripts_dir.glob("*.py")) if not p.stem.startswith("_")}
    ruled = nudge.ruled_tools()
    exempt = nudge.NO_COMMAND_SHAPE
    fails = []
    for tool in sorted(shipped - ruled - set(exempt)):
        fails.append(
            "skills/compuse-toolbox/scripts/%s.py ships with no PreToolUse nudge rule and no "
            "recorded reason. Add a rule to toolbox-nudge.py - price it over the real corpus with "
            "scripts/guard_replay.py and adjudicate the firings - or add an entry to "
            "NO_COMMAND_SHAPE saying why no command shape identifies this chore." % tool)
    for tool in sorted(set(exempt) - shipped):
        fails.append(
            "toolbox-nudge.py NO_COMMAND_SHAPE exempts '%s', which no longer ships under "
            "skills/compuse-toolbox/scripts - drop the entry, or point it at the tool's new "
            "name." % tool)
    # An exemption is the lazy path out of writing a rule, so it has to cost something: the entry
    # must say what was TRIED, not only why the author was not keen. A gate satisfied by an
    # opinion is advice, which is the failure this whole check exists to avoid one level up.
    for tool in sorted(exempt):
        entry = exempt[tool]
        if not (isinstance(entry, tuple) and len(entry) == 2 and all(
                isinstance(part, str) and part.strip() for part in entry)):
            fails.append(
                "toolbox-nudge.py NO_COMMAND_SHAPE['%s'] must be a (reason, evidence) pair with "
                "both parts non-empty. `evidence` states what was actually tried - the candidate "
                "pattern and what it measured over the real corpus, or why no command shape can "
                "exist for this chore." % tool)
    return fails


def check_toolbox_rule_coverage(root):
    return toolbox_rule_coverage_failures(root)


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
    "ai-llm-jev-judge": "KI/btx-skill-jev-judge/skills/jev-judge",
    "coding-python-gitignore": "libs/igittigitt/skills/python-gitignore",
    "coding-python-layered-config": "libs/lib_layered_config/skills/python-layered-config",
    "coding-python-logging": "libs/lib_log_rich/skills/python-logging",
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


def _marketplace_public(root):
    """The `public/` tree a marketplace checkout at `root` compares its twins in, or None.

    A linked worktree may sit outside the tree (a scratch directory), and then its own parents
    hold no `public/`; the main checkout it belongs to does. Without this, a commit from such a
    worktree compared nothing and passed, whatever the twin said.
    """
    return _public_tree(root) or _public_tree(_checkouts(root)[1])


def normalise_mirror(text):
    """Return the comparable body of a mirrored SKILL.md.

    Three divergences are by convention, not drift, so they are erased rather than
    reported: the `name:` field (each copy uses its own repo's skill name), a trailing
    `(<name>)` on the H1, and the tool repo's self-install blockquote. Everything else is
    content, and content that differs between the copies is drift by definition.

    The H1 rule is wider than its purpose: a trailing parenthetical with no nested
    parentheses is erased on EVERY line starting with `# ` (a `# ` comment in a code block
    included), whatever it holds. The text before it is compared verbatim, so an H1 renamed
    to the skill's own name is drift.
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


#: The refs naming a repository's PUBLISHED text, most specific first: the remote's own default
#: branch, then the two names a default branch has in this tree.
_PUBLISHED_REFS = ("origin/HEAD", "origin/master", "origin/main")


def _mirror_ignored(rel):
    return bool(MIRROR_IGNORED_DIRS & set(rel.split("/")))


def _working_tree_files(skill_dir):
    found = {}
    for path in sorted(Path(skill_dir).rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(skill_dir).as_posix()
        if not _mirror_ignored(rel):
            found[rel] = path.read_bytes()
    return found


def _published_commit(directory):
    for ref in _PUBLISHED_REFS:
        rc, out, _ = _git(directory, "rev-parse", "--verify", "-q", ref + "^{commit}")
        if rc == 0 and out.strip():
            return out.strip()
    return None


def _checked_out_bytes(directory, commit, rel, env=None):
    """A file of ``commit`` exactly as a checkout here would write it (eol and filters applied).

    ``commit`` "" names the INDEX (``:./rel``), which is what the next commit will carry; with
    ``env`` naming a ``GIT_INDEX_FILE``, that index."""
    try:
        out = subprocess.run(["git", "cat-file", "--filters", "%s:./%s" % (commit, rel)],
                             cwd=str(directory), capture_output=True, env=env)
    except Exception:  # noqa: BLE001
        return None
    return out.stdout if out.returncode == 0 else None


#: What the commit and push gates read of the side being committed: the index on a commit, HEAD
#: on a push (or `gh pr create`, which publishes HEAD). A commit that takes files from disk itself
#: is a `CommitSelection` instead.
STAGE_INDEX, STAGE_HEAD = "index", "HEAD"


class CommitSelection:
    """A `git commit` that takes files from the WORKING TREE itself: `-a`, `-i <paths>` or `<paths>`.

    Such a commit stages what it names only when it runs, so the index a PreToolUse gate reads
    beforehand is not what it ships. Measured 2026-10-24: `git commit -F msg -- <paths>` with no
    `git add` was refused as DRIFT quoting the old SKILL.md while the files on disk were in sync.
    Git defines the selection, and `_selected_files` has git build it:

    * ``all`` (`-a`): the index, with every tracked file re-staged from disk.
    * ``only`` (`<paths>`, `-o`): HEAD, with the named paths staged from disk, so a change staged
      elsewhere is NOT in this commit.
    * ``include`` (`-i <paths>`): the index, with the named files re-staged from disk.

    ``where`` is the directory the commit runs in, which the pathspecs are relative to.

    Not seen by any PreToolUse reading, this one or the index: a `pre-commit` hook that edits and
    stages files, and environment the command's git gets but this hook does not (a `GIT_*`
    variable or `GIT_CONFIG_*` injected into the shell from outside the command text).
    """

    __slots__ = ("mode", "pathspecs", "where")

    def __init__(self, mode, pathspecs=(), where=None):
        self.mode, self.pathspecs, self.where = mode, tuple(pathspecs), where

    def __repr__(self):
        return "CommitSelection(%r, %r, %r)" % (self.mode, self.pathspecs, self.where)


def _is_commit(stage):
    """True for any stage a COMMIT ships (the index, or a `CommitSelection`), False for a push."""
    return stage == STAGE_INDEX or isinstance(stage, CommitSelection)


def _selection_top(skill_dir, selection):
    """The repository top both the skill and the commit live in, or None if they differ or git fails."""
    rc_top, here_top, _ = _git(skill_dir, "rev-parse", "--show-toplevel")
    rc_where, where_top, _ = _git(selection.where, "rev-parse", "--show-toplevel")
    if rc_top or rc_where or os.path.normcase(here_top.strip()) != os.path.normcase(where_top.strip()):
        return None
    return here_top.strip()


def _stage_selection(selection, top, real_index, temp_index, env):
    """Build in ``temp_index`` what ``selection`` commits, with git's own staging; False if git fails.

    The same plumbing the commit runs: `add -u` re-stages tracked files for `-a` and `-i`, and a
    `<paths>` commit starts from HEAD and updates every path the pathspecs match in the index or
    HEAD (so a path `git rm` removed is removed here too). A partial commit keeps HEAD's blob for a
    skip-worktree entry (sparse checkout), which a HEAD-built index cannot know, so any such match
    gives False and the index reading."""
    if selection.mode == "only":
        rc_m, named = _git_paths(selection.where, "ls-files", "--full-name", "--with-tree=HEAD", "--",
                                 *selection.pathspecs)
        rc_t, tagged = _git_paths(selection.where, "ls-files", "-t", "--full-name", "--", *selection.pathspecs)
        if rc_m or rc_t or any(row.startswith("S ") for row in tagged):
            return False
        if _git(top, "read-tree", "HEAD", env=env)[0]:
            return False
        return not named or _git(top, "update-index", "--add", "--remove", "--", *named, env=env)[0] == 0
    if not os.path.isfile(real_index):
        return False
    shutil.copyfile(real_index, temp_index)
    specs = ("--", ":/") if selection.mode == "all" else ("--", *selection.pathspecs)
    return _git(selection.where, "add", "-u", *specs, env=env)[0] == 0


@contextlib.contextmanager
def _selection_index(directory, selection):
    """Yield the git environment whose index holds what ``selection`` commits, or None.

    Git builds the selection itself, in a throwaway index (`GIT_INDEX_FILE`), and callers read it
    back from there. Reproducing git's add logic by hand was tried first and, over three adversarial
    review rounds on 2026-10-24, kept missing rules git applies: the stat cache (a stat-clean entry
    keeps its STAGED blob under `-a`), the safer-CRLF rule (a CRLF blob already in the index is not
    converted), symlinks and paths behind a symlinked directory, clean filters, and assume-unchanged
    entries. Staging writes the same blobs the commit itself will write; it runs with an empty
    `core.hooksPath`, so no user hook fires during the check, and with `core.splitIndex=false`, so
    no shared-index file is left in the real git dir. None when git cannot say what it takes."""
    top = _selection_top(directory, selection)
    rc, real_index, _ = _git(directory, "rev-parse", "--path-format=absolute", "--git-path", "index")
    if top is None or rc:
        yield None
        return
    with tempfile.TemporaryDirectory(prefix="repo-gate-index-") as scratch:
        temp_index, no_hooks = os.path.join(scratch, "index"), os.path.join(scratch, "no-hooks")
        os.mkdir(no_hooks)
        env = {**os.environ, "GIT_INDEX_FILE": temp_index, "GIT_CONFIG_COUNT": "2",
               "GIT_CONFIG_KEY_0": "core.hooksPath", "GIT_CONFIG_VALUE_0": no_hooks,
               "GIT_CONFIG_KEY_1": "core.splitIndex", "GIT_CONFIG_VALUE_1": "false"}
        yield env if _stage_selection(selection, top, real_index.strip(), temp_index, env) else None


def _selected_files(skill_dir, selection):
    """`shipped_files` for a `CommitSelection`, or None when git cannot say what it takes."""
    with _selection_index(skill_dir, selection) as env:
        if env is None:
            return None
        rc_l, listed = _git_paths(skill_dir, "ls-files", "--", ".", env=env)
        if rc_l:
            return None
        found = {}
        for rel in dict.fromkeys(listed):
            if _mirror_ignored(rel):
                continue
            data = _checked_out_bytes(skill_dir, "", rel, env=env)
            if data is None:
                return None
            found[rel] = data
        return dict(sorted(found.items()))


def shipped_files(skill_dir, stage):
    """Map every comparable file of a mirrored skill to the bytes a commit or push SHIPS.

    The side being committed is judged by what its commit carries, never by its working tree: an
    unstaged edit is not part of a commit, and a staged one is not part of a push until it is
    committed (#111). ``stage`` is ``STAGE_INDEX``, ``STAGE_HEAD`` or a `CommitSelection`, the one
    kind of commit that DOES take files from the working tree; when git cannot say what that
    selection takes, the index is read, as for a plain commit. Without git, or with nothing to list
    (no commit yet), the working tree is all there is, and that is what is compared.
    """
    skill_dir = Path(skill_dir)
    if isinstance(stage, CommitSelection):
        selected = _selected_files(skill_dir, stage)
        if selected is not None:
            return selected
        stage = STAGE_INDEX
    if stage == STAGE_INDEX:
        commit, (rc, listed) = "", _git_paths(skill_dir, "ls-files", "--", ".")
    else:
        commit, (rc, listed) = "HEAD", _git_paths(skill_dir, "ls-tree", "-r", "--name-only", "HEAD", "--", ".")
    if rc:
        return _working_tree_files(skill_dir)
    found = {}
    for rel in dict.fromkeys(listed):            # an unmerged path is listed once per stage
        if _mirror_ignored(rel):
            continue
        data = _checked_out_bytes(skill_dir, commit, rel)
        if data is None:
            return _working_tree_files(skill_dir)
        found[rel] = data
    return dict(sorted(found.items()))


def _on_published(skill_dir, local_since, fallback):
    """The published ref's files, each one the checkout changed since forking replaced by its local copy.

    ``local_since(base)`` returns ``(paths, read)`` - the paths changed here since the fork point
    ``base`` and a reader giving a path's local bytes, or None for a path that is gone - or None
    when it cannot tell. Every failure to read git hands over to ``fallback()``.
    """
    skill_dir = Path(skill_dir)
    published = _published_commit(skill_dir)
    if published is None:
        return fallback()
    rc, base, _ = _git(skill_dir, "merge-base", "HEAD", published)
    base = base.strip()
    rc_up, upstream = _git_paths(skill_dir, "ls-tree", "-r", "--name-only", published, "--", ".")
    local = local_since(base) if rc == 0 and base else None
    if rc_up or local is None:
        return fallback()
    paths, read = local
    found = {}
    for rel in upstream:
        if rel in paths or _mirror_ignored(rel):
            continue
        data = _checked_out_bytes(skill_dir, published, rel)
        if data is None:
            return fallback()
        found[rel] = data
    for rel in paths:
        data = None if _mirror_ignored(rel) else read(rel)
        if data is not None:
            found[rel] = data
    return dict(sorted(found.items()))


def _changed_since(skill_dir, base, *upto):
    # --no-renames: with rename detection on, a moved file lists only its NEW name, and the old one
    # would be read back from the published ref as a file that still exists.
    return _git_paths(skill_dir, "diff", "--name-only", "--relative", "--no-renames", base, *upto, "--", ".")


def mirror_files(skill_dir):
    """Map every comparable file of a mirrored skill to its NEWEST bytes, by relative posix path.

    The reading of the AUDITS (`--mirrors`, `--mirror-of`); the commit and push gates read
    `shipped_files` and `published_files` instead.

    A checkout is not the newest text of anything it has not edited. Measured 2026-10-02: the main
    marketplace checkout sat 16 commits behind origin under another session's uncommitted work, and
    a tool repo whose skill matched origin/master exactly was blocked as DRIFT with no bypass. The
    same staleness hides real drift too, when a stale checkout agrees with a stale twin.

    So a file edited here - uncommitted, untracked, or committed since this checkout forked from
    the published ref - is read from disk, because that is the change in progress; every other
    file is read from the published ref, because that is what installs get. A checkout level with
    or ahead of origin therefore reads exactly as its working tree. Without git, a published ref or
    a fork point, the working tree is all there is, and that is what is compared.
    """

    skill_dir = Path(skill_dir)

    def local_since(base):
        rc_ed, edited = _changed_since(skill_dir, base)
        rc_un, untracked = _git_paths(skill_dir, "ls-files", "--others", "--exclude-standard", "--", ".")
        if rc_ed or rc_un:
            return None
        return set(edited) | set(untracked), lambda rel: (
            (skill_dir / rel).read_bytes() if (skill_dir / rel).is_file() else None)

    return _on_published(skill_dir, local_since, lambda: _working_tree_files(skill_dir))


def published_files(skill_dir):
    """Map every comparable file of a mirrored skill to what its repo has PUBLISHED or COMMITTED.

    The reading of the side a commit or push is NOT being made in: its published ref, with every
    file it committed since forking from that ref read from HEAD. Its uncommitted and untracked
    files are ignored - they belong to another session's work in progress, which neither commit
    ships. Measured as #84: a tool-repo commit was blocked as DRIFT by a marketplace edit nobody
    had committed. With no published ref this is HEAD; without git, the working tree.
    """

    skill_dir = Path(skill_dir)

    def local_since(base):
        rc_ed, edited = _changed_since(skill_dir, base, "HEAD")
        if rc_ed:
            return None
        return set(edited), lambda rel: _checked_out_bytes(skill_dir, "HEAD", rel)

    return _on_published(skill_dir, local_since, lambda: shipped_files(skill_dir, STAGE_HEAD))


#: A published ref last fetched longer ago than this is named beside the comparison that read it.
STALE_REF_DAYS = 7


def _clone_time(common):
    """The clone's own timestamp from the first entry of `logs/HEAD`, or None."""
    try:
        first = (Path(common) / "logs" / "HEAD").read_text(encoding="utf-8", errors="replace").split("\n", 1)[0]
        who, message = first.split("\t", 1)
        return float(who.split()[-2]) if message.startswith("clone:") else None
    except (OSError, ValueError, IndexError):
        return None


def ref_age_days(directory, now=None):
    """Days since the repository holding `directory` last fetched its remote, or None if unknown.

    FETCH_HEAD is rewritten by every fetch and pull, a no-op one included, so its mtime is the last
    fetch. It is per-worktree: a fetch run from a linked worktree writes `worktrees/<name>/FETCH_HEAD`
    and leaves the common one alone, so the newest of all of them is the answer. A clone writes no
    FETCH_HEAD; its `logs/HEAD` clone entry dates the refs instead. Probed on git 2.x, 2026-10-05.
    """
    rc, out, _ = _git(directory, "rev-parse", "--git-common-dir")
    if rc or not out.strip():
        return None
    common = Path(out.strip())
    if not common.is_absolute():
        common = Path(directory) / common
    stamps = []
    for candidate in [common / "FETCH_HEAD", *sorted((common / "worktrees").glob("*/FETCH_HEAD"))]:
        try:
            stamps.append(candidate.stat().st_mtime)
        except OSError:
            continue
    if not stamps:
        stamps = [stamp for stamp in [_clone_time(common)] if stamp is not None]
    if not stamps:
        return None
    return max(0.0, ((time.time() if now is None else now) - max(stamps)) / 86400)


def stale_ref_notes(directories):
    """One line per directory whose published ref was last fetched over STALE_REF_DAYS ago.

    Read-only by design: the gates never fetch (a network call inside a commit hook), so the most
    they can do is say how old the text they compared against is."""
    notes = []
    for directory in directories:
        age = ref_age_days(directory)
        if age is not None and age > STALE_REF_DAYS:
            notes.append("note: the published ref of %s was last fetched %.1f days ago - it may be "
                         "behind its origin; refresh it with a fetch in that repo and compare again."
                         % (directory, age))
    return notes


def _mirror_readers(committing, stage):
    """(marketplace reader, twin reader, sides whose published ref is read) for one comparison."""
    if committing is None:
        return mirror_files, mirror_files, ("marketplace", "twin")

    def shipped(skill_dir):
        return shipped_files(skill_dir, stage)

    if committing == "marketplace":
        return shipped, published_files, ("twin",)
    return published_files, shipped, ("marketplace",)


def _mirror_differences(mine_files, their_files):
    """(differing paths, sample diff lines of SKILL.md) between the marketplace and twin readings."""
    differing, sample = [], []
    for rel in sorted(set(mine_files) | set(their_files)):
        mine, theirs = mine_files.get(rel), their_files.get(rel)
        if mine is None:
            differing.append("%s (only in the twin)" % rel)
        elif theirs is None:
            differing.append("%s (only in the marketplace)" % rel)
        elif rel == "SKILL.md":
            a = normalise_mirror(theirs.decode("utf-8"))
            b = normalise_mirror(mine.decode("utf-8"))
            if a != b:
                differing.append(rel)
                diff = difflib.unified_diff(a.splitlines(), b.splitlines(), "twin", "marketplace",
                                            lineterm="", n=0)
                sample = [line for line in diff
                          if line[:1] in "+-" and line[:3] not in ("---", "+++")]
        elif mine != theirs:
            differing.append(rel)
    return differing, sample


def _matches_uncommitted_other_side(committing, here_dir, twin_dir, mine_files, their_files):
    """True when the side being committed matches the OTHER side's uncommitted text exactly.

    A change made to both copies of a mirrored skill could otherwise commit on neither side first:
    each commit reads the other side at what it committed, and neither has (user decision
    2026-10-12, [200]). The other side is re-read at its newest text, the audits' reading."""
    if committing == "marketplace":
        their_files = mirror_files(twin_dir)
    else:
        mine_files = mirror_files(here_dir)
    return bool(mine_files and their_files) and not _mirror_differences(mine_files, their_files)[0]


def mirror_failures(root, names, committing=None, stage=STAGE_INDEX, notices=None, twins=None):
    """Return a failure per mirrored skill in ``names`` whose twin has drifted.

    A mirrored skill is a DIRECTORY. Several pairs ship `references/` and `scripts/` beside their
    `SKILL.md`, and comparing only `SKILL.md` let three changed reference and script files sit
    unreported while this check printed "in sync" - an absence claim that is wrong is worse than
    no check, because it is the answer the reader hoped for.

    `SKILL.md` is compared through `normalise_mirror`, which erases the three by-convention
    divergences. Every other file must match byte for byte: nothing about them is per-repo.

    How each side is read depends on who asks. ``committing`` None is an AUDIT: both sides at
    their newest text (`mirror_files`). A GATE names the side being committed ("marketplace" or
    "twin"): that side is read at what it ships (`shipped_files` at ``stage``, the index or HEAD)
    and the other at what it published or committed (`published_files`), so neither another
    session's uncommitted edit nor this repo's unstaged one decides a commit. A side with nothing
    to compare - not checked out, or nothing committed - is skipped, as the audit reports.

    A drift message names every side read from a published ref that was last fetched over
    STALE_REF_DAYS ago (`stale_ref_notes`): stale text is the likeliest false drift, and the
    gates never fetch.

    A COMMIT (a gate at ``STAGE_INDEX``) that drifts only from the other side's COMMITTED text but
    matches its uncommitted text exactly is a coordinated change to both copies, and passes: the
    pair is reported in ``notices`` instead, naming the repo to commit next. Only a caller that
    passes a ``notices`` list gets that reading, so the pass can never arrive without its notice.
    A push still reads the other side at what it committed, so the pair cannot be published
    until both sides are.

    ``twins`` maps a skill name to the twin directory to read instead of its main-checkout path, for
    a tool repo worked in from a linked worktree (`_tool_repo_twins`).
    """

    public = _marketplace_public(root)
    if public is None:
        return []
    read_here, read_twin, from_published = _mirror_readers(committing, stage)
    # An audit (committing None) already reads both sides at their newest text, so it never matches here.
    lenient = _is_commit(stage) and notices is not None
    fails = []
    for name in sorted(names):
        relative = MIRRORED_SKILLS.get(name)
        if relative is None:
            continue
        here_dir = Path(root) / "plugins" / "bitranox" / "skills" / name
        twin_dir = Path((twins or {}).get(name) or public / relative)
        if not (here_dir / "SKILL.md").exists() or not (twin_dir / "SKILL.md").exists():
            # The tool repo is not checked out on this machine, so there is nothing to
            # compare against. Silence is right: the audit mode reports the skip.
            continue
        mine_files, their_files = read_here(here_dir), read_twin(twin_dir)
        if not mine_files or not their_files:
            continue  # nothing committed on one side yet: no text either commit could ship
        differing, sample = _mirror_differences(mine_files, their_files)
        if not differing:
            continue
        if lenient and _matches_uncommitted_other_side(committing, here_dir, twin_dir, mine_files, their_files):
            other = twin_dir if committing == "marketplace" else here_dir
            notices.append(
                "skills/%s matches its twin only through uncommitted text at %s, so this commit is "
                "allowed; commit that side next - a push from either repo is refused until both "
                "sides are committed." % (name, other))
            continue
        detail = "\n      ".join(sample[:6]) if sample else "\n      ".join(differing[:6])
        dirs = {"marketplace": here_dir, "twin": twin_dir}
        notes = stale_ref_notes([dirs[side] for side in from_published])
        between = "\n    %s\n    " % "\n    ".join(notes) if notes else " "
        fails.append(
            "skills/%s has drifted from its twin at %s (%d differing file(s): %s). Regenerate the "
            "stale side from the other, re-apply only the three divergences (the `name:` line, a "
            "trailing `(<name>)` on the H1 - the H1 text before it must match - and the "
            "self-install blockquote), and bump that repo's plugin.json.%sFirst lines:\n      %s"
            % (name, relative, len(differing), ", ".join(differing[:6]), between, detail)
        )
    return fails


#: Any file of a skill: a mirrored skill is a directory, so a change to its `references/` or
#: `scripts/` touches it as surely as one to its SKILL.md.
_SKILL_FILE_RX = re.compile(r"^%s/([^/]+)/" % re.escape(_SKILLS_DIR))


def _index_changes(root, env=None):
    """Paths the index (``env``'s, else the real one) changes against HEAD; all of it before a first commit."""
    if _git(root, "rev-parse", "--verify", "-q", "HEAD")[0]:
        return _git_paths(root, "ls-files", env=env)
    return _git_paths(root, "diff", "--cached", "--name-only", "--no-renames", "HEAD", env=env)


def _pushed_changes(root):
    """(rc, paths) the commits since origin/master change; rc non-zero when there is no origin/master."""
    if _git(root, "rev-parse", "--verify", "-q", "origin/master")[0]:
        return 1, []
    return _git_paths(root, "diff", "--name-only", "--no-renames", "origin/master...HEAD")


def _commit_changes(root, stage):
    """(rc, paths) a COMMIT at ``stage`` changes against HEAD: its staged index, or its selection.

    When git cannot build a `CommitSelection`, the working tree's changes count too: the commit
    may take any of them, and a path counted that it does not take only means a check that was
    not needed, never a drift let through."""
    if not isinstance(stage, CommitSelection):
        return _index_changes(root)
    with _selection_index(root, stage) as env:
        if env is not None:
            return _index_changes(root, env)
    rc_i, staged = _index_changes(root)
    rc_w, unstaged = _git_paths(root, "diff", "--name-only", "--no-renames", "HEAD")
    return rc_i or rc_w, staged + unstaged


def check_skill_mirrors(root, stage=STAGE_INDEX, notices=None, publishes=False):
    """Gate the mirrored twin of every skill this change ships a change to.

    Scoped to what the change SHIPS, like the review and description checks are to what changed:
    pre-existing drift in a skill this commit does not change must not block it ([740]: an
    unrelated commit was refused over an unstaged skill edit, and over a peer's unpushed commit),
    and the maintainer has ``--mirrors`` for the full sweep. A commit counts the files its own
    selection changes against HEAD (`_commit_changes`); a push the files its commits change since
    origin/master. A commit whose command also ``publishes`` (`command_publishes`) counts both,
    since the push sends the unpushed commits under it as well.

    The marketplace is the side being committed, read at ``stage`` (the index on a commit, HEAD
    on a push); the twin at what its repo committed, or on a commit with ``notices`` given, at a
    matching uncommitted text (`mirror_failures`).
    """

    changed = []
    if _is_commit(stage):
        rc, changed = _commit_changes(root, stage)
        if rc:
            return []
    if publishes or not _is_commit(stage):
        rc, pushed = _pushed_changes(root)
        if rc:
            return []
        changed += pushed
    touched = {m.group(1) for m in (_SKILL_FILE_RX.match(p) for p in changed) if m}
    return mirror_failures(root, touched & set(MIRRORED_SKILLS), committing="marketplace", stage=stage,
                           notices=notices)


def command_publishes(command, tool_name=None):
    """True when a statement in ``command`` is a `git push` or a `gh pr create`.

    Segmented and anchored like `shell_text.is_gated_command`, heredoc bodies dropped, so a push
    named as DATA does not count."""
    for _at, seg in shell_text.iter_segments(shell_text.strip_heredoc_bodies(command or ""), tool_name):
        seg = seg.strip().lstrip("(").strip()
        if shell_text.is_git_verb(seg, {"push"}, tool_name or "Bash") or shell_text.PR_RE.match(seg):
            return True
    return False


def mirror_stage(command, tool_name=None, cwd=None):
    """What a gated command ships of the repo it runs in: the index for a commit, else HEAD.

    A command that commits anywhere commits the index first, and any push after it in the same
    command pushes that commit, so one `git commit` statement decides. A push or `gh pr create`
    alone publishes HEAD. Segmented exactly like `shell_text.is_gated_command`, heredoc bodies
    dropped, so a commit named as DATA does not count.

    A commit that takes files from the working tree itself (`-a`, a pathspec, `-i`) gives a
    `CommitSelection` instead; its pathspecs resolve from the directory the commit runs in, which
    `cwd` (where the session sits) leads to. Anything the text cannot settle gives the index."""
    for _at, seg in shell_text.iter_segments(shell_text.strip_heredoc_bodies(command or ""), tool_name):
        seg = seg.strip().lstrip("(").strip()
        if shell_text.is_git_verb(seg, {"commit"}, tool_name or "Bash"):
            return _commit_selection(seg, command, tool_name or "Bash", cwd) or STAGE_INDEX
    return STAGE_HEAD


#: `git commit` options whose VALUE is the next token when it is not attached.
_COMMIT_VALUE_OPTS = frozenset({
    "-m", "--message", "-F", "--file", "-C", "--reuse-message", "-c", "--reedit-message",
    "-t", "--template", "--author", "--date", "--trailer", "--cleanup", "--fixup", "--squash"})
#: `git commit` options that take no value, or only an ATTACHED one (`-uno`, `--gpg-sign=<key>`).
_COMMIT_FLAG_OPTS = frozenset({
    "-a", "--all", "-o", "--only", "-i", "--include", "-q", "--quiet", "-v", "--verbose",
    "-s", "--signoff", "--no-signoff", "-n", "--no-verify", "--verify", "-e", "--edit",
    "--no-edit", "--amend", "--no-post-rewrite", "--allow-empty", "--allow-empty-message",
    "--reset-author", "--dry-run", "--short", "--branch", "--porcelain", "--long", "-z", "--null",
    "--status", "--no-status", "-u", "--untracked-files", "-S", "--gpg-sign", "--no-gpg-sign"})
_COMMIT_SHORT_VALUE = frozenset("mFCct")
_COMMIT_SHORT_ATTACHED = frozenset("uS")               # optional value, attached only
_COMMIT_SHORT_FLAGS = frozenset("aoiqvsnez")


#: Characters that let the shell rewrite or cut a word (globs, braces, comments, redirects, pipes,
#: expansions, history, escapes). A statement holding any of them anywhere - even inside a quoted
#: message - is read on the index: after tokenizing, a quoted `'*.md'` (git's own glob) and an
#: unquoted `*.md` (expanded by the shell first) look the same.
_SHELL_REWRITES = frozenset("*?[]{}#<>|&;$`\\~!@")


def _commit_selection(segment, command, tool, cwd):
    """The `CommitSelection` of one `git commit` statement, or None for the plain index commit.

    Only the plainest shape is read, because every other one was shown to make the reading differ
    from what git commits (adversarial review, 2026-10-24): a Bash statement `git [-C <dir>] commit
    <options> [--] <paths>` with no leading assignment or launcher, no other global option (`git
    --icase-pathspecs` and `GIT_*_PATHSPECS=` change pathspec matching), no character the shell
    rewrites (`_SHELL_REWRITES`), and the only `git commit` in the command (a second one commits
    the index), with nothing before it but `cd <absolute dir>` (`_commit_is_plainly_placed`). Also
    None for `-p`/`--interactive`, `--pathspec-from-file`, an option this reader does not know, `-a`
    with paths (git refuses it), a `..` in a `-C` or `cd` path, or no readable directory. None is
    the old reading, so not knowing is never laxer."""
    if tool != "Bash" or any(c in _SHELL_REWRITES for c in segment) or not _commit_is_plainly_placed(command, tool):
        return None
    try:
        tokens = shell_text.split_for_tool(segment, tool)
    except ValueError:
        return None
    operands = _plain_commit_operands(tokens)
    parsed = None if operands is None else _parse_commit_operands(operands)
    if parsed is None:
        return None
    flags, pathspecs = parsed
    where = _commit_dir(command, cwd, tool)
    if where is None or ("a" in flags and pathspecs) or not ("a" in flags or pathspecs):
        return None
    if "a" in flags:
        return CommitSelection("all", (), where)
    return CommitSelection("include" if "i" in flags else "only", pathspecs, where)


def _commit_is_plainly_placed(command, tool):
    """True when the command holds exactly one `git commit` and only `cd <absolute dir>` runs before it.

    The hook reads the disk BEFORE any statement runs, so a statement ahead of the commit that
    writes a file (`git restore`, `cp`, `sed -i`, a formatter) or changes how git matches a pathspec
    (`export GIT_ICASE_PATHSPECS=1`) makes the reading differ from what git commits. Measured by
    adversarial review, 2026-10-24. Statements after the commit run after it and do not matter."""
    commits = 0
    for _at, seg in shell_text.iter_segments(shell_text.strip_heredoc_bodies(command or ""), tool):
        seg = seg.strip()
        if not seg:
            continue
        if shell_text.is_git_verb(seg.lstrip("(").strip(), {"commit"}, tool):
            commits += 1
        elif commits == 0 and not _is_plain_cd(seg):
            return False
    return commits == 1


def _is_plain_cd(segment):
    """`cd <absolute path>` with no shell rewriting and no `..`, so the text names where it lands."""
    if any(c in _SHELL_REWRITES for c in segment):
        return False
    try:
        tokens = shell_text.split_for_tool(segment, "Bash")
    except ValueError:
        return False
    return (len(tokens) == 2 and tokens[0] == "cd" and (tokens[1].startswith("/") or os.path.isabs(tokens[1]))
            and not _climbs(tokens[1]))


def _climbs(path):
    """True for a path with a `..` component: git chdir()s physically, so `-C link/..` lands in the
    parent of the link's TARGET while the text names the link's parent."""
    return ".." in path.replace("\\", "/").split("/")


def _plain_commit_operands(tokens):
    """The operands of `git [-C <dir>]... commit ...`, or None for any other prefix."""
    if not tokens or shell_text.basename_for_tool(tokens[0], "Bash") != "git":
        return None
    at = 1
    while at + 1 < len(tokens) and tokens[at] == "-C":
        if _climbs(tokens[at + 1]):
            return None
        at += 2
    if at >= len(tokens) or tokens[at] != "commit":
        return None
    return tokens[at + 1:]


def _commit_dir(command, cwd, tool):
    if cwd is None:
        return None
    return shell_text.git_verb_dir(command, cwd, {"commit"}, tool)


def _parse_commit_operands(operands):
    """({'a', 'i', ...} selection flags seen, pathspecs) of `git commit`'s operands, or None if unknowable."""
    flags, pathspecs, at = set(), [], 0
    while at < len(operands):
        token = operands[at]
        at += 1
        if token == "--":
            pathspecs.extend(operands[at:])
            break
        if not token.startswith("-") or token == "-":
            pathspecs.append(token)
            continue
        if token.startswith("--"):
            name, attached = token.partition("=")[0], "=" in token
            if name in ("--all", "--include", "--only"):
                flags.add(name[2])
            elif name in _COMMIT_VALUE_OPTS:
                at += 0 if attached else 1
            elif name not in _COMMIT_FLAG_OPTS:
                return None                          # -p's long forms, --pathspec-from-file, unknown
            continue
        skip = _parse_short_cluster(token[1:], flags)
        if skip is None:
            return None
        at += skip
    return flags, pathspecs


def _parse_short_cluster(cluster, flags):
    """Read one `-abc` cluster into ``flags``; the count of following tokens it consumes, or None."""
    for index, letter in enumerate(cluster):
        rest = cluster[index + 1:]
        if letter in _COMMIT_SHORT_VALUE:
            return 0 if rest else 1
        if letter in _COMMIT_SHORT_ATTACHED:
            return 0
        if letter not in _COMMIT_SHORT_FLAGS:
            return None                              # -p, or a letter this reader does not know
        flags.add(letter)
    return 0


#: `git push` options that take their VALUE as the next token.
_PUSH_VALUE_OPTS = frozenset({"-o", "--push-option", "--repo", "--receive-pack", "--exec"})
#: `git push` options that send branches whatever the refspecs say.
_PUSH_BRANCH_OPTS = frozenset({"--all", "--branches", "--mirror", "--follow-tags"})


def _is_tag_ref(repo, name):
    """True when `name` resolves in `repo` as a tag and NOT as a branch (ambiguous is not a tag)."""
    if name.startswith("refs/tags/"):
        return True
    if not name or name.startswith("refs/"):
        return False

    def exists(ref):
        return subprocess.run(["git", "-C", str(repo), "show-ref", "--verify", "--quiet", ref],
                              capture_output=True).returncode == 0
    return exists("refs/tags/" + name) and not exists("refs/heads/" + name)


def _push_sends_only_tags(operands, repo):
    """True when one `git push` statement's operands can send nothing but tags."""
    positional, tags_flag, i = [], False, 0
    while i < len(operands):
        tok = operands[i]
        if tok in _PUSH_VALUE_OPTS:
            i += 2
            continue
        if tok in _PUSH_BRANCH_OPTS:
            return False
        if tok == "--tags":
            tags_flag = True
        elif not tok.startswith("-"):
            positional.append(tok)
        i += 1
    refspecs = positional[1:]                     # the first positional is the remote
    if not refspecs:
        return tags_flag                          # a bare push sends the current branch
    for spec in refspecs:
        src, _, dst = spec.lstrip("+").partition(":")
        if dst and not _is_tag_ref(repo, dst):
            return False
        if src and not _is_tag_ref(repo, src):
            return False
    return True


def pushes_only_tags(command, repo, tool_name=None):
    """True when every gated statement in `command` is a `git push` that can send only tags.

    A tag ships no SKILL.md to installers - a marketplace serves its default branch - so the
    mirror gate has nothing to protect on such a push. Gating it anyway deadlocks a tool repo's
    release: its SKILL.md floors may not name a version PyPI does not serve yet, the tag push is
    what publishes that version, and the twin cannot be synced before it.

    Fails closed: a commit or `gh pr create` anywhere, a refspec that names a branch, resolves to
    nothing, or is both a tag and a branch, and any push option that sends branches, all answer
    False, so the ordinary gate still runs. A name is resolved in `repo`, the repository the
    command lands in; a name the tokenizer mangled resolves to nothing and therefore stays gated.
    """
    found_push = False
    for _at, seg in shell_text.iter_segments(shell_text.strip_heredoc_bodies(command or ""), tool_name):
        seg = seg.strip().lstrip("(").strip()
        if shell_text.PR_RE.match(seg) or shell_text.is_git_verb(seg, {"commit"}, tool_name or "Bash"):
            return False
        operands = shell_text.git_verb_operands(shell_text.argv_for_match(seg, tool_name or "Bash"),
                                                {"push"}, tool_name or "Bash")
        if operands is None:
            continue
        if not _push_sends_only_tags(operands, repo):
            return False
        found_push = True
    return found_push


def _marketplace_checkout(public):
    """The marketplace checkout a mirror is compared against: the one being run from, if any.

    Measured 2026-09-27: run from a worktree on origin/master while the main checkout sat 194
    commits behind, --mirror-of compared the twin against the MAIN checkout and reported DRIFT whose
    '-' lines were the new text, while --mirrors from the same worktree said in sync. The main
    checkout under `public/KI/` stays the answer for a caller not standing in a marketplace checkout
    at all, such as a tool repo's release pipeline. A checkout outside `public` is not preferred:
    the twin lives in that tree, so the comparison must too.
    """
    here = repo_root()
    if here is not None and is_bitranox_skills(here) and here.resolve().is_relative_to(public.resolve()):
        return here
    return public / "KI" / "bitranox-skills"


def _other_marketplace_checkouts(marketplace):
    """Every other checkout of the marketplace repository at `marketplace`: its main checkout and
    each linked worktree, as `git worktree list` names them, that holds the skills tree.

    A tool-repo commit is judged against these too (`gate_tool_repo_mirror`): the marketplace side
    of a coordinated edit is often made in a linked worktree, and reading only the checkout the
    session stands in, or the main one, refused the tool-repo commit while the worktree's push was
    refused for the tool repo not having committed - neither side could move. Measured 2026-10-20.
    """
    _top, main = _checkouts(marketplace)
    rc, out, _ = _git(main, "worktree", "list", "--porcelain", "-z")
    if rc:
        return []
    seen, found = {Path(marketplace).resolve()}, []
    for field in out.split("\0"):
        if not field.startswith("worktree "):
            continue
        path = Path(field[len("worktree "):]).resolve()
        if path not in seen and (path / "plugins" / "bitranox" / "skills").is_dir():
            seen.add(path)
            found.append(path)
    return found


def _checkouts(directory):
    """(top level of the worktree holding `directory`, main checkout of its repository).

    A linked worktree (`git worktree add`, such as `.claude/worktrees/<name>`) is the same repository
    as its main checkout at another path. Its common git dir is `<main>/.git`; a bare repository or
    a separate git dir has no such parent, and then the worktree is its own answer. Outside git,
    `directory` is both.
    """
    directory = Path(directory).resolve()
    rc, out, _ = _git(directory, "rev-parse", "--show-toplevel", "--git-common-dir")
    lines = out.splitlines()
    if rc or len(lines) != 2:
        return directory, directory
    top, common = Path(lines[0]).resolve(), Path(lines[1])
    if not common.is_absolute():
        common = directory / common  # git prints a relative common dir relative to the cwd
    common = common.resolve()
    return top, (common.parent if common.name == ".git" else top)


def _tool_repo_twins(tool_repo):
    """(public tree, {skill name: twin dir as checked out here}) for the tool repo at `tool_repo`.

    MIRRORED_SKILLS names a twin by its path in the MAIN checkout, so ownership is decided there, and
    the twin is then read at the same place in the worktree being worked in: committed from a linked
    worktree, that worktree's text is what ships. Measured 2026-10-12: keyed on the worktree's own
    path, a commit in `.claude/worktrees/<name>` owned no mirrored skill, so the commit gate was
    silent and `--mirror-of` passed while the pair had drifted. `tool_repo` below its top level
    keeps only the twins beneath it, as before. The tree is found from the main checkout, so a
    worktree placed outside `public/` still finds it. (None, {}) when there is no tree.
    """
    here = Path(tool_repo).resolve()
    top, main = _checkouts(here)
    public = _public_tree(main / "x")  # _public_tree looks at parents, so descend one
    if public is None:
        return None, {}
    scope = main / here.relative_to(top) if here.is_relative_to(top) else main
    twins = {}
    for name, rel in MIRRORED_SKILLS.items():
        twin = (public / rel).resolve()
        if twin.is_relative_to(scope):
            twins[name] = top / twin.relative_to(main)
    return public, twins


def audit_mirror_of(tool_repo):
    """Print the state of the mirrored pair belonging to one tool repo.

    The counterpart to ``--mirrors`` for the other side of the mirror: a release pipeline
    running inside a tool repo asks only about ITS pair, because another repo's drift is
    not a reason to block this release. Returns 1 if that pair has drifted, else 0, and
    says so and returns 0 when there is nothing to compare - the repo ships no mirrored
    skill, or this machine has no marketplace checkout - so it is safe to run everywhere.
    """

    tool = Path(tool_repo).resolve()
    public, twins = _tool_repo_twins(tool)
    if public is None:
        print("mirror check: no public/ tree above %s - nothing to compare" % tool)
        return 0
    marketplace = _marketplace_checkout(public)
    if not (marketplace / "plugins" / "bitranox" / "skills").is_dir():
        print("mirror check: no bitranox-skills checkout at %s - nothing to compare" % marketplace)
        return 0
    mine = sorted(twins)
    if not mine:
        print("mirror check: %s ships no skill mirrored in bitranox-skills" % tool.name)
        return 0
    fails = mirror_failures(marketplace, set(mine), twins=twins)
    for name in mine:
        print("%-8s%-34s %s" % ("DRIFT" if any(name in f for f in fails) else "in sync", name, MIRRORED_SKILLS[name]))
    for note in stale_ref_notes([marketplace, tool]):
        print(note)
    for failure in fails:
        print("\n" + failure)
    return 1 if fails else 0


def audit_mirrors(root):
    """Print the state of every mirrored pair. Returns the number of findings.

    A finding is a drifted pair or a twin MIRRORED_SKILLS does not list: unlisted, that pair is
    never compared by any gate, so it is as much a defect as drift and counts toward the exit."""

    public = _marketplace_public(root)
    if public is None:
        print("no public/ tree above %s - nothing to compare" % root)
        return 0
    drifted = 0
    for note in stale_ref_notes([root]):
        print(note)
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
        for note in stale_ref_notes([twin.parent]):
            print("        " + note)
    unlisted = unlisted_mirrors(root, public)
    for pair in unlisted:
        print("UNLISTED %-33s %s" % pair)
    print("\n%d of %d mirrored pairs have drifted." % (drifted, len(MIRRORED_SKILLS)))
    if unlisted:
        print("%d twin%s not listed in MIRRORED_SKILLS - add %s so the gates compare %s."
              % (len(unlisted), " is" if len(unlisted) == 1 else "s are",
                 "it" if len(unlisted) == 1 else "them", "it" if len(unlisted) == 1 else "them"))
    return drifted + len(unlisted)


def _description(path):
    """Return a SKILL.md's description collapsed to one line, "" when it has none.

    The same reader as the CSO lint and the builders (`hc.frontmatter_description`), so a twin is
    matched on the description those ship rather than on a looser first-line guess."""
    return hc.frontmatter_description(path) or ""


def _in_main_checkout(path, public):
    """`path` mapped into the main checkout when it lies in a linked worktree, else None.

    A peer's `git worktree add` beside a listed tool repo carries the same skill, and is the
    same twin checked out a second time, not an unlisted one. A linked worktree's root holds a
    `.git` FILE reading `gitdir: <main>/.git/worktrees/<name>` (relative to that root under
    worktree.useRelativePaths); a clone holds a `.git` directory and stays its own repo.
    """
    for root in [path, *path.parents]:
        if root == public or public not in root.parents:
            return None
        marker = root / ".git"
        if marker.is_dir():
            return None
        if not marker.is_file():
            continue
        try:
            text = marker.read_text(encoding="utf-8").strip()
        except OSError:
            return None
        if not text.startswith("gitdir:"):
            return None
        gitdir = (root / text[len("gitdir:"):].strip()).resolve()
        if gitdir.parent.name != "worktrees" or gitdir.parent.parent.name != ".git":
            return None
        return (gitdir.parent.parent.parent / path.relative_to(root)).resolve()
    return None


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
            if "bitranox-skills" in twin.parts:
                continue
            if twin.parent.resolve() in listed or _in_main_checkout(twin.parent, public) in listed:
                continue
            name = catalog.get(_description(twin))
            if name:
                found.append((name, twin.parent.relative_to(public).as_posix()))
    return found


def run_checks(root, ci, full_pytest=None, run_pytest=True, baseline=0, mirror_at=STAGE_INDEX,
               notices=None, publishes=False):
    """`ci` picks the CHECK SET (CI omits the maintainer-only ones); `full_pytest` picks the pytest
    SCOPE and defaults to `ci`. They are separate axes because a pre-push is BOTH: the maintainer
    (so version-bump, skill-review and mirrors apply) and the last gate before CI (so it runs the
    whole suite CI runs, not just hooks/tests). `mirror_at` is what the commit or push ships of the
    marketplace (`mirror_stage`): the index on a commit, HEAD on a push; the LF and mirror checks
    read it. `publishes` says the same command also pushes (`command_publishes`). `notices`, when
    given, collects what passed but must still reach the model (`check_skill_mirrors`)."""
    if full_pytest is None:
        full_pytest = ci
    failures = []
    failures += check_tests_exist(root)
    failures += check_json_valid(root)
    failures += check_lf_endings(root, stage=mirror_at)
    failures += check_duplicate_basenames(root)
    failures += check_skills_index(root)
    failures += check_attribution(root)
    failures += check_skill_naming(root)
    failures += check_cso(root)
    failures += check_frontmatter(root)
    failures += check_toolbox_rule_coverage(root)
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
        failures += check_skill_mirrors(root, stage=mirror_at, notices=notices, publishes=publishes)
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


def gate_tool_repo_mirror(root, stage=STAGE_INDEX, guessed=False):
    """Check the mirror of a skill edited in its OWN repo, before it is committed or pushed.

    `main` has already read the event and confirmed it is a gated command, and `root` is the
    repository that command lands in (`hook_root`), not the session's working directory.

    The gate fires on every ``git commit``/``git push`` on the machine, but it used to
    return 0 in any repo that is not the marketplace. That left the tool-repo side of a
    mirrored pair unguarded, which is the side that actually drifted: measured twice on
    ``coding-python-network-probe``, which described a subsystem as absent two releases
    after it shipped.

    The tool repo is the side being committed, read at ``stage`` (its index on a commit, HEAD on
    a push); the marketplace at what it published or committed, never another session's
    uncommitted edit there (#84).

    Returns 2 to block a drifted pair, 0 otherwise. Silent when this repo owns no
    mirrored skill, so it does not narrate in every unrelated repo. A block names the repository
    it judged, and with ``guessed`` (`hook_landing`) says it was the session's own because the
    command's directory could not be read.

    The "cannot compare" case is deliberately NOT a bare 0. With no marketplace checkout
    there is nothing to diff, and passing in silence is indistinguishable from passing
    because the pair is in sync - which would make this guard permanently green and
    worthless. It still passes, because blocking would break anyone without the
    checkout, but it says so through ``additionalContext``, the one exit-0 channel the
    model actually reads (plain stdout/stderr on exit 0 does not reach it).
    """

    if root is None:
        return 0

    public, twins = _tool_repo_twins(root)
    mine = sorted(twins)
    if public is None or not mine:
        return 0

    marketplace = _marketplace_checkout(public)
    if not (marketplace / "plugins" / "bitranox" / "skills").is_dir():
        _say_unverifiable(mine, marketplace)
        return 0

    # A COMMIT passes a skill that matches ANY checkout of the marketplace, linked worktrees
    # included (`_other_marketplace_checkouts`); each is read as the main checkout is. A push stays
    # on `marketplace` alone: it publishes, so the other side must have published or committed there.
    candidates = [marketplace]
    if _is_commit(stage):
        candidates += _other_marketplace_checkouts(marketplace)
    notices, fails = [], []
    for name in mine:
        refusals = []
        for candidate in candidates:
            found = []
            failed = mirror_failures(candidate, {name}, committing="twin", stage=stage, notices=found,
                                     twins=twins)
            if not failed:
                notices += found
                break
            refusals.append(failed)
        else:
            fails += refusals[0]  # the checkout a push would read is the one to report
    if not fails:
        _say_context(notices)
        return 0
    # All of it on STDERR: on a PreToolUse exit 2 that is what the model is shown, and stdout is
    # not. The table and the diff are the actionable part, so they cannot go anywhere else.
    for name in mine:
        print("%-8s%-34s %s" % ("DRIFT" if any(name in f for f in fails) else "in sync", name, MIRRORED_SKILLS[name]),
              file=sys.stderr)
    for failure in fails:
        print("\n" + failure, file=sys.stderr)
    print("repo-gate: blocked - %s ships a skill that has drifted from its marketplace twin." % root,
          file=sys.stderr)
    if guessed:
        print(_FALLBACK_NOTE % root, file=sys.stderr)
    return 2


#: Said under any block whose repository came from `hook_landing`'s fallback.
_FALLBACK_NOTE = ("repo-gate: the directory this command runs git in could not be read from its text, "
                  "so the session's repository %s was judged. If the commit lands elsewhere, name the "
                  "target literally (cd /path/to/repo && git commit, or git -C /path/to/repo commit).")


def _say_unverifiable(names, marketplace):
    """Tell the model the mirror could not be checked, rather than exiting 0 in silence."""

    note = (
        "repo-gate: could not verify the marketplace mirror of %s - no bitranox-skills checkout at %s. "
        "The commit is allowed, but nothing confirmed the twin is in sync; run "
        "'repo-gate.py --mirror-of <this repo>' where the marketplace is checked out." % (", ".join(names), marketplace)
    )
    _say_context([note])


def _say_context(notes):
    """Pass ``notes`` to the model on the one exit-0 channel it reads; print nothing for none."""

    if notes:
        text = "\n".join(notes)
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": text}}))



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
            print("repo-gate: not inside a git repository - no CI workflow to read", file=sys.stderr)
            return 2
        print("\n".join(ci_test_dependencies(root)))
        return 0

    if "--pytest-only" in args:
        # The CI test step. It runs the suite WITHOUT capturing, so pytest's own output lands in
        # the CI log live - the gate used to swallow it, leaving a green run with no evidence any
        # test had run. The count is then read from the junit report and held to the floor.
        root = repo_root()
        if root is None:
            print("repo-gate: not inside a git repository - no suite to run", file=sys.stderr)
            return 2
        # The report goes to a temp dir, never the repo root: a stray junit.xml there would
        # dirty the working tree and could be committed by a pathspec-less `git add`.
        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "junit.xml"
            cmd = pytest_argv(root, [root]) + ["--junitxml=" + str(report)]
            rc = subprocess.run(cmd, cwd=str(root)).returncode
            problems = floor_problems(report, expected_collected(root)) if rc == 0 else []
        if rc == 5:
            print("repo-gate: pytest collected no tests - the suite did not run.", file=sys.stderr)
            return 2
        if rc == 1:
            return 1  # tests ran and some failed
        if rc != 0:
            # 2 interrupted (an unimportable test module), 3 internal, 4 usage, negative a signal:
            # none of them is a test result, so none may read as a finding or a pass.
            print("repo-gate: pytest did not complete (exit %d) - the suite did not run." % rc,
                  file=sys.stderr)
            return 2
        if problems:
            for line in problems:
                print(line, file=sys.stderr)
            return 2 if is_could_not_run(problems) else 1
        return 0

    if "--mirror-of" in args:
        # Runs from INSIDE a tool repo, so it must not require the marketplace as cwd:
        # it locates the marketplace from the shared public/ tree itself.
        index = args.index("--mirror-of")
        target = args[index + 1] if len(args) > index + 1 else "."
        return audit_mirror_of(target)

    hook_mode = not (ci or pre_push or mirrors)
    # A git pre-push hook pushes commits, so it reads HEAD; hook mode reads what its command ships.
    stage, publishes = STAGE_HEAD, False
    if hook_mode:
        # A real git pre-push hook receives REF LINES on stdin, never a Claude Code event, so only
        # hook mode parses it - read that way, a pre-push would fail the parse and pass by accident
        # on the one caller that fires when git runs OUTSIDE Claude Code (a terminal, an IDE, a
        # script). That blind spot is how a stale generated catalog shipped twice.
        try:
            event = json.load(sys.stdin)
        except Exception:  # noqa: BLE001
            return 0
        command = (event.get("tool_input") or {}).get("command") or ""
        if not is_gated_command(command, event.get("tool_name")):
            return 0
        root, guessed = hook_landing(event)
        stage = mirror_stage(command, event.get("tool_name"), os.path.normpath(event.get("cwd") or os.getcwd()))
        publishes = command_publishes(command, event.get("tool_name"))
    else:
        root, guessed = repo_root(), False
    if root is None or not is_bitranox_skills(root):
        if pre_push:
            # Someone pointed core.hooksPath here from another repo. Say so rather than blocking
            # a push this gate knows nothing about.
            print("repo-gate: not inside the bitranox-skills repo - pre-push checks skipped",
                  file=sys.stderr)
            return 0
        if ci or mirrors:
            print("repo-gate: not inside the bitranox-skills repo - nothing to check", file=sys.stderr)
            return 2
        # Hook mode outside the marketplace. Not "never interfere" any more: if THIS repo
        # ships a skill mirrored into the marketplace, the pair is checked from this side
        # too. Everything else still passes untouched.
        if root is not None and pushes_only_tags(command, root, event.get("tool_name")):
            if _tool_repo_twins(root)[1]:
                _say_context(["repo-gate: this push sends only tags, so the marketplace mirror was "
                              "not checked - a tag ships no SKILL.md to installers. Sync the twin "
                              "before pushing the branch."])
            return 0
        return gate_tool_repo_mirror(root, stage, guessed)

    if mirrors:
        # The full sweep the commit gate deliberately does not do: it reports every pair,
        # including the ones no current change touches.
        return 1 if audit_mirrors(root) else 0

    notices = [] if hook_mode else None
    failures = run_checks(root, ci, full_pytest=ci or pre_push,
                          run_pytest=run_pytest, baseline=expected_collected(root), mirror_at=stage,
                          notices=notices, publishes=publishes)

    if not failures:
        if ci or pre_push:
            print("repo-gate: all checks passed.")
        _say_context(notices)
        return 0

    header = ("repo-gate: FAILED" if ci else
              "repo-gate: push blocked - fix these first:" if pre_push else
              "repo-gate: commit/push blocked in %s - fix these first:" % root)
    fallback = [_FALLBACK_NOTE % root] if guessed else []
    print("\n".join([header, *failures, *(notices or []), *fallback]), file=sys.stderr)
    if not (ci or pre_push):
        return 2  # the PreToolUse block code, whatever kind the failure was
    return 2 if is_could_not_run(failures) else 1


#: Flags that start a CLI mode. Anything else is hook mode, the one mode a crash may not fail.
_CLI_FLAGS = ("--ci", "--pre-push", "--mirrors", "--mirror-of", "--pytest-only", "--print-test-deps")


def entry():
    """Run `main` under the exit contract of the mode it was started in.

    Hook mode must never wedge a turn, so a crash there passes (0). A CLI mode is read by CI and
    by the git pre-push hook, where the same 0 reads as "all checks passed" for a run that checked
    nothing - so a crash there is 2, could not run, with the traceback on stderr."""
    try:
        return main()
    except Exception:  # noqa: BLE001 - the mode decides what a crash means, not the exception
        if not any(flag in sys.argv[1:] for flag in _CLI_FLAGS):
            return 0
        traceback.print_exc()
        print("repo-gate: crashed - the checks did not complete; this is not a pass.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(entry())
