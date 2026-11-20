"""No shipped plugin Python turns a command-text path into a host path except through shell_text.

On a Windows host the Bash tool is Git Bash, where `/c/temp` is drive C. os.path roots that path at
the CURRENT drive (C:\\c\\temp) instead. `shell_text.resolve_path`, `directory_change` and
`git_verb_dir` read the drive by default (`reads_msys_drives`); a hook that checks `is_rooted` and
then joins or normalises the path itself skips that reading. Two hooks did exactly that while every
cd reader but one had the drive reading switched off, so the shape is enforced here rather than
remembered:

- a function outside shell_text that calls `is_rooted` must not also join, normalise or absolutise
  a path (`os.path.join`/`normpath`/`abspath`) unless `ALLOWED_JOINS` says why that is safe;
- no caller outside shell_text passes `msys_drives=`, which would opt out of the host's reading;
- `msys_drive_path` is called directly only where `ALLOWED_DRIVE_CALLS` says why; a caller that
  wants the host's reading of one word uses `msys_drive_path_for_tool`, which asks
  `reads_msys_drives` like every other reader, instead of deciding the host itself.
"""
import ast
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[2]
_SKIP_PARTS = {"__pycache__", "node_modules", "tests"}
_SINKS = {"join", "normpath", "abspath"}

# (file relative to the plugin root, function) -> why is_rooted plus a join is safe there.
ALLOWED_JOINS = {
    ("hooks/compact-resume.py", "_collect_targets"): "the token went through _as_bash_reads, which "
                                                     "already spelled a Git Bash drive as its drive",
    ("hooks/git-path-not-here-nudge.py", "notice"): "a rooted path is skipped, never joined; only a "
                                                    "relative one is joined onto the cwd",
}

# (file, function) -> why that function decides the drive reading itself. Empty: every shipped
# caller that reads one word takes the host's reading from `msys_drive_path_for_tool`.
ALLOWED_DRIVE_CALLS: dict[tuple[str, str], str] = {}


def _shipped_python_files():
    for path in sorted(PLUGIN_ROOT.rglob("*.py")):
        rel = path.relative_to(PLUGIN_ROOT).parts
        if any(p in _SKIP_PARTS or p.startswith(".venv") for p in rel):
            continue
        if path.name == "shell_text.py":
            continue                      # the module that owns the reading
        yield path


def _called_name(func):
    if isinstance(func, ast.Name):
        return func.id
    return func.attr if isinstance(func, ast.Attribute) else None


def _findings(source):
    """({functions calling is_rooted and a path sink}, {functions passing msys_drives=},
    {functions calling msys_drive_path}) for `source`."""
    joins, opt_outs, drive_calls = set(), set(), set()
    for fn in ast.walk(ast.parse(source)):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        calls = [node for node in ast.walk(fn) if isinstance(node, ast.Call)]
        names = {_called_name(call.func) for call in calls}
        if "is_rooted" in names and names & _SINKS:
            joins.add(fn.name)
        if any(kw.arg == "msys_drives" for call in calls for kw in call.keywords):
            opt_outs.add(fn.name)
        if "msys_drive_path" in names:
            drive_calls.add(fn.name)
    return joins, opt_outs, drive_calls


def test_the_walk_sees_the_plugin_tree():
    """A walk rooted at the wrong directory finds nothing and passes vacuously."""
    names = {p.name for p in _shipped_python_files()}
    assert {"bmk-gate-nudge.py", "missing-mechanism-nudge.py", "git-wrong-repo-nudge.py"} <= names


def test_the_detector_finds_each_shape():
    """Each rule fires on the shape it forbids - the two hooks this guard was written for had the
    first one - and stays quiet on a function that only classifies."""
    source = (
        "import os\n"
        "def join_it(here, target):\n"
        "    if is_rooted(target):\n        return target\n"
        "    return os.path.join(here, target)\n"
        "def opt_out(stmt, here):\n    return directory_change(stmt, here, msys_drives=False)\n"
        "def by_hand(p):\n    return shell_text.msys_drive_path(p, True)\n"
        "def classify(p):\n    return is_rooted(p)\n"
    )
    assert _findings(source) == ({"join_it"}, {"opt_out"}, {"by_hand"})


def test_no_shipped_function_resolves_a_rooted_path_by_hand():
    found = {
        (path.relative_to(PLUGIN_ROOT).as_posix(), name)
        for path in _shipped_python_files()
        for name in _findings(path.read_text(encoding="utf-8"))[0]
    }
    assert found - set(ALLOWED_JOINS) == set(), (
        "use shell_text.resolve_path, which reads a Git Bash drive path (/c/...) as its drive")
    assert set(ALLOWED_JOINS) <= found, "an ALLOWED_JOINS entry no longer matches: remove it"


def test_no_shipped_caller_overrides_the_drive_reading():
    found = {
        (path.relative_to(PLUGIN_ROOT).as_posix(), name)
        for path in _shipped_python_files()
        for name in _findings(path.read_text(encoding="utf-8"))[1]
    }
    assert found == set(), "leave msys_drives to its default, shell_text.reads_msys_drives"


def test_msys_drive_path_is_called_directly_only_where_allowed():
    found = {
        (path.relative_to(PLUGIN_ROOT).as_posix(), name)
        for path in _shipped_python_files()
        for name in _findings(path.read_text(encoding="utf-8"))[2]
    }
    assert found == set(ALLOWED_DRIVE_CALLS)
