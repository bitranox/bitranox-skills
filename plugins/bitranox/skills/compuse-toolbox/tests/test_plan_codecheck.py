"""Tests for plan_codecheck: a plan's python blocks are placed at their repo paths and checked.

pytest runs for real on this interpreter; ruff and pyright are driven through their real seam, the
`--ruff` / `--pyright` command options, with tiny stand-in programs - CI provisions neither tool.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

import plan_codecheck as pc

TOOL = Path(__file__).resolve().parents[1] / "scripts" / "plan_codecheck.py"


def _write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="")
    return path


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    _write(root / "src" / "pkg" / "__init__.py", "")
    _write(root / "src" / "pkg" / "core.py", "def double(x: int) -> int:\n    return x * 2\n")
    return root


def _plan(tmp_path, body: str) -> Path:
    return _write(tmp_path / "plan.md", body)


GOOD = """# Plan

### Task 1: triple

Create `src/pkg/tri.py`:

```python
from pkg.core import double


def triple(x: int) -> int:
    return double(x) + x
```

```python tests/test_tri.py
from pkg.tri import triple


def test_triple() -> None:
    assert triple(2) == 6
```

### Task 2: something else

```python
raise SystemExit("never placed, never run")
```
"""


def _cli(*args, cwd=None):
    proc = subprocess.run([sys.executable, str(TOOL), *map(str, args)], capture_output=True,
                          text=True, encoding="utf-8", errors="replace", cwd=cwd, timeout=300)
    return proc.returncode, proc.stdout, proc.stderr


# ---- extracting and placing ---------------------------------------------------------------------

def test_a_section_runs_to_the_next_heading_of_its_level():
    lines = pc.section_lines(GOOD, "Task 1")
    texts = [t for _n, t in lines]
    assert texts[0] == "### Task 1: triple"
    assert "### Task 2: something else" not in texts


def test_a_heading_inside_a_code_fence_is_not_a_section_boundary():
    text = "## Task 1\n\n```text\n## Task 1 example\n```\n\n```python\nx = 1\n```\n"
    blocks = pc.extract_blocks(pc.section_lines(text, "Task 1"))
    assert [b.text for b in blocks] == ["x = 1\n"]


def test_a_section_named_twice_is_refused_not_guessed():
    with pytest.raises(pc.PlanError, match="2 headings"):
        pc.section_lines(GOOD, "Task")


def test_a_missing_section_is_refused():
    with pytest.raises(pc.PlanError, match="no heading"):
        pc.section_lines(GOOD, "Task 9")


def test_only_python_blocks_are_extracted_and_a_longer_fence_holds_a_shorter_one():
    text = ("````python\n# file: a.py\ns = '''\n```\n'''\n````\n\n```bash\necho hi\n```\n"
            "\n```py\ny = 2\n```\n")
    blocks = pc.extract_blocks(pc.section_lines(text, None))
    assert len(blocks) == 2
    assert "```" in blocks[0].text and blocks[1].text == "y = 2\n"


def test_each_placement_source_is_honoured_in_order(tmp_path):
    text = ("```python src/a.py\na = 1\n```\n\n"
            "```python\n# file: src/b.py\nb = 1\n```\n\n"
            "Modify `src/c.py:12-30` as follows:\n\n```python\nc = 1\n```\n\n"
            "Just an illustration:\n\n```python\nd = 1\n```\n")
    placed, unplaced = pc.place_blocks(pc.extract_blocks(pc.section_lines(text, None)), tmp_path)
    assert sorted(placed) == ["src/a.py", "src/b.py", "src/c.py"]
    assert [b.text for b in unplaced] == ["d = 1\n"]


def test_two_blocks_naming_one_path_are_joined_in_order(tmp_path):
    text = "```python t.py\nx = 1\n```\n\n```python t.py\ny = 2\n```\n"
    placed, _ = pc.place_blocks(pc.extract_blocks(pc.section_lines(text, None)), tmp_path)
    assert placed["t.py"].index("x = 1") < placed["t.py"].index("y = 2")


@pytest.mark.parametrize("bad", ["../escape.py", "/etc/x.py", "C:/x.py"])
def test_a_path_outside_the_repository_is_refused(tmp_path, bad):
    text = f"```python {bad}\nx = 1\n```\n"
    with pytest.raises(pc.PlanError, match="outside the repository"):
        pc.place_blocks(pc.extract_blocks(pc.section_lines(text, None)), tmp_path)


# ---- the checks, end to end ---------------------------------------------------------------------

def test_a_correct_plan_passes_and_the_real_repo_is_not_touched(tmp_path, repo):
    plan = _plan(tmp_path, GOOD)
    rc, out, err = _cli("--plan", plan, "--section", "Task 1", "--repo", repo, "--check", "pytest",
                        "--python", sys.executable)
    assert rc == 0, out + err
    assert "PASS     pytest" in out
    assert not (repo / "src" / "pkg" / "tri.py").exists()
    assert not (repo / "tests").exists()


def test_a_failing_test_in_the_plan_is_a_finding(tmp_path, repo):
    plan = _plan(tmp_path, GOOD.replace("return double(x) + x", "return double(x)"))
    rc, out, _ = _cli("--plan", plan, "--section", "Task 1", "--repo", repo, "--check", "pytest",
                      "--python", sys.executable)
    assert rc == 1
    assert "FAIL     pytest" in out and "assert 4 == 6" in out


def test_the_plans_version_of_an_existing_file_is_the_one_tested(tmp_path, repo):
    plan = _plan(tmp_path, "## T\n\n```python src/pkg/core.py\ndef double(x: int) -> int:\n"
                           "    return x * 3\n```\n\n```python tests/test_core.py\n"
                           "from pkg.core import double\n\n\ndef test_d() -> None:\n"
                           "    assert double(2) == 6\n```\n")
    rc, out, err = _cli("--plan", plan, "--repo", repo, "--check", "pytest", "--python",
                        sys.executable)
    assert rc == 0, out + err


def test_a_test_file_that_collects_nothing_is_a_failure_not_a_pass(tmp_path, repo):
    plan = _plan(tmp_path, "```python tests/test_empty.py\nx = 1\n```\n")
    rc, out, _ = _cli("--plan", plan, "--repo", repo, "--check", "pytest", "--python",
                      sys.executable)
    assert rc == 1 and "FAIL     pytest" in out


def test_pytest_is_skipped_when_no_placed_path_is_a_test(tmp_path, repo):
    plan = _plan(tmp_path, "```python src/pkg/x.py\nx = 1\n```\n")
    rc, out, _ = _cli("--plan", plan, "--repo", repo, "--check", "pytest", "--json")
    env = json.loads(out)
    assert rc == 0 and env["ok"] is True
    assert any(s.startswith("pytest:") for s in env["skipped"])


def test_an_unplaced_block_keeps_the_run_from_passing_unless_allowed(tmp_path, repo):
    plan = _plan(tmp_path, "## T\n\nAn illustration:\n\n```python\nx = 1\n```\n\n"
                           "```python tests/test_ok.py\ndef test_ok() -> None:\n    assert True\n```\n")
    args = ["--plan", plan, "--repo", repo, "--check", "pytest", "--python", sys.executable]
    rc, out, _ = _cli(*args)
    assert rc == 1 and "UNPLACED" in out
    rc, _out, _ = _cli(*args, "--allow-unplaced")
    assert rc == 0


def test_an_interpreter_without_pytest_is_exit_2_not_a_failing_plan(tmp_path, repo):
    # Under `uv run` with no ./.venv the fallback interpreter has no pytest, and its exit 1 would
    # otherwise read as the plan's tests failing.
    import venv
    bare = tmp_path / "bare"
    venv.create(bare, with_pip=False)
    python = bare / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    plan = _plan(tmp_path, GOOD)
    rc, out, _ = _cli("--plan", plan, "--section", "Task 1", "--repo", repo, "--check", "pytest",
                      "--python", python, "--json")
    env = json.loads(out)
    assert rc == 2 and "has no pytest" in env["error"]


def _fake_ruff(tmp_path):
    """Exits 1 with a finding when the text holds BAD; records the --stdin-filename it got."""
    return _write(tmp_path / "fake_ruff.py", (
        "import sys, pathlib\n"
        "name = sys.argv[sys.argv.index('--stdin-filename') + 1]\n"
        "pathlib.Path(sys.argv[0]).with_name('ruff_seen.txt').open('a', encoding='utf-8')"
        ".write(name + '\\n')\n"
        "text = sys.stdin.read()\n"
        "if 'BAD' in text:\n"
        "    print(name + ':1:1: X001 bad thing')\n"
        "    sys.exit(1)\n"))


def test_ruff_gets_each_block_at_its_repo_path_and_a_finding_is_exit_1(tmp_path, repo):
    fake = _fake_ruff(tmp_path)
    plan = _plan(tmp_path, "```python src/pkg/a.py\nBAD = 1\n```\n\n```python src/pkg/b.py\n"
                           "ok = 1\n```\n")
    rc, out, err = _cli("--plan", plan, "--repo", repo, "--check", "ruff", "--ruff",
                        f"{sys.executable} {fake}")
    assert rc == 1, out + err
    assert "X001" in out
    seen = (tmp_path / "ruff_seen.txt").read_text(encoding="utf-8").split()
    assert sorted(seen) == ["src/pkg/a.py", "src/pkg/b.py"]


def test_a_ruff_that_cannot_run_is_exit_2_not_a_pass(tmp_path, repo):
    crash = _write(tmp_path / "crash.py", "import sys\nsys.exit(2)\n")
    plan = _plan(tmp_path, "```python src/pkg/a.py\na = 1\n```\n")
    rc, out, _ = _cli("--plan", plan, "--repo", repo, "--check", "ruff", "--ruff",
                      f"{sys.executable} {crash}", "--json")
    env = json.loads(out)
    assert rc == 2 and env["ok"] is False and "ruff exited 2" in env["error"]


def _fake_pyright(tmp_path, analysed, errors=()):
    diags = [{"file": "x.py", "severity": "error", "message": m,
              "range": {"start": {"line": 0, "character": 0}}} for m in errors]
    report = {"summary": {"filesAnalyzed": analysed, "errorCount": len(diags)},
              "generalDiagnostics": diags}
    return _write(tmp_path / f"fake_pyright_{analysed}.py",
                  f"import json, sys\nprint(json.dumps({report!r}))\nsys.exit({1 if diags else 0})\n")


def test_pyright_that_analysed_fewer_files_than_were_placed_is_exit_2(tmp_path, repo):
    fake = _fake_pyright(tmp_path, analysed=0)
    plan = _plan(tmp_path, "```python src/pkg/a.py\na = 1\n```\n")
    rc, out, _ = _cli("--plan", plan, "--repo", repo, "--check", "pyright", "--pyright",
                      f"{sys.executable} {fake}", "--json")
    env = json.loads(out)
    assert rc == 2 and "analysed 0 of 1" in env["error"]


def test_a_pyright_error_is_a_finding(tmp_path, repo):
    fake = _fake_pyright(tmp_path, analysed=1, errors=["Type mismatch"])
    plan = _plan(tmp_path, "```python src/pkg/a.py\na = 1\n```\n")
    rc, out, _ = _cli("--plan", plan, "--repo", repo, "--check", "pyright", "--pyright",
                      f"{sys.executable} {fake}")
    assert rc == 1 and "Type mismatch" in out


def test_pyright_is_handed_a_strict_config_naming_exactly_the_placed_files(tmp_path, repo):
    """The config the real pyright reads is what decides what it analyses."""
    capture = _write(tmp_path / "capture.py", (
        "import json, shutil, sys\n"
        "cfg = sys.argv[sys.argv.index('-p') + 1]\n"
        f"shutil.copy(cfg, {str(tmp_path / 'seen.json')!r})\n"
        "print(json.dumps({'summary': {'filesAnalyzed': 2}, 'generalDiagnostics': []}))\n"))
    plan = _plan(tmp_path, GOOD)
    rc, out, err = _cli("--plan", plan, "--section", "Task 1", "--repo", repo, "--check", "pyright",
                        "--pyright", f"{sys.executable} {capture}")
    assert rc == 0, out + err
    seen = json.loads((tmp_path / "seen.json").read_text(encoding="utf-8"))
    assert seen["typeCheckingMode"] == "strict"
    assert sorted(seen["include"]) == ["src/pkg/tri.py", "tests/test_tri.py"]


# ---- refusals ----------------------------------------------------------------------------------

@pytest.mark.parametrize("section,needle", [("Task 9", "no heading"), ("Task", "2 headings"),
                                            ("Task 2", "names a path")])
def test_a_plan_that_cannot_be_checked_prints_the_exit_2_envelope(tmp_path, repo, section, needle):
    plan = _plan(tmp_path, GOOD.replace('raise SystemExit("never placed, never run")', "x = 1"))
    rc, out, _ = _cli("--plan", plan, "--section", section, "--repo", repo, "--json")
    env = json.loads(out)
    assert rc == 2 and env["ok"] is False and needle in env["error"]


def test_a_section_with_no_python_block_is_exit_2(tmp_path, repo):
    plan = _plan(tmp_path, "## T\n\n```bash\necho hi\n```\n")
    rc, _out, err = _cli("--plan", plan, "--repo", repo)
    assert rc == 2 and "no ```python block" in err


def test_a_missing_plan_file_is_exit_2(tmp_path, repo):
    rc, _out, _err = _cli("--plan", tmp_path / "nope.md", "--repo", repo)
    assert rc == 2
