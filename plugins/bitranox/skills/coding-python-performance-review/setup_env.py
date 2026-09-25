# /// script
# requires-python = ">=3.13"
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
  running this script (with a note on stderr). Never uv's throwaway script env,
  which `uv run setup_env.py` would otherwise record and which has neither the
  project nor pytest installed.
* a status file (cache/status.txt -> IN_PROGRESS).
* session.json written INTO the scratch dir, holding every path later steps
  need. This single file replaces the old /tmp/bx-perf-session and
  /tmp/bx-perf-skill-dir side-channel files.

Later steps read session.json instead of the /tmp side-channel files, e.g.:

    python -c "import json,sys; print(json.load(open(sys.argv[1]))['tmpdir'])" SESSION_JSON

Exit codes: 0 session created, 2 it could not be (no pyproject.toml, interpreter too old).
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

MIN_PYTHON = (3, 13)
SESSION_FILENAME = "session.json"
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
    """Return True if the running interpreter is at least MIN_PYTHON."""
    info = version_info if version_info is not None else sys.version_info
    return (info[0], info[1]) >= MIN_PYTHON


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
        raise FileNotFoundError(
            "No pyproject.toml found in any parent directory. Not a Python project."
        )

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


def main(argv=None, version_info=None):
    """Run the bootstrap. Print session.json's path and contents; return exit code.

    `version_info` is the same injection seam python_version_ok() offers, so the rest of
    main() can be tested on any interpreter. Without it these tests could only run on 3.13+,
    which is precisely the versions the CI matrix added.
    """
    _utf8_output()
    if not python_version_ok(version_info):
        got = ".".join(str(p) for p in (version_info or sys.version_info)[:3])
        want = ".".join(str(p) for p in MIN_PYTHON)
        print(
            f"ERROR: Python {want}+ required, but running {got} "
            f"({sys.executable}).",
            file=sys.stderr,
        )
        return 2

    try:
        session = create_session()
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

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
