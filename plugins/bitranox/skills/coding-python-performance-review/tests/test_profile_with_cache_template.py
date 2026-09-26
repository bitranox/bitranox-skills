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
    assert "ABORT" in out and "RECOMMEND:" not in out
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


# --- repeated, interleaved measurement: one pair of runs is inside the noise ---------------

def _timed_arms(monkeypatch, target, uncached, cached):
    """A fake suite whose k-th run WITHOUT the cache takes uncached[k] seconds and whose k-th
    run WITH it takes cached[k]; the warm-up takes 1 s. Returns (clock, arm order seen).

    The arm is read from what the suite actually calls, never from the run index, so the test
    holds whatever order the template runs the arms in. Past the end of a list it raises, so
    a template that ran more repeats than the lists hold fails by name instead of hanging."""
    _mod, slow, _calls = target
    clock = FakeClock()
    order = []

    def run(n):
        for _ in range(10):
            sys.modules[TARGET].function_to_cache(21)   # hit rate 90%: only timing can reject
        if n == 0:
            clock.now += 1.0
            return 0
        arm = "C" if sys.modules[TARGET].function_to_cache is not slow else "U"
        times = cached if arm == "C" else uncached
        k = order.count(arm)
        assert k < len(times), f"more {arm} runs than the planted timings ({len(times)})"
        order.append(arm)
        clock.now += times[k]
        return 0

    _fake_pytest(monkeypatch, run)
    return clock, order


def _verdict(monkeypatch, capsys, target, uncached, cached):
    monkeypatch.setattr(pwct, "REPEATS", len(uncached), raising=False)
    clock, order = _timed_arms(monkeypatch, target, uncached, cached)
    rc = pwct.main(clock=clock)
    return rc, capsys.readouterr().out, order


def test_one_lucky_pair_of_runs_is_not_a_recommendation(monkeypatch, capsys, target):
    """No benefit, only noise: the first uncached run happened to be 10% slower than the first
    cached one, the other repeats say the arms are the same."""
    rc, out, _order = _verdict(monkeypatch, capsys, target,
                               uncached=[1.10, 1.00, 1.05, 1.02, 1.08],
                               cached=[1.00, 1.10, 1.03, 1.07, 1.01])
    assert rc == 0
    assert "RECOMMEND:" not in out and "REJECT" in out


def test_a_median_gap_inside_the_spread_of_the_runs_is_rejected_as_noise(monkeypatch, capsys, target):
    """Medians 1.22 s vs 1.08 s (11% apart) but the runs overlap: the slowest cached run is
    slower than the fastest uncached one, so the difference does not exceed the spread."""
    rc, out, _order = _verdict(monkeypatch, capsys, target,
                               uncached=[1.30, 1.00, 1.20, 1.25, 1.22],
                               cached=[1.00, 1.28, 1.05, 1.10, 1.08])
    assert rc == 0
    assert "RECOMMEND:" not in out
    assert "REJECT" in out and "noise" in out


def test_a_benefit_larger_than_the_spread_is_recommended(monkeypatch, capsys, target):
    rc, out, _order = _verdict(monkeypatch, capsys, target,
                               uncached=[1.00, 1.02, 0.98, 1.01, 0.99],
                               cached=[0.10, 0.11, 0.09, 0.10, 0.12])
    assert rc == 0
    assert "RECOMMEND:" in out
    assert "Improvement: 90.0%" in out                   # medians 1.00 s vs 0.10 s


def test_the_arms_are_interleaved_not_run_in_two_blocks(monkeypatch, capsys, target):
    """All-uncached-then-all-cached would confound the arm with anything that drifts over the
    run (a warming disk cache, a CPU that throttles)."""
    _rc, _out, order = _verdict(monkeypatch, capsys, target,
                                uncached=[1.0] * 4, cached=[0.5] * 4)
    assert order.count("U") == order.count("C") == 4
    assert "UUU" not in "".join(order) and "CCC" not in "".join(order)
    assert order[:2] != order[2:4]                       # the order alternates between rounds


def test_every_cached_run_starts_with_an_empty_cache(monkeypatch, capsys, target):
    """A cache carried over from an earlier repeat would make later cached runs all hits -
    faster than any real single process run - and inflate the hit rate."""
    _rc, out, _order = _verdict(monkeypatch, capsys, target,
                                uncached=[1.0] * 3, cached=[0.5] * 3)
    assert "Cache hits: 9" in out and "Cache misses: 1" in out


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


def _copy_template(tmp_path, module, function, repeats=None):
    """Copy the template to a sibling dir and fill in its two TODO constants, as SKILL.md says.

    *repeats* overrides REPEATS in the copy (a real user may raise it for a noisy suite)."""
    tool = tmp_path / "tool"
    tool.mkdir()
    src = os.path.join(os.path.dirname(pwct.__file__), "profile_with_cache_template.py")
    with open(src, encoding="utf-8") as f:
        text = f.read()
    edits = [('MODULE_NAME = "module.submodule"', f'MODULE_NAME = "{module}"'),
             ('FUNCTION_NAME = "function_to_cache"', f'FUNCTION_NAME = "{function}"')]
    if repeats is not None:
        edits.append((f"REPEATS = {pwct.REPEATS}", f"REPEATS = {repeats}"))
    for old, new in edits:
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
    assert "ABORT" in r.stdout and "RECOMMEND:" not in r.stdout


def test_e2e_a_cache_with_no_benefit_is_not_recommended(tmp_path, clean_env):
    """x + 1 costs what a cache lookup costs. A single uncached/cached pair recommended it in
    3-4 of 10 runs from timing noise alone.

    REPEATS is raised in the copy to 7: under pure noise all 7 cached runs beat all 7
    uncached ones with probability 1/3432, so this test cannot flake at a visible rate."""
    proj = _project(tmp_path, PROJECT_FILES)
    script = _copy_template(tmp_path, "mypkg.mod", "f", repeats=7)
    r = _run(script, proj, clean_env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "Cache hits: 99" in r.stdout                  # the cache was exercised: liveness
    assert "RECOMMEND:" not in r.stdout and "REJECT" in r.stdout


def test_e2e_an_expensive_pure_function_is_recommended(tmp_path, clean_env):
    """Each call sleeps 10 ms, so an uncached run takes at least 0.3 s and a cached run pays
    one miss: the separation is decided by sleep() lower bounds, not by how fast the host is."""
    files = dict(PROJECT_FILES)
    files["mypkg/mod.py"] = "import time\n\n\ndef f(x):\n    time.sleep(0.01)\n    return x + 1\n"
    files["tests/test_f.py"] = ("from mypkg.mod import f\n\n\ndef test_f():\n"
                                "    for _ in range(30):\n        assert f(3) == 4\n")
    proj = _project(tmp_path, files)
    script = _copy_template(tmp_path, "mypkg.mod", "f")
    r = _run(script, proj, clean_env)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "RECOMMEND:" in r.stdout, r.stdout
