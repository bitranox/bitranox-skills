"""Behavioural tests for setup_env's pure, importable functions.

conftest.py puts the skill directory on sys.path so `import setup_env` works.
"""
import json
import os
import subprocess
import sys
import tempfile

import setup_env as se

# --- find_project_root -----------------------------------------------------

def test_find_project_root_finds_ancestor(tmp_path):
    root = tmp_path / "proj"
    nested = root / "src" / "pkg"
    nested.mkdir(parents=True)
    (root / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    found = se.find_project_root(nested)
    assert found == root.resolve()


def test_find_project_root_returns_none_when_absent(tmp_path):
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    # tmp_path has no pyproject.toml anywhere up to it
    assert se.find_project_root(nested) is None


def test_find_project_root_self_directory(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    assert se.find_project_root(tmp_path) == tmp_path.resolve()


# --- python_version_ok -----------------------------------------------------

def test_python_version_ok_accepts_and_rejects():
    assert se.python_version_ok((3, 13, 0)) is True
    assert se.python_version_ok((3, 14, 2)) is True
    assert se.python_version_ok((3, 12, 9)) is False
    assert se.python_version_ok((2, 7, 18)) is False


# --- make_scratch_dir ------------------------------------------------------

def test_make_scratch_dir_creates_subdirs():
    tmpdir = se.make_scratch_dir()
    assert tmpdir.is_dir()
    assert tmpdir.name.startswith("bx-perf-")
    for sub in se.SUBDIRS:
        assert (tmpdir / sub).is_dir()


# --- create_session --------------------------------------------------------

def test_create_session_writes_valid_json(tmp_path, monkeypatch):
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    monkeypatch.chdir(proj)

    session = se.create_session()

    # session file exists in the scratch dir and is valid JSON
    session_file = session["session_file"]
    data = json.loads(open(session_file, encoding="utf-8").read())
    for key in ("tmpdir", "project_root", "skill_dir", "python", "status"):
        assert key in data

    assert data["project_root"] == str(proj.resolve())
    assert data["status"] == "IN_PROGRESS"
    assert data["python"]  # sys.executable, non-empty

    # subdirs + status file were created
    tmpdir = se.Path(data["tmpdir"])
    for sub in se.SUBDIRS:
        assert (tmpdir / sub).is_dir()
    status = (tmpdir / "cache" / "status.txt").read_text(encoding="utf-8")
    assert status.strip() == "IN_PROGRESS"


def test_create_session_raises_without_pyproject(tmp_path, monkeypatch):
    bare = tmp_path / "bare"
    bare.mkdir()
    monkeypatch.chdir(bare)
    try:
        se.create_session()
    except FileNotFoundError as exc:
        assert "pyproject.toml" in str(exc)
    else:
        raise AssertionError("expected FileNotFoundError when no pyproject.toml")


def test_main_returns_zero_in_project(tmp_path, monkeypatch, capsys):
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    monkeypatch.chdir(proj)
    rc = se.main(version_info=(3, 13, 0))
    out = capsys.readouterr().out
    assert rc == 0
    assert "Session file:" in out


def test_main_returns_two_without_project(tmp_path, monkeypatch, capsys):
    bare = tmp_path / "bare"
    bare.mkdir()
    monkeypatch.chdir(bare)
    rc = se.main(version_info=(3, 13, 0))
    err = capsys.readouterr().err
    assert rc == 2
    assert "pyproject.toml" in err


def test_main_refuses_an_interpreter_below_the_minimum(tmp_path, monkeypatch, capsys):
    """The version gate itself, which only became reachable in a test once main() grew the
    same version_info seam python_version_ok() already had."""
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    monkeypatch.chdir(proj)
    rc = se.main(version_info=(3, 12, 9))
    err = capsys.readouterr().err
    assert rc == 2
    assert "3.13+ required" in err
    assert "3.12.9" in err


# --- the recorded interpreter is the PROJECT's, not the one running this script ------------

def _venv_python(root, venv=".venv"):
    rel = ("Scripts", "python.exe") if os.name == "nt" else ("bin", "python")
    path = root.joinpath(venv, *rel)
    path.parent.mkdir(parents=True)
    path.write_text("", encoding="utf-8")
    return path


def _project(tmp_path, monkeypatch, name="proj"):
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))  # scratch dirs stay in tmp_path
    proj = tmp_path / name
    (proj / "src").mkdir(parents=True)
    (proj / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    return proj


def test_session_records_the_project_venv_interpreter(tmp_path, monkeypatch):
    # Under `uv run setup_env.py`, sys.executable is uv's throwaway script env, which has
    # neither the project nor pytest installed; every profiling run then fails.
    proj = _project(tmp_path, monkeypatch)
    venv_python = _venv_python(proj.resolve())
    session = se.create_session(start=proj / "src")
    assert session["python"] == str(venv_python)


def test_session_accepts_a_venv_directory_named_venv(tmp_path, monkeypatch):
    proj = _project(tmp_path, monkeypatch)
    venv_python = _venv_python(proj.resolve(), venv="venv")
    assert se.create_session(start=proj)["python"] == str(venv_python)


def test_session_falls_back_to_the_running_interpreter_without_a_venv(tmp_path, monkeypatch):
    proj = _project(tmp_path, monkeypatch)
    assert se.create_session(start=proj)["python"] == sys.executable


def test_main_under_cp1252_stdout_and_a_non_ansi_project_path(tmp_path, clean_env):
    proj = tmp_path / "proj_\u7530\u4e2d"
    proj.mkdir()
    (proj / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    code = "import sys, setup_env; sys.exit(setup_env.main(version_info=(3, 13, 0)))"
    env = clean_env(PYTHONIOENCODING="cp1252", PYTHONPATH=os.path.dirname(se.__file__),
                    TMPDIR=str(tmp_path), TEMP=str(tmp_path), TMP=str(tmp_path))
    r = subprocess.run([sys.executable, "-c", code], cwd=str(proj), env=env,
                       capture_output=True, check=False, timeout=60)
    assert r.returncode == 0, r.stderr
    assert "proj_\u7530\u4e2d" in r.stdout.decode("utf-8")
