"""Deterministic checks for the skills and hooks that no plugin ships.

The marketplace surface is gated from several directions: `repo-gate.py` on commit and push,
`meta-skill-audit` in a clean room, the mirror checks for twin drift. None of it reaches a file
outside the `bitranox-skills` repo, so a personal `~/.claude/skills` entry or a project's
`.claude/skills` has no gate at all.

Selecting what to check is the delicate part, because the same shipped skill is reachable at
several paths at once: the writable source checkout, the marketplace clone under
`~/.claude/plugins/marketplaces`, and the version cache under `~/.claude/plugins/cache`. Tool repos
that ship a mirrored twin add more. Selecting by path shape would review all of them and, worse,
would invite a "fix" into a tool repo outside the mirror ritual, which is exactly the drift the
marketplace CLAUDE.md exists to prevent. So selection asks who OWNS a dir, not where it sits.
"""

import difflib
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

# A plugin root announces itself with one of these; either means some other gate owns the content.
PLUGIN_MANIFESTS = ("plugin.json", "marketplace.json")

# Never worth walking: caches, virtualenvs and vendored trees hold no first-party skill.
PRUNE_DIRS = frozenset({
    ".git", ".hg", ".svn", "node_modules", ".venv", "venv", ".venv-win", "__pycache__",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox", "site-packages", ".cache",
})


def owning_plugin(path):
    """The nearest ancestor a plugin manifest marks as shipped, or None.

    Nearest rather than outermost: a marketplace repo that also ships the plugin carries two
    manifests, and the inner one is the unit that actually installs."""
    candidate = Path(path)
    for parent in (candidate, *candidate.parents):
        marker_dir = parent / ".claude-plugin"
        if any((marker_dir / name).is_file() for name in PLUGIN_MANIFESTS):
            return parent
    return None


def under_installed_plugins(path, home=None):
    """True when `path` sits under `<home>/.claude/plugins`.

    That tree holds installed copies - the marketplace clone and the per-version cache. They carry
    no manifest of their own at every level, and editing one is pointless anyway: the next
    marketplace update overwrites it."""
    base = (Path(home) if home is not None else Path.home()) / ".claude" / "plugins"
    try:
        Path(path).relative_to(base)
    except ValueError:
        return False
    return True


def is_shipped(skills_dir, home=None):
    """True when a plugin already ships this skills dir, so another gate owns it."""
    return under_installed_plugins(skills_dir, home) or owning_plugin(skills_dir) is not None


def skip_reason(skills_dir, home=None):
    """Why this dir is not a target, or None when it is one.

    The reason matters more than the verdict: a selection that silently drops most of what it
    found reads the same whether the ownership rule worked or a path typo emptied the walk."""
    if under_installed_plugins(skills_dir, home):
        return "installed plugin content under ~/.claude/plugins"
    owner = owning_plugin(skills_dir)
    if owner is not None:
        return "shipped by the plugin at %s" % owner
    return None


def _run_git(cwd, args):
    """Git stdout, or None when git is absent, errors, or the path is outside a repository."""
    try:
        proc = subprocess.run(["git", "-C", str(cwd), *args],
                              capture_output=True, text=True, timeout=15)
    except (OSError, subprocess.SubprocessError):
        return None
    return proc.stdout if proc.returncode == 0 else None


def _git_identity_dirs(path):
    """(common git dir, worktree toplevel) for `path`, or (None, None) outside a repository.

    The COMMON dir is what makes a linked worktree recognisable: every worktree of one repository
    reports the same one, while each reports its own toplevel."""
    for extra in (["--path-format=absolute"], []):
        out = _run_git(path, ["rev-parse", *extra, "--git-common-dir", "--show-toplevel"])
        if out is None:
            continue
        lines = [line for line in out.splitlines() if line.strip()]
        if len(lines) < 2:
            continue
        common, top = Path(lines[0]), Path(lines[1])
        if not common.is_absolute():
            common = Path(path) / common
        return common, top
    return None, None


def target_identity(skills_dir):
    """A stable key so two checkouts of one repository are audited once.

    A linked worktree is a second checkout, so the same SKILL.md sits at two paths; auditing both
    spends a reviewer twice and reports every finding twice."""
    path = Path(skills_dir)
    common, top = _git_identity_dirs(path)
    if common is None:
        return (str(_norm(path)),)
    try:
        relative = _norm(path).relative_to(_norm(top))
    except ValueError:
        relative = Path(path.name)
    return (str(_norm(common)), str(relative))


def _norm(path):
    """Resolved when it exists, normalised otherwise - never raises on a missing path."""
    path = Path(path)
    try:
        return path.resolve()
    except OSError:
        return Path(os.path.normpath(str(path)))


def select_targets(candidates, home=None):
    """The candidates no plugin ships, de-duplicated by repository identity, sorted.

    Where two paths share an identity the shorter one wins, which is the main checkout rather than
    a linked worktree nested inside it."""
    keep = {}
    for candidate in candidates:
        path = Path(candidate)
        if is_shipped(path, home):
            continue
        key = target_identity(path)
        current = keep.get(key)
        if current is None or (len(str(path)), str(path)) < (len(str(current)), str(current)):
            keep[key] = path
    return sorted(keep.values())


# --- packaging: what must carry tests -------------------------------------------------------
#
# Lifted out of repo-gate.py so the same rule reaches skills the marketplace does not ship. The
# gate applied it only under `plugins/bitranox`, which is why a personal skill could ship an
# untested script indefinitely.

EXCLUDE_DIRS = frozenset({"tests", "demos", "examples", "__pycache__", "scripts_examples"})
EXCLUDE_FILES = frozenset({"conftest.py", "__init__.py"})


def ships_scripts(pkg):
    """True when `pkg` ships a .py someone actually runs - fixtures and demos do not count."""
    pkg = Path(pkg)
    for path in pkg.rglob("*.py"):
        rel_parts = set(path.relative_to(pkg).parts[:-1])
        if rel_parts & EXCLUDE_DIRS or path.name in EXCLUDE_FILES:
            continue
        return True
    return False


def has_tests(pkg):
    """True when `pkg` carries at least one real test module."""
    pkg = Path(pkg)
    for path in pkg.rglob("test_*.py"):
        parts = path.relative_to(pkg).parts
        if "examples" not in parts and "demos" not in parts:
            return True
    return False


def packages_missing_tests(packages):
    """Those that ship a runnable .py but carry no test. A script with no test is incomplete."""
    return [p for p in packages if ships_scripts(p) and not has_tests(p)]


# --- skill front matter: the CSO rules -------------------------------------------------------

CSO_STOP = frozenset({
    "use", "when", "the", "and", "for", "with", "that", "this", "from", "into", "your", "you",
    "are", "was", "has", "have", "not", "but", "its", "any", "all", "one", "how", "what", "why",
    "where", "which", "should", "must", "can", "will", "also", "such", "them", "then", "than",
    "good", "need", "want", "like", "just",
})

_DESCRIPTION_RX = re.compile(r"^description:\s*(.+(?:\n(?![a-zA-Z_-]+:).*)*)", re.M)


def frontmatter_description(path):
    """The `description:` value from a SKILL.md front matter, or None when there is none."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError:
        return None
    if not text.startswith("---"):
        return None
    match = _DESCRIPTION_RX.search(text.split("---", 2)[1])
    return " ".join(match.group(1).split()) if match else None


def frontmatter_name(path):
    """The `name:` value from a SKILL.md front matter, or None."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError:
        return None
    if not text.startswith("---"):
        return None
    match = re.search(r"^name:\s*(.+)$", text.split("---", 2)[1], re.M)
    return match.group(1).strip() if match else None


def cso_failures_for(label, description):
    """Why `description` fails the CSO rules, at most one message, empty when it passes.

    One message rather than all of them: the first failure is the one to fix, and a description
    that is not trigger-first has not earned a keyword count yet."""
    if description[:1] in (">", "|", '"', "'"):
        return ["%s: description must be a single-line plain YAML scalar - no "
                "'>-'/'|' block scalar and no wrapping quotes (the style marker leaks "
                "into the generated catalog and router; reword any ': ' instead)." % label]
    if not description.lower().startswith("use "):
        return ["%s: description must be trigger-first ('Use when <situations>...'), "
                "never a summary of what the skill does (CSO rule)." % label]
    keywords = {t for t in re.findall(r"[a-z0-9][a-z0-9_-]{3,}", description.lower())
                if t not in CSO_STOP}
    if len(keywords) < 3:
        return ["%s: description yields fewer than 3 distinctive keywords - the "
                "skill router cannot derive triggers from it; name concrete situations, "
                "tools, and symptoms." % label]
    return []


def _holds_skill(skills_dir):
    """True when at least one immediate child ships a SKILL.md. An empty dir is not a target."""
    try:
        return any((child / "SKILL.md").is_file() for child in skills_dir.iterdir() if child.is_dir())
    except OSError:
        return False


def discover_shipped(roots, home=None):
    """Plugin-owned `<dir>/skills` dirs under `roots`. Reported as skipped, never audited.

    Selection would drop these anyway, but INVISIBLY: a tool repo's `skills/` is not
    `.claude/skills`-shaped, so it never becomes a candidate and the skipped list comes back empty.
    An ownership filter whose work leaves no trace reads exactly like one that never ran, and the
    reader has no way to tell a correctly-scoped audit from a walk that missed half the tree."""
    found = set()
    for root in [Path(r) for r in roots]:
        if not root.is_dir():
            continue
        for dirpath, dirnames, _ in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in PRUNE_DIRS]
            here = Path(dirpath)
            if here.name == "skills" and _holds_skill(here) and is_shipped(here, home):
                dirnames[:] = []
                found.add(here)
    return sorted(found)


def discover_candidates(roots, home=None, personal=True):
    """Every `<dir>/.claude/skills` holding a SKILL.md under `roots`, plus `<home>/.claude/skills`.

    Shape only - ownership is `select_targets`' job. A plugin's own `skills/` dir is not a
    candidate at all: Claude Code loads it through the plugin, never as a project skill."""
    home = Path(home) if home is not None else Path.home()
    extra = [home / ".claude"] if personal else []
    found = set()
    for root in [*[Path(r) for r in roots], *extra]:
        if not root.is_dir():
            continue
        for dirpath, dirnames, _ in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in PRUNE_DIRS]
            here = Path(dirpath)
            if here.name == ".claude":
                # The installed-plugin tree is large and owned elsewhere; never descend it.
                dirnames[:] = [d for d in dirnames if d != "plugins"]
            if here.name == "skills" and here.parent.name == ".claude":
                dirnames[:] = []
                if _holds_skill(here):
                    found.add(here)
    return sorted(found)


# --- hook registrations: does the command point at anything real? ----------------------------
#
# repo-gate proves hooks.json PARSES; it never proves a registered command resolves. A typo in a
# path yields a hook that silently never fires, which reads exactly like a hook that fires and
# finds nothing.

_PATHISH = re.compile(r"^(/|~/|\$HOME/|\$\{HOME\}/)")


def _expand(token, home):
    """`~` and `$HOME` expanded against `home`. Other variables are left alone on purpose."""
    home = str(home) if home is not None else str(Path.home())
    for prefix in ("~/", "$HOME/", "${HOME}/"):
        if token.startswith(prefix):
            return str(Path(home) / token[len(prefix):])
    return token


def hook_registrations(settings_path):
    """(event, matcher, command) for every hook a settings file registers, empty if it has none."""
    try:
        data = json.loads(Path(settings_path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    out = []
    for event, groups in (data.get("hooks") or {}).items():
        for group in groups or []:
            matcher = group.get("matcher", "")
            for hook in group.get("hooks") or []:
                command = hook.get("command")
                if command:
                    out.append((event, matcher, command))
    return out


def command_paths(command, home=None):
    """The file paths a shell command names. Only unambiguous ones - a token that still holds an
    unresolved ${VAR} is skipped rather than guessed at."""
    try:
        tokens = shlex.split(command)
    except ValueError:
        tokens = command.split()
    found = []
    for token in tokens:
        if not _PATHISH.match(token):
            continue
        expanded = _expand(token, home)
        if "$" in expanded:
            continue
        found.append(expanded)
    return found


def registration_problems(settings_path, home=None):
    """Registered commands whose target file is missing, as (event, command, missing path)."""
    problems = []
    for event, _matcher, command in hook_registrations(settings_path):
        for path in command_paths(command, home):
            if not Path(path).exists():
                problems.append((event, command, path))
    return problems


def registered_paths(settings_paths, home=None):
    """Every file path any of these settings files registers, existing or not."""
    out = set()
    for settings in settings_paths:
        for _event, _matcher, command in hook_registrations(settings):
            out.update(command_paths(command, home))
    return out


# --- retired shims: a tombstone has to behave like one ---------------------------------------

_RETIRED_RX = re.compile(r"\bRETIRED\b")
_NONZERO_EXIT_RX = re.compile(r"SystemExit\(\s*[1-9]|sys\.exit\(\s*[1-9]|^\s*exit\s+[1-9]", re.M)


def is_retired_shim(path):
    """True when the file announces itself retired in its opening lines."""
    try:
        head = Path(path).read_text(encoding="utf-8", errors="replace")[:1200]
    except OSError:
        return False
    return bool(_RETIRED_RX.search(head))


_SCRIPT_PATH_RX = re.compile(r"(?:[\w.-]+/)+[\w.-]+\.(?:py|sh)\b")
_SCRIPT_NAME_RX = re.compile(r"[\w.-]+\.(?:py|sh)\b")


def _names_replacement(text, own_name):
    """True when the tombstone points a reader somewhere else.

    Phrase-matching is the wrong instrument here: real tombstones say "superseded by", "ships with
    the plugin as", or simply give the path, and a first pass looking for "Replacement:" called a
    perfectly good shim broken. What actually matters is whether another script is named - either
    as a path, or as a basename that is not this file's own."""
    if _SCRIPT_PATH_RX.search(text):
        return True
    return bool({m.group(0) for m in _SCRIPT_NAME_RX.finditer(text)} - {own_name})


def shim_problems(path, registered=(), home=None):
    """What is wrong with a retired shim, empty when it is a well-formed tombstone.

    A shim that exits zero is worse than no shim: the caller sees success and carries on, so the
    guard reads as present and passing while it enforces nothing."""
    path = Path(path)
    text = path.read_text(encoding="utf-8", errors="replace")
    problems = []
    if os.access(path, os.X_OK):
        problems.append("still executable - a retired file should not be runnable")
    if not _NONZERO_EXIT_RX.search(text):
        problems.append("does not exit non-zero - a caller would read it as success")
    if not _names_replacement(text, path.name):
        problems.append("names no replacement - a reader cannot tell what to call instead")
    if str(path) in set(registered):
        problems.append("still registered in a settings file - it would fire and block")
    return problems


def orphan_scripts(hooks_dir, registered=()):
    """Scripts in `hooks_dir` that nothing registers and that are neither library nor tombstone.

    The convention the marketplace follows exactly: a hyphenated name is a hook entry point, an
    underscored name is an importable module. So an unregistered hyphenated script is a hook that
    can never fire."""
    hooks_dir = Path(hooks_dir)
    if not hooks_dir.is_dir():
        return []
    registered = set(registered)
    orphans = []
    for path in sorted(hooks_dir.iterdir()):
        if not path.is_file() or path.suffix not in (".py", ".sh"):
            continue
        if "-" not in path.stem or str(path) in registered:
            continue
        if is_retired_shim(path):
            continue
        orphans.append(path)
    return orphans


# --- tests that exist but cannot run ---------------------------------------------------------

def uncollectable_tests(tests_dir, python=None):
    """Test modules pytest cannot even import, as (nodeid-ish path, first error line).

    A `tests/` dir that exists is not a `tests/` dir that runs. Every check that asks only
    "is there a test file?" reports a module green when it errors during collection."""
    tests_dir = Path(tests_dir)
    if not tests_dir.is_dir():
        return []
    try:
        proc = subprocess.run([python or sys.executable, "-m", "pytest", "--collect-only", "-q",
                               "-p", "no:cacheprovider", str(tests_dir)],
                              capture_output=True, text=True, timeout=180)
    except (OSError, subprocess.SubprocessError) as exc:
        return [(str(tests_dir), "could not run pytest: %s" % exc)]
    if proc.returncode in (0, 5):  # 5 = nothing collected, which is not a collection failure
        return []
    text = (proc.stdout or "") + "\n" + (proc.stderr or "")
    if "No module named pytest" in text:
        return [(str(tests_dir), "pytest not installed - collection unverified")]
    out = [(line[len("ERROR "):].strip(), _first_error_line(text))
           for line in text.splitlines() if line.startswith("ERROR ")]
    if out:
        return out
    culprit = _internalerror_culprit(text, tests_dir)
    return [culprit] if culprit else [(str(tests_dir),
                                       _first_error_line(text) or "collection failed")]


def _first_error_line(text):
    for line in (text or "").splitlines():
        if line.startswith("E   "):
            return line[4:].strip()
    return ""


_TB_FILE_RX = re.compile(r'File "([^"]+)", line \d+')
_EXC_RX = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*(Error|Exit|Exception)\b")


def _internalerror_culprit(text, tests_dir):
    """The test file a pytest INTERNALERROR blames, as (path, exception line), or None.

    A module raising SystemExit at import time never produces a normal `ERROR` line: pytest
    reraises it and dies with INTERNALERROR, so a parser reading only `ERROR ` reports the
    directory and loses the file. That is the exact shape of a test importing a retired shim."""
    base = os.path.abspath(str(tests_dir))
    blamed, exception = None, ""
    for line in text.splitlines():
        match = _TB_FILE_RX.search(line)
        if match and os.path.abspath(match.group(1)).startswith(base):
            blamed = match.group(1)
        stripped = line.replace("INTERNALERROR>", "").strip()
        if _EXC_RX.match(stripped):
            exception = stripped
    return (blamed, exception or "raised during import") if blamed else None


# --- a local skill that shadows a shipped one -------------------------------------------------

def unmanaged_twins(local_skills_dir, shipped_descriptions, threshold=0.90):
    """Local skills whose description matches a shipped skill's, as (name, shipped name, ratio).

    The marketplace runs a mirror gate over the twins it knows about. A local copy is in nobody's
    map, so it drifts silently and an install keeps steering by whichever the router picks."""
    local_skills_dir = Path(local_skills_dir)
    if not local_skills_dir.is_dir():
        return []
    found = []
    for skill in sorted(d for d in local_skills_dir.iterdir() if d.is_dir()):
        description = frontmatter_description(skill / "SKILL.md")
        if not description:
            continue
        best, best_ratio = None, 0.0
        for shipped_name, shipped_desc in (shipped_descriptions or {}).items():
            ratio = difflib.SequenceMatcher(None, description, shipped_desc or "").ratio()
            if ratio > best_ratio:
                best, best_ratio = shipped_name, ratio
        if best is not None and best_ratio >= threshold:
            found.append((skill.name, best, round(best_ratio, 3)))
    return found


def shipped_descriptions(skills_dir):
    """{skill name: description} for a shipped catalogue, to compare local copies against."""
    skills_dir = Path(skills_dir)
    if not skills_dir.is_dir():
        return {}
    out = {}
    for skill in skills_dir.iterdir():
        if skill.is_dir():
            description = frontmatter_description(skill / "SKILL.md")
            if description:
                out[skill.name] = description
    return out


# --- front matter parity ----------------------------------------------------------------------

def frontmatter_problems(skills_dir):
    """Per-skill front-matter failures: a name that disagrees with its dir, plus the CSO rules."""
    skills_dir = Path(skills_dir)
    if not skills_dir.is_dir():
        return []
    problems = []
    for skill in sorted(d for d in skills_dir.iterdir() if d.is_dir()):
        md = skill / "SKILL.md"
        if not md.is_file():
            continue
        label = skill.name
        name = frontmatter_name(md)
        if name is None:
            problems.append("%s: SKILL.md has no `name:` in its front matter." % label)
        elif name != skill.name:
            problems.append("%s: front-matter name is %r but the directory is %r - the router "
                            "keys on one and the loader on the other." % (label, name, skill.name))
        description = frontmatter_description(md)
        if description is None:
            problems.append("%s: SKILL.md has no `description:` - nothing can route to it." % label)
        else:
            problems.extend(cso_failures_for(label, description))
    return problems


# --- graveyards: retired artifacts left where they read as live -------------------------------

def graveyard_entries(root):
    """Retired artifacts that a reader would mistake for live ones, as (path, why).

    A `.orig-<date>` beside its replacement is the SANCTIONED way to retire a file here, so it is
    not flagged for existing. It is flagged when it is still executable, or when the file it backs
    up is gone and it has quietly become the only copy."""
    root = Path(root)
    if not root.is_dir():
        return []
    found = []
    for path in sorted(root.rglob("*.orig-*")):
        if not path.is_file():
            continue
        live = path.parent / path.name.split(".orig-")[0]
        if os.access(path, os.X_OK):
            found.append((path, "retired backup is still executable"))
        elif not live.exists():
            found.append((path, "backs up %s, which no longer exists" % live.name))
    for path in sorted(root.glob("*.bak")):
        if path.is_dir():
            count = sum(1 for _ in path.glob("*/SKILL.md"))
            found.append((path, "parked dir holding %d skill(s); indistinguishable from live at a "
                                "glance" % count))
    found.extend(_stale_bytecode(root))
    found.extend(_stale_nodeids(root))
    return found


def _stale_bytecode(root):
    """Compiled modules whose source is gone - the usual trace of a deleted script."""
    out = []
    for pyc in sorted(Path(root).rglob("__pycache__/*.pyc")):
        source = pyc.parent.parent / (pyc.name.split(".")[0] + ".py")
        if not source.exists():
            out.append((pyc, "bytecode for %s, which no longer exists" % source.name))
    return out


def _stale_nodeids(root):
    """Cached pytest node ids naming a test file that is gone."""
    out = []
    for cache in sorted(Path(root).rglob(".pytest_cache/v/cache/nodeids")):
        try:
            ids = json.loads(cache.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        base = cache.parents[3]
        missing = sorted({i.split("::")[0] for i in ids if isinstance(i, str)}
                         - {str(p.relative_to(base)) for p in base.rglob("*.py")})
        for name in missing:
            out.append((cache, "caches node ids for %s, which no longer exists" % name))
    return out
