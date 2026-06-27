"""Behavioural tests for setup_env's pure, importable functions.

conftest.py puts the skill directory on sys.path so `import setup_env` works.
"""
import json

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
    rc = se.main()
    out = capsys.readouterr().out
    assert rc == 0
    assert "Session file:" in out


def test_main_returns_one_without_project(tmp_path, monkeypatch, capsys):
    bare = tmp_path / "bare"
    bare.mkdir()
    monkeypatch.chdir(bare)
    rc = se.main()
    err = capsys.readouterr().err
    assert rc == 1
    assert "pyproject.toml" in err
