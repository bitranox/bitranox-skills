"""Run SKILL.md's own bash blocks, verbatim, the way a reader executes them.

The blocks are the interface a reader runs, so a defect there loses results no matter how correct
the scripts are: a word-splitting defect drops files under a directory with a space in its name,
and a bare `python` fails with "command not found" on every Linux or macOS box that has only
`python3`, leaving the step to print its success line over an output file it never wrote.

Every block runs with `python` on PATH as a POISON shim: it records that it was called and exits
127, as a missing command does. `python3` resolves to the test interpreter, and the interpreter
session.json records sits under a directory with a space in its name, so an unquoted
`$PYTHON_CMD` splits.
"""
import json
import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parent.parent
SKILL_MD = SKILL_DIR / "SKILL.md"
STEPS = {
    "4a": "cache/cache_candidates.txt",
    "4b": "cache/uncompiled_regex.txt",
    "4f": "cache/memory_candidates.txt",
}
# The finder's own first line: proof it RAN, not merely that the redirect created its file (a
# launch that fails still leaves the file behind, holding the shell's error).
HEADERS = {
    "4a": "# Cache Candidates Analysis",
    "4b": "# Uncompiled Regex Analysis",
    "4f": "# Unbounded Memory Analysis",
}
SOURCE = (
    "import re\n\n"
    "def load(p):\n"
    "    return re.match(r'a+', open(p).read())\n"
)
SKILL_DIR_PLACEHOLDER = 'SKILL_DIR="/absolute/path/to/skills/coding-python-performance-review"'
# A command word `python` (not python3, not the `read_field python` field argument): at the start
# of a line or right after a pipe, a list operator, a subshell, a brace group or a command
# substitution.
BARE_PYTHON = re.compile(r"(?:^|[;&|(`{]|\$\()\s*python(?=\s|$)", re.MULTILINE)

pytestmark = pytest.mark.skipif(
    os.name == "nt" or shutil.which("bash") is None,
    reason="runs the blocks under a POSIX bash; a Windows bash may be WSL, not Git Bash",
)


def _bash_blocks():
    return re.findall(r"```bash\n(.*?)```", SKILL_MD.read_text(encoding="utf-8"), re.DOTALL)


def _block(heading):
    text = SKILL_MD.read_text(encoding="utf-8")
    section = text.split(heading, 1)[1]
    return re.search(r"```bash\n(.*?)```", section, re.DOTALL).group(1)


def _write_exe(path, body):
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _shim_env(root, session):
    """PATH with a poison `python`, a `python3` that works and a `uv` that is not there."""
    shim = root / "bin"
    shim.mkdir(exist_ok=True)
    marker = root / "bare-python-called"
    _write_exe(shim / "python", f'#!/bin/sh\necho "$0 $*" >> "{marker}"\nexit 127\n')
    _write_exe(shim / "uv", "#!/bin/sh\nexit 127\n")
    if not (shim / "python3").exists():
        (shim / "python3").symlink_to(sys.executable)
    env = {k: v for k, v in os.environ.items() if not k.startswith(("GIT_", "BX_PERF_"))}
    env.update(PATH=f"{shim}{os.pathsep}{env.get('PATH', '')}", TMPDIR=str(root / "tmp"),
               HOME=str(root / "home"))
    (root / "tmp").mkdir(exist_ok=True)
    if session is not None:
        env["BX_PERF_SESSION"] = str(session)
    return env, marker


def _recorded_python(root):
    """An interpreter path holding a space, which an unquoted $PYTHON_CMD splits in two.

    A wrapper that execs the test interpreter, not a symlink to it: a venv python moved away from
    its pyvenv.cfg loses the venv's packages, pytest among them.
    """
    spaced = root / "py bin"
    spaced.mkdir(exist_ok=True)
    target = spaced / "python3"
    if not target.exists():
        _write_exe(target, f'#!/bin/sh\nexec "{sys.executable}" "$@"\n')
    return target


def _session(root, name):
    scratch = root / f"scratch-{name}"
    (scratch / "cache").mkdir(parents=True)
    session = scratch / "session.json"
    session.write_text(json.dumps({"tmpdir": str(scratch), "skill_dir": str(SKILL_DIR),
                                   "python": str(_recorded_python(root))}), encoding="utf-8")
    return scratch, session


def _run(script, cwd, env):
    return subprocess.run(["bash", "-c", script], cwd=cwd, env=env, capture_output=True,
                          text=True, timeout=300, check=False)


def _run_step(step, project, files_env=None):
    scratch, session = _session(project.parent, step)
    env, marker = _shim_env(project.parent, session)
    if files_env is not None:
        env["BX_PERF_FILES"] = files_env
    result = _run(_block(f"#### {step}:"), project, env)
    assert not marker.exists(), marker.read_text(encoding="utf-8")
    out_file = scratch / STEPS[step]
    assert out_file.is_file(), result.stdout + result.stderr
    out = out_file.read_text(encoding="utf-8")
    assert HEADERS[step] in out, out
    return out


@pytest.fixture
def spaced_project(tmp_path):
    project = tmp_path / "proj"
    package = project / "src" / "my pkg"
    package.mkdir(parents=True)
    (package / "a.py").write_text(SOURCE, encoding="utf-8")
    return project


@pytest.mark.parametrize("step", sorted(STEPS))
def test_discovered_path_with_a_space_is_scanned_as_one_file(step, spaced_project):
    out = _run_step(step, spaced_project)
    assert "ERROR" not in out, out
    assert "Found 0 " not in out or step == "4a", out


@pytest.mark.parametrize("step", sorted(STEPS))
def test_bx_perf_files_takes_one_path_per_line(step, spaced_project):
    listed = "src/my pkg/a.py\nsrc/my pkg/missing.py\n"
    out = _run_step(step, spaced_project, files_env=listed)
    # the real file is scanned as one path; the missing one is reported by its full name
    assert "ERROR not found: src/my pkg/missing.py" in out, out
    assert "ERROR not found: src/my\n" not in out, out


def test_no_bash_block_runs_a_bare_python():
    blocks = _bash_blocks()
    assert len(blocks) >= 8, "the block extractor found too few blocks to mean anything"
    hits = [m.group(0).strip() for b in blocks for m in BARE_PYTHON.finditer(b)]
    assert hits == [], hits


def test_every_block_that_reads_the_session_carries_the_same_helpers():
    # each block runs in a fresh shell and re-defines the helpers; a copy that drifts is a block
    # that probes differently from the rest, so they must stay byte-identical
    blocks = [b for b in _bash_blocks() if re.search(r"\b(bx_py|read_field)\b", b)]
    assert len(blocks) == 9, len(blocks)  # the Step 2 bootstrap plus eight readers
    bx_py = re.compile(r"^bx_py\(\) \{.*?\n.*?\}$", re.MULTILINE | re.DOTALL)
    read_field = re.compile(r"^read_field\(\) \{.*?\}$", re.MULTILINE)
    bx_defs = [m.group(0) for b in blocks for m in bx_py.finditer(b)]
    rf_defs = [m.group(0) for b in blocks for m in read_field.finditer(b)]
    assert len(bx_defs) == 9 and len(set(bx_defs)) == 1, bx_defs
    assert len(rf_defs) == 8 and len(set(rf_defs)) == 1, rf_defs


def test_bare_python_detector_fires_on_every_command_position():
    # the control for the test above: each spelling the skill has used must be caught
    for line in ('X="$(python - <<\'PY\'', "uv run a.py || python a.py", "python -c 1",
                 "read_field() { python -c 1; }", "a && python b"):
        assert BARE_PYTHON.search(line), line
    for line in ("python3 -c 1", "PYTHON_CMD=\"$(read_field python)\"", "python_files=()",
                 '"$PYTHON_CMD" -m pytest'):
        assert not BARE_PYTHON.search(line), line


def test_a_block_with_no_session_fails_loudly_instead_of_writing_to_root(spaced_project):
    root = spaced_project.parent
    env, marker = _shim_env(root, root / "no-such-session.json")
    result = _run(_block("#### 4b:"), spaced_project, env)
    assert result.returncode != 0, result.stdout
    assert "scan complete" not in result.stdout, result.stdout
    assert "session" in result.stderr.lower(), result.stderr
    assert not marker.exists()


def test_a_python3_that_exists_but_cannot_run_is_skipped(spaced_project):
    # Windows' python3 is often the Store stub: on PATH, exits non-zero. python is the real one.
    root = spaced_project.parent
    scratch, session = _session(root, "stub")
    env, _marker = _shim_env(root, session)
    shim = root / "bin"
    (shim / "python3").unlink()
    _write_exe(shim / "python3", "#!/bin/sh\necho 'Python was not found' >&2\nexit 9009\n")
    _write_exe(shim / "python", f'#!/bin/sh\nexec "{sys.executable}" "$@"\n')
    result = _run(_block("#### 4b:"), spaced_project, env)
    out = (scratch / STEPS["4b"]).read_text(encoding="utf-8")
    assert result.returncode == 0, result.stderr
    assert HEADERS["4b"] in out, out


def test_step2_bootstrap_runs_without_uv_or_a_bare_python(tmp_path):
    project = tmp_path / "proj"
    project.mkdir()
    (project / "pyproject.toml").write_text("[project]\nname = 'p'\n", encoding="utf-8")
    env, marker = _shim_env(tmp_path, None)
    block = _block("### Step 2: Setup")
    assert SKILL_DIR_PLACEHOLDER in block
    block = block.replace(SKILL_DIR_PLACEHOLDER, f'SKILL_DIR="{SKILL_DIR}"')
    result = _run(block, project, env)
    assert not marker.exists(), marker.read_text(encoding="utf-8")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Session file: " in result.stdout, result.stdout


def test_step7_final_run_uses_the_recorded_interpreter(tmp_path):
    project = tmp_path / "proj"
    (project / "tests").mkdir(parents=True)
    (project / "tests" / "test_ok.py").write_text("def test_ok():\n    pass\n", encoding="utf-8")
    scratch, session = _session(tmp_path, "7")
    env, marker = _shim_env(tmp_path, session)
    result = _run(_block("### Step 7: Final Verification"), project, env)
    assert not marker.exists(), marker.read_text(encoding="utf-8")
    status = (scratch / "cache" / "status.txt").read_text(encoding="utf-8").strip()
    assert status == "SUCCESS", result.stdout + result.stderr
    assert "tests/test_ok.py" in result.stdout, result.stdout
