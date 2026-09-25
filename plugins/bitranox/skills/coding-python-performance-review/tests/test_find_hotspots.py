"""find_hotspots: stdlib filtering, the CLI contract, and a round trip into prioritize.

The profiles are real cProfile output of real code, never a hand-written stats dict.
"""
import cProfile
import importlib.util
import sys
import textwrap

import find_hotspots as fh
import prioritize_cache_candidates as pcc

SCRIPT = "find_hotspots.py"

# Every call busy-waits 1 ms, so 150 calls clear the CLI's fixed thresholds (100 calls,
# 0.1 s cumulative) on any machine: a slower machine only makes the total larger.
BUSY_MODULE = textwrap.dedent('''
    import time
    import textwrap


    def own(text):
        end = time.perf_counter() + 0.001
        while time.perf_counter() < end:
            pass
        return textwrap.wrap(text, 20)


    def driver():
        for _ in range(150):
            own("lorem ipsum dolor sit amet " * 20)
''')


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _profile(tmp_path, subdir="proj", name="busy_mod"):
    d = tmp_path / subdir
    d.mkdir()
    src = d / "m2.py"
    src.write_text(BUSY_MODULE, encoding="utf-8")
    try:
        mod = _load(src, name)
        prof = str(tmp_path / "t.prof")
        cProfile.runctx("driver()", {"driver": mod.driver}, {}, prof)
    finally:
        sys.modules.pop(name, None)
    return prof, src


def test_stdlib_functions_are_not_hotspots(tmp_path):
    prof, src = _profile(tmp_path)
    spots = fh.find_hotspots(prof, min_calls=1, min_cumtime=0.0)
    files = {s["file"] for s in spots}
    assert str(src) in files                      # the project's own function is kept
    assert not any(f.endswith("textwrap.py") for f in files), files


def test_exclude_roots_is_the_filter_seam(tmp_path):
    prof, src = _profile(tmp_path)
    spots = fh.find_hotspots(prof, min_calls=1, min_cumtime=0.0, exclude_roots=[str(src.parent)])
    assert str(src) not in {s["file"] for s in spots}


def test_cli_output_round_trips_into_prioritize(tmp_path, run_script):
    prof, src = _profile(tmp_path)
    r = run_script(SCRIPT, prof)
    assert r.returncode == 0, r.stderr
    hot = tmp_path / "hot.txt"
    hot.write_bytes(r.stdout)
    parsed = pcc.parse_hotspots(str(hot))
    assert {"file": str(src), "line": 6, "function": "own"} in parsed
    assert not any(h["file"].endswith("textwrap.py") for h in parsed)


def test_cli_non_ansi_path_under_cp1252_is_written_as_utf8(tmp_path, run_script, clean_env):
    prof, src = _profile(tmp_path, subdir="j\u00fcrgen_\u7530\u4e2d")
    r = run_script(SCRIPT, prof, env=clean_env(PYTHONIOENCODING="cp1252"))
    assert r.returncode == 0, r.stderr
    assert str(src) in r.stdout.decode("utf-8")


def test_cli_no_arguments_exits_2_with_usage(run_script):
    r = run_script(SCRIPT)
    assert r.returncode == 2 and b"usage" in r.stderr.lower()


def test_cli_unreadable_profile_exits_2_without_traceback(tmp_path, run_script):
    bad = tmp_path / "bad.prof"
    bad.write_text("not a profile", encoding="utf-8")
    for path in (bad, tmp_path / "missing.prof"):
        r = run_script(SCRIPT, str(path))
        assert r.returncode == 2
        assert b"ERROR" in r.stderr and b"Traceback" not in r.stderr


def test_busy_wait_really_clears_the_cli_thresholds(tmp_path):
    """The fixture's own premise: without it the CLI tests would pass on an empty report."""
    prof, _src = _profile(tmp_path)
    spots = fh.find_hotspots(prof)
    assert any(s["function"] == "own" for s in spots)
