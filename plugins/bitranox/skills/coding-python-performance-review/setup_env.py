# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Portable, stdlib-only bootstrap for the python-performance-review skill.

Replaces the old POSIX-only bash "Setup" step. Cross-platform (works on
Windows, macOS, Linux): no hardcoded /tmp, no mktemp, no `command -v`, no
bash traps. All logic lives in importable, unit-testable functions; only
main() runs under the __main__ guard.

What it establishes (the equivalent of the old bash Setup):

* PROJECT_ROOT - found by walking up from the current directory for a
  pyproject.toml (clear error + non-zero exit if none).
* a scratch temp directory created with tempfile.mkdtemp(prefix="bx-perf-")
  plus its cache/ logs/ perf/ subdirectories.
* SKILL_DIR  - the directory containing this file (via __file__).
* PYTHON     - the PROJECT's interpreter, which the profiling steps run the test
  suite with: <root>/.venv or <root>/venv when one exists, else the interpreter
  running this script (with a note on stderr). A project venv therefore wins over
  uv's throwaway script env, which has neither the project nor pytest installed,
  when `uv run setup_env.py` launched this; without one, the launcher decides, so
  SKILL.md launches with the user's own python first and `uv run` only as the
  fallback. The recorded interpreter is RUN once to read its version: every later
  step uses it, so it - not the interpreter running this script - must be
  MIN_PYTHON or newer, and one that cannot start at all is refused here rather
  than at the first profiling step.
* a status file (cache/status.txt -> IN_PROGRESS).
* session.json written INTO the scratch dir, holding every path later steps
  need. This single file replaces the old /tmp/bx-perf-session and
  /tmp/bx-perf-skill-dir side-channel files.

Later steps read session.json instead of the /tmp side-channel files, e.g.:

    python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['tmpdir'])" SESSION_JSON

(SKILL.md's read_field does the same with the first of python3, python, py -3 that starts: a bare
`python` is missing on most Linux boxes and on macOS.)

Exit codes: 0 session created, 2 it could not be (no pyproject.toml, or the recorded
interpreter cannot run or is older than MIN_PYTHON; nothing is created then).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# The oldest interpreter the finders and the profiling steps are exercised on.
MIN_PYTHON = (3, 10)
_VERSION_PROBE = "import sys; print('%d.%d.%d' % sys.version_info[:3])"
_PROBE_TIMEOUT_SECONDS = 60
SESSION_FILENAME = "session.json"
NO_PROJECT_MESSAGE = "No pyproject.toml found in any parent directory. Not a Python project."
SUBDIRS = ("cache", "logs", "perf")
VENV_DIRS = (".venv", "venv")


def find_project_root(start):
    """Walk up from *start* looking for a directory containing pyproject.toml.

    Returns the Path of the first ancestor (including *start* itself) that
    holds a pyproject.toml, or None if none is found up to the filesystem root.
    """
    current = Path(start).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate
    return None


def skill_dir():
    """Return the directory that contains this script (the skill directory)."""
    return Path(__file__).resolve().parent


def python_version_ok(version_info=None):
    """Return True if *version_info* (default: the running interpreter) is at least MIN_PYTHON."""
    info = version_info if version_info is not None else sys.version_info
    return (info[0], info[1]) >= MIN_PYTHON


def interpreter_version(python):
    """Run *python* once and return its (major, minor, micro), or None if it cannot run.

    None covers a missing file, a file that is not an interpreter, a non-zero exit, a hang and
    output that is not a version: each means the later steps could not use it either.
    """
    try:
        result = subprocess.run(
            [str(python), "-c", _VERSION_PROBE], capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=_PROBE_TIMEOUT_SECONDS, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    parts = result.stdout.strip().split(".")
    if result.returncode != 0 or len(parts) != 3 or not all(p.isdigit() for p in parts):
        return None
    return tuple(int(p) for p in parts)


def project_python(root):
    """Return the interpreter of the project's own virtualenv under *root*, or None.

    The path is NOT resolved: a venv's python is a symlink to the base interpreter, and
    following it would record an interpreter without the venv's packages.
    """
    rel = ("Scripts", "python.exe") if os.name == "nt" else ("bin", "python")
    for venv in VENV_DIRS:
        candidate = Path(root).joinpath(venv, *rel)
        if candidate.is_file():
            return candidate
    return None


def choose_python(root):
    """Return the project's venv interpreter, else the interpreter running this script."""
    venv_python = project_python(root)
    return str(venv_python) if venv_python is not None else sys.executable


def make_scratch_dir():
    """Create and return a fresh scratch temp dir plus its subdirectories.

    Uses tempfile.mkdtemp so the location honours TMPDIR / TEMP / TMP and is
    valid on every OS (never a hardcoded /tmp).
    """
    tmpdir = Path(tempfile.mkdtemp(prefix="bx-perf-"))
    for sub in SUBDIRS:
        (tmpdir / sub).mkdir(parents=True, exist_ok=True)
    return tmpdir


def create_session(start=None):
    """Build the session: validate the project, create scratch dirs, write session.json.

    Returns the session dict. Raises FileNotFoundError if no pyproject.toml is
    found walking up from *start* (defaults to the current working directory).
    """
    root = find_project_root(start if start is not None else Path.cwd())
    if root is None:
        raise FileNotFoundError(NO_PROJECT_MESSAGE)

    tmpdir = make_scratch_dir()
    session = {
        "tmpdir": str(tmpdir),
        "project_root": str(root),
        "skill_dir": str(skill_dir()),
        "python": choose_python(root),
        "status": "IN_PROGRESS",
    }

    (tmpdir / "cache" / "status.txt").write_text("IN_PROGRESS\n", encoding="utf-8")

    session_path = tmpdir / SESSION_FILENAME
    session_path.write_text(
        json.dumps(session, indent=2) + "\n", encoding="utf-8"
    )
    session["session_file"] = str(session_path)
    return session


def _utf8_output():
    # A cp1252 console cannot encode most non-ASCII paths; this output is parsed as text.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="backslashreplace")
        except (ValueError, OSError):
            pass


def interpreter_problem(python, version_info=None):
    """Why *python* cannot run the later steps, or None when it can.

    `version_info` stands in for running *python* (a test seam, like python_version_ok's).
    """
    version = version_info if version_info is not None else interpreter_version(python)
    if version is None:
        return (f"the recorded interpreter {python} could not be run to read its version; "
                f"repair or recreate the project virtualenv")
    if not python_version_ok(version):
        got = ".".join(str(p) for p in version[:3])
        want = ".".join(str(p) for p in MIN_PYTHON)
        return f"Python {want}+ required, but the recorded interpreter {python} is {got}"
    return None


def main(argv=None, version_info=None):
    """Run the bootstrap. Print session.json's path and contents; return exit code.

    The version gate judges the interpreter the session RECORDS (the project's venv, else the
    one running this script), because that is the one every later step runs. `version_info`
    replaces running it, so the rest of main() can be tested without a real old interpreter.
    Nothing is created when the gate refuses.
    """
    _utf8_output()
    root = find_project_root(Path.cwd())
    if root is None:
        print(f"ERROR: {NO_PROJECT_MESSAGE}", file=sys.stderr)
        return 2
    problem = interpreter_problem(choose_python(root), version_info)
    if problem is not None:
        print(f"ERROR: {problem}.", file=sys.stderr)
        return 2

    session = create_session(start=root)

    if project_python(session["project_root"]) is None:
        print(
            f"NOTE: no project virtualenv ({' or '.join(VENV_DIRS)}) under "
            f"{session['project_root']}; recorded the interpreter running this script "
            f"({session['python']}). If it cannot import the project and pytest, set "
            f"'python' in {session['session_file']}.",
            file=sys.stderr,
        )

    print(f"Session file: {session['session_file']}")
    print(f"Project root: {session['project_root']}")
    print(f"Scratch dir:  {session['tmpdir']}")
    print(f"Skill dir:    {session['skill_dir']}")
    print(f"Python:       {session['python']}")
    print(json.dumps(session, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
