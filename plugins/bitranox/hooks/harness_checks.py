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
import shutil
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


#: Claude Code's documented cap on a skill's front-matter `description`. Going over is not
#: refused: the injected available-skills listing truncates the field mid-word, so the triggers
#: past the cut are invisible to the router while the SKILL.md still reads complete. Nothing
#: warns, which is why this is a gate rather than a rule someone remembers.
DESCRIPTION_CAP = 1024


def cso_failures_for(label, description):
    """Why `description` fails the CSO rules, at most one message, empty when it passes.

    One message rather than all of them: the first failure is the one to fix, and a description
    that is not trigger-first has not earned a keyword count yet."""
    if len(description) > DESCRIPTION_CAP:
        return ["%s: description is %d characters, over the %d cap - the injected "
                "available-skills listing truncates the tail silently, so those triggers never "
                "reach the router. Rewrite it shorter; appending or inserting only moves which "
                "trigger is lost." % (label, len(description), DESCRIPTION_CAP)]
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

# POSIX-absolute plus the two shapes an absolute path takes on Windows: a drive letter
# ("C:\...", "C:/...") and a UNC share ("\\server\share"). Without the Windows shapes,
# command_paths matched NOTHING there, so registration_problems reported zero problems for
# any registration naming a Windows path - the audit silently passed on the platform it was
# supposed to be auditing, which reads as approval rather than as a broken check.
# A leading '/' must be followed by a real name character. A bare "//" is not a path, and it
# reaches here as its own token out of any shell pipeline ("jq '.a // .b'"), where counting it
# invents a finding out of an operator.
_PATHISH_POSIX = re.compile(r"^(/[\w.@+-]|~/|\$HOME/|\$\{HOME\}/)")
_PATHISH_WINDOWS = re.compile(r"^([A-Za-z]:[\\/]|\\\\[^\\])")


def _is_pathish(token, windows=None):
    """True when the token unambiguously names a file path on the platform in question.

    `windows` overrides the platform so both shapes stay askable from either OS; leave it None
    outside tests."""
    on_windows = (os.name == "nt") if windows is None else windows
    return bool(_PATHISH_POSIX.match(token) or (on_windows and _PATHISH_WINDOWS.match(token)))


def _windows_argv(command):
    r"""Windows argv via CommandLineToArgvW - the C runtime's OWN command-line parser.

    This is the function every Windows program uses to read its own command line, so a command
    string is split here exactly as the program it names would split it. ctypes is stdlib, which
    matters: a hook runs on a bare interpreter with no venv and no third-party import available.

    `ctypes.wintypes` does not import on POSIX at all, so the import has to be function-local.
    """
    if not command.strip():
        # CommandLineToArgvW("") does NOT return an empty list - it returns the path of the
        # CURRENT executable, so an empty command would silently become a path to python itself.
        return []
    import ctypes                       # noqa: PLC0415 - Windows-only; wintypes cannot import on POSIX
    from ctypes import wintypes         # noqa: PLC0415 - same

    shell32 = ctypes.WinDLL("shell32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    shell32.CommandLineToArgvW.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_int)]
    shell32.CommandLineToArgvW.restype = ctypes.POINTER(wintypes.LPWSTR)
    kernel32.LocalFree.argtypes = [wintypes.HLOCAL]
    kernel32.LocalFree.restype = wintypes.HLOCAL

    count = ctypes.c_int(0)
    argv = shell32.CommandLineToArgvW(command, ctypes.byref(count))
    if not argv:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return [argv[i] for i in range(count.value)]
    finally:
        kernel32.LocalFree(argv)


def split_command_line(command):
    r"""Split a command string into argv, by the platform's own rules.

    POSIX: shlex. Windows: CommandLineToArgvW, so the string is split exactly as the program it
    names would split it.

    shlex's POSIX mode was the bug. It treats a backslash as an ESCAPE, so "bash C:\dir\hook.sh"
    tokenised to "C:dirhook.sh" - a path that cannot exist, silently dropped by the pathish test,
    leaving the caller with nothing to check. Approximating the rules with shlex-minus-escapes
    fixed the common shapes but still mis-read the C runtime's own `"a\"b"` quoting, so the real
    parser is called instead: it removes the class of problem rather than the instances.

    Kept identical in gate.py and diffbehave.py.
    """
    if os.name != "nt":
        return shlex.split(command)
    return _windows_argv(command)


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
    unresolved ${VAR} is skipped rather than guessed at.

    The split is the platform's own now, so it cannot be asked about the other one; `_is_pathish`
    still can, and is where the per-platform shapes are tested from either OS.
    """
    try:
        tokens = split_command_line(command)
    except (ValueError, OSError):
        tokens = command.split()
    on_windows = os.name == "nt"
    found = []
    for token in tokens:
        if not _is_pathish(token, on_windows):
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


def is_executable(path, posix=None):
    """True if the file carries a POSIX executable bit.

    Windows has no such bit, and os.access(X_OK) there returns True for ANY existing file. Asked
    bare, it reports every retired shim as "still executable" - a finding that is always true and
    never informative - and it makes the `elif not live.exists()` branch in graveyard_entries()
    unreachable, silently retiring a real check. Where the concept does not exist, say False.
    """
    on_posix = (os.name == "posix") if posix is None else posix
    if not on_posix:
        return False
    return os.access(path, os.X_OK)


def shim_problems(path, registered=(), home=None):
    """What is wrong with a retired shim, empty when it is a well-formed tombstone.

    A shim that exits zero is worse than no shim: the caller sees success and carries on, so the
    guard reads as present and passing while it enforces nothing."""
    path = Path(path)
    text = path.read_text(encoding="utf-8", errors="replace")
    problems = []
    if is_executable(path):
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

_DIRECT_COLLECT_TIMEOUT_S = 180
_UV_FALLBACK_TIMEOUT_S = 240


def _run_pytest(argv, timeout):
    """Real subprocess seam for a pytest collection attempt, direct or via the uv fallback.

    Explicit encoding/errors: with no encoding, subprocess decodes with the machine's locale
    codec and fails differently per platform - stdout comes back None on Windows, POSIX raises."""
    return subprocess.run(argv, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=timeout)


def uncollectable_tests(tests_dir, python=None, run=_run_pytest, resolve_uv=None):
    """Test modules pytest cannot even import, as (path, message, unmeasured) triples.

    `unmeasured` is True only when the CHECK itself could not run - neither the launching
    interpreter nor a `uv run --with pytest` fallback could attempt collection. That is a fact
    about this machine's environment, not about the target, so it must never be reported under
    the same label as a real collection failure: a reader who cannot tell the two apart reads an
    unmeasured result as a defect, exactly what happened when this checker's own missing pytest
    surfaced as `[tests-uncollectable] pytest not installed`.

    A `tests/` dir that exists is not a `tests/` dir that runs. Every check that asks only
    "is there a test file?" reports a module green when it errors during collection.

    `run` and `resolve_uv` are the injectable seams (a subprocess call, a PATH lookup); their
    defaults are the real collaborators."""
    tests_dir = Path(tests_dir)
    if not tests_dir.is_dir():
        return []
    direct_argv = [python or sys.executable, "-m", "pytest", "--collect-only", "-q",
                   "-p", "no:cacheprovider", str(tests_dir)]
    try:
        proc = run(direct_argv, timeout=_DIRECT_COLLECT_TIMEOUT_S)
    except (OSError, subprocess.SubprocessError) as exc:
        return [(str(tests_dir), "could not run pytest: %s" % exc, True)]
    if proc.returncode in (0, 5):  # 5 = nothing collected, which is not a collection failure
        return []
    text = (proc.stdout or "") + "\n" + (proc.stderr or "")
    if "No module named pytest" in text:
        return _collect_via_uv_fallback(tests_dir, run, resolve_uv or _default_resolve_uv)
    return _parse_collection_failure(text, tests_dir)


def _default_resolve_uv():
    """Real `resolve_uv` seam: where `uv` sits on PATH, or None."""
    return shutil.which("uv")


def _collect_via_uv_fallback(tests_dir, run, resolve_uv):
    """Retry collection under `uv run --with pytest`, since uv is already required to launch this
    script and can provision pytest on demand. Only when this ALSO cannot run does the launching
    interpreter's missing pytest become an unmeasured result instead of a real measurement."""
    uv_path = resolve_uv()
    if not uv_path:
        return [(str(tests_dir), "pytest is not importable by the launching interpreter, and uv "
                 "is not on PATH to fall back to - collection unverified", True)]
    argv = [uv_path, "run", "--with", "pytest", "python", "-m", "pytest", "--collect-only", "-q",
            "-p", "no:cacheprovider", str(tests_dir)]
    try:
        proc = run(argv, timeout=_UV_FALLBACK_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        return [(str(tests_dir), "uv run --with pytest fallback timed out after %ss - collection "
                 "unverified" % _UV_FALLBACK_TIMEOUT_S, True)]
    except (OSError, subprocess.SubprocessError) as exc:
        return [(str(tests_dir), "uv run --with pytest fallback failed to start: %s - collection "
                 "unverified" % exc, True)]
    if proc.returncode in (0, 5):
        return []
    text = (proc.stdout or "") + "\n" + (proc.stderr or "")
    if "No module named pytest" in text:
        return [(str(tests_dir), "pytest is not importable by the launching interpreter, and the "
                 "uv fallback did not provide it either - collection unverified", True)]
    return _parse_collection_failure(text, tests_dir)


def _parse_collection_failure(text, tests_dir):
    """A real, target-attributable collection failure, as (path, message, unmeasured=False)."""
    out = [(_resolve_reported_path(line[len("ERROR "):].strip(), tests_dir),
            _first_error_line(text), False)
           for line in text.splitlines() if line.startswith("ERROR ")]
    if out:
        return out
    culprit = _internalerror_culprit(text, tests_dir)
    if culprit:
        path, exception = culprit
        return [(path, exception, False)]
    return [(str(tests_dir), _first_error_line(text) or "collection failed", False)]


def _resolve_reported_path(token, tests_dir=None):
    """pytest's `ERROR <path>` rendered as an absolute path when it resolves.

    pytest prints that path relative to its own ROOTDIR, which is not this process's cwd. Two
    renderings both occur and only one used to survive: a `../../../../..` chain (when rootdir
    sits near the cwd) absolutised correctly, but a BARE `test_x.py` (when pytest makes the
    target dir itself the rootdir, which is what a Windows CI runner produced) resolved against
    the cwd, did not exist there, and was handed back as a bare relative name - the very
    "only resolves from one directory" defect this function exists to remove.

    So the target dir is tried as a base before the cwd. Anything that still does not point at a
    real file (a nodeid, an odd rendering) is left untouched rather than turned into an invented
    path."""
    bases = []
    if tests_dir is not None:
        bases += [str(tests_dir), str(Path(tests_dir).parent)]
    bases.append(os.getcwd())
    for base in bases:
        candidate = os.path.abspath(os.path.join(base, token))
        if os.path.exists(candidate):
            return candidate
    return token


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

def frontmatter_unterminated(path):
    """True when a SKILL.md opens a front-matter block that never closes on a line of its own.

    The failure shape is a closing `---` glued to the end of the last value
    (`...ship an OVM change.---`). Every reader in this module splits on a bare `---` substring,
    so they all recover the right value and no other check here notices - the file reads as
    perfectly fine until a loader that wants the delimiter on its own line refuses it.
    """
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except OSError:
        return False
    if not lines or lines[0].strip() != "---":
        return False  # no front matter at all is a different problem, reported by the callers
    return not any(line.strip() == "---" for line in lines[1:])


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
        if frontmatter_unterminated(md):
            problems.append("%s: SKILL.md front matter never closes - the `---` is glued to the "
                            "end of a value instead of standing on its own line." % label)
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
        if is_executable(path):
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


# --- a local file the plugin also ships -------------------------------------------------------
# Contributing upstream is ASYNCHRONOUS for anyone without commit rights: the PR lands in a later
# session, so at the moment the twin appears there is nobody standing at the contribution to retire
# the local copy. Retiring at contribute time cannot close that window, and the duplicate then
# survives every routine pass because each existing check asks a question it still satisfies. A
# recurring dedup pass is what closes it.

def shipped_file_index(shipped_root):
    """{basename: path} for every .py a plugin ships - its hooks/ plus every skill's scripts/tools."""
    root = Path(shipped_root)
    index = {}
    if not root.is_dir():
        return index
    for sub in ("hooks", "skills"):
        base = root / sub
        if not base.is_dir():
            continue
        for p in base.rglob("*.py"):
            if "__pycache__" in p.parts or "tests" in p.parts:
                continue
            index.setdefault(p.name, p)
    return index


def duplicate_shipped_files(local_dirs, shipped_root):
    """(local, shipped, status) per local .py whose basename the plugin also ships.

    status is "identical" (safe to retire) or "drifted" (NOT safe to retire yet). The distinction is
    load-bearing: a local copy can be drifted because it is AHEAD - a fix applied locally, or a wider
    scope - and deleting that to "dedup" destroys the improvement instead of sharing it. A drifted
    pair is a CONTRIBUTE signal first and a retire signal only afterwards.

    A RETIRED tombstone is skipped: it is the completed retirement, and reporting it would push a
    reader to delete the very thing that makes a stale caller fail loudly."""
    index = shipped_file_index(shipped_root)
    out = []
    if not index:
        return out
    for d in local_dirs:
        d = Path(d)
        if not d.is_dir():
            continue
        for p in sorted(d.rglob("*.py")):
            if "__pycache__" in p.parts or p.name not in index:
                continue
            if is_retired_shim(p):
                continue
            twin = index[p.name]
            try:
                same = p.read_bytes() == twin.read_bytes()
            except OSError:
                continue
            out.append((str(p), str(twin), "identical" if same else "drifted"))
    return out
