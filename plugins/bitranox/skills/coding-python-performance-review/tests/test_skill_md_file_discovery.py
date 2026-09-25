"""Run SKILL.md's own step 4a/4b/4f bash blocks, verbatim, against a project whose files sit
under a directory with a space in its name. The blocks are the interface a reader executes, so a
word-splitting defect there loses files no matter how correct the scripts are."""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parent.parent
STEPS = {
    "4a": "cache/cache_candidates.txt",
    "4b": "cache/uncompiled_regex.txt",
    "4f": "cache/memory_candidates.txt",
}
SOURCE = (
    "import re\n\n"
    "def load(p):\n"
    "    return re.match(r'a+', open(p).read())\n"
)

pytestmark = pytest.mark.skipif(
    os.name == "nt" or shutil.which("bash") is None,
    reason="runs the blocks under a POSIX bash; a Windows bash may be WSL, not Git Bash",
)


def _block(step):
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    section = text.split(f"#### {step}:", 1)[1]
    return re.search(r"```bash\n(.*?)```", section, re.S).group(1)


def _run_step(step, project, files_env=None):
    scratch = project.parent / f"scratch-{step}"
    (scratch / "cache").mkdir(parents=True)
    session = scratch / "session.json"
    session.write_text(json.dumps({"tmpdir": str(scratch), "skill_dir": str(SKILL_DIR),
                                   "python": sys.executable}), encoding="utf-8")
    shim = project.parent / "bin"  # read_field calls a bare `python`
    shim.mkdir(exist_ok=True)
    if not (shim / "python").exists():
        (shim / "python").symlink_to(sys.executable)
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(BX_PERF_SESSION=str(session), PATH=f"{shim}{os.pathsep}{env.get('PATH', '')}")
    env.pop("BX_PERF_FILES", None)
    if files_env is not None:
        env["BX_PERF_FILES"] = files_env
    subprocess.run(["bash", "-c", _block(step)], cwd=project, env=env, capture_output=True,
                   timeout=120, check=False)
    return (scratch / STEPS[step]).read_text(encoding="utf-8")


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
