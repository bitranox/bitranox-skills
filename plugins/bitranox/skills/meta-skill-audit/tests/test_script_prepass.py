"""Tests for script_prepass.py. ASCII only.

Every check gets a positive AND a negative case: a check that only ever fires is indistinguishable
from one that always fires, and the negative is what proves it could have answered the other way.
The subprocess seams are injected, so nothing here spawns a process."""

import script_prepass as P


def _write(tmp_path, name, body):
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return [(name, path)]


# ---- syntax -------------------------------------------------------------------------------------

def test_syntax_errors_reports_a_file_that_does_not_parse(tmp_path):
    hits = P.syntax_errors(_write(tmp_path, "bad.py", "def f(:\n"))
    assert hits and "does not parse" in hits[0][2]


def test_syntax_errors_is_silent_on_a_good_file(tmp_path):
    assert P.syntax_errors(_write(tmp_path, "ok.py", "def f():\n    return 1\n")) == []


# ---- unguarded third-party imports ---------------------------------------------------------------

def test_a_module_level_third_party_import_in_a_hook_is_reported(tmp_path):
    hits = P.unguarded_third_party_imports(_write(tmp_path, "h.py", "import yaml\n"))
    assert hits and "yaml" in hits[0][2]


def test_a_try_guarded_import_is_not_reported(tmp_path):
    body = "try:\n    import yaml\nexcept ImportError:\n    yaml = None\n"
    assert P.unguarded_third_party_imports(_write(tmp_path, "h.py", body)) == []


def test_a_function_local_import_is_not_reported(tmp_path):
    body = "def load():\n    import yaml\n    return yaml\n"
    assert P.unguarded_third_party_imports(_write(tmp_path, "h.py", body)) == []


def test_a_stdlib_import_is_not_reported(tmp_path):
    assert P.unguarded_third_party_imports(_write(tmp_path, "h.py", "import json, re, sys\n")) == []


def test_a_sibling_module_import_is_not_reported(tmp_path):
    """hooks/ modules import each other freely; they ship together."""
    hits = P.unguarded_third_party_imports(_write(tmp_path, "h.py", "import shell_text\n"),
                                           siblings=["shell_text", "harness_checks"])
    assert hits == []


def test_a_relative_import_is_not_reported(tmp_path):
    assert P.unguarded_third_party_imports(_write(tmp_path, "h.py", "from . import x\n")) == []


def test_prose_beginning_with_from_is_not_mistaken_for_an_import(tmp_path):
    """The reason this is AST and not grep: a docstring line can start with the word 'from'."""
    body = '"""Text\nfrom somewhere ELSE lands in the wrong store.\n"""\nimport json\n'
    assert P.unguarded_third_party_imports(_write(tmp_path, "h.py", body)) == []


# ---- subprocess decoding -------------------------------------------------------------------------

def test_text_true_without_encoding_is_reported(tmp_path):
    body = "import subprocess\nsubprocess.run(['x'], capture_output=True, text=True)\n"
    hits = P.subprocess_text_without_encoding(_write(tmp_path, "s.py", body))
    assert hits and "no encoding=" in hits[0][2]


def test_text_true_with_encoding_is_not_reported(tmp_path):
    body = "import subprocess\nsubprocess.run(['x'], text=True, encoding='utf-8')\n"
    assert P.subprocess_text_without_encoding(_write(tmp_path, "s.py", body)) == []


def test_universal_newlines_without_encoding_is_reported(tmp_path):
    body = "import subprocess\nsubprocess.Popen(['x'], universal_newlines=True)\n"
    assert P.subprocess_text_without_encoding(_write(tmp_path, "s.py", body))


def test_a_bytes_mode_subprocess_is_not_reported(tmp_path):
    body = "import subprocess\nsubprocess.run(['x'], capture_output=True)\n"
    assert P.subprocess_text_without_encoding(_write(tmp_path, "s.py", body)) == []


# ---- Windows portability leads --------------------------------------------------------------------

def test_os_access_x_ok_is_reported_and_allowlistable(tmp_path):
    body = "import os\nos.access('/bin/sh', os.X_OK)\n"
    assert P.os_access_x_ok(_write(tmp_path, "a.py", body))
    assert P.os_access_x_ok(_write(tmp_path, "a.py", body), allow=["a.py"]) == []


def test_a_platform_guarded_x_ok_is_not_reported(tmp_path):
    """harness_checks.is_executable returns False off POSIX before reaching os.access - correct."""
    body = ("import os\n"
            "def is_executable(path, posix=None):\n"
            "    on_posix = (os.name == 'posix') if posix is None else posix\n"
            "    if not on_posix:\n"
            "        return False\n"
            "    return os.access(path, os.X_OK)\n")
    assert P.os_access_x_ok(_write(tmp_path, "a.py", body)) == []


def test_os_access_r_ok_is_not_reported(tmp_path):
    """R_OK is honest on Windows; only the executable bit is the lie."""
    body = "import os\nos.access('/etc/hosts', os.R_OK)\n"
    assert P.os_access_x_ok(_write(tmp_path, "a.py", body)) == []


def test_shlex_is_reported_and_allowlistable(tmp_path):
    body = "import shlex\nshlex.split('a b')\n"
    assert P.shlex_on_paths(_write(tmp_path, "s.py", body))
    assert P.shlex_on_paths(_write(tmp_path, "s.py", body), allow=["s.py"]) == []


def test_hardcoded_tmp_is_reported_but_a_comment_is_not(tmp_path):
    assert P.hardcoded_tmp(_write(tmp_path, "t.py", 'LOG = "/tmp/x.log"\n'))
    assert P.hardcoded_tmp(_write(tmp_path, "t.py", '# writes to /tmp/x.log by default\n')) == []


def test_a_tempfile_call_is_not_reported(tmp_path):
    body = "import tempfile\np = tempfile.mkdtemp()\n"
    assert P.hardcoded_tmp(_write(tmp_path, "t.py", body)) == []


# ---- PEP 723 --------------------------------------------------------------------------------------

_BLOCK = ('# /// script\n# requires-python = ">=%s"\n# dependencies = ["httpx2"]\n# ///\n'
          'import sys\n')


def test_a_hook_carrying_pep723_metadata_is_reported(tmp_path):
    """run-python.sh execs a plain python3, so inline metadata on a hook is a claim nothing honours."""
    hits = P.pep723_problems(_write(tmp_path, "h.py", _BLOCK % "3.11"), hook_kinds=["h.py"])
    assert hits and "run-python.sh resolves none" in hits[0][2]


def test_a_skill_script_carrying_pep723_metadata_is_fine(tmp_path):
    assert P.pep723_problems(_write(tmp_path, "s.py", _BLOCK % "3.11")) == []


def test_a_floor_above_the_ci_minimum_is_reported(tmp_path):
    """That script cannot run on the oldest cell CI actually tests."""
    hits = P.pep723_problems(_write(tmp_path, "s.py", _BLOCK % "3.13"), ci_min="3.11")
    assert hits and "ABOVE the CI minimum" in hits[0][2]


def test_a_floor_below_the_ci_minimum_is_correct_and_is_not_reported(tmp_path):
    """ci.yml: 3.11 is the supported minimum and shipped scripts declare their OWN floors, so a
    wider promise (>=3.10) is deliberate. Reporting it flagged 27 correct files."""
    assert P.pep723_problems(_write(tmp_path, "s.py", _BLOCK % "3.10"), ci_min="3.11") == []


def test_a_script_with_no_block_is_not_reported(tmp_path):
    assert P.pep723_problems(_write(tmp_path, "s.py", "import sys\n")) == []


def test_pep723_block_extracts_only_the_metadata(tmp_path):
    path = (tmp_path / "s.py")
    path.write_text(_BLOCK % "3.12", encoding="utf-8")
    block = P.pep723_block(path)
    assert "requires-python" in block and "import sys" not in block


# ---- per-file test module -------------------------------------------------------------------------

def test_a_script_no_test_module_names_is_reported(tmp_path):
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_other.py").write_text("import other\n", encoding="utf-8")
    hits = P.per_file_test_module(_write(tmp_path, "lonely.py", "x = 1\n"), test_roots=[tests])
    assert hits and "lonely" in hits[0][2]


def test_a_script_a_test_module_names_is_not_reported(tmp_path):
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_x.py").write_text("import covered\n", encoding="utf-8")
    assert P.per_file_test_module(_write(tmp_path, "covered.py", "x = 1\n"), test_roots=[tests]) == []


def test_a_hyphenated_script_matches_its_underscored_test_module(tmp_path):
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_my_guard.py").write_text("import my_guard\n", encoding="utf-8")
    hits = P.per_file_test_module(_write(tmp_path, "my-guard.py", "x = 1\n"), test_roots=[tests])
    assert hits == []


# ---- argparse vs docs (injected seam) --------------------------------------------------------------

class _Proc:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode, self.stdout, self.stderr = returncode, stdout, stderr


def test_a_documented_flag_absent_from_help_is_reported(tmp_path):
    hits = P.argparse_flags_vs_docs(["t.py"], tmp_path, {"t.py": "run `t.py --then CMD`"},
                                    run=lambda *_a, **_k: _Proc(0, "usage: t.py [--other]"))
    assert hits and "--then" in hits[0][2]


def test_a_documented_flag_present_in_help_is_not_reported(tmp_path):
    hits = P.argparse_flags_vs_docs(["t.py"], tmp_path, {"t.py": "run `t.py --then CMD`"},
                                    run=lambda *_a, **_k: _Proc(0, "usage: t.py [--then CMD]"))
    assert hits == []


def test_a_nonzero_exit_is_unmeasured_not_a_finding(tmp_path):
    """Plenty of these cannot run in a room with no host, no browser and no network."""
    hits = P.argparse_flags_vs_docs(["t.py"], tmp_path, {"t.py": "`t.py --then`"},
                                    run=lambda *_a, **_k: _Proc(2, "", "boom"))
    assert hits == []


def test_a_launch_failure_is_unmeasured_not_a_finding(tmp_path):
    def explode(*_a, **_k):
        raise OSError("no interpreter")

    assert P.argparse_flags_vs_docs(["t.py"], tmp_path, {"t.py": "`t.py --then`"}, run=explode) == []


def test_a_script_the_docs_never_mention_is_skipped(tmp_path):
    called = []
    P.argparse_flags_vs_docs(["t.py"], tmp_path, {}, run=lambda *a, **k: called.append(a) or _Proc())
    assert called == []


# ---- js -------------------------------------------------------------------------------------------

def test_js_parse_reports_a_failing_check(tmp_path):
    hits = P.js_parse([("d.js", tmp_path / "d.js")], run=lambda *_a, **_k: _Proc(1, "", "SyntaxError"))
    assert hits and "node --check fails" in hits[0][2]


def test_js_parse_is_silent_when_node_is_absent(tmp_path):
    def no_node(*_a, **_k):
        raise FileNotFoundError("node")

    assert P.js_parse([("d.js", tmp_path / "d.js")], run=no_node) == []


# ---- shaping and the anti-duplication guard --------------------------------------------------------

def test_group_by_file_shapes_hits_for_a_prompt():
    grouped = P.group_by_file([("a.py", 3, "x"), ("a.py", 0, "y"), ("b.py", 1, "z")])
    assert grouped["a.py"] == ["line 3: x", "y"]
    assert grouped["b.py"] == ["line 1: z"]


def test_no_prepass_check_duplicates_a_repo_gate_check():
    """The only automatic defence against this module quietly re-implementing the real gate.

    If this fails, the check belongs in repo-gate.py or is already there - not in both."""
    import importlib.util
    from pathlib import Path

    gate = Path(__file__).resolve().parents[4] / "hooks" / "repo-gate.py"
    if not gate.is_file():                       # a room staged without hooks/ cannot check this
        return
    spec = importlib.util.spec_from_file_location("repo_gate_for_test", gate)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    gate_checks = {n[len("check_"):] for n in dir(module) if n.startswith("check_")}
    assert not (set(P.CHECKS) & gate_checks), "a pre-pass check shadows a repo-gate check"


def test_run_prepass_never_hands_a_js_file_to_the_python_parser(tmp_path):
    """Feeding .js to ast.parse manufactured two 'syntax errors' in files that were fine."""
    room = tmp_path / "plugin"
    (room / "skills" / "s").mkdir(parents=True)
    (room / "skills" / "s" / "d.js").write_text("export const x = `a${1}b`;\n", encoding="utf-8")
    per_file, _summary = P.run_prepass(room, [("skills/s/d.js", "js")])
    assert per_file == {}


def test_a_sibling_script_anywhere_in_the_plugin_is_not_third_party(tmp_path):
    """recall-memory.py reaches a skill script through sys.path; that module ships in the install."""
    room = tmp_path / "plugin"
    (room / "hooks").mkdir(parents=True)
    (room / "skills" / "meta-collect-knowledge").mkdir(parents=True)
    (room / "skills" / "meta-collect-knowledge" / "gather_scan.py").write_text("x = 1\n",
                                                                              encoding="utf-8")
    (room / "hooks" / "recall-memory.py").write_text("import gather_scan\n", encoding="utf-8")
    per_file, _summary = P.run_prepass(room, [("hooks/recall-memory.py", "hook")])
    assert "gather_scan" not in " ".join(per_file.get("hooks/recall-memory.py", []))


def test_run_prepass_reports_every_check_and_groups_by_file(tmp_path):
    room = tmp_path / "plugin"
    (room / "hooks").mkdir(parents=True)
    (room / "hooks" / "bad-hook.py").write_text(
        "import yaml\nimport subprocess\nsubprocess.run(['x'], text=True)\n", encoding="utf-8")
    per_file, summary = P.run_prepass(room, [("hooks/bad-hook.py", "hook")])
    assert "hooks/bad-hook.py" in per_file
    messages = " ".join(per_file["hooks/bad-hook.py"])
    assert "yaml" in messages and "no encoding=" in messages
    assert len(summary) == len(P.CHECKS)
