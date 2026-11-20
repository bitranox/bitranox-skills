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
  `reads_msys_drives` like every other reader, instead of deciding the host itself;
- `unknown_mounts=` is passed only where `ALLOWED_MOUNT_READINGS` says why: it reads a Git Bash
  mount (`/tmp/x` on Windows) at the current drive's root, a directory Git Bash never means, so
  only a caller that asks whether a landing is rooted, and never opens it, may take it;
- a function that reads command text (calls a shell_text reader, or reads a `command` key) must
  not place a path with pathlib itself (`Path(cwd) / token`, `.is_absolute()`, `os.path.isabs`)
  nor call a function of its module that does, unless `ALLOWED_PATHLIB_RESOLUTION` says why:
  pathlib is the native reading, which on Windows roots `/c/repo` and `/tmp/x` at the cwd's
  drive. tooling-detour-nudge and ci-watch-nudge resolved shell words that way, which the first
  rule cannot see because neither called `is_rooted`. A function that also calls `resolve_path`
  or `msys_drive_path_for_tool` is taken to read its words there first. The rule looks one call
  deep, so a resolver two calls below the reader passes unseen.
"""
import ast
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[2]
_SKIP_PARTS = {"__pycache__", "node_modules", "tests"}
_SINKS = {"join", "normpath", "abspath"}

# (file relative to the plugin root, function) -> why is_rooted plus a join is safe there.
ALLOWED_JOINS = {
    ("hooks/compact-resume.py", "_collect_targets"): "the token went through _as_bash_reads, which "
                                                     "already spelled a Git Bash drive as its drive "
                                                     "and dropped any other Git Bash mount",
    ("hooks/git-path-not-here-nudge.py", "notice"): "a rooted path is skipped, never joined; only a "
                                                    "relative one is joined onto the cwd",
}

# (file, function) -> why that function decides the drive reading itself. Empty: every shipped
# caller that reads one word takes the host's reading from `msys_drive_path_for_tool`.
ALLOWED_DRIVE_CALLS: dict[tuple[str, str], str] = {}

# (file, function) -> why that function may read a Git Bash mount at the current drive's root.
ALLOWED_MOUNT_READINGS = {
    ("hooks/block-write-after-sibling-cd.py", "_write_target"): "asks only whether the -C directory "
                                                               "is rooted, and never opens it",
    ("hooks/block-write-after-sibling-cd.py", "targetless_write"): "asks only whether the landing "
                                                                  "is rooted, and never opens it",
}

# (file, function) -> why a command-reading function that places a path with pathlib is safe.
ALLOWED_PATHLIB_RESOLUTION = {
    ("hooks/commit-tell-sweep.py", "same_command_messages"): "its one pathlib check is "
                                                             "provably_missing, which on Windows "
                                                             "checks only a drive path and leaves "
                                                             "a drive-less root unchecked",
}
_PATH_TYPES = {"Path", "PurePath", "PurePosixPath", "PureWindowsPath"}
_ABSOLUTE_CHECKS = {"is_absolute", "isabs"}
# A function calling one of these reads its words the shell's way first (decision-claim-guard's
# candidates spells each word with msys_drive_path_for_tool before pathlib places it).
_SHELL_READINGS = {"resolve_path", "msys_drive_path_for_tool"}


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
    {functions calling msys_drive_path}, {functions passing unknown_mounts=}) for `source`."""
    joins, opt_outs, drive_calls, mount_readings = set(), set(), set(), set()
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
        if any(kw.arg == "unknown_mounts" for call in calls for kw in call.keywords):
            mount_readings.add(fn.name)
    return joins, opt_outs, drive_calls, mount_readings


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
        "def at_root(stmt):\n    return directory_change(stmt, None, unknown_mounts=False)\n"
    )
    assert _findings(source) == ({"join_it"}, {"opt_out"}, {"by_hand"}, {"at_root"})


def _places_with_pathlib(fn):
    """True when `fn` joins a variable onto a variable with pathlib or asks if a path is absolute."""
    for node in ast.walk(fn):
        if (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div)
                and isinstance(node.left, ast.Call) and _called_name(node.left.func) in _PATH_TYPES
                and node.left.args and not isinstance(node.left.args[0], ast.Constant)
                and not isinstance(node.right, (ast.Constant, ast.JoinedStr))):
            return True
        if isinstance(node, ast.Call) and _called_name(node.func) in _ABSOLUTE_CHECKS:
            return True
    return False


def _shell_text_names(tree):
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "shell_text":
            names |= {alias.asname or alias.name for alias in node.names}
    return names


def _is_command_key(node):
    return isinstance(node, ast.Constant) and node.value == "command"


def _reads_command_text(fn, shell_names):
    """True when `fn` calls a shell_text reader or reads a `command` key (`.get` or a subscript)."""
    for node in ast.walk(fn):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in shell_names:
                return True
            if (isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name)
                    and func.value.id == "shell_text"):
                return True
            if _called_name(func) == "get" and node.args and _is_command_key(node.args[0]):
                return True
        if isinstance(node, ast.Subscript) and _is_command_key(node.slice):
            return True
    return False


def _pathlib_resolutions(source):
    """Functions of `source` that read command text and place a path with pathlib, themselves or
    through a function of the same module that does."""
    tree = ast.parse(source)
    shell_names = _shell_text_names(tree)
    functions = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    placers = {fn.name for fn in functions if _places_with_pathlib(fn)}
    found = set()
    for fn in functions:
        if not _reads_command_text(fn, shell_names):
            continue
        called = {_called_name(n.func) for n in ast.walk(fn) if isinstance(n, ast.Call)}
        if called & _SHELL_READINGS:
            continue
        if fn.name in placers or called & placers:
            found.add(fn.name)
    return found


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


def test_a_mount_is_read_at_the_current_drive_only_where_allowed():
    found = {
        (path.relative_to(PLUGIN_ROOT).as_posix(), name)
        for path in _shipped_python_files()
        for name in _findings(path.read_text(encoding="utf-8"))[3]
    }
    assert found == set(ALLOWED_MOUNT_READINGS), (
        "a Git Bash mount is unknown by default (shell_text Decisions); reading it at the current "
        "drive names a directory Git Bash never means")


def test_the_pathlib_detector_finds_both_hooks_it_was_written_for():
    """The two shapes that escaped the drive reading: ci-watch-nudge joined a `git -C` value onto
    the cwd, and tooling-detour-nudge called a pathlib helper on a shell word. A function that
    only joins a constant, or reads no command text, stays quiet."""
    source = (
        "from pathlib import Path\n"
        "from shell_text import commands_only_aligned, iter_segments\n"
        "def repo_dir(command, cwd):\n"
        "    token = commands_only_aligned(command)\n"
        "    return str((Path(cwd) / token).resolve())\n"
        "def resolve(token, cwd):\n"
        "    p = Path(token)\n"
        "    return p if p.is_absolute() else Path(cwd) / p\n"
        "def notice_bash(command, cwd):\n"
        "    for seg in iter_segments(command):\n"
        "        resolve(seg, cwd)\n"
        "def write_path(event, cwd):\n"
        "    return resolve(event['tool_input']['file_path'], cwd)\n"
        "def by_key(event, cwd):\n"
        "    return resolve(event.get('command'), cwd)\n"
        "def state_file(event, home):\n"
        "    return Path(home) / 'state.json', event.get('command')\n"
        "def read_first(event, cwd):\n"
        "    return resolve(msys_drive_path_for_tool(event.get('command')), cwd)\n"
    )
    assert _pathlib_resolutions(source) == {"repo_dir", "notice_bash", "by_key"}


def test_no_command_reader_places_a_path_with_pathlib():
    found = {
        (path.relative_to(PLUGIN_ROOT).as_posix(), name)
        for path in _shipped_python_files()
        for name in _pathlib_resolutions(path.read_text(encoding="utf-8"))
    }
    assert found - set(ALLOWED_PATHLIB_RESOLUTION) == set(), (
        "place a command word with shell_text.resolve_path (or msys_drive_path_for_tool), which "
        "reads a Git Bash drive (/c/...) as its drive and a mount (/tmp/x) as unknown on Windows")
    assert set(ALLOWED_PATHLIB_RESOLUTION) <= found, (
        "an ALLOWED_PATHLIB_RESOLUTION entry no longer matches: remove it")
