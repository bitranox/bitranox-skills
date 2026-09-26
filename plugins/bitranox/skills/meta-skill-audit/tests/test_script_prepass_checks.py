"""Tests for the tightened script_prepass checks and its main(). ASCII only.

Each defect gets the input that used to slip past (or through) a check, beside the control that must
keep answering the way it did. Subprocess seams are injected; main() runs in process or as a
subprocess of this interpreter only."""

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

import script_prepass as P

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "script_prepass.py"
SKILL_MD = Path(__file__).resolve().parents[1] / "SKILL.md"
BOM = b"\xef\xbb\xbf"


def _write(tmp_path, name, body):
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(body, bytes):
        path.write_bytes(body)
    else:
        path.write_text(body, encoding="utf-8")
    return [(name, path)]


class _Proc:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode, self.stdout, self.stderr = returncode, stdout, stderr


# ---- a UTF-8 BOM is not a syntax error ----------------------------------------------------------

def test_a_bom_file_parses(tmp_path):
    assert P.syntax_errors(_write(tmp_path, "bom.py", BOM + b"import yaml\n")) == []


def test_a_bom_file_still_gets_the_ast_checks(tmp_path):
    hits = P.unguarded_third_party_imports(_write(tmp_path, "bom.py", BOM + b"import yaml\n"))
    assert [(h[0], h[1]) for h in hits] == [("bom.py", 1)]


def test_a_bom_file_control_the_same_file_without_one(tmp_path):
    assert P.syntax_errors(_write(tmp_path, "nobom.py", b"import yaml\n")) == []
    assert P.unguarded_third_party_imports(_write(tmp_path, "nobom.py", b"import yaml\n"))


# ---- os.access(X_OK): which guards count, which calls are seen ----------------------------------

def test_a_darwin_branch_is_not_a_guard_for_x_ok(tmp_path):
    body = ("import os, sys\n"
            "def f(p):\n"
            "    if sys.platform == 'darwin':\n"
            "        return True\n"
            "    return os.access(p, os.X_OK)\n")
    hits = P.os_access_x_ok(_write(tmp_path, "m.py", body))
    assert [h[1] for h in hits] == [5]


def test_a_windows_direction_guard_still_suppresses(tmp_path):
    body = ("import os\n"
            "def f(p):\n"
            "    if os.name != 'posix':\n"
            "        return False\n"
            "    return os.access(p, os.X_OK)\n")
    assert P.os_access_x_ok(_write(tmp_path, "m.py", body)) == []


def test_an_os_name_nt_guard_suppresses(tmp_path):
    body = ("import os\n"
            "def f(p):\n"
            "    if os.name == 'nt':\n"
            "        return False\n"
            "    return os.access(p, os.X_OK)\n")
    assert P.os_access_x_ok(_write(tmp_path, "m.py", body)) == []


def test_an_or_combined_mode_is_seen(tmp_path):
    hits = P.os_access_x_ok(_write(tmp_path, "m.py",
                                   "import os\nos.access('/bin/sh', os.X_OK | os.R_OK)\n"))
    assert [h[1] for h in hits] == [2]


def test_the_bare_name_form_is_seen(tmp_path):
    body = "from os import access, X_OK\naccess('/bin/sh', X_OK)\n"
    assert [h[1] for h in P.os_access_x_ok(_write(tmp_path, "m.py", body))] == [2]


def test_a_bare_name_r_ok_is_not_reported(tmp_path):
    body = "from os import access, R_OK\naccess('/bin/sh', R_OK)\n"
    assert P.os_access_x_ok(_write(tmp_path, "m.py", body)) == []


# ---- a try: guards an import only when it catches ImportError -----------------------------------

@pytest.mark.parametrize("handler", ["except ValueError:\n    pass\n", "finally:\n    pass\n"])
def test_a_try_that_cannot_catch_an_import_error_is_not_a_guard(tmp_path, handler):
    body = "try:\n    import yaml\n" + handler
    assert P.unguarded_third_party_imports(_write(tmp_path, "h.py", body))


@pytest.mark.parametrize("handler", ["except ImportError:", "except ModuleNotFoundError:",
                                     "except (OSError, ImportError):", "except Exception:",
                                     "except:"])
def test_a_try_that_catches_an_import_error_is_a_guard(tmp_path, handler):
    body = "try:\n    import yaml\n%s\n    yaml = None\n" % handler
    assert P.unguarded_third_party_imports(_write(tmp_path, "h.py", body)) == []


# ---- hard-coded /tmp and /var -------------------------------------------------------------------

@pytest.mark.parametrize("line", ['p = Path("/tmp") / "x.log"\n', 'root = "/var"\n',
                                  "LOG = '/tmp/x.log'\n"])
def test_a_bare_or_trailing_tmp_literal_is_reported(tmp_path, line):
    assert P.hardcoded_tmp(_write(tmp_path, "t.py", line))


def test_a_path_that_merely_starts_with_var_is_not_reported(tmp_path):
    assert P.hardcoded_tmp(_write(tmp_path, "t.py", 'p = "/variable/x"\n')) == []


def test_hardcoded_tmp_line_numbers_are_not_shifted_by_a_form_feed(tmp_path):
    hits = P.hardcoded_tmp(_write(tmp_path, "t.py", 'a = 1\n\x0c\nLOG = "/tmp/x"\n'))
    assert [h[1] for h in hits] == [3]


# ---- a test module names the stem as a word, not as a substring --------------------------------

def _tests(tmp_path, name, body):
    tests = tmp_path / "tests"
    tests.mkdir(exist_ok=True)
    (tests / name).write_text(body, encoding="utf-8")
    return tests


def test_a_short_stem_inside_another_test_name_is_not_coverage(tmp_path):
    tests = _tests(tmp_path, "test_other.py", "def test_check_output():\n    assert 1\n")
    hits = P.per_file_test_module(_write(tmp_path, "check.py", "x = 1\n"), test_roots=[tests])
    assert hits and "'check'" in hits[0][2]


@pytest.mark.parametrize("name,body", [
    ("test_check.py", "def test_x():\n    assert 1\n"),
    ("test_other.py", "import check\n"),
    ("test_other.py", "from check import run\n"),
    ("test_other.py", "import os, check\n"),
    ("test_other.py", "SCRIPT = HERE / 'check.py'\n"),
    ("conftest.py", "def fixture():\n    return load_script('check')\n"),
])
def test_a_real_reference_to_the_stem_is_coverage(tmp_path, name, body):
    tests = _tests(tmp_path, name, body)
    assert P.per_file_test_module(_write(tmp_path, "check.py", "x = 1\n"), test_roots=[tests]) == []


def test_a_hyphenated_stem_is_covered_by_its_underscored_import(tmp_path):
    tests = _tests(tmp_path, "test_guard.py", "import my_guard\n")
    assert P.per_file_test_module(_write(tmp_path, "my-guard.py", "x = 1\n"),
                                  test_roots=[tests]) == []


# ---- node --check is actually run ---------------------------------------------------------------

def _room_with_js(tmp_path, body):
    room = tmp_path / "plugin"
    (room / "skills" / "a").mkdir(parents=True)
    (room / "skills" / "a" / "broken.js").write_text(body, encoding="utf-8")
    return room


def test_run_prepass_runs_node_check_over_the_js_targets(tmp_path):
    seen = []

    def run(cmd, cwd, timeout=20):
        seen.append(cmd)
        return _Proc(1, "", "SyntaxError: Unexpected token")

    room = _room_with_js(tmp_path, "function (\n")
    facts, _leads, summary = P.run_prepass(room, [("skills/a/broken.js", "js")], run=run)
    assert "node --check fails" in " ".join(facts.get("skills/a/broken.js", []))
    assert seen == [["node", "--check", "skills/a/broken.js"]]
    assert any(line.startswith("js_parse") for line in summary)


def test_run_prepass_control_a_passing_js_file_is_clean(tmp_path):
    room = _room_with_js(tmp_path, "const x = 1;\n")
    facts, _leads, _summary = P.run_prepass(room, [("skills/a/broken.js", "js")],
                                            run=lambda *_a, **_k: _Proc(0))
    assert facts == {}


def test_run_prepass_never_hands_python_to_node(tmp_path):
    seen = []
    room = tmp_path / "plugin"
    (room / "hooks").mkdir(parents=True)
    (room / "hooks" / "h.py").write_text("x = 1\n", encoding="utf-8")
    P.run_prepass(room, [("hooks/h.py", "hook")], run=lambda cmd, *_a, **_k: seen.append(cmd))
    assert seen == []


# ---- main()-------------------------------------------------------------------------------------

def _fixture_plugin(tmp_path):
    room = tmp_path / "plugin"
    (room / "hooks").mkdir(parents=True)
    (room / "hooks" / "h.py").write_text(
        "import subprocess\nsubprocess.run(['x'], text=True)\n", encoding="utf-8")
    return room


def test_main_on_a_plugin_reports_its_hits_and_target_count(tmp_path, capsys):
    rc = P.main(["--room", str(_fixture_plugin(tmp_path))])
    out = capsys.readouterr().out
    assert rc == 0
    assert "subprocess_text_without_encoding" in out and "1 hit(s)" in out
    assert re.search(r"TOTAL: 1 target\(s\) scanned", out), out


def test_main_json_on_a_plugin(tmp_path, capsys):
    rc = P.main(["--room", str(_fixture_plugin(tmp_path)), "--json"])
    assert rc == 0 and '"hooks/h.py"' in capsys.readouterr().out


@pytest.mark.parametrize("json_flag", [[], ["--json"]])
def test_main_on_a_missing_room_exits_2(tmp_path, capsys, json_flag):
    rc = P.main(["--room", str(tmp_path / "does-not-exist")] + json_flag)
    captured = capsys.readouterr()
    assert rc == 2 and "TOTAL" not in captured.out and "does-not-exist" in captured.err


def test_main_on_a_dir_that_is_not_a_plugin_exits_2(tmp_path, capsys):
    skill = tmp_path / "some-skill"
    skill.mkdir()
    (skill / "SKILL.md").write_text("# x\n", encoding="utf-8")
    assert P.main(["--room", str(skill)]) == 2
    assert "hooks/" in capsys.readouterr().err


def test_main_survives_a_console_that_cannot_encode_the_room_path(tmp_path):
    env = dict(os.environ, PYTHONIOENCODING="cp1252")
    env.pop("PYTHONUTF8", None)
    proc = subprocess.run([sys.executable, str(SCRIPT), "--room",
                           str(tmp_path / "\u6280\u80fd-missing")], capture_output=True, env=env)
    assert proc.returncode == 2, proc.stderr.decode("utf-8", "replace")


# ---- the documented launcher cannot fail silently -----------------------------------------------

SKILLS_DIR = Path(__file__).resolve().parents[2]
# The shim's own first argument, quoted or not. `--hook` is also an ordinary flag of other tools
# (adjudicate.py --hook HOOK.py, memory_engine add --hook "When ..."), so only the word directly
# after run-python.sh selects the shim's fail-open mode.
_FAIL_OPEN_LAUNCH = re.compile(r"run-python\.sh[\"']?\s+--hook\b")


def _fail_open_launches(text):
    """Lines that launch a script through run-python.sh in its `--hook` (fail-open) mode."""
    return [line for line in text.split("\n") if _FAIL_OPEN_LAUNCH.search(line)]


def test_the_fail_open_launch_detector_tells_the_hook_mode_from_a_flag_named_hook():
    assert _fail_open_launches('bash hooks/run-python.sh --hook x.py') != []
    assert _fail_open_launches('bash "$ROOT/hooks/run-python.sh" --hook "$ROOT/x.py"') != []
    assert _fail_open_launches("BITRANOX_RUN_PYTHON_STRICT=1 bash run-python.sh --hook x.py") != []
    assert _fail_open_launches("bash hooks/run-python.sh x.py") == []
    assert _fail_open_launches("bash hooks/run-python.sh x.py --hook H.py") == []
    assert _fail_open_launches("uv run scripts/adjudicate.py --hook HOOK.py") == []
    assert _fail_open_launches("(only a `--hook` launch fails open)") == []


def test_no_skill_md_sends_a_cli_through_the_fail_open_launcher():
    """run-python.sh is strict by default: a CLI launch that cannot run its script (a mistyped
    path, no Python 3) exits 3 with a stderr line. Only `--hook` - the mode hooks.json registers
    hooks with - turns that into exit 0, so a skill step launched that way reads a typo as a clean
    run. BITRANOX_RUN_PYTHON_STRICT=1 does not rescue it: `--hook` also honours the
    BITRANOX_HOOKS_OFF kill-switch, which exits 0 before the script is even looked for.
    A hooks.json registration example belongs in a reference file, not a SKILL.md step."""
    skill_mds = sorted(SKILLS_DIR.glob("*/SKILL.md"))
    assert SKILL_MD.resolve() in [p.resolve() for p in skill_mds], "scanned the wrong directory"
    bad = [f"{path.parent.name}: {line.strip()}" for path in skill_mds
           for line in _fail_open_launches(path.read_text(encoding="utf-8"))]
    assert bad == []


# ---- os.access(X_OK): a platform test guards only the code it dominates -------------------------
# A platform test anywhere in the function used to silence every X_OK call in it, so a call made
# BEFORE the test, or after a branch that falls through, still ran on Windows and was not reported.

def _x_ok_lines(tmp_path, body):
    return [h[1] for h in P.os_access_x_ok(_write(tmp_path, "m.py", body))]


def test_an_x_ok_call_before_the_platform_test_is_reported(tmp_path):
    body = ("import os\n"
            "def f(p):\n"
            "    ok = os.access(p, os.X_OK)\n"
            "    if os.name == 'nt':\n"
            "        print('windows')\n"
            "    return ok\n")
    assert _x_ok_lines(tmp_path, body) == [3]


def test_a_platform_branch_that_falls_through_does_not_guard_the_call_after_it(tmp_path):
    body = ("import os\n"
            "def f(p):\n"
            "    if os.name == 'nt':\n"
            "        print('windows')\n"
            "    return os.access(p, os.X_OK)\n")
    assert _x_ok_lines(tmp_path, body) == [5]


def test_an_early_exit_inside_a_loop_does_not_guard_code_after_the_loop(tmp_path):
    body = ("import os\n"
            "def f(ps, q):\n"
            "    for p in ps:\n"
            "        if os.name == 'nt':\n"
            "            continue\n"
            "        os.access(p, os.X_OK)\n"
            "    return os.access(q, os.X_OK)\n")
    assert _x_ok_lines(tmp_path, body) == [7]


@pytest.mark.parametrize("body", [
    # the call sits inside the POSIX branch
    "import os\ndef f(p):\n    if os.name == 'posix':\n        return os.access(p, os.X_OK)\n"
    "    return False\n",
    # ... or in the else of a Windows test
    "import os\ndef f(p):\n    if os.name == 'nt':\n        return False\n    else:\n"
    "        return os.access(p, os.X_OK)\n",
    # an early exit that raises
    "import os, sys\ndef f(p):\n    if sys.platform.startswith('win'):\n"
    "        raise OSError('posix only')\n    return os.access(p, os.X_OK)\n",
    # the platform test and the call in one expression
    "import os\ndef f(p):\n    return os.name == 'posix' and os.access(p, os.X_OK)\n",
    "import os\ndef f(p):\n    return os.access(p, os.X_OK) if os.name == 'posix' else False\n",
    # a module-level branch
    "import os\nif os.name == 'posix':\n    OK = os.access('/bin/sh', os.X_OK)\n",
])
def test_a_dominating_platform_test_suppresses(tmp_path, body):
    assert _x_ok_lines(tmp_path, body) == []


def test_a_platform_flag_read_in_one_function_does_not_guard_another(tmp_path):
    """The name that carries the platform test is scoped to the function that assigns it."""
    body = ("import os\n"
            "def a():\n"
            "    on_posix = os.name == 'posix'\n"
            "    return on_posix\n"
            "def b(p, on_posix):\n"
            "    if not on_posix:\n"
            "        return False\n"
            "    return os.access(p, os.X_OK)\n")
    assert _x_ok_lines(tmp_path, body) == [8]


# ---- per_file_test_module: a quoted stem counts only where a loader names it ---------------------

@pytest.mark.parametrize("body", [
    "def test_x():\n    assert parse(mode='check')\n",
    "def test_x():\n    assert CHOICES == ['check', 'run']\n",
    "def test_x():\n    assert {'check': 1}\n",
])
def test_a_short_stem_as_an_unrelated_string_is_not_coverage(tmp_path, body):
    tests = _tests(tmp_path, "test_other.py", body)
    hits = P.per_file_test_module(_write(tmp_path, "check.py", "x = 1\n"), test_roots=[tests])
    assert hits and "'check'" in hits[0][2]


@pytest.mark.parametrize("name,body", [
    ("test_other.py", "def test_x():\n    mod = load_script('check')\n"),
    ("test_other.py", "import importlib\nmod = importlib.import_module('check')\n"),
    ("conftest.py", "_HOOK_MODULES = {\n    'check': 'check_alias',\n}\n"),
])
def test_a_loader_naming_the_stem_is_coverage(tmp_path, name, body):
    tests = _tests(tmp_path, name, body)
    assert P.per_file_test_module(_write(tmp_path, "check.py", "x = 1\n"), test_roots=[tests]) == []


def test_a_hyphenated_hook_in_an_alias_map_is_coverage(tmp_path):
    tests = _tests(tmp_path, "conftest.py", "_HOOK_MODULES = {'my-guard': 'my_guard'}\n")
    assert P.per_file_test_module(_write(tmp_path, "my-guard.py", "x = 1\n"),
                                  test_roots=[tests]) == []


# ---- js_parse: no node is UNMEASURED, and a timeout costs one file, not the hits before it -------

def test_js_parse_records_every_file_unmeasured_when_node_is_absent(tmp_path):
    def no_node(*_a, **_k):
        raise FileNotFoundError("node")

    unmeasured = []
    hits = P.js_parse([("a.js", tmp_path / "a.js"), ("b.js", tmp_path / "b.js")], run=no_node,
                      unmeasured=unmeasured)
    assert hits == [] and [u[0] for u in unmeasured] == ["a.js", "b.js"]


def test_js_parse_keeps_earlier_hits_when_a_later_file_times_out(tmp_path):
    replies = iter([_Proc(1, "", "SyntaxError"), subprocess.TimeoutExpired("node", 20), _Proc(0)])

    def run(*_a, **_k):
        reply = next(replies)
        if isinstance(reply, Exception):
            raise reply
        return reply

    unmeasured = []
    hits = P.js_parse([("bad.js", tmp_path / "bad.js"), ("slow.js", tmp_path / "slow.js"),
                       ("ok.js", tmp_path / "ok.js")], run=run, unmeasured=unmeasured)
    assert [h[0] for h in hits] == ["bad.js"]
    assert [u[0] for u in unmeasured] == ["slow.js"]


def test_run_prepass_says_unmeasured_when_node_is_absent(tmp_path):
    def no_node(*_a, **_k):
        raise FileNotFoundError("node")

    room = _room_with_js(tmp_path, "const x = 1;\n")
    _facts, _leads, summary = P.run_prepass(room, [("skills/a/broken.js", "js")], run=no_node)
    line = [s for s in summary if s.startswith("js_parse")][0]
    assert "UNMEASURED" in line and "1 file(s)" in line, line


def test_run_prepass_control_a_measured_js_scan_says_nothing_unmeasured(tmp_path):
    room = _room_with_js(tmp_path, "const x = 1;\n")
    _facts, _leads, summary = P.run_prepass(room, [("skills/a/broken.js", "js")],
                                            run=lambda *_a, **_k: _Proc(0))
    assert not any("UNMEASURED" in s for s in summary), summary
