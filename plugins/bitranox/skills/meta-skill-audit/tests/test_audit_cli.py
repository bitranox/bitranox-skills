"""End-to-end tests for audit_skills.main() and its real reviewer launcher. ASCII only.

The reviewer is a FAKE `claude` put first on PATH - PATH is the one true external edge here - so
these run the real `_subprocess_runner`, the real room staging and the real pre-pass, and never
spawn a real reviewer or touch the network. Each fake records its argv to a log file so the hook
switch can be asserted on the command the CLI would really receive."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import audit_skills as A

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "audit_skills.py"

FAKE = r'''
import json, os, sys, time
log = os.environ.get("FAKE_CLAUDE_LOG")
if log:
    with open(log, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(sys.argv[1:]) + "\n")
sys.stdin.read()
mode = os.environ.get("FAKE_CLAUDE_MODE", "clean")
if mode == "clean":
    print("NO FINDINGS")
elif mode == "fail":
    sys.stderr.write("Invalid API key\n")
    sys.exit(1)
elif mode == "prose":
    print("Looking back, nothing unsettled.")
elif mode == "sleep":
    time.sleep(3)
    print("NO FINDINGS")
'''


def _fake_claude(tmp_path, monkeypatch, mode="clean"):
    """Install a fake `claude` first on PATH. Returns the argv log path."""
    bindir = tmp_path / "bin"
    bindir.mkdir(exist_ok=True)
    script = bindir / "fake_claude.py"
    script.write_text(FAKE, encoding="utf-8")
    if os.name == "nt":
        (bindir / "claude.cmd").write_text('@"%s" "%s" %%*\r\n' % (sys.executable, script),
                                           encoding="utf-8")
    else:
        exe = bindir / "claude"
        exe.write_text("#!%s\n%s" % (sys.executable, FAKE), encoding="utf-8")
        exe.chmod(0o755)
    log = tmp_path / "claude-argv.log"
    monkeypatch.setenv("PATH", str(bindir) + os.pathsep + os.environ.get("PATH", ""))
    monkeypatch.setenv("FAKE_CLAUDE_LOG", str(log))
    monkeypatch.setenv("FAKE_CLAUDE_MODE", mode)
    return log


def _plugin(tmp_path):
    root = tmp_path / "src" / "plugin"
    (root / "skills" / "alpha" / "scripts").mkdir(parents=True)
    (root / "skills" / "alpha" / "SKILL.md").write_text("# alpha\n", encoding="utf-8")
    (root / "skills" / "alpha" / "scripts" / "x.py").write_text("X = 1\n", encoding="utf-8")
    (root / "hooks").mkdir()
    (root / "hooks" / "my-guard.py").write_text("import sys\n", encoding="utf-8")
    return root


def _loose_skills(tmp_path):
    skills = tmp_path / "home" / ".claude" / "skills"
    (skills / "toolbox").mkdir(parents=True)
    (skills / "toolbox" / "SKILL.md").write_text("# toolbox\n", encoding="utf-8")
    return skills


def _report(tmp_path, stem):
    return (tmp_path / "room" / "reports" / ("%s.audit.txt" % stem)).read_text(encoding="utf-8")


# ---- the reviewer launcher ----------------------------------------------------------------------

def test_every_reviewer_is_launched_with_all_hooks_disabled(tmp_path, monkeypatch):
    """The user's Stop hooks replaced 6 of 79 reports; their SessionStart hooks wrote into the room."""
    log = _fake_claude(tmp_path, monkeypatch)
    assert A.main(["--plugin", str(_plugin(tmp_path)), "--room", str(tmp_path / "room")]) == 0
    argv = json.loads(log.read_text(encoding="utf-8").splitlines()[0])
    settings = argv[argv.index("--settings") + 1]
    assert json.loads(settings) == {"disableAllHooks": True}
    assert argv[:2] == ["-p", "--model"]


def test_a_failing_cli_makes_the_run_exit_1_and_says_why(tmp_path, monkeypatch):
    _fake_claude(tmp_path, monkeypatch, mode="fail")
    rc = A.main(["--plugin", str(_plugin(tmp_path)), "--room", str(tmp_path / "room")])
    body = _report(tmp_path, "alpha")
    assert rc == 1
    assert "claude exited 1" in body.splitlines()[0] and "Invalid API key" in body


def test_a_clean_run_exits_0(tmp_path, monkeypatch):
    """The control for the test above: same fake, succeeding."""
    _fake_claude(tmp_path, monkeypatch, mode="clean")
    assert A.main(["--plugin", str(_plugin(tmp_path)), "--room", str(tmp_path / "room")]) == 0
    assert _report(tmp_path, "alpha") == "NO FINDINGS"


def test_a_reviewer_that_ends_on_prose_makes_the_run_exit_1(tmp_path, monkeypatch):
    _fake_claude(tmp_path, monkeypatch, mode="prose")
    rc = A.main(["--scripts", "--plugin", str(_plugin(tmp_path)), "--room", str(tmp_path / "room")])
    assert rc == 1
    assert _report(tmp_path, "hooks__my-guard").startswith(A.REPORT_MISSING_MARKER)


def test_a_missing_cli_is_recorded_as_not_found(tmp_path, monkeypatch):
    empty = tmp_path / "emptybin"
    empty.mkdir()
    monkeypatch.setenv("PATH", str(empty))
    rc = A.main(["--plugin", str(_plugin(tmp_path)), "--room", str(tmp_path / "room")])
    assert rc == 1 and "not found" in _report(tmp_path, "alpha").splitlines()[0]


def test_a_timed_out_reviewer_is_recorded_as_a_timeout(tmp_path, monkeypatch):
    _fake_claude(tmp_path, monkeypatch, mode="sleep")
    rc = A.main(["--plugin", str(_plugin(tmp_path)), "--room", str(tmp_path / "room"),
                 "--timeout", "1"])
    assert rc == 1 and "timed out" in _report(tmp_path, "alpha").splitlines()[0]


# ---- listing what a run would review ------------------------------------------------------------

def test_list_of_a_skills_dir_counts_its_skills(tmp_path, capsys):
    rc = A.main(["--list", "--skills-dir", str(_loose_skills(tmp_path)),
                 "--room", str(tmp_path / "room")])
    out = capsys.readouterr().out
    assert rc == 0 and "toolbox" in out and "TOTAL: 1 skill(s)" in out


def test_list_previews_the_source_a_fresh_run_would_copy_not_a_stale_room(tmp_path, monkeypatch,
                                                                          capsys):
    _fake_claude(tmp_path, monkeypatch)
    src = _plugin(tmp_path)
    room = str(tmp_path / "room")
    assert A.main(["--scripts", "--plugin", str(src), "--room", room]) == 0
    (src / "skills" / "alpha" / "scripts" / "new.py").write_text("N = 1\n", encoding="utf-8")
    capsys.readouterr()
    assert A.main(["--list", "--scripts", "--plugin", str(src), "--room", room]) == 0
    fresh = capsys.readouterr().out
    assert "new.py" in fresh and "TOTAL: 3 script(s)" in fresh


def test_list_with_reuse_room_previews_the_room_copy(tmp_path, monkeypatch, capsys):
    """The control: --reuse-room reviews the existing copy, so that is what --list must show."""
    _fake_claude(tmp_path, monkeypatch)
    src = _plugin(tmp_path)
    room = str(tmp_path / "room")
    assert A.main(["--scripts", "--plugin", str(src), "--room", room]) == 0
    (src / "skills" / "alpha" / "scripts" / "new.py").write_text("N = 1\n", encoding="utf-8")
    capsys.readouterr()
    assert A.main(["--list", "--scripts", "--reuse-room", "--plugin", str(src), "--room", room]) == 0
    reused = capsys.readouterr().out
    assert "new.py" not in reused and "TOTAL: 2 script(s)" in reused


# ---- refusals exit 2 ----------------------------------------------------------------------------

def test_scripts_mode_refuses_a_skills_dir(tmp_path, capsys):
    with pytest.raises(SystemExit) as caught:
        A.main(["--scripts", "--skills-dir", str(_loose_skills(tmp_path)),
                "--room", str(tmp_path / "room")])
    assert caught.value.code == 2 and "--plugin" in capsys.readouterr().err


@pytest.mark.parametrize("flag", [["--kind", "hook"], ["--skip-existing"], ["--include-vendored"]])
def test_a_scripts_only_flag_in_skill_mode_is_refused(tmp_path, monkeypatch, capsys, flag):
    """The skill sweep cannot honour these; accepting them silently reviewed every skill."""
    log = _fake_claude(tmp_path, monkeypatch)
    with pytest.raises(SystemExit) as caught:
        A.main(flag + ["--plugin", str(_plugin(tmp_path)), "--room", str(tmp_path / "room")])
    err = capsys.readouterr().err
    assert caught.value.code == 2 and flag[0] in err and "--scripts" in err
    assert not log.exists() and not (tmp_path / "room").exists()


@pytest.mark.parametrize("flag", [["--kind", "hook"], ["--skip-existing"], ["--include-vendored"]])
def test_a_scripts_only_flag_with_scripts_is_accepted(tmp_path, capsys, flag):
    """Control: the same flag in the mode that honours it."""
    rc = A.main(["--list", "--scripts"] + flag + ["--plugin", str(_plugin(tmp_path)),
                                                  "--room", str(tmp_path / "room")])
    assert rc == 0 and "TOTAL:" in capsys.readouterr().out


def test_hooks_dir_without_skills_dir_is_refused(tmp_path, capsys):
    hooks = _plugin(tmp_path) / "hooks"
    with pytest.raises(SystemExit) as caught:
        A.main(["--list", "--hooks-dir", str(hooks), "--plugin", str(hooks.parent),
                "--room", str(tmp_path / "room")])
    assert caught.value.code == 2 and "--hooks-dir" in capsys.readouterr().err


def test_hooks_dir_with_skills_dir_is_accepted(tmp_path, capsys):
    """Control: --hooks-dir is honoured beside --skills-dir."""
    hooks = _plugin(tmp_path) / "hooks"
    rc = A.main(["--list", "--hooks-dir", str(hooks), "--skills-dir", str(_loose_skills(tmp_path)),
                 "--room", str(tmp_path / "room")])
    assert rc == 0 and "toolbox" in capsys.readouterr().out


def test_a_room_inside_the_source_is_refused_by_the_cli(tmp_path, monkeypatch, capsys):
    log = _fake_claude(tmp_path, monkeypatch)
    src = _plugin(tmp_path)
    assert A.main(["--plugin", str(src), "--room", str(src / "auditroom")]) == 2
    assert "inside the source" in capsys.readouterr().err
    assert not (src / "auditroom").exists() and not log.exists()
    assert A.main(["--list", "--plugin", str(src), "--room", str(src / "auditroom")]) == 2


def test_an_unknown_kind_is_refused(tmp_path):
    with pytest.raises(SystemExit) as caught:
        A.main(["--scripts", "--kind", "hooks", "--plugin", str(_plugin(tmp_path)),
                "--room", str(tmp_path / "room")])
    assert caught.value.code == 2


@pytest.mark.parametrize("mode", [["--scripts"], []])
def test_an_only_that_selects_nothing_exits_2(tmp_path, monkeypatch, mode):
    log = _fake_claude(tmp_path, monkeypatch)
    rc = A.main(mode + ["--only", "nosuchthing", "--plugin", str(_plugin(tmp_path)),
                        "--room", str(tmp_path / "room")])
    assert rc == 2 and not log.exists(), "no reviewer may be spent on an empty selection"


def test_a_known_kind_selects_its_slice(tmp_path, monkeypatch, capsys):
    """The control for the two tests above."""
    _fake_claude(tmp_path, monkeypatch)
    rc = A.main(["--scripts", "--kind", "hook", "--plugin", str(_plugin(tmp_path)),
                 "--room", str(tmp_path / "room")])
    assert rc == 0 and "across 1 script(s)" in capsys.readouterr().out


def test_a_source_inside_the_room_is_refused_and_kept(tmp_path, monkeypatch):
    _fake_claude(tmp_path, monkeypatch)
    room = tmp_path / "room"
    assert A.main(["--plugin", str(_plugin(tmp_path)), "--room", str(room)]) == 0
    assert A.main(["--plugin", str(room / "plugin"), "--room", str(room)]) == 2
    assert (room / "plugin" / "skills" / "alpha" / "SKILL.md").is_file()


def test_a_crash_exits_2_not_1(tmp_path):
    """1 means 'a target has no report'; a crash must not read as that verdict."""
    rc = A.main(["--plugin", str(tmp_path / "does-not-exist"), "--room", str(tmp_path / "room")])
    assert rc == 2


def test_help_describes_skip_existing_as_a_complete_report():
    out = subprocess.run([sys.executable, str(SCRIPT), "--help"], capture_output=True,
                         text=True, encoding="utf-8", errors="replace", check=True).stdout
    flat = " ".join(out.split())
    assert "non-empty" not in flat and "complete report" in flat


# ---- output survives a non-UTF-8 console --------------------------------------------------------

def test_list_survives_a_console_that_cannot_encode_a_skill_name(tmp_path):
    skills = tmp_path / "skills"
    (skills / "werkzeug-\u6280\u80fd").mkdir(parents=True)
    (skills / "werkzeug-\u6280\u80fd" / "SKILL.md").write_text("# x\n", encoding="utf-8")
    env = dict(os.environ, PYTHONIOENCODING="cp1252")
    env.pop("PYTHONUTF8", None)
    proc = subprocess.run([sys.executable, str(SCRIPT), "--list", "--skills-dir", str(skills),
                           "--room", str(tmp_path / "room")], capture_output=True, env=env)
    assert proc.returncode == 0, proc.stderr.decode("utf-8", "replace")
    assert b"werkzeug-" in proc.stdout and b"TOTAL: 1 skill(s)" in proc.stdout
