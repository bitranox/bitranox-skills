"""profile_with_cache_template: the measure-first gate must not fabricate its evidence.

Two layers. In-process tests drive main() with a fake ``pytest`` module (the suite runner is
the external edge: a real suite would make the numbers machine-dependent) and an injected
clock, so every timing is exact. End-to-end tests copy the template the way SKILL.md Step 6
prescribes - into a separate directory - and run it against a real project with real pytest.
"""
import os
import subprocess
import sys
import types

import pytest

import profile_with_cache_template as pwct

TARGET = "fake_target_mod"
FUNC = "function_to_cache"


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


@pytest.fixture
def target(monkeypatch):
    """A target module whose function counts real (uncached) executions."""
    calls = {"n": 0}
    mod = types.ModuleType(TARGET)

    def slow(x):
        calls["n"] += 1
        return x * 2

    mod.function_to_cache = slow
    monkeypatch.setitem(sys.modules, TARGET, mod)
    monkeypatch.setattr(pwct, "MODULE_NAME", TARGET)
    monkeypatch.setattr(pwct, "FUNCTION_NAME", FUNC)
    return mod, slow, calls


def _fake_pytest(monkeypatch, run):
    """Install a fake pytest whose main() calls run(n) for the n-th suite run (0-based)."""
    fake = types.ModuleType("pytest")
    runs = {"n": 0}

    def fake_main(argv):
        rc = run(runs["n"])
        runs["n"] += 1
        return rc

    fake.main = fake_main
    monkeypatch.setitem(sys.modules, "pytest", fake)
    return runs


def test_a_failing_suite_aborts_instead_of_recommending(monkeypatch, capsys, target):
    mod, slow, _calls = target

    def run(n):
        for _ in range(10):
            sys.modules[TARGET].function_to_cache(21)
        return 1 if sys.modules[TARGET].function_to_cache is not slow else 0  # the cache breaks it

    _fake_pytest(monkeypatch, run)
    rc = pwct.main()
    out = capsys.readouterr().out
    assert rc == 2
    assert "ABORT" in out and "RECOMMEND" not in out
    assert mod.function_to_cache is slow               # the patch is undone after the failure


def test_a_suite_that_fails_without_the_cache_aborts_too(monkeypatch, capsys, target):
    _fake_pytest(monkeypatch, lambda n: 1)
    assert pwct.main() == 2
    assert "ABORT" in capsys.readouterr().out


def test_from_imported_references_are_patched_too(monkeypatch, target):
    """A test module that did `from mod import f` holds its own reference to the original."""
    _mod, slow, calls = target
    test_module = types.ModuleType("fake_test_module")
    test_module.function_to_cache = slow               # what `from fake_target_mod import ...` binds
    monkeypatch.setitem(sys.modules, "fake_test_module", test_module)

    def run(n):
        for _ in range(4):
            sys.modules["fake_test_module"].function_to_cache(21)
        return 0

    _fake_pytest(monkeypatch, run)
    _elapsed, info, hit_rate = pwct.profile_with_cache()
    assert (info.hits, info.misses) == (3, 1)
    assert hit_rate == 75.0
    assert calls["n"] == 1                             # the cache really absorbed the repeats
    assert test_module.function_to_cache is slow       # restored afterwards


def test_cold_start_cost_is_not_credited_to_the_cache(monkeypatch, capsys, target):
    """A/A: the first suite run pays 5 s of import/collection, every run pays 1 s of work.

    Timing cold against warm would read as an 83% "improvement" from a cache that saves
    nothing. Warm against warm reads 0%.
    """
    clock = FakeClock()

    def run(n):
        clock.now += (5.0 if n == 0 else 0.0) + 1.0
        for _ in range(10):
            sys.modules[TARGET].function_to_cache(21)   # hit rate 90%: only timing can reject it
        return 0

    _fake_pytest(monkeypatch, run)
    rc = pwct.main(clock=clock)
    out = capsys.readouterr().out
    assert rc == 0
    assert "Improvement: 0.0%" in out
    assert "REJECT: Performance improvement" in out


# --- end to end: the template copied out of the project, run with real pytest -------------

PROJECT_FILES = {
    "pyproject.toml": "[project]\nname = 'mypkg'\nversion = '0'\n",
    "mypkg/__init__.py": "",
    "mypkg/mod.py": "def f(x):\n    return x + 1\n",
    "tests/test_f.py": ("from mypkg.mod import f\n\n\ndef test_f():\n"
                        "    for _ in range(100):\n        assert f(3) == 4\n"),
}


def _project(tmp_path, files):
    proj = tmp_path / "proj"
    for rel, text in files.items():
        path = proj / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return proj


def _copy_template(tmp_path, module, function):
    """Copy the template to a sibling dir and fill in its two TODO constants, as SKILL.md says."""
    tool = tmp_path / "tool"
    tool.mkdir()
    src = os.path.join(os.path.dirname(pwct.__file__), "profile_with_cache_template.py")
    with open(src, encoding="utf-8") as f:
        text = f.read()
    for old, new in (('MODULE_NAME = "module.submodule"', f'MODULE_NAME = "{module}"'),
                     ('FUNCTION_NAME = "function_to_cache"', f'FUNCTION_NAME = "{function}"')):
        assert text.count(old) == 1, old
        text = text.replace(old, new)
    dest = tool / f"profile_cache_{function}.py"
    dest.write_text(text, encoding="utf-8")
    return dest


def _run(script, cwd, clean_env):
    return subprocess.run([sys.executable, str(script)], cwd=str(cwd), env=clean_env(),
                          capture_output=True, text=True, encoding="utf-8", errors="replace",
                          timeout=180, check=False)


def test_e2e_copied_template_imports_an_uninstalled_project_and_sees_from_imports(tmp_path, clean_env):
    proj = _project(tmp_path, PROJECT_FILES)
    script = _copy_template(tmp_path, "mypkg.mod", "f")
    r = _run(script, proj, clean_env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "ModuleNotFoundError" not in r.stdout + r.stderr
    assert "Cache hits: 99" in r.stdout and "Cache misses: 1" in r.stdout


def test_e2e_failing_suite_exits_2_with_abort(tmp_path, clean_env):
    files = dict(PROJECT_FILES)
    files["tests/test_f.py"] = "from mypkg.mod import f\n\n\ndef test_f():\n    assert f(3) == 5\n"
    proj = _project(tmp_path, files)
    script = _copy_template(tmp_path, "mypkg.mod", "f")
    r = _run(script, proj, clean_env)
    assert r.returncode == 2, r.stdout + r.stderr
    assert "ABORT" in r.stdout and "RECOMMEND" not in r.stdout
